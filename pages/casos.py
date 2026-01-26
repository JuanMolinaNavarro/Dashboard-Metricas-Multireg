from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit_shadcn_ui as ui

from helpers import api_client, charts
from helpers.utils import date_range_picker, exclude_agent_rows, prepare_table, quick_range, render_description


def _init_state(key: str):
    if key not in st.session_state:
        st.session_state[key] = quick_range(7)
    if "casos_mode" not in st.session_state:
        st.session_state["casos_mode"] = "custom"
    if "casos_empresa" not in st.session_state:
        st.session_state["casos_empresa"] = ""


def render():
    st.header("Abandonos")

    _init_state("casos_range")
    start, end = st.session_state["casos_range"]

    range_options = ["Ultimas 24h", "Ultimas 48h", "Ultimos 7 dias", "Personalizado"]
    mode_to_label = {
        "24h": "Ultimas 24h",
        "48h": "Ultimas 48h",
        "7d": "Ultimos 7 dias",
        "custom": "Personalizado",
    }
    label_to_mode = {v: k for k, v in mode_to_label.items()}
    current_label = mode_to_label.get(st.session_state["casos_mode"], "Personalizado")
    range_cols = st.columns([6, 1], gap="small")
    with range_cols[0]:
        selected_label = st.radio(
            "Rango rapido",
            range_options,
            index=range_options.index(current_label),
            horizontal=True,
            key="casos_range_choice",
        )
    with range_cols[1]:
        refresh = st.button("Actualizar", key="cas_refresh", use_container_width=True)
    if refresh:
        st.cache_data.clear()
        st.rerun()
    st.session_state["casos_mode"] = label_to_mode.get(selected_label, "custom")

    if st.session_state["casos_mode"] == "custom":
        st.session_state["casos_range"] = date_range_picker("cas_picker", (start, end))
    else:
        st.caption("Usando rango rapido. Selecciona Personalizado para elegir fechas.")

    start, end = st.session_state["casos_range"]

    team_uuid = ""
    agent_email = ""
    as_of = ""

    mode = st.session_state["casos_mode"]
    if mode == "24h":
        resueltos = api_client.casos_resueltos_ultimas_24h(team_uuid, agent_email)
        abandonados = api_client.casos_abandonados_24h_ultimas_24h(team_uuid, agent_email, as_of)
    elif mode == "48h":
        resueltos = api_client.casos_resueltos_ultimas_48h(team_uuid, agent_email)
        abandonados = api_client.casos_abandonados_24h_ultimas_48h(team_uuid, agent_email, as_of)
    elif mode == "7d":
        resueltos = api_client.casos_resueltos_ultimos_7_dias(team_uuid, agent_email)
        abandonados = api_client.casos_abandonados_24h_ultimos_7_dias(team_uuid, agent_email, as_of)
    else:
        resueltos = api_client.casos_resueltos(start, end, team_uuid, agent_email)
        abandonados = api_client.casos_abandonados_24h(start, end, team_uuid, agent_email, as_of)

    res_rows = resueltos.get("data", resueltos) if isinstance(resueltos, dict) else resueltos
    ab_rows = abandonados.get("data", abandonados) if isinstance(abandonados, dict) else abandonados
    df_res = pd.DataFrame(res_rows)
    df_ab = pd.DataFrame(ab_rows)
    df_res = exclude_agent_rows(df_res, "olartefacundo@outlook.com")
    df_ab = exclude_agent_rows(df_ab, "olartefacundo@outlook.com")

    if df_res.empty and df_ab.empty:
        st.info("Sin datos para el rango seleccionado.")
        return

    def _aggregate(df_r: pd.DataFrame, df_a: pd.DataFrame, key: str) -> pd.DataFrame:
        res_group = df_r.groupby(key, dropna=False, as_index=False).agg(
            casos_abiertos_res=("casos_abiertos", "sum"),
            casos_resueltos=("casos_resueltos", "sum"),
        ) if not df_r.empty else pd.DataFrame(columns=[key, "casos_abiertos_res", "casos_resueltos"])
        ab_group = df_a.groupby(key, dropna=False, as_index=False).agg(
            casos_abiertos_ab=("casos_abiertos", "sum"),
            casos_abandonados=("casos_abandonados_24h", "sum"),
        ) if not df_a.empty else pd.DataFrame(columns=[key, "casos_abiertos_ab", "casos_abandonados"])

        merged = pd.merge(res_group, ab_group, on=key, how="outer")
        merged["casos_abiertos"] = merged[["casos_abiertos_res", "casos_abiertos_ab"]].max(axis=1)
        merged["casos_abiertos"] = merged["casos_abiertos"].fillna(0)
        merged["casos_resueltos"] = merged["casos_resueltos"].fillna(0)
        merged["casos_abandonados"] = merged["casos_abandonados"].fillna(0)

        merged["pct_resueltos"] = merged.apply(
            lambda row: (row["casos_resueltos"] / row["casos_abiertos"] * 100)
            if row["casos_abiertos"]
            else 0,
            axis=1,
        )
        merged["pct_abandonados"] = merged.apply(
            lambda row: (row["casos_abandonados"] / row["casos_abiertos"] * 100)
            if row["casos_abiertos"]
            else 0,
            axis=1,
        )

        return merged[[key, "casos_abiertos", "casos_resueltos", "pct_resueltos", "casos_abandonados", "pct_abandonados"]]

    team_key = "team_name" if "team_name" in df_res.columns or "team_name" in df_ab.columns else "team_uuid"
    if team_key not in df_res.columns and team_key in df_ab.columns:
        df_res[team_key] = df_ab[team_key]
    if team_key not in df_ab.columns and team_key in df_res.columns:
        df_ab[team_key] = df_res[team_key]

    agent_key = "agent_email"

    empresas = (
        [
            n
            for n in sorted(
                pd.concat([df_res.get(team_key, pd.Series()), df_ab.get(team_key, pd.Series())])
                .dropna()
                .unique()
            )
            if n != "CHATBOT"
        ]
        if team_key in df_res.columns or team_key in df_ab.columns
        else []
    )
    if empresas:
        opciones = ["Todos"] + empresas
        seleccion = st.radio(
            "Filtrar por empresa",
            opciones,
            horizontal=True,
            key="casos_empresa_choice",
        )
        st.session_state["casos_empresa"] = "" if seleccion == "Todos" else seleccion

    selected_empresa = st.session_state["casos_empresa"]
    if selected_empresa and team_key in df_res.columns:
        df_res = df_res[df_res[team_key] == selected_empresa]
    if selected_empresa and team_key in df_ab.columns:
        df_ab = df_ab[df_ab[team_key] == selected_empresa]

    team_table = _aggregate(df_res, df_ab, team_key)
    agent_table = _aggregate(df_res, df_ab, agent_key)

    def _format_table(df: pd.DataFrame, key_col: str) -> pd.DataFrame:
        key_label = "Agente" if key_col == "agent_email" else "Empresa"
        renamed = df.rename(
            columns={
                key_col: key_label,
                "casos_abiertos": "Casos Abiertos",
                "casos_resueltos": "Casos Resueltos",
                "pct_resueltos": "Porcentaje de Resueltos",
                "casos_abandonados": "Casos Abandonados",
                "pct_abandonados": "Porcentaje de Abandonados",
            }
        )
        return renamed

    def _style_casos(df: pd.DataFrame):
        def _color_resueltos(val):
            try:
                value = float(val)
            except (TypeError, ValueError):
                return ""
            if value < 80:
                return "color: #dc2626; font-weight: 600;"
            if value < 90:
                return "color: #f59e0b; font-weight: 600;"
            return "color: #16a34a; font-weight: 600;"

        def _color_abandonados(val):
            try:
                value = float(val)
            except (TypeError, ValueError):
                return ""
            if value > 25:
                return "color: #dc2626; font-weight: 600;"
            if value >= 15:
                return "color: #f59e0b; font-weight: 600;"
            return "color: #16a34a; font-weight: 600;"

        styler = df.style
        if "Porcentaje de Resueltos" in df.columns:
            styler = styler.applymap(_color_resueltos, subset=["Porcentaje de Resueltos"])
        if "Porcentaje de Abandonados" in df.columns:
            styler = styler.applymap(_color_abandonados, subset=["Porcentaje de Abandonados"])
        styler = styler.format(
            {
                "Porcentaje de Resueltos": "{:.2f}",
                "Porcentaje de Abandonados": "{:.2f}",
            }
        )
        return styler

    total_abiertos = team_table["casos_abiertos"].sum()
    total_resueltos = team_table["casos_resueltos"].sum()
    total_abandonados = team_table["casos_abandonados"].sum()
    pct_resueltos = (total_resueltos / total_abiertos * 100) if total_abiertos else 0
    pct_abandonados = (total_abandonados / total_abiertos * 100) if total_abiertos else 0

    def _donut(pct: float):
        if pct >= 75:
            color = "#16a34a"
        elif pct >= 65:
            color = "#f59e0b"
        else:
            color = "#dc2626"

        df_donut = pd.DataFrame(
            {"segmento": ["Porcentaje", "Restante"], "valor": [pct, max(0.0, 100 - pct)]}
        )
        fig = px.pie(df_donut, names="segmento", values="valor", hole=0.6)
        fig.update_traces(
            marker=dict(colors=[color, "#e5e7eb"]),
            textinfo="none",
            hovertemplate="%{label}: %{value:.2f}%<extra></extra>",
        )
        fig.update_layout(
            showlegend=False,
            annotations=[
                dict(
                    text=f"{pct:.2f}%",
                    x=0.5,
                    y=0.5,
                    showarrow=False,
                    font=dict(size=18),
                )
            ],
            margin=dict(l=0, r=0, t=40, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

    donut_cols = st.columns(2)
    with donut_cols[0]:
        st.markdown("#### Porcentaje de Casos Resueltos")
        render_description(
            "Porcentaje sobre el total de casos registrados en el rango de tiempo seleccionado que se hayan resuelto finalmente, sean a tiempo o no lo sean."
        )
        _donut(pct_resueltos)
    with donut_cols[1]:
        st.markdown("#### Porcentaje de Casos Abandonados")
        render_description(
            "Porcentaje sobre el total de casos registrados en el rango de tiempo en el que el cliente no obtuvo una respuesta por 24 horas o más."
        )
        _donut(pct_abandonados)

    st.markdown("#### Resumen por empresa")
    if "team_uuid" in team_table.columns:
        team_table = team_table.drop(columns=["team_uuid"])
    if "team_uuid" in agent_table.columns:
        agent_table = agent_table.drop(columns=["team_uuid"])

    team_display = _format_table(team_table, team_key)
    if "Empresa" in team_display.columns:
        team_display = team_display[team_display["Empresa"] != "CHATBOT"]
    team_display = prepare_table(team_display)
    st.dataframe(_style_casos(team_display), use_container_width=True)
    st.caption(
        "% Resueltos: Verde mas del 90%, Amarillo entre 80% - 90%, Rojo menos del 80%. | "
        "% Abandonados: Verde menos del 15%, Amarillo entre 15% - 25%, Rojo más del 25%."
    )

    st.markdown("#### Resumen por agente")
    agent_display = _format_table(agent_table, agent_key)
    agent_display = prepare_table(agent_display)
    st.dataframe(_style_casos(agent_display), use_container_width=True)
    st.caption(
        "% Resueltos: verde > 90%, amarillo 80% - 90%, rojo < 80%. | "
        "% Abandonados: verde < 15%, amarillo 15% - 25%, rojo > 25%."
    )


if __name__ == "__main__":
    render()
