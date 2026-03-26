from __future__ import annotations

import pandas as pd

from helpers.agent_mapping import (
    normalize_agent_key,
    normalize_text,
    resolve_agent_name,
    with_agent_display_names,
)


def test_normalize_text_strips_diacritics_and_symbols():
    value = "  Sof\u00eda Villafa\u00f1e  "
    assert normalize_text(value) == "sofia villafane"


def test_resolve_agent_name_matches_initial_plus_last_name():
    names = ["Tomas Nieva", "Camila Zerrizuela"]
    assert resolve_agent_name("calltnieva@providers.com.ar", names) == "Tomas Nieva"
    assert resolve_agent_name("callczerrizuela@providers.com.ar", names) == "Camila Zerrizuela"


def test_resolve_agent_name_returns_email_when_unmapped():
    names = ["Mauro Soto"]
    email = "agentedesconocido@providers.com.ar"
    assert resolve_agent_name(email, names) == email


def test_resolve_agent_name_uses_supervisora_override():
    assert resolve_agent_name("supervisora_callc@multireg.com.ar", []) == "Supervisora"


def test_normalize_agent_key_merges_juan_rosa_alias():
    assert normalize_agent_key("Juan Rosa") == "juan rosas"
    assert normalize_agent_key("Juan Rosas") == "juan rosas"


def test_with_agent_display_names_adds_agent_name_column():
    df = pd.DataFrame(
        {
            "agent_email": [
                "calltnieva@providers.com.ar",
                "callmsoto@providers.com.ar",
            ]
        }
    )
    mapped = with_agent_display_names(
        df,
        email_col="agent_email",
        display_col="agent_name",
        call_agent_names=["Tomas Nieva", "Mauro Soto"],
    )

    assert list(mapped["agent_name"]) == ["Tomas Nieva", "Mauro Soto"]
