"""
Dashboard interactivo — Sueldos IT Argentina (Sysarmy 2026.1)

Dos vistas:
1. Foto actual: análisis de la última edición (2026.1) con filtros interactivos.
2. Evolución histórica: series 2020-2026 (sueldo real, género, conformidad),
   construidas a partir de los datos consolidados que publica openqube.

Corre con:
    streamlit run app/streamlit_app.py
"""

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
CLEAN_CSV_PATH = BASE_DIR / "data" / "processed" / "sueldos_clean.csv"
HIST_DIR = BASE_DIR / "data" / "processed"

st.set_page_config(page_title="Sueldos IT Argentina 2026", layout="wide")


@st.cache_data
def load_data() -> pd.DataFrame:
    """Carga el dataset limpio y lo pasa por SQLite (en memoria) antes de
    graficarlo, para mantener la consulta vía SQL como parte del pipeline.

    Nota: no dependemos de un archivo .db persistido en el repo (los binarios
    quedan afuera del control de versiones vía .gitignore); la base se arma
    al vuelo a partir de data/processed/sueldos_clean.csv, así funciona igual
    corriendo local o desplegado en Streamlit Cloud.
    """
    raw = pd.read_csv(CLEAN_CSV_PATH)
    with sqlite3.connect(":memory:") as conn:
        raw.to_sql("salarios", conn, index=False)
        df = pd.read_sql("SELECT * FROM salarios", conn)
    df["seniority"] = pd.Categorical(
        df["seniority"], categories=["Junior", "Semi-Senior", "Senior"], ordered=True
    )
    return df


@st.cache_data
def load_historico() -> dict:
    return {
        "salario": pd.read_csv(HIST_DIR / "historico_salario_mediano.csv", parse_dates=["date"]),
        "genero_pct": pd.read_csv(HIST_DIR / "historico_genero_participacion.csv", parse_dates=["date"]),
        "genero_salario": pd.read_csv(HIST_DIR / "historico_genero_salario.csv", parse_dates=["date"]),
        "conformidad": pd.read_csv(HIST_DIR / "historico_conformidad_genero.csv", parse_dates=["date"]),
    }


df = load_data()
hist = load_historico()

st.title("Sueldos IT Argentina")
st.caption("Fuente: encuesta de sueldos IT de Sysarmy, procesada y publicada por openqube.io")

tab_actual, tab_historico = st.tabs(["Foto actual (2026.1)", "Evolución histórica (2020-2026)"])

