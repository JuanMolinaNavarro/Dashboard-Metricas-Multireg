# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from helpers.utils import date_range_picker, format_seconds, prepare_table, render_description

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
REPORTE_PATH = DATA_DIR / "reporte.csv"
DETALLE_PATH = DATA_DIR / "detalle_llamadas.csv"


@st.cache_data(ttl=900)
def _read_csv(path: Path, mtime: float) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin1")


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return _read_csv(path, path.stat().st_mtime)


def _safe_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def _first_col(df: pd.DataFrame, name: str) -> pd.Series | None:
    matches = [idx for idx, col in enumerate(df.columns) if col == name]
    if not matches:
        return None
    return df.iloc[:, matches[0]]


def _filter_range(df: pd.DataFrame, column: str, start: date, end: date) -> pd.DataFrame:
    if df.empty or column not in df.columns:
        return df
    dt = _safe_datetime(df[column]).dt.date
    mask = (dt >= start) & (dt <= end)
    return df.loc[mask].copy()


def _kpi(label: str, value: str, help_text: str | None = None) -> None:
    col = st.container()
    with col:
        st.markdown(
            f"<div class='kpi-card'><div class='kpi-label'>{label}</div><div class='kpi-value'>{value}</div></div>",
            unsafe_allow_html=True,
        )
        if help_text:
            render_description(help_text)


def _render_satisfaccion(df: pd.DataFrame) -> None:
    st.subheader("Encuestas de satisfaccion")
    render_description(
        "Puntuaciones de encuestas realizadas luego de la atencion del asesor de llamadas, "
        "separadas por asesor en la tabla y generalizadas en el grafico."
    )
    if df.empty:
        st.info("Aún no hay datos en reporte.csv")
        return

    if "Satisfaccion" not in df.columns:
        st.warning("El CSV no tiene la columna 'Satisfaccion'.")
        return

    df = df.copy()
    satisf_col = _first_col(df, "Satisfaccion")
    if satisf_col is None:
        st.warning("No se pudo leer la columna 'Satisfaccion'.")
        return

    label_map = {
        "1. Muy insatisfecho": "Muy Insatisfecho",
        "2. Insatisfecho": "Insatisfecho",
        "3. Neutral": "Neutral",
        "4. Satisfecho": "Satisfecho",
        "5. Muy satisfecho": "Muy Satisfecho",
    }
    satisf_display = satisf_col.map(label_map).fillna(satisf_col)

    counts = satisf_display.value_counts().reset_index()
    counts.columns = ["Satisfaccion", "Total"]
    color_map = {
        "Muy Insatisfecho": "#d32f2f",
        "Insatisfecho": "#ef6c00",
        "Neutral": "#fbc02d",
        "Satisfecho": "#8bc34a",
        "Muy Satisfecho": "#2e7d32",
    }
    satisfaccion_order = [
        "Muy Satisfecho",
        "Satisfecho",
        "Neutral",
        "Insatisfecho",
        "Muy Insatisfecho",
    ]
    fig = px.bar(
        counts,
        x="Satisfaccion",
        y="Total",
        text="Total",
        color="Satisfaccion",
        color_discrete_map=color_map,
        category_orders={"Satisfaccion": satisfaccion_order},
    )
    fig.update_layout(height=360, margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig, use_container_width=True)

    agent_col = _first_col(df, "Agente")
    if agent_col is not None:
        ordered_cols = [
            "Muy Insatisfecho",
            "Insatisfecho",
            "Neutral",
            "Satisfecho",
            "Muy Satisfecho",
        ]
        agent_pivot = (
            pd.DataFrame({"Agente": agent_col, "Satisfaccion": satisf_display})
            .groupby(["Agente", "Satisfaccion"])
            .size()
            .unstack(fill_value=0)
            .reindex(columns=ordered_cols, fill_value=0)
            .reset_index()
        )

        def _highlight_extremes(row: pd.Series) -> list[str]:
            styles = [""] * len(row)
            max_bad = agent_pivot["Muy Insatisfecho"].max()
            max_good = agent_pivot["Muy Satisfecho"].max()
            if row["Muy Insatisfecho"] == max_bad and max_bad > 0:
                return ["color: #b71c1c; font-weight: 600;"] * len(row)
            if row["Muy Satisfecho"] == max_good and max_good > 0:
                return ["color: #1b5e20; font-weight: 600;"] * len(row)
            return styles

        styled = agent_pivot.style.apply(_highlight_extremes, axis=1)
        styled = styled.set_table_styles(
            [
                {"selector": "th.col1", "props": [("color", "#b71c1c"), ("font-weight", "700")]},
                {"selector": "th.col5", "props": [("color", "#1b5e20"), ("font-weight", "700")]},
            ]
        )
        st.dataframe(styled, use_container_width=True)
        render_description(
            "Las filas resaltadas en rojo corresponden al asesor con mas respuestas "
            "de Muy Insatisfecho; en verde, el asesor con mas respuestas de Muy Satisfecho."
        )


