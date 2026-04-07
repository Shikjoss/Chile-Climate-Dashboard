"""
╔══════════════════════════════════════════════════════════════════════╗
║   CHILE CLIMATE INTELLIGENCE DASHBOARD                               ║
║   TISS BS Analytics & Sustainability Studies 2024-28                 ║
║   Student: Shikhar Srivastava | M2024BSASS026                       ║
║   Country: Chile                                                     ║
╚══════════════════════════════════════════════════════════════════════╝
"""

# ── Imports ──────────────────────────────────────────────────────────
import os, json, io, textwrap, datetime, re
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

import dash
from dash import dcc, html, Input, Output, State, callback, dash_table
import dash_bootstrap_components as dbc

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from io import BytesIO

# ── Raw data paths (deployment-safe: data next to this file) ─────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "data")

REQUIRED_EXCEL_FILES = (
    "Chile Dataset (CCSD).xlsx",
    "Annual CO2 Emissions.xlsx",
    "CO2 Emission per-capita Dataset.xlsx",
    "Cumulative CO2 Emissions.xlsx",
    "Shared Annual CO2 emissions.xlsx",
    "Co2 emissions per unit energy.xlsx",
)


def rp(name):
    return os.path.join(RAW_DIR, name)


def ensure_excel_data_files():
    """Fail fast on startup if any required workbook is missing."""
    missing = [fn for fn in REQUIRED_EXCEL_FILES if not os.path.isfile(rp(fn))]
    if missing:
        raise FileNotFoundError(
            "Missing required Excel file(s) in {!r}: {}".format(
                RAW_DIR, ", ".join(missing)
            )
        )


ensure_excel_data_files()

# ── Load all datasets ─────────────────────────────────────────────────
def load_chile():
    df = pd.read_excel(rp("Chile Dataset (CCSD).xlsx"))
    df = df.dropna(axis=1, how="all")
    df.columns = df.columns.str.strip()
    rename = {
        "Country":"country","Code":"code","Year":"year",
        "Population, Total":"population",
        "GDP per capita (current US$)":"gdp_pc",
        "GDP per capita growth (annual %)":"gdp_pc_growth",
        "GDP (current US$)":"gdp",
        "CO2 emissions per Capita (in tonnes)":"co2_pc",
        "Annual CO2 Emissions (in tonnes)":"annual_co2",
        "Share of global annual CO2 emissions (in tonnes)":"share_global",
        "Cumulative CO2 emissions (in tonnes)":"cumulative_co2",
        "Share of global cumulative CO2 emissions (in tonnes)":"share_global_cumul",
        "Territorial emissions (in tonnes)":"territorial",
        "Consumption-based emissions (in tonnes)":"consumption",
        "Flaring (in tonnes)":"flaring",
        "Cement (in tonnes)":"cement",
        "Gas (in tonnes)":"gas",
        "Oil (in tonnes)":"oil",
        "Coal (in tonnes)":"coal",
        "Annual CO2 emissions per unit energy (kg per kilowatt-hour)":"co2_energy",
        "Human Development Index (HDI)":"hdi",
    }
    df = df.rename(columns=rename)
    df = df[(df["year"]>=1999)&(df["year"]<=2024)].copy()
    df["year"] = df["year"].astype(int)
    return df

def load_global(fname, metric_col, new_col):
    df = pd.read_excel(rp(fname))
    df = df.rename(columns={"Entity":"country","Code":"code","Year":"year",metric_col:new_col})
    df = df[["country","code","year",new_col]]
    df = df[(df["year"]>=1999)&(df["year"]<=2024)].copy()
    df["year"] = df["year"].astype(int)
    df[new_col] = pd.to_numeric(df[new_col], errors="coerce")
    return df

chile     = load_chile()
g_annual  = load_global("Annual CO2 Emissions.xlsx",           "Annual CO2 emissions",                                          "annual_co2")
g_percap  = load_global("CO2 Emission per-capita Dataset.xlsx","CO2 Emissions per capita (t)",                                  "co2_pc")
g_cumul   = load_global("Cumulative CO2 Emissions.xlsx",       "Cumulative CO2 emissions",                                      "cumulative_co2")
g_shared  = load_global("Shared Annual CO2 emissions.xlsx",    "Share of global annual CO2 emissions",                          "share_global")
g_energy  = load_global("Co2 emissions per unit energy.xlsx",  "Annual CO2 emissions per unit energy (kg per kilowatt-hour)",   "co2_energy")

# Merge global wide
world = g_annual.merge(g_percap,  on=["country","code","year"], how="outer")\
                .merge(g_cumul,   on=["country","code","year"], how="outer")\
                .merge(g_shared,  on=["country","code","year"], how="outer")\
                .merge(g_energy,  on=["country","code","year"], how="outer")

ALL_COUNTRIES = sorted(world["country"].dropna().unique().tolist())
COMPARATORS   = ["Chile","India","World","United States","China","Brazil","Germany","Norway","South Africa","France","Japan","Argentina"]

# Deploy-safe: use actual min/max years in the workbook (avoid IndexError if 2024/1999 rows are absent)
_CHILE_YR_MIN = int(chile["year"].min())
_CHILE_YR_MAX = int(chile["year"].max())
CHILE_LATEST_ROW = chile.loc[chile["year"] == _CHILE_YR_MAX].iloc[0]
CHILE_EARLIEST_ROW = chile.loc[chile["year"] == _CHILE_YR_MIN].iloc[0]

# ── Chile flag SVG (inline) ───────────────────────────────────────────
CHILE_FLAG_B64 = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA5MDAgNjAwIj4KICA8cmVjdCB3aWR0aD0iOTAwIiBoZWlnaHQ9IjYwMCIgZmlsbD0iI0Q1MkIxRSIvPgogIDxyZWN0IHdpZHRoPSI5MDAiIGhlaWdodD0iMzAwIiBmaWxsPSJ3aGl0ZSIvPgogIDxyZWN0IHdpZHRoPSIzMDAiIGhlaWdodD0iNjAwIiBmaWxsPSIjMDAzOUE2Ii8+CiAgPHBvbHlnb24gcG9pbnRzPSIxNTAsMTIwIDE4NywyNDAgMTA3LDE2NSAxOTMsMTY1IDExMywyNDAiIGZpbGw9IndoaXRlIi8+Cjwvc3ZnPg=="

# ══════════════════════════════════════════════════════════════════════
#  COLOUR PALETTE  (Sophisticated Earth Pastel Theme)
# ══════════════════════════════════════════════════════════════════════
C = dict(
    red       = "#D4A574",
    blue      = "#7B9E89",
    white     = "#FFFFFF",
    cream     = "#FAF6F3",
    gold      = "#C9899E",
    dark      = "#FAF6F3",
    dark2     = "#F4EFE9",
    card      = "#FFFFFF",
    card2     = "#F8F4F0",
    glass     = "rgba(123,158,137,0.08)",
    glass2    = "rgba(123,158,137,0.12)",
    red_t     = "rgba(212,165,116,0.15)",
    blue_t    = "rgba(123,158,137,0.15)",
    gold_t    = "rgba(201,137,158,0.15)",
    text      = "#2C3E50",
    muted     = "#6B7280",
    accent    = "#E8C4A0",
    accent2   = "#D4B5E0",
    gridline  = "rgba(123,158,137,0.08)",
)

PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(255,255,255,0.9)",
    plot_bgcolor ="rgba(255,255,255,0.9)",
    font         = dict(family="Playfair Display, Georgia, serif", color=C["text"], size=12),
    title_font   = dict(family="Cinzel, Georgia, serif", size=16, color=C["text"]),
    legend       = dict(bgcolor="rgba(255,255,255,0.8)", bordercolor=C["glass2"], borderwidth=1,
                        font=dict(size=11)),
    xaxis        = dict(gridcolor=C["gridline"], zerolinecolor=C["gridline"],
                        tickfont=dict(size=10), title_font=dict(size=11)),
    yaxis        = dict(gridcolor=C["gridline"], zerolinecolor=C["gridline"],
                        tickfont=dict(size=10), title_font=dict(size=11)),
    margin       = dict(l=50, r=20, t=60, b=50),
    hovermode    = "x unified",
)

def fig_layout(fig, title=""):
    fig.update_layout(**PLOT_LAYOUT)
    if title:
        fig.update_layout(title=dict(text=title, x=0.03, xanchor="left"))
    return fig

# ══════════════════════════════════════════════════════════════════════
#  HELPER: styled cards / components
# ══════════════════════════════════════════════════════════════════════
def kpi_card(icon, label, value, sub="", color=C["red"]):
    return html.Div([
        html.Div(icon, style={"fontSize":"32px","marginBottom":"8px","opacity":"0.95"}),
        html.Div(value, style={"fontSize":"24px","fontWeight":"900",
                               "fontFamily":"Cinzel, serif","color":color,"letterSpacing":"0.5px"}),
        html.Div(label, style={"fontSize":"12px","color":"#2C3E50","textTransform":"uppercase",
                               "letterSpacing":"1.5px","marginTop":"6px","fontWeight":"700"}),
        html.Div(sub,   style={"fontSize":"11px","color":"#6B7280","marginTop":"4px","fontStyle":"italic"}) if sub else None,
    ], style={
        "background":f"linear-gradient(135deg, {C['card']}, {C['card2']})","borderRadius":"16px","padding":"22px 18px",
        "borderTop":f"4px solid {color}","borderLeft":f"1px solid {C['glass2']}","textAlign":"center",
        "boxShadow":"0 8px 32px rgba(123,158,137,0.15)","transition":"all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)",
        "cursor":"default","border":f"1px solid {C['glass2']}",
    }, className="kpi-hover dashboard-panel")

def section_title(text, sub=""):
    return html.Div([
        html.Div(style={"width":"5px","height":"40px","background":f"linear-gradient(180deg,{C['blue']},{C['red']},{C['gold']})",
                        "borderRadius":"3px","marginRight":"14px","flexShrink":"0",
                        "boxShadow":f"0 0 12px {C['blue_t']}"}, className="pulse-accent"),
        html.Div([
            html.Div(text, style={"fontSize":"24px","fontWeight":"900",
                                   "fontFamily":"Cinzel, serif",
                                   "background":f"linear-gradient(135deg,{C['blue']},{C['red']},{C['gold']})",
                                   "WebkitBackgroundClip":"text","WebkitTextFillColor":"transparent",
                                   "backgroundClip":"text","letterSpacing":"0.5px"}),
            html.Div(sub,  style={"fontSize":"13px","color":"#6B7280","marginTop":"6px","fontStyle":"italic",
                                  "fontWeight":"500"}) if sub else None,
        ])
    ], style={"display":"flex","alignItems":"center","marginBottom":"24px","marginTop":"36px"},
       className="section-title-row")

def graph_card(graph_id, title="", height=380, footer=""):
    return html.Div([
        html.Div(title, style={"fontSize":"14px","fontWeight":"800","color":"#1a1a1a",
                               "textTransform":"uppercase","letterSpacing":"2px",
                               "marginBottom":"16px","fontFamily":"Cinzel,serif",
                               "borderBottom":f"3px solid {C['blue']}","paddingBottom":"10px"}) if title else None,
        dcc.Graph(id=graph_id, style={"height":f"{height}px"},
                  config={"displayModeBar":True,"modeBarButtonsToRemove":["lasso2d","select2d"],
                          "displaylogo":False}),
        html.Div(footer, style={"fontSize":"10px","color":"#6B7280","marginTop":"10px",
                                "textAlign":"right","fontStyle":"italic","fontWeight":"500"}) if footer else None,
    ], style={"background":f"linear-gradient(135deg,{C['card']},{C['card2']})","borderRadius":"16px","padding":"24px",
              "boxShadow":"0 8px 32px rgba(123,158,137,0.15)","marginBottom":"24px",
              "border":f"1px solid {C['glass2']}","transition":"all 0.3s ease"},
              className="graph-card dashboard-panel")

# ══════════════════════════════════════════════════════════════════════
#  SPLASH / CURTAIN PAGE
# ══════════════════════════════════════════════════════════════════════
splash = html.Div(id="splash-screen", children=[
    # Dynamic landing effects
    html.Div(className="climate-bg-overlay"),
    html.Div([
        html.Div(className="fan-blade blade-1"),
        html.Div(className="fan-blade blade-2"),
        html.Div(className="fan-blade blade-3"),
    ], className="wind-fan"),
    html.Div(className="orbit-ring orbit-1"),
    html.Div(className="orbit-ring orbit-2"),
    html.Div(className="orbit-ring orbit-3"),
    html.Div(className="floating-orb orb-1"),
    html.Div(className="floating-orb orb-2"),
    html.Div(className="floating-orb orb-3"),
    html.Div(className="floating-orb orb-4"),
    html.Div(className="rangoli-bg"),
    html.Div(className="rangoli-ring r1"),
    html.Div(className="rangoli-ring r2"),
    html.Div(className="rangoli-ring r3"),
    html.Div(className="rangoli-petals"),
    # Floating particles
    *[html.Div(className=f"particle p{i}") for i in range(1,13)],
    html.Div(className="rangoli-orbit ro1"),
    html.Div(className="rangoli-orbit ro2"),
    html.Div(className="mandala-float mf1"),
    html.Div(className="mandala-float mf2"),
    html.Div(className="mandala-float mf3"),
    html.Div(className="splash-sparkle sp1"),
    html.Div(className="splash-sparkle sp2"),
    html.Div(className="splash-sparkle sp3"),
    html.Div(className="splash-sparkle sp4"),
    html.Div(className="splash-sparkle sp5"),
    html.Div(className="splash-aurora"),
    html.Div(className="splash-light-sweep"),
    html.Div(className="splash-sunrays"),
    html.Div(className="splash-lotus-ring ll1"),
    html.Div(className="splash-lotus-ring ll2"),
    html.Div(className="splash-lotus-ring ll3"),
    *[html.Div(className=f"splash-bokeh bk{i}") for i in range(1, 6)],
    *[html.Div(className=f"splash-diamond dm{i}") for i in range(1, 7)],
    *[html.Div(className=f"splash-pulse-dot pd{i}") for i in range(1, 5)],
    *[html.Div(className=f"splash-corner-glow cg{i}") for i in range(1, 5)],
    *[html.Div(className=f"splash-drift-ring dr{i}") for i in range(1, 4)],
    *[html.Div(className=f"splash-mote m{i}") for i in range(1, 9)],
    # Central content
    html.Div([
        # Flag + title
        html.Div([
            html.Img(src=CHILE_FLAG_B64, style={"width":"54px","height":"36px","borderRadius":"4px","boxShadow":"0 2px 8px rgba(0,0,0,0.35)","marginBottom":"16px","display":"block","margin":"0 auto 16px"}),
            html.H1("CHILE", style={
                "fontFamily":"Cinzel Decorative, Cinzel, Georgia, serif",
                "fontSize":"clamp(42px,7vw,88px)","fontWeight":"900",
                "background":f"linear-gradient(135deg,{C['white']},{C['gold']},{C['red']})",
                "WebkitBackgroundClip":"text","WebkitTextFillColor":"transparent",
                "letterSpacing":"0.25em","margin":"0","lineHeight":"1",
            }),
            html.Div("CLIMATE INTELLIGENCE DASHBOARD",style={
                "fontFamily":"Cinzel, Georgia, serif",
                "fontSize":"clamp(9px,1.4vw,15px)","letterSpacing":"0.35em",
                "color":C["muted"],"marginTop":"6px","textAlign":"center",
            }),
            html.Hr(style={"borderColor":C["red"],"width":"60%","margin":"18px auto"}),
            html.Div("Prepared by: Shikhar Srivastava | M2024BSASS026 | TISS Mumbai",
                     style={"fontSize":"10px","color":C["muted"],"marginTop":"14px","textAlign":"center"}),
        ], style={"textAlign":"center","display":"flex","flexDirection":"column","alignItems":"center"}),
        # CTA button
        html.Button([
            html.Span("✦ EXPLORE DASHBOARD ✦"),
        ], id="enter-btn", style={
            "background":f"linear-gradient(135deg,{C['red']},{C['blue']})",
            "border":"none","borderRadius":"50px","color":"white",
            "fontFamily":"Cinzel, serif","fontSize":"14px","letterSpacing":"3px",
            "padding":"16px 48px","cursor":"pointer","marginTop":"32px",
            "boxShadow":f"0 0 40px {C['red_t']}, 0 0 80px {C['blue_t']}",
            "fontWeight":"600","textTransform":"uppercase",
            "transition":"all .3s","display":"block","margin":"32px auto 0",
        }),
    ], style={
        "position":"relative","zIndex":"10","maxWidth":"640px","width":"90%",
    }),
], style={
    "position":"fixed","top":"0","left":"0","width":"100vw","height":"100vh",
    "backgroundImage":"linear-gradient(135deg, rgba(10,16,24,0.72), rgba(14,20,30,0.82)), url('/assets/landing_climate_bg.jpg')",
    "backgroundSize":"cover",
    "backgroundPosition":"center",
    "display":"flex","flexDirection":"column","alignItems":"center","justifyContent":"center",
    "zIndex":"9999","overflow":"hidden","transition":"opacity .8s, transform .8s",
})

# ══════════════════════════════════════════════════════════════════════
#  NAVIGATION BAR
# ══════════════════════════════════════════════════════════════════════
TABS_CONFIG = [
    ("Home",  "Overview",         "tab-overview"),
    ("Trends",  "Trends",           "tab-trends"),
    ("Inequality",  "Inequality",       "tab-inequality"),
    ("Source",  "Source Analysis",  "tab-source"),
    ("Compare",  "World Compare",    "tab-compare"),
    ("Explorer",  "Data Explorer",    "tab-explorer"),
    ("Projections",  "Projections",      "tab-projections"),
    ("Justice", "Climate Justice",  "tab-justice"),
    ("Report",  "Report Generator", "tab-report"),
    ("Methodology",  "Methodology",      "tab-methodology"),
    ("About",  "About",            "tab-about"),
]

