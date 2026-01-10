from __future__ import annotations

import pandas as pd

from helpers import charts


def test_line_chart_returns_figure():
    df = pd.DataFrame({"fecha": ["2024-01-01"], "total": [1]})
    fig = charts.line_chart(df, x="fecha", y="total")
    assert fig is not None


def test_ranking_chart_returns_figure():
    df = pd.DataFrame({"agente": ["A"], "segundos": [120]})
    fig = charts.ranking_chart(df, x="agente", y="segundos")
    assert fig is not None
