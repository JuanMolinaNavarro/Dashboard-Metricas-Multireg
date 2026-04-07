from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st
from helpers import api_client
from helpers.utils import month_range_picker

CHATBOT_TEAM = "CHATBOT"
TOTAL_LABEL = "Total"

ALL_METRICS = [
    "Volumen",
    "Abandonados",
    "FRT promedio (min)",
    "Duración promedio (min)",
    "% Resueltos",
    "% Cerrados mismo día",
]

# Metrics where a lower value is better (Variación green when negative)
LOWER_IS_BETTER = {"Abandonados", "FRT promedio (min)", "Duración promedio (min)"}

# Display format type per metric
METRIC_FORMAT = {
    "Volumen": "integer",
    "Abandonados": "integer",
    "FRT promedio (min)": "decimal",
    "Duración promedio (min)": "decimal",
    "% Resueltos": "percent",
    "% Cerrados mismo día": "percent",
}

METRIC_DESCRIPTIONS = {
    "Volumen": "Conversaciones nuevas abiertas en el período.",
    "Abandonados": "Casos sin respuesta del agente por ≥24 h. Objetivo: mantener cerca de cero.",
    "FRT promedio (min)": "Tiempo promedio entre la apertura del caso y la primera respuesta del agente.",
    "Duración promedio (min)": "Duración promedio de las conversaciones cerradas.",
    "% Resueltos": "Porcentaje de casos abiertos que fueron cerrados.",
    "% Cerrados mismo día": "Porcentaje de casos abiertos y cerrados en el mismo día.",
}

MONTH_LONG = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}
MONTH_SHORT = {
    1: "Ene",
    2: "Feb",
    3: "Mar",
    4: "Abr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Ago",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dic",
}


# ── State ─────────────────────────────────────────────────────────────────────


def _init_state() -> None:
    if "comp_n_periods" not in st.session_state:
        st.session_state["comp_n_periods"] = 2


# ── Data helpers ──────────────────────────────────────────────────────────────


def _to_list(data) -> list:
    if isinstance(data, list):
        return data
    return []


def _df_clean(raw) -> pd.DataFrame:
    rows = _to_list(raw)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    if "team_name" not in df.columns:
        return pd.DataFrame()
    return df[df["team_name"].notna() & (df["team_name"] != CHATBOT_TEAM)].copy()


def _aggregate_period(start: date, end: date) -> dict[str, dict[str, float | None]]:
    """Return {metric: {team_name: value, 'Total': value}} for the given date range."""
    result: dict[str, dict[str, float | None]] = {}

    # Volumen
    df = _df_clean(
        api_client.get_json(
            "/metrics/equipos", {"desde": str(start), "hasta": str(end)}
        )
    )
    if not df.empty and "conversaciones_entrantes" in df.columns:
        agg = df.groupby("team_name")["conversaciones_entrantes"].sum()
        d: dict[str, float | None] = {k: float(v) for k, v in agg.items()}
        d[TOTAL_LABEL] = float(agg.sum())
        result["Volumen"] = d

    # Abandonados
    df = _df_clean(api_client.casos_abandonados_historico(start, end))
    if not df.empty and "casos_abandonados_24h" in df.columns:
        agg = df.groupby("team_name")["casos_abandonados_24h"].sum()
        d = {k: float(v) for k, v in agg.items()}
        d[TOTAL_LABEL] = float(agg.sum())
        result["Abandonados"] = d

    # FRT promedio (min) — weighted average
    df = _df_clean(api_client.frt_tiempo_primera_respuesta(start, end))
    if (
        not df.empty
        and "avg_frt_seconds" in df.columns
        and "casos_respondidos" in df.columns
    ):
        df = df[df["avg_frt_seconds"] > 0].copy()
        if not df.empty:
            df["_w"] = df["avg_frt_seconds"] * df["casos_respondidos"]
            agg = df.groupby("team_name").agg(
                _w=("_w", "sum"), _n=("casos_respondidos", "sum")
            )
            d = {}
            for team, row in agg.iterrows():
                d[team] = (
                    round(row["_w"] / row["_n"] / 60, 1) if row["_n"] > 0 else None
                )
            total_w = float(df["_w"].sum())
            total_n = float(df["casos_respondidos"].sum())
            d[TOTAL_LABEL] = round(total_w / total_n / 60, 1) if total_n > 0 else None
            result["FRT promedio (min)"] = d

    # Duración promedio (min) — weighted average
    df = _df_clean(api_client.duracion_promedio(start, end))
    if (
        not df.empty
        and "avg_duration_seconds" in df.columns
        and "conversaciones_cerradas" in df.columns
    ):
        df = df[df["avg_duration_seconds"] > 0].copy()
        if not df.empty:
            df["_w"] = df["avg_duration_seconds"] * df["conversaciones_cerradas"]
            agg = df.groupby("team_name").agg(
                _w=("_w", "sum"), _n=("conversaciones_cerradas", "sum")
            )
            d = {}
            for team, row in agg.iterrows():
                d[team] = (
                    round(row["_w"] / row["_n"] / 60, 1) if row["_n"] > 0 else None
                )
            total_w = float(df["_w"].sum())
            total_n = float(df["conversaciones_cerradas"].sum())
            d[TOTAL_LABEL] = round(total_w / total_n / 60, 1) if total_n > 0 else None
            result["Duración promedio (min)"] = d

    # % Resueltos
    df = _df_clean(api_client.casos_resueltos(start, end))
    if (
        not df.empty
        and "casos_resueltos" in df.columns
        and "casos_abiertos" in df.columns
    ):
        agg = df.groupby("team_name").agg(
            res=("casos_resueltos", "sum"), ab=("casos_abiertos", "sum")
        )
        d = {}
        for team, row in agg.iterrows():
            d[team] = (
                round(100.0 * row["res"] / row["ab"], 1) if row["ab"] > 0 else None
            )
        total_res = float(df["casos_resueltos"].sum())
        total_ab = float(df["casos_abiertos"].sum())
        d[TOTAL_LABEL] = (
            round(100.0 * total_res / total_ab, 1) if total_ab > 0 else None
        )
        result["% Resueltos"] = d

    # % Cerrados mismo día
    df = _df_clean(api_client.casos_cerrados_mismo_dia(start, end))
    if (
        not df.empty
        and "casos_cerrados_mismo_dia" in df.columns
        and "casos_abiertos" in df.columns
    ):
        agg = df.groupby("team_name").agg(
            cerr=("casos_cerrados_mismo_dia", "sum"), ab=("casos_abiertos", "sum")
        )
        d = {}
        for team, row in agg.iterrows():
            d[team] = (
                round(100.0 * row["cerr"] / row["ab"], 1) if row["ab"] > 0 else None
            )
        total_cerr = float(df["casos_cerrados_mismo_dia"].sum())
        total_ab = float(df["casos_abiertos"].sum())
        d[TOTAL_LABEL] = (
            round(100.0 * total_cerr / total_ab, 1) if total_ab > 0 else None
        )
        result["% Cerrados mismo día"] = d

    return result


