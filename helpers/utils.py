from __future__ import annotations

import calendar
from datetime import date, timedelta
from typing import Optional, Tuple

import streamlit as st
from helpers.agent_mapping import resolve_agent_name


def quick_range(days: int) -> Tuple[date, date]:
    end = date.today()
    start = end - timedelta(days=days)
    return start, end


def current_month_range() -> Tuple[date, date]:
    today = date.today()
    return today.replace(day=1), today


def prev_month_range() -> Tuple[date, date]:
    today = date.today()
    last_day_prev = today.replace(day=1) - timedelta(days=1)
    return last_day_prev.replace(day=1), last_day_prev


_MONTH_NAMES_LONG = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


def month_range_picker(key: str, default_offset: int = 0) -> Tuple[date, date]:
    """Render year + month selectboxes and return (first_day, last_day) of the selected month.

    Args:
        key: Unique key prefix for the Streamlit widgets.
        default_offset: How many months back from today to pre-select (0 = current month).
    """
    today = date.today()
    def_year = today.year
    def_month = today.month - default_offset
    while def_month < 1:
        def_month += 12
        def_year -= 1

    year_options = list(range(today.year - 2, today.year + 1))
    if def_year not in year_options:
        def_year = year_options[0]

    sel_year = st.selectbox(
        "Año",
        options=year_options,
        index=year_options.index(def_year),
        key=f"{key}_year",
    )
    sel_month = st.selectbox(
        "Mes",
        options=list(range(1, 13)),
        format_func=lambda m: _MONTH_NAMES_LONG[m],
        index=def_month - 1,
        key=f"{key}_month",
    )

    last_day = calendar.monthrange(sel_year, sel_month)[1]
    return date(sel_year, sel_month, 1), date(sel_year, sel_month, last_day)


def date_range_picker(key: str, default: Optional[Tuple[date, date]] = None) -> Tuple[date, date]:
    if default is None:
        default = quick_range(7)
    start, end = default
    picked = st.date_input("Rango de fechas", value=(start, end), key=key, max_value=date.today())
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


def render_description(text: str) -> None:
    st.markdown(f"<div class=\"desc-text\">{text}</div>", unsafe_allow_html=True)


def _map_agent_cell(value):
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text or "@" not in text:
        return value
    return resolve_agent_name(text)


def prepare_table(df):
    if df is None or df.empty:
        return df
    df = df.copy()
    for col in ("agent_email", "Agente"):
        if col in df.columns:
            df[col] = df[col].apply(_map_agent_cell)
    numeric_cols = df.select_dtypes(include="number").columns
    if len(numeric_cols) > 0:
        df[numeric_cols] = df[numeric_cols].round(2)
    df.index = range(1, len(df) + 1)
    return df
