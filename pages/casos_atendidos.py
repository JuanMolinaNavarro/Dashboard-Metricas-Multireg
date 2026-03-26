from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from config import DEFAULT_MAX_SECONDS
from helpers import api_client
from helpers.agent_mapping import normalize_agent_key, with_agent_display_names
from helpers.calls_ranking import load_attended_calls_by_agent
from helpers.utils import date_range_picker, prepare_table, quick_range, render_description


def _init_state(key: str) -> None:
    if key not in st.session_state:
        st.session_state[key] = quick_range(7)
    if "casos_atendidos_mode" not in st.session_state:
        st.session_state["casos_atendidos_mode"] = "custom"


def _extract_rows(payload) -> list[dict]:
    if isinstance(payload, dict):
        data = payload.get("data", [])
        return data if isinstance(data, list) else []
    return payload if isinstance(payload, list) else []


def _aggregate_casos(df_r: pd.DataFrame, df_a: pd.DataFrame, key: str) -> pd.DataFrame:
    res_group = (
        df_r.groupby(key, dropna=False, as_index=False).agg(
            casos_abiertos_res=("casos_abiertos", "sum"),
            casos_resueltos=("casos_resueltos", "sum"),
        )
        if not df_r.empty
        else pd.DataFrame(columns=[key, "casos_abiertos_res", "casos_resueltos"])
    )
    ab_group = (
        df_a.groupby(key, dropna=False, as_index=False).agg(
            casos_abiertos_ab=("casos_abiertos", "sum"),
            casos_abandonados=("casos_abandonados_24h", "sum"),
        )
        if not df_a.empty
        else pd.DataFrame(columns=[key, "casos_abiertos_ab", "casos_abandonados"])
    )

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
    return merged[
        [key, "casos_abiertos", "casos_resueltos", "pct_resueltos", "casos_abandonados", "pct_abandonados"]
    ]


