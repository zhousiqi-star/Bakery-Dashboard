# Bakery production dashboard

**Group 4** · In-Class Group Exercise, Part 1

A one-screen Streamlit app that tells the production manager of a single French
bakery, every morning at 06:30, **which items to bake more of today and which to
bake less of** — using yesterday's till data.

- **App:** _(Streamlit Cloud URL — fill in after deploy)_
- **Repo:** _(public GitHub URL — fill in after push)_

---

## Step 1 — The dataset

| | |
|---|---|
| **Dataset** | [French Bakery Daily Sales](https://www.kaggle.com/datasets/matthieugimbert/french-bakery-daily-sales) |
| **File used** | `Bakery sales.csv` — 14.0 MB (limit was ~25 MB) |
| **Licence** | Data files © Original Authors |
| **Rows** | 234,005 receipt lines |
| **Columns** | `date`, `time`, `ticket_number`, `article`, `Quantity`, `unit_price` (+ a row-number column, dropped) |
| **Period** | 2021-01-02 → 2022-09-30 — **600 open days** inside a 637-day calendar span |
| **What one row is** | **one line on one till receipt**: one article, at one time, on one ticket |
| **Real or synthetic** | **Real.** The dataset page says: *"The dataset belongs to a French bakery."* The page states the objective as *"Forecast the sales in order to ease the production planning"* — which is exactly the decision this app supports. |

**Is it a toy dataset?** No. Not Iris, not Titanic, not California housing. It is
one real shop's till export, and it is awkward in the ways real exports are
awkward — the price column is French-formatted text, there are refunds, there are
days the shop was shut, and there are no category labels.

**The role: one person, not a department.** The **production manager**
(*chef de production*). She decides, once a day, how much of each item to make.
Everything on the page exists to change one number in that decision.

**Business area (from the allowed list): `sales`** — with `inventory` behaviour
inferred from it. The data has no inventory column; what it does have is the
*time of the last sale of each item each day*, which is the till-side fingerprint
of a shelf that emptied.

---

## Step 2 — The decision

> **If the production manager sees that an item's last sale yesterday came
> earlier than that item's own normal hour — while it still sold at its normal
> volume — she will bake more of it this morning; and if she sees an item sold
> far below its own normal share of the shop, she will bake less of it.**

Three things make this a real decision rather than a dashboard for its own sake:

1. **The right to change something exists.** She owns the bake plan. The action
   happens today, before the next data point arrives.
2. **The rhythm matches.** The data is produced once a day (till day-close); she
   decides once a day. Neither side is waiting on the other.
3. **Being late costs money, and the cost is nameable.** A baguette that sells out
   at 12:52 on a Friday instead of its usual 18:10 loses the whole afternoon's
   sales of the shop's single biggest item (144,756 € over the period, **25.9 %**
   of all revenue). A brioche baked 40 % too big is waste with no salvage value.
   Both errors are measured in the same currency and both are fixed tomorrow.

**Why not "revenue down 20 %"?** Because that is a fact, not an instruction. The
manager cannot bake a revenue figure. Every metric here ends in *this item, this
many more / fewer*.

---

## Step 3 — What is on the page

### The three headline numbers

| # | Metric | What it answers |
|---|---|---|
| 1 | **Yesterday's revenue vs its own same-weekday baseline** | Should today's bake be bigger or smaller *overall*? |
| 2 | **Items to bake more** — last sale earlier than their own median, while still selling ≥80 % of their normal volume | Which specific items ran out? |
| 3 | **Items to bake less** — no sale at all, or volume below 60 % of their own normal share of the shop | Which specific items are backing up? |

### Two supporting charts

- **Recent 12 same-weekdays, revenue vs baseline.** Gaps are *closed days*, never
  zero-filled. The bar for the day under analysis is red.
- **Last-sale clock for the TOP-20 items.** A grey tick is each item's own normal
  time; a coloured dot is yesterday. Red = ran out early, orange = sold short,
  green = normal, grey = no sale at all.

### The one filter

**Which weekday.** Not a date range, not a product picker. Sunday carries **22.6 %**
of annual revenue and Wednesday **9.0 %** — a 2.5× gap — so any average that pools
weekdays answers a question nobody asked. Picking the weekday is the only choice
that changes the answer materially.

### The two things I deliberately left out

1. **Average basket value.** The daily average basket is 3.85 €, and its
   p10–p90 range is only **3.24–4.79 €** (coefficient of variation **16.4 %**). It
   barely moves, so it cannot change a single batch size. Putting it on the page
   would spend one of the three metric slots on a number that never triggers an
   action.
2. **The intraday footfall curve.** The shop opens at a fixed hour and the
   production decision is finished before 07:00. Today's footfall curve is always
   *too late* to influence today's bake. It is a debrief input, not a decision
   input — it belongs in an after-close report, not on a pre-dawn screen.

### Where this page can mislead you

