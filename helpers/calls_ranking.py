from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Iterable

import pandas as pd

from helpers.agent_mapping import normalize_agent_key

ATTENDED_STATUSES = {
    "success",
    "resolved",
    "resuelto",
    "atendido",
}


def _read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin1")


def count_attended_calls(
    df: pd.DataFrame,
    start: date,
    end: date,
    date_col: str,
    agent_cols: Iterable[str],
    status_col: str = "Estado",
) -> dict[str, int]:
    if df is None or df.empty or date_col not in df.columns:
        return {}

    dates = pd.to_datetime(df[date_col], errors="coerce").dt.date
    mask = dates.notna() & (dates >= start) & (dates <= end)
    filtered = df.loc[mask].copy()
    if filtered.empty:
        return {}

    if status_col in filtered.columns:
        status = filtered[status_col].astype(str).str.strip().str.lower()
        filtered = filtered[status.isin(ATTENDED_STATUSES)]
        if filtered.empty:
            return {}

    agent_col = next((col for col in agent_cols if col in filtered.columns), None)
    if agent_col is None:
        return {}

    normalized = filtered[agent_col].astype(str).str.strip().map(normalize_agent_key)
    normalized = normalized[normalized != ""]
    if normalized.empty:
        return {}

    counts = normalized.value_counts()
    return {str(key): int(value) for key, value in counts.items()}


def load_attended_calls_by_agent(
    start: date,
    end: date,
    data_dir: Path | None = None,
) -> dict[str, int]:
    base_dir = data_dir or (Path(__file__).resolve().parents[1] / "data")

    sources = (
        (base_dir / "detalle_llamadas.csv", "Fecha", ("Agente2", "Agente")),
        (base_dir / "detalle_llamadas_ccc.csv", "Hora Inicio", ("Agente", "Nombre Agente")),
    )

    totals: dict[str, int] = {}
    for path, date_col, agent_cols in sources:
        if not path.exists():
            continue
        df = _read_csv(path)
        counts = count_attended_calls(df, start, end, date_col=date_col, agent_cols=agent_cols)
        for agent_key, value in counts.items():
            totals[agent_key] = totals.get(agent_key, 0) + value

    return totals
