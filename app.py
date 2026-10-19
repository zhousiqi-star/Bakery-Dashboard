"""Bakery production dashboard - Streamlit app.

Who it is for : the production manager (chef de production) of a single French
                bakery, at 06:30, before the first bake of the day.
What it does  : tells him which items ran out too early yesterday (bake more)
                and which ones sold clearly below their own normal share
                (bake less) - so he can change every batch this morning.

Run: streamlit run app.py
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from bakery import (
    CHART_OCC,
    DATA_PATH,
    SOFT_SHARE_RATIO,
    load_sales,
    analyze,
)

# 改成你的组名 —— 作业 Step 5 第 1 条要求标题里带队名。
TEAM_NAME = "Group 4"

st.set_page_config(page_title="Bakery production dashboard", layout="wide")


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="读取 234,005 行小票数据…")
def get_data() -> pd.DataFrame:
    return load_sales(DATA_PATH)


df = get_data()

data_start = df["date"].min()
data_end = df["date"].max()

# ---------------------------------------------------------------------------
# header
# ---------------------------------------------------------------------------
st.title("🥖 今天早上该多烤什么、少烤什么")
st.caption(
    f"{TEAM_NAME} · 给这家的**生产主管**看的：每天 06:30 开炉前 5 分钟，"
    "用昨天收银机的数据决定今天每一炉的产量。"
)

# ---------------------------------------------------------------------------
# filter — the only one he needs
# ---------------------------------------------------------------------------
dow_options = {
    "周一": 0, "周二": 1, "周三": 2, "周四": 3, "周五": 4, "周六": 5, "周日": 6,
}
c1, c2, c3 = st.columns([1, 1, 2])
with c1:
    dow_label = st.selectbox(
        "看哪个星期几",
        list(dow_options),
        index=4,
        help="不同星期的销量差 2.5 倍（周日占全年营收 22.6%，周三 9.0%），"
             "所以每个星期都要跟它自己的历史比。",
    )
res = analyze(df, dow_options[dow_label])

with c2:
    st.metric("分析的日子", f"{res['day']:%m-%d}", help=f"{res['weekday']}，数据集里该星期第 {res['n_occ']} 次营业")
with c3:
    st.markdown(
        f"<div style='padding-top:1.6rem;color:#666;font-size:0.9rem'>"
        f"这台收银机当天录了 <b>{res['lines_day']:,}</b> 行、<b>{res['tickets_day']:,}</b> 张小票"
        f"</div>",
        unsafe_allow_html=True,
    )

st.divider()

# ---------------------------------------------------------------------------
# top: the three headline numbers
# ---------------------------------------------------------------------------
basis_txt = "去年同期同一天" if res["rev_basis"] == "yoy" else "前 4 个同星期"
rev_delta = res["rev_delta"]

m1, m2, m3 = st.columns(3)
with m1:
    st.metric(
        f"{res['weekday']}营收",
        f"{res['rev_day']:,.0f} €",
        delta=f"{rev_delta:+.1f}% vs {basis_txt}" if pd.notna(rev_delta) else None,
        help="跟「去年同一天」比，不是跟上周比——上周可能还在旺季末尾，"
             "跟上周比会把季节回落当成生意变差。",
    )
with m2:
    st.metric(
        "该多烤的单品",
        f"{len(res['early'])} 个",
        help="昨天比它自己平常的时候更早就卖完了，而且还卖得动 → 明天多做",
    )
with m3:
    n_cut = len(set(res["absent"]["article"]) | set(res["soft"]["article"]))
    st.metric(
        "该少烤的单品",
        f"{n_cut} 个",
        help="昨天干脆没卖出去，或者销量掉到它自己正常份额的 60% 以下（而且没有提前卖完）→ 明天少做",
    )

# ---------------------------------------------------------------------------
# middle: the two charts that explain why
# ---------------------------------------------------------------------------
st.subheader("为什么是这个数")

left, right = st.columns([1, 1], gap="large")

with left:
    st.markdown(f"**① 最近 {CHART_OCC} 个{res['weekday']}的营收 vs 它自己的基线**")
    ch = res["chart1"]
    fig = go.Figure()
    fig.add_bar(
        x=ch["date"], y=ch["revenue"], name="当天营收",
        marker_color=["#c0392b" if r else "#95a5a6" for r in ch["is_day"]],
    )
    fig.add_scatter(
        x=ch["date"], y=ch["baseline"], name="基线",
        mode="lines+markers", line=dict(color="#2c3e50", width=2, dash="dot"),
    )
    fig.update_layout(
        height=340, margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        yaxis_title="€", xaxis_title=None,
        hovermode="x unified",
        xaxis=dict(tickformat="%m-%d"),
    )
    st.plotly_chart(fig, width='stretch')
    st.caption(
        "灰柱是已有数据，红柱是分析当天。断口是歇业日，不是营收 0——"
        "这家店 37 天没开门，其中 29 天是周三（2021 年 1–4 月每周三不开）。"
    )

with right:
    st.markdown(f"**② TOP-20 单品昨天最后卖出的时刻**")
    it = res["items"].dropna(subset=["today_minute"]).sort_values("revenue_12w", ascending=False).head(20)
    it = it.sort_values("base_minute")
    fig2 = go.Figure()
    fig2.add_scatter(
        x=it["base_minute"] / 60, y=it["article"], mode="markers",
        name="它自己的平常时刻（中位）",
        marker=dict(color="#bdc3c7", size=9, symbol="line-ns-open",
                    line=dict(width=2, color="#7f8c8d")),
    )
    colors = ["#c0392b" if s == "early" else "#27ae60" if s == "on_track" else "#f39c12"
              for s in it["state"]]
    fig2.add_scatter(
        x=it["today_minute"] / 60, y=it["article"], mode="markers",
        name="昨天实际",
        marker=dict(color=colors, size=11),
        text=[f"{a}：基线 {b} → 昨天 {t}" for a, b, t in
              zip(it["article"], it["base_hhmm"], it["today_hhmm"])],
        hoverinfo="text",
    )
    fig2.update_layout(
        height=340, margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        xaxis=dict(title="售出时刻（小时，24h）", range=[6, 21]),
        yaxis_title=None,
    )
    st.plotly_chart(fig2, width='stretch')
    st.caption(
        "同一个「卖完」时刻，对面包和对甜点是两件完全不同的事："
        "法棍平常卖到 18:45（全天补烤），布里欧修 12:32 就收工（早上一次出炉）。"
        "所以基线是每个单品**自己的**中位时刻，不是统一的钟点。"
    )

st.divider()

# ---------------------------------------------------------------------------
# bottom: the two action lists
# ---------------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs(
    [f"🔴 今天多烤（{len(res['early'])}）",
     f"🟢 今天少烤（{len(set(res['absent']['article']) | set(res['soft']['article']))}）",
     "全部 TOP-20"]
)

with tab1:
    if res["early"].empty:
        st.info("没有单品比它自己的常态更早卖完 —— 今天的产量按平常走。")
    else:
        show = res["early"].copy()
        show = show.assign(
            单品=show["article"],
            平常卖到=show["base_hhmm"],
            昨天卖到=show["today_hhmm"],
            早了=show["gap_hhmm"],
            昨天销量=show["today_qty"].round(0).astype("Int64"),
            平常销量=show["base_qty"].round(0).astype("Int64"),
            近12期营收=(show["revenue_12w"] / 12).round(1).map(lambda v: f"{v:.0f} €/期"),
        )
        st.dataframe(
            show[["单品", "平常卖到", "昨天卖到", "早了", "昨天销量", "平常销量", "近12期营收"]],
            hide_index=True, width='stretch',
        )
        st.caption(
            f"判定：昨天的最后售出时刻比它自己近 12 个{res['weekday']}的中位时刻早 30 分钟以上，"
            "**并且**昨天销量仍达到平常的 80% 以上。"
            "第二条是为了排除「本来就卖得差」——只早不少卖，才说明是卖光了，不是没人买。"
        )

with tab2:
    cut_absent = res["absent"][["article", "revenue_12w", "today_hhmm"]].copy()
    cut_absent = cut_absent.rename(columns={
        "article": "单品", "revenue_12w": "近12期营收", "today_hhmm": "昨天最后售出",
    })
    cut_absent.insert(1, "原因", "昨天完全没卖出去")
    cut_absent["昨天份额"] = "0%"

    cut_soft = res["soft"][["article", "revenue_12w", "share_ratio", "qty_ratio"]].copy()
    cut_soft = cut_soft.rename(columns={
        "article": "单品", "revenue_12w": "近12期营收", "share_ratio": "昨天份额",
    })
    cut_soft.insert(1, "原因", "卖得动，但明显少于它自己的常态")
    cut_soft["昨天最后售出"] = "正常时段"
    cut_soft["昨天份额"] = cut_soft["昨天份额"].map(lambda v: f"{v:.0%}")
    cut_soft = cut_soft[["单品", "原因", "近12期营收", "昨天最后售出", "昨天份额"]]

    if cut_absent.empty and cut_soft.empty:
        st.info("没有该砍的单品。")
    else:
        both = pd.concat([cut_absent, cut_soft], ignore_index=True)
        both["近12期营收"] = both["近12期营收"].round(0).astype("Int64").map(lambda v: f"{v:,} €")
        st.dataframe(both, hide_index=True, width='stretch')
        st.caption(
            f"「明显少于常态」= 昨天卖出的件数占全店的比例，低于它自己在近 12 个"
            f"{res['weekday']}的同一比例中位数的 {SOFT_SHARE_RATIO:.0%}，"
            "**并且**它没有提前卖完（提前卖完是备少了，归上面那张表）。"
            "用份额而不是绝对件数，是因为整个店在各个季节的客流不同——"
            "9 月全店都少卖三成的时候，绝对件数会把 8 个单品同时误报成卖不动。"
        )

with tab3:
    allit = res["items"].copy()
    label = {"early": "🔴 早卖完", "soft": "🟠 卖得少",
             "on_track": "✅ 正常",
             "absent": "🟢 没卖出", "thin": "⚪ 数据不足"}
    allit["状态"] = allit["state"].map(label)
    out = allit.assign(
        单品=allit["article"],
        近12期营收=allit["revenue_12w"].round(0).astype("Int64").map(lambda v: f"{v:,} €"),
        平常卖到=allit["base_hhmm"],
        昨天卖到=allit["today_hhmm"],
        差了=allit["gap_hhmm"],
        观测数=allit["n_obs"],
    )[["状态", "单品", "近12期营收", "平常卖到", "昨天卖到", "差了", "观测数"]]
    st.dataframe(
        out.sort_values(["状态", "近12期营收"], ascending=[True, False]),
        hide_index=True, width='stretch',
    )
    st.caption(
        f"这 20 个单品占近 {CHART_OCC} 个{res['weekday']}营收的 {res['top_share']:.1%}。"
        "只盯这 20 个，是因为剩下 129 个加起来不到四分之一，管不过来也不值得管。"
    )

# ---------------------------------------------------------------------------
# footer: data period + refresh frequency (assignment Step 4 requirement)
# ---------------------------------------------------------------------------
st.divider()
st.caption(
    f"**数据期间**：{data_start.year} 年 {data_start.month} 月 – "
    f"{data_end.year} 年 {data_end.month} 月（Kaggle 快照，"
    f"600 个营业日）。**生产环境刷新频率：每天凌晨一次**（收银机日结后导出）。"
    f"主管每天 06:30 看一次——刷新和复盘不同频，是因为炉子一天只排一次。"
)

with st.expander("这个页面故意没放什么，以及哪里容易看错"):
    st.markdown(
        """