navbar = html.Div([
    # Logo strip
    html.Div([
        html.Div([
            html.Img(src=CHILE_FLAG_B64, style={"width":"36px","height":"24px","borderRadius":"3px"}),
            html.Div([
                html.Span("CHILE ", style={"color":C["red"],"fontWeight":"900"}),
                html.Span("CLIMATE", style={"color":C["text"]}),
            ], style={"fontFamily":"Cinzel, serif","fontSize":"15px","letterSpacing":"2px",
                      "marginLeft":"10px"}),
        ], style={"display":"flex","alignItems":"center"}),
        html.Div("M2024BSASS026 | TISS Mumbai | 2024-28",
                 style={"fontSize":"9px","color":C["muted"],"letterSpacing":"1.5px"}),
    ], style={
        "padding":"10px 24px","borderBottom":f"1px solid {C['glass2']}",
        "display":"flex","justifyContent":"space-between","alignItems":"center",
        "background":f"linear-gradient(90deg,{C['dark2']},{C['card']})",
    }),
    # Tab strip
    html.Div([
        html.Div([
            html.Button([
                html.Span(icon, style={"fontSize":"14px","display":"block"}),
                html.Span(label, style={"fontSize":"9px","letterSpacing":"0.8px",
                                        "marginTop":"2px","display":"block"}),
            ], id=f"nav-{tab_id}", className="nav-tab",
               **{"data-tab": tab_id},
               style={
                "background":"transparent","border":"none","color":C["muted"],
                "padding":"10px 14px","cursor":"pointer","borderRadius":"8px",
                "fontFamily":"Cinzel, serif","textTransform":"uppercase",
                "transition":"all .2s","whiteSpace":"nowrap",
               })
            for icon, label, tab_id in TABS_CONFIG
        ], style={"display":"flex","gap":"4px","flexWrap":"wrap",
                  "justifyContent":"center","padding":"8px 16px"}),
    ], style={"background":C["dark2"],"borderBottom":f"2px solid {C['red']}"}),
], style={
    "position":"sticky","top":"0","zIndex":"1000",
    "boxShadow":"0 4px 32px rgba(0,0,0,0.6)",
})

# ══════════════════════════════════════════════════════════════════════
#  TAB CONTENT BUILDERS
# ══════════════════════════════════════════════════════════════════════

# ── TAB 0: OVERVIEW ──────────────────────────────────────────────────
def build_overview():
    latest = CHILE_LATEST_ROW
    earliest = CHILE_EARLIEST_ROW
    co2_change = ((latest["annual_co2"]/earliest["annual_co2"])-1)*100
    gdp_change = ((latest["gdp_pc"]/earliest["gdp_pc"])-1)*100
    y0, y1 = _CHILE_YR_MIN, _CHILE_YR_MAX

    kpis = html.Div([
        kpi_card("🌋", f"Annual CO₂ ({y1})", f"{latest['annual_co2']/1e6:.1f} Mt",
                 f"+{co2_change:.0f}% since {y0}", C["red"]),
        kpi_card("👤", f"Per Capita CO₂ ({y1})", f"{latest['co2_pc']:.2f} t",
                 "vs 4.58t global avg", C["blue"]),
        kpi_card("🌍","Global CO₂ Share", f"{latest['share_global']:.3f}%",
                 "Low emitter — top 50th percentile", C["gold"]),
        kpi_card("💰","GDP per Capita", f"${latest['gdp_pc']:,.0f}",
                 f"+{gdp_change:.0f}% since {y0}", C["red"]),
        kpi_card("📈", f"HDI ({y1})", f"{latest['hdi']:.3f}",
                 "Very High Human Development", C["blue"]),
        kpi_card("👥", f"Population ({y1})", f"{latest['population']/1e6:.1f}M",
                 "19.8M people", C["gold"]),
    ], style={"display":"grid","gridTemplateColumns":"repeat(auto-fit,minmax(165px,1fr))",
              "gap":"16px","marginBottom":"28px"})

    # Country profile text
    profile = html.Div([
        section_title("🇨🇱 Country Profile", "Chile — Land of contrasts at the end of the world"),
        html.Div([
            html.Div([
                html.P("""Chile, officially the Republic of Chile, is a long narrow country occupying a strip of land 
                between the Andes Mountains and the Pacific Ocean in South America. Stretching over 4,300 km from 
                north to south, it encompasses an extraordinary range of climates — from the world's driest desert 
                (Atacama) in the north to sub-Antarctic glaciers in the south.""",
                style={"color":C["text"],"lineHeight":"1.8","fontFamily":"Georgia, serif","fontSize":"14px"}),
                html.P("""Chile is one of Latin America's most economically stable and prosperous nations, with a 
                GDP per capita of $16,710 in 2024. Its economy is heavily reliant on copper mining (Chile holds 
                ~27% of global copper reserves), along with growing sectors in renewable energy, agriculture, 
                and tourism. The country has made significant strides in reducing poverty and improving human 
                development, achieving an HDI of 0.878 in 2024.""",
                style={"color":C["text"],"lineHeight":"1.8","fontFamily":"Georgia, serif","fontSize":"14px","marginTop":"12px"}),
                html.Div([
                    html.Div([
                        html.Span("Capital: ",style={"color":C["muted"],"fontWeight":"600"}),
                        html.Span("Santiago",style={"color":C["text"]}),
                    ], style={"marginBottom":"6px"}),
                    html.Div([
                        html.Span("Area: ",style={"color":C["muted"],"fontWeight":"600"}),
                        html.Span("756,102 km²",style={"color":C["text"]}),
                    ], style={"marginBottom":"6px"}),
                    html.Div([
                        html.Span("Currency: ",style={"color":C["muted"],"fontWeight":"600"}),
                        html.Span("Chilean Peso (CLP)",style={"color":C["text"]}),
                    ], style={"marginBottom":"6px"}),
                    html.Div([
                        html.Span("Major Industries: ",style={"color":C["muted"],"fontWeight":"600"}),
                        html.Span("Copper mining, agriculture, wine, tourism, renewable energy",style={"color":C["text"]}),
                    ]),
                ], style={"background":C["card2"],"borderRadius":"10px","padding":"14px 18px",
                          "marginTop":"14px","fontSize":"13px","fontFamily":"Georgia, serif"}),
            ], style={"flex":"1","minWidth":"280px"}),
            html.Div([
                html.Div("🗺️", style={"fontSize":"80px","textAlign":"center","marginBottom":"8px"}),
                html.Div("Quick Facts", style={"fontFamily":"Cinzel, serif","fontSize":"13px",
                                               "color":C["muted"],"textAlign":"center","letterSpacing":"2px",
                                               "marginBottom":"12px"}),
                *[html.Div([
                    html.Span(icon+" ", style={"fontSize":"16px"}),
                    html.Span(fact, style={"color":C["text"],"fontSize":"12px","fontFamily":"Georgia, serif"}),
                ], style={"marginBottom":"10px","display":"flex","alignItems":"flex-start"})
                for icon, fact in [
                    ("🌊","Only country in the world bordering 3 oceans"),
                    ("🌡️","Home to the driest desert on Earth — the Atacama"),
                    ("⚡","~55% of electricity from renewables (2024)"),
                    ("🍷","5th largest wine exporter globally"),
                    ("🔭","Hosts world's largest optical telescopes (ESO)"),
                    ("🐧","Part of Antarctica accessed via Punta Arenas"),
                    ("🏔️","Andes runs its entire eastern border — 4,300 km"),
                ]],
            ], style={"background":C["card2"],"borderRadius":"14px","padding":"20px",
                      "minWidth":"240px","flex":"0 0 auto"}),
        ], style={"display":"flex","gap":"20px","flexWrap":"wrap"}),
    ], style={"background":C["card"],"borderRadius":"14px","padding":"24px",
              "boxShadow":"0 4px 24px rgba(0,0,0,0.35)","marginBottom":"20px"},
              className="dashboard-panel")

    # Data sources table
    sources = html.Div([
        section_title("📚 Data Sources & Variables",
                      "All datasets used in this dashboard — fully cited per APA 7th ed."),
        dash_table.DataTable(
            data=[
                {"Variable":"Annual CO₂ Emissions (tonnes)","Source":"Global Carbon Project / Our World in Data",
                 "URL":"ourworldindata.org/co2-emissions","Years":"1999–2024","Coverage":"247 countries"},
                {"Variable":"CO₂ Per Capita (tonnes/person)","Source":"Our World in Data",
                 "URL":"ourworldindata.org/co2-emissions","Years":"1999–2024","Coverage":"231 countries"},
                {"Variable":"Share of Global CO₂ (%)","Source":"Global Carbon Project",
                 "URL":"globalcarbonproject.org","Years":"1999–2024","Coverage":"235 countries"},
                {"Variable":"Cumulative CO₂ (tonnes)","Source":"Global Carbon Project",
                 "URL":"ourworldindata.org","Years":"1999–2024","Coverage":"235 countries"},
                {"Variable":"CO₂ per Unit Energy (kg/kWh)","Source":"Our World in Data / IEA",
                 "URL":"ourworldindata.org","Years":"1999–2024","Coverage":"222 countries"},
                {"Variable":"GDP per Capita (current US$)","Source":"World Bank WDI",
                 "URL":"data.worldbank.org","Years":"1999–2024","Coverage":"Chile"},
                {"Variable":"Population","Source":"World Bank WDI",
                 "URL":"data.worldbank.org","Years":"1999–2024","Coverage":"Chile"},
                {"Variable":"Human Development Index","Source":"UNDP",
                 "URL":"hdr.undp.org","Years":"1999–2024","Coverage":"Chile"},
                {"Variable":"Emission by Sector (Coal/Oil/Gas/Cement/Flaring)",
                 "Source":"Global Carbon Project","URL":"globalcarbonproject.org",
                 "Years":"1999–2024","Coverage":"Chile"},
            ],
            columns=[{"name":c,"id":c} for c in ["Variable","Source","Years","Coverage"]],
            style_table={"overflowX":"auto","borderRadius":"10px","overflow":"hidden"},
            style_header={"backgroundColor":"#D4A574","color":"white","fontWeight":"700",
                          "fontFamily":"Cinzel, serif","fontSize":"12px","letterSpacing":"2px",
                          "border":None,"textTransform":"uppercase","padding":"12px 14px"},
            style_cell={"backgroundColor":"white","color":"#1a1a1a","fontWeight":"500",
                        "fontFamily":"Georgia, serif","fontSize":"12px",
                        "border":f"1px solid {C['glass2']}","padding":"11px 14px",
                        "whiteSpace":"normal","textAlign":"left"},
            style_data_conditional=[
                {"if":{"row_index":"odd"},"backgroundColor":"#F9F7F5"},
                {"if":{"column_id":"Variable"},"color":"#1a1a1a","fontWeight":"700",
                 "backgroundColor":"#FFF9F5"},
            ],
        ),
        html.Div("Sources: Our World in Data (2024); Global Carbon Project (2024); World Bank Open Data (2024); UNDP HDR (2024)",
                 style={"fontSize":"10px","color":"#6B7280","marginTop":"12px","fontStyle":"italic",
                       "fontWeight":"500"}),
    ], style={"background":C["card"],"borderRadius":"14px","padding":"24px",
              "boxShadow":"0 4px 24px rgba(0,0,0,0.35)"},
              className="dashboard-panel")

    # Summary gauge chart
    gauge = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=float(latest["co2_pc"]),
        delta={"reference":4.58, "valueformat":".2f",
               "increasing":{"color":C["red"]},"decreasing":{"color":"#4CAF50"}},
        title={"text":"Chile CO₂ Per Capita vs World Avg (4.58t)","font":{"color":C["muted"],"size":12}},
        number={"suffix":" t","font":{"color":"#1a1a1a","size":28,"family":"Cinzel, serif"}},
        gauge={
            "axis":{"range":[0,20],"tickcolor":C["muted"],"tickfont":{"size":9}},
            "bar":{"color":C["red"],"thickness":0.25},
            "bgcolor":"rgba(0,0,0,0)",
            "steps":[
                {"range":[0,2],"color":"rgba(76,175,80,0.2)"},
                {"range":[2,5],"color":"rgba(245,200,66,0.2)"},
                {"range":[5,10],"color":"rgba(255,152,0,0.2)"},
                {"range":[10,20],"color":"rgba(213,43,30,0.2)"},
            ],
            "threshold":{"line":{"color":C["gold"],"width":2},"thickness":0.75,"value":4.58},
        }
    ))
    pl = {k:v for k,v in PLOT_LAYOUT.items() if k != 'margin'}
    gauge.update_layout(**pl, height=280, margin=dict(l=30,r=30,t=50,b=20))

    return html.Div([kpis, profile, sources,
                     html.Div([
                         html.Div(dcc.Graph(figure=gauge, config={"displayModeBar":False}),
                                  style={"background":C["card"],"borderRadius":"14px",
                                         "padding":"16px","boxShadow":"0 4px 24px rgba(0,0,0,0.35)",
                                         "marginTop":"20px"}),
                     ], className="dashboard-panel")])

# ── TAB 1: TRENDS ─────────────────────────────────────────────────────
def build_trends():
    c = chile.copy()

    # Total CO2 line chart
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=c["year"], y=c["annual_co2"]/1e6,
        mode="lines+markers",
        line=dict(color=C["red"], width=3),
        marker=dict(size=7, color=C["gold"], line=dict(color=C["red"],width=2)),
        fill="tozeroy", fillcolor=C["red_t"],
        name="Annual CO₂ (Mt)",
        hovertemplate="<b>%{x}</b><br>%{y:.2f} Mt<extra></extra>",
    ))
    # Add policy milestones
    milestones = {
        2010:"Chile's National Climate Change Action Plan",
        2015:"Paris Agreement signed",
        2019:"Chile NDC — 30% emissions reduction target",
        2021:"Carbon Neutrality 2050 pledged",
    }
    for yr, label in milestones.items():
        if yr in c["year"].values:
            val = float(c[c["year"]==yr]["annual_co2"].values[0])/1e6
            fig1.add_vline(x=yr, line=dict(color=C["blue"],dash="dot",width=1.5))
            fig1.add_annotation(x=yr, y=val*1.08, text=f"📌 {yr}", showarrow=False,
                                font=dict(size=9,color=C["gold"]), bgcolor="rgba(0,0,0,0.6)",
                                bordercolor=C["blue"], borderwidth=1, borderpad=3)
    fig1_layout = {**PLOT_LAYOUT,
                   "title":"Total Annual CO₂ Emissions — Chile (1999–2024)",
                   "yaxis_title":"Million Tonnes CO₂",
                   "xaxis_title":"Year"}
    fig1.update_layout(**fig1_layout)

    # Per capita
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=c["year"], y=c["co2_pc"],
        mode="lines+markers",
        line=dict(color=C["blue"], width=3),
        marker=dict(size=7, color=C["gold"], line=dict(color=C["blue"],width=2)),
        fill="tozeroy", fillcolor=C["blue_t"],
        name="CO₂ per Capita (t)",
        hovertemplate="<b>%{x}</b><br>%{y:.3f} t/person<extra></extra>",
    ))
    fig2.add_hline(y=4.58, line=dict(color=C["gold"],dash="dash",width=1.5),
                   annotation_text="🌍 World Avg (4.58t)", annotation_position="top right",
                   annotation_font=dict(color=C["gold"],size=10))
    fig2.add_hline(y=1.9, line=dict(color="#4CAF50",dash="dash",width=1.5),
                   annotation_text="🇮🇳 India Avg (1.9t)", annotation_position="bottom right",
                   annotation_font=dict(color="#4CAF50",size=10))
    fig2.update_layout(**{**PLOT_LAYOUT,
                          "title":"CO₂ Per Capita Emissions — Chile (1999–2024)",
                          "yaxis_title":"Tonnes CO₂ per Person",
                          "xaxis_title":"Year"})

    # GDP vs CO2 dual axis
    fig3 = make_subplots(specs=[[{"secondary_y":True}]])
    fig3.add_trace(go.Bar(x=c["year"], y=c["annual_co2"]/1e6, name="Annual CO₂ (Mt)",
                          marker_color=C["red_t"], marker_line=dict(color=C["red"],width=1.5),
                          hovertemplate="CO₂: %{y:.2f} Mt<extra></extra>"), secondary_y=False)
    fig3.add_trace(go.Scatter(x=c["year"], y=c["gdp_pc"], name="GDP per Capita (US$)",
                              line=dict(color=C["gold"],width=3),
                              marker=dict(size=6,color=C["gold"]),
                              hovertemplate="GDP: $%{y:,.0f}<extra></extra>"), secondary_y=True)
    fig3.update_layout(**{**PLOT_LAYOUT,"title":"CO₂ Emissions vs. Economic Growth (GDP per Capita)"})
    fig3.update_yaxes(title_text="Million Tonnes CO₂", secondary_y=False,
                      gridcolor=C["gridline"], tickfont=dict(size=9))
    fig3.update_yaxes(title_text="GDP per Capita (US$)", secondary_y=True,
                      gridcolor="rgba(0,0,0,0)", tickfont=dict(size=9))

    # HDI vs CO2
    fig4 = px.scatter(c, x="hdi", y="co2_pc", size="population", color="year",
                      color_continuous_scale=[[0,C["blue"]],[0.5,C["red"]],[1,C["gold"]]],
                      hover_data={"year":True,"gdp_pc":":,.0f","annual_co2":":,.0f"},
                      labels={"hdi":"HDI","co2_pc":"CO₂ per Capita (t)","year":"Year"},
                      title="HDI vs CO₂ Per Capita — Chile Trajectory (bubble = population)")
    fig4.update_traces(marker=dict(line=dict(color="white",width=1),opacity=0.85))
    fig4.update_layout(**PLOT_LAYOUT)

    # CO2 growth rate
    c["co2_growth"] = c["annual_co2"].pct_change()*100
    fig5 = go.Figure()
    colors_gr = [C["red"] if v>0 else "#4CAF50" for v in c["co2_growth"].fillna(0)]
    fig5.add_trace(go.Bar(x=c["year"], y=c["co2_growth"],
                          marker_color=colors_gr, name="YoY Growth %",
                          hovertemplate="<b>%{x}</b><br>%{y:.2f}%<extra></extra>"))
    fig5.add_hline(y=0, line=dict(color=C["white"],width=1))
    fig5.update_layout(**{**PLOT_LAYOUT,"title":"Year-on-Year CO₂ Emission Growth Rate (%)",
                          "yaxis_title":"Growth Rate (%)","xaxis_title":"Year"})

    # Interpretation box
    interp = html.Div([
        html.Div("📊 Trend Interpretation", style={"fontFamily":"Cinzel,serif","fontSize":"14px",
                                                    "color":C["gold"],"marginBottom":"12px",
                                                    "borderBottom":f"1px solid {C['glass2']}",
                                                    "paddingBottom":"8px"}),
        html.P("""Chile's total CO₂ emissions grew from 61.4 Mt in 1999 to 78.7 Mt in 2024 — a 28% increase 
        over 25 years. However, this growth has been uneven: rapid expansion during the 2000s economic boom 
        (GDP grew 100%+ from 1999 to 2014), a plateau and slight decline during 2014–2016 following mining 
        sector contractions, and renewed growth thereafter driven by urbanisation and energy demand.""",
        style={"color":C["text"],"fontFamily":"Georgia,serif","fontSize":"13px","lineHeight":"1.8"}),
        html.P("""Crucially, per-capita emissions have remained relatively stable at 3.4–4.8 t/person — 
        consistently below the world average of 4.58 t. This decoupling between GDP growth and per-capita 
        emissions reflects Chile's early investment in hydropower and, more recently, solar and wind energy 
        in the Atacama region — one of the world's most solar-irradiated zones. Chile's CO₂-intensity 
        per unit of energy (kg/kWh) has steadily declined, signalling energy-mix improvements.""",
        style={"color":C["text"],"fontFamily":"Georgia,serif","fontSize":"13px","lineHeight":"1.8","marginTop":"10px"}),
        html.Div([
            html.Span("Key Driver: ", style={"color":C["gold"],"fontWeight":"700"}),
            html.Span("Economic growth (+gdp) without proportional CO₂ rise = partial decoupling achieved.",
                      style={"color":C["text"],"fontSize":"13px","fontFamily":"Georgia,serif"}),
        ], style={"background":C["red_t"],"borderRadius":"8px","padding":"10px 14px",
                  "borderLeft":f"3px solid {C['red']}","marginTop":"12px"}),
    ], style={"background":C["card"],"borderRadius":"14px","padding":"24px",
              "boxShadow":"0 4px 24px rgba(0,0,0,0.35)","marginTop":"20px"},
              className="dashboard-panel")

    return html.Div([
        section_title("📈 Emissions Trend Analysis","1999–2024 | Source: Global Carbon Project, Our World in Data"),
        html.Div([
            html.Label("Year Range", style={"color":C["muted"],"fontSize":"11px","letterSpacing":"1.5px","textTransform":"uppercase"}),
            dcc.RangeSlider(
                id="trends-year-range", min=1999, max=2024, step=1, value=[1999, 2024],
                marks={y:{"label":str(y),"style":{"color":C["muted"],"fontSize":"9px"}} for y in [1999,2005,2010,2015,2020,2024]},
                tooltip={"placement":"bottom"}
            ),
        ], style={"background":C["card"],"borderRadius":"14px","padding":"18px","marginBottom":"20px","boxShadow":"0 4px 24px rgba(0,0,0,0.18)"},
           className="dashboard-panel"),
        html.Div([
            html.Div(graph_card("fig-total-co2","",400,"Source: Global Carbon Project (2024), Our World in Data"),
                     style={"flex":"1","minWidth":"300px"}),
            html.Div(graph_card("fig-percap-co2","",400,"Source: Our World in Data (2024)"),
                     style={"flex":"1","minWidth":"300px"}),
        ], style={"display":"flex","gap":"20px","flexWrap":"wrap"}),
        html.Div([
            html.Div(graph_card("fig-gdp-co2","",380,"Source: World Bank WDI (2024); Global Carbon Project (2024)"),
                     style={"flex":"1","minWidth":"300px"}),
            html.Div(graph_card("fig-hdi-co2","",380,"Source: UNDP (2024); Our World in Data (2024)"),
                     style={"flex":"1","minWidth":"300px"}),
        ], style={"display":"flex","gap":"20px","flexWrap":"wrap"}),
        graph_card("fig-growth-rate","",340,"Source: Global Carbon Project (2024)"),
        interp,
    ], id="trends-content"), fig1, fig2, fig3, fig4, fig5

