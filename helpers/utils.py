from __future__ import annotations

from datetime import date, timedelta
from typing import Optional, Tuple

import streamlit as st


def quick_range(days: int) -> Tuple[date, date]:
    end = date.today()
    start = end - timedelta(days=days)
    return start, end


def date_range_picker(key: str, default: Optional[Tuple[date, date]] = None) -> Tuple[date, date]:
    if default is None:
        default = quick_range(7)
    start, end = default
    picked = st.date_input("Rango de fechas", value=(start, end), key=key)
    if isinstance(picked, tuple) and len(picked) == 2:
        return picked[0], picked[1]
    return start, end


def exclude_agent_rows(df, excluded_email: str):
    if df is None or df.empty:
        return df
    for col in ("agent_email", "Agente"):
        if col in df.columns:
            df = df[df[col] != excluded_email]
    return df


def format_seconds(value) -> str:
    if value is None:
        return "0s"
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return str(value)
    if seconds < 120:
        return f"{seconds:.0f} seg"
    if seconds <= 7200:
        minutes = seconds / 60
        return f"{minutes:.2f} min"
    hours = seconds / 3600
    return f"{hours:.2f} hs"


def info_icon(text: str) -> str:
    safe_text = text.replace('"', "&quot;")
    return (
        f'<span class="info-icon" data-tooltip="{safe_text}" style="cursor: help; margin-left: 6px; display: inline-flex; '
        'align-items: center;">'
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
        'xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
        '<circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>'
        '<path d="M12 16v-5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'
        '<circle cx="12" cy="8" r="1" fill="currentColor"/>'
        "</svg></span>"
    )


def prepare_table(df):
    if df is None or df.empty:
        return df
    df = df.copy()
    numeric_cols = df.select_dtypes(include="number").columns
    if len(numeric_cols) > 0:
        df[numeric_cols] = df[numeric_cols].round(2)
    df.index = range(1, len(df) + 1)
    return df
