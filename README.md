# 🥖 Bakery production dashboard — **Siqi Zhou**

In-Class Group Exercise, Part 1 · single-member team

**EN** — A one-screen Streamlit app that tells the production manager of one French
bakery, every morning at 06:30, **which items to bake more of today and which to
bake less of**, using yesterday's till data.

**中文** — 一个单页 Streamlit 应用，每天 06:30 开炉前，用昨天收银机的数据告诉一家法国面包店的**生产主管：今天哪几样该多烤、哪几样该少烤**。

- **App:** <https://bakery-dashboard-bnzfchs8jw5cuizxfbctpb.streamlit.app>
- **Repo:** <https://github.com/zhousiqi-star/Bakery-Dashboard>

---

## Language / 语言选择

**EN** — The dataset page states *"The dataset belongs to a French bakery"*: the
articles are French (`TRADITIONAL BAGUETTE`, `KOUIGN AMANN`, `BANETTE`), the prices
are written `"0,90 €"` (decimal comma, euro sign, narrow no-break space), and the
dataset author documents `COUPE` as the service where customers have their whole
bread sliced. **The person this page is for is a French baker at 06:30 in the
morning**, so the page itself is in **French** — the language of the person making
the decision, not the language of the course.

Everything that is read by a developer rather than by the baker stays in **English**:
`bakery.py`, the comments, the EDA notebook, and the first half of every section
below. The README is bilingual so both audiences can check it.

One implementation consequence worth knowing: because the UI and the library speak
different languages, `bakery.py` returns **English** weekday names and English state
keys (`early` / `soft` / `absent` / `on_track` / `thin`), and `app.py` alone holds
the translation layer (`JOURS`, `MOIS`, `fr_num`, `fr_pct`, `fr_articles`). No French
string ever leaks into the data layer, so the metrics stay testable without a UI.

**中文** — 数据集的页面原文写着 *"The dataset belongs to a French bakery"*：商品名是法语（`TRADITIONAL BAGUETTE`、`KOUIGN AMANN`、`BANETTE`），价格写成 `"0,90 €"`（逗号当小数点、欧元符号、窄空格），作者还专门解释了 `COUPE` 是"帮客人把整条面包切片"的服务。**这个页面是给一位法国面包师在早上六点半看的**，所以页面语言用**法语**——用做决定的人的语言，而不是课程的语言。

凡是给开发者看、不给面包师看的东西，一律保持**英语**：`bakery.py`、代码注释、EDA notebook，以及下面每一节的前半部分。README 中英对照，两边的人都能核对。

一个实现上的后果值得说明：界面和数据层语言不同，所以 `bakery.py` 返回**英语**的星期名和英语状态键（`early` / `soft` / `absent` / `on_track` / `thin`），只有 `app.py` 持有翻译层（`JOURS`、`MOIS`、`fr_num`、`fr_pct`、`fr_articles`）。法语字符串永远不会漏进数据层，所以指标不依赖界面也能被测试。

---

## Step 1 — The dataset / 数据集

