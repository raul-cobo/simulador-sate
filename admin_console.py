import os
import pandas as pd
import io
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
        self.editing_org_id = None

    def render(self):
        self.contenedor.clear()
        if app.storage.user.get('role') == 'ADMIN':
            self.admin_autenticado = True

        if not self.admin_autenticado:
            self.render_login()
        else:
            self.render_dashboard()

    def render_login(self):
        with self.contenedor.classes('justify-center items-center'):
            with ui.card().classes('p-10 rounded-3xl bg-white shadow-2xl items-center').style('width: 25vw; min-width: 320px;'):
                ui.image('logo_original.png').classes('w-48 mb-2')
                ui.label('CONSOLA MAESTRA').classes('text-xl font-bold text-gray-800 mb-6 tracking-widest')
                u_in = ui.input('Usuario').classes('w-full mb-4').props('outlined')
                p_in = ui.input('Contraseña', password=True, password_toggle_button=True).classes('w-full mb-6').props('outlined')
                p_in.on('keydown.enter', lambda: self.verificar_admin(u_in.value, p_in.value))
                ui.button('ACCEDER', on_click=lambda: self.verificar_admin(u_in.value, p_in.value)).classes('w-full py-4 text-white font-bold rounded-xl').style(f'background-color: {DARK_BLUE}')

    def verificar_admin(self, user, pwd):
        if not supabase: return
        try:
            res = supabase.table('admins').select('*').eq('username', user).eq('password', pwd).execute()
            if res.data:
                app.storage.user.update({'role': 'ADMIN', 'authenticated': True, 'username': user})
                self.render()
            else:
                ui.notify('Credenciales incorrectas', type='negative')
        except Exception as e: ui.notify(f'Error: {e}', type='negative')

    def cerrar_sesion(self):
        app.storage.user.clear()
        self.admin_autenticado = False
        self.render()

    # ==========================================
    # GESTIÓN DE ORGANIZACIONES
    # ==========================================
    def preparar_edicion(self, org, inputs):
        self.editing_org_id = org['id']
        inputs['nom'].value = org['name']
        inputs['pwd'].value = org['password']
        inputs['sape'].value = org['sape_licenses']
        inputs['sapp'].value = org['sapp_licenses']
        inputs['demo'].value = org.get('is_demo', False)
        
        p = org.get('privileges', {})
        inputs['p_usr'].value = p.get('can_create_users', False)
        inputs['p_test'].value = p.get('can_assign_tests', False)
        inputs['p_stat'].value = p.get('can_view_org_stats', False)
        inputs['p_comp'].value = p.get('can_compare_anon', False)
        
        ui.notify(f"Modo Edición: {org['name']}", type='info')

    def guardar_organizacion(self, inputs):
        if not inputs['nom'].value or not inputs['pwd'].value:
            ui.notify('Nombre y Contraseña son obligatorios', type='warning')
            return

        datos = {
            "name": inputs['nom'].value.strip(),
            "password": inputs['pwd'].value.strip(),
            "sape_licenses": int(inputs['sape'].value),
            "sapp_licenses": int(inputs['sapp'].value),
            "is_demo": inputs['demo'].value,
            "privileges": {
                "can_create_users": inputs['p_usr'].value,
                "can_assign_tests": inputs['p_test'].value,
                "can_view_org_stats": inputs['p_stat'].value,
                "can_compare_anon": inputs['p_comp'].value,
                "can_request_custom": True
            }
        }
        
        try:
            if self.editing_org_id:
                supabase.table('organizations').update(datos).eq('id', self.editing_org_id).execute()
                ui.notify("Organización actualizada correctamente", type='positive')
            else:
                datos["id"] = datos["name"].lower().replace(" ", "_")
                datos["is_active"] = True
                supabase.table('organizations').insert(datos).execute()
                ui.notify("Nueva organización registrada", type='positive')
            
            self.editing_org_id = None
            self.render()
        except Exception as e:
            ui.notify(f"Error de base de datos: {e}", type='negative')

    # ==========================================
    # CARGA MASIVA DIRIGIDA Y PLANTILLAS
    # ==========================================
    def descargar_plantilla(self):
        df = pd.DataFrame({
            "username": ["usuario_ejemplo_01", "usuario_ejemplo_02"],
            "password": ["ClaveSegura1*", "ClaveSegura2*"],
            "tests": ["SAPE", "AMBAS"],
            "sape_sectors": ["TECH, CONSULTORIA", "HOSTELERIA"],
            "sapp_profile": ["", "sanitaria, no_sanitaria"],
            "sapp_groups": ["", "personales, profesionales"]
        })
        file_path = "Plantilla_Audeo_Corporativa.xlsx"
        df.to_excel(file_path, index=False)
        ui.download(file_path)
        ui.notify('Plantilla descargada', type='positive')

    async def procesar_carga_masiva_dirigida(self, e, org_id):
        if not org_id:
            ui.notify('Por favor, selecciona primero una organización en el desplegable', type='warning')
            return
        
        ui.notify(f'Procesando archivo para: {org_id}...', type='info')
        try:
            content = io.BytesIO(e.content.read())
            if e.name.endswith('.csv'):
                df = pd.read_csv(content, sep=None, engine='python')
            else:
                df = pd.read_excel(content)

            df.columns = df.columns.str.lower().str.strip()
            
            # Validación de columnas obligatorias (org_id ya no es necesario en el excel)
            req = ['username', 'password', 'tests']
            if not all(col in df.columns for col in req):
                ui.notify('El archivo no tiene las columnas mínimas: username, password, tests', type='negative')
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
                    "org_id": org_id, # INYECCIÓN DIRECTA Y SEGURA
                    "role": "USER",
                    "is_deleted": False,
                    "profile_data": profile_data
                }
                
                # Insertamos en Supabase
                supabase.table("users").upsert(payload).execute()
                
                # Registramos en el Action Log (Historial Verde-Azul de Creación)
                supabase.table('action_logs').insert({
                    'org_id': org_id, 'action_type': 'REGISTER_BULK', 'target_user': payload['username'], 
                    'performed_by': 'SUPER_ADMIN', 'status_color': 'green-blue'
                }).execute()
                
                count += 1

            ui.notify(f'Éxito: {count} usuarios importados a la organización {org_id}.', type='positive')
            self.render()

        except Exception as ex:
            ui.notify(f'Error procesando Excel: {ex}', type='negative')
            # Log de error (Amarillo-Rojo)
            supabase.table('action_logs').insert({
                'org_id': org_id, 'action_type': 'ERROR_BULK', 'target_user': 'ARCHIVO_MASIVO', 
                'performed_by': 'SUPER_ADMIN', 'status_color': 'yellow-red', 'metadata': {'error': str(ex)}
            }).execute()

    # ==========================================
    # RENDER DEL DASHBOARD PRINCIPAL
    # ==========================================
    def render_dashboard(self):
        with self.contenedor.classes('p-8'):
            # Header
            with ui.row().classes('w-full justify-between items-center mb-6 bg-[#161B22] p-6 rounded-2xl border border-gray-800 shadow-xl'):
                with ui.row().classes('items-center gap-6'):
                    ui.image('logo_blanco.png').classes('w-40')
                    ui.label('ERP DE ADMINISTRACIÓN AUDEO').classes('text-2xl text-white font-black tracking-tight')
                ui.button('CERRAR SESIÓN', on_click=self.cerrar_sesion, color='red').classes('px-8 py-2 font-bold rounded-xl')

            # SISTEMA DE PESTAÑAS
            with ui.tabs().classes('w-full bg-[#161B22] text-[#83ABF1] rounded-t-2xl font-bold') as tabs:
                t_orgs = ui.tab('ORGANIZACIONES', icon='domain')
                t_users = ui.tab('USUARIOS GLOBALES', icon='people')
                t_stats = ui.tab('ESTADÍSTICAS Y LOGS', icon='analytics')

            with ui.tab_panels(tabs, value=t_orgs).classes('w-full bg-[#161B22] border border-gray-800 rounded-b-2xl shadow-2xl p-0'):
                
                # ----------------------------------------------------------------
                # PESTAÑA 1: ORGANIZACIONES
                # ----------------------------------------------------------------
                with ui.tab_panel(t_orgs).classes('p-8'):
                    with ui.row().classes('w-full gap-8 items-start'):
                        
                        # Formulario de Alta y Edición
                        with ui.column().classes('w-1/3 min-w-[400px] bg-[#0E1117] p-8 rounded-2xl border border-gray-800'):
                            ui.label('Configuración de Organización').classes('text-xl text-[#83ABF1] font-bold mb-4 border-b border-gray-800 pb-2')
                            
                            inputs = {
                                'nom': ui.input('Nombre Comercial').classes('w-full mb-2').props('dark outlined'),
                                'pwd': ui.input('Clave Maestra').classes('w-full mb-4').props('dark outlined'),
                                'sape': ui.number('Lic. SAPE', value=0, min=0).classes('w-full mb-2').props('dark outlined'),
                                'sapp': ui.number('Lic. SAPP', value=0, min=0).classes('w-full mb-4').props('dark outlined'),
                                'demo': ui.checkbox('Cuenta DEMO (Pruebas al 10%)').classes('text-white mb-4 border-b border-gray-800 pb-4 w-full'),
                                
                                'p_usr': ui.checkbox('Puede crear/editar usuarios').classes('text-white'),
                                'p_test': ui.checkbox('Puede asignar pruebas/sectores').classes('text-white'),
                                'p_stat': ui.checkbox('Ver estadísticas de su organización').classes('text-white'),
                                'p_comp': ui.checkbox('Ver comparativas anónimas sectoriales').classes('text-white')
                            }
                            
                            ui.button('GUARDAR ORGANIZACIÓN', on_click=lambda: self.guardar_organizacion(inputs)).classes('w-full py-4 text-white font-bold rounded-xl mt-6').style(f'background-color: {DARK_BLUE}')
                            ui.button('LIMPIAR FORMULARIO', on_click=self.render).classes('w-full mt-2').props('flat color=gray')

                        # Listado de Organizaciones Activas
                        with ui.column().classes('flex-1 bg-[#0E1117] p-8 rounded-2xl border border-gray-800'):
                            ui.label('Cartera de Clientes Activos').classes('text-xl text-[#83ABF1] font-bold mb-4')
                            try:
                                orgs = supabase.table('organizations').select('*').order('name').execute().data
                                if orgs:
                                    for o in orgs:
                                        with ui.row().classes('w-full justify-between items-center p-4 border-b border-gray-800 hover:bg-[#161B22] rounded-lg transition-colors'):
                                            with ui.column().classes('gap-1'):
                                                ui.label(o['name'].upper()).classes('text-white font-bold text-lg')
                                                ui.label(f"Org_ID: {o['id']} | Demos: {'Activado' if o.get('is_demo') else 'No'}").classes('text-xs text-gray-500')
                                                ui.label(f"SAPE: {o['sape_licenses']} | SAPP: {o['sapp_licenses']}").classes('text-sm text-[#83ABF1]')
                                            with ui.row().classes('gap-2'):
                                                ui.button(icon='edit', on_click=lambda o=o: self.preparar_edicion(o, inputs)).props('flat round color=blue')
                                                # No incluimos borrar por defecto en ERP B2B para evitar borrar datos en cascada, pero lo dejamos preparado
                                else:
                                    ui.label("Aún no hay organizaciones creadas.").classes('text-gray-500 italic')
                            except Exception as e:
                                ui.label(f"Error cargando base de datos: {e}").classes('text-red-500')

                # ----------------------------------------------------------------
                # PESTAÑA 2: USUARIOS GLOBALES Y CARGA MASIVA
                # ----------------------------------------------------------------
                with ui.tab_panel(t_users).classes('p-8'):
                    with ui.row().classes('w-full gap-8 items-start'):
                        
                        # Carga Masiva Dirigida
                        with ui.column().classes('w-1/3 bg-[#0E1117] p-6 rounded-xl border border-gray-800'):
                            ui.label('Carga Masiva Dirigida').classes('text-xl text-[#83ABF1] font-bold mb-4')
                            
                            org_options = {o['id']: o['name'] for o in orgs} if orgs else {}
                            target_org = ui.select(org_options, label='1. Selecciona Organización Destino').classes('w-full mb-6').props('dark outlined')
                            
                            ui.label('2. Sube el Excel para inyectar').classes('text-sm text-gray-400 mb-2')
                            ui.upload(on_upload=lambda e: self.procesar_carga_masiva_dirigida(e, target_org.value), label="Subir Archivo", auto_upload=True).classes('w-full mb-6')
                            
                            ui.button('Descargar Plantilla XLSX', icon='download', on_click=self.descargar_plantilla).classes('w-full bg-green-700 text-white font-bold')

                        # Buscador Global de Usuarios
                        with ui.column().classes('flex-1 bg-[#0E1117] p-6 rounded-xl border border-gray-800'):
                            ui.label('Directorio Global de Usuarios').classes('text-xl text-[#83ABF1] font-bold mb-4')
                            try:
                                usr_data = supabase.table('users').select('username, org_id, role, created_at').order('created_at', desc=True).limit(100).execute().data
                                if usr_data:
                                    cols_usr = [
                                        {'name': 'username', 'label': 'Usuario', 'field': 'username', 'align': 'left'},
                                        {'name': 'org_id', 'label': 'Empresa', 'field': 'org_id', 'align': 'center'},
                                        {'name': 'role', 'label': 'Rol', 'field': 'role', 'align': 'center'},
                                        {'name': 'created_at', 'label': 'Fecha Alta', 'field': 'created_at', 'align': 'right'}
                                    ]
                                    # Limpiamos las fechas
                                    for row in usr_data: row['created_at'] = row['created_at'][:10]
                                    ui.table(columns=cols_usr, rows=usr_data, row_key='username').classes('w-full bg-[#161B22] text-white')
                                else:
                                    ui.label('No hay usuarios en la plataforma.').classes('text-gray-500')
                            except Exception as e: ui.label(f'Error leyendo usuarios: {e}')

                # ----------------------------------------------------------------
                # PESTAÑA 3: ESTADÍSTICAS Y LOGS (HISTORIAL COLORES)
                # ----------------------------------------------------------------
                with ui.tab_panel(t_stats).classes('p-8'):
                    ui.label('Monitor de Actividad B2B').classes('text-xl text-[#83ABF1] font-bold mb-6')
                    
                    # Leyenda de Colores Documento Maestro
                    with ui.row().classes('gap-6 mb-8 w-full justify-center bg-[#0E1117] p-4 rounded-xl border border-gray-800'):
                        ui.label('🟢 Activas').classes('text-green-400 font-bold')
                        ui.label('🟢🔵 Nuevas').classes('text-blue-400 font-bold')
                        ui.label('🟢🟡 Editadas').classes('text-yellow-400 font-bold')
                        ui.label('🟡🔴 Error').classes('text-orange-500 font-bold')
                        ui.label('🔴 Eliminadas').classes('text-red-500 font-bold')

                    # Tabla de Action Logs
                    with ui.column().classes('w-full bg-[#0E1117] p-6 rounded-xl border border-gray-800'):
                        try:
                            logs = supabase.table('action_logs').select('*').order('created_at', desc=True).limit(50).execute().data
                            if logs:
                                for log in logs:
                                    color = log.get('status_color', 'green')
                                    bg_col = "bg-green-500" if color == "green" else "bg-blue-500" if color == "green-blue" else "bg-yellow-500" if color == "green-yellow" else "bg-orange-500" if color == "yellow-red" else "bg-red-500"
                                    
                                    with ui.row().classes('w-full items-center gap-6 mb-2 p-3 border-b border-gray-800/50 hover:bg-[#161B22]'):
                                        ui.element('div').classes(f'w-3 h-3 rounded-full shadow-[0_0_10px_rgba(255,255,255,0.2)] {bg_col}')
                                        ui.label(log.get('created_at', '')[:16].replace('T', ' ')).classes('text-gray-500 text-sm w-32')
                                        ui.label(log.get('org_id')).classes('text-white font-bold text-sm w-40 truncate')
                                        ui.label(log.get('action_type')).classes('text-[#83ABF1] text-xs font-bold w-32')
                                        ui.label(log.get('target_user')).classes('text-gray-300 text-sm')
                            else:
                                ui.label('Aún no hay registros de actividad.').classes('text-gray-500')
                        except Exception as e: ui.label(f'Error cargando logs: {e}')