**故意没放的两样：**

1. **客单价**。全期中位数 3.85 €，p10–p90 只有 3.24–4.79 €，几乎不动。
   它变化的那点幅度不足以改变任何一炉的产量，放上去只会占掉一个指标位。
2. **小时级客流曲线**。开门时间固定、生产决策在 07:00 前就做完了，
   当天的客流曲线对「今天烤多少」永远来得太晚——它是复盘材料，不是决策输入。
   （如果要它，应该做成打烊后的日报，不是开炉前的大屏。）

**容易看错的地方：**

- **37 天没有记录 ≠ 那天卖 0**。这 37 天是歇业，其中 **29 天是周三**（2021 年 1–4 月每周三不开门），
  所以周三是唯一一个只有 62 个观测的星期。图上断口就是断口，没有补零。
- **`unit_price` 是法文文本** `"0,90 €"`（逗号当小数点 + 欧元符号 + 窄空格），
  必须清洗后才能算营收，否则整列变字符串。
- **`Quantity` 有 1,295 行负数**（0.55%，合计 −2,201 件），是退货/更正。
  算「最后售出时刻」时已排除，否则会把断货时刻往后推、掩盖真的卖光。
- **一个 `ticket_number` 可以有多行**（43% 的小票 ≥2 行），所以行数不是客流。
- **`COUPE`（3,526 €）是切片服务，不是商品**；8 个 `DIVERS *`（合计 10,749 € = 1.92%）是杂项桶，
  任何品类映射都拆不开——所以这里根本不做品类图。
- **2021 上半年是疫情低基数**。用「去年同期」基线时，2022 年的同比会偏正；
  这不是生意突然变好，所以绝对增幅要谨慎读。
- **周日是周三的 2.5 倍**（22.6% vs 9.0% 年营收）。任何把星期混在一起的均值都没有意义，
  所以这个页面强迫你先选星期几。
"""
    )
