# -*- coding: utf-8 -*-
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
import urllib3

# Disable SSL warnings for self-signed certificates when verify is False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y"}


def _get_output_dir() -> Path:
    base = Path(__file__).resolve().parents[1]
    env_dir = os.getenv("CALLS_OUTPUT_DIR")
    return Path(env_dir).expanduser() if env_dir else base / "data"


def _download_csv(session: requests.Session, url: str, output_path: Path) -> bool:
    response = session.get(url)
    if response.status_code != 200:
        print(f"No se pudo descargar CSV. Código HTTP: {response.status_code}")
        return False
    output_path.write_bytes(response.content)
    print(f"CSV descargado correctamente en '{output_path}'.")
    return True


def _clean_reporte_csv(path: Path) -> None:
    try:
        df = pd.read_csv(path)
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="latin1")
    if "No. de Agente" in df.columns:
        df = df[df["No. de Agente"].astype(str).str.strip().str.lower() != "total"]
        df.to_csv(path, index=False)
        print("CSV reporte CCC limpiado (fila Total removida).")


def main() -> int:
    base_url = "https://192.168.10.100"
    login_url = f"{base_url}/index.php"

    today_str = datetime.now().strftime("%d+%b+%Y")
    date_start = os.getenv("CALLS_CCC_DATE_START", "25+Jul+2025")
    date_end = os.getenv("CALLS_CCC_DATE_END", today_str)

    csv_url = (
        f"{base_url}/index.php?menu=reports_break"
        f"&txt_fecha_init={today_str}&txt_fecha_end={today_str}"
        "&exportcsv=yes&rawmode=yes"
    )

    login_data = {
        "input_user": "jmolina",
        "input_pass": "jmolina.123",
        "submit_login": "Ingresar",
    }

    output_dir = _get_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    reporte_path = output_dir / "reporte_ccc.csv"
    detalle_path = output_dir / "detalle_llamadas_ccc.csv"

    verify_ssl = _env_bool("CALLS_VERIFY_SSL", False)
    session = requests.Session()
    session.verify = verify_ssl

    session.get(login_url)
    login_response = session.post(login_url, data=login_data)

    if "logout" not in login_response.text.lower() and "cdrreport" not in login_response.text.lower():
        print("Error al iniciar sesión.")
        return 1

    print("Sesión iniciada correctamente.")
    if _download_csv(session, csv_url, reporte_path):
        _clean_reporte_csv(reporte_path)

    print("Empezando segundo archivo.")
    csv_url_2 = (
        f"{base_url}/index.php?menu=calls_detail"
        f"&date_start={date_start}&date_end={date_end}"
        f"&calltype=&agent=&queue=&phone=&id_campaign_out=&id_campaign_in="
        f"&exportcsv=yes&rawmode=yes"
    )

    _download_csv(session, csv_url_2, detalle_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
