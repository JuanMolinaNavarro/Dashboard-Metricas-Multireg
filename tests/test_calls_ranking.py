from __future__ import annotations

from datetime import date

import pandas as pd

from helpers.calls_ranking import count_attended_calls


def test_count_attended_calls_filters_status_and_date_range():
    df = pd.DataFrame(
        {
            "Fecha": ["2026-03-25", "2026-03-25", "2026-03-24", "2026-03-24", "2026-03-20"],
            "Agente2": [
                "Mauro Soto",
                "Mauro Soto",
                "Camila Zerrizuela",
                "Juan Rosa",
                "Mauro Soto",
            ],
            "Estado": ["Success", "activa", "resolved", "success", "success"],
        }
    )

    result = count_attended_calls(
        df,
        start=date(2026, 3, 24),
        end=date(2026, 3, 25),
        date_col="Fecha",
        agent_cols=("Agente2", "Agente"),
    )

    assert result == {
        "mauro soto": 1,
        "camila zerrizuela": 1,
        "juan rosas": 1,
    }


def test_count_attended_calls_uses_first_existing_agent_column():
    df = pd.DataFrame(
        {
            "Hora Inicio": ["2026-03-25 09:00:00", "2026-03-25 10:00:00"],
            "Agente": ["Sofia Villafañe", "Sofia Villafañe"],
            "Estado": ["Success", "Success"],
        }
    )

    result = count_attended_calls(
        df,
        start=date(2026, 3, 25),
        end=date(2026, 3, 25),
        date_col="Hora Inicio",
        agent_cols=("Nombre Agente", "Agente"),
    )

    assert result == {"sofia villafane": 2}
