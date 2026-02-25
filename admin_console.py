import os
import pandas as pd
import io
import json
from nicegui import ui
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = None
try:
    if SUPABASE_URL and SUPABASE_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"Error Supabase en Admin: {e}")

BG_COLOR = "#0E1117"
DARK_BLUE = "#0D248D"

class ConsolaAdmin:
    def __init__(self):
        self.contenedor = ui.column().classes('w-full min-h-screen p-0 m-0').style(f'background-color: {BG_COLOR}')
        self.admin_autenticado = False

    def render(self):
        self.contenedor.clear()
        
        # Verificamos si ya estamos logueados como admin en la sesión global
        from nicegui import app
        if app.storage.user.get('role') == 'admin':
            self.admin_autenticado = True

        if not self.admin_autenticado:
            self.render_login()
        else:
            self.render_dashboard()

    async def procesar_carga_masiva(self, e):
        ui.notify('Procesando archivo...', type='info')
        try:
            # Leer archivo según extensión
            if e.name.endswith('.csv'):
                df = pd.read_csv(io.BytesIO(e.content.read()), sep=None, engine='python')
            elif e.name.endswith('.xlsx'):
                df = pd.read_excel(io.BytesIO(e.content.read()))
            else:
                ui.notify('Formato no soportado. Usa CSV o XLSX', type='negative')
                return

            # Normalizar columnas a minúsculas para evitar errores
            df.columns = df.columns.str.lower().str.strip()
            
            # Validar columnas mínimas
            columnas_requeridas = ['username', 'password', 'org_id', 'tests']
            for col in columnas_requeridas:
                if col not in df.columns:
                    ui.notify(f'Falta la columna requerida: {col}', type='negative')
                    return

            usuarios_insertados = 0
            for _, row in df.iterrows():
                tests = str(row['tests']).upper()
                sape_active = "SAPE" in tests or "AMBAS" in tests
                sapp_active = "SAPP" in tests or "AMBAS" in tests

                # Construir el nuevo JSONB Estructural y retro-compatible
                profile_data = {
                    "sape_attempts_allowed": 1 if sape_active else 0, # Retro-compatibilidad
                    "sapp_attempts_allowed": 1 if sapp_active else 0, # Retro-compatibilidad
                    "sape": {
                        "attempts": 1 if sape_active else 0,
                        "sectors": [s.strip() for s in str(row.get('sape_sectors', '')).split(',')] if pd.notna(row.get('sape_sectors')) else []
                    },
                    "sapp": {
                        "attempts": 1 if sapp_active else 0,
                        "profile": str(row.get('sapp_profile', '')).strip(),
                        "groups": [g.strip() for g in str(row.get('sapp_groups', '')).split(',')] if pd.notna(row.get('sapp_groups')) else []
                    }
                }

                payload = {
                    "username": str(row['username']).strip(),
                    "password": str(row['password']).strip(),
                    "org_id": str(row['org_id']).strip(),
                    "role": "USER",
                    "is_deleted": False,
                    "profile_data": profile_data
                }
                
                # Insertar en base de datos (se usa upsert por si el usuario ya existe)
                supabase.table("users").upsert(payload).execute()
                usuarios_insertados += 1

            ui.notify(f'Éxito: {usuarios_insertados} usuarios importados y configurados.', type='positive')

        except Exception as ex:
            print(f"Error procesando carga masiva: {ex}")
            ui.notify(f'Error en el formato del archivo: {str(ex)}', type='negative')

    def render_login(self):
        """Pantalla de login conectada a Supabase"""
        with self.contenedor.classes('justify-center items-center'):
            with ui.card().classes('p-10 rounded-3xl bg-white shadow-2xl items-center').style('width: 25vw; min-width: 300px;'):
                ui.image('logo_original.png').classes('w-48 mb-2')
                ui.label('CONSOLA MAESTRA').classes('text-xl font-bold text-gray-800 mb-6 tracking-widest')
                
                u_in = ui.input('Usuario Admin').classes('w-full mb-4').props('outlined')
                p_in = ui.input('Contraseña', password=True).classes('w-full mb-6').props('outlined')
                
                btn = ui.button('ACCEDER AL PANEL', on_click=lambda: self.verificar_admin(u_in.value, p_in.value)) \
                    .classes('w-full py-4 font-bold text-white rounded-xl transition-all').style(f'background-color: {DARK_BLUE}')
                btn.on('mouseenter', lambda: btn.style('transform: scale(1.05)'))
                btn.on('mouseleave', lambda: btn.style('transform: scale(1.0)'))

    def verificar_admin(self, user, pwd):
        """Busca las credenciales en la tabla 'admins' de Supabase"""
        if not supabase:
            ui.notify('Error de conexión a la base de datos.', type='negative')
            return
            
        try:
            # Consultamos a Supabase si existe este administrador
            res = supabase.table('admins').select('*').eq('username', user).eq('password', pwd).execute()
            
            if res.data and len(res.data) > 0:
                self.admin_autenticado = True
                self.contenedor.classes(remove='justify-center items-center', add='p-8 items-start')
                self.render()
            else:
                ui.notify('Acceso denegado. Credenciales incorrectas.', type='negative', position='top')
        except Exception as e:
            ui.notify(f'Error al verificar credenciales: {e}', type='negative')

    def cerrar_sesion(self):
        self.admin_autenticado = False
        self.contenedor.classes(remove='p-8 items-start', add='justify-center items-center')
        self.render()

    def obtener_organizaciones(self):
        if not supabase: return []
        try:
            res = supabase.table('organizations').select('*').execute()
            return res.data
        except Exception as e:
            ui.notify(f'Error al cargar BD: {e}', type='negative')
            return []

    def crear_organizacion(self, nombre, pwd, sape_lic, sapp_lic, is_demo):
        if not supabase: return
        nuevo_id = nombre.lower().replace(" ", "_")
        
        datos = {
            "id": nuevo_id,
            "name": nombre,
            "password": pwd,
            "sape_licenses": int(sape_lic or 0),
            "sapp_licenses": int(sapp_lic or 0),
            "is_demo": is_demo,
            "is_active": True,
            "can_use_sape": int(sape_lic or 0) > 0,
            "can_use_sapp": int(sapp_lic or 0) > 0
        }
        
        try:
            supabase.table('organizations').insert([datos]).execute()
            ui.notify(f'Organización "{nombre}" creada con éxito', type='positive')
            self.render()
        except Exception as e:
            ui.notify(f'Error al registrar empresa: {e}', type='negative')

    def render_dashboard(self):
        """El Panel de Control de Administración"""
        with self.contenedor:
            # CABECERA
            with ui.row().classes('w-full justify-between items-center mb-8 px-4'):
                with ui.row().classes('items-center gap-4'):
                    ui.image('logo_blanco.png').classes('w-32')
                    ui.label('ADMINISTRACIÓN B2B').classes('text-2xl text-white font-bold tracking-wide')
                ui.button('CERRAR SESIÓN', on_click=self.cerrar_sesion).classes('bg-red-600 text-white font-bold rounded-lg px-6 py-2')

            # FILA 1: NUEVA ORGANIZACIÓN + CARTERA DE CLIENTES
            with ui.row().classes('w-full max-w-7xl mx-auto gap-8 items-stretch mb-8'):
                # PANEL IZQUIERDO: NUEVA ORGANIZACIÓN
                with ui.column().classes('w-1/3 min-w-[350px] bg-[#161B22] p-6 rounded-2xl border border-gray-700 shadow-lg'):
                    ui.label('Alta de Nueva Organización').classes('text-xl text-white font-bold mb-4')
                    
                    nombre_in = ui.input('Nombre de la Empresa').classes('w-full mb-2').props('dark outlined')
                    pwd_in = ui.input('Contraseña para el cliente').classes('w-full mb-4').props('dark outlined')
                    
                    with ui.row().classes('w-full justify-between gap-4 mb-4'):
                        sape_in = ui.number('Licencias SAPE', value=0, min=0).classes('w-[45%]').props('dark outlined')
                        sapp_in = ui.number('Licencias SAPP', value=0, min=0).classes('w-[45%]').props('dark outlined')
                    
                    demo_check = ui.checkbox('Es una cuenta DEMO').classes('text-white mb-6')
                    
                    ui.button('REGISTRAR EMPRESA', on_click=lambda: self.crear_organizacion(
                        nombre_in.value, pwd_in.value, sape_in.value, sapp_in.value, demo_check.value
                    )).classes('w-full py-3 text-white font-bold rounded-lg transition-all').style(f'background-color: {DARK_BLUE}')

                # PANEL DERECHO: BASE DE DATOS
                with ui.column().classes('flex-1 bg-[#161B22] p-6 rounded-2xl border border-gray-700 shadow-lg'):
                    ui.label('Cartera de Clientes Activos').classes('text-xl text-white font-bold mb-4')
                    
                    orgs = self.obtener_organizaciones()
                    if not orgs:
                        ui.label('Aún no hay organizaciones registradas en Supabase.').classes('text-gray-400 italic')
                    else:
                        columnas = [
                            {'name': 'name', 'label': 'Empresa', 'field': 'name', 'align': 'left'},
                            {'name': 'sape', 'label': 'Lic. SAPE', 'field': 'sape_licenses'},
                            {'name': 'sapp', 'label': 'Lic. SAPP', 'field': 'sapp_licenses'},
                            {'name': 'demo', 'label': 'Demo', 'field': 'is_demo'},
                            {'name': 'estado', 'label': 'Activa', 'field': 'is_active'}
                        ]
                        ui.table(columns=columnas, rows=orgs, row_key='name').classes('w-full bg-[#0E1117] text-white rounded-lg border border-gray-700')

            # FILA 2: CARGA MASIVA DE USUARIOS (Independiente)
            with ui.row().classes('w-full max-w-7xl mx-auto gap-8 items-start'):
                with ui.column().classes('w-full bg-[#161B22] p-6 rounded-2xl border border-gray-700 shadow-lg'):
                    ui.label('Carga Masiva de Usuarios (CSV / XLSX)').classes('text-xl text-white font-bold mb-2')
                    ui.label('Formato requerido: username, password, org_id, tests, sape_sectors, sapp_profile, sapp_groups').classes('text-gray-400 text-sm mb-4')
                    
                    ui.upload(on_upload=self.procesar_carga_masiva, label="Seleccionar y subir archivo...", auto_upload=True).classes('w-full max-w-lg')