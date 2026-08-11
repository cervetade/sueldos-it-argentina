"""
ETL - Load
Persiste el dataset limpio en una base SQLite, simulando la etapa de
"load" de un pipeline ETL real.

Input:  data/processed/sueldos_clean.csv
Output: data/processed/sueldos.db  (tabla: salarios)
"""

import shutil
import sqlite3
import tempfile
from pathlib import Path

import pandas as pd

CLEAN_CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "sueldos_clean.csv"
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "sueldos.db"
TABLE_NAME = "salarios"


def load_to_sqlite(csv_path: Path = CLEAN_CSV_PATH, db_path: Path = DB_PATH) -> None:
    """Construye la base SQLite.

    Nota: en algunos entornos con almacenamiento sincronizado/en red, SQLite
    puede fallar al escribir directamente ("disk I/O error") porque no
    soportan el locking de archivos que SQLite necesita. Por eso se arma la
    base primero en un directorio temporal local y luego se copia al destino
    final ya completa.
    """
    df = pd.read_csv(csv_path)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_db_path = Path(tmp_dir) / "sueldos.db"
        with sqlite3.connect(tmp_db_path) as conn:
            df.to_sql(TABLE_NAME, conn, if_exists="replace", index=False)
            count = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]

        db_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(tmp_db_path, db_path)

    print(f"{count} filas cargadas en {db_path} (tabla '{TABLE_NAME}')")


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    return sqlite3.connect(db_path)


if __name__ == "__main__":
    load_to_sqlite()