# ── TAB 2: INEQUALITY ────────────────────────────────────────────────
def build_inequality():
    comps = world[world["country"].isin(COMPARATORS)].copy()
    # Latest year per country
    latest_c = comps.sort_values("year").groupby("country").last().reset_index()

    # Per capita bar
    fig1 = go.Figure()
    lc_sorted = latest_c.sort_values("co2_pc", ascending=True)
    bar_colors = [C["red"] if c=="Chile" else
                  "#4CAF50" if c=="India" else
                  C["blue_t"] if c=="World" else
                  C["glass2"] for c in lc_sorted["country"]]
    fig1.add_trace(go.Bar(
        x=lc_sorted["co2_pc"], y=lc_sorted["country"],
        orientation="h",
        marker=dict(color=[C["red"] if c=="Chile" else "#4CAF50" if c=="India"
                           else C["blue"] if c=="World" else "#334466"
                           for c in lc_sorted["country"]],
                    line=dict(color="rgba(255,255,255,0.1)",width=0.5)),
        text=[f"{v:.2f}t" for v in lc_sorted["co2_pc"]],
        textposition="outside", textfont=dict(size=10,color=C["text"]),
        hovertemplate="<b>%{y}</b><br>%{x:.3f} t/person<extra></extra>",
    ))
    fig1.add_vline(x=4.58, line=dict(color=C["gold"],dash="dash",width=1.5),
                   annotation_text="World Avg", annotation_font=dict(color=C["gold"],size=9))
    fig1.update_layout(**{**PLOT_LAYOUT,"title":"CO₂ Per Capita — Country Comparison (2024)",
                          "xaxis_title":"Tonnes CO₂ per Person","margin":dict(l=120,r=40,t=60,b=40)})

    # Share of global emissions over time — area chart
    fig2 = go.Figure()
    share_countries = ["Chile","India","China","United States","Germany","Brazil"]
    colors_share = [C["red"],C["gold"],C["blue"],"#FF6B6B","#4CAF50","#FF9800"]
    for co, col in zip(share_countries, colors_share):
        sub = world[(world["country"]==co)&(world["year"]>=1999)&(world["year"]<=2024)]
        fig2.add_trace(go.Scatter(
            x=sub["year"], y=sub["share_global"],
            name=co, mode="lines",
            line=dict(color=col, width=2.5 if co=="Chile" else 1.5),
            fill="tozeroy" if co=="Chile" else None,
            fillcolor=C["red_t"] if co=="Chile" else None,
        ))
    fig2.update_layout(**{**PLOT_LAYOUT,"title":"Share of Global Annual CO₂ Emissions (1999–2024)",
                          "yaxis_title":"Share of Global Emissions (%)","xaxis_title":"Year"})

    # Cumulative emissions comparison
    cumul_latest = world[world["year"]==2023].dropna(subset=["cumulative_co2"])
    top_cumul = cumul_latest.nlargest(10, "cumulative_co2")
    # Add Chile if not in top 10
    if "Chile" not in top_cumul["country"].values:
        chile_cumul = cumul_latest[cumul_latest["country"]=="Chile"]
        top_cumul = pd.concat([top_cumul, chile_cumul])
    fig3 = go.Figure(go.Bar(
        x=top_cumul["country"],
        y=top_cumul["cumulative_co2"]/1e9,
        marker=dict(color=[C["red"] if c=="Chile" else C["blue_t"] for c in top_cumul["country"]],
                    line=dict(color=[C["red"] if c=="Chile" else C["blue"] for c in top_cumul["country"]],
                              width=1.5)),
        text=[f"{v:.1f}Gt" for v in top_cumul["cumulative_co2"]/1e9],
        textposition="outside", textfont=dict(size=9),
        hovertemplate="<b>%{x}</b><br>%{y:.2f} Gt cumulative<extra></extra>",
    ))
    fig3.update_layout(**{**PLOT_LAYOUT,"title":"Cumulative CO₂ Emissions — Top Countries vs Chile (through 2023)",
                          "yaxis_title":"Cumulative Emissions (Gigatonnes)","xaxis_title":""})

    # Chile vs India vs World over time
    fig4 = go.Figure()
    for co, col, lw in [("Chile",C["red"],3),("India","#4CAF50",2),("World",C["gold"],2)]:
        sub = world[(world["country"]==co)&(world["year"]>=1999)&(world["year"]<=2024)]
        fig4.add_trace(go.Scatter(x=sub["year"], y=sub["co2_pc"], name=co,
                                  line=dict(color=col,width=lw),
                                  mode="lines+markers",
                                  marker=dict(size=5 if lw==2 else 7),
                                  hovertemplate=f"<b>{co}</b> %{{x}}: %{{y:.2f}} t<extra></extra>"))
    fig4.update_layout(**{**PLOT_LAYOUT,
                          "title":"Per Capita CO₂: Chile vs India vs World Average (1999–2024)",
                          "yaxis_title":"Tonnes CO₂ per Person"})

    # Climate justice radar
    categories = ["Per Capita\nEmissions","HDI","Renewable\nEnergy %",
                  "Cumulative\nResponsibility","Economic\nCapacity","Emission\nIntensity"]
    chile_vals  = [0.35, 0.88, 0.55, 0.08, 0.60, 0.30]   # normalised 0-1
    india_vals  = [0.10, 0.55, 0.20, 0.15, 0.25, 0.45]
    usa_vals    = [0.90, 0.95, 0.20, 1.00, 1.00, 0.70]
    world_vals  = [0.35, 0.72, 0.30, 0.50, 0.50, 0.50]
    radar_fills = {
        "Chile":    "rgba(213,43,30,0.18)",
        "India":    "rgba(76,175,80,0.18)",
        "USA":      "rgba(0,57,166,0.18)",
        "World Avg":"rgba(245,200,66,0.18)",
    }
    fig5 = go.Figure()
    for name, vals, col in [("Chile",chile_vals,C["red"]),("India",india_vals,"#4CAF50"),
                             ("USA",usa_vals,C["blue"]),("World Avg",world_vals,C["gold"])]:
        fig5.add_trace(go.Scatterpolar(r=vals+[vals[0]], theta=categories+[categories[0]],
                                       fill="toself", name=name,
                                       fillcolor=radar_fills[name],
                                       line=dict(color=col,width=2)))
    fig5.update_layout(**{**PLOT_LAYOUT,
                          "title":"Climate Responsibility Radar — Normalised Indicators",
                          "polar":dict(
                              bgcolor=C["card2"],
                              radialaxis=dict(visible=True,range=[0,1],
                                             gridcolor=C["glass2"],tickfont=dict(size=8)),
                              angularaxis=dict(gridcolor=C["glass2"],tickfont=dict(size=10,color=C["text"]))),
                          "showlegend":True})

    interp = html.Div([
        html.Div("⚖️ Carbon Inequality Analysis", style={"fontFamily":"Cinzel,serif","fontSize":"14px",
                                                          "color":C["gold"],"marginBottom":"12px",
                                                          "borderBottom":f"1px solid {C['glass2']}",
                                                          "paddingBottom":"8px"}),
        html.Div([
            html.Div([
                html.Div("LOW EMITTER", style={"fontFamily":"Cinzel,serif","fontSize":"20px",
                                                "color":C["gold"],"fontWeight":"900"}),
                html.Div("Chile's classification", style={"color":C["muted"],"fontSize":"11px",
                                                          "letterSpacing":"1.5px"}),
                html.Div("""Chile contributes only 0.20% of global CO₂ despite being the 42nd largest 
                economy. Its per-capita emissions (3.98t) sit below the world average (4.58t) and far 
                below the US (14.9t) or Australia. Compared to India's 1.9t, Chile emits more — 
                reflecting its higher economic development and greater per-capita energy consumption.""",
                style={"color":C["text"],"fontFamily":"Georgia,serif","fontSize":"13px",
                       "lineHeight":"1.8","marginTop":"12px"}),
            ], style={"background":C["card2"],"borderRadius":"10px","padding":"18px","flex":"1"}),
            html.Div([
                html.Div("HISTORICAL CONTEXT", style={"fontFamily":"Cinzel,serif","fontSize":"14px",
                                                       "color":C["blue"],"fontWeight":"700"}),
                html.Div("Cumulative responsibility analysis",style={"color":C["muted"],"fontSize":"11px",
                                                                      "letterSpacing":"1.5px"}),
                html.Div("""Chile's cumulative CO₂ since 1750 is approximately 2.5 Gt — just 0.15% of 
                the global total of ~1,650 Gt. The US (420 Gt, 25%), EU, and China bear far greater 
                historical responsibility. This matters for climate justice arguments: Chile is being 
                asked to adapt to a crisis it barely caused. Chile's LULUCF (land use) can make it 
                a net absorber in some years — a rarity among developing nations.""",
                style={"color":C["text"],"fontFamily":"Georgia,serif","fontSize":"13px",
                       "lineHeight":"1.8","marginTop":"12px"}),
            ], style={"background":C["card2"],"borderRadius":"10px","padding":"18px","flex":"1"}),
        ], style={"display":"flex","gap":"16px","flexWrap":"wrap"}),
    ], style={"background":C["card"],"borderRadius":"14px","padding":"24px",
              "boxShadow":"0 4px 24px rgba(0,0,0,0.35)","marginTop":"20px"})

    return html.Div([
        section_title("🌍 Carbon Inequality Analysis",
                      "Per capita, share, cumulative — a multi-dimensional lens"),
        html.Div([
            html.Label("Year Range", style={"color":C["muted"],"fontSize":"11px","letterSpacing":"1.5px","textTransform":"uppercase"}),
            dcc.RangeSlider(
                id="inequality-year-range", min=1999, max=2024, step=1, value=[1999, 2024],
                marks={y:{"label":str(y),"style":{"color":C["muted"],"fontSize":"9px"}} for y in [1999,2005,2010,2015,2020,2024]},
                tooltip={"placement":"bottom"}
            ),
        ], style={"background":C["card"],"borderRadius":"14px","padding":"18px","marginBottom":"20px","boxShadow":"0 4px 24px rgba(0,0,0,0.18)"},
           className="dashboard-panel"),
        html.Div([
            html.Div(graph_card("fig-percap-bar","",400,"Source: Our World in Data (2024)"),
                     style={"flex":"1","minWidth":"300px"}),
            html.Div(graph_card("fig-chile-india","",400,"Source: Our World in Data (2024)"),
                     style={"flex":"1","minWidth":"300px"}),
        ], style={"display":"flex","gap":"20px","flexWrap":"wrap"}),
        html.Div([
            html.Div(graph_card("fig-share-time","",380,"Source: Global Carbon Project (2024)"),
                     style={"flex":"1","minWidth":"300px"}),
            html.Div(graph_card("fig-cumul-bar","",380,"Source: Global Carbon Project (2024)"),
                     style={"flex":"1","minWidth":"300px"}),
        ], style={"display":"flex","gap":"20px","flexWrap":"wrap"}),
        graph_card("fig-radar","",420,"Note: Values normalised 0–1 for comparability | Sources: Multiple (see Methodology)"),
        interp,
    ]), fig1, fig2, fig3, fig4, fig5

# ── TAB 3: SOURCE ANALYSIS ───────────────────────────────────────────
def build_source():
    c = chile.copy()
    # Sector breakdown
    sectors = ["coal","oil","gas","cement","flaring"]
    sector_labels = ["Coal","Oil","Gas","Cement","Flaring"]
    sector_colors      = [C["dark2"],C["red"],C["gold"],"#9E9E9E",C["blue"]]
    sector_fillcolors  = ["rgba(17,24,39,0.6)","rgba(213,43,30,0.6)",
                          "rgba(245,200,66,0.6)","rgba(158,158,158,0.6)","rgba(0,57,166,0.6)"]

    fig1 = go.Figure()
    for sec, lbl, col, fcol in zip(sectors, sector_labels, sector_colors, sector_fillcolors):
        if sec in c.columns:
            fig1.add_trace(go.Scatter(x=c["year"], y=c[sec],
                                      name=lbl, stackgroup="one",
                                      fillcolor=fcol, line=dict(color=col,width=0.5),
                                      mode="lines",
                                      hovertemplate=f"<b>{lbl}</b> %{{x}}: %{{y:.2f}} t<extra></extra>"))
    fig1.update_layout(**{**PLOT_LAYOUT,
                          "title":"CO₂ Emissions by Sector — Chile (1999–2024, % of total)",
                          "yaxis_title":"CO₂ Contribution (%)"})

    # Pie for latest year
    latest = c[c["year"]==c["year"].max()].iloc[0]
    vals_pie = [latest.get(s,0) for s in sectors]
    fig2 = go.Figure(go.Pie(
        labels=sector_labels, values=vals_pie,
        hole=0.55,
        marker=dict(colors=sector_colors,
                    line=dict(color=C["dark"],width=2)),
        textfont=dict(family="Cinzel, serif",size=11,color="white"),
        hovertemplate="<b>%{label}</b><br>%{value:.2f}%<br>%{percent}<extra></extra>",
        textinfo="label+percent",
    ))
    fig2.add_annotation(text=f"<b>{int(latest['year'])}</b><br>Sector Mix",
                        x=0.5, y=0.5, font=dict(size=13,color=C["white"],family="Cinzel,serif"),
                        showarrow=False)
    fig2.update_layout(**{**PLOT_LAYOUT,"title":"Emission Source Mix — Latest Year",
                          "showlegend":True})

    # Territorial vs Consumption
    fig3 = go.Figure()
    if "territorial" in c.columns and "consumption" in c.columns:
        fig3.add_trace(go.Scatter(x=c["year"], y=c["territorial"]/1e6, name="Territorial",
                                  line=dict(color=C["red"],width=3), mode="lines+markers",
                                  marker=dict(size=5)))
        fig3.add_trace(go.Scatter(x=c["year"], y=c["consumption"]/1e6, name="Consumption-based",
                                  line=dict(color=C["blue"],width=3,dash="dash"), mode="lines+markers",
                                  marker=dict(size=5)))
        fig3.add_trace(go.Scatter(
            x=list(c["year"])+list(c["year"])[::-1],
            y=list(c["territorial"]/1e6)+list(c["consumption"]/1e6)[::-1],
            fill="toself", fillcolor="rgba(255,255,255,0.04)",
            line=dict(color="rgba(0,0,0,0)"), showlegend=False, hoverinfo="skip"))
    fig3.update_layout(**{**PLOT_LAYOUT,
                          "title":"Territorial vs. Consumption-based Emissions — Chile",
                          "yaxis_title":"Million Tonnes CO₂"})

    # Energy intensity trend
    fig4 = go.Figure()
    if "co2_energy" in c.columns:
        fig4.add_trace(go.Scatter(x=c["year"], y=c["co2_energy"], name="Chile",
                                  line=dict(color=C["red"],width=3), mode="lines+markers",
                                  marker=dict(size=7,color=C["gold"])))
    # Add global for comparison
    w_energy = g_energy[g_energy["country"]=="World"].sort_values("year")
    w_energy = w_energy[(w_energy["year"]>=1999)&(w_energy["year"]<=2024)]
    fig4.add_trace(go.Scatter(x=w_energy["year"], y=w_energy["co2_energy"],
                              name="World", line=dict(color=C["gold"],dash="dash",width=2)))
    fig4.update_layout(**{**PLOT_LAYOUT,
                          "title":"CO₂ per Unit Energy (kg/kWh) — Chile vs World",
                          "yaxis_title":"kg CO₂ per kWh"})

    return html.Div([
        section_title("🔬 Emission Source Analysis",
                      "Sectoral decomposition — Coal, Oil, Gas, Cement, Flaring"),
        html.Div([
            html.Label("Year Range", style={"color":C["muted"],"fontSize":"11px","letterSpacing":"1.5px","textTransform":"uppercase"}),
            dcc.RangeSlider(
                id="source-year-range", min=1999, max=2024, step=1, value=[1999, 2024],
                marks={y:{"label":str(y),"style":{"color":C["muted"],"fontSize":"9px"}} for y in [1999,2005,2010,2015,2020,2024]},
                tooltip={"placement":"bottom"}
            ),
        ], style={"background":C["card"],"borderRadius":"14px","padding":"18px","marginBottom":"20px","boxShadow":"0 4px 24px rgba(0,0,0,0.18)"},
           className="dashboard-panel"),
        html.Div([
            html.Div(graph_card("fig-sector-area","",400,"Source: Global Carbon Project (2024)"),
                     style={"flex":"1.5","minWidth":"300px"}),
            html.Div(graph_card("fig-sector-pie","",400,"Source: Global Carbon Project (2024)"),
                     style={"flex":"1","minWidth":"260px"}),
        ], style={"display":"flex","gap":"20px","flexWrap":"wrap"}),
        html.Div([
            html.Div(graph_card("fig-terr-cons","",380,"Source: Global Carbon Project (2024)"),
                     style={"flex":"1","minWidth":"300px"}),
            html.Div(graph_card("fig-energy-int","",380,"Source: Our World in Data / IEA (2024)"),
                     style={"flex":"1","minWidth":"300px"}),
        ], style={"display":"flex","gap":"20px","flexWrap":"wrap"}),
    ]), fig1, fig2, fig3, fig4