# ============================================================
# TAB 1 — Foto actual
# ============================================================
with tab_actual:
    st.caption(
        f"{len(df):,} respuestas analizadas tras la limpieza de datos.".replace(",", ".")
    )

    with st.sidebar:
        st.header("Filtros — foto actual")

        seniorities = st.multiselect(
            "Seniority", options=list(df["seniority"].cat.categories), default=list(df["seniority"].cat.categories)
        )
        roles = st.multiselect("Rol", options=sorted(df["rol"].dropna().unique()), default=[])
        modalidades = st.multiselect(
            "Modalidad de trabajo", options=sorted(df["modalidad"].dropna().unique()), default=[]
        )
        provincias = st.multiselect(
            "Provincia", options=sorted(df["provincia"].dropna().unique()), default=[]
        )

    filtered = df[df["seniority"].isin(seniorities)]
    if roles:
        filtered = filtered[filtered["rol"].isin(roles)]
    if modalidades:
        filtered = filtered[filtered["modalidad"].isin(modalidades)]
    if provincias:
        filtered = filtered[filtered["provincia"].isin(provincias)]

    if filtered.empty:
        st.warning("No hay datos para esta combinación de filtros.")
        st.stop()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Respuestas", f"{len(filtered):,}".replace(",", "."))
    col2.metric("Sueldo mediano", f"$ {filtered['salario_bruto_ars'].median():,.0f}".replace(",", "."))
    col3.metric("Sueldo promedio", f"$ {filtered['salario_bruto_ars'].mean():,.0f}".replace(",", "."))
    col4.metric("% remoto", f"{(filtered['modalidad'] == '100% remoto').mean() * 100:.0f}%")

    st.divider()

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Sueldo bruto por seniority")
        fig = px.box(
            filtered, x="seniority", y="salario_bruto_ars", color="seniority",
            category_orders={"seniority": ["Junior", "Semi-Senior", "Senior"]},
            labels={"salario_bruto_ars": "Sueldo bruto (ARS)", "seniority": "Seniority"},
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Sueldo mediano por rol")
        top_roles = filtered["rol"].value_counts().head(10).index
        g = (
            filtered[filtered["rol"].isin(top_roles)]
            .groupby("rol")["salario_bruto_ars"]
            .median()
            .sort_values()
        )
        fig2 = px.bar(g, orientation="h", labels={"value": "Sueldo mediano (ARS)", "rol": "Rol"})
        fig2.update_layout(showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    c3, c4 = st.columns(2)

    with c3:
        st.subheader("Sueldo mediano por modalidad de trabajo")
        g2 = filtered.groupby("modalidad")["salario_bruto_ars"].median().sort_values()
        fig3 = px.bar(g2, orientation="h", labels={"value": "Sueldo mediano (ARS)", "modalidad": ""})
        fig3.update_layout(showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)

    with c4:
        st.subheader("Sueldo mediano por género")
        g3 = (
            filtered.groupby("genero")["salario_bruto_ars"]
            .agg(["count", "median"])
            .query("count >= 10")
            .sort_values("median")
        )
        fig4 = px.bar(g3, y=g3.index, x="median", orientation="h", labels={"median": "Sueldo mediano (ARS)", "y": ""})
        fig4.update_layout(showlegend=False)
        st.plotly_chart(fig4, use_container_width=True)

    st.divider()

    st.subheader("Sueldo mediano por lenguaje / tecnología principal (respuestas con n >= 30)")
    lang = (
        filtered.groupby("lenguaje_principal")["salario_bruto_ars"]
        .agg(["count", "median"])
        .query("count >= 30")
        .sort_values("median", ascending=False)
        .head(15)
    )
    fig5 = px.bar(lang, x=lang.index, y="median", labels={"median": "Sueldo mediano (ARS)", "lenguaje_principal": ""})
    st.plotly_chart(fig5, use_container_width=True)

    with st.expander("Ver datos filtrados"):
        st.dataframe(filtered)

# ============================================================
# TAB 2 — Evolución histórica
# ============================================================
with tab_historico:
    st.caption(
        "Series semestrales 2020-2026, construidas a partir de los datos consolidados "
        "que publica openqube en cada edición de la encuesta. La cuarentena por COVID-19 "
        "en Argentina empezó el 20/03/2020, marcada con una línea punteada."
    )
    st.info(
        "**Por qué esta vista se enfoca en sueldo y género:** openqube solo "
        "publica pre-consolidadas 4 series históricas (sueldo mediano, "
        "participación por género, sueldo por género y conformidad por "
        "género). No existe un histórico armado de modalidad de trabajo "
        "(remoto/híbrido/presencial) para ver ese quiebre desde la "
        "cuarentena — para eso habría que procesar a mano el dataset crudo "
        "de cada una de las ~12 ediciones semestrales desde 2020.",
        icon="ℹ️",
    )

    QUARANTINE_DATE = "2020-03-20"

    # --- Sueldo real: ARS constantes + USD ---
    st.subheader("Sueldo mediano: pesos constantes vs. dólares")
    moneda = st.radio(
        "Ver en:", ["Pesos constantes (ajustado por IPC)", "Dólares oficial", "Dólares blue"],
        horizontal=True,
    )
    s = hist["salario"]
    col_map = {
        "Pesos constantes (ajustado por IPC)": ("ars_const", "Pesos argentinos constantes"),
        "Dólares oficial": ("usd_oficial", "USD oficial"),
        "Dólares blue": ("usd_blue", "USD blue"),
    }
    col, label = col_map[moneda]

    fig_s = go.Figure()
    fig_s.add_trace(go.Scatter(x=s["date"], y=s[col], mode="lines+markers", name=label))
    fig_s.add_vline(x=QUARANTINE_DATE, line_dash="dot", line_color="gray")
    fig_s.add_annotation(x=QUARANTINE_DATE, y=1.05, yref="paper", showarrow=False, text="Cuarentena")
    fig_s.update_layout(yaxis_title=label, xaxis_title="Edición de la encuesta")
    st.plotly_chart(fig_s, use_container_width=True)

    first, last = s.iloc[0], s.iloc[-1]
    variacion_real = (last["ars_const"] / first["ars_const"] - 1) * 100
    st.caption(
        f"Entre {first['date'].strftime('%b %Y')} y {last['date'].strftime('%b %Y')}, "
        f"el sueldo mediano en pesos constantes (poder adquisitivo real) varió {variacion_real:+.1f}%."
    )

    st.divider()

    # --- Género: participación ---
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Participación en la encuesta por género")
        gp = hist["genero_pct"]
        fig_gp = go.Figure()
        for genero in ["Hombre Cis", "Mujer Cis"]:
            if genero in gp.columns:
                fig_gp.add_trace(go.Scatter(x=gp["date"], y=gp[genero] * 100, mode="lines+markers", name=genero))
        fig_gp.add_vline(x=QUARANTINE_DATE, line_dash="dot", line_color="gray")
        fig_gp.update_layout(yaxis_title="% de respuestas", xaxis_title="Edición")
        st.plotly_chart(fig_gp, use_container_width=True)

    with c2:
        st.subheader("Brecha salarial de género (mediana en ARS)")
        gs = hist["genero_salario"]
        fig_gs = go.Figure()
        for genero in ["Hombre Cis", "Mujer Cis"]:
            if genero in gs.columns:
                fig_gs.add_trace(go.Scatter(x=gs["date"], y=gs[genero], mode="lines+markers", name=genero))
        fig_gs.add_vline(x=QUARANTINE_DATE, line_dash="dot", line_color="gray")
        fig_gs.update_layout(yaxis_title="Sueldo mediano (ARS nominal)", xaxis_title="Edición")
        st.plotly_chart(fig_gs, use_container_width=True)

    brecha_ini = gs.iloc[0]["Mujer Cis"] / gs.iloc[0]["Hombre Cis"]
    brecha_fin = gs.iloc[-1]["Mujer Cis"] / gs.iloc[-1]["Hombre Cis"]
    st.caption(
        f"En {gs.iloc[0]['date'].strftime('%b %Y')}, una mujer cis ganaba {brecha_ini*100:.0f} centavos "
        f"por cada peso de un hombre cis. En {gs.iloc[-1]['date'].strftime('%b %Y')}, {brecha_fin*100:.0f} centavos. "
        "La brecha prácticamente no se movió en estos 6 años."
    )

    st.divider()

    # --- Conformidad ---
    st.subheader("Conformidad promedio con los ingresos, por género")
    st.caption("Escala de 1 (poco conforme) a 4 (muy conforme).")
    c = hist["conformidad"]
    fig_c = go.Figure()
    fig_c.add_trace(go.Scatter(x=c["date"], y=c["hombre_cis"], mode="lines+markers", name="Hombre Cis"))
    fig_c.add_trace(go.Scatter(x=c["date"], y=c["mujer_cis"], mode="lines+markers", name="Mujer Cis"))
    fig_c.add_vline(x=QUARANTINE_DATE, line_dash="dot", line_color="gray")
    fig_c.update_layout(yaxis_title="Conformidad promedio (1-4)", xaxis_title="Edición")
    st.plotly_chart(fig_c, use_container_width=True)

    with st.expander("Ver datos históricos"):
        st.write("Sueldo mediano")
        st.dataframe(hist["salario"])
        st.write("Participación por género")
        st.dataframe(hist["genero_pct"])
        st.write("Sueldo por género")
        st.dataframe(hist["genero_salario"])
        st.write("Conformidad por género")
        st.dataframe(hist["conformidad"])
