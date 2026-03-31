from __future__ import annotations

import requests
import streamlit as st

from datetime import date, timedelta

from helpers.api_client import (
    create_user,
    update_user,
    deactivate_user,
    list_users,
    get_eventos,
    create_evento,
    delete_evento,
    get_json,
)


ROLE_OPTIONS = ["admin", "supervisor", "sa"]

COLOR_OPTIONS = {
    "Incidencia": "#EF553B",
    "Corte Masivo": "#FECB52",
    "Otros": "#00CC96",
}


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

    st.divider()

    # ---------------------------------------------------------------
    # Eventos en graficos de tendencias
    # ---------------------------------------------------------------
    st.subheader("Eventos en graficos de tendencias")
    st.caption(
        "Los eventos aparecen como lineas verticales punteadas en todos los graficos de la pestana Tendencias."
    )

    # Listado de eventos recientes (ultimos 90 dias + proximos 30)
    ev_desde = date.today() - timedelta(days=90)
    ev_hasta = date.today() + timedelta(days=30)
    try:
        eventos = get_eventos(ev_desde, ev_hasta)
    except requests.RequestException:
        eventos = []
        st.error("No se pudo cargar la lista de eventos.")

    HEX_TO_NAME = {v: k for k, v in COLOR_OPTIONS.items()}

    if eventos:
        # --- Table ---
        header_style = (
            "background:#1e1e1e; color:#aaa; font-size:12px; font-weight:600; "
            "text-transform:uppercase; letter-spacing:.05em; padding:8px 12px; "
            "border-bottom:1px solid #333; text-align:left;"
        )
        cell_style = (
            "padding:8px 12px; border-bottom:1px solid #2a2a2a; "
            "font-size:13px; vertical-align:top;"
        )
        rows_html = ""
        for ev in eventos:
            color_hex = ev.get("color", "#EF553B")
            tipo_name = HEX_TO_NAME.get(color_hex, color_hex)
            unidad = ev.get("unidad") or "Global"
            titulo = ev.get("titulo") or ""
            desc = ev.get("descripcion") or "—"
            fecha = ev.get("fecha") or ""
            rows_html += (
                f"<tr>"
                f"<td style='{cell_style}'>"
                f"  <span style='color:{color_hex}; font-weight:700;'>● {tipo_name}</span>"
                f"</td>"
                f"<td style='{cell_style}'>{unidad}</td>"
                f"<td style='{cell_style}'>{titulo}</td>"
                f"<td style='{cell_style}; color:#999;'>{desc}</td>"
                f"<td style='{cell_style}'>{fecha}</td>"
                f"</tr>"
            )

        table_html = f"""
        <table style='width:100%; border-collapse:collapse; margin-bottom:16px;'>
          <thead>
            <tr>
              <th style='{header_style}'>Tipo</th>
              <th style='{header_style}'>Unidad</th>
              <th style='{header_style}'>Titulo</th>
              <th style='{header_style}'>Descripcion</th>
              <th style='{header_style}'>Fecha</th>
            </tr>
          </thead>
          <tbody>{rows_html}</tbody>
        </table>
        """
        st.markdown(table_html, unsafe_allow_html=True)

        # --- Delete buttons below table ---
        st.markdown("<p style='font-size:12px; color:#666; margin-top:4px;'>Eliminar evento:</p>", unsafe_allow_html=True)
        del_cols = st.columns(len(eventos))
        for i, ev in enumerate(eventos):
            with del_cols[i]:
                label = f"{ev.get('fecha')} · {ev.get('titulo', '')[:20]}"
                if st.button(label, key=f"del_ev_{ev.get('id')}"):
                    try:
                        delete_evento(int(ev.get("id")))
                        st.success("Evento eliminado.")
                        st.rerun()
                    except requests.RequestException:
                        st.error("No se pudo eliminar el evento.")
    else:
        st.info("No hay eventos registrados en los proximos 30 dias ni en los ultimos 90.")

    # Fetch teams for the unidad selector
    try:
        _today = date.today()
        _teams_raw = get_json(
            "/metrics/equipos",
            {"desde": str(_today - timedelta(days=30)), "hasta": str(_today)},
        )
        team_names = sorted({r["team_name"] for r in (_teams_raw if isinstance(_teams_raw, list) else []) if r.get("team_name")})
    except requests.RequestException:
        team_names = []

    unidad_options = ["— Global (todas las unidades) —"] + team_names

    st.markdown("**Agregar evento**")
    with st.form("create_evento_form"):
        ev_fecha = st.date_input("Fecha del evento", value=date.today(), key="ev_fecha")
        ev_titulo = st.text_input("Titulo (max 120 caracteres)", key="ev_titulo")
        ev_desc = st.text_area("Descripcion opcional", key="ev_desc", height=80)
        ev_color_label = st.selectbox(
            "Color de la linea",
            options=list(COLOR_OPTIONS.keys()),
            index=0,
            key="ev_color",
        )
        ev_unidad_label = st.selectbox(
            "Unidad (dejar en Global para mostrar en todas)",
            options=unidad_options,
            index=0,
            key="ev_unidad",
        )
        submitted_ev = st.form_submit_button("Crear evento")

    if submitted_ev:
        if not ev_titulo.strip():
            st.warning("El titulo no puede estar vacio.")
        else:
            selected_unidad = (
                ""
                if ev_unidad_label == "— Global (todas las unidades) —"
                else ev_unidad_label
            )
            try:
                nuevo = create_evento(
                    fecha=str(ev_fecha),
                    titulo=ev_titulo.strip(),
                    descripcion=ev_desc.strip(),
                    color=COLOR_OPTIONS[ev_color_label],
                    unidad=selected_unidad,
                )
                st.success(f"Evento creado: {nuevo.get('fecha')} — {nuevo.get('titulo')}")
                st.rerun()
            except requests.RequestException:
                st.error("No se pudo crear el evento.")
