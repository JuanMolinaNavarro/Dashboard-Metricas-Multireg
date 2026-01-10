from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit_shadcn_ui as ui

from helpers import api_client, charts
from helpers.utils import date_range_picker, info_icon, prepare_table, quick_range


def _init_state(key: str):
    if key not in st.session_state:
        st.session_state[key] = quick_range(7)
    if "casos_atendidos_mode" not in st.session_state:
        st.session_state["casos_atendidos_mode"] = "custom"


def render():
    st.header("Casos Atendidos")

    _init_state("casos_atendidos_range")
    start, end = st.session_state["casos_atendidos_range"]

    range_options = ["Ultimas 24h", "Ultimas 48h", "Ultimos 7 dias", "Personalizado"]
    mode_to_label = {
        "24h": "Ultimas 24h",
        "48h": "Ultimas 48h",
        "7d": "Ultimos 7 dias",
        "custom": "Personalizado",
    }
    label_to_mode = {v: k for k, v in mode_to_label.items()}
    current_label = mode_to_label.get(st.session_state["casos_atendidos_mode"], "Personalizado")
    range_cols = st.columns([6, 1], gap="small")
    with range_cols[0]:
        selected_label = st.radio(
            "Rango rapido",
            range_options,
            index=range_options.index(current_label),
            horizontal=True,
            key="casos_atendidos_range_choice",
        )
    with range_cols[1]:
        refresh = st.button("Actualizar", key="ca_refresh", use_container_width=True)
    if refresh:
        st.cache_data.clear()
        st.rerun()
    st.session_state["casos_atendidos_mode"] = label_to_mode.get(selected_label, "custom")

    mode = st.session_state["casos_atendidos_mode"]
    if mode == "custom":
        st.session_state["casos_atendidos_range"] = date_range_picker(
            "casos_atendidos_picker",
            (start, end),
        )
    else:
        if mode == "24h":
            st.session_state["casos_atendidos_range"] = quick_range(1)
        elif mode == "48h":
            st.session_state["casos_atendidos_range"] = quick_range(2)
        else:
            st.session_state["casos_atendidos_range"] = quick_range(7)
        st.caption("Usando rango rapido. Selecciona Personalizado para elegir fechas.")

    start, end = st.session_state["casos_atendidos_range"]
    st.markdown(f"### Rango seleccionado: {start} a {end}")

    mode = st.session_state["casos_atendidos_mode"]
    if mode == "24h":
        data = api_client.casos_atendidos_ultimas_24h()
    elif mode == "48h":
        data = api_client.casos_atendidos_ultimas_48h()
    elif mode == "7d":
        data = api_client.casos_atendidos_ultimos_7_dias()
    else:
        data = api_client.metrics_casos_atendidos(start, end)
    resumen = api_client.metrics_casos_atendidos_resumen(start, end)

    if isinstance(resumen, dict):
        entradas = float(resumen.get("conversaciones_entrantes", 0))
        atendidas = float(resumen.get("conversaciones_atendidas_same_day", 0))
        if "pct_atendidas" in resumen:
            pct_val = float(resumen["pct_atendidas"])
        else:
            pct_val = (atendidas / entradas * 100) if entradas else 0.0

        if pct_val > 75:
            color = "#16a34a"
        elif pct_val >= 60:
            color = "#f59e0b"
        else:
            color = "#dc2626"

        donut_df = pd.DataFrame(
            {"segmento": ["Atendidas", "Restante"], "valor": [pct_val, 100 - pct_val]}
        )
        st.markdown(
            f"#### Porcentaje de conversaciones atendidas {info_icon('Porcentaje calculado como atendidas mismo dia / conversaciones entrantes del rango.')}",
            unsafe_allow_html=True,
        )
        fig = px.pie(donut_df, names="segmento", values="valor", hole=0.6)
        fig.update_traces(
            marker=dict(colors=[color, "#e5e7eb"]),
            textinfo="none",
            hovertemplate="%{label}: %{value:.2f}%<extra></extra>",
        )
        fig.update_layout(
            showlegend=False,
            annotations=[
                dict(
                    text=f"{pct_val:.2f}%",
                    x=0.5,
                    y=0.5,
                    showarrow=False,
                    font=dict(size=20),
                )
            ],
            margin=dict(l=0, r=0, t=0, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

        kpi_cols = st.columns(2)
        with kpi_cols[0]:
            st.markdown(
                f"""
<div class="kpi-card">
  <div style="font-size: 14px; opacity: 0.8;">Conversaciones entrantes {info_icon('Total de conversaciones entrantes en el rango seleccionado.')}</div>
  <div style="font-size: 32px; font-weight: 700;">{int(entradas)}</div>
</div>
""",
                unsafe_allow_html=True,
            )
        with kpi_cols[1]:
            st.markdown(
                f"""
<div class="kpi-card">
  <div style="font-size: 14px; opacity: 0.8;">Atendidas mismo dia {info_icon('Total de conversaciones atendidas el mismo dia en el rango seleccionado.')}</div>
  <div style="font-size: 32px; font-weight: 700;">{int(atendidas)}</div>
</div>
""",
                unsafe_allow_html=True,
            )
    else:
        st.info("Resumen no disponible para el rango seleccionado.")

    st.subheader("Detalle")
    rows = data.get("data", data) if isinstance(data, dict) else data
    df = pd.DataFrame(rows)
    if not df.empty:
        if "team_uuid" in df.columns:
            df = df.drop(columns=["team_uuid"])
        if "pct_atendidas" in df.columns:
            df["pct_atendidas"] = df["pct_atendidas"].round(2)
        df = df.rename(
            columns={
                "dia": "Dia",
                "conversaciones_entrantes": "Conversaciones Entrantes",
                "conversaciones_atendidas_same_day": "Conversaciones Atendidas (Mismo Dia)",
                "pct_atendidas": "% Atendidas",
            }
        )
        st.markdown(
            f"#### Detalle por dia {info_icon('Detalle diario de conversaciones entrantes y atendidas mismo dia en el rango.')}",
            unsafe_allow_html=True,
        )
        def _style_atendidas(df_styled: pd.DataFrame):
            if "% Atendidas" not in df_styled.columns:
                return df_styled
            def _color(val):
                try:
                    value = float(val)
                except (TypeError, ValueError):
                    return ""
                if value < 80:
                    return "color: #dc2626; font-weight: 600;"
                if value < 90:
                    return "color: #f59e0b; font-weight: 600;"
                return ""
            styler = df_styled.style.applymap(_color, subset=["% Atendidas"])
            styler = styler.format({"% Atendidas": "{:.2f}"})
            return styler

        table_df = prepare_table(df)
        st.dataframe(_style_atendidas(table_df), use_container_width=True)
        if "fecha" in df.columns and "total" in df.columns:
            fig = charts.line_chart(df, x="fecha", y="total", title="Casos atendidos")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sin datos para el rango seleccionado.")


if __name__ == "__main__":
    render()
