# Dashboard Metricas Callcenter

Dashboard web en Streamlit para consumir los endpoints de metricas del callcenter, con UI moderna (streamlit-shadcn-ui), graficos interactivos y semaforos de estado.

## Estructura

```
Dashboard-Metricas-Multireg/
├── app.py
├── config.py
├── requirements.txt
├── README.md
├── data/
│  └── .gitkeep
├── helpers/
│  ├── __init__.py
│  ├── api_client.py
│  ├── charts.py
│  ├── semaforos.py
│  └── utils.py
├── pages/
│  ├── __init__.py
│  ├── casos_atendidos.py
│  ├── frt.py
│  ├── duracion.py
│  ├── casos.py
│  └── llamadas.py
├── scripts/
│  └── fetch_llamadas.py
├── assets/
│  └── styles.css
├── tests/
│  ├── conftest.py
│  ├── test_api_client.py
│  ├── test_charts.py
│  └── test_semaforos.py
└── .gitignore
```

## Requisitos

- Python 3.10+

## Instalacion

```bash
python -m venv .venv
. .venv/Scripts/activate  # PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Configuracion

- Variable de entorno opcional:
  - `API_BASE_URL` (por defecto `http://localhost:8000`)
- Variables para el script de llamadas:
  - `CALLS_BASE_URL` (por defecto `https://10.0.116.10`)
  - `CALLS_USER` / `CALLS_PASS` (credenciales del sistema)
  - `CALLS_DATE_START` (por defecto `10+Jul+2025`)
  - `CALLS_OUTPUT_DIR` (por defecto `./data`)
  - `CALLS_VERIFY_SSL` (`true/false`, por defecto `false`)

## Ejecutar

```bash
streamlit run app.py
```

## UI

- Tabs principales: Casos Atendidos, Tiempo de primera respuesta, Duracion, Casos, Llamadas
- Filtros por rango de fechas y parametros opcionales
- KPIs con semaforos
- Tablas y graficos interactivos

## Llamadas (CSV)

El script `scripts/fetch_llamadas.py` descarga y prepara dos archivos:
- `data/reporte.csv` (satisfacción)
- `data/detalle_llamadas.csv` (detalle de llamadas)

Ejemplo de ejecución manual:

```bash
CALLS_BASE_URL=https://10.0.116.10 \
CALLS_USER=admin \
CALLS_PASS=******** \
python scripts/fetch_llamadas.py
```

En servidor (cron cada 15 minutos):

```bash
*/15 * * * * cd /ruta/Tablero-metricas/Dashboard-Metricas-Multireg && CALLS_USER=admin CALLS_PASS=******** python3 scripts/fetch_llamadas.py >> /var/log/fetch_llamadas.log 2>&1
```

## Tests

```bash
pytest
```