def _render_kpi_card(label: str, value: int) -> None:
    st.markdown(
        f"""
<div class="kpi-card">
  <div style="font-size: 14px; opacity: 0.8;">{label}</div>
  <div style="font-size: 32px; font-weight: 700;">{value}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def _style_atendidas(df_styled: pd.DataFrame):
    if "% Atendidas" not in df_styled.columns:
        return df_styled

    def _color(value):
        try:
            pct = float(value)
        except (TypeError, ValueError):
            return ""
        if pct < 80:
            return "color: #dc2626; font-weight: 600;"
        if pct < 90:
            return "color: #f59e0b; font-weight: 600;"
        return "color: #16a34a; font-weight: 600;"

    styler = df_styled.style.applymap(_color, subset=["% Atendidas"])
    return styler.format({"% Atendidas": "{:.2f}"})


def _style_ranking(df_numeric: pd.DataFrame):
    df_display = prepare_table(df_numeric)
    styler = df_display.style

    score_cols = [
        "Casos Resueltos (WhatsApp)",
        "Llamadas Atendidas",
        "% Casos en SLA",
        "% Casos Resueltos",
        "% Casos Abandonados",
        "Score",
    ]

    for column in score_cols:
        if column not in df_numeric.columns:
            continue

        series = pd.to_numeric(df_numeric[column], errors="coerce").dropna()
        if series.empty:
            continue

        if column == "% Casos Abandonados":
            best_value = float(series.min())
            worst_value = float(series.max())
        else:
            best_value = float(series.max())
            worst_value = float(series.min())

        if best_value == worst_value:
            continue

        def _color_value(value, best=best_value, worst=worst_value):
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                return ""
            if numeric == best:
                return "color: #16a34a; font-weight: 700;"
            if numeric == worst:
                return "color: #dc2626; font-weight: 700;"
            return ""

        styler = styler.applymap(_color_value, subset=[column])

    if "Score" in df_display.columns:
        styler = styler.set_properties(subset=["Score"], **{"background-color": "#0072a0"})

    styler = styler.format(
        {
            "% Casos en SLA": "{:.2f}",
            "% Casos Resueltos": "{:.2f}",
            "% Casos Abandonados": "{:.2f}",
            "Score": "{:.2f}",
        }
    )
    return styler


def _build_ranking_df(start, end) -> pd.DataFrame:
    ranking = api_client.frt_ranking_agentes_compuesto(
        start,
        end,
        max_seconds=DEFAULT_MAX_SECONDS,
        limit=100,
        team_uuid="",
    )
    rank_df = pd.DataFrame(_extract_rows(ranking))
    if rank_df.empty or "agent_email" not in rank_df.columns:
        return pd.DataFrame()

    rank_df = rank_df[rank_df["agent_email"].notna()].copy()
    if rank_df.empty:
        return pd.DataFrame()

    rank_df = with_agent_display_names(rank_df, email_col="agent_email", display_col="agent_name")
    calls_by_agent = load_attended_calls_by_agent(start, end)
    rank_df["Llamadas Atendidas"] = (
        rank_df["agent_name"]
        .apply(lambda name: int(calls_by_agent.get(normalize_agent_key(name), 0)))
        .astype(int)
    )

    rank_df["Casos Resueltos (WhatsApp)"] = (
        pd.to_numeric(rank_df.get("casos_resueltos"), errors="coerce")
        .fillna(0)
        .clip(lower=0)
        .astype(int)
    )
    rank_df["% Casos en SLA"] = pd.to_numeric(rank_df.get("pct_sla"), errors="coerce").fillna(0.0)
    rank_df["% Casos Resueltos"] = pd.to_numeric(rank_df.get("pct_resueltos"), errors="coerce").fillna(0.0)
    rank_df["% Casos Abandonados"] = (
        pd.to_numeric(rank_df.get("pct_abandonados_24h"), errors="coerce").fillna(0.0)
    )

    score_base = pd.to_numeric(rank_df.get("score_final"), errors="coerce").fillna(0.0)
    puntos_resueltos = (rank_df["Casos Resueltos (WhatsApp)"] // 5).astype(int)
    puntos_llamadas = (rank_df["Llamadas Atendidas"] // 2).astype(int)
    rank_df["Score"] = (score_base + puntos_resueltos + puntos_llamadas).round(2)

    rank_df["Agente"] = rank_df["agent_name"].fillna(rank_df["agent_email"]).astype(str)
    rank_df = rank_df[
        [
            "Agente",
            "Casos Resueltos (WhatsApp)",
            "Llamadas Atendidas",
            "% Casos en SLA",
            "% Casos Resueltos",
            "% Casos Abandonados",
            "Score",
        ]
    ]
    rank_df = rank_df.sort_values(["Score", "Agente"], ascending=[False, True]).reset_index(drop=True)
    return rank_df


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
        if st.button("Actualizar", key="ca_refresh", use_container_width=True):
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
        pct_val = float(resumen.get("pct_atendidas", (atendidas / entradas * 100) if entradas else 0.0))

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
            st.markdown("#### Porcentaje de Casos Atendidos en el mismo día")
            render_description(
                "Porcentaje de casos recibidos que fueron atendidos en el mismo día en el que ingresaron. (Verde mayor o igual a 75%, Amarillo entre 60% y 75%, Rojo menor a 60%)"
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

        df_res = pd.DataFrame(_extract_rows(casos_resueltos))
        df_ab = pd.DataFrame(_extract_rows(casos_abandonados))
        team_key = "team_name" if "team_name" in df_res.columns or "team_name" in df_ab.columns else "team_uuid"
        if team_key in df_res.columns or team_key in df_ab.columns:
            if team_key not in df_res.columns:
                df_res[team_key] = None
            if team_key not in df_ab.columns:
                df_ab[team_key] = None
            if "team_name" in df_res.columns:
                df_res = df_res[df_res["team_name"] != "CHATBOT"]
            if "team_name" in df_ab.columns:
                df_ab = df_ab[df_ab["team_name"] != "CHATBOT"]

            empresa_table = _aggregate_casos(df_res, df_ab, team_key).rename(columns={team_key: "Empresa"})
            empresa_table = empresa_table[empresa_table["Empresa"] != "CHATBOT"]
            empresa_table = empresa_table.rename(columns={"casos_abiertos": "Casos Recibidos"})
            pie_df = empresa_table[["Empresa", "Casos Recibidos"]].copy()
            pie_df["Casos Recibidos"] = pd.to_numeric(pie_df["Casos Recibidos"], errors="coerce").fillna(0)
            pie_df = pie_df[pie_df["Casos Recibidos"] > 0]
            with donut_cols[1]:
                if not pie_df.empty:
                    fig_empresas = px.pie(pie_df, names="Empresa", values="Casos Recibidos")
                    fig_empresas.update_traces(
                        textinfo="percent+label",
                        hovertemplate="%{label}: %{value} (%{percent})<extra></extra>",
                    )
                    fig_empresas.update_layout(margin=dict(l=0, r=0, t=0, b=0))
                    st.plotly_chart(fig_empresas, use_container_width=True)
                else:
                    st.info("Sin datos para la distribucion por unidad.")
        else:
            with donut_cols[1]:
                st.info("Sin datos para la distribucion por unidad.")

        df_pend = pd.DataFrame(_extract_rows(pendientes))
        casos_pendientes = (
            float(df_pend["casos_pendientes"].sum())
            if not df_pend.empty and "casos_pendientes" in df_pend.columns
            else 0.0
        )
        casos_en_curso = entradas - casos_pendientes

        kpi_cols = st.columns(4)
        with kpi_cols[0]:
            _render_kpi_card("Casos recibidos", int(entradas))
        with kpi_cols[1]:
            _render_kpi_card("Casos Pendientes", int(casos_pendientes))
        with kpi_cols[2]:
            _render_kpi_card("Atendidos mismo dia", int(atendidas))
        with kpi_cols[3]:
            _render_kpi_card("Casos en curso", int(casos_en_curso))

        st.markdown("#### Ranking de agentes")
        ranking_df = _build_ranking_df(start, end)
        if not ranking_df.empty:
            styler = _style_ranking(ranking_df)
            st.dataframe(styler, use_container_width=True)
        else:
            st.info("Sin datos de ranking para el rango seleccionado.")
    else:
        st.info("Resumen no disponible para el rango seleccionado.")

    rows = _extract_rows(data)
    df = pd.DataFrame(rows)
    if df.empty:
        st.info("Sin datos para el rango seleccionado.")
        return

    if "team_uuid" in df.columns:
        df = df.drop(columns=["team_uuid"])
    if "team_name" in df.columns:
        df = df[df["team_name"] != "CHATBOT"]
    if "pct_atendidas" in df.columns:
        df["pct_atendidas"] = pd.to_numeric(df["pct_atendidas"], errors="coerce").fillna(0).round(2)

    df = df.rename(
        columns={
            "dia": "Dia",
            "agent_email": "Agente",
            "conversaciones_entrantes": "Casos Recibidos",
            "conversaciones_atendidas_same_day": "Casos Atendidos (Mismo Dia)",
            "pct_atendidas": "% Atendidas",
        }
    )

    st.markdown("#### Detalle por dia")
    render_description(
        "Cantidad de casos recibidos comparada con la cantidad de casos atendidos en ese mismo día, junto con su porcentaje correspondiente."
    )
    st.markdown(
        "Objetivo: Porcentaje de casos atendidos en el mismo dia sea mayor al 90% (verde), luego si esta entre 80% y 90% (amarillo), menor a 80% (rojo)."
    )
    st.dataframe(_style_atendidas(prepare_table(df)), use_container_width=True)
    st.caption("% Atendidas: Verde mayor o igual a 90%, Amarillo 80% entre 90%, Rojo menos del 80%.")


if __name__ == "__main__":
    render()
