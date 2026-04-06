from __future__ import annotations

from datetime import date as date_type, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from helpers import api_client
from helpers.utils import prepare_table, quick_range

CHATBOT_TEAM = "CHATBOT"

COLOR_NAMES = {
    "#EF553B": "Incidencia",
    "#FECB52": "Corte Masivo",
    "#00CC96": "Otros",
}
TOTAL_LABEL = "Total"
TOTAL_COLOR = "#D2691E"


def _init_state():
    if "tend_range" not in st.session_state:
        st.session_state["tend_range"] = quick_range(90)
    if "tend_mode" not in st.session_state:
        st.session_state["tend_mode"] = "90d"


def _to_list(data) -> list:
    if isinstance(data, list):
        return data
    return []


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df[df["team_name"].notna()]
    df = df[df["team_name"] != CHATBOT_TEAM]
    df["dia"] = pd.to_datetime(df["dia"])
    df = df[df["dia"].dt.date < date_type.today()]
    return df


def _load_volumen(start, end) -> pd.DataFrame:
    data = api_client.get_json("/metrics/equipos", {"desde": str(start), "hasta": str(end)})
    rows = _to_list(data)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df = df[df["team_name"].notna()]
    df = df[df["team_name"] != CHATBOT_TEAM]
    df["dia"] = pd.to_datetime(df["dia"])
    df = df[df["dia"].dt.date < date_type.today()]
    return df[["dia", "team_name", "conversaciones_entrantes"]]


def _load_abandonados(start, end) -> pd.DataFrame:
    rows = _to_list(api_client.casos_abandonados_historico(start, end))
    if not rows:
        return pd.DataFrame()
    df = _clean(pd.DataFrame(rows))
    agg = df.groupby(["dia", "team_name"], as_index=False)["casos_abandonados_24h"].sum()
    return agg


def _load_frt(start, end) -> pd.DataFrame:
    rows = _to_list(api_client.frt_tiempo_primera_respuesta(start, end))
    if not rows:
        return pd.DataFrame()
    df = _clean(pd.DataFrame(rows))
    df = df[df["avg_frt_seconds"] > 0]
    df["_w"] = df["avg_frt_seconds"] * df["casos_respondidos"]
    agg = df.groupby(["dia", "team_name"], as_index=False).agg(
        frt_sum_w=("_w", "sum"),
        frt_n=("casos_respondidos", "sum"),
    )
    agg["avg_frt_minutos"] = (agg["frt_sum_w"] / agg["frt_n"].replace(0, float("nan")) / 60).round(2)
    return agg[["dia", "team_name", "avg_frt_minutos", "frt_sum_w", "frt_n"]]


def _load_duracion(start, end) -> pd.DataFrame:
    rows = _to_list(api_client.duracion_promedio(start, end))
    if not rows:
        return pd.DataFrame()
    df = _clean(pd.DataFrame(rows))
    df = df[df["avg_duration_seconds"] > 0]
    df["_w"] = df["avg_duration_seconds"] * df["conversaciones_cerradas"]
    agg = df.groupby(["dia", "team_name"], as_index=False).agg(
        dur_sum_w=("_w", "sum"),
        dur_n=("conversaciones_cerradas", "sum"),
    )
    agg["avg_duracion_minutos"] = (
        agg["dur_sum_w"] / agg["dur_n"].replace(0, float("nan")) / 60
    ).round(2)
    return agg[["dia", "team_name", "avg_duracion_minutos", "dur_sum_w", "dur_n"]]


def _load_cerrados_mismo_dia(start, end) -> pd.DataFrame:
    rows = _to_list(api_client.casos_cerrados_mismo_dia(start, end))
    if not rows:
        return pd.DataFrame()
    df = _clean(pd.DataFrame(rows))
    agg = df.groupby(["dia", "team_name"], as_index=False).agg(
        casos_abiertos=("casos_abiertos", "sum"),
        casos_cerrados_mismo_dia=("casos_cerrados_mismo_dia", "sum"),
    )
    agg["pct_cerrados_mismo_dia"] = (
        100.0 * agg["casos_cerrados_mismo_dia"]
        / agg["casos_abiertos"].replace(0, float("nan"))
    ).round(2)
    return agg[["dia", "team_name", "pct_cerrados_mismo_dia", "casos_abiertos", "casos_cerrados_mismo_dia"]]


