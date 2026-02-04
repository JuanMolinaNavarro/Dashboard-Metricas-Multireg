from __future__ import annotations

import requests
import streamlit as st

from helpers.api_client import (
    create_user,
    update_user,
    deactivate_user,
    list_users,
)


ROLE_OPTIONS = ["admin", "supervisor", "sa"]


def _handle_http_error(exc: requests.HTTPError) -> None:
    if exc.response is not None and exc.response.status_code == 404:
        st.error("Usuario no encontrado.")
        return
    if exc.response is not None and exc.response.status_code == 409:
        st.error("El username ya existe.")
        return
    st.error("Error al procesar la solicitud.")


def render() -> None:
    st.header("Panel de Administrador")

    st.subheader("Usuarios registrados")
    try:
        users = list_users()
    except requests.RequestException:
        st.error("No se pudo cargar el listado de usuarios.")
        users = []

    if users:
        for user in users:
            col_info, col_edit, col_deactivate = st.columns([5, 1, 1])
            with col_info:
                estado = "Activo" if user.get("isActive") else "Inactivo"
                st.write(
                    f"#{user.get('id')} | {user.get('username')} | "
                    f"{user.get('nombre')} {user.get('apellido')} | "
                    f"Rol: {user.get('rol')} | {estado}"
                )
            with col_edit:
                if st.button("Editar", key=f"edit_{user.get('id')}"):
                    st.session_state["edit_user_id"] = user.get("id")
                    st.session_state["edit_username"] = user.get("username") or ""
                    st.session_state["edit_nombre"] = user.get("nombre") or ""
                    st.session_state["edit_apellido"] = user.get("apellido") or ""
                    st.session_state["edit_rol"] = user.get("rol") or "admin"
            with col_deactivate:
                if st.button("Desactivar", key=f"deactivate_{user.get('id')}"):
                    try:
                        deactivate_user(int(user.get("id")))
                        st.success(f"Usuario desactivado: {user.get('username')}")
                        st.rerun()
                    except requests.HTTPError as exc:
                        _handle_http_error(exc)
                    except requests.RequestException:
                        st.error("No se pudo conectar con la API.")
    else:
        st.info("No hay usuarios registrados.")

    st.divider()

    edit_user_id = st.session_state.get("edit_user_id")
    if edit_user_id:
        st.subheader("Modificar usuario")
        with st.form("update_user_form"):
            user_id = st.number_input(
                "ID de usuario",
                min_value=1,
                step=1,
                value=int(edit_user_id),
            )
            new_username = st.text_input(
                "Nuevo username (opcional)",
                value=st.session_state.get("edit_username", ""),
            )
            new_password = st.text_input("Nuevo password (opcional)", type="password")
            new_nombre = st.text_input(
                "Nuevo nombre (opcional)",
                value=st.session_state.get("edit_nombre", ""),
            )
            new_apellido = st.text_input(
                "Nuevo apellido (opcional)",
                value=st.session_state.get("edit_apellido", ""),
            )
            current_rol = st.session_state.get("edit_rol", "admin")
            rol_index = (
                ROLE_OPTIONS.index(current_rol) if current_rol in ROLE_OPTIONS else 0
            )
            new_rol = st.selectbox(
                "Nuevo rol (opcional)",
                ROLE_OPTIONS,
                index=rol_index,
            )
            submitted_update = st.form_submit_button("Modificar usuario")

        if submitted_update:
            payload = {}
            if new_username:
                payload["username"] = new_username
            if new_password:
                payload["password"] = new_password
            if new_nombre:
                payload["nombre"] = new_nombre
            if new_apellido:
                payload["apellido"] = new_apellido
            if new_rol:
                payload["rol"] = new_rol

            if not payload:
                st.warning("Ingresa al menos un campo para modificar.")
            else:
                try:
                    user = update_user(int(user_id), payload)
                    st.success(f"Usuario actualizado: {user.get('username')}")
                    st.session_state.pop("edit_user_id", None)
                    st.session_state.pop("edit_username", None)
                    st.session_state.pop("edit_nombre", None)
                    st.session_state.pop("edit_apellido", None)
                    st.session_state.pop("edit_rol", None)
                    st.rerun()
                except requests.HTTPError as exc:
                    _handle_http_error(exc)
                except requests.RequestException:
                    st.error("No se pudo conectar con la API.")
    else:
        st.subheader("Crear usuario")
        with st.form("create_user_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            nombre = st.text_input("Nombre")
            apellido = st.text_input("Apellido")
            rol = st.selectbox("Rol", ROLE_OPTIONS, index=0)
            submitted = st.form_submit_button("Crear usuario")

        if submitted:
            try:
                user = create_user(
                    {
                        "username": username,
                        "password": password,
                        "nombre": nombre,
                        "apellido": apellido,
                        "rol": rol,
                    }
                )
                st.success(f"Usuario creado: {user.get('username')}")
            except requests.HTTPError as exc:
                _handle_http_error(exc)
            except requests.RequestException:
                st.error("No se pudo conectar con la API.")
