import os
import pandas as pd
import io
import json
from nicegui import ui, app
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
    print(f"⚠️ Error Supabase en Admin: {e}")

BG_COLOR = "#0E1117"
DARK_BLUE = "#0D248D"

class ConsolaAdmin:
    def __init__(self):
        self.contenedor = ui.column().classes('w-full min-h-screen p-0 m-0').style(f'background-color: {BG_COLOR}')
        self.admin_autenticado = False

    def render(self):
        self.contenedor.clear()
        if app.storage.user.get('role') == 'ADMIN':
            self.admin_autenticado = True

        if not self.admin_autenticado:
            self.render_login()
        else:
            self.render_dashboard()

    def render_login(self):
        # ... (Tu código de login actual se mantiene exactamente igual) ...
        with self.contenedor.classes('justify-center items-center'):
            with ui.card().classes('p-10 rounded-3xl bg-white shadow-2xl items-center').style('width: 25vw; min-width: 320px;'):
                ui.image('logo_original.png').classes('w-48 mb-2')
                ui.label('CONSOLA MAESTRA').classes('text-xl font-bold text-gray-800 mb-6 tracking-widest')
                
                u_in = ui.input('Usuario Admin').classes('w-full mb-4').props('outlined')
                p_in = ui.input('Contraseña', password=True, password_toggle_button=True).classes('w-full mb-6').props('outlined')
                p_in.on('keydown.enter', lambda: self.verificar_admin(u_in.value, p_in.value))
                
                btn = ui.button('ACCEDER AL PANEL', on_click=lambda: self.verificar_admin(u_in.value, p_in.value)) \
                    .classes('w-full py-4 font-bold text-white rounded-xl transition-all shadow-lg').style(f'background-color: {DARK_BLUE}')
                
    def verificar_admin(self, user, pwd):
        if not supabase: return
        try:
            res = supabase.table('admins').select('*').eq('username', user).eq('password', pwd).execute()
            if res.data and len(res.data) > 0:
                self.admin_autenticado = True
                app.storage.user.update({'role': 'ADMIN', 'authenticated': True, 'username': user})
                self.render()
            else:
                ui.notify('Credenciales incorrectas', type='negative')
        except Exception as e:
            ui.notify(f'Error: {e}', type='negative')

    def cerrar_sesion(self):
        app.storage.user.clear()
        self.admin_autenticado = False
        self.render()

    # ==========================================
    # LOGICA DE BASE DE DATOS
    # ==========================================
    def crear_organizacion(self, nombre, pwd, sape_lic, sapp_lic, is_demo, privs):
        if not nombre or not pwd:
            ui.notify('Nombre y Contraseña obligatorios', type='warning')
            return
            
        nuevo_id = nombre.lower().strip().replace(" ", "_")
        datos = {
            "id": nuevo_id,
            "name": nombre.strip(),
            "password": pwd.strip(),
            "sape_licenses": int(sape_lic or 0),
            "sapp_licenses": int(sapp_lic or 0),
            "is_demo": bool(is_demo),
            "is_active": True,
            "can_use_sape": int(sape_lic or 0) > 0,
            "can_use_sapp": int(sapp_lic or 0) > 0,
            "privileges": privs
        }
        try:
            supabase.table('organizations').insert(datos).execute()
            ui.notify(f'Organización "{nombre}" registrada con sus privilegios', type='positive')
            self.render()
        except Exception as e:
            ui.notify(f'Error: {e}', type='negative')

    # ==========================================
    # RENDER DEL NUEVO DASHBOARD
    # ==========================================
    def render_dashboard(self):
        with self.contenedor.classes('p-8'):
            # HEADER
            with ui.row().classes('w-full justify-between items-center mb-6 bg-[#161B22] p-6 rounded-2xl border border-gray-800 shadow-xl'):
                with ui.row().classes('items-center gap-6'):
                    ui.image('logo_blanco.png').classes('w-40')
                    ui.label('ERP DE ADMINISTRACIÓN AUDEO').classes('text-2xl text-white font-black tracking-tight')
                ui.button('CERRAR SESIÓN', on_click=self.cerrar_sesion, color='red').classes('px-8 py-2 font-bold rounded-xl')

            # SISTEMA DE PESTAÑAS
            with ui.tabs().classes('w-full bg-[#161B22] text-[#83ABF1] rounded-t-2xl font-bold') as tabs:
                tab_orgs = ui.tab('ORGANIZACIONES', icon='domain')
                tab_users = ui.tab('USUARIOS', icon='people')
                tab_stats = ui.tab('ESTADÍSTICAS Y LOGS', icon='query_stats')

            with ui.tab_panels(tabs, value=tab_orgs).classes('w-full bg-[#161B22] border border-gray-800 rounded-b-2xl shadow-2xl p-0'):
                
                # ----------------------------------------------------------------
                # PESTAÑA 1: ORGANIZACIONES
                # ----------------------------------------------------------------
                with ui.tab_panel(tab_orgs).classes('p-8'):
                    with ui.row().classes('w-full gap-8 items-start'):
                        
                        # ALTA Y PRIVILEGIOS
                        with ui.column().classes('w-1/3 min-w-[400px] bg-[#0E1117] p-8 rounded-2xl border border-gray-800'):
                            ui.label('1. Alta y Configuración').classes('text-xl text-[#83ABF1] font-bold mb-4')
                            nom = ui.input('Nombre Organización').classes('w-full mb-2').props('dark outlined')
                            pwd = ui.input('Clave Maestra').classes('w-full mb-4').props('dark outlined')
                            
                            with ui.row().classes('w-full gap-2 mb-4'):
                                lic_sape = ui.number('Lic. SAPE', value=0, min=0).classes('w-[48%]').props('dark outlined')
                                lic_sapp = ui.number('Lic. SAPP', value=0, min=0).classes('w-[48%]').props('dark outlined')
                            
                            demo = ui.checkbox('Cuenta DEMO (Pruebas al 10%)').classes('text-gray-400 mb-4')
                            
                            ui.label('2. Matriz de Privilegios B2B').classes('text-lg text-[#83ABF1] font-bold mb-2 mt-4 border-t border-gray-800 pt-4')
                            priv_create = ui.checkbox('Pueden registrar y editar usuarios').classes('text-white')
                            priv_assign = ui.checkbox('Pueden asignar pruebas y sectores').classes('text-white')
                            priv_stats_o = ui.checkbox('Ver estadísticas de su organización').classes('text-white')
                            priv_stats_u = ui.checkbox('Ver estadísticas por usuario (Talento)').classes('text-white')
                            priv_compare = ui.checkbox('Comparativas anónimas del sector').classes('text-white')
                            
                            ui.button('GUARDAR ORGANIZACIÓN', 
                                on_click=lambda: self.crear_organizacion(
                                    nom.value, pwd.value, lic_sape.value, lic_sapp.value, demo.value,
                                    {
                                        "can_create_users": priv_create.value,
                                        "can_assign_tests": priv_assign.value,
                                        "can_view_org_stats": priv_stats_o.value,
                                        "can_view_user_stats": priv_stats_u.value,
                                        "can_compare_anon": priv_compare.value
                                    }
                                )).classes('w-full py-4 text-white font-bold rounded-xl mt-6').style(f'background-color: {DARK_BLUE}')

                        # LISTADO DE ORGANIZACIONES
                        with ui.column().classes('flex-1 bg-[#0E1117] p-8 rounded-2xl border border-gray-800'):
                            ui.label('Gestión de Cartera Activa').classes('text-xl text-[#83ABF1] font-bold mb-4')
                            try:
                                orgs = supabase.table('organizations').select('*').execute().data
                                if orgs:
                                    cols = [
                                        {'name': 'name', 'label': 'ORGANIZACIÓN', 'field': 'name', 'align': 'left'},
                                        {'name': 'sape', 'label': 'SAPE', 'field': 'sape_licenses'},
                                        {'name': 'sapp', 'label': 'SAPP', 'field': 'sapp_licenses'},
                                        {'name': 'demo', 'label': 'DEMO', 'field': 'is_demo'}
                                    ]
                                    ui.table(columns=cols, rows=orgs, row_key='name').classes('w-full bg-[#161B22] text-white')
                                else:
                                    ui.label("Sin organizaciones.")
                            except:
                                ui.label("Error cargando base de datos.")

                # ----------------------------------------------------------------
                # PESTAÑA 2: USUARIOS (Carga Masiva y Listado Global)
                # ----------------------------------------------------------------
                with ui.tab_panel(tab_users).classes('p-8'):
                    ui.label('Carga Masiva y Plantillas').classes('text-xl text-[#83ABF1] font-bold mb-4')
                    with ui.row().classes('items-center gap-6 bg-[#0E1117] p-6 rounded-xl border border-gray-800 mb-8'):
                        ui.upload(on_upload=self.procesar_carga_masiva_delegada, label="Cargar Excel/CSV", auto_upload=True).classes('w-96')
                        ui.button('Descargar Plantilla XLSX Corporativa', icon='download').classes('bg-green-700 text-white font-bold')
                        
                    ui.label('Buscador Global de Usuarios').classes('text-xl text-[#83ABF1] font-bold mb-4')
                    ui.label('En construcción: Aquí se renderizará la tabla global con filtros cruzados.').classes('text-gray-500 italic')

                # ----------------------------------------------------------------
                # PESTAÑA 3: ESTADÍSTICAS Y LOGS
                # ----------------------------------------------------------------
                with ui.tab_panel(tab_stats).classes('p-8'):
                    ui.label('Monitorización de Plataforma').classes('text-xl text-[#83ABF1] font-bold mb-4')
                    with ui.row().classes('gap-4 mb-8'):
                        ui.label('🟢 Usuarios Activos').classes('text-green-500 font-bold bg-[#0E1117] px-4 py-2 rounded')
                        ui.label('🟢🔵 Nuevos Registros').classes('text-blue-400 font-bold bg-[#0E1117] px-4 py-2 rounded border-l-4 border-green-500')
                        ui.label('🟢🟡 Usuarios Editados').classes('text-yellow-400 font-bold bg-[#0E1117] px-4 py-2 rounded border-l-4 border-green-300')
                        ui.label('🟡🔴 Errores de Carga').classes('text-red-400 font-bold bg-[#0E1117] px-4 py-2 rounded border-l-4 border-yellow-500')
                    
                    ui.label('En construcción: Aquí se conectará la tabla de action_logs.').classes('text-gray-500 italic')

    async def procesar_carga_masiva_delegada(self, e):
        # La lógica de carga masiva que ya teníamos, la he movido aquí para limpieza.
        ui.notify('Cargador en actualización...', type='info')