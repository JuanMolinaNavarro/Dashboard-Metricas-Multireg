from __future__ import annotations

from typing import Iterable

import pandas as pd
import plotly.express as px


def line_chart(df: pd.DataFrame, x: str, y: str, title: str = ""):
    return px.line(df, x=x, y=y, title=title, markers=True)


def bar_chart(df: pd.DataFrame, x: str, y: str, title: str = ""):
    return px.bar(df, x=x, y=y, title=title, text=y)


def ranking_chart(df: pd.DataFrame, x: str, y: str, title: str = ""):
    fig = px.bar(df, x=x, y=y, title=title, orientation="h")
    fig.update_layout(yaxis=dict(autorange="reversed"))
    return fig


def ensure_dataframe(data: Iterable[dict]) -> pd.DataFrame:
    return pd.DataFrame(list(data))