def _render_detalle(df: pd.DataFrame) -> None:
    st.subheader("Llamadas")
    render_description(
        "Informacion generalizada sobre llamadas, en los recuadros los datos son calculados por unidad, "
        "en las tablas calculadas por asesor."
    )
    if df.empty:
        st.info("Aún no hay datos en detalle_llamadas.csv")
        return

    if "Fecha" in df.columns:
        df["Fecha"] = _safe_datetime(df["Fecha"]).dt.date

    if "Duración" in df.columns:
        avg_duration = df["Duración"].mean()
    else:
        avg_duration = 0

    if "Tiempo Espera" in df.columns:
        avg_wait = df["Tiempo Espera"].mean()
    else:
        avg_wait = 0

    kpi_cols = st.columns(3)
    with kpi_cols[0]:
        _kpi("Total llamadas", f"{len(df):,}")
    with kpi_cols[1]:
        _kpi("Duración promedio", format_seconds(avg_duration))
    with kpi_cols[2]:
        _kpi("Espera promedio", format_seconds(avg_wait))

    if "Estado" in df.columns:
        estado_map = {
            "success": "Resuelto",
            "resolved": "Resuelto",
            "resuelto": "Resuelto",
            "abandonado": "Abandonado",
            "abandoned": "Abandonado",
            "activa": "En curso",
            "en curso": "En curso",
            "active": "En curso",
        }
        estado_norm = df["Estado"].astype(str).str.strip().str.lower()
        estado_display = estado_norm.map(estado_map).fillna(df["Estado"])
        estado_counts = estado_display.value_counts().reset_index()
        estado_counts.columns = ["Estado", "Total"]
        estado_colors = {"Resuelto": "#2e7d32", "Abandonado": "#d32f2f", "En curso": "#fbc02d"}
        estado_order = ["Resuelto", "En curso", "Abandonado"]
        fig = px.bar(
            estado_counts,
            x="Estado",
            y="Total",
            text="Total",
            color="Estado",
            color_discrete_map=estado_colors,
            category_orders={"Estado": estado_order},
        )
        fig.update_layout(height=320, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig, use_container_width=True)

    group_col = "Agente2" if "Agente2" in df.columns else "Agente"
    if group_col in df.columns:
        grouped = (
            df.groupby(group_col)
            .agg(
                Total=(group_col, "size"),
                Duracion_Prom=("Duración", "mean"),
                Espera_Prom=("Tiempo Espera", "mean"),
            )
            .reset_index()
        )
        grouped["Duracion_Prom"] = grouped["Duracion_Prom"].apply(format_seconds)
        grouped["Espera_Prom"] = grouped["Espera_Prom"].apply(format_seconds)
        grouped = grouped.rename(
            columns={
                group_col: "Agente",
                "Total": "Total de Llamadas",
                "Duracion_Prom": "Duracion Promedio",
                "Espera_Prom": "Tiempo de espera Promedio",
            }
        )
        st.dataframe(prepare_table(grouped), use_container_width=True)


def render() -> None:
    st.header("Llamadas")

    reporte_df = _load_csv(REPORTE_PATH)
    detalle_df = _load_csv(DETALLE_PATH)

    st.markdown("---")

    if "llamadas_range" not in st.session_state:
        today = date.today()
        st.session_state["llamadas_range"] = (today - timedelta(days=7), today)
    if "llamadas_quick" not in st.session_state:
        st.session_state["llamadas_quick"] = "Hoy"

    quick_options = ["Hoy", "Ayer", "Ultimos 7 dias", "Ultimos 30 dias", "Personalizado"]
    quick_cols = st.columns([6, 1], gap="small")
    with quick_cols[0]:
        selected_quick = st.radio(
            "Rango rapido",
            quick_options,
            horizontal=True,
            key="llamadas_quick",
        )
    with quick_cols[1]:
        if st.button("Actualizar", key="llamadas_refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    today = date.today()
    if selected_quick == "Hoy":
        st.session_state["llamadas_range"] = (today, today)
    elif selected_quick == "Ayer":
        yesterday = today - timedelta(days=1)
        st.session_state["llamadas_range"] = (yesterday, yesterday)
    elif selected_quick == "Ultimos 7 dias":
        st.session_state["llamadas_range"] = (today - timedelta(days=7), today)
    elif selected_quick == "Ultimos 30 dias":
        st.session_state["llamadas_range"] = (today - timedelta(days=30), today)

    if selected_quick == "Personalizado":
        range_start, range_end = date_range_picker(
            "llamadas_range_picker", st.session_state["llamadas_range"]
        )
        st.session_state["llamadas_range"] = (range_start, range_end)
    else:
        range_start, range_end = st.session_state["llamadas_range"]
    detalle_filtrado = _filter_range(detalle_df, "Fecha", range_start, range_end)
    reporte_filtrado = _filter_range(reporte_df, "Fecha", range_start, range_end)

    _render_satisfaccion(reporte_filtrado)
    st.markdown("---")
    _render_detalle(detalle_filtrado)