def _get_all_teams(periods_agg: list[dict]) -> list[str]:
    teams: set[str] = set()
    for period_data in periods_agg:
        for metric_data in period_data.values():
            teams.update(k for k in metric_data if k != TOTAL_LABEL)
    return sorted(teams)


# ── Table rendering ───────────────────────────────────────────────────────────


def _fmt_value(v, fmt: str) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    if fmt == "integer":
        return f"{v:.0f}"
    if fmt == "percent":
        return f"{v:.1f}%"
    return f"{v:.1f}"


def _fmt_variacion(v, fmt: str) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    sign = "+" if v >= 0 else ""
    if fmt == "integer":
        return f"{sign}{v:.0f}"
    if fmt == "percent":
        return f"{sign}{v:.1f}%"
    return f"{sign}{v:.1f}"


def _render_metric_table(
    metric: str,
    period_labels: list[str],
    periods_agg: list[dict],
    empresas_to_show: list[str],
) -> None:
    st.markdown(f"#### {metric}")
    st.markdown(
        f"<p class='desc-text'>{METRIC_DESCRIPTIONS[metric]}</p>",
        unsafe_allow_html=True,
    )

    # Build DataFrame
    rows = []
    for empresa in empresas_to_show:
        row: dict = {"Empresa": empresa}
        for label, period_data in zip(period_labels, periods_agg):
            row[label] = period_data.get(metric, {}).get(empresa)
        rows.append(row)

    df = pd.DataFrame(rows)

    # Variación: numeric delta between last two periods
    has_variacion = len(period_labels) >= 2
    if has_variacion:
        last = period_labels[-1]
        prev = period_labels[-2]
        df["Variación"] = df[last] - df[prev]

    if df.empty:
        st.caption("Sin datos para este período.")
        return

    fmt = METRIC_FORMAT[metric]
    lower = metric in LOWER_IS_BETTER

    # ── Value formatting ───────────────────────────────────────────────────
    fmt_dict = {col: lambda v, f=fmt: _fmt_value(v, f) for col in period_labels}
    if has_variacion:
        fmt_dict["Variación"] = lambda v, f=fmt: _fmt_variacion(v, f)

    styler = df.style.format(fmt_dict, na_rep="—")

    # ── Color: best / worst period per empresa row (green bg / red bg) ────
    if len(period_labels) >= 2:

        def _highlight_periods(row: pd.Series) -> pd.Series:
            styles = pd.Series("", index=row.index)
            is_total = row.get("Empresa") == TOTAL_LABEL
            if is_total:
                return styles
            valid = {
                c: row[c]
                for c in period_labels
                if c in row.index
                and row[c] is not None
                and not (isinstance(row[c], float) and pd.isna(row[c]))
            }
            if len(valid) < 2:
                return styles
            best = min(valid, key=valid.get) if lower else max(valid, key=valid.get)
            worst = max(valid, key=valid.get) if lower else min(valid, key=valid.get)
            if best != worst:
                styles[best] = "background-color: rgba(22, 163, 74, 0.13)"
                styles[worst] = "background-color: rgba(220, 38, 38, 0.09)"
            return styles

        styler = styler.apply(_highlight_periods, axis=1)

    # ── Color: Variación text (green = improvement, red = worsening) ──────
    if has_variacion:

        def _color_variacion(v) -> str:
            if v is None or (isinstance(v, float) and pd.isna(v)) or v == 0:
                return ""
            if lower:
                return (
                    "color: #16a34a; font-weight: 600"
                    if v < 0
                    else "color: #dc2626; font-weight: 600"
                )
            return (
                "color: #16a34a; font-weight: 600"
                if v > 0
                else "color: #dc2626; font-weight: 600"
            )

        styler = styler.applymap(_color_variacion, subset=["Variación"])

    # ── Total row: bold + subtle top border ───────────────────────────────
    def _style_total(row: pd.Series) -> list[str]:
        if row.get("Empresa") == TOTAL_LABEL:
            return ["font-weight: 700; border-top: 1px solid #cbd5e1"] * len(row)
        return [""] * len(row)

    styler = styler.apply(_style_total, axis=1)

    # ── Empresa column: bold ──────────────────────────────────────────────
    styler = styler.applymap(lambda _: "font-weight: 600", subset=["Empresa"])

    st.dataframe(styler, use_container_width=True, hide_index=True)


