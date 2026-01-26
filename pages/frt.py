from __future__ import annotations

import pandas as pd
import streamlit as st
import streamlit_shadcn_ui as ui

from config import DEFAULT_FRT_LIMIT, DEFAULT_MAX_SECONDS
from helpers import api_client
from helpers.utils import date_range_picker, exclude_agent_rows, format_seconds, prepare_table, quick_range, render_description


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

    ranking = api_client.frt_ranking_agentes(start, end, limit=100, team_uuid=team_uuid)
    resumen_agentes = api_client.frt_resumen_agentes(start, end)
    resumen_equipos = api_client.frt_resumen_equipos(start, end)

    rows = frt_data.get("data", frt_data) if isinstance(frt_data, dict) else frt_data
    df = pd.DataFrame(rows)
    if not df.empty:
        team_names = (
            [n for n in sorted(df["team_name"].dropna().unique().tolist()) if n != "CHATBOT"]
            if "team_name" in df.columns
            else []
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
        if "team_name" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["team_name"] != "CHATBOT"]

        avg_val = filtered_df["avg_frt_seconds"].mean() if "avg_frt_seconds" in filtered_df.columns else 0
        median_val = (
            filtered_df["median_frt_seconds"].mean() if "median_frt_seconds" in filtered_df.columns else 0
        )
        p90_val = filtered_df["p90_frt_seconds"].mean() if "p90_frt_seconds" in filtered_df.columns else 0

        # Casos abiertos por empresa desde resumen-equipos
        resumen_eq_rows = (
            resumen_equipos.get("data", resumen_equipos)
            if isinstance(resumen_equipos, dict)
            else resumen_equipos
        )
        df_resumen_eq = pd.DataFrame(resumen_eq_rows)
        df_resumen_eq = exclude_agent_rows(df_resumen_eq, "olartefacundo@outlook.com")
        if selected_team and "team_name" in df_resumen_eq.columns:
            df_resumen_eq = df_resumen_eq[df_resumen_eq["team_name"] == selected_team]
        casos_abiertos = (
            float(df_resumen_eq["casos_abiertos"].sum())
            if not df_resumen_eq.empty and "casos_abiertos" in df_resumen_eq.columns
            else 0
        )

        kpi_cols = st.columns(4)
        with kpi_cols[0]:
            st.markdown(
                f"""
<div class="kpi-card">
  <div style="font-size: 14px; opacity: 0.8;">Casos Abiertos</div>
  <div style="font-size: 32px; font-weight: 700;">{int(casos_abiertos)}</div>
</div>
""",
                unsafe_allow_html=True,
            )
        with kpi_cols[1]:
            st.markdown(
                f"""
<div class="kpi-card">
  <div style="font-size: 14px; opacity: 0.8;">Tiempo de primera respuesta (Promedio)</div>
  <div style="font-size: 32px; font-weight: 700;">{format_seconds(avg_val)}</div>
</div>
""",
                unsafe_allow_html=True,
            )
        with kpi_cols[2]:
            st.markdown(
                f"""
<div class="kpi-card">
  <div style="font-size: 14px; opacity: 0.8;">Tiempo de primera respuesta (Mediana)</div>
  <div style="font-size: 32px; font-weight: 700;">{format_seconds(median_val)}</div>
</div>
""",
                unsafe_allow_html=True,
            )
        with kpi_cols[3]:
            st.markdown(
                f"""
<div class="kpi-card">
  <div style="font-size: 14px; opacity: 0.8;">Tiempo de primera respuesta (Percentil 90)</div>
  <div style="font-size: 32px; font-weight: 700;">{format_seconds(p90_val)}</div>
</div>
""",
                unsafe_allow_html=True,
            )

        if selected_team:
            display_df = filtered_df.copy()
            if "team_uuid" in display_df.columns:
                display_df = display_df.drop(columns=["team_uuid"])

            avg_series = display_df["avg_frt_seconds"] if "avg_frt_seconds" in display_df.columns else None
            min_avg = float(avg_series.min()) if avg_series is not None and not avg_series.empty else None
            max_avg = float(avg_series.max()) if avg_series is not None and not avg_series.empty else None

            for col in ("avg_frt_seconds", "median_frt_seconds", "p90_frt_seconds"):
                if col in display_df.columns:
                    display_df[col] = display_df[col].apply(format_seconds)
            display_df = display_df.rename(
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
            st.markdown("#### Detalle por empresa")

            def _style_best_worst(row):
                if min_avg is None or max_avg is None:
                    return [""] * len(row)
                idx = row.name
                try:
                    value = float(filtered_df.loc[idx, "avg_frt_seconds"])
                except Exception:
                    return [""] * len(row)
                if value == min_avg:
                    return ["color: #16a34a; font-weight: 700; text-decoration: underline;"] * len(row)
                if value == max_avg:
                    return ["color: #dc2626; font-weight: 700; text-decoration: underline;"] * len(row)
                return [""] * len(row)

            numeric_df = filtered_df.reset_index(drop=True).copy()
            table_df = display_df.reset_index(drop=True)
            table_df = prepare_table(table_df)

            # compute min/max avg_frt_seconds excluding zeros and the supervisora agent
            avg_series_raw = numeric_df["avg_frt_seconds"] if "avg_frt_seconds" in numeric_df.columns else None
            exclude_mask = (
                numeric_df["agent_email"] != "supervisora_callc@multireg.com.ar"
                if "agent_email" in numeric_df.columns
                else True
            )
            nonzero_avg = (
                avg_series_raw[(avg_series_raw > 0) & exclude_mask]
                if avg_series_raw is not None
                else None
            )
            min_avg_nz = float(nonzero_avg.min()) if nonzero_avg is not None and not nonzero_avg.empty else None
            max_avg_nz = float(nonzero_avg.max()) if nonzero_avg is not None and not nonzero_avg.empty else None

            def _style_best_worst_row(row):
                if avg_series_raw is None:
                    return [""] * len(row)
                idx = row.name - 1  # table_df index starts at 1
                try:
                    avg_val = float(numeric_df.loc[idx, "avg_frt_seconds"])
                except Exception:
                    avg_val = None
                try:
                    responded = float(numeric_df.loc[idx, "casos_respondidos"])
                except Exception:
                    responded = None

                if responded == 0:
                    return ["color: #f59e0b; font-weight: 700; text-decoration: underline;"] * len(row)
                if min_avg_nz is not None and avg_val == min_avg_nz:
                    return ["color: #16a34a; font-weight: 700; text-decoration: underline;"] * len(row)
                if max_avg_nz is not None and avg_val == max_avg_nz:
                    return ["color: #dc2626; font-weight: 700; text-decoration: underline;"] * len(row)
                return [""] * len(row)

            styler = table_df.style.apply(_style_best_worst_row, axis=1)
            st.dataframe(styler, use_container_width=True)
            st.caption(
                "Amarillo: ningun caso respondido."
                "Verde: menor tiempo promedio."
                "Rojo: mayor tiempo promedio."
            )
        else:
            st.markdown("<div class=\"kpi-info-spacer\"></div>", unsafe_allow_html=True)
            st.info("Selecciona una empresa para ver la tabla de detalle.")
    else:
        st.info("Sin datos para el rango seleccionado.")

    st.markdown("#### Ranking de agentes")
    render_description(
        "Agentes rankeados por desempeño en base al tiempo de primera respuesta promedio."
    )
    rank_rows = ranking.get("data", ranking) if isinstance(ranking, dict) else ranking
    rank_df = pd.DataFrame(rank_rows)
    rank_df = exclude_agent_rows(rank_df, "olartefacundo@outlook.com")
    if "agent_email" in rank_df.columns:
        rank_df = rank_df[rank_df["agent_email"] != "supervisora_callc@multireg.com.ar"]

    resumen_rows = (
        resumen_agentes.get("data", resumen_agentes)
        if isinstance(resumen_agentes, dict)
        else resumen_agentes
    )
    resumen_df = pd.DataFrame(resumen_rows)
    if "agent_email" in resumen_df.columns:
        resumen_df = resumen_df[resumen_df["agent_email"] != "supervisora_callc@multireg.com.ar"]

    if not rank_df.empty:
        if "agent_email" in resumen_df.columns:
            rank_df = rank_df.merge(
                resumen_df[["agent_email", "casos_abiertos"]],
                on="agent_email",
                how="left",
            )
        rank_df = rank_df.reset_index(drop=True)
        rank_df.insert(0, "N", rank_df.index + 1)
        if "team_uuid" in rank_df.columns:
            rank_df = rank_df.drop(columns=["team_uuid"])

        numeric_rank = rank_df.copy()
        avg_series = numeric_rank["avg_frt_seconds"] if "avg_frt_seconds" in numeric_rank.columns else None
        nonzero_avg = avg_series[avg_series > 0] if avg_series is not None else None
        min_avg = float(nonzero_avg.min()) if nonzero_avg is not None and not nonzero_avg.empty else None
        max_avg = float(nonzero_avg.max()) if nonzero_avg is not None and not nonzero_avg.empty else None

        for col in ("avg_frt_seconds", "median_frt_seconds", "p90_frt_seconds"):
            if col in rank_df.columns:
                rank_df[col] = rank_df[col].apply(format_seconds)

        rank_df = rank_df.rename(
            columns={
                "agent_email": "Agente",
                "casos_abiertos": "Casos Recibidos",
                "casos_respondidos": "Casos Respondidos",
                "avg_frt_seconds": "Tiempo de primera respuesta Promedio (s)",
                "median_frt_seconds": "Tiempo de primera respuesta Mediana (s)",
                "p90_frt_seconds": "Tiempo de primera respuesta P90 (s)",
            }
        )
        if "Casos Recibidos" in rank_df.columns:
            cols = rank_df.columns.tolist()
            if "Agente" in cols and "Casos Respondidos" in cols:
                cols.remove("Casos Recibidos")
                insert_at = cols.index("Casos Respondidos")
                cols.insert(insert_at, "Casos Recibidos")
                rank_df = rank_df[cols]
        rank_df = prepare_table(rank_df)

        def _style_rank_row(row):
            if min_avg is None or max_avg is None:
                return [""] * len(row)
            idx = row.name - 1
            try:
                value = float(numeric_rank.loc[idx, "avg_frt_seconds"])
            except Exception:
                return [""] * len(row)
            if value == min_avg:
                return ["color: #16a34a; font-weight: 700;"] * len(row)
            if value == max_avg:
                return ["color: #dc2626; font-weight: 700;"] * len(row)
            return [""] * len(row)

        styler = rank_df.style.apply(_style_rank_row, axis=1)
        st.dataframe(styler, use_container_width=True)
        st.caption(
            "Verde: mejor rankeado. "
            "Rojo: peor rankeado."
        )
    else:
        st.info("Sin datos de ranking disponibles.")

    max_seconds = st.text_input(
        "SLA max segundos",
        value=str(DEFAULT_MAX_SECONDS),
        key="frt_max_seconds",
    )
    sla = api_client.frt_sla(start, end, int(max_seconds), team_uuid, agent_email)
    st.markdown("#### SLA por agente")
    render_description(
        "Service Level Agreement, basado en la cantidad de tiempo que se demora en contestar un caso, se muestra los casos recibidos por empresa, la cantidad que se respondieron y la cantidad que se encuentra dentro del SLA, incluido su porcentaje. El valor de tiempo máximo de SLA se puede modificar (valor por defecto 300 segundos)."
    )
    sla_rows = sla.get("data", sla) if isinstance(sla, dict) else sla
    df_sla = pd.DataFrame(sla_rows)
    df_sla = exclude_agent_rows(df_sla, "olartefacundo@outlook.com")
    def _style_sla(df: pd.DataFrame):
        if "% SLA" not in df.columns:
            return df
        series = pd.to_numeric(df["% SLA"], errors="coerce")
        nonzero = series[series > 0]
        min_sla = float(nonzero.min()) if not nonzero.empty else None
        max_sla = float(nonzero.max()) if not nonzero.empty else None

        def _color_row(row):
            try:
                value = float(row["% SLA"])
            except (TypeError, ValueError, KeyError):
                return [""] * len(row)
            if max_sla is not None and value == max_sla and value > 0:
                return ["color: #16a34a; font-weight: 700;"] * len(row)
            if min_sla is not None and value == min_sla and value > 0:
                return ["color: #dc2626; font-weight: 700;"] * len(row)
            return [""] * len(row)

        styler = df.style.apply(_color_row, axis=1)
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
        if "agent_email" in resumen_df.columns and "casos_abiertos" in resumen_df.columns:
            sla_agent = sla_agent.merge(
                resumen_df[["agent_email", "casos_abiertos"]],
                left_on="Agente",
                right_on="agent_email",
                how="left",
            )
            sla_agent = sla_agent.drop(columns=["agent_email"]).rename(
                columns={"casos_abiertos": "Casos Recibidos"}
            )
            if "Agente" in sla_agent.columns:
                sla_agent = sla_agent[sla_agent["Agente"] != "supervisora_callc@multireg.com.ar"]
            if "Casos Recibidos" in sla_agent.columns:
                sla_agent["Casos Recibidos"] = (
                    sla_agent["Casos Recibidos"].fillna(0).astype(int)
                )
            cols = sla_agent.columns.tolist()
            if "Agente" in cols and "Casos Respondidos" in cols and "Casos Recibidos" in cols:
                cols.remove("Casos Recibidos")
                cols.insert(cols.index("Casos Respondidos"), "Casos Recibidos")
                sla_agent = sla_agent[cols]
        sla_agent = prepare_table(sla_agent)
        st.dataframe(_style_sla(sla_agent), use_container_width=True)
        st.caption(
            "Verde valor SLA mas alto. Rojo valor SLA mas bajo."
        )
    else:
        st.info("Sin datos de SLA por agente.")

    st.markdown("#### SLA por empresa")
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
            if "team_name" in df_resumen_eq.columns and "casos_abiertos" in df_resumen_eq.columns:
                sla_team = sla_team.merge(
                    df_resumen_eq[df_resumen_eq["team_name"] != "CHATBOT"][
                        ["team_name", "casos_abiertos"]
                    ].rename(columns={"team_name": "Empresa"}),
                    on="Empresa",
                    how="left",
                )
                sla_team = sla_team.rename(columns={"casos_abiertos": "Casos Recibidos"})
                if "Casos Recibidos" in sla_team.columns:
                    sla_team["Casos Recibidos"] = (
                        sla_team["Casos Recibidos"].fillna(0).astype(int)
                    )
                cols = sla_team.columns.tolist()
                if "Empresa" in cols and "Casos Respondidos" in cols and "Casos Recibidos" in cols:
                    cols.remove("Casos Recibidos")
                    cols.insert(cols.index("Casos Respondidos"), "Casos Recibidos")
                    sla_team = sla_team[cols]
            if "Empresa" in sla_team.columns:
                sla_team = sla_team[sla_team["Empresa"] != "CHATBOT"]
            sla_team = prepare_table(sla_team)
            st.dataframe(_style_sla(sla_team), use_container_width=True)
            st.caption(
                "Verde valor SLA mas alto. Rojo valor SLA mas bajo."
            )
        else:
            st.info("Sin datos de SLA por empresa.")
    else:
        st.info("Sin datos de SLA por empresa.")

    st.markdown("#### Resumen por agentes")
    render_description(
        "Muestra el tiempo que demora un agente en general en contestar por primera vez a una conversación, tenemos 3 mediciones distintas: promedio, mediana y percentil 90 (el tiempo de primera respuesta promedio en el 90 porciento de los casos)."
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
        if "team_name" in df_agents.columns:
            df_agents = df_agents[df_agents["team_name"] != "CHATBOT"]
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
        st.dataframe(prepare_table(df_agents), use_container_width=True)
    else:
        st.info("Sin datos por agentes.")

    st.markdown("#### Resumen por empresas")
    render_description(
        "Muestra el tiempo que demora un agente en general en contestar por primera vez a una conversación, tenemos 3 mediciones distintas: promedio, mediana y percentil 90 (el tiempo de primera respuesta promedio en el 90 porciento de los casos)."
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
        df_teams = df_teams[df_teams["team_name"] != "CHATBOT"]
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
        st.dataframe(prepare_table(df_teams), use_container_width=True)
    else:
        st.info("Sin datos por empresas.")


if __name__ == "__main__":
    render()