def _load_resueltos(start, end) -> pd.DataFrame:
    rows = _to_list(api_client.casos_resueltos(start, end))
    if not rows:
        return pd.DataFrame()
    df = _clean(pd.DataFrame(rows))
    agg = df.groupby(["dia", "team_name"], as_index=False).agg(
        casos_abiertos=("casos_abiertos", "sum"),
        casos_resueltos=("casos_resueltos", "sum"),
    )
    agg["pct_resueltos"] = (
        100.0 * agg["casos_resueltos"] / agg["casos_abiertos"].replace(0, float("nan"))
    ).round(2)
    return agg[["dia", "team_name", "pct_resueltos", "casos_abiertos", "casos_resueltos"]]


# --- Total row builders ---

def _append_total_simple(df: pd.DataFrame, selected_teams: list[str], value_col: str) -> pd.DataFrame:
    sub = df[df["team_name"].isin(selected_teams)]
    agg = sub.groupby("dia", as_index=False)[value_col].sum()
    agg["team_name"] = TOTAL_LABEL
    return pd.concat([df, agg[["dia", "team_name", value_col]]], ignore_index=True)


def _append_total_weighted(
    df: pd.DataFrame,
    selected_teams: list[str],
    value_col: str,
    sum_w_col: str,
    n_col: str,
    divisor: float = 1.0,
) -> pd.DataFrame:
    sub = df[df["team_name"].isin(selected_teams)]
    agg = sub.groupby("dia", as_index=False).agg(
        _sum_w=(sum_w_col, "sum"),
        _n=(n_col, "sum"),
    )
    agg[value_col] = (agg["_sum_w"] / agg["_n"].replace(0, float("nan")) / divisor).round(2)
    agg["team_name"] = TOTAL_LABEL
    return pd.concat([df, agg[["dia", "team_name", value_col]]], ignore_index=True)


def _append_total_ratio(
    df: pd.DataFrame,
    selected_teams: list[str],
    value_col: str,
    num_col: str,
    den_col: str,
    scale: float = 100.0,
) -> pd.DataFrame:
    sub = df[df["team_name"].isin(selected_teams)]
    agg = sub.groupby("dia", as_index=False).agg(
        _num=(num_col, "sum"),
        _den=(den_col, "sum"),
    )
    agg[value_col] = (scale * agg["_num"] / agg["_den"].replace(0, float("nan"))).round(2)
    agg["team_name"] = TOTAL_LABEL
    return pd.concat([df, agg[["dia", "team_name", value_col]]], ignore_index=True)


CHART_DESCRIPTIONS = {
    "volumen": (
        "Conversaciones nuevas abiertas cada dia.",
        "Picos sostenidos pueden señalar campanas o eventos externos. "
        "Valles abruptos suelen coincidir con feriados o problemas de ingreso de contactos. "
        "Comparar unidades permite detectar cuales absorben mas carga.",
    ),
    "abandonados": (
        "Casos cuyo ultimo mensaje fue del cliente hace ≥24h sin respuesta del agente.",
        "Un crecimiento sostenido indica sobrecarga o falta de seguimiento. "
        "Picos aislados suelen corresponder a dias de alta demanda sin refuerzo de personal. "
        "El objetivo es mantener esta curva lo mas cercana a cero posible.",
    ),
    "frt": (
        "Tiempo promedio entre la apertura del caso y el primer mensaje del agente (ponderado por casos respondidos).",
        "Valores altos señalan demoras en la atencion inicial. "
        "Si una unidad tiene FRT sistematicamente mayor, conviene revisar la distribucion de carga o los procesos de asignacion.",
    ),
    "duracion": (
        "Duracion promedio entre la apertura y el cierre de la conversacion (ponderada por conversaciones cerradas).",
        "Duraciones elevadas pueden reflejar casos complejos o falta de resolucion eficiente. "
        "Un aumento repentino en una unidad puede indicar un problema puntual de proceso o un agente sin herramientas adecuadas.",
    ),
    "resueltos": (
        "Porcentaje de conversaciones abiertas ese dia que fueron cerradas (en cualquier momento).",
        "Una tendencia descendente sostenida indica acumulacion de casos sin resolver. "
        "Unidades con porcentaje bajo de forma consistente pueden necesitar revision de criterios de cierre o refuerzo de equipo.",
    ),
    "cerrados_mismo_dia": (
        "Porcentaje de conversaciones abiertas y cerradas en el mismo dia local.",
        "Refleja la capacidad del equipo de resolver casos de forma inmediata. "
        "Valores altos indican alta eficiencia operativa. "
        "Una brecha grande entre '% resueltas' y '% cerradas mismo dia' sugiere que muchos casos se resuelven con retraso.",
    ),
}