# ── Main render ───────────────────────────────────────────────────────────────


def render() -> None:
    st.header("Comparativas")
    _init_state()

    n = st.session_state["comp_n_periods"]

    # ── Period pickers ────────────────────────────────────────────────────
    st.markdown(
        "<p style='font-size:13px; color:#9ca3af; margin-bottom:6px;'>Selecciona los períodos a comparar</p>",
        unsafe_allow_html=True,
    )

    period_cols = st.columns(n, gap="small")
    periods: list[tuple[str, date, date]] = []

    # Track labels to handle duplicate month selections
    used_labels: dict[str, int] = {}
    for i in range(n):
        with period_cols[i]:
            with st.container(border=True):
                st.caption(f"Período {i + 1}")
                start, end = month_range_picker(f"comp_p{i}", default_offset=n - 1 - i)
                base = f"{MONTH_LONG[start.month]} {start.year}"
                count = used_labels.get(base, 0) + 1
                used_labels[base] = count
                label = base if count == 1 else f"{base} ({count})"
                periods.append((label, start, end))

    # Buttons sit below the period frames
    btn_cols = st.columns([1, 1, 5], gap="small")
    with btn_cols[0]:
        if n < 6:
            if st.button(
                "Agregar nuevo período", key="comp_add", use_container_width=True
            ):
                st.session_state["comp_n_periods"] += 1
                st.rerun()
    with btn_cols[1]:
        if n > 1:
            if st.button(
                "Quitar último período", key="comp_remove", use_container_width=True
            ):
                st.session_state["comp_n_periods"] -= 1
                st.rerun()

    # ── Filters ───────────────────────────────────────────────────────────
    with st.container(border=True):
        empresas_placeholder = st.empty()
        show_total = st.checkbox("Total", value=True, key="comp_show_total")
    # ── Load data ─────────────────────────────────────────────────────────
    with st.spinner("Cargando datos..."):
        periods_agg = [_aggregate_period(start, end) for _, start, end in periods]

    all_teams = _get_all_teams(periods_agg)
    if not all_teams:
        st.info("No hay datos para los períodos seleccionados.")
        return

    # Now populate the empresa multiselect with real options
    with empresas_placeholder:
        selected_empresas = st.multiselect(
            "Empresas",
            options=all_teams,
            default=all_teams,
            key="comp_empresas",
        )

    if not selected_empresas and not show_total:
        st.warning("Selecciona al menos una empresa o activa el Total.")
        return

    empresas_to_show = list(selected_empresas) + ([TOTAL_LABEL] if show_total else [])
    period_labels = [lbl for lbl, _, _ in periods]

    # ── Metric tables in 2-column grid (all metrics, always) ─────────────
    st.markdown("---")
    for row_start in range(0, len(ALL_METRICS), 2):
        chunk = ALL_METRICS[row_start : row_start + 2]
        grid = st.columns(len(chunk), gap="large")
        for col_i, metric in enumerate(chunk):
            with grid[col_i]:
                _render_metric_table(
                    metric, period_labels, periods_agg, empresas_to_show
                )
        st.write("")  # vertical gap between grid rows
