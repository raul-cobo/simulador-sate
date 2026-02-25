import os
import pandas as pd
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
CARD_COLOR = "#161B22"
ACCENT_COLOR = "#83ABF1"

class ConsolaOrganizacion:
    def __init__(self):
        self.contenedor = ui.column().classes('w-full min-h-screen p-0 m-0').style(f'background-color: {BG_COLOR}')
        self.org_id = app.storage.user.get('org_id')
        self.username = app.storage.user.get('username')
        self.org_data = {}
        self.users_data = []
        self.evals_data = []

    def cargar_datos(self):
        """Carga solo los datos pertenecientes al org_id de este cliente (Seguridad RLS lógica)"""
        if not supabase or not self.org_id: return
        
        try:
            # 1. Licencias y nombre de la Organización
            res_org = supabase.table('organizations').select('*').eq('id', self.org_id).execute()
            if res_org.data: self.org_data = res_org.data[0]

            # 2. Usuarios de esta Organización
            res_usr = supabase.table('users').select('username, role, profile_data, created_at, status').eq('org_id', self.org_id).execute()
            if res_usr.data: self.users_data = res_usr.data

            # 3. Evaluaciones completadas por esta Organización
            res_eval = supabase.table('evaluations').select('*').eq('org_id', self.org_id).execute()
            if res_eval.data: self.evals_data = res_eval.data
        except Exception as e:
            ui.notify(f"Error cargando datos de la organización: {e}", type='negative')

    def cerrar_sesion(self):
        app.storage.user.clear()
        ui.navigate.to('/')

    def render(self):
        self.contenedor.clear()
        
        # Verificación estricta de Rol
        if app.storage.user.get('role') != 'ORG_ADMIN':
            with self.contenedor.classes('items-center justify-center'):
                ui.label("Acceso Denegado: Privilegios insuficientes").classes('text-red-500 text-2xl font-bold')
            return
        
        self.cargar_datos()
        
        with self.contenedor.classes('p-8'):
            # ==========================================
            # 1. CABECERA
            # ==========================================
            with ui.row().classes('w-full justify-between items-center mb-8 bg-[#161B22] p-6 rounded-2xl border border-gray-800 shadow-xl'):
                with ui.row().classes('items-center gap-6'):
                    ui.image('logo_blanco.png').classes('w-40')
                    nombre_empresa = self.org_data.get('name', self.org_id).upper()
                    ui.label(f'PORTAL CORPORATIVO | {nombre_empresa}').classes('text-2xl text-white font-black tracking-tight')
                with ui.row().classes('items-center gap-6'):
                    ui.label(f"Responsable: {self.username}").classes('text-[#83ABF1] font-medium')
                    ui.button('CERRAR SESIÓN', on_click=self.cerrar_sesion, color='red').classes('px-6 py-2 font-bold rounded-xl')

            # ==========================================
            # 2. KPIs (Métricas Rápidas)
            # ==========================================
            lic_sape = self.org_data.get('sape_licenses', 0)
            total_users = len([u for u in self.users_data if u.get('role') != 'ORG_ADMIN'])
            total_evals = len(self.evals_data)

            with ui.row().classes('w-full gap-6 mb-8'):
                self.crear_kpi_card('Licencias SAPE', str(lic_sape), 'vpn_key', '#83ABF1')
                self.crear_kpi_card('Usuarios Asignados', str(total_users), 'group', '#4CAF50')
                self.crear_kpi_card('Pruebas Completadas', str(total_evals), 'task_alt', '#FFC107')

            # ==========================================
            # 3. PANELES DE GESTIÓN (TABS)
            # ==========================================
            with ui.tabs().classes('w-full bg-[#161B22] text-[#83ABF1] rounded-t-2xl font-bold') as tabs:
                tab_talento = ui.tab('EXPLORADOR DE TALENTO', icon='troubleshoot')
                tab_equipo = ui.tab('GESTIÓN DE EQUIPO', icon='manage_accounts')

            with ui.tab_panels(tabs, value=tab_talento).classes('w-full bg-[#161B22] border border-gray-800 rounded-b-2xl p-8 shadow-2xl'):
                
                # --- TAB 1: RESULTADOS ---
                with ui.tab_panel(tab_talento):
                    self.render_explorador_talento()
                
                # --- TAB 2: USUARIOS ---
                with ui.tab_panel(tab_equipo):
                    self.render_gestion_equipo()

    def crear_kpi_card(self, titulo, valor, icono, color):
        with ui.row().classes('flex-1 bg-[#161B22] p-6 rounded-2xl border border-gray-800 shadow-lg items-center gap-6'):
            ui.icon(icono, size='3.5rem').style(f'color: {color}')
            with ui.column().classes('gap-0'):
                ui.label(titulo).classes('text-gray-400 text-sm font-bold uppercase tracking-wider')
                ui.label(valor).classes('text-4xl text-white font-black')

    def render_explorador_talento(self):
        ui.label('Resultados de Evaluaciones (SAPE)').classes('text-xl text-white font-bold mb-6')
        
        if not self.evals_data:
            ui.label("Aún no hay evaluaciones completadas en tu organización.").classes('text-gray-500 italic py-4')
            return
        
        filas = []
        for ev in self.evals_data:
            res = ev.get('results', {})
            potencial = res.get('potencial', 0)
            
            # Clasificación visual del potencial
            if potencial >= 75: estado = "🟢 Alto"
            elif potencial >= 50: estado = "🟡 Medio"
            else: estado = "🔴 Riesgo"
            
            filas.append({
                'usuario': ev.get('user_id', 'Desconocido'),
                'sector': ev.get('sector', 'N/A'),
                'potencial': f"{potencial}%",
                'ire': res.get('ire_global', 0),
                'estado': estado,
                'fecha': ev.get('created_at', '')[:10]
            })
        
        columnas = [
            {'name': 'usuario', 'label': 'USUARIO EVALUADO', 'field': 'usuario', 'align': 'left', 'sortable': True},
            {'name': 'sector', 'label': 'SECTOR', 'field': 'sector', 'align': 'center'},
            {'name': 'potencial', 'label': 'POTENCIAL', 'field': 'potencial', 'align': 'center', 'sortable': True},
            {'name': 'ire', 'label': 'I.R.E.', 'field': 'ire', 'align': 'center', 'sortable': True},
            {'name': 'estado', 'label': 'DIAGNÓSTICO', 'field': 'estado', 'align': 'center', 'sortable': True},
            {'name': 'fecha', 'label': 'FECHA', 'field': 'fecha', 'align': 'right', 'sortable': True},
        ]
        
        ui.table(columns=columnas, rows=filas, row_key='usuario').classes('w-full bg-[#0E1117] text-white rounded-xl border border-gray-800')

    def render_gestion_equipo(self):
        ui.label('Directorio de Usuarios').classes('text-xl text-white font-bold mb-6')
        
        if not self.users_data:
            ui.label("No hay usuarios registrados en esta organización.").classes('text-gray-500')
            return
        
        filas = []
        for u in self.users_data:
            if u.get('role') == 'ORG_ADMIN': continue # Ocultar al propio admin de la lista
            
            p_data = u.get('profile_data', {})
            # Extraer intentos de forma retro-compatible
            sape_att = p_data.get('sape', {}).get('attempts', 0) if isinstance(p_data.get('sape'), dict) else p_data.get('sape_attempts_allowed', 0)
            
            estado_test = "✅ Completado" if sape_att == 0 else "⏳ Pendiente"
            
            filas.append({
                'username': u.get('username'),
                'intentos': sape_att,
                'estado': estado_test,
                'alta': u.get('created_at', '')[:10]
            })

        columnas = [
            {'name': 'username', 'label': 'IDENTIFICADOR', 'field': 'username', 'align': 'left', 'sortable': True},
            {'name': 'estado', 'label': 'ESTADO SAPE', 'field': 'estado', 'align': 'center', 'sortable': True},
            {'name': 'intentos', 'label': 'INTENTOS RESTANTES', 'field': 'intentos', 'align': 'center'},
            {'name': 'alta', 'label': 'FECHA REGISTRO', 'field': 'alta', 'align': 'right', 'sortable': True},
        ]
        
        ui.table(columns=columnas, rows=filas, row_key='username').classes('w-full bg-[#0E1117] text-white rounded-xl border border-gray-800')