def _render_chart_header(key: str) -> None:
    short, detail = CHART_DESCRIPTIONS[key]
    st.markdown(
        f"<p style='margin:0 0 2px 0; font-size:13px; color:#aaa;'>{short}</p>"
        f"<p style='margin:0 0 8px 0; font-size:12px; color:#777; line-height:1.4;'>{detail}</p>",
        unsafe_allow_html=True,
    )


def _render_eventos_table(eventos: list[dict]) -> None:
    if not eventos:
        return

    records = []
    colors = []
    for ev in eventos:
        color_hex = ev.get("color", "#EF553B")
        colors.append(color_hex)
        records.append({
            "Tipo": COLOR_NAMES.get(color_hex, color_hex),
            "Unidad": ev.get("unidad") or "Global",
            "Titulo": ev.get("titulo") or "",
            "Descripcion": ev.get("descripcion") or "",
            "Fecha": ev.get("fecha") or "",
        })

    df = pd.DataFrame(records)
    df = prepare_table(df)

    def _color_tipo(col):
        return [f"color: {hex_}" for hex_ in colors]

    styler = df.style.apply(_color_tipo, subset=["Tipo"])
    st.dataframe(styler, use_container_width=True)


def _load_eventos(start, end) -> list[dict]:
    try:
        data = api_client.get_eventos(start, end)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _apply_eventos(
    fig: go.Figure, eventos: list[dict], selected_teams: list[str], show_total: bool = False
) -> None:
    for ev in eventos:
        unidad = ev.get("unidad")
        # Unit-specific event: skip if that unit is not visible,
        # unless Mostrar Total is on (all data is aggregated anyway)
        if unidad and not show_total and unidad not in selected_teams:
            continue
        label = ev["titulo"]
        if unidad:
            label = f"{label} ({unidad})"
        x_val = pd.Timestamp(ev["fecha"])
        x_str = x_val.strftime("%Y-%m-%d")
        fig.add_shape(
            type="line",
            x0=x_str,
            x1=x_str,
            y0=0,
            y1=1,
            xref="x",
            yref="paper",
            line=dict(dash="dot", color=ev["color"], width=1.5),
        )
        fig.add_annotation(
            x=x_str,
            y=1,
            xref="x",
            yref="paper",
            text=label,
            showarrow=False,
            xanchor="left",
            yanchor="top",
            font=dict(size=10, color=ev["color"]),
            bgcolor="rgba(0,0,0,0.5)",
        )


