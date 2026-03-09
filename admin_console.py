import os
import pandas as pd
import io
from nicegui import ui, app
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime

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

# --- LISTAS OFICIALES ---
SECTORES_SAPE = [
    'TECH', 'CONSULTORIA', 'PYME', 'HOSTELERIA', 'AUTOEMPLEO', 
    'SOCIAL', 'INTRA', 'SALUD', 'PSICOLOGIA_SANITARIA', 'PSICOLOGÍA_NO_SANITARIA'
]
PERFILES_SAPP = [
    'Psicología educativa', 'Psicología organizacional', 
    'Psicología sanitaria', 'Psicología social'
]
COMPETENCIAS_SAPP = [
    'Competencias personales', 'Competencias profesionales', 'Competencias técnicas'
]

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
        inputs['pwd'].value = org.get('password', '')
        inputs['sape'].value = org['sape_licenses']
        inputs['sapp'].value = org['sapp_licenses']
        inputs['demo'].value = org.get('is_demo', False)
        
        p = org.get('privileges', {})
        inputs['p_usr'].value = p.get('can_create_users', False)
        inputs['p_stat'].value = p.get('can_view_org_stats', False)
        inputs['p_comp'].value = p.get('can_compare_anon', False)
        
        inputs['p_sape'].value = p.get('can_assign_sape', False)
        inputs['p_sape_sectores'].value = p.get('allowed_sape_sectors', [])
        
        inputs['p_sapp'].value = p.get('can_assign_sapp', False)
        inputs['p_sapp_perfiles'].value = p.get('allowed_sapp_profiles', [])
        inputs['p_sapp_comp'].value = p.get('allowed_sapp_comps', [])
        
        ui.notify(f"Modo Edición: {org['name']}", type='info')

    def guardar_organizacion(self, inputs: dict) -> None:
        if not inputs['nom'].value:
            ui.notify('El nombre comercial es obligatorio', type='warning')
            return

        org_payload = {
            "name": inputs['nom'].value.strip(),
            "password": inputs['pwd'].value.strip() if inputs['pwd'].value else "",
            "sape_licenses": int(inputs['sape'].value or 0),
            "sapp_licenses": int(inputs['sapp'].value or 0),
            "is_demo": inputs['demo'].value,
            "privileges": {
                "can_create_users": inputs['p_usr'].value,
                "can_view_org_stats": inputs['p_stat'].value,
                "can_compare_anon": inputs['p_comp'].value,
                "can_request_custom": True,
                "can_assign_sape": inputs['p_sape'].value,
                "allowed_sape_sectors": inputs['p_sape_sectores'].value or [],
                "can_assign_sapp": inputs['p_sapp'].value,
                "allowed_sapp_profiles": inputs['p_sapp_perfiles'].value or [],
                "allowed_sapp_comps": inputs['p_sapp_comp'].value or []
            }
        }

        try:
            if getattr(self, 'editing_org_id', None):
                supabase.table('organizations').update(org_payload).eq('id', self.editing_org_id).execute()
                ui.notify('Organización actualizada', type='positive')
            else:
                org_payload["id"] = org_payload["name"].lower().replace(" ", "_")
                org_payload["is_active"] = True
                org_payload["licencias_compradas"] = 0 

                res_org = supabase.table('organizations').insert(org_payload).execute()
                
                if not res_org.data:
                    raise Exception("Fallo al obtener la organización guardada.")
                
                new_org_id = res_org.data[0]['id']
                
                admin_username = inputs.get('admin_user').value.strip()
                admin_password = inputs.get('admin_pass').value.strip()

                if not admin_username or not admin_password:
                    raise Exception("Debes especificar el Usuario y Contraseña del Administrador.")

                user_payload = {
                    "username": admin_username,
                    "password": admin_password,
                    "org_id": new_org_id,
                    "role": "ORG_ADMIN",
                    "is_deleted": False,
                    "profile_data": {
                        "is_main_admin": True,
                        "created_at": datetime.now().isoformat()
                    }
                }

                supabase.table('users').insert(user_payload).execute()
                ui.notify(f'Organización y Administrador "{admin_username}" creados con éxito', type='positive')

            self.editing_org_id = None
            self.render() 
            
        except Exception as e:
            ui.notify(f'Error de base de datos: {e}', type='negative')

    # ==========================================
    # PANEL DE FACTURACIÓN Y LICENCIAS
    # ==========================================
    def render_billing_panel(self):
        def calcular_precio(cantidad: int) -> float:
            if cantidad >= 500: return 3.00
            elif cantidad >= 51: return 5.00
            elif cantidad >= 10: return 7.00
            elif cantidad >= 1: return 9.90
            return 0.0

        estado = {
            'org_seleccionada': None,
            'cantidad': 0,
            'precio_unidad': 0.0,
            'total': 0.0
        }

        # Extraemos orgs de la base de datos para el select
        try:
            res_orgs = supabase.table('organizations').select('id, name, licencias_compradas').execute()
            lista_orgs_raw = res_orgs.data
            lista_orgs = {org['id']: f"{org['name']} (Disponibles: {org.get('licencias_compradas', 0)})" for org in lista_orgs_raw}
            
            # Buscamos solicitudes de compra no atendidas en los logs (últimos 7 días)
            res_solicitudes = supabase.table('action_logs').select('*')\
                .eq('action_type', 'SOLICITUD_COMPRA')\
                .order('created_at', desc=True).limit(10).execute()
            solicitudes = res_solicitudes.data
            
        except Exception as e:
            lista_orgs = {}
            lista_orgs_raw = []
            solicitudes = []

        def actualizar_calculos(e=None, forced_qty=None):
            try: cantidad = forced_qty if forced_qty is not None else (int(e.value) if e and e.value else 0)
            except ValueError: cantidad = 0
                
            estado['cantidad'] = cantidad
            estado['precio_unidad'] = calcular_precio(cantidad)
            estado['total'] = estado['cantidad'] * estado['precio_unidad']
            
            lbl_precio_unidad.set_text(f"{estado['precio_unidad']:.2f} € / ud")
            lbl_total.set_text(f"{estado['total']:,.2f} €".replace(',', '.'))
            
            if input_cantidad.value != cantidad:
                input_cantidad.set_value(cantidad)
                
            btn_asignar.set_visibility(cantidad > 0 and estado['org_seleccionada'] is not None)

        def seleccionar_org(e=None, forced_org=None):
            estado['org_seleccionada'] = forced_org if forced_org else e.value
            if select_org.value != estado['org_seleccionada']:
                select_org.set_value(estado['org_seleccionada'])
            btn_asignar.set_visibility(estado['cantidad'] > 0 and estado['org_seleccionada'] is not None)

        def cargar_solicitud_en_calculadora(org_id, cantidad_texto):
            # Extrae el número de la cadena "Solicitados X ciclos"
            import re
            numeros = re.findall(r'\d+', cantidad_texto)
            if numeros:
                qty = int(numeros[0])
                seleccionar_org(forced_org=org_id)
                actualizar_calculos(forced_qty=qty)
                ui.notify(f"Solicitud cargada en la calculadora.", type='info')

        def procesar_asignacion():
            org_id = estado['org_seleccionada']
            cantidad = estado['cantidad']
            if not org_id or cantidad <= 0: return
            
            try:
                # Obtenemos licencias actuales
                res_org = supabase.table('organizations').select('licencias_compradas').eq('id', org_id).single().execute()
                actuales = res_org.data.get('licencias_compradas', 0) if res_org.data else 0
                
                # Sumamos las compradas
                nuevas = actuales + cantidad
                supabase.table('organizations').update({'licencias_compradas': nuevas}).eq('id', org_id).execute()
                
                # Registramos el log financiero
                supabase.table('action_logs').insert({
                    'org_id': org_id, 'action_type': 'BILLING_PURCHASE', 'target_user': f'+{cantidad} Licencias', 
                    'performed_by': 'SUPER_ADMIN', 'status_color': 'green', 'metadata': {'total_eur': estado['total']}
                }).execute()

                ui.notify(f"✅ {cantidad} licencias asignadas. Total a facturar: {estado['total']:.2f}€", type='positive')
                self.render() # Recarga todo el dashboard para actualizar el dropdown
                
            except Exception as ex:
                ui.notify(f"Error asignando licencias: {ex}", type='negative')

        with ui.column().classes('w-full gap-8 items-start'):
            
            # --- PANEL SUPERIOR: SOLICITUDES ENTRANTES ---
            if solicitudes:
                with ui.column().classes('w-full bg-[#161B22] border-2 border-[#83ABF1] rounded-2xl p-6 shadow-xl relative'):
                    ui.icon('notifications_active', color='#83ABF1', size='2rem').classes('absolute -top-4 -right-4 bg-[#0E1117] rounded-full p-2 border border-[#83ABF1]')
                    ui.label('SOLICITUDES DE COMPRA PENDIENTES').classes('text-[#83ABF1] font-black tracking-widest text-lg mb-4')
                    
                    for sol in solicitudes:
                        # Buscamos el nombre de la org
                        org_name = next((o['name'] for o in lista_orgs_raw if o['id'] == sol['org_id']), sol['org_id'])
                        fecha = sol.get('created_at', '')[:16].replace('T', ' a las ')
                        
                        with ui.row().classes('w-full items-center justify-between p-4 bg-[#0E1117] rounded-xl border border-blue-900/50 mb-2'):
                            with ui.column().classes('gap-1'):
                                ui.label(f"{org_name}").classes('text-white font-bold text-lg')
                                ui.label(f"{sol['target_user']} ({sol.get('metadata', {}).get('error', 'Plan B2B')})").classes('text-[#83ABF1] font-bold')
                                ui.label(f"Recibido el {fecha}").classes('text-gray-500 text-xs')
                            
                            ui.button('ATENDER Y FACTURAR', icon='point_of_sale', 
                                     on_click=lambda org=sol['org_id'], qt=sol['target_user']: cargar_solicitud_en_calculadora(org, qt))\
                                     .classes('bg-[#0D248D] text-white font-bold rounded-lg')

            # --- PANEL INFERIOR: CALCULADORA B2B ---
            with ui.row().classes('w-full gap-8'):
                
                # FORMULARIO IZQUIERDO
                with ui.column().classes('flex-grow bg-[#0E1117] p-8 rounded-2xl border border-gray-800'):
                    ui.label('Asignación Manual de Licencias').classes('text-xl text-[#83ABF1] font-bold mb-6')
                    
                    select_org = ui.select(lista_orgs, label='1. Selecciona la Organización', on_change=seleccionar_org).classes('w-full mb-6')
                    select_org.props('dark filled color="blue"')
                    
                    input_cantidad = ui.number(label='2. Volumen de Licencias (1 licencia = 3 pasaciones)', value=0, min=0, on_change=actualizar_calculos).classes('w-full text-xl')
                    input_cantidad.props('dark filled color="blue"')

                # CALCULADORA / RECIBO DERECHO
                with ui.card().classes('w-96 bg-[#161B22] border border-[#83ABF1]/30 p-8 shadow-2xl flex flex-col justify-between rounded-2xl'):
                    ui.label('RESUMEN DE FACTURACIÓN').classes('text-[#83ABF1] font-bold text-sm tracking-widest mb-6 border-b border-gray-800 pb-2')
                    
                    with ui.row().classes('w-full justify-between items-center mb-4'):
                        ui.label('Precio unitario:').classes('text-gray-400')
                        lbl_precio_unidad = ui.label('0.00 € / ud').classes('text-white font-mono font-bold text-lg')
                    
                    with ui.row().classes('w-full justify-between items-center mt-6 pt-4 border-t border-gray-800'):
                        ui.label('TOTAL:').classes('text-gray-400 font-bold')
                        lbl_total = ui.label('0.00 €').classes('text-4xl text-[#22C55E] font-black font-mono')

                    btn_asignar = ui.button('CONFIRMAR Y ASIGNAR', on_click=procesar_asignacion).classes('w-full bg-[#0D248D] text-white font-bold mt-8 py-4 rounded-xl shadow-lg')
                    btn_asignar.set_visibility(False)

            # TABLA DE PRECIOS COMO REFERENCIA
            with ui.column().classes('w-full bg-[#161B22] p-6 rounded-2xl border border-gray-800 mt-4'):
                ui.label('Tabla Oficial de Precios B2B').classes('text-sm text-gray-400 font-bold mb-2')
                with ui.row().classes('w-full justify-between gap-4'):
                    ui.label('• Unidad (1): 9.90€').classes('text-xs text-gray-500')
                    ui.label('• Pequeño (10-50): 7.00€').classes('text-xs text-gray-500')
                    ui.label('• Centros (51-200): 5.00€').classes('text-xs text-gray-500')
                    ui.label('• Masivo (+500): 3.00€').classes('text-xs text-gray-500')

    # ==========================================
    # CARGA MASIVA DIRIGIDA Y PLANTILLAS
    # ==========================================
    def descargar_plantilla(self):
        df = pd.DataFrame({
            "username": ["usuario_ejemplo_01", "usuario_ejemplo_02"],
            "password": ["ClaveSegura1*", "ClaveSegura2*"],
            "tests": ["SAPE", "AMBAS"],
            "sape_sectors": ["TECH, CONSULTORIA", "HOSTELERIA"],
            "sapp_profile": ["", "Psicología sanitaria, Psicología educativa"],
            "sapp_groups": ["", "Competencias personales, Competencias profesionales"]
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
                    "org_id": org_id,
                    "role": "USER",
                    "is_deleted": False,
                    "profile_data": profile_data
                }
                
                supabase.table("users").upsert(payload).execute()
                
                supabase.table('action_logs').insert({
                    'org_id': org_id, 'action_type': 'REGISTER_BULK', 'target_user': payload['username'], 
                    'performed_by': 'SUPER_ADMIN', 'status_color': 'green-blue'
                }).execute()
                
                count += 1

            ui.notify(f'Éxito: {count} usuarios importados a la organización {org_id}.', type='positive')
            self.render()

        except Exception as ex:
            ui.notify(f'Error procesando Excel: {ex}', type='negative')
            supabase.table('action_logs').insert({
                'org_id': org_id, 'action_type': 'ERROR_BULK', 'target_user': 'ARCHIVO_MASIVO', 
                'performed_by': 'SUPER_ADMIN', 'status_color': 'yellow-red', 'metadata': {'error': str(ex)}
            }).execute()

    # ==========================================
    # RENDER DEL DASHBOARD PRINCIPAL
    # ==========================================
    def render_dashboard(self):
        with self.contenedor.classes('p-8'):
            with ui.row().classes('w-full justify-between items-center mb-6 bg-[#161B22] p-6 rounded-2xl border border-gray-800 shadow-xl'):
                with ui.row().classes('items-center gap-6'):
                    ui.image('logo_blanco.png').classes('w-40')
                    ui.label('ERP DE ADMINISTRACIÓN AUDEO').classes('text-2xl text-white font-black tracking-tight')
                ui.button('CERRAR SESIÓN', on_click=self.cerrar_sesion, color='red').classes('px-8 py-2 font-bold rounded-xl')

            # --- PESTAÑAS ---
            with ui.tabs().classes('w-full bg-[#161B22] text-[#83ABF1] rounded-t-2xl font-bold') as tabs:
                t_orgs = ui.tab('ORGANIZACIONES', icon='domain')
                t_billing = ui.tab('FACTURACIÓN B2B', icon='point_of_sale')
                t_users = ui.tab('USUARIOS GLOBALES', icon='people')
                t_stats = ui.tab('ESTADÍSTICAS Y LOGS', icon='analytics')

            with ui.tab_panels(tabs, value=t_orgs).classes('w-full bg-[#161B22] border border-gray-800 rounded-b-2xl shadow-2xl p-0'):
                
                # PANEL 1: ORGANIZACIONES
                with ui.tab_panel(t_orgs).classes('p-8'):
                    with ui.row().classes('w-full gap-8 items-start'):
                        
                        # FORMULARIO DE ALTA/EDICIÓN
                        with ui.column().classes('w-1/3 min-w-[420px] bg-[#0E1117] p-8 rounded-2xl border border-gray-800'):
                            ui.label('Configuración Básica').classes('text-lg text-[#83ABF1] font-bold mb-4 border-b border-gray-800 pb-2 w-full')
                            
                            inputs = {
                                'nom': ui.input('Nombre Comercial').classes('w-full mb-2').props('dark outlined'),
                                'pwd': ui.input('Clave Maestra').classes('w-full mb-4').props('dark outlined'),
                                'sape': ui.number('Lic. SAPE', value=0, min=0).classes('w-full mb-2').props('dark outlined'),
                                'sapp': ui.number('Lic. SAPP', value=0, min=0).classes('w-full mb-4').props('dark outlined'),
                                'demo': ui.checkbox('Cuenta DEMO (Pruebas al 10%)').classes('text-white mb-6 w-full'),
                                
                                'p_usr': ui.checkbox('Puede crear/editar usuarios').classes('text-white'),
                                'p_stat': ui.checkbox('Ver estadísticas de su organización').classes('text-white'),
                                'p_comp': ui.checkbox('Ver comparativas anónimas sectoriales').classes('text-white mb-4'),
                                
                                'p_sape': ui.checkbox('Habilitar asignación de SAPE').classes('text-[#83ABF1] font-bold mt-2'),
                                'p_sape_sectores': ui.select(SECTORES_SAPE, multiple=True, label='Sectores SAPE Permitidos').classes('w-full mb-4 ml-4').props('dark outlined use-chips'),
                                
                                'p_sapp': ui.checkbox('Habilitar asignación de SAPP').classes('text-green-400 font-bold mt-2'),
                                'p_sapp_perfiles': ui.select(PERFILES_SAPP, multiple=True, label='Sectores SAPP Permitidos').classes('w-full mb-2 ml-4').props('dark outlined use-chips'),
                                'p_sapp_comp': ui.select(COMPETENCIAS_SAPP, multiple=True, label='Competencias SAPP Permitidas').classes('w-full mb-2 ml-4').props('dark outlined use-chips')
                            }
                            
                            inputs['p_sape_sectores'].bind_visibility_from(inputs['p_sape'], 'value')
                            inputs['p_sapp_perfiles'].bind_visibility_from(inputs['p_sapp'], 'value')
                            inputs['p_sapp_comp'].bind_visibility_from(inputs['p_sapp'], 'value')

                            with ui.column().classes('w-full mt-6 p-6 border border-[#83ABF1]/30 rounded-xl bg-[#161B22] shadow-lg'):
                                ui.label('CREDENCIALES DE ACCESO').classes('text-[#83ABF1] text-xs font-black tracking-widest mb-1')
                                ui.label('Crea el usuario que gestionará esta organización.').classes('text-gray-400 text-xs mb-4')
                                
                                inputs['admin_user'] = ui.input('Usuario Admin (ej: ugr_admin)').props('dark outlined').classes('w-full mb-3')
                                inputs['admin_pass'] = ui.input('Contraseña Admin', password=True).props('dark outlined password-toggle-button').classes('w-full')
                            
                            ui.button('GUARDAR ORGANIZACIÓN', on_click=lambda: self.guardar_organizacion(inputs)).classes('w-full py-4 text-[#0E1117] font-bold rounded-xl mt-6').style(f'background-color: {DARK_BLUE}')
                            ui.button('LIMPIAR FORMULARIO', on_click=self.render).classes('w-full mt-2').props('flat color=gray')

                        # LISTADO DE ORGANIZACIONES
                        with ui.column().classes('flex-1 bg-[#0E1117] p-8 rounded-2xl border border-gray-800'):
                            ui.label('Cartera de Clientes Activos').classes('text-xl text-[#83ABF1] font-bold mb-4')
                            try:
                                orgs = supabase.table('organizations').select('*').order('name').execute().data
                                if orgs:
                                    for o in orgs:
                                        with ui.row().classes('w-full justify-between items-center p-4 border-b border-gray-800 hover:bg-[#161B22] rounded-lg transition-colors'):
                                            with ui.column().classes('gap-1'):
                                                ui.label(o['name'].upper()).classes('text-white font-bold text-lg')
                                                ui.label(f"Org_ID: {o['id']}").classes('text-xs text-gray-500')
                                                ui.label(f"SAPE: {o['sape_licenses']} | SAPP: {o['sapp_licenses']} | Ciclos: {o.get('licencias_compradas', 0)}").classes('text-sm text-[#83ABF1] font-bold')
                                            with ui.row().classes('gap-2'):
                                                ui.button(icon='edit', on_click=lambda o=o: self.preparar_edicion(o, inputs)).props('flat round color=blue')
                                else:
                                    ui.label("Aún no hay organizaciones creadas.").classes('text-gray-500 italic')
                            except Exception as e:
                                ui.label(f"Error cargando base de datos: {e}").classes('text-red-500')

                # PANEL 2: FACTURACIÓN B2B
                with ui.tab_panel(t_billing).classes('p-8'):
                    self.render_billing_panel()

                # PANEL 3: USUARIOS GLOBALES
                with ui.tab_panel(t_users).classes('p-8'):
                    with ui.row().classes('w-full gap-8 items-start'):
                        with ui.column().classes('w-1/3 bg-[#0E1117] p-6 rounded-xl border border-gray-800'):
                            ui.label('Carga Masiva Dirigida').classes('text-xl text-[#83ABF1] font-bold mb-4')
                            try:
                                orgs = supabase.table('organizations').select('id, name').order('name').execute().data
                                org_options = {o['id']: o['name'] for o in orgs} if orgs else {}
                            except:
                                org_options = {}

                            target_org = ui.select(org_options, label='1. Selecciona Organización Destino').classes('w-full mb-6').props('dark outlined')
                            ui.label('2. Sube el Excel para inyectar').classes('text-sm text-gray-400 mb-2')
                            ui.upload(on_upload=lambda e: self.procesar_carga_masiva_dirigida(e, target_org.value), label="Subir Archivo", auto_upload=True).classes('w-full mb-6')
                            ui.button('Descargar Plantilla XLSX', icon='download', on_click=self.descargar_plantilla).classes('w-full bg-green-700 text-white font-bold')

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
                                    for row in usr_data: row['created_at'] = row['created_at'][:10]
                                    ui.table(columns=cols_usr, rows=usr_data, row_key='username').classes('w-full bg-[#161B22] text-white')
                                else:
                                    ui.label('No hay usuarios en la plataforma.').classes('text-gray-500')
                            except Exception as e: ui.label(f'Error leyendo usuarios: {e}')

                # PANEL 4: ESTADÍSTICAS Y LOGS
                with ui.tab_panel(t_stats).classes('p-8'):
                    ui.label('Monitor de Actividad B2B').classes('text-xl text-[#83ABF1] font-bold mb-6')
                    with ui.row().classes('gap-6 mb-8 w-full justify-center bg-[#0E1117] p-4 rounded-xl border border-gray-800'):
                        ui.label('🟢 Activas').classes('text-green-400 font-bold')
                        ui.label('🟢🔵 Nuevas').classes('text-blue-400 font-bold')
                        ui.label('🟢🟡 Editadas').classes('text-yellow-400 font-bold')
                        ui.label('🟡🔴 Error').classes('text-orange-500 font-bold')
                        ui.label('🔴 Eliminadas').classes('text-red-500 font-bold')

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
                                        ui.label(log.get('target_user')).classes('text-gray-300 text-sm truncate w-64')
                            else:
                                ui.label('Aún no hay registros de actividad.').classes('text-gray-500')
                        except Exception as e: ui.label(f'Error cargando logs: {e}')