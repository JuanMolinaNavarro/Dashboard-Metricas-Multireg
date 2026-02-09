# -*- coding: utf-8 -*-
import io
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
import urllib3

# Disable SSL warnings for self-signed certificates when verify is False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

AGENTES = {
    "5001": "Mauro Soto",
    "5004": "Bruno Roldan",
    "5005": "Tomas Nieva",
    "5006": "Facundo Lizarraga",
    "5007": "Camila Zerrizuela",
    "5008": "Sofia Villafañe",
    "5009": "Florencia Suero",
    "5010": "Milagros Texeira",
    "5011": "Maria Triviño",
    "5012": "Cristian Miranda",
}


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y"}


def _get_output_dir() -> Path:
    base = Path(__file__).resolve().parents[1]
    env_dir = os.getenv("CALLS_OUTPUT_DIR")
    return Path(env_dir).expanduser() if env_dir else base / "data"


def _map_agente(text: str) -> str:
    try:
        if not isinstance(text, str):
            return ""
        if "SIP/" in text:
            start = text.index("SIP/") + 4
            code = text[start : start + 4]
            return AGENTES.get(code, code)
        return ""
    except Exception:
        return ""


def _map_satisfaccion(destino) -> str:
    mapping = {
        "6005": "5. Muy satisfecho",
        "6004": "4. Satisfecho",
        "6003": "3. Neutral",
        "6002": "2. Insatisfecho",
        "6001": "1. Muy insatisfecho",
    }
    return mapping.get(str(destino), "Otro")


def _download_csv(session: requests.Session, url: str, output_path: Path) -> bool:
    response = session.get(url)
    if response.status_code != 200:
        print(f"No se pudo descargar CSV. Código HTTP: {response.status_code}")
        return False
    if "csv" not in response.headers.get("Content-Type", "").lower():
        print("La respuesta no parece ser CSV. Se guardará para inspección.")
        output_path.write_bytes(response.content)
        return False
    output_path.write_bytes(response.content)
    print(f"CSV descargado correctamente en '{output_path}'.")
    return True


def _process_reporte_csv(path: Path) -> None:
    df = pd.read_csv(path)

    if "Canal destino" in df.columns:
        df["Agente"] = df["Canal destino"].apply(_map_agente)

    if "Destino" in df.columns:
        df["Satisfaccion"] = df["Destino"].apply(_map_satisfaccion)

    df.to_csv(path, index=False)
    print("CSV reporte modificado y guardado.")


def _process_detalle_csv(text: str, output_path: Path) -> None:
    df = pd.read_csv(io.StringIO(text))

    required = ["Agente", "Hora Inicio", "Hora Fin", "Duración", "Tiempo Espera", "Estado"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        print(f"Faltan columnas en detalle CSV: {', '.join(missing)}")

    available_cols = [col for col in required if col in df.columns]
    df = df[available_cols]

    if "Agente" in df.columns:
        df["Agente"] = df["Agente"].fillna(0)
        df["Agente"] = df["Agente"].astype(str).str.replace(".0", "", regex=False)
        df = df[~df["Agente"].isin(["5002", "5003", "5010"])]

    if "Hora Inicio" in df.columns:
        df["Hora Inicio"] = pd.to_datetime(df["Hora Inicio"], errors="coerce")
    if "Hora Fin" in df.columns:
        df["Hora Fin"] = pd.to_datetime(df["Hora Fin"], errors="coerce")

    if "Hora Inicio" in df.columns and "Hora Fin" in df.columns:
        df["Hora Inicio"] = df["Hora Inicio"].fillna(df["Hora Fin"])
        df["Hora"] = df["Hora Inicio"].dt.strftime("%H:00")
        df["Hora Inicio"] = df["Hora Inicio"].dt.date
        df = df.rename(columns={"Hora Inicio": "Fecha"})
        df = df.drop(columns=["Hora Fin"])

    if "Tiempo Espera" in df.columns:
        df["Tiempo Espera"] = (
            pd.to_timedelta(df["Tiempo Espera"], errors="coerce")
            .dt.total_seconds()
            .fillna(0)
            .astype(int)
        )

    if "Duración" in df.columns:
        df["Duración"] = df["Duración"].replace("-", "0", regex=False)
        df["Duración"] = (
            pd.to_timedelta(df["Duración"], errors="coerce")
            .dt.total_seconds()
            .fillna(0)
            .astype(int)
        )
        df["Franja Duración"] = (df["Duración"] // 60).astype(int)

    if "Agente" in df.columns:
        df["Agente2"] = df["Agente"].map(AGENTES)

    if "Estado" in df.columns:
        df = df[df["Estado"].ne("End Monitor")]

    df.to_csv(output_path, index=False)
    print("Archivo detalle guardado correctamente.")


def main() -> int:
    base_url = os.getenv("CALLS_BASE_URL", "https://10.0.116.10").rstrip("/")
    login_url = f"{base_url}/index.php"

    date_start = os.getenv("CALLS_DATE_START", "10+Jul+2025")
    date_end = datetime.now().strftime("%d+%b+%Y")

    csv_url = (
        f"{base_url}/index.php?menu=cdrreport&date_start={date_start}&date_end={date_end}"
        "&field_name=dst&field_pattern=600&status=ALL&ringgroup=&exportcsv=yes&rawmode=yes"
    )

    login_data = {
        "input_user": os.getenv("CALLS_USER", ""),
        "input_pass": os.getenv("CALLS_PASS", ""),
        "submit_login": "Ingresar",
    }

    output_dir = _get_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    reporte_path = output_dir / "reporte.csv"
    detalle_path = output_dir / "detalle_llamadas.csv"

    verify_ssl = _env_bool("CALLS_VERIFY_SSL", False)
    session = requests.Session()
    session.verify = verify_ssl

    if not login_data["input_user"] or not login_data["input_pass"]:
        print("Faltan credenciales. Define CALLS_USER y CALLS_PASS.")
        return 1

    session.get(login_url)
    login_response = session.post(login_url, data=login_data)

    if "logout" not in login_response.text.lower() and "cdrreport" not in login_response.text.lower():
        print("Error al iniciar sesión.")
        return 1

    print("Sesión iniciada correctamente.")
    if _download_csv(session, csv_url, reporte_path):
        _process_reporte_csv(reporte_path)

    print("Empezando segundo archivo.")
    hoy = datetime.today().strftime("%d+%b+%Y")
    csv_url_2 = (
        f"{base_url}/index.php?menu=calls_detail"
        f"&date_start=01+Jan+2023&date_end={hoy}"
        f"&calltype=&agent=&queue=&phone=&id_campaign_out=&id_campaign_in="
        f"&exportcsv=yes&rawmode=yes"
    )

    response_csv = session.get(csv_url_2)
    if response_csv.status_code != 200:
        print(f"Error al descargar CSV 2: {response_csv.status_code}")
        return 1

    _process_detalle_csv(response_csv.text, detalle_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
