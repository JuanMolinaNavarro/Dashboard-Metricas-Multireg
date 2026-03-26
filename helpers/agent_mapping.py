from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Iterable

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

CALL_AGENT_SOURCES: tuple[tuple[Path, tuple[str, ...]], ...] = (
    (DATA_DIR / "detalle_llamadas.csv", ("Agente2", "Agente")),
    (DATA_DIR / "detalle_llamadas_ccc.csv", ("Agente",)),
    (DATA_DIR / "reporte.csv", ("Agente",)),
    (DATA_DIR / "reporte_ccc.csv", ("Nombre Agente",)),
)

# Exact overrides for emails that should always map to one specific call-agent name.
EMAIL_NAME_OVERRIDES = {
    "calltnieva@providers.com.ar": "Tomas Nieva",
    "calljrosas@providers.com.ar": "Juan Rosas",
    "calleroldan@providers.com.ar": "Esteban Roldan",
    "callsofiav@providers.com.ar": "Sofia Villafa\u00f1e",
    "operador15@viaccc.com": "Lucas Salazar",
    "supervisora_callc@multireg.com.ar": "Supervisora",
}

# Known textual aliases that should be treated as one canonical agent key.
AGENT_KEY_ALIASES = {
    "juan rosa": "juan rosas",
}

# Baseline list so mapping does not depend only on the most recent CSV slice.
STATIC_CALL_AGENT_NAMES = (
    "Mauro Soto",
    "Bruno Roldan",
    "Tomas Nieva",
    "Facundo Lizarraga",
    "Camila Zerrizuela",
    "Sofia Villafane",
    "Florencia Suero",
    "Milagros Texeira",
    "Maria Trivino",
    "Cristian Miranda",
)

_LOOKUP_PREFIX = re.compile(r"^(?:callcenter|call|agente|agent|asesor|advisor)+")
_CACHE_KEY: tuple[tuple[str, float], ...] | None = None
_CACHE_NAMES: tuple[str, ...] = tuple()


def _fix_mojibake(value: str) -> str:
    if "\u00c3" not in value and "\u00c2" not in value:
        return value
    try:
        return value.encode("latin1").decode("utf-8")
    except UnicodeError:
        return value


def normalize_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    text = _fix_mojibake(text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_agent_key(value: object) -> str:
    key = normalize_text(value)
    if not key:
        return ""
    return AGENT_KEY_ALIASES.get(key, key)


def _normalize_compact(value: object) -> str:
    return normalize_text(value).replace(" ", "")


def _read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin1")


def _load_names_from_csv(path: Path, columns: tuple[str, ...]) -> set[str]:
    if not path.exists():
        return set()
    df = _read_csv(path)
    names: set[str] = set()
    for column in columns:
        if column not in df.columns:
            continue
        values = df[column].dropna().astype(str).str.strip()
        names.update(value for value in values if value and value.lower() != "nan")
    return names


def _dedupe_names(names: Iterable[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for name in names:
        clean = " ".join(str(name).split())
        key = normalize_text(clean)
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(clean)
    return deduped


def get_call_agent_names() -> list[str]:
    global _CACHE_KEY, _CACHE_NAMES

    cache_key: list[tuple[str, float]] = []
    for path, _columns in CALL_AGENT_SOURCES:
        cache_key.append((str(path), path.stat().st_mtime if path.exists() else -1.0))
    cache_key_tuple = tuple(cache_key)
    if cache_key_tuple == _CACHE_KEY:
        return list(_CACHE_NAMES)

    names: set[str] = set(STATIC_CALL_AGENT_NAMES)
    for path, columns in CALL_AGENT_SOURCES:
        names.update(_load_names_from_csv(path, columns))

    deduped = _dedupe_names(names)
    _CACHE_KEY = cache_key_tuple
    _CACHE_NAMES = tuple(sorted(deduped))
    return list(_CACHE_NAMES)


def _name_tokens(name: str) -> list[str]:
    return [token for token in normalize_text(name).split(" ") if token]


def _email_lookup_key(agent_email: str) -> str:
    local_part = str(agent_email).strip().split("@", 1)[0]
    local_part = _normalize_compact(local_part)
    local_part = _LOOKUP_PREFIX.sub("", local_part)
    return local_part


def _first_last(tokens: list[str]) -> tuple[str, str] | None:
    if len(tokens) < 2:
        return None
    return tokens[0], tokens[-1]


def resolve_agent_name(agent_email: str, call_agent_names: Iterable[str] | None = None) -> str:
    email = str(agent_email).strip()
    if not email:
        return email

    override = EMAIL_NAME_OVERRIDES.get(email.lower())
    if override:
        return override

    names = _dedupe_names(call_agent_names) if call_agent_names is not None else get_call_agent_names()
    lookup_key = _email_lookup_key(email)
    if not lookup_key:
        return email

    full_name_matches: list[str] = []
    initial_last_matches: list[str] = []
    suffix_matches: list[str] = []
    for name in names:
        parsed = _first_last(_name_tokens(name))
        if parsed is None:
            continue
        first_name, last_name = parsed
        if lookup_key == f"{first_name}{last_name}":
            full_name_matches.append(name)
        if lookup_key == f"{first_name[:1]}{last_name}":
            initial_last_matches.append(name)
        if lookup_key.endswith(last_name) and lookup_key.startswith(first_name[:1]):
            suffix_matches.append(name)

    if len(full_name_matches) == 1:
        return full_name_matches[0]
    if len(initial_last_matches) == 1:
        return initial_last_matches[0]
    if len(suffix_matches) == 1:
        return suffix_matches[0]
    return email


def with_agent_display_names(
    df: pd.DataFrame,
    email_col: str = "agent_email",
    display_col: str = "agent_name",
    call_agent_names: Iterable[str] | None = None,
) -> pd.DataFrame:
    if df is None or df.empty or email_col not in df.columns:
        return df

    names = _dedupe_names(call_agent_names) if call_agent_names is not None else get_call_agent_names()
    mapped = df.copy()
    mapped[display_col] = mapped[email_col].apply(lambda email: resolve_agent_name(email, names))
    return mapped