- **37 days with no rows are not days with 0 € of sales.** They are closed days,
  and **29 of them are Wednesdays** (the shop did not open on Wednesdays from
  January to April 2021). Wednesday therefore has only **62 observations** while
  every other weekday has 88–91. The chart shows a gap; it does not plot zero.
- **`unit_price` is text in French format** — `"0,90 €"`: comma decimal separator,
  euro sign, narrow no-break space. It must be cleaned before any arithmetic;
  otherwise the whole column stays a string and revenue silently becomes nonsense.
- **1,295 rows (0.55 %) have a negative `Quantity`**, totalling −2,201 units —
  refunds and corrections. They are excluded when computing the last sale of the
  day, otherwise a late refund pushes the "last sale" later and hides a genuine
  stock-out.
- **One `ticket_number` can hold several lines** (43.0 % of tickets have ≥2), so
  **row count is not customer count**. 234,005 rows are 136,451 tickets.
- **`COUPE` (3,526 €) is a slicing service, not a product**, and the 6 `DIVERS *`
  entries (10,749 € = **1.92 %**) are miscellaneous buckets that no category
  mapping can split. That is why this page has **no category chart** — the
  manager's decision unit is the individual article, and rolling up to categories
  would destroy exactly the granularity she can act on.
- **H1 2021 is a pandemic-depressed base.** Year-over-year growth in 2022 is
  partly recovery. The *absolute* percentage should be read with that in mind;
  the *ranking* of items is not affected.
- **Sunday is 2.5× Wednesday** (22.6 % vs 9.0 % of annual revenue), and the two
  are never comparable.

### Design decisions that were forced by the data, not chosen in advance

The first version of this dashboard used "the last 4 same weekdays" as the
baseline. Measured across the whole period, that baseline reports a revenue drop
of more than 20 % on **27.1 %** of all days — and on **75 %** of the days in
September 2022, when the summer peak simply ended. A baseline that cries wolf
every autumn is worse than no baseline. Switching to "the same weekday one year
earlier" cuts that to **15.9 %** overall and **7.1 %** in September 2022, so that
is what ships.

Likewise, an earlier version flagged "sold out early" on the last-sale time
alone. Checking 8,561 item-days showed that **19.2 %** of the early gaps came from
items that had simply sold badly that day. Adding the second condition — the item
must *also* have moved ≥80 % of its normal volume — drops the daily list to a mean
of **3.9 items**, and 20.8 % of days now return an empty list. A short list that
is right beats a long list that has to be argued with.

---

## Step 4 — How often the data refreshes, and why

**The data refreshes once a day, in the small hours,** after the till is closed
and the day's receipts are exported. This is a design fact, not a limitation: the
events being counted — a batch of dough going into the oven, a tray emptying —
happen a handful of times per day. There is no faster clock in the process.

**The manager reads it once a day, at 06:30,** five minutes before the first bake.
This is deliberately *not* the same frequency as the refresh. Refresh is a
property of the data; reading is a property of the decision. The oven is loaded
once a day, so looking twice would only produce the same answer twice.

**Why real time would be actively worse here.** A live screen would let her watch
the baguette shelf empty at 12:52 — at which point the dough for the afternoon
bake either exists or does not. Real-time visibility without real-time production
capacity converts an actionable decision into anxiety. What real time *does* buy
is a genuinely different feature:

> **An alert, not a dashboard.** If any TOP-20 item's last sale lands before its
> own baseline for **three consecutive occurrences of that weekday**, push a
> message at 06:00 instead of waiting to be looked at. That is a threshold event
> with a short list; it does not need a screen. The screen earns its keep on the
> questions that need human judgement — *is this a stock-out or did people simply
> not want it today?* — and those are answered once a day, not once a minute.

---

## Running it locally

```bash
uv sync                      # or: pip install -r requirements.txt
streamlit run app.py
```

Python 3.11+ (developed on 3.13; deploys on Streamlit Cloud with 3.14).

## Files

| File | What it is |
|---|---|
| `app.py` | the Streamlit page — layout, three metrics, two charts, three tables |
| `bakery.py` | data loading, price cleaning, and every metric in one place; run it directly for a self-check across all seven weekdays |
| `data/bakery_sales.csv` | the dataset (14.0 MB) |
| `requirements.txt` / `pyproject.toml` | dependencies |

## What this data cannot answer

The dataset contains **no stock, no production quantity, no waste, no sell-out
flag, no cost, no margin, no customer id, no discount, no weather, no shift, and
no category**.

So this dashboard can tell you **whether you under-baked** (the item ran out and
was still selling). It **cannot** tell you whether you over-baked — over-baking
shows up as unsold bread in the bin, and the bin is not in the export. The
"bake less" list is therefore built from the till-side proxy (sold far below its
own normal share), and it is honestly weaker evidence than the "bake more" list.
Saying so is part of the deliverable.