| | |
|---|---|
| **Dataset** | [French Bakery Daily Sales](https://www.kaggle.com/datasets/matthieugimbert/french-bakery-daily-sales) |
| **File used** | `Bakery sales.csv` — 14.0 MB (limit was ~25 MB) |
| **Licence** | Data files © Original Authors |
| **Rows** | 234,005 receipt lines |
| **Columns** | `date`, `time`, `ticket_number`, `article`, `Quantity`, `unit_price` (+ an exported row-number column, dropped) |
| **Period** | 2021-01-02 → 2022-09-30 — **600 open days** inside a 637-day calendar span |
| **What one row is** | **one line on one till receipt**: one article, at one time, on one ticket |
| **Real or synthetic** | **Real.** Page text: *"The dataset belongs to a French bakery"*, objective *"Forecast the sales in order to ease the production planing"* — which is exactly the decision this app supports. |
| **Country** | 🇫🇷 **France** (single shop; French article names and French price formatting) |

**EN — Is it a toy dataset?** No. Not Iris, not Titanic, not California housing. It
is one real shop's till export, and it is awkward in the ways real exports are
awkward: the price column is French-formatted *text*, there are refunds, there are
days the shop was shut, and there is no category column.

**中文 —— 它是不是教学玩具？** 不是。不是 Iris、不是 Titanic、不是 California housing。这是**一家真实门店的收银机导出**，而且它像所有真实的导出一样别扭：价格列是法文**文本**，有退货，有歇业日，而且**没有品类列**。

**The role: one person, not a department.**
**角色：一个人，不是一个部门。**

**EN** — The **production manager** (*responsable de production*). She decides, once
a day, how much of each item to make. Every element on the page exists to change one
number in that decision.

**中文** — **生产主管**。她每天决定一次：每一样做多少。页面上的每一个元素，都必须能改变这个决定里的某一个数字。

**Business area / 业务领域** — `sales`, with the **inventory** question inferred from
it. The export has no inventory column; what it does have is the *time of the last
sale of each item each day*, which is the till-side fingerprint of a shelf that
emptied. / 归入 `sales`，并从中推断出 **inventory** 问题。导出里没有库存列，但它有**每样单品每天最后售出的时刻**——那是"货架空了"在收银机一侧留下的指纹。

**Why not the other directions** — a category trend chart is impossible here (no
category column, and the `article` names are coarse buckets: `TRAITEUR` alone hides
**67 distinct prices**), and a customer/retention dashboard is impossible too (no
customer id). The two questions this data can actually answer are *did we run out*
and *did this item lose its share of the basket*.
/ **为什么不做别的方向**——品类趋势图做不了（没有品类列，而且 `article` 是粗粒度桶，`TRAITEUR` 一个名字下藏着 **67 个不同单价**）；用户/留存也做不了（没有客户 ID）。这份数据真正能回答的只有两个问题：**有没有卖断**、**某单品有没有丢掉它自己的份额**。

---

## Step 2 — Justify the dashboard / 为什么值得做一张大屏

> **EN** — **If** the production manager sees that an item's last sale yesterday came
> **earlier than that item's own normal hour** — while it still sold at ≥80 % of its
> normal volume — **she will bake more of it this morning**; and **if** she sees an
> item sold **far below its own normal share of the shop** (and it did not run out),
> **she will bake less of it.**

> **中文** —— **如果**生产主管看到某单品昨天的最后售出时刻**早于它自己的平常时刻**，而且它昨天仍卖到了平常量的 80% 以上（说明是卖光了，不是没人买），**她今天早上就会多做这一样**；**如果**她看到某单品卖出的份额**远低于它自己平常的份额**，而且它没提前卖完（说明是备多了），**她今天早上就会少做这一样**。

### 1. Who looks at it, and how often / 谁看，多久看一次

**EN** — The production manager, **once a day at 06:30**, five minutes before the
first bake. Not the owner, not the accountant, not "the team".

**中文** — 生产主管本人，**每天早上 06:30 一次**，开炉前五分钟。不是老板、不是会计、不是"大家"。

### 2. The decision it supports / 它支撑什么决定

See the sentence above. It ends in a **repeated physical action** — changing a batch
size — not in "being informed". / 见上面那句话。它的落点是一个**每天重复发生的物理动作**（改一炉的产量），不是"了解到情况"。

### 3. What she does today without it, and what that costs / 没有这张表她今天怎么做，代价是什么

**EN** — Today she uses two things: the **paper production sheet from the same
weekday last week**, and a **glance at what is left on the shelf at closing**. Both
are unreliable in one specific, measurable way.

- **The cost in mistakes — this is the expensive one.** A till records the sales that
  *happened*; it cannot record the customer who walked in at 16:00, found no
  croissant and left. So "sold badly" and "sold out" look **identical** on paper.
  Measured on this data: of 8,785 item-days, **2,405 ended "early" by an hour or
  more, and 19.5 % of those (469) were items that had sold less than half their
  normal volume** — they were not sold out at all, they were simply not wanted that
  day. A method that cannot separate those two cases acts on the wrong half of them.
- **The cost in repetition.** The mistake does not get fixed once — it repeats. A
  weekday pattern recurs **52 times a year**. Reusing last week's sheet means last
  week's error is baked again this week.
- **The cost in time.** Reconstructing "what did this item normally do" from a stack
  of paper sheets is manual work every morning; the page answers it in one look, at
  the granularity of the actual decision (**3.56 items per day** need a change, median
  3, p90 7 — not 149).

**中文** — 今天她用两样东西：**上周同一个星期的纸质生产单**，和**打烊时瞄一眼货架还剩什么**。这两样都在一个具体、可测量的地方不可靠。

- **错误的代价——这是最贵的一项。** 收银机记录的是**发生了的**销售；它记录不了下午四点钟走进来、发现可颂没了、然后走掉的那位客人。所以"卖得差"和"卖光了"在纸上**长得一模一样**。在这份数据上实测：8,785 个"单品×日"观测里，有 **2,405 次提前一小时以上收工，其中 19.5%（469 次）其实当天只卖到平常量的一半以下**——那根本不是卖光了，是那天没人要。分不开这两种情况的方法，有一半的决策是做错的。
- **重复的代价。** 错误不会被修一次就消失——它会重演。同一个星期的规律**一年重复 52 次**。用上周的生产单，等于把上周的错误再烤一遍。
- **时间的代价。** 从一叠纸里回溯"这一样平常卖多少"是每天早上都要做的体力活；这张表一眼答完，而且是在决策真正的颗粒度上答的：每天**平均 3.56 个单品**需要改（中位 3、p90 7），不是 149 个。

### 4. Why a dashboard, and not an email / report / alert / 为什么是大屏，而不是邮件、周报或告警

**EN** — Because the question needs **human judgement once a day, with two signals
that must be read together**. "Did this item run out, or did it just not sell?" is
*not* answerable by a threshold — it needs the two conditions side by side (time of
last sale vs its own median, plus volume vs its own normal). That is a judgement,
made once, by a person, at a fixed hour.

Where it is *not* a judgement — a stock-out that keeps repeating — the right product
is an **alert, not a screen**, and Step 4 says exactly which one that is.

**中文** — 因为这个问题需要**人每天判断一次，而且两个信号必须放在一起读**。"这一样是卖光了，还是今天就是没人要？"**不是阈值能回答的**——它需要把两个条件并排放在眼前（最后售出时刻 vs 它自己的中位，加上销量 vs 它自己的常态）。这是判断，一天一次，由人来做，在固定的钟点。

凡是**不需要判断**的部分——反复出现的断货——正确的产品形态是**告警，不是大屏**，Step 4 指明了是哪一个。

---

## Step 3 — What matters, and what I cut / 放什么、砍什么

The EDA notebook is `eda_bakery.ipynb` (pandas + matplotlib, 15 code cells, 5
figures, all outputs committed). Every finding below is a cell output, not a guess.
/ EDA 在 `eda_bakery.ipynb` 里（pandas + matplotlib，15 个代码单元、5 张图，输出已提交）。下面每条结论都是某个单元的真实输出，不是猜的。

### The three headline numbers (top of the page, within 5 seconds) / 顶部三个指标

| # | Metric | What it answers | 中文 |
|---|---|---|---|
| 1 | **Yesterday's revenue vs its own same-weekday baseline** | Should today's bake be bigger or smaller *overall*? | 昨天营收 vs 它自己的同星期基线——今天整体该加量还是减量？ |
| 2 | **Items to bake more** — last sale earlier than their own median **while still selling ≥80 % of normal volume** | Which specific items ran out? | 该多烤——比自己的中位时刻早收工，**且**仍卖到常态 80% 以上 |
| 3 | **Items to bake less** — no sale at all, or volume below **60 % of their own normal share of the shop** | Which specific items are backing up? | 该少烤——完全没卖出，或销量跌破自己平常份额的 60% |

All three end in **an item count she can act on**, not in a rate. / 三个指标的落点都是**她能动手的单品数**，不是一个百分比。

### Two supporting charts / 两张支撑图

- **Recent 12 same-weekdays, revenue vs its own baseline.** Gaps are **closed days**,
  never zero-filled. The day under analysis is the red bar.
  / 最近 12 个同星期的营收 vs 它自己的基线。断口是**歇业日**，从不补零。分析当天是红柱。
- **Last-sale clock for the TOP-20 items.** A grey tick is each item's own normal
  time; a coloured dot is yesterday. Red = ran out early, orange = sold short, green =
  normal, grey = no sale at all.
  / TOP-20 的"最后售出时刻"横条。灰线是每样**自己的**平常时刻，彩点是昨天。红=早卖完，橙=卖得少，绿=正常，灰=完全没卖。

The second chart is the one that makes the page defensible: it makes visible that
**"sold out at 12:24" is catastrophic for a brioche and completely normal for the
baguette**, whose median last sale is **18:42** because it is baked in waves all day.
A single global cut-off would fire on 24.8 % of brioches and 0.0 % of baguettes.
/ 第二张图是这张页面站得住脚的原因：它让"12:24 就卖完"这件事对布里欧修是灾难、对法棍完全正常这件事变得可见——法棍中位卖到 **18:42**，因为它是全天分批补烤的。一个统一的钟点阈值，会对 24.8% 的布里欧修报警、对法棍 0.0%。

### The one filter / 唯一的一个筛选

**Which weekday.** Not a date range, not a product picker, not ten sliders.
**Which weekday**, because Sunday carries **22.6 %** of annual revenue and Wednesday
**9.0 %** — a **2.5×** gap — so any average that pools weekdays answers a question
nobody asked.

**中文** — **哪一个星期几**。不是日期区间，不是单品多选，不是十个滑块。因为周日占全年营收 **22.6%**、周三 **9.0%**，差 **2.5 倍**——任何把星期混在一起的均值，回答的都是没人问过的问题。

A date-range slider was considered and rejected: it would let her compare a Sunday
against a Wednesday, which is the single most common way to read this shop's numbers
wrong. / 曾考虑加日期区间滑块，已否决：那会让她拿周日跟周三比，而这是把这家店的数字读错最常见的一种方式。

### The two things I deliberately left out / 故意没放的两样

**1. Average basket / 客单价**
**EN** — the daily average basket has a median of **3.85 €** and a p10–p90 of only
**3.24–4.79 €** (coefficient of variation **16.4 %**). It barely moves, so it cannot
change a single batch size. Putting it on the page would spend one of three metric
slots on a number that never triggers an action. It is in the notebook, not the app.
**中文** — 日均客单价中位 **3.85 €**，p10–p90 只有 **3.24–4.79 €**（变异系数 **16.4%**）。它几乎不动，改不了任何一炉的产量。放上去等于用一个指标位换一个永远不会触发动作的数字。它在 notebook 里，不在大屏上。

**2. Intraday footfall curve / 小时级客流曲线**
**EN** — the shop opens at a fixed hour and the bake plan is finished before 07:00.
Today's footfall curve is therefore always **too late** to influence today's bake. It
is a **debrief** input, not a decision input; it belongs in an after-close report.
**中文** — 开门时间固定，生产决策在 07:00 前就做完了。所以当天的客流曲线**永远来不及**影响当天的出炉。它是**复盘**材料，不是决策输入；它属于打烊后的日报。

### Where this page can mislead you / 哪里容易看错

Every one of these is handled on the page, mostly as a caption — the point of this
list is that the page **does not hide them**.
/ 下列每一条页面都处理了（多数是一条 caption）——这份清单的意义在于：页面**不藏**这些事。

- **37 days with no rows are not days with 0 € of sales.** They are closed days, and
  **29 of the 37 are Wednesdays** (the shop did not open on Wednesdays from January to
  April 2021). Wednesday therefore has only **62 observations** while the others have
  88–91. The chart shows a gap; it never plots a zero.
  / **37 天没有任何记录，不等于那 37 天卖了 0 €。** 那是歇业，其中 **29 天是周三**。所以周三只有 **62 个观测**，其他星期有 88–91 个。图上是断口，从不画零。
- **`unit_price` is text in French format** — `"0,90 €"`: comma decimal separator,
  euro sign, narrow no-break space (`U+202F`). It must be cleaned before any
  arithmetic, otherwise the column stays a string and revenue silently becomes wrong.
  / **`unit_price` 是法文格式的文本** `"0,90 €"`。不清洗就做算术，整列变字符串，营收会**静默地**算错。
- **1,295 rows (0.55 %) have a negative `Quantity`**, totalling **−2,201 units** —
  refunds and corrections. Excluded when computing the last sale of the day, otherwise
  a late refund pushes the "last sale" later and hides a genuine stock-out.
  / **1,295 行（0.55%）`Quantity` 为负**，合计 **−2,201 件**，是退货和更正。算"最后售出时刻"时已排除，否则一次迟到的退货会把断货时刻往后推，掩盖真的卖光。
- **One `ticket_number` can hold several lines** (43.0 % of tickets have ≥2), so **row
  count is not customer count**: 234,005 rows are 136,451 tickets. And the per-ticket
  basket median is 2.50 € — which is *not* the 3.85 € daily average quoted above;
  two different denominators, both correct, and confusing them is easy.
  / **一张小票可以有多行**（43.0% 的小票 ≥2 行），所以**行数不是客流**：234,005 行 = 136,451 张小票。按小票算的客单价中位是 2.50 €，**不是**上面那个 3.85 € 的日均值——两个分母都正确，但很容易混。
- **`COUPE` (3,526 €) is a slicing service, not a product**, and the 6 `DIVERS *`
  entries (10,749 € = **1.92 %**) are miscellaneous buckets that no category mapping
  can split. That is why this page has **no category chart**: the manager's decision
  unit is the individual article, and rolling up to categories would destroy exactly
  the granularity she can act on.
  / **`COUPE`（3,526 €）是切片服务，不是商品**；6 个 `DIVERS *`（10,749 € = **1.92%**）是任何品类映射都拆不开的杂项桶。所以这里**没有品类图**：她的决策单位是单个 article，汇总到品类正好抹掉唯一可行动的粒度。
- **H1 2021 is a pandemic-depressed base.** 2022 year-over-year growth is partly
  recovery; read the *absolute* percentage with that in mind. The *ranking* of items
  is not affected.
  / **2021 上半年是疫情低基数**。2022 的同比有一部分是恢复，读绝对增幅要带这个前提；单品的**排名**不受影响。
- **The "bake less" list is weaker evidence than the "bake more" list.** A stock-out
  leaves a trace in the till (the item stops selling mid-afternoon). Over-baking does
  not — it ends in the bin, and the bin is not in the export. So "bake less" is an
  **acknowledged proxy**, and the page says so.
  / **"该少烤"这张表的证据强度弱于"该多烤"。** 断货在收银机里留下痕迹（下午突然不卖了）；备多了没有——它最后进了垃圾桶，而垃圾桶不在导出里。所以"该少烤"是一个**明确承认的代理指标**，页面写了这句话。

### Design decisions that were forced by the data / 被数据推翻后定下的设计

These three are the substance of the exercise. Each one started as a reasonable idea
and was **killed by a measurement**.
/ 这三条是这次作业的实质。每一条都始于一个看起来合理的设计，然后**被一次实测推翻**。

**① The revenue baseline: "last 4 same weekdays" → "same weekday one year ago"**
**EN** — The first version compared each day against the previous four same weekdays.
Across the whole period that reports a drop of more than 20 % on **27.1 %** of all
days — and on **75.0 %** of the days in September 2022, when the summer peak simply
ended (revenue goes from **1,737 €/day in August** to **779 €/day in September**).
A baseline that cries wolf every autumn is worse than no baseline. The year-over-year
baseline reports **15.9 %** overall and **7.1 %** in September 2022.
**中文** — 第一版用"前 4 个同星期"。全期实测：**27.1%** 的日子被判超过 −20%；到 2022 年 9 月夏季峰值结束时，**75.0%** 的日子被误报成营收下跌（8 月日均 **1,737 €** → 9 月 **779 €**）。每年秋天都喊狼来了的基线，比没有基线更糟。改成"去年同期同星期"后，全期 **15.9%**、9 月只有 **7.1%**。

**② The stock-out signal: one condition → two conditions**
**EN** — Flagging "last sale earlier than its own median" alone confuses *ran out*
with *nobody wanted it*. Checked over **8,785 item-days**: of the **2,405** that ended
an hour or more early, **19.5 %** had sold **less than half** their normal volume.
Example: `SPECIAL BREAD` on 2021-09-27 ended **217 minutes early** having sold **1
unit against a normal 14.5**. Adding the second condition — it must also have moved
≥80 % of its normal volume — brings the daily list to a mean of **3.56 items**
(median 3, p90 7, max 15) and **8.9 %** of days with no signal at all. A short list
that is right beats a long list that has to be argued with.
**中文** — 只看"比自己的中位时刻早收工"，会把**卖光了**和**没人要**混为一谈。实测 **8,785 个观测**：提前一小时以上收工的 **2,405** 次里，**19.5%** 当天只卖到常态量的一半以下。例如 `SPECIAL BREAD` 在 2021-09-27 提前 **217 分钟**收工，但只卖出 **1 件**（常态 14.5 件）。加上第二个条件（仍卖到常态 80% 以上）后，每天平均 **3.56 个**（中位 3、p90 7、最多 15），**8.9%** 的日子一条都不报。短而对的名单，胜过需要逐条争论的长名单。

**③ The "bake less" rule: absolute units → share of shop units**
**EN** — Comparing each item's volume against its own normal volume has exactly the
same seasonal defect as the revenue baseline. On 2022-09-26 that rule flags **15 of
the 20 items** — the page turns red and nobody reads it, because the whole shop is
down from 1,038 € to 694 €. Normalising by the item's **share of total units sold**
makes it insensitive to the shop's overall level: on the same day it flags **4**
items, all at a share ratio of **0.0** — they genuinely did not sell.
**中文** — 拿单品绝对件数跟自己的常态比，有和营收基线一模一样的季节缺陷。2022-09-26 那条规则报了 **20 个里的 15 个**——满页飘红没人看，因为整家店从 1,038 € 掉到 694 €。改成按**占全店件数的份额**归一化后，对全店水平不敏感：同一天只报 **4 个**，份额比全是 **0.0**——是真的没卖出去。

### Order of the page / 页面顺序

Top = the three numbers (nobody scrolls before reading them) → middle = the two
charts that explain *why* a number moved → bottom = the action tables and the detail
for someone who wants to dig in.
/ 顶部=三个数字（没人会先滚动再看指标）→ 中部=解释"为什么"的两张图 → 底部=可行动的明细表和给想深挖的人看的全表。

---

## Step 4 — Refresh frequency / 刷新频率

### 1. How often should the data refresh / 数据该多久刷一次

**Once a day, in the small hours**, after the till is closed and the day's receipts
are exported. This is a design fact, not a limitation: the events being counted — a
batch of dough going into the oven, a tray emptying — happen a handful of times per
day. **There is no faster clock in the process**, so collecting faster would add cost
without adding information.
/ **每天凌晨一次**，收银机日结后导出。这是设计事实，不是妥协：被记录的事件——一炉面进烤箱、一盘卖空——一天只发生几次。**这个流程里没有更快的时钟**，所以采集得更快只会增加成本，不增加信息。

### 2. How often should someone review it — and is that the same thing / 多久看一次，和刷新是一回事吗

**No, and this is the point.** Refresh is a property of the *data*; review is a
property of the *decision*. The manager reads it **once a day at 06:30**, five minutes
before the first bake. Looking twice would produce the same answer twice.
/ **不是一回事，而这正是要点。** 刷新是**数据**的属性，查看是**决策**的属性。主管**每天 06:30 看一次**，开炉前五分钟。看两遍只会得到两遍相同的答案。

### 3. What is tracked over time, and what should trigger action / 长期追踪什么，什么该触发动作

**EN — Tracked over time:** the last-sale clock of the top-20 items, and the
revenue-vs-baseline series. Those are the two things worth watching for drift.

**Triggers action (the alert, not the screen):** if any TOP-20 item's last sale lands
before **its own median** for **three consecutive occurrences of that weekday**, push
a message at **06:00** instead of waiting to be looked at.

Why three, and not one: a single early finish is exactly the ambiguity measured in
② above — sold out, or a bad day? Three in a row on the *same weekday* is no longer
ambiguous, because the comparison is already within a single weekday.

**中文 —— 长期追踪：** top-20 的"最后售出时刻"和"营收 vs 基线"两条序列，这两样才值得看漂移。
**触发动作（用告警，不用大屏）：** 任一 top-20 单品**连续 3 次同星期**的最后售出早于**它自己的中位**，就在**06:00** 推一条消息，而不是等人来看。
**为什么是 3 次不是 1 次：** 单次提前收工正是上面②量出来的那种模糊情况——卖光了，还是这天就没人？**同一个星期**连着三次，就不模糊了，因为比较本身已经限定在同一个星期内。

### 4. What stale data costs / 数据过时的代价

**EN** — The cost is measurable, because the clock is weekly:

- **One day stale** — today's bake is set from the wrong day's pattern. The Sunday
  page run on a Monday over-bakes by a factor of **2.5** (Sunday 22.6 % of annual
  revenue vs Wednesday 9.0 %); the Monday page run on a Sunday under-bakes by the same
  factor and the shop sells out by mid-morning.
- **One week stale** — every one of the **3.56 items** the page would have flagged is
  missed, and last week's error is baked again. A weekday pattern recurs **52 times a
  year**, so a week-stale dashboard converts one mistake into a recurring one.
- **One month stale** — the dashboard crosses the seasonal turn it was specifically
  built to survive. Between August and September 2022 the shop goes from **1,737 €/day
  to 779 €/day**; a month-old page would tell her to bake for a shop that no longer
  exists.

The failure mode is asymmetric and that is why freshness matters here: **over-baking
produces waste with no salvage value, under-baking produces a customer who leaves.**
Neither is recoverable tomorrow — the bread is either in the bin or was never baked.

**中文** — 代价是可以量化的，因为节拍是按星期的：

- **过时一天** — 今天的产量按错误那天的规律排。周一打开周日的页面，会**多烤 2.5 倍**（周日占全年营收 22.6%，周三 9.0%）；周日打开周一的页面，会少烤同样的倍数，上午就卖空。
- **过时一周** — 页面本该报出的那 **3.56 个**单品全部漏掉，上周的错误再烤一遍。同一个星期的规律**一年重复 52 次**，所以"过时一周"会把一次错误变成一种反复发生的错误。
- **过时一个月** — 页面会跨过它本来就是为了扛住的那个季节转折。2022 年 8 月到 9 月，这家店从**日均 1,737 €** 掉到 **779 €**；一个月前的页面，是在为一个已经不存在了的店排产。

失败是不对称的，这正是新鲜度在这里重要的原因：**烤多了变成没有残值的浪费，烤少了变成一位走掉的客人。** 两样都补不回来——面包要么已经在垃圾桶里，要么从来没被烤出来。

**On the page / 页面上的那一行:** *Période des données : janvier 2021 – septembre
2022 (instantané Kaggle, 600 jours d'ouverture). Fréquence de rafraîchissement en
production : une fois par jour, la nuit.* — Step 4 requires this line, and it is the
last caption on the page.

---

## Running it locally / 本地运行

```bash
uv init                        # already done; pyproject.toml is committed
uv sync                        # or: pip install -r requirements.txt
streamlit run app.py
```

**EN** — Python 3.11+ (developed on 3.13; deploys on Streamlit Cloud with **3.14**, as
the assignment requires — set it under *Advanced settings*).

The app itself needs only `requirements.txt`. The EDA notebook needs two extras that
the app does not: `matplotlib` and `jupyter` (`pip install matplotlib jupyter`).
Its outputs are already committed, so you can also read it without running anything.

**中文** — Python 3.11+（在 3.13 上开发；按作业要求部署到 Streamlit Cloud 时选 **3.14**，在 *Advanced settings* 里设置）。

大屏本身只依赖 `requirements.txt`。EDA notebook 额外需要 `matplotlib` 和 `jupyter`（`pip install matplotlib jupyter`），**大屏不需要它们**。notebook 的输出已经提交进去了，所以不运行也能直接读。

## Files / 文件

| File | What it is | 中文 |
|---|---|---|
| `app.py` | the Streamlit page — layout, three metrics, two charts, three tables. **The only file that speaks French.** | 大屏本体。**唯一说法语的文件。** |
| `bakery.py` | data loading, French price cleaning, and every metric in one place. Run it directly for a self-check across all seven weekdays. | 数据加载、法文价格清洗、全部指标。直接运行可跑七个星期的自检。 |
| `eda_bakery.ipynb` | the Step 3 EDA notebook — 15 code cells, 5 figures, outputs committed | Step 3 的 EDA notebook，输出已提交 |
| `data/bakery_sales.csv` | the dataset (14.0 MB) | 数据集 |
| `requirements.txt` / `pyproject.toml` | dependencies | 依赖 |
| `README.md` | this file — the graded deliverable | 本文件，评分主体 |

Self-check / 自检: `python bakery.py` prints one line per weekday (English, because
the data layer stays English) —
`Monday 2022-09-26 occ=88 rev 694EUR vs 509EUR (+36.2%, yoy) | early 1 absent 4 soft 0 ok 15`.

## What this data cannot answer / 这份数据回答不了什么

**EN** — The export contains **no stock, no production quantity, no waste, no
sell-out flag, no cost, no margin, no customer id, no discount, no payment method, no
weather, no shift, and no category**.

So this dashboard can tell you **whether you under-baked** — the item ran out while it
was still selling. It **cannot** tell you whether you over-baked: over-baking shows up
as unsold bread in the bin, and the bin is not in the export. The "bake less" list is
therefore built from the till-side proxy (sold far below its own normal share), and it
is honestly **weaker evidence** than the "bake more" list. Saying so is part of the
deliverable.

**中文** — 导出里**没有库存、没有生产量、没有报废、没有售罄标记、没有成本、没有毛利、没有客户 ID、没有折扣、没有支付方式、没有天气、没有班次、没有品类**。

所以这张页面能告诉你**有没有备少了**（东西还在卖的时候就没货了）。它**不能**告诉你有没有备多了——备多了体现为垃圾桶里没卖掉的面包，而垃圾桶不在导出里。所以"该少烤"这张表用的是收银机一侧的代理指标（份额远低于自己的常态），它诚实地**弱于**"该多烤"那张表。把这件事写出来，本身就是交付的一部分。