def _line_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    y_label: str,
    teams: list[str],
    yformat: str = "number",
    eventos: list[dict] | None = None,
    show_total: bool = False,
) -> go.Figure:
    fig = go.Figure()

    if yformat == "percent":
        y_hover = "%{y:.1f}%"
    elif yformat == "minutes":
        y_hover = "%{y:.1f} min"
    else:
        y_hover = "%{y:.0f}"

    if df.empty or not teams:
        fig.add_annotation(
            text="Sin datos para el rango seleccionado",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=13, color="gray"),
        )
    else:
        for team in teams:
            subset = df[df["team_name"] == team].sort_values(x_col)
            if subset.empty:
                continue
            is_total = team == TOTAL_LABEL
            fig.add_trace(
                go.Scatter(
                    x=subset[x_col],
                    y=subset[y_col],
                    mode="lines+markers",
                    name=team,
                    hovertemplate=(
                        f"%{{x|%d/%m/%Y}}<br>{y_label}: {y_hover}"
                        f"<extra>{team}</extra>"
                    ),
                    line=dict(
                        width=3 if is_total else 2,
                        color=TOTAL_COLOR if is_total else None,
                    ),
                    marker=dict(size=6 if is_total else 5),
                )
            )

    fig.update_layout(
        xaxis_title=None,
        yaxis_title=y_label,
        hovermode="x unified",
        height=320,
        margin=dict(l=55, r=10, t=10, b=45),
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.01,
            font=dict(size=10),
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
        ),
        xaxis=dict(
            tickformat="%d/%m",
            tickangle=-30,
        ),
    )
    if yformat == "percent":
        fig.update_yaxes(range=[0, 100])
    if eventos:
        _apply_eventos(fig, eventos, teams, show_total=show_total)
    return fig


