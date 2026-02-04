from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, Optional

import requests
import streamlit as st

from config import API_BASE_URL


@st.cache_data(ttl=300)
def get_json(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"{API_BASE_URL}{path}"
    cleaned_params = None
    if params:
        cleaned_params = {k: v for k, v in params.items() if v not in ("", None)}
    response = requests.get(url, params=cleaned_params, timeout=30)
    response.raise_for_status()
    return response.json()


def login(username: str, password: str) -> Dict[str, Any]:
    url = f"{API_BASE_URL}/auth/login"
    response = requests.post(url, json={"username": username, "password": password}, timeout=30)
    response.raise_for_status()
    return response.json()


def create_user(payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{API_BASE_URL}/users"
    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def update_user(user_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{API_BASE_URL}/users/{user_id}"
    response = requests.put(url, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def deactivate_user(user_id: int) -> Dict[str, Any]:
    url = f"{API_BASE_URL}/users/{user_id}/deactivate"
    response = requests.patch(url, json={}, timeout=30)
    response.raise_for_status()
    return response.json()


def list_users() -> Dict[str, Any]:
    url = f"{API_BASE_URL}/users"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def _recent_range(days: int) -> tuple[date, date]:
    end = date.today()
    start = end - timedelta(days=days)
    return start, end


def _recent_range_params(days: int) -> Dict[str, str]:
    start, end = _recent_range(days)
    return {"desde": str(start), "hasta": str(end)}


def get_json_with_fallback(
    path: str,
    params: Optional[Dict[str, Any]] = None,
    fallback=None,
) -> Dict[str, Any]:
    try:
        return get_json(path, params)
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404 and fallback:
            st.warning(f"Endpoint no disponible: {path}. Usando fallback por rango.")
            return fallback()
        raise


def metrics_casos_atendidos(desde: date, hasta: date) -> Dict[str, Any]:
    return get_json("/metrics/casos-atendidos", {"desde": str(desde), "hasta": str(hasta)})


def metrics_casos_atendidos_resumen(desde: date, hasta: date) -> Dict[str, Any]:
    return get_json("/metrics/casos-atendidos/resumen", {"desde": str(desde), "hasta": str(hasta)})


def casos_atendidos_ultimas_24h() -> Dict[str, Any]:
    def _fallback():
        start, end = _recent_range(1)
        return metrics_casos_atendidos(start, end)

    return get_json_with_fallback(
        "/metrics/casos-atendidos/ultimas-24h",
        _recent_range_params(1),
        fallback=_fallback,
    )


def casos_atendidos_ultimas_48h() -> Dict[str, Any]:
    def _fallback():
        start, end = _recent_range(2)
        return metrics_casos_atendidos(start, end)

    return get_json_with_fallback(
        "/metrics/casos-atendidos/ultimas-48h",
        _recent_range_params(2),
        fallback=_fallback,
    )


def casos_atendidos_ultimos_7_dias() -> Dict[str, Any]:
    def _fallback():
        start, end = _recent_range(7)
        return metrics_casos_atendidos(start, end)

    return get_json_with_fallback(
        "/metrics/casos-atendidos/ultimos-7-dias",
        _recent_range_params(7),
        fallback=_fallback,
    )


def casos_abiertos_ultimas_24h(team_uuid: str = "", agent_email: str = "") -> Dict[str, Any]:
    return get_json_with_fallback(
        "/metrics/casos-abiertos/ultimas-24h",
        {**_recent_range_params(1), "team_uuid": team_uuid, "agent_email": agent_email},
    )


def casos_abiertos_ultimas_48h(team_uuid: str = "", agent_email: str = "") -> Dict[str, Any]:
    return get_json_with_fallback(
        "/metrics/casos-abiertos/ultimas-48h",
        {**_recent_range_params(2), "team_uuid": team_uuid, "agent_email": agent_email},
    )


def casos_abiertos_ultimos_7_dias(team_uuid: str = "", agent_email: str = "") -> Dict[str, Any]:
    return get_json_with_fallback(
        "/metrics/casos-abiertos/ultimos-7-dias",
        {**_recent_range_params(7), "team_uuid": team_uuid, "agent_email": agent_email},
    )


def frt_ultimas_24h(team_uuid: str = "", agent_email: str = "") -> Dict[str, Any]:
    def _fallback():
        start, end = _recent_range(1)
        return frt_tiempo_primera_respuesta(start, end, team_uuid, agent_email)

    return get_json_with_fallback(
        "/metrics/tiempo-primera-respuesta/ultimas-24h",
        {**_recent_range_params(1), "team_uuid": team_uuid, "agent_email": agent_email},
        fallback=_fallback,
    )


def frt_ultimas_48h(team_uuid: str = "", agent_email: str = "") -> Dict[str, Any]:
    def _fallback():
        start, end = _recent_range(2)
        return frt_tiempo_primera_respuesta(start, end, team_uuid, agent_email)

    return get_json_with_fallback(
        "/metrics/tiempo-primera-respuesta/ultimas-48h",
        {**_recent_range_params(2), "team_uuid": team_uuid, "agent_email": agent_email},
        fallback=_fallback,
    )


def frt_ultimos_7_dias(team_uuid: str = "", agent_email: str = "") -> Dict[str, Any]:
    def _fallback():
        start, end = _recent_range(7)
        return frt_tiempo_primera_respuesta(start, end, team_uuid, agent_email)

    return get_json_with_fallback(
        "/metrics/tiempo-primera-respuesta/ultimos-7-dias",
        {**_recent_range_params(7), "team_uuid": team_uuid, "agent_email": agent_email},
        fallback=_fallback,
    )


def casos_resueltos_ultimas_24h(team_uuid: str = "", agent_email: str = "") -> Dict[str, Any]:
    def _fallback():
        start, end = _recent_range(1)
        return casos_resueltos(start, end, team_uuid, agent_email)

    return get_json_with_fallback(
        "/metrics/casos-resueltos/ultimas-24h",
        {**_recent_range_params(1), "team_uuid": team_uuid, "agent_email": agent_email},
        fallback=_fallback,
    )


def casos_resueltos_ultimas_48h(team_uuid: str = "", agent_email: str = "") -> Dict[str, Any]:
    def _fallback():
        start, end = _recent_range(2)
        return casos_resueltos(start, end, team_uuid, agent_email)

    return get_json_with_fallback(
        "/metrics/casos-resueltos/ultimas-48h",
        {**_recent_range_params(2), "team_uuid": team_uuid, "agent_email": agent_email},
        fallback=_fallback,
    )


def casos_resueltos_ultimos_7_dias(team_uuid: str = "", agent_email: str = "") -> Dict[str, Any]:
    def _fallback():
        start, end = _recent_range(7)
        return casos_resueltos(start, end, team_uuid, agent_email)

    return get_json_with_fallback(
        "/metrics/casos-resueltos/ultimos-7-dias",
        {**_recent_range_params(7), "team_uuid": team_uuid, "agent_email": agent_email},
        fallback=_fallback,
    )


def casos_abandonados_24h_ultimas_24h(
    team_uuid: str = "", agent_email: str = "", as_of: str = ""
) -> Dict[str, Any]:
    params = {**_recent_range_params(1), "team_uuid": team_uuid, "agent_email": agent_email}
    if as_of:
        params["as_of"] = as_of
    def _fallback():
        start, end = _recent_range(1)
        return casos_abandonados_24h(start, end, team_uuid, agent_email, as_of)

    return get_json_with_fallback(
        "/metrics/casos-abandonados-24h/ultimas-24h",
        params,
        fallback=_fallback,
    )


def casos_abandonados_24h_ultimas_48h(
    team_uuid: str = "", agent_email: str = "", as_of: str = ""
) -> Dict[str, Any]:
    params = {**_recent_range_params(2), "team_uuid": team_uuid, "agent_email": agent_email}
    if as_of:
        params["as_of"] = as_of
    def _fallback():
        start, end = _recent_range(2)
        return casos_abandonados_24h(start, end, team_uuid, agent_email, as_of)

    return get_json_with_fallback(
        "/metrics/casos-abandonados-24h/ultimas-48h",
        params,
        fallback=_fallback,
    )


def casos_abandonados_24h_ultimos_7_dias(
    team_uuid: str = "", agent_email: str = "", as_of: str = ""
) -> Dict[str, Any]:
    params = {**_recent_range_params(7), "team_uuid": team_uuid, "agent_email": agent_email}
    if as_of:
        params["as_of"] = as_of
    def _fallback():
        start, end = _recent_range(7)
        return casos_abandonados_24h(start, end, team_uuid, agent_email, as_of)

    return get_json_with_fallback(
        "/metrics/casos-abandonados-24h/ultimos-7-dias",
        params,
        fallback=_fallback,
    )

def frt_tiempo_primera_respuesta(
    desde: date, hasta: date, team_uuid: str = "", agent_email: str = ""
) -> Dict[str, Any]:
    return get_json(
        "/metrics/tiempo-primera-respuesta",
        {
            "desde": str(desde),
            "hasta": str(hasta),
            "team_uuid": team_uuid,
            "agent_email": agent_email,
        },
    )


def frt_sla(
    desde: date,
    hasta: date,
    max_seconds: int,
    team_uuid: str = "",
    agent_email: str = "",
) -> Dict[str, Any]:
    return get_json(
        "/metrics/tiempo-primera-respuesta/sla",
        {
            "desde": str(desde),
            "hasta": str(hasta),
            "max_seconds": max_seconds,
            "team_uuid": team_uuid,
            "agent_email": agent_email,
        },
    )


def frt_agentes_resumen(desde: date, hasta: date, team_uuid: str = "") -> Dict[str, Any]:
    return get_json(
        "/metrics/tiempo-primera-respuesta/agentes-resumen",
        {"desde": str(desde), "hasta": str(hasta), "team_uuid": team_uuid},
    )


def frt_ranking_agentes(
    desde: date,
    hasta: date,
    order: str = "asc",
    limit: int = 10,
    team_uuid: str = "",
) -> Dict[str, Any]:
    return get_json(
        "/metrics/tiempo-primera-respuesta/ranking-agentes",
        {
            "desde": str(desde),
            "hasta": str(hasta),
            "order": order,
            "limit": limit,
            "team_uuid": team_uuid,
        },
    )


def frt_resumen_agentes(desde: date, hasta: date) -> Dict[str, Any]:
    return get_json(
        "/metrics/tiempo-primera-respuesta/resumen-agentes",
        {"desde": str(desde), "hasta": str(hasta)},
    )


def frt_resumen_equipos(desde: date, hasta: date) -> Dict[str, Any]:
    return get_json(
        "/metrics/tiempo-primera-respuesta/resumen-equipos",
        {"desde": str(desde), "hasta": str(hasta)},
    )


def duracion_promedio(
    desde: date, hasta: date, team_uuid: str = "", agent_email: str = ""
) -> Dict[str, Any]:
    return get_json(
        "/metrics/duracion-promedio",
        {
            "desde": str(desde),
            "hasta": str(hasta),
            "team_uuid": team_uuid,
            "agent_email": agent_email,
        },
    )


def duracion_resumen_agentes(desde: date, hasta: date) -> Dict[str, Any]:
    return get_json(
        "/metrics/duracion-promedio/resumen-agentes",
        {"desde": str(desde), "hasta": str(hasta)},
    )


def duracion_resumen_equipos(desde: date, hasta: date) -> Dict[str, Any]:
    return get_json(
        "/metrics/duracion-promedio/resumen-equipos",
        {"desde": str(desde), "hasta": str(hasta)},
    )


def casos_resueltos(
    desde: date, hasta: date, team_uuid: str = "", agent_email: str = ""
) -> Dict[str, Any]:
    return get_json(
        "/metrics/casos-resueltos",
        {
            "desde": str(desde),
            "hasta": str(hasta),
            "team_uuid": team_uuid,
            "agent_email": agent_email,
        },
    )


def casos_abandonados_24h(
    desde: date,
    hasta: date,
    team_uuid: str = "",
    agent_email: str = "",
    as_of: str = "",
) -> Dict[str, Any]:
    params = {
        "desde": str(desde),
        "hasta": str(hasta),
        "team_uuid": team_uuid,
        "agent_email": agent_email,
    }
    if as_of:
        params["as_of"] = as_of
    return get_json("/metrics/casos-abandonados-24h", params)


def casos_pendientes(
    desde: date, hasta: date, team_uuid: str = "", agent_email: str = ""
) -> Dict[str, Any]:
    return get_json(
        "/metrics/casos-pendientes",
        {
            "desde": str(desde),
            "hasta": str(hasta),
            "team_uuid": team_uuid,
            "agent_email": agent_email,
        },
    )
