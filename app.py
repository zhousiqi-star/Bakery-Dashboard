"""Tableau de bord de production — application Streamlit.

Public      : la responsable de production d'une boulangerie française, à 06h30,
              cinq minutes avant la première fournée du matin.
Ce qu'elle   : quels articles sont partis trop tôt hier (à enfourner en plus) et
fait         lesquels se sont nettement moins vendus que d'habitude (à enfourner
              en moins) — pour ajuster chaque fournée ce matin même.

Langue : français. Le jeu de données appartient à une boulangerie française
(articles en français, prix au format « 0,90 € »), donc l'écran parle la langue
du terrain, pas celle du cours.

Lancer : streamlit run app.py
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from bakery import (
    CHART_OCC,
    DATA_PATH,
    SOFT_SHARE_RATIO,
    analyze,
    load_sales,
)

TEAM_NAME = "Siqi Zhou"

# bakery.py stays English on purpose; this is the one place that translates.
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def jour(dow: int) -> str:
    """0 -> 'lundi' (French weekday name for the UI)."""
    return JOURS[dow]


# strftime %B depends on the OS locale; Windows would print "January".
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
        "août", "septembre", "octobre", "novembre", "décembre"]


def fr_month(d) -> str:
    return f"{MOIS[d.month - 1]} {d.year}"


def fr_num(x: float, dec: int = 0) -> str:
    """1234.5 -> '1 234,5' (espace fine insécable + virgule décimale, usage FR)."""
    s = f"{x:,.{dec}f}"
    return s.replace(",", "\u202f").replace(".", ",")


def fr_pct(x: float, dec: int = 0, signed: bool = False) -> str:
    sign = "+" if (signed and x >= 0) else ""
    return f"{sign}{fr_num(x, dec)} %"


def fr_articles(n: int) -> str:
    """1 -> '1 article', 4 -> '4 articles' (French plural rule)."""
    return f"{n} article" if n == 1 else f"{n} articles"


st.set_page_config(page_title="Tableau de bord production — boulangerie",
                   layout="wide")


# ---------------------------------------------------------------------------
# données
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="Lecture des 234 005 lignes de caisse…")
def get_data() -> pd.DataFrame:
    return load_sales(DATA_PATH)


df = get_data()

data_start = df["date"].min()
data_end = df["date"].max()

# ---------------------------------------------------------------------------
# en-tête
# ---------------------------------------------------------------------------
st.title("🥖 Ce matin : on enfourne quoi de plus, quoi de moins ?")
st.caption(
    f"{TEAM_NAME} · Pour la **responsable de production** de cette boulangerie : "
    "chaque matin à 06h30, cinq minutes avant la première fournée, pour décider "
    "des quantités du jour à partir des ventes d'hier."
)

# ---------------------------------------------------------------------------
# le seul filtre dont elle a besoin
# ---------------------------------------------------------------------------
dow_options = {
    "lundi": 0, "mardi": 1, "mercredi": 2, "jeudi": 3,
    "vendredi": 4, "samedi": 5, "dimanche": 6,
}
c1, c2, c3 = st.columns([1, 1, 2])
with c1:
    dow_label = st.selectbox(
        "Quel jour de la semaine ?",
        [k.capitalize() for k in dow_options],
        index=4,
        help="Les ventes varient d'un facteur 2,5 selon le jour (le dimanche pèse "
             "22,6 % du CA annuel, le mercredi 9,0 %). Chaque jour se compare donc "
             "à son propre historique, jamais à une moyenne tous jours confondus.",
    )
res = analyze(df, dow_options[dow_label.lower()])

with c2:
    st.metric(
        "Jour analysé", f"{res['day']:%d/%m}",
        help=f"{jour(res['dow']).capitalize()} — {res['n_occ']}e occurrence de ce jour "
             "de la semaine dans le jeu de données.",
    )
with c3:
    st.markdown(
        f"<div style='padding-top:1.6rem;color:#666;font-size:0.9rem'>"
        f"Ce jour-là, la caisse a enregistré <b>{fr_num(res['lines_day'])}</b> lignes "
        f"sur <b>{fr_num(res['tickets_day'])}</b> tickets"
        f"</div>",
        unsafe_allow_html=True,
    )

st.divider()

# ---------------------------------------------------------------------------
# haut : les trois chiffres de tête
# ---------------------------------------------------------------------------
basis_txt = "le même jour l'an dernier" if res["rev_basis"] == "yoy" else "les 4 mêmes jours précédents"
rev_delta = res["rev_delta"]

m1, m2, m3 = st.columns(3)
with m1:
    st.metric(
        f"CA du {jour(res['dow'])}",
        f"{fr_num(res['rev_day'])} €",
        delta=f"{fr_pct(rev_delta, 1, signed=True)} vs {basis_txt}" if pd.notna(rev_delta) else None,
        help="La comparaison se fait avec le même jour l'an dernier, pas avec la "
             "semaine dernière : la semaine dernière est encore souvent en fin de "
             "pic estival, et cette comparaison prendrait la décrue saisonnière "
             "pour une baisse d'activité.",
    )
with m2:
    st.metric(
        "À enfourner en plus",
        fr_articles(len(res["early"])),
        help="Hier, ils sont partis plus tôt que leur heure habituelle **et** ils "
             "se vendaient encore normalement → rupture, donc à produire davantage.",
    )
with m3:
    n_cut = len(set(res["absent"]["article"]) | set(res["soft"]["article"]))
    st.metric(
        "À enfourner en moins",
        fr_articles(n_cut),
        help="Hier, ils ne se sont pas vendus du tout, ou leur part des ventes du "
             f"magasin est tombée sous {fr_pct(SOFT_SHARE_RATIO * 100)} de leur part "
             "habituelle (sans être partis trop tôt) → à produire moins.",
    )

# ---------------------------------------------------------------------------
# milieu : les deux graphiques qui expliquent pourquoi
# ---------------------------------------------------------------------------
st.subheader("Pourquoi ces chiffres")

left, right = st.columns([1, 1], gap="large")

with left:
    st.markdown(f"**① CA des {CHART_OCC} derniers {jour(res['dow'])}s vs sa propre base**")
    ch = res["chart1"]
    fig = go.Figure()
    fig.add_bar(
        x=ch["date"], y=ch["revenue"], name="CA du jour",
        marker_color=["#c0392b" if r else "#95a5a6" for r in ch["is_day"]],
    )
    fig.add_scatter(
        x=ch["date"], y=ch["baseline"], name="Base",
        mode="lines+markers", line=dict(color="#2c3e50", width=2, dash="dot"),
    )
    fig.update_layout(
        height=340, margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        yaxis_title="€", xaxis_title=None,
        hovermode="x unified",
        xaxis=dict(tickformat="%d/%m"),
    )
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Les barres grises sont l'historique, la barre rouge est le jour analysé. "
        "Les trous sont des jours de fermeture, pas un CA de 0 — la boulangerie a "
        "fermé 37 jours, dont 29 mercredis (fermeture hebdomadaire de janvier à avril 2021)."
    )

with right:
    st.markdown("**② Heure de la dernière vente hier — top 20**")
    it = (res["items"].dropna(subset=["today_minute"])
          .sort_values("revenue_12w", ascending=False).head(20)
          .sort_values("base_minute"))
    fig2 = go.Figure()
    fig2.add_scatter(
        x=it["base_minute"] / 60, y=it["article"], mode="markers",
        name="Son heure habituelle (médiane)",
        marker=dict(color="#bdc3c7", size=9, symbol="line-ns-open",
                    line=dict(width=2, color="#7f8c8d")),
    )
    colors = ["#c0392b" if s == "early" else "#27ae60" if s == "on_track" else "#f39c12"
              for s in it["state"]]
    fig2.add_scatter(
        x=it["today_minute"] / 60, y=it["article"], mode="markers",
        name="Hier, en réel",
        marker=dict(color=colors, size=11),
        text=[f"{a} : base {b} → hier {t}" for a, b, t in
              zip(it["article"], it["base_hhmm"], it["today_hhmm"])],
        hoverinfo="text",
    )
    fig2.update_layout(
        height=340, margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        xaxis=dict(title="Heure de la dernière vente (h, 24 h)", range=[6, 21]),
        yaxis_title=None,
    )
    st.plotly_chart(fig2, width="stretch")
    st.caption(
        "Une même « heure de fin » ne veut pas dire la même chose pour un pain et "
        "pour une viennoiserie : la baguette se vend jusqu'à 18h42 (cuisson étalée "
        "toute la journée), la brioche s'arrête à 12h24 (une seule fournée le matin). "
        "La base est donc l'heure médiane **de chaque article**, pas une heure de "
        "référence unique."
    )

st.divider()

# ---------------------------------------------------------------------------
# bas : les deux listes d'action
# ---------------------------------------------------------------------------
n_cut_total = len(set(res["absent"]["article"]) | set(res["soft"]["article"]))
tab1, tab2, tab3 = st.tabs(
    [f"🔴 Enfourner plus ({len(res['early'])})",
     f"🟢 Enfourner moins ({n_cut_total})",
     "Top 20 complet"]
)

with tab1:
    if res["early"].empty:
        st.info("Aucun article n'est parti plus tôt que son habitude — "
                "on garde les quantités habituelles ce matin.")
    else:
        show = res["early"].copy()
        show = show.assign(
            Article=show["article"],
            Habituel=show["base_hhmm"],
            Hier=show["today_hhmm"],
            Écart=show["gap_hhmm"],
            Qté_hier=show["today_qty"].round(0).astype("Int64"),
            Qté_hab=show["base_qty"].round(0).astype("Int64"),
            CA_12s=(show["revenue_12w"] / 12).round(1).map(lambda v: f"{fr_num(v)} €/sem."),
        )
        st.dataframe(
            show[["Article", "Habituel", "Hier", "Écart", "Qté_hier", "Qté_hab", "CA_12s"]],
            hide_index=True, width="stretch",
        )
        st.caption(
            f"Règle : la dernière vente d'hier tombe au moins 30 minutes avant l'heure "
            f"médiane de ses {12} derniers {jour(res['dow'])}s, **et** les quantités "
            "vendues atteignent encore 80 % de la normale. La seconde condition écarte "
            "les articles qui se vendaient simplement mal ce jour-là — partir tôt "
            "*et* en quantité, c'est une rupture, pas un manque de clients."
        )

with tab2:
    cut_absent = res["absent"][["article", "revenue_12w", "today_hhmm"]].copy()
    cut_absent = cut_absent.rename(columns={
        "article": "Article", "revenue_12w": "CA_12s", "today_hhmm": "Dernière_vente",
    })
    cut_absent.insert(1, "Motif", "Aucune vente hier")
    cut_absent["Part_hier"] = "0 %"

    cut_soft = res["soft"][["article", "revenue_12w", "share_ratio"]].copy()
    cut_soft = cut_soft.rename(columns={
        "article": "Article", "revenue_12w": "CA_12s", "share_ratio": "Part_hier",
    })
    cut_soft.insert(1, "Motif", "Se vend, mais nettement moins que d'habitude")
    cut_soft["Dernière_vente"] = "Horaire normal"
    cut_soft["Part_hier"] = cut_soft["Part_hier"].map(
        lambda v: f"{fr_num(v * 100)} %")

    if cut_absent.empty and cut_soft.empty:
        st.info("Aucun article à réduire ce matin.")
    else:
        both = pd.concat([cut_absent, cut_soft], ignore_index=True)
        both["CA_12s"] = (both["CA_12s"].round(0).astype("Int64")
                          .map(lambda v: f"{fr_num(v)} €"))
        both = both[["Article", "Motif", "CA_12s", "Dernière_vente", "Part_hier"]]
        st.dataframe(both, hide_index=True, width="stretch")
        st.caption(
            "« Nettement moins que d'habitude » = la part de cet article dans les "
            f"unités vendues du magasin tombe sous {fr_pct(SOFT_SHARE_RATIO * 100)} de "
            f"sa propre part médiane sur les {12} derniers {jour(res['dow'])}s, **et** il "
            "n'est pas parti trop tôt (partir trop tôt = sous-production, c'est le "
            "tableau du dessus). On raisonne en part et non en quantités absolues, "
            "parce que la fréquentation varie avec la saison : en septembre, quand "
            "tout le magasin vend 30 % de moins, des quantités absolues signaleraient "
            "huit articles à tort."
        )

with tab3:
    allit = res["items"].copy()
    label = {"early": "🔴 Parti tôt", "soft": "🟠 Vendu peu",
             "on_track": "✅ Normal",
             "absent": "🟢 Aucune vente", "thin": "⚪ Données insuffisantes"}
    allit["État"] = allit["state"].map(label)
    out = allit.assign(
        Article=allit["article"],
        CA_12s=allit["revenue_12w"].round(0).astype("Int64").map(lambda v: f"{fr_num(v)} €"),
        Habituel=allit["base_hhmm"],
        Hier=allit["today_hhmm"],
        Écart=allit["gap_hhmm"],
        Obs=allit["n_obs"],
    )[["État", "Article", "CA_12s", "Habituel", "Hier", "Écart", "Obs"]]
    st.dataframe(
        out.sort_values(["État", "CA_12s"], ascending=[True, False]),
        hide_index=True, width="stretch",
    )
    st.caption(
        f"Ces 20 articles pèsent {fr_pct(res['top_share'] * 100, 1)} du CA des "
        f"{CHART_OCC} derniers {jour(res['dow'])}s. On ne suit qu'eux : les 129 autres "
        "pèsent ensemble moins d'un quart des ventes, impossible à piloter au "
        "quotidien et pas rentable à surveiller."
    )

# ---------------------------------------------------------------------------
# pied de page : période des données + fréquence de rafraîchissement (étape 4)
# ---------------------------------------------------------------------------
st.divider()
st.caption(
    f"**Période des données** : {fr_month(data_start)} – {fr_month(data_end)} "
    "(instantané Kaggle, 600 jours d'ouverture). "
    "**Fréquence de rafraîchissement en production : une fois par jour, la nuit** "
    "(export après clôture de la caisse). La responsable la consulte chaque matin à "
    "06h30 — rafraîchir et consulter n'ont pas la même fréquence, parce que le four "
    "n'est chargé qu'une fois par jour."
)

with st.expander("Ce que cette page ne montre pas — et ce qui peut tromper"):
    st.markdown(
        f"""
