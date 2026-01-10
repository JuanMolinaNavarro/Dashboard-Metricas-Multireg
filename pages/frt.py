from __future__ import annotations

import pandas as pd
import streamlit as st
import streamlit_shadcn_ui as ui

from config import DEFAULT_FRT_LIMIT, DEFAULT_MAX_SECONDS
from helpers import api_client
from helpers.utils import date_range_picker, exclude_agent_rows, format_seconds, info_icon, prepare_table, quick_range


def _init_state(key: str):
    if key not in st.session_state:
        st.session_state[key] = quick_range(7)
    if "frt_mode" not in st.session_state:
        st.session_state["frt_mode"] = "custom"
    if "frt_team" not in st.session_state:
        st.session_state["frt_team"] = ""


def render():
    st.header("Tiempo de primera respuesta")

    _init_state("frt_range")
    start, end = st.session_state["frt_range"]

    range_options = ["Ultimas 24h", "Ultimas 48h", "Ultimos 7 dias", "Personalizado"]
    mode_to_label = {
        "24h": "Ultimas 24h",
        "48h": "Ultimas 48h",
        "7d": "Ultimos 7 dias",
        "custom": "Personalizado",
    }
    label_to_mode = {v: k for k, v in mode_to_label.items()}
    current_label = mode_to_label.get(st.session_state["frt_mode"], "Personalizado")
    range_cols = st.columns([6, 1], gap="small")
    with range_cols[0]:
        selected_label = st.radio(
            "Rango rapido",
            range_options,
            index=range_options.index(current_label),
            horizontal=True,
            key="frt_range_choice",
        )
    with range_cols[1]:
        refresh = st.button("Actualizar", key="frt_refresh", use_container_width=True)
    if refresh:
        st.cache_data.clear()
        st.rerun()
    st.session_state["frt_mode"] = label_to_mode.get(selected_label, "custom")

    mode = st.session_state["frt_mode"]
    if mode == "custom":
        st.session_state["frt_range"] = date_range_picker("frt_picker", (start, end))
    elif mode == "24h":
        st.session_state["frt_range"] = quick_range(1)
        st.caption("Usando rango rapido (24h). Selecciona Personalizado para elegir fechas.")
    elif mode == "48h":
        st.session_state["frt_range"] = quick_range(2)
        st.caption("Usando rango rapido (48h). Selecciona Personalizado para elegir fechas.")
    else:
        st.session_state["frt_range"] = quick_range(7)
        st.caption("Usando rango rapido (7 dias). Selecciona Personalizado para elegir fechas.")

    start, end = st.session_state["frt_range"]

    team_uuid = ""
    agent_email = ""

    if mode == "24h":
        frt_data = api_client.frt_ultimas_24h(team_uuid, agent_email)
    elif mode == "48h":
        frt_data = api_client.frt_ultimas_48h(team_uuid, agent_email)
    elif mode == "7d":
        frt_data = api_client.frt_ultimos_7_dias(team_uuid, agent_email)
    else:
        frt_data = api_client.frt_tiempo_primera_respuesta(start, end, team_uuid, agent_email)

    ranking = api_client.frt_ranking_agentes(start, end, limit=DEFAULT_FRT_LIMIT, team_uuid=team_uuid)
    resumen_agentes = api_client.frt_resumen_agentes(start, end)
    resumen_equipos = api_client.frt_resumen_equipos(start, end)

    st.subheader("Detalle de tiempo de primera respuesta")
    rows = frt_data.get("data", frt_data) if isinstance(frt_data, dict) else frt_data
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
                key="frt_team_choice",
            )
            st.session_state["frt_team"] = "" if selected_team_label == "Todos" else selected_team_label

        selected_team = st.session_state["frt_team"]
        filtered_df = df
        if selected_team and "team_name" in df.columns:
            filtered_df = df[df["team_name"] == selected_team]
        filtered_df = exclude_agent_rows(filtered_df, "olartefacundo@outlook.com")

        avg_val = filtered_df["avg_frt_seconds"].mean() if "avg_frt_seconds" in filtered_df.columns else 0
        median_val = (
            filtered_df["median_frt_seconds"].mean() if "median_frt_seconds" in filtered_df.columns else 0
        )
        p90_val = filtered_df["p90_frt_seconds"].mean() if "p90_frt_seconds" in filtered_df.columns else 0

        kpi_cols = st.columns(3)
        with kpi_cols[0]:
            st.markdown(
                f"""
<div class="kpi-card">
  <div style="font-size: 14px; opacity: 0.8;">Tiempo de primera respuesta (Promedio) {info_icon('Promedio de tiempo de primera respuesta en el rango seleccionado.')}</div>
  <div style="font-size: 32px; font-weight: 700;">{format_seconds(avg_val)}</div>
</div>
""",
                unsafe_allow_html=True,
            )
        with kpi_cols[1]:
            st.markdown(
                f"""
<div class="kpi-card">
  <div style="font-size: 14px; opacity: 0.8;">Tiempo de primera respuesta (Mediana) {info_icon('Mediana del tiempo de primera respuesta en el rango seleccionado.')}</div>
  <div style="font-size: 32px; font-weight: 700;">{format_seconds(median_val)}</div>
</div>
""",
                unsafe_allow_html=True,
            )
        with kpi_cols[2]:
            st.markdown(
                f"""
<div class="kpi-card">
  <div style="font-size: 14px; opacity: 0.8;">Tiempo de primera respuesta (Percentil 90) {info_icon('Percentil 90 del tiempo de primera respuesta en el rango seleccionado.')}</div>
  <div style="font-size: 32px; font-weight: 700;">{format_seconds(p90_val)}</div>
</div>
""",
                unsafe_allow_html=True,
            )

        if selected_team:
            if "team_uuid" in filtered_df.columns:
                filtered_df = filtered_df.drop(columns=["team_uuid"])
            for col in ("avg_frt_seconds", "median_frt_seconds", "p90_frt_seconds"):
                if col in filtered_df.columns:
                    filtered_df[col] = filtered_df[col].apply(format_seconds)
            filtered_df = filtered_df.rename(
                columns={
                    "dia": "Dia",
                    "team_name": "Empresa",
                    "agent_email": "Agente",
                    "casos_abiertos": "Casos Abiertos",
                    "casos_respondidos": "Casos Respondidos",
                    "avg_frt_seconds": "Tiempo de primera respuesta Promedio (s)",
                    "median_frt_seconds": "Tiempo de primera respuesta Mediana (s)",
                    "p90_frt_seconds": "Tiempo de primera respuesta P90 (s)",
                }
            )
            st.markdown(
                f"#### Detalle por empresa {info_icon('Detalle diario de tiempos por empresa en el rango seleccionado.')}",
                unsafe_allow_html=True,
            )
            ui.table(prepare_table(filtered_df))
        else:
            st.markdown("<div class=\"kpi-info-spacer\"></div>", unsafe_allow_html=True)
            st.info("Selecciona una empresa para ver la tabla de detalle.")
    else:
        st.info("Sin datos para el rango seleccionado.")

    st.markdown(
        f"#### Ranking de agentes {info_icon('Ranking de agentes por tiempo de primera respuesta promedio en el rango seleccionado.')}",
        unsafe_allow_html=True,
    )
    rank_rows = ranking.get("data", ranking) if isinstance(ranking, dict) else ranking
    rank_df = pd.DataFrame(rank_rows)
    rank_df = exclude_agent_rows(rank_df, "olartefacundo@outlook.com")
    if not rank_df.empty:
        rank_df = rank_df.reset_index(drop=True)
        rank_df.insert(0, "N", rank_df.index + 1)
        if "team_uuid" in rank_df.columns:
            rank_df = rank_df.drop(columns=["team_uuid"])
        for col in ("avg_frt_seconds", "median_frt_seconds", "p90_frt_seconds"):
            if col in rank_df.columns:
                rank_df[col] = rank_df[col].apply(format_seconds)
        rank_df = rank_df.rename(
            columns={
                "agent_email": "Agente",
                "casos_respondidos": "Casos Respondidos",
                "avg_frt_seconds": "Tiempo de primera respuesta Promedio (s)",
                "median_frt_seconds": "Tiempo de primera respuesta Mediana (s)",
                "p90_frt_seconds": "Tiempo de primera respuesta P90 (s)",
            }
        )
        ui.table(prepare_table(rank_df))
    else:
        st.info("Sin datos de ranking disponibles.")

    max_seconds = st.text_input(
        "SLA max segundos",
        value=str(DEFAULT_MAX_SECONDS),
        key="frt_max_seconds",
    )
    sla = api_client.frt_sla(start, end, int(max_seconds), team_uuid, agent_email)
    st.markdown(
        f"#### SLA por agente {info_icon('Porcentaje de respuestas dentro del SLA configurado, agrupado por agente. Colores: amarillo 70%-<90%, rojo <70%.')}",
        unsafe_allow_html=True,
    )
    sla_rows = sla.get("data", sla) if isinstance(sla, dict) else sla
    df_sla = pd.DataFrame(sla_rows)
    df_sla = exclude_agent_rows(df_sla, "olartefacundo@outlook.com")
    def _style_sla(df: pd.DataFrame):
        if "% SLA" not in df.columns:
            return df
        def _color(val):
            try:
                value = float(val)
            except (TypeError, ValueError):
                return ""
            if value < 70:
                return "color: #dc2626; font-weight: 600;"
            if value < 90:
                return "color: #f59e0b; font-weight: 600;"
            return ""
        styler = df.style.applymap(_color, subset=["% SLA"])
        styler = styler.format({"% SLA": "{:.2f}"})
        return styler

    if not df_sla.empty and "agent_email" in df_sla.columns:
        sla_agent = df_sla.groupby("agent_email", as_index=False).agg(
            casos_respondidos=("casos_respondidos", "sum"),
            casos_en_sla=("casos_en_sla", "sum"),
        )
        sla_agent["pct_sla"] = sla_agent.apply(
            lambda row: (row["casos_en_sla"] / row["casos_respondidos"] * 100)
            if row["casos_respondidos"]
            else 0,
            axis=1,
        )
        sla_agent["pct_sla"] = sla_agent["pct_sla"].round(2)
        sla_agent = sla_agent.rename(
            columns={
                "agent_email": "Agente",
                "casos_respondidos": "Casos Respondidos",
                "casos_en_sla": "Casos en SLA",
                "pct_sla": "% SLA",
            }
        )
        sla_agent = prepare_table(sla_agent)
        st.dataframe(_style_sla(sla_agent), use_container_width=True)
    else:
        st.info("Sin datos de SLA por agente.")

    st.markdown(
        f"#### SLA por empresa {info_icon('Porcentaje de respuestas dentro del SLA configurado, agrupado por empresa. Colores: amarillo 70%-<90%, rojo <70%.')}",
        unsafe_allow_html=True,
    )
    if not df_sla.empty:
        team_key = "team_name" if "team_name" in df_sla.columns else "team_uuid"
        if team_key in df_sla.columns:
            sla_team = df_sla.groupby(team_key, as_index=False).agg(
                casos_respondidos=("casos_respondidos", "sum"),
                casos_en_sla=("casos_en_sla", "sum"),
            )
            sla_team["pct_sla"] = sla_team.apply(
                lambda row: (row["casos_en_sla"] / row["casos_respondidos"] * 100)
                if row["casos_respondidos"]
                else 0,
                axis=1,
            )
            sla_team["pct_sla"] = sla_team["pct_sla"].round(2)
            if "team_uuid" in sla_team.columns:
                sla_team = sla_team.drop(columns=["team_uuid"])
            sla_team = sla_team.rename(
                columns={
                    team_key: "Empresa",
                    "casos_respondidos": "Casos Respondidos",
                    "casos_en_sla": "Casos en SLA",
                    "pct_sla": "% SLA",
                }
            )
            sla_team = prepare_table(sla_team)
            st.dataframe(_style_sla(sla_team), use_container_width=True)
        else:
            st.info("Sin datos de SLA por empresa.")
    else:
        st.info("Sin datos de SLA por empresa.")

    st.markdown(
        f"#### Resumen por agentes {info_icon('Resumen por agente con tiempos promedio, mediana y p90 en el rango.')}",
        unsafe_allow_html=True,
    )
    agents_rows = resumen_agentes.get("data", resumen_agentes) if isinstance(resumen_agentes, dict) else resumen_agentes
    df_agents = pd.DataFrame(agents_rows)
    df_agents = exclude_agent_rows(df_agents, "olartefacundo@outlook.com")
    if not df_agents.empty:
        if "team_uuid" in df_agents.columns:
            df_agents = df_agents.drop(columns=["team_uuid"])
        for col in ("avg_frt_seconds", "median_frt_seconds", "p90_frt_seconds"):
            if col in df_agents.columns:
                df_agents[col] = df_agents[col].apply(format_seconds)
        df_agents = df_agents.rename(
            columns={
                "agent_email": "Agente",
                "casos_abiertos": "Casos Abiertos",
                "casos_respondidos": "Casos Respondidos",
                "avg_frt_seconds": "Tiempo de primera respuesta Promedio (s)",
                "median_frt_seconds": "Tiempo de primera respuesta Mediana (s)",
                "p90_frt_seconds": "Tiempo de primera respuesta P90 (s)",
            }
        )
        ui.table(prepare_table(df_agents))
    else:
        st.info("Sin datos por agentes.")

    st.markdown(
        f"#### Resumen por empresas {info_icon('Resumen por empresa con tiempos promedio, mediana y p90 en el rango.')}",
        unsafe_allow_html=True,
    )
    teams_rows = resumen_equipos.get("data", resumen_equipos) if isinstance(resumen_equipos, dict) else resumen_equipos
    df_teams = pd.DataFrame(teams_rows)
    df_teams = exclude_agent_rows(df_teams, "olartefacundo@outlook.com")
    if not df_teams.empty:
        if "team_uuid" in df_teams.columns:
            df_teams = df_teams.drop(columns=["team_uuid"])
        for col in ("avg_frt_seconds", "median_frt_seconds", "p90_frt_seconds"):
            if col in df_teams.columns:
                df_teams[col] = df_teams[col].apply(format_seconds)
        df_teams = df_teams.rename(
            columns={
                "team_name": "Empresa",
                "casos_abiertos": "Casos Abiertos",
                "casos_respondidos": "Casos Respondidos",
                "avg_frt_seconds": "Tiempo de primera respuesta Promedio (s)",
                "median_frt_seconds": "Tiempo de primera respuesta Mediana (s)",
                "p90_frt_seconds": "Tiempo de primera respuesta P90 (s)",
            }
        )
        ui.table(prepare_table(df_teams))
    else:
        st.info("Sin datos por empresas.")


if __name__ == "__main__":
    render()
