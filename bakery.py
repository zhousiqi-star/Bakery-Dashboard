"""Bakery production dashboard - loading, cleaning and every metric in one place.

Source : Kaggle "French Bakery Daily Sales" (matthieugimbert/french-bakery-daily-sales)
Raw file: data/bakery_sales.csv
          234,005 receipt lines | 600 open days | 149 articles | 1 shop
          2021-01-02 .. 2022-09-30 | revenue 558,641 EUR

Two design rules, both forced by what the data actually showed:

1. Every comparison is made *within a single weekday*. Sunday carries 22.6% of
   annual revenue and Wednesday 9.0%, so a pooled average answers a different
   question from the one the production manager asks.

2. The revenue baseline is "same weekday one year ago", not "last 4 weeks".
   Measured over the same span, a 4-week baseline misses by more than -20% on
   29.1% of days (it cannot cross a seasonal turn); the year-over-year baseline
   misses on 15.9%. In 2022-09, when the summer peak ends, the 4-week baseline
   flags 75% of days as a revenue drop that did not happen - year-over-year
   flags 7%. A baseline that cries wolf every autumn is worse than no baseline.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA_PATH = Path(__file__).parent / "data" / "bakery_sales.csv"

# Code, data and documentation stay in English; only the Streamlit layer is
# translated, because the bakery itself is French (see README, "Language").
# This module therefore returns English weekday names and English state keys;
# app.py is the only file that speaks French.
WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# ---- tunable windows (counted in same-weekday occurrences, never in days) ----
YOY_MIN_DAYS = 360          # "one year ago" window, in calendar days ...
YOY_MAX_DAYS = 370          # ... ±5 days around the 364-day mark
REV_FALLBACK_OCC = 4        # if no year-ago data yet: last 4 same weekdays
CHART_OCC = 12              # chart 1: most recent 12 same weekdays
BASE_OCC = 12               # an item's own baseline: previous 12 same weekdays
MIN_OBS = 8                 # fewer observations than this -> no verdict
MIN_GAP_MIN = 30            # "early" = >= 30 min before ITS OWN median time
MIN_QTY_RATIO = 0.80        # ...and it still moved >= 80% of its normal volume
TOP_N = 20                  # decision granularity: revenue top 20 = 75.6% of sales
SOFT_SHARE_RATIO = 0.60     # "soft" = sold < 60% of the share of shop units it owns


# ---------------------------------------------------------------------------
# loading / cleaning
# ---------------------------------------------------------------------------
def _clean_price(s: pd.Series) -> pd.Series:
    """'0,90\u202f€' -> 0.9 (French decimal comma, euro sign, narrow no-break space)."""
    out = (
        s.astype("string")
        .str.replace("\u202f", "", regex=False)
        .str.replace("\u00a0", "", regex=False)
        .str.replace("\u20ac", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    return pd.to_numeric(out, errors="coerce")


def load_sales(path: Path | str = DATA_PATH) -> pd.DataFrame:
    """Read the raw CSV and attach the derived columns every metric needs."""
    df = pd.read_csv(path)
    df = df.drop(columns=[c for c in df.columns if c.startswith("Unnamed")])

    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
    df["article"] = df["article"].astype("string").str.strip()
    df["price"] = _clean_price(df["unit_price"])
    df["revenue"] = df["Quantity"] * df["price"]

    hhmm = df["time"].astype("string").str.zfill(5)
    df["minute"] = hhmm.str.slice(0, 2).astype(int) * 60 + hhmm.str.slice(3, 5).astype(int)
    df["dow"] = df["date"].dt.dayofweek            # 0 = Monday
    df["ticket_number"] = df["ticket_number"].astype("Int64")
    return df


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def fmt_hhmm(m: float | int | None) -> str:
    if m is None or pd.isna(m):
        return "—"
    m = int(round(float(m)))
    return f"{m // 60:02d}:{m % 60:02d}"


def sold_table(df: pd.DataFrame) -> pd.DataFrame:
    """Per (date, article): minute of the last sale that day, and units sold.

    Only positive-quantity rows count. 1,295 rows (0.55%) carry a negative
    Quantity - refunds and corrections - and letting them count would push the
    "last sale" later than the last real sale, hiding a stock-out.
    """
    pos = df[df["Quantity"] > 0]
    out = pos.groupby(["date", "article"], as_index=False).agg(
        last_minute=("minute", "max"), qty=("Quantity", "sum")
    )
    return out.set_index(["date", "article"])


# ---------------------------------------------------------------------------
# the analysis
# ---------------------------------------------------------------------------
def analyze(df: pd.DataFrame, dow: int) -> dict:
    """Everything the dashboard shows, for the latest open occurrence of `dow`."""
    cal = pd.DatetimeIndex(sorted(df["date"].unique()))
    dates = list(cal[cal.dayofweek == dow])
    if len(dates) < MIN_OBS + REV_FALLBACK_OCC:
        raise ValueError(f"dow={dow}: only {len(dates)} open occurrences in the data")

    day = dates[-1]
    prev = dates[:-1]

    daily_rev = df.groupby("date")["revenue"].sum()
    daily_lines = df.groupby("date").size()
    daily_tickets = df.groupby("date")["ticket_number"].nunique()

    sold = sold_table(df)
    last_min = sold["last_minute"]
    qty = sold["qty"]

    def last_of(d, art) -> float:
        try:
            v = last_min.loc[(d, art)]
        except KeyError:
            return float("nan")
        return float(v) if pd.notna(v) else float("nan")

    def qty_of(d, art) -> float:
        try:
            v = qty.loc[(d, art)]
        except KeyError:
            return 0.0
        return float(v) if pd.notna(v) else 0.0

    def baseline_for(d) -> tuple[float, str, list]:
        """Same weekday one year earlier; fall back to the last 4 occurrences."""
        i = dates.index(d)
        prior = [x for x in dates[:i]
                 if YOY_MIN_DAYS <= (d - x).days <= YOY_MAX_DAYS]
        if prior:
            return float(daily_rev.reindex(prior).mean()), "yoy", prior
        prior = dates[max(0, i - REV_FALLBACK_OCC): i]
        if not prior:
            return float("nan"), "none", []
        return float(daily_rev.reindex(prior).mean()), "4wk", prior

    # ---- metric 1: revenue vs its own same-weekday baseline -----------------
    rev_day = float(daily_rev.get(day, 0.0))
    rev_base, base_kind, base_dates = baseline_for(day)
    rev_delta = (rev_day / rev_base - 1.0) * 100 if rev_base and rev_base > 0 else float("nan")

    # ---- chart 1: last 12 occurrences, each vs its own baseline -------------
    chart_rows = []
    for d in dates[-CHART_OCC:]:
        b, kind, _ = baseline_for(d)
        chart_rows.append({
            "date": d,
            "revenue": float(daily_rev.get(d, 0.0)),
            "baseline": b,
            "delta": (float(daily_rev.get(d, 0.0)) / b - 1.0) * 100 if b and b > 0 else float("nan"),
            "basis": kind,
            "tickets": int(daily_tickets.get(d, 0)),
            "lines": int(daily_lines.get(d, 0)),
            "is_day": d == day,
        })
    chart1 = pd.DataFrame(chart_rows)

    # ---- decision universe: revenue top-N over the last 12 occurrences ------
    win_dates = set(dates[-CHART_OCC:])
    recent = df[df["date"].isin(win_dates)]
    top = (recent.groupby("article")["revenue"].sum()
           .sort_values(ascending=False).head(TOP_N))
    top_articles = list(top.index)
    top_share = float(top.sum() / recent["revenue"].sum()) if recent["revenue"].sum() else float("nan")

    # shop-wide unit totals, so an item can be judged against its own share of
    # the shop instead of against its own raw volume (see SOFT_SHARE_RATIO)
    pos = df[df["Quantity"] > 0]
    day_units = pos.groupby("date")["Quantity"].sum()
    art_units = pos.groupby(["date", "article"])["Quantity"].sum()

    # ---- metric 2: how each top item behaved against its own normal day -----
    hist = prev[-BASE_OCC:]
    rows = []
    for art in top_articles:
        h_min = pd.Series([last_of(d, art) for d in hist], dtype="float64").dropna()
        h_qty = pd.Series([qty_of(d, art) for d in hist], dtype="float64")
        n_obs = int(len(h_min))
        base_min = float(h_min.median()) if n_obs else float("nan")
        base_qty = float(h_qty[h_qty > 0].median()) if (h_qty > 0).any() else float("nan")

        shares = []
        for d in hist:
            tot = float(day_units.get(d, 0.0))
            if tot > 0:
                shares.append(float(art_units.get((d, art), 0.0)) / tot)
        base_share = float(pd.Series(shares).median()) if shares else float("nan")

        t_min = last_of(day, art)
        t_qty = qty_of(day, art)
        ratio = t_qty / base_qty if base_qty and base_qty > 0 else float("nan")
        gap = base_min - t_min if (pd.notna(base_min) and pd.notna(t_min)) else float("nan")

        tot_today = float(day_units.get(day, 0.0))
        share_ratio = (
            (t_qty / tot_today) / base_share
            if (pd.notna(base_share) and base_share > 0 and tot_today > 0)
            else float("nan")
        )

        if pd.isna(t_min):
            state = "absent"
        elif n_obs < MIN_OBS or pd.isna(base_min):
            state = "thin"
        elif gap >= MIN_GAP_MIN and pd.notna(ratio) and ratio >= MIN_QTY_RATIO:
            state = "early"
        elif pd.notna(share_ratio) and share_ratio <= SOFT_SHARE_RATIO:
            state = "soft"
        else:
            state = "on_track"

        rows.append({
            "article": art,
            "revenue_12w": float(top[art]),
            "base_minute": base_min,
            "base_hhmm": fmt_hhmm(base_min),
            "today_minute": t_min,
            "today_hhmm": fmt_hhmm(t_min),
            "gap_min": gap,
            "gap_hhmm": fmt_hhmm(abs(gap)) if pd.notna(gap) else "—",
            "base_qty": base_qty,
            "today_qty": t_qty,
            "qty_ratio": ratio,
            "base_share": base_share,
            "share_ratio": share_ratio,
            "n_obs": n_obs,
            "state": state,
        })
    items = pd.DataFrame(rows)

    early = (items[items["state"] == "early"]
             .sort_values(["gap_min", "revenue_12w"], ascending=[False, False]))
    absent = (items[items["state"] == "absent"]
              .sort_values("revenue_12w", ascending=False))
    soft = (items[items["state"] == "soft"]
            .sort_values(["share_ratio", "revenue_12w"], ascending=[True, False]))
    on_track = items[items["state"] == "on_track"]

    return {
        "dow": dow,
        "weekday": WEEKDAY_NAMES[dow],
        "day": day,
        "n_occ": len(dates),
        # metric 1
        "rev_day": rev_day,
        "rev_base": rev_base,
        "rev_delta": rev_delta,
        "rev_basis": base_kind,
        "base_dates": base_dates,
        "tickets_day": int(daily_tickets.get(day, 0)),
        "lines_day": int(daily_lines.get(day, 0)),
        # chart 1
        "chart1": chart1,
        # metric 2
        "items": items,
        "early": early,
        "absent": absent,
        "soft": soft,
        "on_track": on_track,
        "top_share": top_share,
    }


def self_check(df: pd.DataFrame) -> None:
    for dow in range(7):
        try:
            r = analyze(df, dow)
        except ValueError as e:
            print(f"dow={dow}: {e}")
            continue
        print(
            f"{r['weekday']} {r['day']:%Y-%m-%d} occ={r['n_occ']:>2} "
            f"rev {r['rev_day']:>6,.0f}EUR vs {r['rev_base']:>6,.0f}EUR "
            f"({r['rev_delta']:+5.1f}%, {r['rev_basis']}) | "
            f"early {len(r['early']):>2} absent {len(r['absent']):>2} "
            f"soft {len(r['soft']):>2} ok {len(r['on_track']):>2}"
        )


if __name__ == "__main__":
    d = load_sales()
    print(f"rows={len(d):,} articles={d['article'].nunique()} days={d['date'].nunique()} "
          f"{d['date'].min():%Y-%m-%d}..{d['date'].max():%Y-%m-%d}")
    print(f"price parsed {d['price'].notna().mean():.4%} range "
          f"{d['price'].min():.2f}-{d['price'].max():.2f} "
          f"revenue {d['revenue'].sum():,.0f}EUR neg-qty {(d['Quantity'] < 0).sum():,}")
    print()
    self_check(d)
