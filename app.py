from __future__ import annotations

import streamlit as st
import streamlit_shadcn_ui as ui
import streamlit.components.v1 as components
import requests

from config import APP_TITLE
from pages import casos_atendidos, casos, duracion, frt, admin_panel
from helpers.api_client import login


st.set_page_config(page_title=APP_TITLE, layout="wide")

with open("assets/styles.css", "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown(
    "<style>[data-testid='stSidebar']{display:none;} header, [data-testid='stToolbar']{display:none;}</style>",
    unsafe_allow_html=True,
)

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "auth_user" not in st.session_state:
    st.session_state["auth_user"] = None

st.title(APP_TITLE)

if not st.session_state["authenticated"]:
    left_col, center_col, right_col = st.columns([1, 1, 1])
    with center_col:
        st.markdown("<div class='login-title'>Ingresar</div>", unsafe_allow_html=True)
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input(
                "Usuario", placeholder="usuario", key="login_username"
            )
            password = st.text_input(
                "Contraseña",
                type="password",
                placeholder="contraseña",
                key="login_password",
            )
            submitted = st.form_submit_button("Ingresar")

    components.html(
        """
        <script>
          (function () {
            const forms = window.parent.document.querySelectorAll("div[data-testid='stForm']");
            forms.forEach((form) => {
              const button = form.querySelector("button");
              if (button && button.innerText.trim() === "Ingresar") {
                form.classList.add("login-form");
                const textInputs = form.querySelectorAll("input[type='text']");
                const passInputs = form.querySelectorAll("input[type='password']");
                if (textInputs[0]) {
                  textInputs[0].setAttribute("autocomplete", "username");
                  textInputs[0].setAttribute("name", "username");
                }
                if (passInputs[0]) {
                  passInputs[0].setAttribute("autocomplete", "current-password");
                  passInputs[0].setAttribute("name", "password");
                }
              }
            });
          })();
        </script>
        """,
        height=0,
    )

    if submitted:
        try:
            user = login(username, password)
            st.session_state["authenticated"] = True
            st.session_state["auth_user"] = user
            st.rerun()
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 401:
                st.error("Usuario o contraseña incorrectos.")
            else:
                st.error("No se pudo iniciar sesión. Verifica la API.")
        except requests.RequestException:
            st.error("No se pudo conectar con la API.")

    st.stop()

auth_user = st.session_state.get("auth_user") or {}
user_role = auth_user.get("rol")

if "show_admin_panel" not in st.session_state:
    st.session_state["show_admin_panel"] = False

with st.container():
    col_title, col_user = st.columns([3, 1])
    with col_user:
        st.markdown("<div id='header-user-anchor'></div>", unsafe_allow_html=True)
        name_col, admin_col, logout_col = st.columns([1, 1, 1])
        with name_col:
            st.markdown(
                f"<span class='header-user-name'>{auth_user.get('nombre', '')} {auth_user.get('apellido', '')}</span>",
                unsafe_allow_html=True,
            )
        with admin_col:
            if user_role == "sa":
                if st.session_state.get("show_admin_panel"):
                    if st.button("Volver"):
                        st.session_state["show_admin_panel"] = False
                        st.session_state["main_tabs"] = "Inicio"
                        st.rerun()
                else:
                    if st.button("Panel de Administrador"):
                        st.session_state["show_admin_panel"] = True
                        st.rerun()
        with logout_col:
            if st.button("Cerrar sesión"):
                st.session_state["authenticated"] = False
                st.session_state["auth_user"] = None
                st.session_state["show_admin_panel"] = False
                st.rerun()

    components.html(
        """
        <script>
          (function () {
            const anchor = window.parent.document.querySelector("#header-user-anchor");
            if (!anchor) return;
            const column = anchor.closest("div[data-testid='stColumn']");
            if (!column) return;
            const row = column.querySelector("div[data-testid='stHorizontalBlock']");
            if (!row) return;
            row.classList.add("header-user-row");
          })();
        </script>
        """,
        height=0,
    )

if "main_tabs" not in st.session_state:
    st.session_state["main_tabs"] = "Inicio"

if st.session_state.get("show_admin_panel"):
    if user_role != "sa":
        st.session_state["show_admin_panel"] = False
        st.error("Acceso denegado.")
        st.stop()
    admin_panel.render()
    st.stop()

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
