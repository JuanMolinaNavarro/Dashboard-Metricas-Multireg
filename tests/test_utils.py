from __future__ import annotations

import pandas as pd

from helpers.utils import prepare_table


def test_prepare_table_maps_agent_email_columns():
    df = pd.DataFrame(
        {
            "Agente": ["calltnieva@providers.com.ar", "N/A"],
            "agent_email": ["calljrosas@providers.com.ar", "sin-correo"],
            "valor": [1.236, 2.999],
        }
    )

    prepared = prepare_table(df)

    assert prepared.loc[1, "Agente"] == "Tomas Nieva"
    assert prepared.loc[1, "agent_email"] == "Juan Rosas"
    assert prepared.loc[2, "Agente"] == "N/A"
    assert prepared.loc[2, "agent_email"] == "sin-correo"
    assert prepared.loc[1, "valor"] == 1.24
    assert prepared.loc[2, "valor"] == 3.0