**Deux choses volontairement laissées de côté :**

1. **Le panier moyen.** Médiane {fr_num(3.85, 2)} €, p10–p90 entre {fr_num(3.24, 2)} €
   et {fr_num(4.79, 2)} € : il ne bouge quasiment pas. Son amplitude ne suffit à
   changer aucune fournée, et l'afficher coûterait une des trois places de la ligne
   d'indicateurs.
2. **La courbe de fréquentation heure par heure.** L'ouverture est à heure fixe et la
   décision de production est prise avant 07h00 ; la courbe du jour arrive toujours
   trop tard pour la fournée du jour. C'est un matériau de débriefing, pas une entrée
   de décision. (Si on la veut, elle appartient à un rapport d'après-fermeture, pas à
   un écran d'avant-aube.)

**Ce qui peut tromper :**

- **37 jours sans aucune ligne ne sont pas des jours à 0 € de ventes.** Ce sont des
  fermetures, et **29 sont des mercredis** (fermeture hebdomadaire de janvier à
  avril 2021). Le mercredi n'a donc que **62 observations** là où les autres jours en
  ont 88 à 91. Le graphique montre un trou ; il ne trace pas de zéro.
- **`unit_price` est du texte au format français** — `"0,90 €"` : virgule décimale,
  symbole euro, espace fine insécable. Il faut le nettoyer avant tout calcul, sinon la
  colonne reste du texte et le CA devient silencieusement faux.
- **1 295 lignes (0,55 %) ont une `Quantity` négative**, pour −2 201 unités au total :
  ce sont des retours et des corrections. Elles sont exclues du calcul de la dernière
  vente, sinon un retour tardif repousse l'heure de fin et masque une vraie rupture.
- **Un même `ticket_number` peut contenir plusieurs lignes** (43,0 % des tickets en ont
  au moins 2) : le nombre de lignes n'est donc pas le nombre de clients.
  234 005 lignes = 136 451 tickets.
- **`COUPE` ({fr_num(3526)} €) est un service de tranchage, pas un produit**, et les
  6 entrées `DIVERS *` ({fr_num(10749)} € = 1,92 %) sont des fourre-tout qu'aucun
  mapping de catégories ne peut séparer. C'est pourquoi cette page ne comporte
  **aucun graphique par catégorie** : l'unité de décision de la responsable est
  l'article, et remonter aux catégories détruirait précisément la granularité sur
  laquelle elle peut agir.
- **Le premier semestre 2021 est une base déprimée par la pandémie.** La croissance
  2022 est en partie un rattrapage : le pourcentage absolu doit être lu avec cette
  réserve ; le classement des articles, lui, n'est pas affecté.
- **Le dimanche vaut 2,5 fois le mercredi** (22,6 % contre 9,0 % du CA annuel) : les
  deux ne sont jamais comparables.
- **La liste « en moins » est une preuve plus faible que celle « en plus ».** La
  rupture se voit dans la caisse (l'article s'arrête de se vendre en pleine journée) ;
  la surproduction, non — elle finit à la poubelle, et la poubelle n'est pas dans
  l'export. C'est pourquoi on la mesure par un proxy assumé : la part des ventes.
"""
    )