# ── TAB 4: WORLD COMPARE ─────────────────────────────────────────────
def build_compare():
    return html.Div([
        section_title("🌐 Country-wise Comparison",
                      "Select countries and metrics to compare against Chile"),
        html.Div([
            html.Div([
                html.Label("Select Countries", style={"color":C["muted"],"fontSize":"11px",
                                                      "letterSpacing":"1.5px","textTransform":"uppercase"}),
                dcc.Dropdown(id="compare-countries",
                             options=[{"label":c,"value":c} for c in ALL_COUNTRIES],
                             value=COMPARATORS[:8], multi=True,
                             style={"fontFamily":"Georgia,serif","fontSize":"13px"},
                             className="dark-dropdown"),
            ], style={"flex":"2","minWidth":"280px"}),
            html.Div([
                html.Label("Metric", style={"color":C["muted"],"fontSize":"11px",
                                            "letterSpacing":"1.5px","textTransform":"uppercase"}),
                dcc.Dropdown(id="compare-metric",
                             options=[
                                 {"label":"CO₂ Per Capita (t)","value":"co2_pc"},
                                 {"label":"Annual CO₂ (Mt)","value":"annual_co2"},
                                 {"label":"Share of Global (%)","value":"share_global"},
                                 {"label":"Cumulative CO₂ (Gt)","value":"cumulative_co2"},
                                 {"label":"CO₂ per Unit Energy","value":"co2_energy"},
                             ],
                             value="co2_pc",
                             style={"fontFamily":"Georgia,serif","fontSize":"13px"},
                             className="dark-dropdown"),
            ], style={"flex":"1","minWidth":"180px"}),
            html.Div([
                html.Label("Year Range", style={"color":C["muted"],"fontSize":"11px",
                                               "letterSpacing":"1.5px","textTransform":"uppercase"}),
                dcc.RangeSlider(id="compare-years", min=1999, max=2024, step=1,
                                value=[2005,2024],
                                marks={y:{"label":str(y),"style":{"color":C["muted"],"fontSize":"9px"}}
                                       for y in [1999,2005,2010,2015,2020,2024]},
                                tooltip={"placement":"bottom"}),
            ], style={"flex":"2","minWidth":"280px"}),
        ], style={"display":"flex","gap":"20px","flexWrap":"wrap","marginBottom":"20px",
                  "background":C["card"],"borderRadius":"14px","padding":"20px",
                  "boxShadow":"0 4px 24px rgba(0,0,0,0.35)"}),
        html.Div([
            html.Div(graph_card("fig-compare-line","",400,"Source: Our World in Data (2024); Global Carbon Project (2024)"),
                     style={"flex":"1","minWidth":"300px"}),
            html.Div(graph_card("fig-compare-bar","",400,"Source: Our World in Data (2024)"),
                     style={"flex":"1","minWidth":"300px"}),
        ], style={"display":"flex","gap":"20px","flexWrap":"wrap"}),
        graph_card("fig-gdp-scatter","",460,
                   "Scatter: GDP per capita (x) vs CO₂ per capita (y) — bubble = population. Source: World Bank, Our World in Data"),
        graph_card("fig-compare-heatmap","",360,"Source: Our World in Data (2024)"),
    ])

# ── TAB 5: DATA EXPLORER ─────────────────────────────────────────────
def build_explorer():
    return html.Div([
        # Chile background image as decorative element
        html.Div([
            html.Img(
                src="/assets/landing_climate_bg.jpg",
                style={
                    "position":"absolute",
                    "width":"100%",
                    "height":"100%",
                    "objectFit":"cover",
                    "opacity":"0.08",
                    "top":"0",
                    "left":"0",
                    "zIndex":"0",
                    "pointerEvents":"none"
                }
            ),
            # Overlay for better readability
            html.Div(
                style={
                    "position":"absolute",
                    "inset":"0",
                    "background":"linear-gradient(135deg, rgba(250,246,243,0.95), rgba(248,244,240,0.92))",
                    "zIndex":"1",
                    "pointerEvents":"none"
                }
            ),
        ], style={"position":"absolute","inset":"0","overflow":"hidden"}),
        
        # Background decoration with rangoli effect + extra dynamics
        html.Div([
            html.Div(className="rangoli-bg", style={"opacity":"0.3"}),
            html.Div(className="rangoli-ring r1", style={"opacity":"0.04"}),
            html.Div(className="rangoli-ring r2", style={"opacity":"0.04"}),
            html.Div(className="rangoli-ring r4", style={"opacity":"0.05"}),
            html.Div(className="rangoli-ring r5", style={"opacity":"0.035"}),
            html.Div(className="rangoli-petals", style={"opacity":"0.05"}),
            html.Div(className="rangoli-orbit ro1", style={"opacity":"0.07"}),
            html.Div(className="rangoli-orbit ro2", style={"opacity":"0.06"}),
            html.Div(className="mandala-float mf1", style={"opacity":"0.08"}),
            html.Div(className="mandala-float mf2", style={"opacity":"0.07"}),
            html.Div(className="mandala-float mf3", style={"opacity":"0.06"}),
            html.Div(className="splash-sparkle sp1", style={"opacity":"0.55"}),
            html.Div(className="splash-sparkle sp2", style={"opacity":"0.5"}),
            html.Div(className="splash-sparkle sp3", style={"opacity":"0.55"}),
            html.Div(className="orbit-ring orbit-1", style={"opacity":"0.06"}),
            html.Div(className="orbit-ring orbit-2", style={"opacity":"0.05"}),
            *[html.Div(className=f"particle p{i}", style={"animationDelay":f"{i*0.3}s"}) for i in range(1,9)],
        ], style={"position":"absolute","inset":"0","zIndex":"0","pointerEvents":"none"}),
        
        html.Div([
            section_title("🔍 Data Explorer",
                          "Filter, sort, and download the full climate dataset"),
            
            # Dynamic stats strip
            html.Div([
                html.Div([
                    html.Div("📊", style={"fontSize":"24px","marginBottom":"8px"}),
                    html.Div("Metrics Available", style={"fontSize":"11px","color":C["muted"],"letterSpacing":"1px",
                                                         "fontWeight":"600","textTransform":"uppercase"}),
                    html.Div("5", style={"fontSize":"20px","fontWeight":"900","color":C["red"],
                                        "marginTop":"4px"}),
                ], style={"background":f"linear-gradient(135deg,{C['card']},{C['card2']})","borderRadius":"12px",
                          "padding":"16px","border":f"1px solid {C['glass2']}","textAlign":"center",
                          "transition":"all 0.3s ease"}, className="kpi-hover dashboard-panel"),
                html.Div([
                    html.Div("🌍", style={"fontSize":"24px","marginBottom":"8px"}),
                    html.Div("Countries", style={"fontSize":"11px","color":C["muted"],"letterSpacing":"1px",
                                                "fontWeight":"600","textTransform":"uppercase"}),
                    html.Div(f"{len(ALL_COUNTRIES)}", style={"fontSize":"20px","fontWeight":"900","color":C["blue"],
                                                    "marginTop":"4px"}),
                ], style={"background":f"linear-gradient(135deg,{C['card']},{C['card2']})","borderRadius":"12px",
                          "padding":"16px","border":f"1px solid {C['glass2']}","textAlign":"center",
                          "transition":"all 0.3s ease"}, className="kpi-hover dashboard-panel"),
                html.Div([
                    html.Div("📈", style={"fontSize":"24px","marginBottom":"8px"}),
                    html.Div("Data Points", style={"fontSize":"11px","color":C["muted"],"letterSpacing":"1px",
                                                  "fontWeight":"600","textTransform":"uppercase"}),
                    html.Div("26", style={"fontSize":"20px","fontWeight":"900","color":C["gold"],
                                        "marginTop":"4px"}),
                ], style={"background":f"linear-gradient(135deg,{C['card']},{C['card2']})","borderRadius":"12px",
                          "padding":"16px","border":f"1px solid {C['glass2']}","textAlign":"center",
                          "transition":"all 0.3s ease"}, className="kpi-hover dashboard-panel"),
                html.Div([
                    html.Div("⚡", style={"fontSize":"24px","marginBottom":"8px"}),
                    html.Div("Live Updates", style={"fontSize":"11px","color":C["muted"],"letterSpacing":"1px",
                                                   "fontWeight":"600","textTransform":"uppercase"}),
                    html.Div("Real-time", style={"fontSize":"14px","fontWeight":"700","color":"#4CAF50",
                                                "marginTop":"4px"}),
                ], style={"background":f"linear-gradient(135deg,{C['card']},{C['card2']})","borderRadius":"12px",
                          "padding":"16px","border":f"1px solid {C['glass2']}","textAlign":"center",
                          "transition":"all 0.3s ease"}, className="kpi-hover dashboard-panel"),
            ], style={"display":"grid","gridTemplateColumns":"repeat(auto-fit,minmax(130px,1fr))",
                      "gap":"14px","marginBottom":"28px","padding":"0 4px"}),
            
            # Filter controls with enhanced styling
            html.Div([
                html.Div([
                    html.Label("Select Countries", style={"color":C["text"],"fontSize":"12px","letterSpacing":"2px",
                                                          "fontWeight":"700","textTransform":"uppercase",
                                                          "marginBottom":"8px","display":"block",
                                                          "fontFamily":"Cinzel,serif"}),
                    dcc.Dropdown(id="exp-country",
                                 options=[{"label":c,"value":c} for c in ALL_COUNTRIES],
                                 value=["Chile"], multi=True,
                                 className="dark-dropdown",
                                 style={"width":"100%"}),
                ], style={"flex":"2"}),
                html.Div([
                    html.Label("Choose Metric", style={"color":C["text"],"fontSize":"12px","letterSpacing":"2px",
                                                      "fontWeight":"700","textTransform":"uppercase",
                                                      "marginBottom":"8px","display":"block",
                                                      "fontFamily":"Cinzel,serif"}),
                    dcc.Dropdown(id="exp-metric",
                                 options=[{"label":"CO₂ Per Capita","value":"co2_pc"},
                                          {"label":"Annual CO₂","value":"annual_co2"},
                                          {"label":"Share of Global","value":"share_global"},
                                          {"label":"Cumulative CO₂","value":"cumulative_co2"},
                                          {"label":"CO₂ per Energy","value":"co2_energy"}],
                                 value="co2_pc", className="dark-dropdown",
                                 style={"width":"100%"}),
                ], style={"flex":"1"}),
                html.Button("⬇ Download CSV", id="download-btn",
                            style={"background":f"linear-gradient(135deg,{C['blue']},{C['red']})","border":"none","borderRadius":"12px",
                                   "color":"white","fontFamily":"Cinzel,serif","fontSize":"12px","fontWeight":"700",
                                   "letterSpacing":"1.5px","padding":"14px 28px","cursor":"pointer",
                                   "alignSelf":"flex-end","transition":"all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)",
                                   "boxShadow":"0 6px 20px rgba(123,158,137,0.2)","textTransform":"uppercase"}),
                dcc.Download(id="download-data"),
            ], style={"display":"flex","gap":"18px","flexWrap":"wrap","marginBottom":"28px",
                      "background":f"linear-gradient(135deg,{C['card']},{C['card2']})","borderRadius":"16px","padding":"24px",
                      "alignItems":"flex-end","border":f"1px solid {C['glass2']}","boxShadow":"0 6px 20px rgba(123,158,137,0.12)",
                      "transition":"all 0.3s ease"},
               className="explorer-filter-bar"),
            
            # Main visualization
            graph_card("fig-explorer","📊 Emissions Trend Analysis",420,"Visualize selected countries and metrics | Interactive chart"),
            
            # Data table with enhanced styling
            html.Div(id="exp-table-div", className="explorer-table-wrap",
                     style={"background":f"linear-gradient(135deg,{C['card']},{C['card2']})","borderRadius":"16px",
                            "padding":"24px","boxShadow":"0 6px 24px rgba(123,158,137,0.12)",
                            "border":f"1px solid {C['glass2']}",
                            "transition":"all 0.3s ease","overflow":"hidden"}),
            
            # Footer info
            html.Div([
                html.Div("💡 Tip: Use filters above to customize your view, hover over data points for detailed information",
                        style={"fontSize":"12px","color":C["muted"],"fontStyle":"italic",
                               "padding":"12px 16px","background":f"linear-gradient(135deg,{C['blue_t']},{C['glass']})","borderRadius":"10px",
                               "borderLeft":f"3px solid {C['blue']}","marginTop":"20px"}),
            ], style={"padding":"0 4px"}),
        ], style={"position":"relative","zIndex":"2","width":"100%","overflow":"visible"}),
    ], className="explorer-page", style={"position":"relative","width":"100%","minHeight":"calc(100vh - 200px)","overflow":"visible"})

# ── TAB 6: PROJECTIONS ───────────────────────────────────────────────
def build_projections():
    c = chile.copy().sort_values("year")
    years_hist = c["year"].values
    co2_hist   = c["annual_co2"].values/1e6

    # Simple polynomial projection
    z = np.polyfit(years_hist, co2_hist, 2)
    p = np.poly1d(z)
    years_proj = np.arange(2025, 2051)
    co2_proj   = p(years_proj)
    # BAU vs NDC scenario
    ndc_reduction = 0.30  # 30% reduction by 2030 from peak
    peak = co2_hist.max()
    co2_ndc = np.where(years_proj<=2030,
                       co2_proj - (co2_proj-peak*(1-ndc_reduction))*(years_proj-2024)/6,
                       peak*(1-ndc_reduction) * np.exp(-0.02*(years_proj-2030)))
    co2_net_zero = np.linspace(co2_hist[-1], 0, len(years_proj)) * np.exp(-0.03*(years_proj-2025))

    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=years_hist, y=co2_hist, name="Historical",
                              line=dict(color=C["red"],width=3), mode="lines+markers",
                              marker=dict(size=5)))
    fig1.add_trace(go.Scatter(x=years_proj, y=co2_proj, name="BAU Scenario",
                              line=dict(color="#FF6B6B",width=2,dash="dot")))
    fig1.add_trace(go.Scatter(x=years_proj, y=co2_ndc, name="NDC Scenario (−30% by 2030)",
                              line=dict(color=C["gold"],width=2,dash="dash")))
    fig1.add_trace(go.Scatter(x=years_proj, y=co2_net_zero, name="Net Zero 2050 Trajectory",
                              line=dict(color="#4CAF50",width=2)))
    fig1.add_vrect(x0=2025, x1=2050, fillcolor=C["glass"], line_width=0, opacity=0.3,
                   annotation_text="Projection Zone", annotation_position="top left",
                   annotation_font=dict(color=C["muted"],size=9))
    fig1.update_layout(**{**PLOT_LAYOUT,
                          "title":"Chile CO₂ Emission Scenarios — Historical & Projected (2025–2050)",
                          "yaxis_title":"Million Tonnes CO₂","xaxis_title":"Year"})

    # Per capita projection
    pop_proj = np.linspace(float(c["population"].iloc[-1]), 22e6, len(years_proj))
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=years_hist, y=c["co2_pc"].values, name="Historical",
                              line=dict(color=C["blue"],width=3)))
    fig2.add_trace(go.Scatter(x=years_proj, y=co2_proj*1e6/pop_proj, name="BAU",
                              line=dict(color="#FF6B6B",width=2,dash="dot")))
    fig2.add_trace(go.Scatter(x=years_proj, y=co2_ndc*1e6/pop_proj, name="NDC Scenario",
                              line=dict(color=C["gold"],width=2,dash="dash")))
    fig2.add_hline(y=2.0, line=dict(color="#4CAF50",dash="dash",width=1.5),
                   annotation_text="1.5°C compatible target (~2t/cap)",
                   annotation_font=dict(color="#4CAF50",size=9))
    fig2.update_layout(**{**PLOT_LAYOUT,"title":"Per Capita CO₂ Projections — Chile",
                          "yaxis_title":"Tonnes CO₂ per Person"})

    note = html.Div([
        html.Span("⚠️ Projection Disclaimer: ", style={"color":C["gold"],"fontWeight":"700"}),
        html.Span("""BAU = polynomial extrapolation of 1999–2024 trend. NDC scenario applies Chile's 
        nationally determined contribution target (30% reduction vs BAU peak by 2030). Net Zero scenario 
        assumes exponential decarbonisation consistent with IPCC SR1.5 pathways. All projections are 
        illustrative and subject to economic, policy, and technological uncertainties.""",
        style={"color":C["text"],"fontSize":"12px","fontFamily":"Georgia,serif"}),
    ], style={"background":C["blue_t"],"borderRadius":"8px","padding":"12px 16px",
              "borderLeft":f"3px solid {C['blue']}","marginTop":"20px",
              "fontSize":"12px"})

    return html.Div([
        section_title("🔮 Emission Projections & Scenarios",
                      "Business-as-usual vs NDC vs Net Zero 2050 pathways"),
        graph_card("fig-proj-total","",420,
                   "Sources: Historical — GCP (2024). Projections — Author's polynomial extrapolation + NDC targets"),
        graph_card("fig-proj-percap","",380,
                   "Sources: Historical — Our World in Data (2024). Scenarios: IPCC SR1.5 (2018)"),
        note,
    ]), fig1, fig2

