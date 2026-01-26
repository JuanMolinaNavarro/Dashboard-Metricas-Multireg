from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit_shadcn_ui as ui

from config import DEFAULT_MAX_SECONDS
from helpers import api_client, charts
from helpers.utils import date_range_picker, format_seconds, prepare_table, quick_range, render_description


def _init_state(key: str):
    if key not in st.session_state:
        st.session_state[key] = quick_range(7)
    if "casos_atendidos_mode" not in st.session_state:
        st.session_state["casos_atendidos_mode"] = "custom"


def render():
    st.header("Inicio")

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
        casos_resueltos = api_client.casos_resueltos_ultimas_24h("", "")
        casos_abandonados = api_client.casos_abandonados_24h_ultimas_24h("", "", "")
    elif mode == "48h":
        data = api_client.casos_atendidos_ultimas_48h()
        casos_resueltos = api_client.casos_resueltos_ultimas_48h("", "")
        casos_abandonados = api_client.casos_abandonados_24h_ultimas_48h("", "", "")
    elif mode == "7d":
        data = api_client.casos_atendidos_ultimos_7_dias()
        casos_resueltos = api_client.casos_resueltos_ultimos_7_dias("", "")
        casos_abandonados = api_client.casos_abandonados_24h_ultimos_7_dias("", "", "")
    else:
        data = api_client.metrics_casos_atendidos(start, end)
        casos_resueltos = api_client.casos_resueltos(start, end, "", "")
        casos_abandonados = api_client.casos_abandonados_24h(start, end, "", "", "")
    resumen = api_client.metrics_casos_atendidos_resumen(start, end)
    pendientes = api_client.casos_pendientes(start, end, "", "")

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
        donut_cols = st.columns(2, gap="large")
        with donut_cols[0]:
            st.markdown("#### Porcentaje de Conversaciones Atendidas en el mismo día")
            render_description(
                "Porcentaje de conversaciones entrantes que fueron atendidas en el mismo día en el que ingresaron. (Verde mayor o igual a 75%, Amarillo entre 60% y 75%, Rojo menor a 60%)"
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
        with donut_cols[1]:
            st.markdown("#### Distribucion de casos por Unidad")
            render_description(
                "Porciones del total de mensajes que recibe cada unidad. CCC es atendido por 8 agentes, mientras que el resto de unidades es atendido por 7 agentes."
            )

        pend_rows = pendientes.get("data", pendientes) if isinstance(pendientes, dict) else pendientes
        df_pend = pd.DataFrame(pend_rows)
        casos_pendientes = (
            float(df_pend["casos_pendientes"].sum())
            if not df_pend.empty and "casos_pendientes" in df_pend.columns
            else 0
        )

        kpi_cols = st.columns(3)
        with kpi_cols[0]:
            st.markdown(
                f"""
<div class="kpi-card">
  <div style="font-size: 14px; opacity: 0.8;">Conversaciones entrantes</div>
  <div style="font-size: 32px; font-weight: 700;">{int(entradas)}</div>
</div>
""",
                unsafe_allow_html=True,
            )
        with kpi_cols[1]:
            st.markdown(
                f"""
<div class="kpi-card">
  <div style="font-size: 14px; opacity: 0.8;">Casos Pendientes</div>
  <div style="font-size: 32px; font-weight: 700;">{int(casos_pendientes)}</div>
</div>
""",
                unsafe_allow_html=True,
            )
        with kpi_cols[2]:
            st.markdown(
                f"""
<div class="kpi-card">
  <div style="font-size: 14px; opacity: 0.8;">Atendidas mismo dia</div>
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
        if "entradas" not in locals():
            entradas = float(df.get("conversaciones_entrantes", pd.Series(dtype=float)).sum())
            atendidas = float(df.get("conversaciones_atendidas_same_day", pd.Series(dtype=float)).sum())
            pct_val = (atendidas / entradas * 100) if entradas else 0.0
        if "team_uuid" in df.columns:
            df = df.drop(columns=["team_uuid"])
        if "team_name" in df.columns:
            df = df[df["team_name"] != "CHATBOT"]
        if "pct_atendidas" in df.columns:
            df["pct_atendidas"] = df["pct_atendidas"].round(2)
        df = df.rename(
            columns={
                "dia": "Dia",
                "agent_email": "Agente",
                "conversaciones_entrantes": "Conversaciones Entrantes",
                "conversaciones_atendidas_same_day": "Conversaciones Atendidas (Mismo Dia)",
                "pct_atendidas": "% Atendidas",
            }
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
                return "color: #16a34a; font-weight: 600;"
            styler = df_styled.style.applymap(_color, subset=["% Atendidas"])
            styler = styler.format({"% Atendidas": "{:.2f}"})
            return styler

        def _aggregate(df_in: pd.DataFrame, key: str) -> pd.DataFrame:
            grouped = df_in.groupby(key, dropna=False, as_index=False).agg(
                conversaciones_entrantes=("Conversaciones Entrantes", "sum"),
                conversaciones_atendidas=("Conversaciones Atendidas (Mismo Dia)", "sum"),
            )
            grouped["% Atendidas"] = grouped.apply(
                lambda row: (row["conversaciones_atendidas"] / row["conversaciones_entrantes"] * 100)
                if row["conversaciones_entrantes"]
                else 0,
                axis=1,
            )
            return grouped

        # Tablas usando los endpoints de "Casos"
        res_rows = casos_resueltos.get("data", casos_resueltos) if isinstance(casos_resueltos, dict) else casos_resueltos
        ab_rows = casos_abandonados.get("data", casos_abandonados) if isinstance(casos_abandonados, dict) else casos_abandonados
        df_res = pd.DataFrame(res_rows)
        df_ab = pd.DataFrame(ab_rows)
        if "team_uuid" in df_res.columns:
            df_res = df_res.drop(columns=["team_uuid"])
        if "team_uuid" in df_ab.columns:
            df_ab = df_ab.drop(columns=["team_uuid"])

        def _aggregate_casos(df_r: pd.DataFrame, df_a: pd.DataFrame, key: str) -> pd.DataFrame:
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

        def _style_resueltos(df_styled: pd.DataFrame):
            if "% Resueltos" not in df_styled.columns:
                return df_styled
            def _color(val):
                try:
                    value = float(val)
                except (TypeError, ValueError):
                    return ""
                if value < 75:
                    return "color: #dc2626; font-weight: 600;"
                if value < 85:
                    return "color: #f59e0b; font-weight: 600;"
                return "color: #16a34a; font-weight: 600;"
            styler = df_styled.style.applymap(_color, subset=["% Resueltos"])
            styler = styler.format({"% Resueltos": "{:.2f}"})
            return styler

        if team_key in df_res.columns or team_key in df_ab.columns:
            if "team_name" in df_res.columns:
                df_res = df_res[df_res["team_name"] != "CHATBOT"]
            if "team_name" in df_ab.columns:
                df_ab = df_ab[df_ab["team_name"] != "CHATBOT"]
            empresa_table = _aggregate_casos(df_res, df_ab, team_key).rename(
                columns={team_key: "Empresa"}
            )
            empresa_table = empresa_table[empresa_table["Empresa"] != "CHATBOT"]
            empresa_table = empresa_table.rename(
                columns={
                    "casos_abiertos": "Casos Recibidos",
                    "casos_resueltos": "Casos Resueltos",
                    "pct_resueltos": "% Resueltos",
                }
            )
            empresa_table = empresa_table[["Empresa", "Casos Recibidos", "Casos Resueltos", "% Resueltos"]]
            if "Casos Recibidos" in empresa_table.columns:
                empresa_table["Casos Recibidos"] = (
                    empresa_table["Casos Recibidos"].fillna(0).astype(int)
                )
            pie_df = empresa_table.copy()
            pie_df = pie_df[pie_df["Casos Recibidos"] > 0]
            if not pie_df.empty:
                fig_empresas = px.pie(
                    pie_df,
                    names="Empresa",
                    values="Casos Recibidos",
                )
                fig_empresas.update_traces(
                    textinfo="percent+label",
                    hovertemplate="%{label}: %{value} (%{percent})<extra></extra>",
                )
                fig_empresas.update_layout(margin=dict(l=0, r=0, t=0, b=0))
                with donut_cols[1]:
                    st.plotly_chart(fig_empresas, use_container_width=True)
            st.markdown("#### Resumen por unidad: Resoluciones")
            render_description(
                "Cantidad de casos recibidos y resueltos mostrando su porcentaje de resolución, en el rango de tiempo establecido por Unidad."
            )
            st.dataframe(_style_resueltos(prepare_table(empresa_table)), use_container_width=True)
            st.caption("% Resueltos: Verde mayor o igual a 85%, Amarillo entre 75% y 85%, Rojo menor al 75%.")
        else:
            st.info("No hay datos por empresa para este endpoint.")

        if "agent_email" in df_res.columns or "agent_email" in df_ab.columns:
            agente_table = _aggregate_casos(df_res, df_ab, "agent_email").rename(
                columns={"agent_email": "Agente"}
            )
            agente_table = agente_table.rename(
                columns={
                    "casos_abiertos": "Casos Recibidos",
                    "casos_resueltos": "Casos Resueltos",
                    "pct_resueltos": "% Resueltos",
                }
            )
            agente_table = agente_table[["Agente", "Casos Recibidos", "Casos Resueltos", "% Resueltos"]]
            if "Casos Recibidos" in agente_table.columns:
                agente_table["Casos Recibidos"] = (
                    agente_table["Casos Recibidos"].fillna(0).astype(int)
                )
            st.markdown("#### Resumen por agente: Resoluciones")
            render_description(
                "Cantidad de casos recibidos y resueltos mostrando su porcentaje de resolución, en el rango de tiempo establecido por cada Agente."
            )
            st.dataframe(_style_resueltos(prepare_table(agente_table)), use_container_width=True)
            st.caption("% Resueltos: Verde mayor o igual a 85%, Amarillo entre 75% y 85%, Rojo menor al 75%.")
        else:
            st.info("No hay datos por agente para este endpoint.")

        def _style_sla(df_styled: pd.DataFrame):
            if "% SLA" not in df_styled.columns:
                return df_styled
            series = pd.to_numeric(df_styled["% SLA"], errors="coerce")
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

            styler = df_styled.style.apply(_color_row, axis=1)
            styler = styler.format({"% SLA": "{:.2f}"})
            return styler

        st.markdown("#### SLA por unidad")
        render_description(
            "Service Level Agreement, basado en la cantidad de tiempo que se demora en contestar un caso, se muestra los casos recibidos por empresa, la cantidad que se respondieron y la cantidad que se encuentra dentro del rango del SLA, incluido su porcentaje. El valor de tiempo maximo de SLA se puede modificar (valor por defecto 300 segundos)."
        )
        max_seconds = st.text_input(
            "Cantidad de segundos maximos de SLA",
            value=str(DEFAULT_MAX_SECONDS),
            key="casos_atendidos_sla_max_seconds",
        )
        sla = api_client.frt_sla(start, end, int(max_seconds), "", "")
        sla_rows = sla.get("data", sla) if isinstance(sla, dict) else sla
        df_sla = pd.DataFrame(sla_rows)
        if "team_name" in df_sla.columns:
            df_sla = df_sla[df_sla["team_name"] != "CHATBOT"]

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
                resumen_equipos = api_client.frt_resumen_equipos(start, end)
                resumen_rows = (
                    resumen_equipos.get("data", resumen_equipos)
                    if isinstance(resumen_equipos, dict)
                    else resumen_equipos
                )
                df_resumen_eq = pd.DataFrame(resumen_rows)
                if "team_name" in df_resumen_eq.columns:
                    df_resumen_eq = df_resumen_eq[df_resumen_eq["team_name"] != "CHATBOT"]
                if "team_name" in df_resumen_eq.columns and "casos_abiertos" in df_resumen_eq.columns:
                    sla_team = sla_team.merge(
                        df_resumen_eq[["team_name", "casos_abiertos"]].rename(
                            columns={"team_name": "Empresa"}
                        ),
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
                sla_team = prepare_table(sla_team)
                st.dataframe(_style_sla(sla_team), use_container_width=True)
                st.caption("Verde valor mas alto en %SLA, Rojo valor mas bajo en %SLA.")
            else:
                st.info("Sin datos de SLA por empresa.")
        else:
            st.info("Sin datos de SLA por empresa.")

        st.markdown("#### Resumen por empresas: Tiempo de primera respuesta")
        render_description(
            "Muestra el tiempo que demora un agente en general en contestar por primera vez a una conversación, tenemos 3 mediciones distintas: promedio, mediana y percentil 90 (el tiempo de primera respuesta promedio en el 90% de los casos)."
        )
        resumen_equipos = api_client.frt_resumen_equipos(start, end)
        teams_rows = (
            resumen_equipos.get("data", resumen_equipos)
            if isinstance(resumen_equipos, dict)
            else resumen_equipos
        )
        df_teams = pd.DataFrame(teams_rows)
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

        st.markdown("#### Detalle por dia")
        render_description(
            "Cantidad de conversaciones entrantes comparada con la cantidad de conversaciones atendidas en ese mismo día, junto con su porcentaje correspondiente."
        )
        st.markdown(
            "Objetivo: Porcentaje de casos atendidos en el mismo dia sea mayor al 90% (verde), luego si esta entre 80% y 90% (amarillo), menor a 80% (rojo)."
        )
        table_df = prepare_table(df)
        st.dataframe(_style_atendidas(table_df), use_container_width=True)
        st.caption("% Atendidas: Verde mayor o igual a 90%, Amarillo 80% entre 90%, Rojo menos del 80%.")
        if "fecha" in df.columns and "total" in df.columns:
            fig = charts.line_chart(df, x="fecha", y="total", title="Casos atendidos")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sin datos para el rango seleccionado.")


if __name__ == "__main__":
    render()