def render():
    st.header("Tendencias")
    _init_state()

    start, end = st.session_state["tend_range"]

    # --- Range selector ---
    range_options = ["Ultimos 7 dias", "Ultimos 30 dias", "Ultimos 90 dias", "Personalizado"]
    mode_to_label = {
        "7d": "Ultimos 7 dias",
        "30d": "Ultimos 30 dias",
        "90d": "Ultimos 90 dias",
        "custom": "Personalizado",
    }
    label_to_mode = {v: k for k, v in mode_to_label.items()}
    current_label = mode_to_label.get(st.session_state["tend_mode"], "Personalizado")

    top_cols = st.columns([5, 1], gap="small")
    with top_cols[0]:
        selected_label = st.radio(
            "Rango",
            range_options,
            index=range_options.index(current_label) if current_label in range_options else 0,
            horizontal=True,
            key="tend_range_choice",
            label_visibility="collapsed",
        )
    with top_cols[1]:
        refresh = st.button("Actualizar", key="tend_refresh", use_container_width=True)

    new_mode = label_to_mode.get(selected_label, "custom")
    if new_mode != st.session_state["tend_mode"] or refresh:
        st.session_state["tend_mode"] = new_mode
        if new_mode == "7d":
            st.session_state["tend_range"] = quick_range(7)
            start, end = st.session_state["tend_range"]
        elif new_mode == "30d":
            st.session_state["tend_range"] = quick_range(30)
            start, end = st.session_state["tend_range"]
        elif new_mode == "90d":
            st.session_state["tend_range"] = quick_range(90)
            start, end = st.session_state["tend_range"]

    if st.session_state["tend_mode"] == "custom":
        picked = st.date_input(
            "Rango de fechas",
            value=(start, end),
            key="tend_date_input",
        )
        if isinstance(picked, tuple) and len(picked) == 2:
            start, end = picked
            st.session_state["tend_range"] = (start, end)

    # --- Load all data ---
    with st.spinner("Cargando datos..."):
        df_vol = _load_volumen(start, end)
        df_aban = _load_abandonados(start, end)
        df_frt = _load_frt(start, end)
        df_dur = _load_duracion(start, end)
        df_res = _load_resueltos(start, end)
        df_cerr = _load_cerrados_mismo_dia(start, end)
        eventos = _load_eventos(start, end)

    # --- Build team list from all datasets ---
    all_teams: set[str] = set()
    for df in (df_vol, df_aban, df_frt, df_dur, df_res, df_cerr):
        if not df.empty and "team_name" in df.columns:
            all_teams.update(df["team_name"].dropna().unique())
    all_teams_sorted = sorted(all_teams)

    if not all_teams_sorted:
        st.info("No hay datos para el rango seleccionado.")
        return

    # --- Filters ---
    selected_teams = st.multiselect(
        "Unidades",
        options=all_teams_sorted,
        default=all_teams_sorted,
        key="tend_teams",
    )
    show_total = st.checkbox("Mostrar Total", value=True, key="tend_show_total")

    if not selected_teams and not show_total:
        st.warning("Selecciona al menos una unidad o activa el Total.")
        return

    # --- Append Total rows (always all units, independent of selection) ---
    df_vol  = _append_total_simple(df_vol, all_teams_sorted, "conversaciones_entrantes")
    df_aban = _append_total_simple(df_aban, all_teams_sorted, "casos_abandonados_24h")
    df_frt  = _append_total_weighted(df_frt, all_teams_sorted, "avg_frt_minutos", "frt_sum_w", "frt_n", divisor=60.0)
    df_dur  = _append_total_weighted(df_dur, all_teams_sorted, "avg_duracion_minutos", "dur_sum_w", "dur_n", divisor=60.0)
    df_res  = _append_total_ratio(df_res, all_teams_sorted, "pct_resueltos", "casos_resueltos", "casos_abiertos")
    df_cerr = _append_total_ratio(df_cerr, all_teams_sorted, "pct_cerrados_mismo_dia", "casos_cerrados_mismo_dia", "casos_abiertos")

    # Total first so it draws on top
    teams_for_chart = ([TOTAL_LABEL] if show_total else []) + selected_teams

    # --- Charts: 2 por fila ---
    st.markdown("---")

    row1 = st.columns(2, gap="large")
    with row1[0]:
        st.markdown("### Volumen de conversaciones")
        _render_chart_header("volumen")
        st.plotly_chart(
            _line_chart(df_vol, "dia", "conversaciones_entrantes", "Conv.", teams_for_chart, eventos=eventos, show_total=show_total),
            use_container_width=True,
        )
    with row1[1]:
        st.markdown("### Casos abandonados")
        _render_chart_header("abandonados")
        st.plotly_chart(
            _line_chart(df_aban, "dia", "casos_abandonados_24h", "Abandonados", teams_for_chart, eventos=eventos, show_total=show_total),
            use_container_width=True,
        )

    st.markdown("---")

    row2 = st.columns(2, gap="large")
    with row2[0]:
        st.markdown("### Tiempo de primera respuesta (FRT)")
        _render_chart_header("frt")
        st.plotly_chart(
            _line_chart(
                df_frt, "dia", "avg_frt_minutos", "FRT (min)", teams_for_chart, yformat="minutes", eventos=eventos, show_total=show_total
            ),
            use_container_width=True,
        )
    with row2[1]:
        st.markdown("### Duracion promedio")
        _render_chart_header("duracion")
        st.plotly_chart(
            _line_chart(
                df_dur, "dia", "avg_duracion_minutos", "Dur. (min)", teams_for_chart, yformat="minutes", eventos=eventos, show_total=show_total
            ),
            use_container_width=True,
        )

    st.markdown("---")

    row3 = st.columns(2, gap="large")
    with row3[0]:
        st.markdown("### % Conversaciones resueltas")
        _render_chart_header("resueltos")
        st.plotly_chart(
            _line_chart(
                df_res, "dia", "pct_resueltos", "% Resueltas", teams_for_chart, yformat="percent", eventos=eventos, show_total=show_total
            ),
            use_container_width=True,
        )
    with row3[1]:
        st.markdown("### % Conversaciones cerradas el mismo dia")
        _render_chart_header("cerrados_mismo_dia")
        st.plotly_chart(
            _line_chart(
                df_cerr,
                "dia",
                "pct_cerrados_mismo_dia",
                "% Cerradas same-day",
                teams_for_chart,
                yformat="percent",
                eventos=eventos,
                show_total=show_total,
            ),
            use_container_width=True,
        )

    # --- Eventos table ---
    if eventos:
        st.markdown("---")
        st.markdown("### Eventos")
        _render_eventos_table(eventos)
