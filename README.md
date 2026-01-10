# Dashboard Metricas Callcenter

Dashboard web en Streamlit para consumir los endpoints de metricas del callcenter, con UI moderna (streamlit-shadcn-ui), graficos interactivos y semaforos de estado.

## Estructura

```
my_dashboard/
├── app.py
├── config.py
├── requirements.txt
├── README.md
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
│  └── casos.py
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

## Ejecutar

```bash
streamlit run app.py
```

## UI

- Tabs principales: Casos Atendidos, Tiempo de primera respuesta, Duracion, Casos
- Filtros por rango de fechas y parametros opcionales
- KPIs con semaforos
- Tablas y graficos interactivos

## Tests

```bash
pytest
```
