from __future__ import annotations

from helpers.semaforos import evaluar_kpi, evaluar_porcentaje


def test_semaforo_verde():
    sem = evaluar_kpi(80, 100)
    assert sem.color == "green"


def test_semaforo_amarillo():
    sem = evaluar_kpi(105, 100, tolerancia=0.1)
    assert sem.color == "yellow"


def test_semaforo_rojo():
    sem = evaluar_kpi(130, 100)
    assert sem.color == "red"


def test_semaforo_porcentaje_thresholds():
    assert evaluar_porcentaje(45).color == "red"
    assert evaluar_porcentaje(65).color == "red"
    assert evaluar_porcentaje(75).color == "yellow"
    assert evaluar_porcentaje(95).color == "green"
