from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Semaforo:
    label: str
    color: str
    icon: str


def evaluar_kpi(valor: float, objetivo: float, tolerancia: float = 0.1) -> Semaforo:
    if objetivo <= 0:
        return Semaforo(label="Sin objetivo", color="gray", icon="⚪")

    ratio = valor / objetivo
    if ratio <= 1:
        return Semaforo(label="En objetivo", color="green", icon="🟢")
    if ratio <= 1 + tolerancia:
        return Semaforo(label="Cerca del umbral", color="yellow", icon="🟡")
    return Semaforo(label="Fuera de objetivo", color="red", icon="🔴")


def evaluar_porcentaje(
    valor_pct: float, red: float = 50, yellow: float = 70, green: float = 90
) -> Semaforo:
    if valor_pct >= green:
        return Semaforo(label=f">= {green}%", color="green", icon="🟢")
    if valor_pct >= yellow:
        return Semaforo(label=f">= {yellow}%", color="yellow", icon="🟡")
    if valor_pct >= red:
        return Semaforo(label=f">= {red}%", color="red", icon="🔴")
    return Semaforo(label=f"< {red}%", color="red", icon="🔴")
