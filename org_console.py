import os
import pandas as pd
import io
from nicegui import ui, app
from supabase import create_client, Client
from dotenv import load_dotenv

# ==========================================
# CONFIGURACIÓN E INICIALIZACIÓN
# ==========================================
load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = None
try:
    if SUPABASE_URL and SUPABASE_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"⚠️ Error Supabase en OrgConsole: {e}")

BG_COLOR = "#0E1117"
DARK_BLUE = "#0D248D"

class ConsolaOrganizacion:
    def __init__(self):
        self.contenedor = ui.column().classes('w-full min-h-screen p-0 m-0').style(f'background-color: {BG_COLOR}')
        self.org_id = app.storage.user.get('org_id')
        self.username = app.storage.user.get('username')
        self.org_data = {}
        self.privilegios = {}
        self.users_data = []
        self.evals_data = []
        self.logs_data = []

    def cargar_datos(self):
        """Carga solo los datos pertenecientes al org_id de este cliente"""
        if not supabase or not self.org_id: return
        
        try:
            # 1. Datos y Privilegios de la Organización
            res_org = supabase.table('organizations').select('*').eq('id', self.org_id).execute()
            if res_org.data: 
                self.org_data = res_org.data[0]
                self.privilegios = self.org_data.get('privileges', {}) or {}

            # 2. Usuarios
            res_usr = supabase.table('users').select('*').eq('org_id', self.org_id).execute()
            if res_usr.data: self.users_data = res_usr.data

            # 3. Evaluaciones completadas
            res_eval = supabase.table('evaluations').select('*').eq('org_id', self.org_id).execute()
            if res_eval.data: self.evals_data = res_eval.data
            
            # 4. Action Logs (Historial de colores)
            res_logs = supabase.table('action_logs').select('*').eq('org_id', self.org_id).order('created_at', desc=True).limit(50).execute()
            if res_logs.data: self.logs_data = res_logs.data

        except Exception as e:
            ui.notify(f"Error cargando datos de la organización: {e}", type='negative')

    def registrar_log(self, action_type, target_user, color):
        if not supabase: return
        try:
            supabase.table('action_logs').insert({
                'org_id': self.org_id,
                'action_type': action_type,
                'target_user': target_user,
                'performed_by': self.username,
                'status_color': color
            }).execute()
        except:
            pass

    def solicitar_licencias(self):
        # Aquí en el futuro podemos enviar un email al Admin o registrar la petición en una tabla de facturación
        ui.notify("Solicitud enviada a Administración. Nos pondremos en contacto para la facturación posterior.", type='positive', icon='check_circle', position='top')

    def cerrar_sesion(self):
        app.storage.user.clear()
        ui.navigate.to('/')

    def render(self):
        self.contenedor.clear()
        if app.storage.user.get('role') != 'ORG_ADMIN':
            ui.navigate.to('/')
            return
        
        self.cargar_datos()
        
        with self.contenedor.classes('p-8'):
            # CABECERA
            with ui.row().classes('w-full justify-between items-center mb-6 bg-[#161B22] p-6 rounded-2xl border border-gray-800 shadow-xl'):
                with ui.row().classes('items-center gap-6'):
                    ui.image('logo_blanco.png').classes('w-40')
                    nombre_empresa = self.org_data.get('name', self.org_id).upper()
                    ui.label(f'PORTAL B2B | {nombre_empresa}').classes('text-2xl text-white font-black tracking-tight')
                with ui.row().classes('items-center gap-4'):
                    ui.button('Solicitar + Licencias', on_click=self.solicitar_licencias, icon='add_shopping_cart').classes('bg-green-600 text-white font-bold rounded-lg')
                    ui.button('CERRAR SESIÓN', on_click=self.cerrar_sesion, color='red').classes('font-bold rounded-lg')

            # KPIs RÁPIDOS
            with ui.row().classes('w-full gap-4 mb-8'):
                ui.label(f"🔑 SAPE: {self.org_data.get('sape_licenses', 0)}").classes('bg-[#0E1117] text-[#83ABF1] px-6 py-3 rounded-xl border border-gray-800 font-bold')
                ui.label(f"🔑 SAPP: {self.org_data.get('sapp_licenses', 0)}").classes('bg-[#0E1117] text-[#83ABF1] px-6 py-3 rounded-xl border border-gray-800 font-bold')
                ui.label(f"👥 Usuarios: {len(self.users_data)}").classes('bg-[#0E1117] text-white px-6 py-3 rounded-xl border border-gray-800 font-bold')

            # PESTAÑAS
            with ui.tabs().classes('w-full bg-[#161B22] text-[#83ABF1] rounded-t-2xl font-bold') as tabs:
                tab_usuarios = ui.tab('USUARIOS', icon='manage_accounts')
                tab_estadisticas = ui.tab('ESTADÍSTICAS E HISTORIAL', icon='query_stats')

            with ui.tab_panels(tabs, value=tab_usuarios).classes('w-full bg-[#161B22] border border-gray-800 rounded-b-2xl p-8 shadow-2xl'):
                
                # --- PESTAÑA USUARIOS ---
                with ui.tab_panel(tab_usuarios):
                    with ui.row().classes('w-full gap-8 items-start'):
                        
                        # BLOQUE IZQUIERDO: CREACIÓN MASIVA / INDIVIDUAL (Renderizado Condicional por Privilegios)
                        with ui.column().classes('w-1/3 min-w-[350px]'):
                            if self.privilegios.get('can_create_users', False):
                                # Individual
                                with ui.column().classes('w-full bg-[#0E1117] p-6 rounded-2xl border border-gray-800 mb-6'):
                                    ui.label('Registrar Usuario Manual').classes('text-lg text-[#83ABF1] font-bold mb-4')
                                    u_nom = ui.input('Nombre de Usuario').classes('w-full mb-2').props('dark outlined')
                                    u_pwd = ui.input('Contraseña', password=True, password_toggle_button=True).classes('w-full mb-4').props('dark outlined')
                                    ui.button('Crear Usuario', on_click=lambda: ui.notify("Función de creación individual en desarrollo", type='info')).classes('w-full bg-[#83ABF1] text-[#0E1117] font-bold')
                                
                                # Masivo
                                with ui.column().classes('w-full bg-[#0E1117] p-6 rounded-2xl border border-gray-800'):
                                    ui.label('Carga Masiva (CSV / XLSX)').classes('text-lg text-[#83ABF1] font-bold mb-2')
                                    ui.button('Descargar Plantilla Corporativa', icon='file_download').classes('w-full mb-4 bg-gray-700 text-white')
                                    ui.upload(on_upload=self.procesar_carga_masiva_org, label="Sube tu archivo", auto_upload=True).classes('w-full')
                            else:
                                with ui.column().classes('w-full bg-[#0E1117] p-6 rounded-2xl border border-red-900/50 items-center text-center'):
                                    ui.icon('lock', size='3rem', color='red').classes('mb-4 opacity-50')
                                    ui.label('Creación de usuarios deshabilitada.').classes('text-red-400 font-bold mb-2')
                                    ui.label('Contacta con administración para habilitar esta función o enviar listados.').classes('text-sm text-gray-500')

                        # BLOQUE DERECHO: LISTADO DE USUARIOS DE LA EMPRESA
                        with ui.column().classes('flex-1 bg-[#0E1117] p-6 rounded-2xl border border-gray-800'):
                            ui.label('Directorio de Usuarios').classes('text-xl text-[#83ABF1] font-bold mb-4')
                            if not self.users_data:
                                ui.label('No hay usuarios en la organización.').classes('text-gray-500 italic')
                            else:
                                filas = []
                                for u in self.users_data:
                                    if u.get('role') == 'ORG_ADMIN': continue
                                    filas.append({
                                        'user': u.get('username'),
                                        'role': u.get('role'),
                                        'status': 'Activo' if not u.get('is_deleted') else 'Eliminado',
                                        'date': u.get('created_at', '')[:10]
                                    })
                                cols = [
                                    {'name': 'user', 'label': 'Usuario', 'field': 'user', 'align': 'left'},
                                    {'name': 'status', 'label': 'Estado', 'field': 'status', 'align': 'center'},
                                    {'name': 'date', 'label': 'Alta', 'field': 'date', 'align': 'right'}
                                ]
                                ui.table(columns=cols, rows=filas, row_key='user').classes('w-full bg-[#161B22] text-white')

                # --- PESTAÑA ESTADÍSTICAS E HISTORIAL ---
                with ui.tab_panel(tab_estadisticas):
                    with ui.row().classes('w-full gap-8'):
                        
                        # HISTORIAL (Action Logs de Colores)
                        with ui.column().classes('w-1/2 bg-[#0E1117] p-6 rounded-2xl border border-gray-800'):
                            ui.label('Historial de Registros').classes('text-xl text-[#83ABF1] font-bold mb-6')
                            
                            # Leyenda de Colores
                            with ui.row().classes('gap-4 mb-6 text-xs text-gray-400 font-bold'):
                                ui.label('🟢 Activas').classes('bg-green-900/30 px-2 py-1 rounded')
                                ui.label('🟢🔵 Nuevas').classes('bg-blue-900/30 px-2 py-1 rounded border-l-2 border-green-500')
                                ui.label('🟢🟡 Editadas').classes('bg-yellow-900/30 px-2 py-1 rounded border-l-2 border-green-500')
                                ui.label('🟡🔴 Error').classes('bg-red-900/30 px-2 py-1 rounded border-l-2 border-yellow-500')
                                ui.label('🔴 Eliminadas').classes('bg-red-900/30 px-2 py-1 rounded')

                            if not self.logs_data:
                                ui.label('No hay registros recientes.').classes('text-gray-500')
                            else:
                                for log in self.logs_data:
                                    color = log.get('status_color', 'green')
                                    # Mapeo de colores a tailwind
                                    bg_col = "bg-green-500" if color == "green" else "bg-blue-500" if color == "green-blue" else "bg-yellow-500" if color == "green-yellow" else "bg-red-500"
                                    
                                    with ui.row().classes('w-full items-center gap-4 mb-2 p-2 border-b border-gray-800/50 hover:bg-[#161B22]'):
                                        ui.element('div').classes(f'w-3 h-3 rounded-full {bg_col}')
                                        ui.label(log.get('created_at', '')[:16].replace('T', ' ')).classes('text-gray-500 text-sm')
                                        ui.label(log.get('action_type')).classes('text-white font-bold text-sm w-24')
                                        ui.label(log.get('target_user')).classes('text-[#83ABF1] text-sm')

                        # ESTADÍSTICAS BÁSICAS (Visibilidad por privilegios)
                        with ui.column().classes('w-1/2'):
                            if self.privilegios.get('can_view_org_stats', False):
                                ui.label('Estadísticas Globales').classes('text-xl text-[#83ABF1] font-bold mb-4')
                                ui.label('Panel de Business Intelligence en construcción. Mostrará gráficos de pruebas, sectores y usuarios.').classes('text-gray-500 italic p-6 border border-gray-800 rounded-xl')
                            else:
                                ui.label('Estadísticas Deshabilitadas').classes('text-xl text-gray-600 font-bold mb-4')

    async def procesar_carga_masiva_org(self, e):
        # Esta versión fuerza el org_id al del cliente logueado, por seguridad
        ui.notify('Procesando archivo B2B...', type='info')
        self.registrar_log('MASIVO', 'Archivo subido', 'green-blue')
        # La lógica de pandas irá aquí, pero forzando: row['org_id'] = self.org_id