"""
Dashboard interactivo — Sueldos IT Argentina (Sysarmy 2026.1)

Corre con:
    streamlit run app/streamlit_app.py
"""

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "sueldos.db"

st.set_page_config(page_title="Sueldos IT Argentina 2026", layout="wide")


@st.cache_data
def load_data() -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql("SELECT * FROM salarios", conn)
    df["seniority"] = pd.Categorical(
        df["seniority"], categories=["Junior", "Semi-Senior", "Senior"], ordered=True
    )
    return df


df = load_data()

st.title("Sueldos IT Argentina — Encuesta Sysarmy 2026.1")
st.caption(
    "Fuente: encuesta de sueldos IT de Sysarmy / openqube.io. "
    f"{len(df):,} respuestas analizadas tras la limpieza de datos.".replace(",", ".")
)

# --- Filtros ---
with st.sidebar:
    st.header("Filtros")

    seniorities = st.multiselect(
        "Seniority", options=list(df["seniority"].cat.categories), default=list(df["seniority"].cat.categories)
    )
    roles = st.multiselect(
        "Rol", options=sorted(df["rol"].dropna().unique()), default=[]
    )
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

# --- Métricas principales ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Respuestas", f"{len(filtered):,}".replace(",", "."))
col2.metric("Sueldo mediano", f"$ {filtered['salario_bruto_ars'].median():,.0f}".replace(",", "."))
col3.metric("Sueldo promedio", f"$ {filtered['salario_bruto_ars'].mean():,.0f}".replace(",", "."))
col4.metric("% remoto", f"{(filtered['modalidad'] == '100% remoto').mean() * 100:.0f}%")

st.divider()

# --- Sueldo por seniority ---
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
    fig2 = px.bar(
        g, orientation="h",
        labels={"value": "Sueldo mediano (ARS)", "rol": "Rol"},
    )
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