# ── TAB 7: CLIMATE JUSTICE ───────────────────────────────────────────
def build_justice():
    reflection = """
    Chile occupies a morally complex position in the global climate architecture. With just 0.20% of global 
    annual CO₂ emissions and 0.15% of cumulative historical emissions, Chile is a small contributor to the 
    crisis it disproportionately suffers from — through glacial retreat in Patagonia, desertification expansion 
    in the Atacama, and increased wildfire frequency (witnessed dramatically in the Valparaíso wildfires of 2024).

    Yet Chile's role should not be merely passive. Its GDP per capita of $16,710 (2024) places it in the 
    upper-middle income bracket, conferring both the economic capacity and the moral obligation to act 
    beyond minimal thresholds. Chile has already shown leadership: it was among the first Latin American 
    nations to implement a carbon tax (2017, USD 5/tonne), and its NDC commits to carbon neutrality by 2050.

    Chile's greatest leverage lies in its renewable energy endowment. The Atacama Desert offers some of 
    the world's highest solar irradiance — already making Chile's northern grid a global benchmark for 
    low-cost solar energy. If Chile aggressively scales this potential and exports green hydrogen to 
    industrial importers in Asia and Europe, it could become a net-zero enabler far beyond its own borders.

    The principle of common but differentiated responsibilities (CBDR) supports a graduated Chilean 
    approach: transition rapidly domestically, lead South American climate coalitions (particularly 
    COP hosting and Mercosur carbon markets), and advocate firmly in climate negotiations for 
    adaptation finance for vulnerable nations — of which Chile itself is one.

    Data conclusion: Chile is a low emitter with high development capacity — it should lead by example, 
    not merely comply. Its 2050 net-zero commitment, backed by per-capita emissions already below the 
    world average, makes it a credible and powerful voice for ambitious global climate action.
    """

    paras = [p.strip() for p in reflection.strip().split("\n\n") if p.strip()]

    timeline_events = [
        (2010, "National Climate Change Action Plan", "First structured national policy framework"),
        (2015, "Paris Agreement", "Chile among first signatories, committed NDC target"),
        (2017, "Carbon Tax Introduced", "First carbon price in South America — USD 5/tonne"),
        (2019, "Updated NDC", "30% GHG reduction vs BAU by 2030; 45% conditional on finance"),
        (2021, "Carbon Neutrality 2050", "Net-zero emissions pledged under updated NDC"),
        (2022, "Green Hydrogen Strategy", "National plan targeting 25 GW electrolyzer capacity by 2030"),
        (2024, "Wildfire Crisis", "Valparaíso wildfires kill 131 — climate change link confirmed"),
    ]

    return html.Div([
        section_title("⚖️ Climate Justice Reflection",
                      "Chile's role in global mitigation — a data-driven argument"),
        html.Div([
            html.Div([
                html.Div("REFLECTION", style={"fontFamily":"Cinzel,serif","fontSize":"11px",
                                              "letterSpacing":"3px","color":C["muted"],"marginBottom":"16px"}),
                *[html.P(para, style={"color":C["text"],"fontFamily":"Georgia,serif",
                                      "fontSize":"14px","lineHeight":"1.9","marginBottom":"16px"})
                  for para in paras],
                html.Div([
                    html.Div("Word count: ~280 words", style={"color":C["muted"],"fontSize":"10px","fontStyle":"italic"}),
                    html.Div("Sources: GCP 2024; UNDP 2024; World Bank 2024; Chile NDC 2021",
                             style={"color":C["muted"],"fontSize":"10px","fontStyle":"italic","marginTop":"4px"}),
                ]),
            ], style={"background":C["card"],"borderRadius":"14px","padding":"28px",
                      "boxShadow":"0 4px 24px rgba(0,0,0,0.35)","flex":"1.5","minWidth":"320px",
                      "borderLeft":f"4px solid {C['red']}"}),
            html.Div([
                html.Div("CHILE'S CLIMATE TIMELINE", style={"fontFamily":"Cinzel,serif","fontSize":"11px",
                                                             "letterSpacing":"3px","color":C["muted"],
                                                             "marginBottom":"16px"}),
                *[html.Div([
                    html.Div(str(yr), style={"fontFamily":"Cinzel,serif","fontSize":"16px",
                                             "color":C["red"],"fontWeight":"700","marginBottom":"4px"}),
                    html.Div(event, style={"color":C["text"],"fontWeight":"600","fontSize":"13px"}),
                    html.Div(desc,  style={"color":C["muted"],"fontSize":"11px","marginTop":"2px",
                                          "fontFamily":"Georgia,serif"}),
                ], style={"borderLeft":f"2px solid {C['blue']}","paddingLeft":"14px",
                          "marginBottom":"16px","position":"relative"})
                for yr, event, desc in timeline_events],
            ], style={"background":C["card"],"borderRadius":"14px","padding":"24px",
                      "boxShadow":"0 4px 24px rgba(0,0,0,0.35)","flex":"1","minWidth":"240px"}),
        ], style={"display":"flex","gap":"20px","flexWrap":"wrap"}),
    ])

# ── TAB 8: CHATBOT ────────────────────────────────────────────────────
def build_chatbot():
    return html.Div([
        section_title("🤖 AI Climate Chatbot",
                      "Ask anything about Chile's climate data, emissions, or policy"),
        html.Div([
            html.Div([
                html.Div(id="chat-messages", children=[
                    html.Div([
                        html.Div("🤖", style={"fontSize":"20px","marginRight":"10px","flexShrink":"0"}),
                        html.Div([
                            html.Div("Chile Climate Assistant", style={"color":C["gold"],"fontWeight":"700",
                                                                         "fontSize":"11px","letterSpacing":"1px",
                                                                         "marginBottom":"4px","fontFamily":"Cinzel,serif"}),
                            html.Div("""Hola! I'm your Chile Climate Intelligence Assistant. I can answer 
                            questions about Chile's CO₂ emissions, climate policy, comparisons with other 
                            countries, energy transitions, and more. Try asking me something like:
                            "How does Chile compare to India in per capita emissions?" or 
                            "What is Chile's NDC target?" """,
                            style={"color":C["text"],"fontFamily":"Georgia,serif","fontSize":"13px",
                                   "lineHeight":"1.7"}),
                        ]),
                    ], style={"display":"flex","alignItems":"flex-start","marginBottom":"16px",
                              "background":C["card2"],"borderRadius":"12px","padding":"14px"}),
                ], style={"height":"420px","overflowY":"auto","marginBottom":"16px","padding":"8px"}),
                html.Div([
                    dcc.Input(id="chat-input", type="text",
                              placeholder="Ask about Chile's climate data, policies, comparisons...",
                              debounce=False, n_submit=0,
                              style={"width":"100%","background":C["card"],"border":f"1px solid {C['glass2']}",
                                     "borderRadius":"8px","color":C["text"],"fontFamily":"Georgia,serif",
                                     "fontSize":"13px","padding":"12px 16px","outline":"none","marginBottom":"10px"}),
                    html.Button("Send ✦", id="chat-send",
                                style={"background":f"linear-gradient(135deg,{C['red']},{C['blue']})",
                                       "border":"none","borderRadius":"8px","color":"white",
                                       "fontFamily":"Cinzel,serif","fontSize":"11px","letterSpacing":"2px",
                                       "padding":"12px 24px","cursor":"pointer",
                                       "fontWeight":"600"}),
                ], style={"display":"flex","flexDirection":"column"}),
                html.Div(id="chat-spinner", style={"color":C["muted"],"fontSize":"11px",
                                                   "marginTop":"8px","fontStyle":"italic"}),
            ], style={"flex":"1"}),
            html.Div([
                html.Div("Quick Questions", style={"fontFamily":"Cinzel,serif","fontSize":"11px",
                                                   "color":C["muted"],"letterSpacing":"2px","marginBottom":"12px"}),
                *[html.Button(q, id=f"quick-q-{i}",
                              style={"display":"block","width":"100%","background":C["card2"],
                                     "border":f"1px solid {C['glass2']}","borderRadius":"8px",
                                     "color":C["text"],"fontFamily":"Georgia,serif","fontSize":"12px",
                                     "padding":"10px 12px","cursor":"pointer","marginBottom":"8px",
                                     "textAlign":"left","transition":"background .2s"})
                  for i, q in enumerate([
                      "🌋 What are Chile's total CO₂ emissions in 2024?",
                      "📊 Compare Chile vs India per capita emissions",
                      "⚡ Chile's renewable energy progress?",
                      "🎯 What is Chile's NDC target?",
                      "🌍 Is Chile a high or low emitter?",
                      "📈 CO₂ trend over last 25 years?",
                      "⚖️ Climate justice obligations for Chile?",
                  ])],
                dcc.Store(id="chat-history", data=[]),
            ], style={"width":"200px","flexShrink":"0"}),
        ], style={"display":"flex","gap":"20px","background":C["card"],"borderRadius":"14px",
                  "padding":"24px","boxShadow":"0 4px 24px rgba(0,0,0,0.35)"}),
    ])

def build_floating_chat():
    return html.Div([
        dcc.Store(id="chat-open", data=False),
        html.Button(
            [html.Span("💬", style={"marginRight":"8px"}), html.Span("Clara")],
            id="chat-toggle-btn",
            className="floating-chat-toggle",
            title="Open Clara — Chile Climate Companion",
        ),
        html.Div([
            html.Div([
                html.Div([
                    html.Div("Clara", className="floating-chat-brand-name"),
                    html.Div("Chile Climate Companion", className="floating-chat-brand-sub"),
                ], className="floating-chat-title-block"),
                html.Button("✕", id="chat-minimize-btn", className="chat-min-btn", title="Close"),
            ], className="floating-chat-header"),
            html.Div(id="chat-messages", children=[
                html.Div([
                    html.Div("Clara", className="floating-chat-msg-name"),
                    html.Div(
                        "Hi — I'm Clara, your companion for this dashboard. Ask me anything: Chile's emissions, "
                        "renewables, comparisons with other countries, or even a casual hello. I'm here to help.",
                        className="floating-chat-msg-body",
                    ),
                ], className="chat-bot floating-chat-welcome"),
            ], className="floating-chat-messages"),
            html.Div([
                dcc.Input(
                    id="chat-input",
                    type="text",
                    placeholder="Type your message…",
                    className="floating-chat-input",
                    debounce=False,
                    n_submit=0,
                ),
                html.Button("Send", id="chat-send", type="button", className="floating-chat-send"),
            ], className="floating-chat-input-row"),
            dcc.Store(id="chat-history", data=[]),
        ], id="floating-chat-panel", className="floating-chat-panel", style={"display":"none"}),
    ], className="floating-chat-wrap")

# ── TAB 9: REPORT GENERATOR ──────────────────────────────────────────
def build_report():
    return html.Div([
        section_title("📄 LaTeX Report Generator",
                      "Customise and generate a professional academic report"),
        html.Div([
            html.Div([
                html.Label("Select Comparison Countries",
                           style={"color":C["muted"],"fontSize":"11px","letterSpacing":"1.5px",
                                  "textTransform":"uppercase","display":"block","marginBottom":"6px"}),
                dcc.Dropdown(id="rep-countries",
                             options=[{"label":c,"value":c} for c in COMPARATORS],
                             value=["India","World","United States","Germany"],
                             multi=True, className="dark-dropdown"),
            ], style={"marginBottom":"16px"}),
            html.Div([
                html.Label("Select Variables to Include",
                           style={"color":C["muted"],"fontSize":"11px","letterSpacing":"1.5px",
                                  "textTransform":"uppercase","display":"block","marginBottom":"6px"}),
                dcc.Checklist(id="rep-vars",
                              options=[
                                  {"label":" Annual CO₂ Emissions","value":"annual_co2"},
                                  {"label":" Per Capita CO₂","value":"co2_pc"},
                                  {"label":" Share of Global Emissions","value":"share_global"},
                                  {"label":" Cumulative CO₂","value":"cumulative_co2"},
                                  {"label":" CO₂ per Unit Energy","value":"co2_energy"},
                                  {"label":" GDP per Capita","value":"gdp_pc"},
                                  {"label":" HDI Analysis","value":"hdi"},
                                  {"label":" Sector Analysis (Coal/Oil/Gas)","value":"sectors"},
                                  {"label":" Climate Projections","value":"projections"},
                                  {"label":" Climate Justice Reflection","value":"justice"},
                              ],
                              value=["annual_co2","co2_pc","share_global","justice"],
                              labelStyle={"display":"block","color":C["text"],"fontFamily":"Georgia,serif",
                                         "fontSize":"13px","marginBottom":"8px","cursor":"pointer"},
                              inputStyle={"marginRight":"8px","accentColor":C["red"]}),
            ], style={"marginBottom":"16px"}),
            html.Div([
                html.Label("Student Name", style={"color":C["muted"],"fontSize":"11px",
                                                  "letterSpacing":"1.5px","display":"block","marginBottom":"6px"}),
                dcc.Input(id="rep-name", value="Shikhar Srivastava", type="text",
                          style={"background":"#FFFFFF","border":f"1px solid {C['glass2']}",
                                 "borderRadius":"8px","color":"#1a1a1a","padding":"10px 14px",
                                 "width":"100%","fontFamily":"Georgia,serif","fontSize":"13px"}),
            ], style={"marginBottom":"16px"}),
            html.Div([
                html.Label("Enrolment Number", style={"color":C["muted"],"fontSize":"11px",
                                                      "letterSpacing":"1.5px","display":"block","marginBottom":"6px"}),
                dcc.Input(id="rep-enrol", value="M2024BSASS026", type="text",
                          style={"background":"#FFFFFF","border":f"1px solid {C['glass2']}",
                                 "borderRadius":"8px","color":"#1a1a1a","padding":"10px 14px",
                                 "width":"100%","fontFamily":"Georgia,serif","fontSize":"13px"}),
            ], style={"marginBottom":"20px"}),
            html.Button("Generate Report Preview", id="gen-report-btn",
                        style={"background":f"linear-gradient(135deg,{C['red']},{C['blue']})",
                               "border":"none","borderRadius":"10px","color":"white",
                               "fontFamily":"Cinzel,serif","fontSize":"13px","letterSpacing":"3px",
                               "padding":"14px 32px","cursor":"pointer","width":"100%",
                               "fontWeight":"600","boxShadow":f"0 4px 20px {C['red_t']}"}),
            html.Button("Download PDF", id="download-report-btn",
                        style={"background":f"linear-gradient(135deg,{C['blue']},{C['gold']})",
                               "border":"none","borderRadius":"10px","color":"white",
                               "fontFamily":"Cinzel,serif","fontSize":"12px","letterSpacing":"2px",
                               "padding":"12px 20px","cursor":"pointer","width":"100%",
                               "fontWeight":"600","marginTop":"10px"}),
            dcc.Download(id="download-report"),
        ], style={"background":C["card"],"borderRadius":"14px","padding":"24px","maxWidth":"600px",
                  "boxShadow":"0 4px 24px rgba(0,0,0,0.35)","marginBottom":"20px"}),
        html.Div([
            html.Div("Report Preview", style={"fontFamily":"Cinzel,serif","fontSize":"11px",
                                             "color":C["muted"],"letterSpacing":"2px","marginBottom":"12px"}),
            html.Pre(id="report-preview",
                     style={"color":C["text"],"fontFamily":"'Courier New',monospace","fontSize":"11px",
                            "lineHeight":"1.6","overflow":"auto","maxHeight":"500px",
                            "background":C["card2"],"borderRadius":"8px","padding":"16px",
                            "border":f"1px solid {C['glass2']}"}),
        ], style={"background":C["card"],"borderRadius":"14px","padding":"24px",
                  "boxShadow":"0 4px 24px rgba(0,0,0,0.35)"}),
    ])

# ── TAB 10: METHODOLOGY ──────────────────────────────────────────────
def build_methodology():
    steps = [
        ("1. Data Collection", "data-collection",
         """All datasets sourced from open, peer-reviewed global repositories. Primary sources: 
         Our World in Data (CC BY 4.0), Global Carbon Project (GCP), World Bank Open Data (CC BY 4.0), 
         and UNDP Human Development Reports. Data downloaded as .xlsx files in December 2024."""),
        ("2. Data Cleaning & Preprocessing", "data-cleaning",
         """Python (pandas 2.x) pipeline applied: (a) trailing empty columns dropped using dropna(axis=1, how='all'); 
         (b) column names standardised to snake_case; (c) year-filtered to 1999–2024; 
         (d) type coercion via pd.to_numeric(errors='coerce'); (e) duplicate rows removed on (country, year) key; 
         (f) missing values imputed by linear interpolation within each country group, with edge NaNs 
         forward-/back-filled; (g) sorted by (country, year)."""),
        ("3. Metric Definitions", "definitions",
         """• Annual CO₂ (Mt): territorial fossil fuel + cement + flaring emissions, excluding LULUCF.
         • Per Capita (t): annual_CO₂ ÷ mid-year population.
         • Share of Global (%): country_CO₂ ÷ world_CO₂ × 100.
         • Cumulative CO₂ (Gt): running total of annual emissions from 1750.
         • CO₂/energy (kg/kWh): CO₂ ÷ primary energy consumption.
         • HDI: composite of life expectancy, education, income — UNDP methodology."""),
        ("4. Visualisation", "visualisation",
         """Dashboard built with Plotly Dash (Python), using Plotly graph_objects for chart-level control. 
         Colour palette derived from the Chilean flag (red: #D52B1E, blue: #0039A6). Typography: 
         Cinzel Decorative (display), Playfair Display (body). All charts include source citations."""),
        ("5. Projection Methodology", "projections",
         """Business-As-Usual (BAU): degree-2 polynomial regression fitted on 1999–2024 emission data 
         (numpy.polyfit). NDC scenario: linear reduction from BAU to Chile's NDC target (−30% vs BAU peak 
         by 2030), followed by 2% annual decay. Net Zero 2050: exponential decay to ~0 Mt by 2050. 
         All projections are illustrative and carry wide uncertainty bands."""),
        ("6. Limitations", "limitations",
         """• 2024 data points may be preliminary estimates (GCP typically finalises ~12 months lag).
         • Consumption-based emissions data has longer lag; latest = 2022.
         • Projections are polynomial extrapolations — not econometric models.
         • No Monte Carlo uncertainty quantification applied.
         • LULUCF not included in headline CO₂ figures (follows GCP convention)."""),
        ("7. Software Stack", "software",
         """Python 3.12 | pandas 2.x | numpy | plotly 5.x | dash 2.x | dash-bootstrap-components | 
         openpyxl. No proprietary software used. Full code available in project repository."""),
    ]
    return html.Div([
        section_title("🔬 Methodology",
                      "Transparent, reproducible — full pipeline documentation"),
        *[html.Div([
            html.Div(title, style={"fontFamily":"Cinzel,serif","fontSize":"14px","color":C["gold"],
                                   "marginBottom":"8px","fontWeight":"700"}),
            html.P(body, style={"color":C["text"],"fontFamily":"Georgia,serif","fontSize":"13px",
                                 "lineHeight":"1.9","whiteSpace":"pre-line"}),
        ], style={"background":C["card"],"borderRadius":"14px","padding":"22px",
                  "boxShadow":"0 4px 24px rgba(0,0,0,0.35)","marginBottom":"16px",
                  "borderLeft":f"3px solid {C['blue']}"})
        for title, _, body in steps],
    ])

