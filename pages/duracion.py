from __future__ import annotations

import pandas as pd
import streamlit as st
import streamlit_shadcn_ui as ui

from helpers import api_client, charts
from helpers.utils import date_range_picker, exclude_agent_rows, format_seconds, info_icon, prepare_table, quick_range


def _init_state(key: str):
    if key not in st.session_state:
        st.session_state[key] = quick_range(7)
    if "duracion_mode" not in st.session_state:
        st.session_state["duracion_mode"] = "custom"
    if "duracion_team" not in st.session_state:
        st.session_state["duracion_team"] = ""


def render():
    st.header("Duracion Promedio")

    _init_state("duracion_range")
    start, end = st.session_state["duracion_range"]

    range_options = ["Ultimas 24h", "Ultimas 48h", "Ultimos 7 dias", "Personalizado"]
    mode_to_label = {
        "24h": "Ultimas 24h",
        "48h": "Ultimas 48h",
        "7d": "Ultimos 7 dias",
        "custom": "Personalizado",
    }
    label_to_mode = {v: k for k, v in mode_to_label.items()}
    current_label = mode_to_label.get(st.session_state["duracion_mode"], "Personalizado")
    range_cols = st.columns([6, 1], gap="small")
    with range_cols[0]:
        selected_label = st.radio(
            "Rango rapido",
            range_options,
            index=range_options.index(current_label),
            horizontal=True,
            key="duracion_range_choice",
        )
    with range_cols[1]:
        refresh = st.button("Actualizar", key="dur_refresh", use_container_width=True)
    if refresh:
        st.cache_data.clear()
        st.rerun()
    st.session_state["duracion_mode"] = label_to_mode.get(selected_label, "custom")

    mode = st.session_state["duracion_mode"]
    if mode == "custom":
        st.session_state["duracion_range"] = date_range_picker(
            "dur_picker",
            (start, end),
        )
    elif mode == "24h":
        st.session_state["duracion_range"] = quick_range(1)
        st.caption("Usando rango rapido (24h). Selecciona Personalizado para elegir fechas.")
    elif mode == "48h":
        st.session_state["duracion_range"] = quick_range(2)
        st.caption("Usando rango rapido (48h). Selecciona Personalizado para elegir fechas.")
    else:
        st.session_state["duracion_range"] = quick_range(7)
        st.caption("Usando rango rapido (7 dias). Selecciona Personalizado para elegir fechas.")

    start, end = st.session_state["duracion_range"]

    agent_email = ""

    data = api_client.duracion_promedio(start, end, "", agent_email)
    resumen_agentes = api_client.duracion_resumen_agentes(start, end)
    resumen_equipos = api_client.duracion_resumen_equipos(start, end)

    st.subheader("Promedio general")
    rows = data.get("data", data) if isinstance(data, dict) else data
    df = pd.DataFrame(rows)
    if not df.empty:
        team_names = (
            sorted(df["team_name"].dropna().unique().tolist()) if "team_name" in df.columns else []
        )
        if team_names:
            options = ["Todos"] + team_names
            selected_team_label = st.radio(
                "Filtrar por empresa",
                options,
                horizontal=True,
                key="duracion_team_choice",
            )
            st.session_state["duracion_team"] = "" if selected_team_label == "Todos" else selected_team_label

        selected_team = st.session_state["duracion_team"]
        if selected_team and "team_name" in df.columns:
            df = df[df["team_name"] == selected_team]
        df = exclude_agent_rows(df, "olartefacundo@outlook.com")

        mediana = df["median_duration_seconds"].mean() if "median_duration_seconds" in df.columns else 0
        promedio = df["avg_duration_seconds"].mean() if "avg_duration_seconds" in df.columns else 0
        p90 = df["p90_duration_seconds"].mean() if "p90_duration_seconds" in df.columns else 0

        kpi_cols = st.columns(3)
        with kpi_cols[0]:
            st.markdown(
                f"""
<div class="kpi-card">
  <div style="font-size: 14px; opacity: 0.8;">Duracion (Mediana) {info_icon('Promedio de la mediana de duracion para el rango seleccionado.')}</div>
  <div style="font-size: 32px; font-weight: 700;">{format_seconds(mediana)}</div>
</div>
""",
                unsafe_allow_html=True,
            )
        with kpi_cols[1]:
            st.markdown(
                f"""
<div class="kpi-card">
  <div style="font-size: 14px; opacity: 0.8;">Duracion (Promedio) {info_icon('Promedio de duracion para el rango seleccionado.')}</div>
  <div style="font-size: 32px; font-weight: 700;">{format_seconds(promedio)}</div>
</div>
""",
                unsafe_allow_html=True,
            )
        with kpi_cols[2]:
            st.markdown(
                f"""
<div class="kpi-card">
  <div style="font-size: 14px; opacity: 0.8;">Duracion (Percentil 90) {info_icon('Promedio del percentil 90 de duracion para el rango seleccionado.')}</div>
  <div style="font-size: 32px; font-weight: 700;">{format_seconds(p90)}</div>
</div>
""",
                unsafe_allow_html=True,
            )

        numeric_cols = df.select_dtypes(include="number").columns
        if len(numeric_cols) > 0:
            df = df.loc[~(df[numeric_cols] == 0).all(axis=1)]
        if selected_team:
            if "team_uuid" in df.columns:
                df = df.drop(columns=["team_uuid"])
            for col in ("avg_duration_seconds", "median_duration_seconds", "p90_duration_seconds"):
                if col in df.columns:
                    df[col] = df[col].apply(format_seconds)
            df = df.rename(
                columns={
                    "dia": "Dia",
                    "team_name": "Empresa",
                    "agent_email": "Agente",
                    "conversaciones_cerradas": "Conversaciones Cerradas",
                    "avg_duration_seconds": "Duracion Promedio (s)",
                    "median_duration_seconds": "Duracion Mediana (s)",
                    "p90_duration_seconds": "Duracion P90 (s)",
                }
            )
            st.markdown(
                f"#### Detalle por empresa {info_icon('Detalle diario filtrado por empresa en el rango seleccionado.')}",
                unsafe_allow_html=True,
            )
            ui.table(prepare_table(df))
        else:
            st.markdown("<div class=\"kpi-info-spacer\"></div>", unsafe_allow_html=True)
            st.info("Selecciona una empresa para ver la tabla de promedio general.")
    else:
        st.info("Sin datos para el rango seleccionado.")

    st.markdown(
        f"#### Resumen por agentes {info_icon('Resumen por agente con duraciones promedio, mediana y p90 en el rango.')}",
        unsafe_allow_html=True,
    )
    agents_rows = resumen_agentes.get("data", resumen_agentes) if isinstance(resumen_agentes, dict) else resumen_agentes
    df_agents = pd.DataFrame(agents_rows)
    df_agents = exclude_agent_rows(df_agents, "olartefacundo@outlook.com")
    numeric_cols = df_agents.select_dtypes(include="number").columns
    if len(numeric_cols) > 0:
        df_agents = df_agents.loc[~(df_agents[numeric_cols] == 0).all(axis=1)]
    if not df_agents.empty:
        if "team_uuid" in df_agents.columns:
            df_agents = df_agents.drop(columns=["team_uuid"])
        for col in ("avg_duration_seconds", "median_duration_seconds", "p90_duration_seconds"):
            if col in df_agents.columns:
                df_agents[col] = df_agents[col].apply(format_seconds)
        df_agents = df_agents.rename(
            columns={
                "agent_email": "Agente",
                "conversaciones_cerradas": "Conversaciones Cerradas",
                "avg_duration_seconds": "Duracion Promedio (s)",
                "median_duration_seconds": "Duracion Mediana (s)",
                "p90_duration_seconds": "Duracion P90 (s)",
            }
        )
        ui.table(prepare_table(df_agents))
    else:
        st.info("Sin datos por agentes.")

    st.markdown(
        f"#### Resumen por empresas {info_icon('Resumen por empresa con duraciones promedio, mediana y p90 en el rango.')}",
        unsafe_allow_html=True,
    )
    teams_rows = resumen_equipos.get("data", resumen_equipos) if isinstance(resumen_equipos, dict) else resumen_equipos
    df_teams = pd.DataFrame(teams_rows)
    df_teams = exclude_agent_rows(df_teams, "olartefacundo@outlook.com")
    if st.session_state["duracion_team"] and "team_name" in df_teams.columns:
        df_teams = df_teams[df_teams["team_name"] == st.session_state["duracion_team"]]
    numeric_cols = df_teams.select_dtypes(include="number").columns
    if len(numeric_cols) > 0:
        df_teams = df_teams.loc[~(df_teams[numeric_cols] == 0).all(axis=1)]
    if not df_teams.empty:
        if "team_uuid" in df_teams.columns:
            df_teams = df_teams.drop(columns=["team_uuid"])
        for col in ("avg_duration_seconds", "median_duration_seconds", "p90_duration_seconds"):
            if col in df_teams.columns:
                df_teams[col] = df_teams[col].apply(format_seconds)
        df_teams = df_teams.rename(
            columns={
                "team_name": "Empresa",
                "conversaciones_cerradas": "Conversaciones Cerradas",
                "avg_duration_seconds": "Duracion Promedio (s)",
                "median_duration_seconds": "Duracion Mediana (s)",
                "p90_duration_seconds": "Duracion P90 (s)",
            }
        )
        ui.table(prepare_table(df_teams))
    else:
        st.info("Sin datos por empresas.")


if __name__ == "__main__":
    render()
