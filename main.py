from nicegui import ui
from supabase import create_client
import os

# --- CONEXIÓN ---
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# --- LÓGICA DE NEGOCIO ---
def handle_login(u, p):
    try:
        res = supabase.table("users").select("*").eq("username", u).execute()
        if res.data and res.data[0]['password'] == p:
            user = res.data[0]
            # Guardamos datos básicos en la sesión de la app
            ui.navigate.to(f'/manager/{user["org_id"]}')
        else:
            ui.notify('Acceso denegado', type='negative')
    except:
        ui.notify('Error de conexión', type='negative')

# --- PÁGINA DE LOGIN ---
@ui.page('/')
def login_page():
    with ui.card().classes('absolute-center shadow-10 pa-lg').style('width: 350px'):
        ui.label('🧬 AUDEO').classes('text-h4 text-center full-width text-blue-9')
        u_input = ui.input('Usuario')
        p_input = ui.input('Password', password=True)
        ui.button('ENTRAR', on_click=lambda: handle_login(u_input.value, p_input.value)).classes('full-width q-mt-md')

# --- PÁGINA DEL MANAGER (B2B) ---
@ui.page('/manager/{org_id}')
def manager_dashboard(org_id: str):
    # 1. Recuperar equipo de la DB
    res = supabase.table("users").select("username, role").eq("org_id", org_id).execute()
    equipo = res.data if res.data else []

    with ui.header().classes('bg-blue-9'):
        ui.label(f'Panel Manager: {org_id}').classes('text-h6')
        ui.button('Salir', on_click=lambda: ui.navigate.to('/')).props('flat color=white')

    with ui.column().classes('w-full max-w-4xl mx-auto q-pa-md'):
        ui.label('Mi Equipo').classes('text-h4 q-mb-md')
        
        # Tabla NiceGUI (Mucho más rápida y limpia que Streamlit)
        columns = [
            {'name': 'username', 'label': 'Usuario', 'field': 'username', 'sortable': True},
            {'name': 'role', 'label': 'Rol', 'field': 'role'}
        ]
        ui.table(columns=columns, rows=equipo, row_key='username').classes('w-full shadow-2')

        with ui.card().classes('q-mt-lg pa-md bg-grey-2'):
            ui.label('Añadir nuevo alumno').classes('text-h6')
            with ui.row():
                new_u = ui.input('Email')
                new_p = ui.input('Pass')
                ui.button('Crear', on_click=lambda: ui.notify('Usuario creado (lógica pendiente)')).props('icon=add')

ui.run(port=int(os.environ.get("PORT", 8080)), title="Audeo Platform")