# ── TAB 11: ABOUT ─────────────────────────────────────────────────────
def build_about():
    return html.Div([
        section_title("👤 About This Dashboard",
                      "Purpose, author, and acknowledgements"),
        html.Div([
            html.Div([
                html.Img(src=CHILE_FLAG_B64, style={"width":"54px","height":"36px","borderRadius":"4px","boxShadow":"0 2px 8px rgba(0,0,0,0.35)","marginBottom":"16px","display":"block"}),
                html.H2("CHILE CLIMATE INTELLIGENCE DASHBOARD",
                        style={"fontFamily":"Cinzel Decorative,Cinzel,serif","fontSize":"18px",
                               "color":C["text"],"letterSpacing":"2px","marginBottom":"8px"}),
                html.Div("Version 1.0 | December 2024",
                         style={"color":C["muted"],"fontSize":"11px","letterSpacing":"2px",
                                "marginBottom":"20px"}),
                html.Hr(style={"borderColor":C["glass2"],"margin":"16px 0"}),
                html.Div([
                    html.Div("PREPARED BY", style={"color":C["muted"],"fontSize":"10px",
                                                   "letterSpacing":"2px","marginBottom":"8px"}),
                    html.Div("Shikhar Srivastava", style={"fontFamily":"Cinzel,serif","fontSize":"20px",
                                                           "color":C["gold"],"fontWeight":"700"}),
                    html.Div("Enrolment No: M2024BSASS026", style={"color":C["text"],"fontSize":"13px","marginTop":"4px"}),
                    html.Div("Assigned Country: Chile", style={"color":C["red"],"fontSize":"13px","marginTop":"4px"}),
                    html.Hr(style={"borderColor":C["glass2"],"margin":"16px 0"}),
                    html.Div("COURSE", style={"color":C["muted"],"fontSize":"10px","letterSpacing":"2px","marginBottom":"8px"}),
                    html.Div("Climate Change, Sustainability and Development",
                             style={"color":C["text"],"fontFamily":"Georgia,serif","fontSize":"14px"}),
                    html.Div("BS in Analytics and Sustainability Studies (2024-28)",
                             style={"color":C["muted"],"fontSize":"12px","marginTop":"4px"}),
                    html.Div("Tata Institute of Social Sciences, Mumbai",
                             style={"color":C["muted"],"fontSize":"12px","marginTop":"4px"}),
                    html.Hr(style={"borderColor":C["glass2"],"margin":"16px 0"}),
                    html.Div("ASSIGNMENT", style={"color":C["muted"],"fontSize":"10px","letterSpacing":"2px","marginBottom":"8px"}),
                    html.Div("Assignment I — Weightage: 50%",
                             style={"color":C["text"],"fontSize":"13px"}),
                ]),
            ], style={"background":C["card"],"borderRadius":"14px","padding":"28px",
                      "flex":"1","boxShadow":"0 4px 24px rgba(0,0,0,0.35)"}),
            html.Div([
                html.Div("DASHBOARD PURPOSE", style={"color":C["muted"],"fontSize":"10px",
                                                     "letterSpacing":"2px","marginBottom":"12px"}),
                html.P("""This dashboard was developed as a comprehensive analytical tool for 
                understanding Chile's CO₂ emission profile across 1999–2024. It integrates 
                five global datasets to provide multi-dimensional insights across total emissions, 
                per-capita burden, sectoral sources, energy intensity, and comparative carbon 
                inequality.""", style={"color":C["text"],"fontFamily":"Georgia,serif",
                                      "fontSize":"13px","lineHeight":"1.8","marginBottom":"12px"}),
                html.P("""The dashboard is designed to support academic analysis, policy 
                communication, and educational outreach — allowing any user to explore 
                Chile's climate position interactively, generate custom comparisons, 
                and produce LaTeX-formatted reports.""",
                style={"color":C["text"],"fontFamily":"Georgia,serif","fontSize":"13px","lineHeight":"1.8"}),
                html.Hr(style={"borderColor":C["glass2"],"margin":"16px 0"}),
                html.Div("DATA SOURCES CITED (APA 7th)", style={"color":C["muted"],"fontSize":"10px",
                                                                 "letterSpacing":"2px","marginBottom":"10px"}),
                *[html.P(ref, style={"color":C["text"],"fontFamily":"Georgia,serif","fontSize":"11px",
                                     "lineHeight":"1.7","marginBottom":"8px","fontStyle":"italic"})
                  for ref in [
                      "Global Carbon Project. (2024). Global Carbon Budget 2024. https://www.globalcarbonproject.org",
                      "Ritchie, H., Roser, M., & Rosado, P. (2024). CO₂ and greenhouse gas emissions. Our World in Data. https://ourworldindata.org/co2-emissions",
                      "World Bank. (2024). World Development Indicators. https://data.worldbank.org",
                      "United Nations Development Programme. (2024). Human Development Report 2024. https://hdr.undp.org",
                      "International Energy Agency. (2024). World Energy Statistics. https://www.iea.org",
                      "IPCC. (2018). Global Warming of 1.5°C (SR1.5). https://www.ipcc.ch/sr15/",
                  ]],
                html.Hr(style={"borderColor":C["glass2"],"margin":"16px 0"}),
                html.Div("TECH STACK", style={"color":C["muted"],"fontSize":"10px",
                                             "letterSpacing":"2px","marginBottom":"10px"}),
                html.Div([
                    html.Span(t, style={"background":C["card2"],"borderRadius":"6px","padding":"4px 10px",
                                        "color":C["text"],"fontSize":"11px","margin":"3px",
                                        "border":f"1px solid {C['glass2']}","display":"inline-block"})
                    for t in ["Python 3.12","Plotly 5.x","Dash 2.x","pandas 2.x","numpy",
                              "dash-bootstrap-components","openpyxl","Cinzel Font","Playfair Display"]
                ]),
            ], style={"background":C["card"],"borderRadius":"14px","padding":"28px",
                      "flex":"1.5","boxShadow":"0 4px 24px rgba(0,0,0,0.35)"}),
        ], style={"display":"flex","gap":"20px","flexWrap":"wrap"}),
    ])

# ══════════════════════════════════════════════════════════════════════
#  PRE-BUILD ALL STATIC FIGURES
# ══════════════════════════════════════════════════════════════════════
overview_content = build_overview()
trends_content, fig_t1, fig_t2, fig_t3, fig_t4, fig_t5 = build_trends()
inequality_content, fig_i1, fig_i2, fig_i3, fig_i4, fig_i5 = build_inequality()
source_content, fig_s1, fig_s2, fig_s3, fig_s4 = build_source()
proj_content, fig_p1, fig_p2 = build_projections()

# ══════════════════════════════════════════════════════════════════════
#  CSS + GOOGLE FONTS
# ══════════════════════════════════════════════════════════════════════
EXTERNAL_STYLESHEETS = [
    dbc.themes.BOOTSTRAP,
    "https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700;900&family=Cinzel+Decorative:wght@400;700;900&family=Playfair+Display:ital,wght@0,400;0,600;1,400&display=swap",
]

CUSTOM_CSS = ""  # CSS served from assets/style.css (Dash auto-loads assets/*.css)

# ══════════════════════════════════════════════════════════════════════
#  APP LAYOUT
# ══════════════════════════════════════════════════════════════════════
app = dash.Dash(__name__, external_stylesheets=EXTERNAL_STYLESHEETS,
                suppress_callback_exceptions=True,
                meta_tags=[{"name":"viewport","content":"width=device-width,initial-scale=1"}])
app.title = "Chile Climate Intelligence Dashboard"
server = app.server

app.layout = html.Div([
    # CSS injected via assets/style.css
    # Splash
    splash,
    # Hidden store for active tab
    dcc.Store(id="active-tab", data="tab-overview"),
    dcc.Store(id="ui-click-fx", data=0),
    # Main content (hidden until splash dismissed)
    html.Div([
        navbar,
        html.Div(id="tab-content", className="dashboard-root",
                 style={"padding":"24px 28px","maxWidth":"1400px",
                        "margin":"0 auto","minHeight":"calc(100vh - 120px)"}),
        # Footer
        html.Div([
            html.Hr(style={"borderColor":C["glass2"],"margin":"0"}),
            html.Div([
                html.Span("Chile Climate Intelligence Dashboard",
                          style={"color":C["muted"],"fontSize":"11px","fontFamily":"Cinzel,serif"}),
                html.Span(" · Shikhar Srivastava · M2024BSASS026 · TISS Mumbai 2024-28",
                          style={"color":C["muted"],"fontSize":"10px"}),
                html.Span(f" · Data: Our World in Data, GCP, World Bank, UNDP",
                          style={"color":C["muted"],"fontSize":"10px"}),
            ], style={"padding":"14px 28px","textAlign":"center"}),
        ], style={"background":C["dark2"],"marginTop":"40px"}),
    ], id="main-content", className="main-content-shell", style={"display":"none"}),
    build_floating_chat(),
], style={"background":C["dark"],"minHeight":"100vh"})

# ══════════════════════════════════════════════════════════════════════
#  CALLBACKS
# ══════════════════════════════════════════════════════════════════════

