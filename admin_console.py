import os
import pandas as pd
import io
import json
from nicegui import ui, app
from supabase import create_client, Client
from dotenv import load_dotenv

# ==========================================
# 1. CONFIGURACIÓN E INICIALIZACIÓN
# ==========================================
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
        
        # Verificamos sesión persistente (Rol ADMIN en mayúsculas como en la DB)
        if app.storage.user.get('role') == 'ADMIN':
            self.admin_autenticado = True

        if not self.admin_autenticado:
            self.render_login()
        else:
            self.render_dashboard()

    # ==========================================
    # 2. LÓGICA DE AUTENTICACIÓN
    # ==========================================
    def render_login(self):
        """Pantalla de login centrada"""
        with self.contenedor.classes('justify-center items-center'):
            with ui.card().classes('p-10 rounded-3xl bg-white shadow-2xl items-center').style('width: 25vw; min-width: 320px;'):
                ui.image('logo_original.png').classes('w-48 mb-2')
                ui.label('CONSOLA MAESTRA').classes('text-xl font-bold text-gray-800 mb-6 tracking-widest')
                
                u_in = ui.input('Usuario Admin').classes('w-full mb-4').props('outlined')
                p_in = ui.input('Contraseña', password=True).classes('w-full mb-6').props('outlined')
                p_in.on('keydown.enter', lambda: self.verificar_admin(u_in.value, p_in.value))
                
                btn = ui.button('ACCEDER AL PANEL', on_click=lambda: self.verificar_admin(u_in.value, p_in.value)) \
                    .classes('w-full py-4 font-bold text-white rounded-xl transition-all shadow-lg').style(f'background-color: {DARK_BLUE}')
                btn.on('mouseenter', lambda: btn.style('transform: scale(1.05)'))
                btn.on('mouseleave', lambda: btn.style('transform: scale(1.0)'))

    def verificar_admin(self, user, pwd):
        """Validación contra tabla 'admins' con diagnóstico"""
        if not supabase:
            ui.notify('Error: No hay conexión a Supabase', type='negative')
            return
            
        try:
            res = supabase.table('admins').select('*').eq('username', user).eq('password', pwd).execute()
            
            if res.data and len(res.data) > 0:
                self.admin_autenticado = True
                app.storage.user.update({'role': 'ADMIN', 'authenticated': True, 'username': user})
                ui.notify(f'Bienvenido, Administrador', type='positive')
                self.render()
            else:
                ui.notify('Credenciales incorrectas', type='negative')
        except Exception as e:
            ui.notify(f'Error de verificación: {e}', type='negative')

    def cerrar_sesion(self):
        app.storage.user.clear()
        self.admin_autenticado = False
        self.render()

    # ==========================================
    # 3. GESTIÓN DE ORGANIZACIONES
    # ==========================================
    def obtener_organizaciones(self):
        if not supabase: return []
        try:
            res = supabase.table('organizations').select('*').order('name').execute()
            return res.data
        except Exception as e:
            print(f"Error cargando orgs: {e}")
            return []

    def crear_organizacion(self, nombre, pwd, sape_lic, sapp_lic, is_demo):
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
            "can_use_sapp": int(sapp_lic or 0) > 0
        }
        
        try:
            supabase.table('organizations').insert(datos).execute()
            ui.notify(f'Organización "{nombre}" registrada', type='positive')
            self.render()
        except Exception as e:
            ui.notify(f'Error: {e}', type='negative')

    # ==========================================
    # 4. CARGA MASIVA DE USUARIOS
    # ==========================================
    async def procesar_carga_masiva(self, e):
        ui.notify('Procesando archivo...', type='info')
        try:
            content = io.BytesIO(e.content.read())
            if e.name.endswith('.csv'):
                df = pd.read_csv(content, sep=None, engine='python')
            else:
                df = pd.read_excel(content)

            df.columns = df.columns.str.lower().str.strip()
            
            # Validación de columnas
            req = ['username', 'password', 'org_id', 'tests']
            if not all(col in df.columns for col in req):
                ui.notify('El archivo no tiene las columnas requeridas', type='negative')
                return

            count = 0
            for _, row in df.iterrows():
                tests = str(row['tests']).upper()
                sape_active = any(x in tests for x in ["SAPE", "AMBAS"])
                sapp_active = any(x in tests for x in ["SAPP", "AMBAS"])

                profile_data = {
                    "sape_attempts_allowed": 1 if sape_active else 0,
                    "sapp_attempts_allowed": 1 if sapp_active else 0,
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
                
                supabase.table("users").upsert(payload).execute()
                count += 1

            ui.notify(f'Éxito: {count} usuarios importados.', type='positive')
            self.render()

        except Exception as ex:
            ui.notify(f'Error en importación: {ex}', type='negative')

    # ==========================================
    # 5. RENDER DEL DASHBOARD
    # ==========================================
    def render_dashboard(self):
        """Panel principal con Grid dinámico"""
        with self.contenedor.classes('p-8'):
            # HEADER
            with ui.row().classes('w-full justify-between items-center mb-10 bg-[#161B22] p-6 rounded-2xl border border-gray-800 shadow-xl'):
                with ui.row().classes('items-center gap-6'):
                    ui.image('logo_blanco.png').classes('w-40')
                    ui.label('CENTRAL DE ADMINISTRACIÓN B2B').classes('text-2xl text-white font-black tracking-tight')
                ui.button('CERRAR SESIÓN', on_click=self.cerrar_sesion, color='red').classes('px-8 py-2 font-bold rounded-xl')

            # CONTENIDO: ALTA Y LISTADO
            with ui.row().classes('w-full gap-8 items-stretch mb-8'):
                # PANEL IZQUIERDO: FORMULARIO
                with ui.column().classes('w-1/3 min-w-[380px] bg-[#161B22] p-8 rounded-3xl border border-gray-800 shadow-2xl'):
                    ui.label('Alta de Organización').classes('text-xl text-[#83ABF1] font-bold mb-6 border-b border-gray-800 pb-2 w-full')
                    
                    nom = ui.input('Nombre Comercial').classes('w-full mb-3').props('dark outlined')
                    pwd = ui.input('Clave Maestra Cliente').classes('w-full mb-6').props('dark outlined')
                    
                    with ui.row().classes('w-full justify-between gap-2 mb-6'):
                        lic_sape = ui.number('SAPE Lic.', value=0, min=0).classes('w-[45%]').props('dark outlined')
                        lic_sapp = ui.number('SAPP Lic.', value=0, min=0).classes('w-[45%]').props('dark outlined')
                    
                    demo = ui.checkbox('Cuenta de Demostración / Cortesía').classes('text-gray-400 mb-8')
                    
                    ui.button('REGISTRAR Y ACTIVAR', 
                              on_click=lambda: self.crear_organizacion(nom.value, pwd.value, lic_sape.value, lic_sapp.value, demo.value)) \
                              .classes('w-full py-4 text-white font-bold rounded-2xl shadow-lg hover:scale-105 transition-all').style(f'background-color: {DARK_BLUE}')

                # PANEL DERECHO: LISTADO
                with ui.column().classes('flex-1 bg-[#161B22] p-8 rounded-3xl border border-gray-800 shadow-2xl'):
                    ui.label('Cartera de Clientes en Tiempo Real').classes('text-xl text-[#83ABF1] font-bold mb-6 border-b border-gray-800 pb-2 w-full')
                    
                    orgs = self.obtener_organizaciones()
                    if not orgs:
                        ui.label('No hay organizaciones registradas.').classes('text-gray-500 italic text-center w-full py-10')
                    else:
                        columnas = [
                            {'name': 'name', 'label': 'ORGANIZACIÓN', 'field': 'name', 'align': 'left', 'sortable': True},
                            {'name': 'sape', 'label': 'SAPE', 'field': 'sape_licenses'},
                            {'name': 'sapp', 'label': 'SAPP', 'field': 'sapp_licenses'},
                            {'name': 'demo', 'label': 'DEMO', 'field': 'is_demo'},
                            {'name': 'status', 'label': 'ESTADO', 'field': 'is_active'}
                        ]
                        ui.table(columns=columnas, rows=orgs, row_key='name').classes('w-full bg-[#0E1117] text-white rounded-xl border border-gray-800')

            # SECCIÓN INFERIOR: CARGA MASIVA
            with ui.row().classes('w-full'):
                with ui.column().classes('w-full bg-[#161B22] p-8 rounded-3xl border border-gray-800 shadow-2xl'):
                    ui.label('Importación Masiva de Usuarios').classes('text-xl text-[#83ABF1] font-bold mb-4')
                    with ui.row().classes('items-center gap-10'):
                        ui.upload(on_upload=self.procesar_carga_masiva, 
                                  label="Cargar Excel o CSV", 
                                  auto_upload=True).classes('w-[500px]')
                        
                        with ui.column().classes('text-gray-500 text-sm'):
                            ui.label('• Columnas: username, password, org_id, tests')
                            ui.label('• Opcionales: sape_sectors, sapp_profile, sapp_groups')
                            ui.label('• El sistema actualizará datos si el usuario ya existe.')