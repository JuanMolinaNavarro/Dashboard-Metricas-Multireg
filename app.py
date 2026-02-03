from __future__ import annotations

import streamlit as st
import streamlit_shadcn_ui as ui

from config import APP_TITLE
from pages import casos_atendidos, casos, duracion, frt


st.set_page_config(page_title=APP_TITLE, layout="wide")

with open("assets/styles.css", "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown(
    "<style>[data-testid='stSidebar']{display:none;} header, [data-testid='stToolbar']{display:none;}</style>",
    unsafe_allow_html=True,
)

st.title(APP_TITLE)

if "main_tabs" not in st.session_state:
    st.session_state["main_tabs"] = "Inicio"

# Usar selectbox para mejor experiencia mobile
selected_tab = st.selectbox(
    "Sección",
    ["Inicio", "Tiempo de primera respuesta", "Duracion", "Abandonos"],
    index=["Inicio", "Tiempo de primera respuesta", "Duracion", "Abandonos"].index(
        st.session_state["main_tabs"]
    ),
    key="main_tabs",
    label_visibility="collapsed",
)

if selected_tab == "Inicio":
    casos_atendidos.render()
elif selected_tab == "Tiempo de primera respuesta":
    frt.render()
elif selected_tab == "Duracion":
    duracion.render()
elif selected_tab == "Abandonos":
    casos.render()