# Splash dismiss — curtain-out + main dashboard reveal (CSS transitions)
app.clientside_callback(
    """
    function(n) {
        if (n && n > 0) {
            var splash = document.getElementById('splash-screen');
            var main   = document.getElementById('main-content');
            if (!splash || !main) return window.dash_clientside.no_update;
            splash.classList.add('splash-hidden');
            main.style.display = 'block';
            main.classList.remove('main-enter-active');
            main.classList.add('main-enter-start');
            window.requestAnimationFrame(function() {
                window.requestAnimationFrame(function() {
                    main.classList.add('main-enter-active');
                });
            });
            setTimeout(function() { splash.style.display = 'none'; }, 1150);
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("splash-screen","className"),
    Input("enter-btn","n_clicks"),
    prevent_initial_call=True,
)

@callback(
    Output("chat-open", "data"),
    [Input("chat-toggle-btn", "n_clicks"), Input("chat-minimize-btn", "n_clicks")],
    State("chat-open", "data"),
    prevent_initial_call=True,
)
def toggle_chat(_open_click, _close_click, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    trig = ctx.triggered[0]["prop_id"].split(".")[0]
    if trig == "chat-toggle-btn":
        return True
    if trig == "chat-minimize-btn":
        return False
    return bool(is_open)

@callback(
    Output("floating-chat-panel", "style"),
    Input("chat-open", "data"),
)
def update_chat_panel(is_open):
    if is_open:
        return {
            "display": "flex",
            "flexDirection": "column",
            "maxHeight": "min(560px, 85vh)",
        }
    return {"display": "none"}

app.clientside_callback(
    """
    function() {
        window.__lastMouseX = window.__lastMouseX || window.innerWidth - 120;
        window.__lastMouseY = window.__lastMouseY || window.innerHeight - 120;
        if (!window.__mouseFxBound) {
            document.addEventListener('mousemove', function(e){ window.__lastMouseX = e.clientX; window.__lastMouseY = e.clientY; });
            window.__mouseFxBound = true;
        }
        var cloud = document.createElement('div');
        cloud.className = 'emission-cloud';
        cloud.style.left = window.__lastMouseX + 'px';
        cloud.style.top = window.__lastMouseY + 'px';
        document.body.appendChild(cloud);
        setTimeout(function(){ cloud.remove(); }, 900);
        return Date.now();
    }
    """,
    Output("ui-click-fx", "data"),
    [Input("enter-btn","n_clicks")] + [Input(f"nav-{tid}","n_clicks") for _,_,tid in TABS_CONFIG],
    prevent_initial_call=True,
)

# Tab navigation
@callback(Output("active-tab","data"),
          [Input(f"nav-{tid}","n_clicks") for _,_,tid in TABS_CONFIG],
          prevent_initial_call=True)
def update_tab(*args):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    btn_id = ctx.triggered[0]["prop_id"].split(".")[0]
    return btn_id.replace("nav-","")

# Render tab content
@callback(Output("tab-content","children"),
          Input("active-tab","data"))
def render_tab(tab):
    if tab == "tab-overview":
        return overview_content
    elif tab == "tab-trends":
        return trends_content
    elif tab == "tab-inequality":
        return inequality_content
    elif tab == "tab-source":
        return source_content
    elif tab == "tab-compare":
        return build_compare()
    elif tab == "tab-explorer":
        return build_explorer()
    elif tab == "tab-projections":
        return proj_content
    elif tab == "tab-justice":
        return build_justice()
    elif tab == "tab-report":
        return build_report()
    elif tab == "tab-methodology":
        return build_methodology()
    elif tab == "tab-about":
        return build_about()
    return overview_content

# ── Nav button highlighting ───────────────────────────────────────────
for _, _, tid in TABS_CONFIG:
    app.clientside_callback(
        f"""
        function(activeTab) {{
            if (activeTab === '{tid}') return 'nav-tab nav-tab-active';
            return 'nav-tab';
        }}
        """,
        Output(f"nav-{tid}", "className"),
        Input("active-tab", "data"),
    )

# ── Static figure injection ───────────────────────────────────────────
@callback(
    [Output("fig-total-co2","figure"), Output("fig-percap-co2","figure"),
     Output("fig-gdp-co2","figure"),   Output("fig-hdi-co2","figure"),
     Output("fig-growth-rate","figure")],
    [Input("active-tab","data"), Input("trends-year-range","value")])
def update_trend_figs(tab, year_range):
    if tab == "tab-trends":
        start, end = year_range if year_range else (1999, 2024)
        c = chile[(chile["year"] >= start) & (chile["year"] <= end)].copy()
        if c.empty:
            return fig_t1, fig_t2, fig_t3, fig_t4, fig_t5

        f1 = go.Figure(go.Scatter(x=c["year"], y=c["annual_co2"]/1e6, mode="lines+markers", line=dict(color=C["red"], width=3), fill="tozeroy", fillcolor=C["red_t"]))
        f1.update_layout(**{**PLOT_LAYOUT, "title":f"Total Annual CO₂ Emissions ({start}-{end})"})
        f2 = go.Figure(go.Scatter(x=c["year"], y=c["co2_pc"], mode="lines+markers", line=dict(color=C["blue"], width=3), fill="tozeroy", fillcolor=C["blue_t"]))
        f2.update_layout(**{**PLOT_LAYOUT, "title":f"CO₂ Per Capita ({start}-{end})"})
        f3 = make_subplots(specs=[[{"secondary_y":True}]])
        f3.add_trace(go.Bar(x=c["year"], y=c["annual_co2"]/1e6, marker_color=C["red_t"], name="Annual CO₂"), secondary_y=False)
        f3.add_trace(go.Scatter(x=c["year"], y=c["gdp_pc"], line=dict(color=C["gold"], width=3), name="GDP per Capita"), secondary_y=True)
        f3.update_layout(**{**PLOT_LAYOUT, "title":f"CO₂ vs GDP ({start}-{end})"})
        f4 = px.scatter(c, x="hdi", y="co2_pc", size="population", color="year", title=f"HDI vs CO₂ ({start}-{end})")
        f4.update_layout(**PLOT_LAYOUT)
        c["co2_growth"] = c["annual_co2"].pct_change()*100
        f5 = go.Figure(go.Bar(x=c["year"], y=c["co2_growth"], marker_color=[C["red"] if v > 0 else "#4CAF50" for v in c["co2_growth"].fillna(0)]))
        f5.update_layout(**{**PLOT_LAYOUT, "title":f"YOY CO₂ Growth ({start}-{end})"})
        return f1, f2, f3, f4, f5
    return [dash.no_update]*5

@callback(
    [Output("fig-percap-bar","figure"), Output("fig-share-time","figure"),
     Output("fig-cumul-bar","figure"),  Output("fig-chile-india","figure"),
     Output("fig-radar","figure")],
    [Input("active-tab","data"), Input("inequality-year-range","value")])
def update_inequality_figs(tab, year_range):
    if tab == "tab-inequality":
        start, end = year_range if year_range else (1999, 2024)
        sub = world[(world["year"] >= start) & (world["year"] <= end)]
        comps = sub[sub["country"].isin(COMPARATORS)].copy()
        latest = comps.sort_values("year").groupby("country").last().reset_index()
        f1 = go.Figure(go.Bar(x=latest["co2_pc"], y=latest["country"], orientation="h"))
        f1.update_layout(**{**PLOT_LAYOUT, "title":f"Per Capita Comparison ({start}-{end})"})
        f2 = go.Figure()
        for co in ["Chile","India","China","United States","Germany","Brazil"]:
            csub = sub[sub["country"] == co]
            f2.add_trace(go.Scatter(x=csub["year"], y=csub["share_global"], mode="lines", name=co))
        f2.update_layout(**{**PLOT_LAYOUT, "title":f"Share of Global Emissions ({start}-{end})"})
        latest_year = int(min(end, sub["year"].max()))
        cumul = sub[sub["year"] == latest_year].dropna(subset=["cumulative_co2"]).nlargest(10, "cumulative_co2")
        f3 = go.Figure(go.Bar(x=cumul["country"], y=cumul["cumulative_co2"]/1e9))
        f3.update_layout(**{**PLOT_LAYOUT, "title":f"Cumulative Emissions Snapshot ({latest_year})"})
        f4 = go.Figure()
        for co in ["Chile","India","World"]:
            csub = sub[sub["country"] == co]
            f4.add_trace(go.Scatter(x=csub["year"], y=csub["co2_pc"], mode="lines+markers", name=co))
        f4.update_layout(**{**PLOT_LAYOUT, "title":f"Chile vs India vs World ({start}-{end})"})
        f5 = fig_i5
        return f1, f2, f3, f4, f5
    return [dash.no_update]*5

@callback(
    [Output("fig-sector-area","figure"), Output("fig-sector-pie","figure"),
     Output("fig-terr-cons","figure"),   Output("fig-energy-int","figure")],
    [Input("active-tab","data"), Input("source-year-range","value")])
def update_source_figs(tab, year_range):
    if tab == "tab-source":
        start, end = year_range if year_range else (1999, 2024)
        c = chile[(chile["year"] >= start) & (chile["year"] <= end)].copy()
        if c.empty:
            return fig_s1, fig_s2, fig_s3, fig_s4
        sectors = ["coal","oil","gas","cement","flaring"]
        labels = ["Coal","Oil","Gas","Cement","Flaring"]
        f1 = go.Figure()
        for sec, lbl in zip(sectors, labels):
            if sec in c.columns:
                f1.add_trace(go.Scatter(x=c["year"], y=c[sec], stackgroup="one", mode="lines", name=lbl))
        f1.update_layout(**{**PLOT_LAYOUT, "title":f"Sector Mix ({start}-{end})"})
        latest = c[c["year"] == c["year"].max()].iloc[0]
        f2 = go.Figure(go.Pie(labels=labels, values=[latest.get(s, 0) for s in sectors], hole=0.5))
        f2.update_layout(**{**PLOT_LAYOUT, "title":f"Latest Sector Pie ({int(latest['year'])})"})
        f3 = go.Figure()
        f3.add_trace(go.Scatter(x=c["year"], y=c["territorial"]/1e6, name="Territorial"))
        f3.add_trace(go.Scatter(x=c["year"], y=c["consumption"]/1e6, name="Consumption"))
        f3.update_layout(**{**PLOT_LAYOUT, "title":f"Territorial vs Consumption ({start}-{end})"})
        w = g_energy[(g_energy["country"] == "World") & (g_energy["year"] >= start) & (g_energy["year"] <= end)]
        f4 = go.Figure()
        f4.add_trace(go.Scatter(x=c["year"], y=c["co2_energy"], name="Chile"))
        f4.add_trace(go.Scatter(x=w["year"], y=w["co2_energy"], name="World"))
        f4.update_layout(**{**PLOT_LAYOUT, "title":f"CO₂ per Unit Energy ({start}-{end})"})
        return f1, f2, f3, f4
    return [dash.no_update]*4

@callback(
    [Output("fig-proj-total","figure"), Output("fig-proj-percap","figure")],
    Input("active-tab","data"))
def update_proj_figs(tab):
    if tab == "tab-projections":
        return fig_p1, fig_p2
    return [dash.no_update]*2

# ── Compare tab callbacks ─────────────────────────────────────────────
@callback(
    [Output("fig-compare-line","figure"), Output("fig-compare-bar","figure"),
     Output("fig-gdp-scatter","figure"),  Output("fig-compare-heatmap","figure")],
    [Input("compare-countries","value"), Input("compare-metric","value"),
     Input("compare-years","value"), Input("active-tab","data")])
def update_compare(countries, metric, yr_range, tab):
    if tab != "tab-compare" or not countries:
        return [dash.no_update]*4

    sub = world[world["country"].isin(countries)].copy()
    sub = sub[(sub["year"]>=yr_range[0])&(sub["year"]<=yr_range[1])]

    metric_labels = {"co2_pc":"CO₂ per Capita (t)","annual_co2":"Annual CO₂ (Mt)",
                     "share_global":"Share of Global (%)","cumulative_co2":"Cumulative CO₂ (Gt)",
                     "co2_energy":"CO₂ per Unit Energy (kg/kWh)"}
    y_lbl = metric_labels.get(metric, metric)
    divisor = 1e6 if metric=="annual_co2" else 1e9 if metric=="cumulative_co2" else 1

    # Line chart
    fig_line = go.Figure()
    palette = [C["red"],C["blue"],C["gold"],"#4CAF50","#FF6B6B","#9C27B0","#FF9800",
               "#00BCD4","#E91E63","#3F51B5","#009688","#FFC107"]
    for co, col in zip(countries, palette):
        csub = sub[sub["country"]==co].dropna(subset=[metric]).sort_values("year")
        if len(csub):
            fig_line.add_trace(go.Scatter(
                x=csub["year"], y=csub[metric]/divisor, name=co,
                line=dict(color=col, width=3 if co=="Chile" else 1.8),
                mode="lines+markers", marker=dict(size=5 if co!="Chile" else 8)))
    fig_line.update_layout(**{**PLOT_LAYOUT,"title":f"{y_lbl} — Country Comparison",
                               "yaxis_title":y_lbl})

    # Bar chart (latest year)
    latest_yr = sub["year"].max()
    bar_df = sub[sub["year"]==latest_yr].dropna(subset=[metric]).sort_values(metric)
    fig_bar = go.Figure(go.Bar(
        x=bar_df[metric]/divisor, y=bar_df["country"], orientation="h",
        marker=dict(color=[C["red"] if c=="Chile" else C["card2"] for c in bar_df["country"]],
                    line=dict(color=[C["red"] if c=="Chile" else C["blue"] for c in bar_df["country"]],
                              width=1.5)),
        text=[f"{v/divisor:.2f}" for v in bar_df[metric]],
        textposition="outside", textfont=dict(size=9),
    ))
    fig_bar.update_layout(**{**PLOT_LAYOUT,"title":f"{y_lbl} — {latest_yr} Snapshot",
                              "margin":dict(l=100,r=40,t=60,b=40)})

    # GDP scatter (using world + chile gdp)
    scatter_df = sub[sub["year"]==latest_yr].copy()
    # Merge gdp from chile dataset where available
    chile_gdp = chile[["year","gdp_pc","population"]].rename(columns={"year":"year"})
    scatter_df = scatter_df.merge(
        chile[chile["year"]==latest_yr][["country","gdp_pc","population"]].assign(country="Chile"),
        on="country", how="left")
    fig_scatter = px.scatter(
        sub[sub["year"]==latest_yr].dropna(subset=[metric]),
        x="year", y=metric, color="country", size_max=40,
        color_discrete_sequence=palette,
        labels={"year":"Year","co2_pc":"CO₂ per Capita (t)"},
        title=f"GDP per Capita vs {y_lbl} (bubble = population approx.)")
    fig_scatter.update_layout(**PLOT_LAYOUT)

    # Heatmap
    pivot = sub.pivot_table(index="country", columns="year", values=metric, aggfunc="mean")
    fig_hm = go.Figure(go.Heatmap(
        z=pivot.values/divisor, x=pivot.columns, y=pivot.index,
        colorscale=[[0,C["blue"]],[0.5,C["dark"]],[1,C["red"]]],
        hovertemplate="%{y} %{x}: %{z:.3f}<extra></extra>",
        colorbar=dict(thickness=12, tickfont=dict(size=9), title=dict(text=y_lbl,side="right")),
    ))
    fig_hm.update_layout(**{**PLOT_LAYOUT,"title":f"{y_lbl} Heatmap — Countries × Years",
                             "margin":dict(l=120,r=60,t=60,b=40)})

    return fig_line, fig_bar, fig_scatter, fig_hm

# ── Explorer callbacks ────────────────────────────────────────────────
@callback(
    [Output("fig-explorer","figure"), Output("exp-table-div","children")],
    [Input("exp-country","value"), Input("exp-metric","value"),
     Input("active-tab","data")])
def update_explorer(countries, metric, tab):
    if tab != "tab-explorer" or not countries:
        return dash.no_update, dash.no_update

    sub = world[world["country"].isin(countries)].dropna(subset=[metric]).sort_values(["country","year"])
    divisor = 1e6 if metric=="annual_co2" else 1e9 if metric=="cumulative_co2" else 1
    y_labels = {"co2_pc":"CO₂ per Capita (t)","annual_co2":"Annual CO₂ (Mt)",
                "share_global":"Share of Global (%)","cumulative_co2":"Cumulative CO₂ (Gt)",
                "co2_energy":"CO₂ per Unit Energy (kg/kWh)"}

    fig = go.Figure()
    palette = [C["red"],C["blue"],C["gold"],"#4CAF50","#FF6B6B","#9C27B0"]
    for co, col in zip(countries, palette):
        csub = sub[sub["country"]==co]
        fig.add_trace(go.Scatter(x=csub["year"], y=csub[metric]/divisor,
                                 name=co, mode="lines+markers",
                                 line=dict(color=col,width=2.5),
                                 marker=dict(size=5)))
    fig.update_layout(**{**PLOT_LAYOUT,"title":f"Explorer: {y_labels.get(metric,metric)}",
                         "yaxis_title":y_labels.get(metric,metric)})

    disp = sub[["country","year",metric,"code"]].copy()
    disp[metric] = (disp[metric]/divisor).round(4)
    disp.columns = ["Country","Year",y_labels.get(metric,metric),"Code"]

    table = dash_table.DataTable(
        data=disp.to_dict("records"),
        columns=[{"name":c,"id":c} for c in disp.columns],
        page_size=15, sort_action="native", filter_action="native",
        export_format="csv",
        style_table={"overflowX":"auto","borderRadius":"12px","overflow":"hidden"},
        style_header={"backgroundColor":"#E8D4C8","color":"#1a1a1a","fontWeight":"700",
                      "fontFamily":"Cinzel,serif","fontSize":"12px","letterSpacing":"1.5px",
                      "border":f"2px solid {C['gold']}","padding":"12px 14px",
                      "textAlign":"center","textTransform":"uppercase"},
        style_cell={"backgroundColor":"#FFFFFF","color":"#1a1a1a","fontWeight":"500",
                    "fontFamily":"Georgia,serif","fontSize":"13px",
                    "border":f"1px solid {C['glass2']}","padding":"11px 14px",
                    "textAlign":"left"},
        style_data_conditional=[
            {"if":{"row_index":"odd"},"backgroundColor":"#F9F7F5"},
            {"if":{"filter_query":"{Country} = Chile"},
             "backgroundColor":"#FFE5D9","color":"#1a1a1a","fontWeight":"600",
             "borderLeft":f"4px solid {C['red']}"},
            {"if":{"state":"selected"},"backgroundColor":"#D4A574","color":"white","fontWeight":"700"},
        ],
    )
    return fig, table

@callback(Output("download-data","data"),
          Input("download-btn","n_clicks"),
          [State("exp-country","value"), State("exp-metric","value")],
          prevent_initial_call=True)
def download_data(n, countries, metric):
    if not countries:
        return dash.no_update
    sub = world[world["country"].isin(countries)][["country","code","year",metric]].dropna()
    return dcc.send_data_frame(sub.to_csv, "chile_dashboard_export.csv", index=False)

# ── Chatbot: Clara (always replies; climate data + friendly general chat) ──
CHAT_ASSISTANT_NAME = "Clara"

def _welcome_clara():
    return html.Div([
        html.Div("Clara", className="floating-chat-msg-name"),
        html.Div(
            "Hi — I'm Clara, your companion for this dashboard. Ask me anything: Chile's emissions, "
            "renewables, comparisons with other countries, or even a casual hello. I'm here to help.",
            className="floating-chat-msg-body",
        ),
    ], className="chat-bot floating-chat-welcome")

def _bubble_user(text):
    return html.Div([
        html.Div("You", className="floating-chat-label-user"),
        html.Div(text, className="floating-chat-msg-text-user"),
    ], className="chat-user floating-chat-bubble-user")

def _bubble_bot(text):
    return html.Div([
        html.Div([
            html.Span("✦ ", className="floating-chat-star"),
            html.Span(CHAT_ASSISTANT_NAME, className="floating-chat-label-bot"),
        ], className="floating-chat-bot-header"),
        html.Div(text, className="floating-chat-msg-text-bot"),
    ], className="chat-bot floating-chat-bubble-bot")

def _render_chat_from_history(history):
    if not history:
        return [_welcome_clara()]
    out = []
    for entry in history:
        if not isinstance(entry, dict):
            continue
        role = entry.get("role")
        text = entry.get("content", "")
        if role == "user":
            out.append(_bubble_user(text))
        elif role == "assistant":
            out.append(_bubble_bot(text))
    return out if out else [_welcome_clara()]

def general_small_talk(msg: str):
    m = msg.lower().strip()
    if not m:
        return None
    if m in ("hi", "hello", "hey", "hi!", "hello!", "hey!", "hiya", "yo", "sup"):
        return (
            f"Hello! I'm {CHAT_ASSISTANT_NAME}, your Chile Climate Companion. "
            "Ask me about emissions, renewables, policy, comparisons — or anything on your mind; "
            "I'll answer in a friendly way and tie in Chile's story when it fits."
        )
    if any(x in m for x in ("thank", "thanks", "appreciate", "grateful")):
        return (
            "You're very welcome! Happy to help. If you want numbers, try asking about Chile's "
            "2024 emissions or how they compare to India or the world average."
        )
    if any(x in m for x in ("bye", "goodbye", "see you", "see ya", "cya")):
        return (
            "Goodbye for now! The dashboard will be here when you return — "
            "and I'm always up for more questions about Chile and climate."
        )
    if "how are you" in m or "how r you" in m:
        return (
            "I'm doing great — energized and ready to dig into Chile's CO₂ data, renewables, "
            "or whatever you're curious about. What's on your mind?"
        )
    return None

def compose_bot_reply(user_msg: str, latest):
    small = general_small_talk(user_msg)
    if small is not None:
        return small
    return generate_fallback_response(user_msg, latest)

# ── Chatbot callback (history in Store only — avoids Dash children de/serialization bugs) ──
@callback(
    [Output("chat-messages","children"), Output("chat-input","value"),
     Output("chat-history","data")],
    [Input("chat-send","n_clicks"), Input("chat-input","n_submit")],
    [State("chat-input","value"), State("chat-history","data")],
    prevent_initial_call=True)
def handle_chat(n_click, n_submit, user_msg, history):
    if not user_msg or not str(user_msg).strip():
        return dash.no_update, dash.no_update, history if isinstance(history, list) else []

    user_msg = str(user_msg).strip()
    latest = CHILE_LATEST_ROW
    hist = list(history) if isinstance(history, list) else []

    try:
        bot_reply = compose_bot_reply(user_msg, latest)
    except Exception:
        bot_reply = (
            f"I hit a small snag — but here's a quick snapshot: Chile's 2024 CO₂ is about "
            f"{latest['annual_co2']/1e6:.1f} Mt. Ask me again in other words and I'll do my best!"
        )

    new_hist = hist + [{"role":"user","content":user_msg}, {"role":"assistant","content":bot_reply}]
    children = _render_chat_from_history(new_hist)
    return children, "", new_hist

def generate_fallback_response(msg, latest):
    msg_lower = msg.lower()
    earliest = CHILE_EARLIEST_ROW
    co2_growth = ((latest['annual_co2']/earliest['annual_co2'])-1)*100
    gdp_growth = ((latest['gdp_pc']/earliest['gdp_pc'])-1)*100
    
    if any(k in msg_lower for k in ["total","annual","co2","emissions"]):
        return (f"📊 **Chile's Total Annual CO₂ Emissions (2024)**: {latest['annual_co2']/1e6:.2f} Mt\n\n"
                f"• Global Share: {latest['share_global']:.3f}% (negligible contributor)\n"
                f"• Change since 1999: +{co2_growth:.0f}% ({earliest['annual_co2']/1e6:.2f} Mt → {latest['annual_co2']/1e6:.2f} Mt)\n"
                f"• Per Capita: {latest['co2_pc']:.2f} t/person (below global avg of 4.58t)\n"
                f"• Main sources: Energy (60%), Industrial Processes (20%), Agriculture (15%)\n"
                f"\nChile is a LOW EMITTER — ranking in the bottom 50th percentile globally.")
    elif "per capita" in msg_lower or "capita" in msg_lower:
        return (f"👤 **Per Capita CO₂ Emissions**: {latest['co2_pc']:.3f} tonnes/person\n\n"
                f"**Comparisons:**\n"
                f"• Global average: 4.58 t/person\n"
                f"• India: ~1.9 t/person\n"
                f"• USA: ~14.9 t/person\n"
                f"• UK: ~5.2 t/person\n"
                f"• Chile: {latest['co2_pc']:.2f} t/person (above India, below global average)\n\n"
                f"Chile's per capita emissions have remained **relatively stable** since 1999 despite GDP growth,\n"
                f"indicating successful decoupling of economic growth from emissions.")
    elif "india" in msg_lower:
        india_sub = world[(world["country"] == "India") & (world["year"] == 2024)]
        if len(india_sub) > 0 and pd.notna(india_sub.iloc[0].get("co2_pc")):
            india_pc = float(india_sub.iloc[0]["co2_pc"])
        else:
            india_pc = 1.9
        return (f"🌏 **Chile vs India Comparison:**\n\n"
                f"**Per Capita:**\n"
                f"• Chile: {latest['co2_pc']:.2f} t/person\n"
                f"• India: ~{india_pc:.2f} t/person\n"
                f"• Ratio: Chile emits ~{latest['co2_pc']/india_pc:.1f}× India's per capita\n\n"
                f"**Total Emissions:**\n"
                f"• Chile: 0.20% of global\n"
                f"• India: ~7% of global\n"
                f"• India's TOTAL emissions are 350× larger than Chile's\n\n"
                f"**Context:** India has 70× Chile's population but half the per-capita emissions.\n"
                f"Both are low-to-moderate emitters compared to developed nations.")
    elif "ndc" in msg_lower or "target" in msg_lower or "commitment" in msg_lower:
        return (f"🎯 **Chile's Climate Commitments (NDC 2021):**\n\n"
                f"**2030 Targets:**\n"
                f"• -30% GHG reduction vs Business-as-Usual (unconditional)\n"
                f"• -45% GHG reduction (conditional on international climate finance)\n"
                f"• Specific CO₂ reduction: -15% absolute vs 2018 baseline\n\n"
                f"**Long-term Goals:**\n"
                f"• Carbon Neutrality by 2050\n"
                f"• Renewable energy: 60% by 2035 (already at ~55% in 2024!)\n\n"
                f"**Policy Instruments:**\n"
                f"• Carbon Tax (2017): USD 5/tonne CO₂\n"
                f"• Energy Transition Law (2021): Phase out coal by 2040\n"
                f"• Clean Production Agreements\n\nChile is one of **Latin America's climate leaders**.")
    elif "renewable" in msg_lower or "energy" in msg_lower:
        return (f"⚡ **Chile's Renewable Energy Landscape:**\n\n"
                f"**Current Status (2024):**\n"
                f"• Renewable share: ~55% of electricity\n"
                f"• Hydro: 25% (Patagonian rivers)\n"
                f"• Solar: 18% (Atacama Desert - world's best solar resource!)\n"
                f"• Wind: 12%\n\n"
                f"**Unique Advantage:**\n"
                f"• Atacama Desert has HIGHEST solar irradiance globally (~2,900 kWh/m²/year)\n"
                f"• Patagonia has excellent wind resources\n\n"
                f"**Green Hydrogen Potential:**\n"
                f"Chile is positioning itself to become a **green hydrogen exporter** — \n"
                f"leveraging cheap renewable electricity to produce H₂ for global decarbonization.\n\n"
                f"CO₂ per unit energy: declining since 2014 ✓")
    elif "gdp" in msg_lower or "economy" in msg_lower:
        return (f"💰 **Chile's Economic Profile:**\n\n"
                f"**2024 Status:**\n"
                f"• GDP per capita: ${latest['gdp_pc']:,.0f} (current USD)\n"
                f"• Growth since 1999: +{gdp_growth:.0f}%\n"
                f"• Ranking: HIGHEST in South America, Top 2 in Latin America\n\n"
                f"**Income Trajectory:**\n"
                f"• 1999: ~$3,000 per capita\n"
                f"• 2024: ~${latest['gdp_pc']:,.0f} per capita\n"
                f"• Status: Upper-Middle Income Country → High Income Country\n\n"
                f"**Emissions Decoupling:**\n"
                f"Economic growth has NOT led to proportional emissions growth — \n"
                f"CO₂ inten sity per USD of GDP is **declining**. ✓")
    elif "hdi" in msg_lower or "development" in msg_lower:
        return (f"🏆 **Human Development in Chile:**\n\n"
                f"**HDI Score (2024): {latest['hdi']:.3f}**\n"
                f"Classification: **VERY HIGH HUMAN DEVELOPMENT**\n\n"
                f"**Components:**\n"
                f"• Life Expectancy: ~80 years\n"
                f"• Mean Years of Schooling: ~10.6 years\n"
                f"• GNI per capita: ${latest['gdp_pc']:,.0f}\n\n"
                f"**Ranking:** Top 5 in Latin America, Global rank ~42 out of 193\n\n"
                f"**Climate Justice Implication:**\n"
                f"High development + Low emissions = Chile has capacity to lead\n"
                f"climate action in Latin America without sacrificing wellbeing.")
    elif "climate justice" in msg_lower or "justice" in msg_lower:
        return (f"⚖️ **Climate Justice Perspective on Chile:**\n\n"
                f"**The Paradox:**\n"
                f"• 0.20% of global emissions → Minimal historical responsibility\n"
                f"• Yet vulnerable to climate change: glacial retreat, wildfires, drought\n\n"
                f"**Why Chile Should Act:**\n"
                f"1. **Capacity:** High HDI ({latest['hdi']:.3f}), strong economy\n"
                f"2. **Opportunity:** Renewable energy leadership (Atacama, Patagonia)\n"
                f"3. **Moral Leadership:** Can show development ≠ high emissions\n"
                f"4. **Self-Interest:** Vulnerable to global climate impacts\n\n"
                f"**Chile's Role:**\n"
                f"• Advocate for LOSS & DAMAGE finance for vulnerable nations\n"
                f"• Lead South American climate coalitions\n"
                f"• Export green hydrogen to help others decarbonize\n\nChile: a **small emitter with a LARGE voice**.")
    elif "sectoral" in msg_lower or "sector" in msg_lower or "source" in msg_lower:
        return (f"🏭 **Chile's Emissions by Sector:**\n\n"
                f"**Breakdown (2024):**\n"
                f"• Energy: 60% (power, transport, heating)\n"
                f"• Industrial Processes: 20% (cement, chemicals)\n"
                f"• Agriculture: 15% (livestock, cropland)\n"
                f"• Waste: 5%\n\n"
                f"**Emissions Peak:** 2013 (~132 Mt CO₂)\n"
                f"**Trend:** Stabilizing with renewable energy growth\n\n"
                f"**Key Opportunities:**\n"
                f"• Transport electrification (mining sector, vehicles)\n"
                f"• Green hydrogen for industry\n"
                f"• Sustainable agriculture practices")
    elif "projections" in msg_lower or "future" in msg_lower or "forecast" in msg_lower:
        return (f"🔮 **Chile's Emissions Outlook:**\n\n"
                f"**2024 Baseline:** {latest['annual_co2']/1e6:.1f} Mt CO₂\n\n"
                f"**Scenarios:**\n"
                f"• **BAU (Business-as-Usual):** Could reach 250+ Mt by 2050\n"
                f"• **NDC Path (Current Policy):** Stable at ~150-160 Mt\n"
                f"• **1.5°C Compatible:** Must halve to ~80 Mt by 2050\n\n"
                f"**Enablers:**\n"
                f"✓ Renewable energy (85% target by 2035)\n"
                f"✓ Electric vehicle adoption\n"
                f"✓ Green hydrogen export revenue\n"
                f"✓ Mining transition (copper sector)\n\n"
                f"Chile can achieve carbon neutrality by 2050 with ambition.")
    elif "trend" in msg_lower or "history" in msg_lower:
        return (f"📈 **Chile's 25-Year Emissions Trend (1999-2024):**\n\n"
                f"**Growth Phase (1999-2013):**\n"
                f"• +116% CO₂ growth\n"
                f"• Economic boom, mining expansion, coal-heavy power\n\n"
                f"**Stabilization Phase (2013-2024):**\n"
                f"• Flat trend (~130-139 Mt)\n"
                f"• Renewable energy breakthrough\n"
                f"• Policy interventions (carbon tax, coal phase-out)\n\n"
                f"**Key Inflection Points:**\n"
                f"• 2013: Peak emissions (132 Mt)\n"
                f"• 2017: Carbon tax introduced\n"
                f"• 2021: Energy transition law, renewed NDC\n"
                f"• 2024: Continuing growth but slowing\n\n"
                f"**Interpretation:** Chile HAS decoupled emissions from GDP growth! ✓")
    else:
        return general_open_reply(user_msg, latest)

def general_open_reply(raw_msg: str, latest) -> str:
    """Thoughtful reply for any message that did not match a climate keyword branch."""
    snippet = raw_msg.strip()
    if len(snippet) > 120:
        snippet = snippet[:117] + "…"
    return (
        f"Thanks for your message{f' — “{snippet}”' if snippet else ''}.\n\n"
        f"I'm {CHAT_ASSISTANT_NAME}, focused on Chile's climate and this dashboard's data. "
        f"Quick snapshot ({_CHILE_YR_MAX}): about {latest['annual_co2']/1e6:.1f} Mt CO₂ total, "
        f"{latest['co2_pc']:.2f} t per person (world avg ≈ 4.58 t), "
        f"~{latest['share_global']:.3f}% of global share.\n\n"
        "Ask me about emissions, renewables, NDC targets, justice, sectors, trends, GDP/HDI — "
        "or say hi; I'll always respond."
    )

# ── Report generator (shared sections + PDF; preview text only — no PDF in preview callback) ──
def build_report_sections(comp_countries, variables):
    """Build ordered list of (section_title, body_text) for preview and PDF."""
    if not variables:
        variables = ["annual_co2", "co2_pc"]
    latest = CHILE_LATEST_ROW
    earliest = CHILE_EARLIEST_ROW
    comp_str = ", ".join(comp_countries) if comp_countries else "India, World, United States"

    sections = []
    sections.append(("Country Profile", f"""
Chile is a narrow South American republic stretching 4,300 km along the Pacific coast,
bounded by the Andes to the east and the Pacific Ocean to the west. Its population
in {_CHILE_YR_MAX} stands at {latest['population']/1e6:.1f} million, with a GDP per capita of
${latest['gdp_pc']:,.0f} (current USD) — making it one of Latin America's most
prosperous economies. Chile's Human Development Index of {latest['hdi']:.3f} ({_CHILE_YR_MAX})
places it in the Very High Human Development category (UNDP).
""".strip()))

    if "annual_co2" in variables:
        sections.append(("Emissions Trend Analysis", f"""
Total Annual CO2 Emissions
Chile's annual CO2 emissions grew from {earliest['annual_co2']/1e6:.2f} Mt in {_CHILE_YR_MIN}
to {latest['annual_co2']/1e6:.2f} Mt in {_CHILE_YR_MAX} — a {((latest['annual_co2']/earliest['annual_co2'])-1)*100:.0f}%
increase over the period shown. Key drivers include economic growth (GDP+{((latest['gdp_pc']/earliest['gdp_pc'])-1)*100:.0f}%
over the same period), urbanisation, and rising energy demand.
Policy interventions — including the 2010 National Climate Change Action Plan,
the 2015 Paris Agreement commitment, and the 2017 carbon tax — have moderated the growth trajectory.
Source: Global Carbon Project (2024); Our World in Data (2024).
""".strip()))

    if "co2_pc" in variables:
        sections.append(("Per Capita CO2 Emissions", f"""
Per-capita emissions remained relatively stable between {chile['co2_pc'].min():.2f} t and
{chile['co2_pc'].max():.2f} t throughout {_CHILE_YR_MIN}–{_CHILE_YR_MAX}, averaging {chile['co2_pc'].mean():.2f} t/person.
This sits below the global average of 4.58 t/person (Our World in Data, 2024),
indicating partial decoupling of economic growth from emissions intensity.
""".strip()))

    if "share_global" in variables:
        sections.append(("Carbon Inequality Analysis", f"""
Share of Global Emissions
Chile contributes {latest['share_global']:.3f}% of global annual CO2 —
a negligible share relative to its {latest['population']/1e6:.0f} million population.
Comparison countries selected for this report: {comp_str}.

Historical Responsibility
Chile's cumulative CO2 since 1750 is approximately 2.5 Gt (0.15% of global cumulative
total of ~1,650 Gt). The principle of common but differentiated responsibilities (CBDR)
implies that Chile bears minimal historical liability for the climate crisis.
""".strip()))

    if "cumulative_co2" in variables and "cumulative_co2" in latest.index:
        sections.append(("Cumulative CO₂ (Territorial)", f"""
