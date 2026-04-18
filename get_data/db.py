from sqlalchemy import create_engine, text
import pandas as pd

CONN_STR = (
    "mssql+pyodbc://sa:SotexSolutions123!@localhost:1433/SotexHackathon"
    "?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"
)

_engine = create_engine(CONN_STR, pool_pre_ping=True)

def q(sql: str, params: dict | None = None) -> pd.DataFrame:
    """Pokreni SQL upit, vrati rezultat kao pandas DataFrame."""
    with _engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        return pd.DataFrame(result.fetchall(), columns=list(result.keys()))