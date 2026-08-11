"""
ETL - Transform
Limpia y normaliza el dataset de la Encuesta de Sueldos IT Argentina (Sysarmy 2026.1).

Input:  data/raw/sueldos_2026_1.csv   (dataset "CLEAN" publicado por openqube/Sysarmy)
Output: data/processed/sueldos_clean.csv
"""

import pandas as pd
from pathlib import Path

RAW_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "sueldos_2026_1.csv"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "sueldos_clean.csv"

# El archivo exportado desde Google Sheets trae 9 filas de encabezado/nota legal
# antes de la fila real de columnas.
HEADER_SKIPROWS = 9

# Columnas del dataset original que nos interesan, con su nuevo nombre en español simple.
COLUMN_MAP = {
    "donde_estas_trabajando": "provincia",
    "dedicacion": "dedicacion",
    "tipo_de_contrato": "tipo_contrato",
    "ultimo_salario_mensual_o_retiro_bruto_en_pesos_argentinos": "salario_bruto_ars",
    "ultimo_salario_mensual_o_retiro_neto_en_pesos_argentinos": "salario_neto_ars",
    "sueldo_dolarizado": "sueldo_dolarizado",
    "seniority": "seniority",
    "trabajo_de": "rol",
    "anos_de_experiencia": "anios_experiencia",
    "modalidad_de_trabajo": "modalidad",
    "genero": "genero",
    "cantidad_de_personas_en_tu_organizacion": "tamanio_empresa",
    "lenguajes_de_programacion_o_tecnologias_que_utilices_en_tu_puesto_actual": "lenguajes",
    "que_tan_conforme_estas_con_tus_ingresos_laborales": "conformidad_ingresos",
    "estas_buscando_trabajo": "buscando_trabajo",
}

# Orden esperado (de menor a mayor) para las categorías de seniority.
SENIORITY_ORDER = ["Junior", "Semi-Senior", "Senior"]


def load_raw(path: Path = RAW_PATH) -> pd.DataFrame:
    return pd.read_csv(path, skiprows=HEADER_SKIPROWS)


def select_and_rename(df: pd.DataFrame) -> pd.DataFrame:
    df = df[list(COLUMN_MAP.keys())].copy()
    df = df.rename(columns=COLUMN_MAP)
    return df


def clean_salary(df: pd.DataFrame) -> pd.DataFrame:
    # Descartamos filas sin salario bruto (la variable principal de análisis).
    df = df.dropna(subset=["salario_bruto_ars"])

    # Recortamos outliers extremos con el criterio de percentiles 1 y 99,
    # en vez de un umbral fijo, para no perder respuestas válidas de sueldos
    # muy altos o muy bajos que sí ocurren en el mercado IT.
    low, high = df["salario_bruto_ars"].quantile([0.01, 0.99])
    df = df[(df["salario_bruto_ars"] >= low) & (df["salario_bruto_ars"] <= high)]

    return df


def clean_categoricals(df: pd.DataFrame) -> pd.DataFrame:
    df["seniority"] = pd.Categorical(
        df["seniority"], categories=SENIORITY_ORDER, ordered=True
    )
    df["genero"] = df["genero"].fillna("Prefiero no decir")
    df["provincia"] = df["provincia"].str.strip()
    df["rol"] = df["rol"].str.strip()
    return df


def add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    # Primer lenguaje/tecnología mencionado, útil para agrupar sin explotar filas.
    df["lenguaje_principal"] = (
        df["lenguajes"].fillna("No especifica").str.split(",").str[0].str.strip()
    )

    bins = [-1, 2, 5, 10, 100]
    labels = ["0-2 años", "3-5 años", "6-10 años", "10+ años"]
    df["experiencia_bucket"] = pd.cut(df["anios_experiencia"], bins=bins, labels=labels)

    return df


def run() -> pd.DataFrame:
    df = load_raw()
    df = select_and_rename(df)
    df = clean_salary(df)
    df = clean_categoricals(df)
    df = add_derived_columns(df)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)
    print(f"Filas finales: {len(df)}")
    print(f"Guardado en: {OUT_PATH}")
    return df


if __name__ == "__main__":
    run()