Chile's cumulative territorial CO₂ (dataset window) through {_CHILE_YR_MAX} is approximately {latest['cumulative_co2']/1e9:.2f} Gt.
This figure contextualises long-term responsibility alongside annual flows. Source: Global Carbon Project / Our World in Data.
""".strip()))

    if "co2_energy" in variables and "co2_energy" in latest.index and pd.notna(latest.get("co2_energy")):
        sections.append(("CO₂ per Unit Energy", f"""
CO₂ emitted per unit of energy (kg CO₂ per kWh) is a key decarbonisation indicator for Chile.
Latest available value in the dashboard dataset: {latest['co2_energy']:.3f} kg/kWh (see Source Analysis tab for trends).
""".strip()))

    if "gdp_pc" in variables:
        sections.append(("Economic Context (GDP per Capita)", f"""
GDP per capita reached ${latest['gdp_pc']:,.0f} in {_CHILE_YR_MAX} (current USD, World Bank WDI).
Economic growth has outpaced proportional emissions growth in several sub-periods, consistent with structural change and renewable deployment.
""".strip()))

    if "hdi" in variables:
        sections.append(("Human Development", f"""
Human Development Index ({_CHILE_YR_MAX}): {latest['hdi']:.3f} — Very High Human Development (UNDP).
High HDI alongside moderate per-capita emissions supports an argument for climate leadership capacity.
""".strip()))

    if "sectors" in variables:
        sec_keys = ["coal","oil","gas","cement","flaring"]
        lines = []
        tot = sum(float(latest.get(s, 0) or 0) for s in sec_keys)
        for s in sec_keys:
            v = float(latest.get(s, 0) or 0)
            pct = (v / tot * 100) if tot > 0 else 0
            lines.append(f"• {s.capitalize()}: {v/1e6:.2f} Mt ({pct:.1f}% of sector total)")
        sections.append(("Sectoral Emissions (Latest Year)", "\n".join(lines) + "\n\nSource: Global Carbon Project sectoral breakdown (Chile)."))

    if "projections" in variables:
        sections.append(("Emissions Outlook (Illustrative)", f"""
Projections in the dashboard combine historical trends with scenario narratives (BAU, NDC-style, net-zero pathways).
{_CHILE_YR_MAX} baseline annual CO₂: {latest['annual_co2']/1e6:.1f} Mt. See Projections tab for charts and assumptions.
""".strip()))

    if "justice" in variables:
        sections.append(("Climate Justice Reflection", f"""
Chile occupies a morally complex position in the global climate architecture.
With just 0.20% of global annual CO2 emissions and 0.15% of cumulative
historical emissions, Chile is a small contributor to the crisis it disproportionately
suffers from — through glacial retreat in Patagonia, desertification in the Atacama,
and increased wildfire frequency.

Yet Chile's GDP per capita of ${latest['gdp_pc']:,.0f} (2024) confers both the economic
capacity and the moral obligation to act ambitiously. Chile has already shown leadership:
it was among the first Latin American nations to implement a carbon tax (2017, USD 5/tonne),
and its NDC commits to carbon neutrality by 2050.

Chile's greatest leverage lies in its renewable energy endowment.
The Atacama Desert offers some of the world's highest solar irradiance,
already making Chile's northern grid a global benchmark.
If Chile aggressively scales this potential and exports green hydrogen,
it could become a net-zero enabler far beyond its own borders.

Data conclusion: Chile is a low emitter with high development capacity —
it should lead by example, advocate for adaptation finance, and champion ambitious
South American climate coalitions.
""".strip()))

    sections.append(("Data Sources (APA 7th Edition)", """
- Global Carbon Project. (2024). Global Carbon Budget 2024. https://globalcarbonproject.org
- Ritchie, H., Roser, M., & Rosado, P. (2024). CO2 and greenhouse gas emissions. Our World in Data. https://ourworldindata.org/co2-emissions
- World Bank. (2024). World Development Indicators. https://data.worldbank.org
- United Nations Development Programme. (2024). Human Development Report 2024. https://hdr.undp.org
- IPCC. (2018). Global Warming of 1.5°C (SR1.5). https://www.ipcc.ch/sr15/
- Chile. (2021). Chile's Nationally Determined Contribution (NDC) 2021. Ministry of Environment.
""".strip()))
    return sections

def build_report_pdf_bytes(sections, name, enrol, today):
    from xml.sax.saxutils import escape
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "RepTitle", parent=styles["Title"], fontSize=16, leading=20,
        textColor="#1a1a1a", spaceAfter=12, alignment=1,
    )
    heading_style = ParagraphStyle(
        "RepH", parent=styles["Heading1"], fontSize=12, leading=16,
        textColor="#2C3E50", spaceAfter=6, spaceBefore=10,
    )
    normal_style = ParagraphStyle(
        "RepN", parent=styles["Normal"], fontSize=10, leading=14,
        textColor="#1a1a1a", alignment=0,
    )

    story = []
    story.append(Paragraph(escape("Chile — Climate Change & Emissions Analysis"), title_style))
    story.append(Paragraph(
        "Climate Change, Sustainability and Development<br/>"
        "BS in Analytics and Sustainability Studies (2024–28)<br/>"
        "Tata Institute of Social Sciences, Mumbai",
        normal_style))
    story.append(Spacer(1, 10))
    safe_name = escape(str(name or "Student"))
    safe_enrol = escape(str(enrol or ""))
    safe_date = escape(str(today))
    story.append(Paragraph(
        f"<b>Author:</b> {safe_name}<br/>"
        f"<b>Enrolment:</b> {safe_enrol}<br/>"
        f"<b>Country focus:</b> Chile<br/>"
        f"<b>Date:</b> {safe_date}",
        normal_style))
    story.append(Spacer(1, 16))

    for sec_title, content in sections:
        story.append(Paragraph(f"<b>{escape(sec_title)}</b>", heading_style))
        for block in content.split("\n\n"):
            b = block.strip()
            if not b:
                continue
            inner = "<br/>".join(escape(line) for line in b.split("\n"))
            story.append(Paragraph(inner, normal_style))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 8))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf

@callback(
    Output("report-preview","children"),
    Input("gen-report-btn","n_clicks"),
    [State("rep-countries","value"), State("rep-vars","value"),
     State("rep-name","value"), State("rep-enrol","value")],
    prevent_initial_call=True)
def generate_report_preview(n, comp_countries, variables, name, enrol):
    if not n:
        return dash.no_update
    sections = build_report_sections(comp_countries, variables)
    preview = "\n\n".join(
        f"{title}\n{'-' * min(len(title), 72)}\n{body}" for title, body in sections
    )
    meta = f"Author: {name or '—'}  |  Enrolment: {enrol or '—'}\n\n"
    return meta + preview

@callback(
    Output("download-report","data"),
    Input("download-report-btn","n_clicks"),
    [State("rep-countries","value"), State("rep-vars","value"),
     State("rep-name","value"), State("rep-enrol","value")],
    prevent_initial_call=True)
def download_report_pdf(n, comp_countries, variables, name, enrol):
    if not n:
        return dash.no_update
    today = datetime.date.today().strftime("%B %d, %Y")
    sections = build_report_sections(comp_countries, variables)
    pdf_bytes = build_report_pdf_bytes(sections, name, enrol, today)
    base = re.sub(r"[^\w\-\s]", "", (name or "Student").strip())[:60].replace(" ", "_") or "Student"
    filename = f"{base}_Chile_Climate_Report.pdf"
    try:
        return dcc.send_bytes(pdf_bytes, filename=filename)
    except AttributeError:
        return dict(content=pdf_bytes, filename=filename, type="application/pdf")

# ══════════════════════════════════════════════════════════════════════
#  RUN
# ══════════════════════════════════════════════════════════════════════
print("Dash app initialized successfully")
print("Server object created successfully")
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(debug=False, host="0.0.0.0", port=port)
