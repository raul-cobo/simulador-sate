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
        
        # Carga los saldos independientes
        inputs['sape_balance'].value = org.get('sape_balance', 0)
        inputs['sapp_balance'].value = org.get('sapp_balance', 0)
        inputs['saiv_balance'].value = org.get('saiv_balance', 0)
        
        inputs['demo'].value = org.get('is_demo', False)
        inputs['pin'].value = org.get('pin_seguridad', '1234')
        
        inputs['razon_social'].value = org.get('razon_social', '')
        inputs['cif'].value = org.get('cif_nif', '')
        inputs['direccion'].value = org.get('direccion_fiscal', '')
        inputs['cp'].value = org.get('codigo_postal', '')
        inputs['ciudad'].value = org.get('ciudad', '')
        
        p = org.get('privileges', {})
        inputs['p_usr'].value = p.get('can_create_users', False)
        inputs['p_stat'].value = p.get('can_view_org_stats', False)
        inputs['p_comp'].value = p.get('can_compare_anon', False)
        
        inputs['p_sape'].value = p.get('can_assign_sape', False)
        inputs['p_sape_sectores'].value = p.get('allowed_sape_sectors', [])
        
        inputs['p_sapp'].value = p.get('can_assign_sapp', False)
        inputs['p_sapp_perfiles'].value = p.get('allowed_sapp_profiles', [])
        inputs['p_sapp_comp'].value = p.get('allowed_sapp_comps', [])
        
        inputs['p_saiv'].value = p.get('can_assign_saiv', False)
        
        ui.notify(f"Modo Edición: {org['name']}", type='info')

    def guardar_organizacion(self, inputs: dict) -> None:
        if not inputs['nom'].value:
            ui.notify('El nombre comercial es obligatorio', type='warning')
            return

        org_payload = {
            "name": inputs['nom'].value.strip(),
            "password": inputs['pwd'].value.strip() if inputs['pwd'].value else "",
            
            # Guardamos los saldos independientes asignados
            "sape_balance": int(inputs['sape_balance'].value or 0),
            "sapp_balance": int(inputs['sapp_balance'].value or 0),
            "saiv_balance": int(inputs['saiv_balance'].value or 0),
            
            "is_demo": inputs['demo'].value,
            "pin_seguridad": inputs['pin'].value.strip() if inputs['pin'].value else '1234',
            
            "razon_social": inputs['razon_social'].value.strip() if inputs['razon_social'].value else None,
            "cif_nif": inputs['cif'].value.strip() if inputs['cif'].value else None,
            "direccion_fiscal": inputs['direccion'].value.strip() if inputs['direccion'].value else None,
            "codigo_postal": inputs['cp'].value.strip() if inputs['cp'].value else None,
            "ciudad": inputs['ciudad'].value.strip() if inputs['ciudad'].value else None,
            
            "privileges": {
                "can_create_users": inputs['p_usr'].value,
                "can_view_org_stats": inputs['p_stat'].value,
                "can_compare_anon": inputs['p_comp'].value,
                "can_request_custom": True,
                "can_assign_sape": inputs['p_sape'].value,
                "allowed_sape_sectors": inputs['p_sape_sectores'].value or [],
                "can_assign_sapp": inputs['p_sapp'].value,
                "allowed_sapp_profiles": inputs['p_sapp_perfiles'].value or [],
                "allowed_sapp_comps": inputs['p_sapp_comp'].value or [],
                "can_assign_saiv": inputs['p_saiv'].value
            }
        }

        try:
            if getattr(self, 'editing_org_id', None):
                supabase.table('organizations').update(org_payload).eq('id', self.editing_org_id).execute()
                ui.notify('Organización actualizada correctamente', type='positive')
            else:
                org_payload["id"] = org_payload["name"].lower().replace(" ", "_")
                org_payload["is_active"] = True

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
        # Aquí simplificamos la lógica porque los precios pueden variar por test, 
        # pero la inyección manual permitirá inyectar a uno de los tres cajones.
        estado = {
            'org_seleccionada': None,
            'cantidad': 0,
            'tipo_test': 'SAPE'
        }

        try:
            res_orgs = supabase.table('organizations').select('id, name, sape_balance, sapp_balance, saiv_balance, razon_social, cif_nif').execute()
            lista_orgs_raw = res_orgs.data
            lista_orgs = {org['id']: f"{org['name']} (E:{org.get('sape_balance',0)}|P:{org.get('sapp_balance',0)}|V:{org.get('saiv_balance',0)})" for org in lista_orgs_raw}
        except Exception as e:
            lista_orgs = {}
            lista_orgs_raw = []

        def procesar_asignacion_manual():
            org_id = estado['org_seleccionada']
            cantidad = estado['cantidad']
            tipo = estado['tipo_test']
            if not org_id or cantidad <= 0: return
            
            try:
                res_org = supabase.table('organizations').select('sape_balance, sapp_balance, saiv_balance').eq('id', org_id).single().execute()
                
                if tipo == 'SAPE':
                    nuevas = res_org.data.get('sape_balance', 0) + cantidad
                    supabase.table('organizations').update({'sape_balance': nuevas}).eq('id', org_id).execute()
                elif tipo == 'SAPP':
                    nuevas = res_org.data.get('sapp_balance', 0) + cantidad
                    supabase.table('organizations').update({'sapp_balance': nuevas}).eq('id', org_id).execute()
                else:
                    nuevas = res_org.data.get('saiv_balance', 0) + cantidad
                    supabase.table('organizations').update({'saiv_balance': nuevas}).eq('id', org_id).execute()
                
                supabase.table('action_logs').insert({
                    'org_id': org_id, 'action_type': 'BILLING_PURCHASE_MANUAL', 'target_user': f'+{cantidad} {tipo}', 
                    'performed_by': 'SUPER_ADMIN', 'status_color': 'green'
                }).execute()

                ui.notify(f"✅ {cantidad} licencias de {tipo} asignadas.", type='positive')
                self.render() 
                
            except Exception as ex:
                ui.notify(f"Error asignando licencias: {ex}", type='negative')

        with ui.column().classes('w-full gap-8 items-start'):
            with ui.row().classes('w-full gap-8 mt-4'):
                with ui.column().classes('w-full bg-[#0E1117] p-8 rounded-2xl border border-gray-800'):
                    ui.label('Inyección Directa de Licencias').classes('text-xl text-[#83ABF1] font-bold mb-6')
                    
                    select_org = ui.select(lista_orgs, label='1. Selecciona Organización', on_change=lambda e: estado.update({'org_seleccionada': e.value})).classes('w-full mb-6').props('dark filled color="blue"')
                    select_tipo = ui.select(['SAPE', 'SAPP', 'SAIV'], label='2. Tipo de Licencia', value='SAPE', on_change=lambda e: estado.update({'tipo_test': e.value})).classes('w-full mb-6').props('dark filled color="blue"')
                    input_cantidad = ui.number(label='3. Volumen (1 SAPE/SAPP = 3 usos. 1 SAIV = 1 uso)', value=0, min=0, on_change=lambda e: estado.update({'cantidad': int(e.value or 0)})).classes('w-full text-xl').props('dark filled color="blue"')

                    btn_asignar = ui.button('EJECUTAR INYECCIÓN', on_click=procesar_asignacion_manual).classes('w-full bg-[#22C55E] text-[#0E1117] font-bold mt-8 py-4 rounded-xl shadow-lg hover:scale-105')

    # ==========================================
    # CARGA MASIVA DIRIGIDA Y CREACIÓN MANUAL (CON GATEKEEPER 3 CAJONES)
    # ==========================================
    def descargar_plantilla(self):
        df = pd.DataFrame({
            "username": ["usuario_ejemplo_01", "usuario_ejemplo_02"],
            "password": ["ClaveSegura1*", "ClaveSegura2*"],
            "tests": ["SAPE", "SAPE, SAIV"], 
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
            ui.notify('Selecciona primero una organización en el desplegable', type='warning')
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
                ui.notify('Faltan columnas requeridas (username, password, tests)', type='negative')
                return

            # --- GATEKEEPER DE LOS 3 CAJONES ---
            res_org = supabase.table('organizations').select('name, privileges, sape_balance, sapp_balance, saiv_balance').eq('id', org_id).single().execute()
            if not res_org.data: return
                
            org_data = res_org.data
            org_nombre = org_data.get('name', org_id)
            privileges = org_data.get('privileges', {})

            sape_actual = org_data.get('sape_balance', 0)
            sapp_actual = org_data.get('sapp_balance', 0)
            saiv_actual = org_data.get('saiv_balance', 0)

            # Contar la demanda del archivo
            req_sape = sum(1 for _, r in df.iterrows() if any(x in str(r['tests']).upper() for x in ["SAPE", "AMBAS", "TODAS"]))
            req_sapp = sum(1 for _, r in df.iterrows() if any(x in str(r['tests']).upper() for x in ["SAPP", "AMBAS", "TODAS"]))
            req_saiv = sum(1 for _, r in df.iterrows() if any(x in str(r['tests']).upper() for x in ["SAIV", "TODAS"]))
            
            if req_sape > sape_actual or req_sapp > sapp_actual or req_saiv > saiv_actual:
                ui.notify(f'⚠️ Saldo insuficiente en la organización {org_nombre}. Demanda: SAPE({req_sape}), SAPP({req_sapp}), SAIV({req_saiv}). Stock: SAPE({sape_actual}), SAPP({sapp_actual}), SAIV({saiv_actual}).', type='warning', timeout=10000)
                return

            count_usuarios = 0

            for _, row in df.iterrows():
                tests = str(row['tests']).upper()
                sape_active = any(x in tests for x in ["SAPE", "AMBAS", "TODAS"])
                sapp_active = any(x in tests for x in ["SAPP", "AMBAS", "TODAS"])
                saiv_active = any(x in tests for x in ["SAIV", "TODAS"])

                # Validar permisos
                if saiv_active and not privileges.get('can_assign_saiv', False): saiv_active = False

                # Regla 1:3 y 1:1
                profile_data = {
                    "sape": {
                        "attempts": 3 if sape_active else 0,
                        "sectors": [s.strip() for s in str(row.get('sape_sectors', '')).split(',')] if pd.notna(row.get('sape_sectors')) else []
                    },
                    "sapp": {
                        "attempts": 3 if sapp_active else 0,
                        "profile": str(row.get('sapp_profile', '')).strip(),
                        "groups": [g.strip() for g in str(row.get('sapp_groups', '')).split(',')] if pd.notna(row.get('sapp_groups')) else []
                    },
                    "saiv": {
                        "attempts": 1 if saiv_active else 0
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
                count_usuarios += 1
                
            # Restamos de los tres cajones
            supabase.table('organizations').update({
                'sape_balance': sape_actual - req_sape,
                'sapp_balance': sapp_actual - req_sapp,
                'saiv_balance': saiv_actual - req_saiv
            }).eq('id', org_id).execute()

            # Logs
            supabase.table('action_logs').insert({
                'org_id': org_id, 'action_type': 'REGISTER_BULK', 'target_user': f'{count_usuarios} usuarios creados', 
                'performed_by': 'SUPER_ADMIN', 'status_color': 'green-blue'
            }).execute()
            
            supabase.table('action_logs').insert({
                'org_id': org_id, 'action_type': 'LICENSE_CONSUMED', 'target_user': f'-{req_sape}S -{req_sapp}P -{req_saiv}V', 
                'performed_by': 'SUPER_ADMIN', 'status_color': 'green-yellow', 'metadata': {'motivo': 'Carga Masiva Admin'}
            }).execute()

            ui.notify(f'Éxito: {count_usuarios} usuarios importados. Saldo actualizado.', type='positive', timeout=8000)
            self.render()

        except Exception as ex:
            ui.notify(f'Error procesando Excel: {ex}', type='negative')

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

            with ui.tabs().classes('w-full bg-[#161B22] text-[#83ABF1] rounded-t-2xl font-bold') as tabs:
                t_orgs = ui.tab('ORGANIZACIONES', icon='domain')
                t_billing = ui.tab('INYECCIÓN DE SALDO', icon='point_of_sale')
                t_users = ui.tab('USUARIOS GLOBALES', icon='people')
                t_stats = ui.tab('ESTADÍSTICAS Y LOGS', icon='analytics')

            with ui.tab_panels(tabs, value=t_orgs).classes('w-full bg-[#161B22] border border-gray-800 rounded-b-2xl shadow-2xl p-0'):
                
                # PANEL 1: ORGANIZACIONES
                with ui.tab_panel(t_orgs).classes('p-8'):
                    with ui.row().classes('w-full gap-8 items-start'):
                        
                        # --- FORMULARIO DE ALTA/EDICIÓN (CON LOS 3 CAJONES) ---
                        with ui.column().classes('w-1/3 min-w-[450px]'):
                            with ui.column().classes('w-full bg-[#0E1117] p-8 rounded-2xl border border-gray-800 mb-6'):
                                ui.label('Configuración Operativa').classes('text-lg text-[#83ABF1] font-bold mb-4 border-b border-gray-800 pb-2 w-full')
                                
                                inputs = {
                                    'nom': ui.input('Nombre Comercial').classes('w-full mb-2').props('dark outlined'),
                                    'pwd': ui.input('Clave Maestra').classes('w-full mb-4').props('dark outlined'),
                                    
                                    # LOS TRES CAJONES DE SALDO INICIAL
                                    'sape_balance': ui.number('Stock Inicial SAPE (1 Lic = 3 usos)', value=0, min=0).classes('w-full mb-2 font-bold text-blue-300').props('dark outlined'),
                                    'sapp_balance': ui.number('Stock Inicial SAPP (1 Lic = 3 usos)', value=0, min=0).classes('w-full mb-2 font-bold text-green-300').props('dark outlined'),
                                    'saiv_balance': ui.number('Stock Inicial SAIV (1 Lic = 1 uso)', value=0, min=0).classes('w-full mb-6 font-bold text-purple-300').props('dark outlined'),
                                    
                                    'demo': ui.checkbox('Cuenta DEMO (Pruebas al 10%)').classes('text-white mb-2 w-full'),
                                    'pin': ui.input('PIN de Compras B2B').classes('w-full mb-2').props('dark outlined'),
                                    
                                    'razon_social': ui.input('Razón Social (Para Factura)').classes('w-full mt-4 mb-2').props('dark outlined'),
                                    'cif': ui.input('CIF / NIF').classes('w-full mb-2').props('dark outlined'),
                                    'direccion': ui.input('Dirección Fiscal').classes('w-full mb-2').props('dark outlined'),
                                    'cp': ui.input('Código Postal').classes('w-1/2 inline-block pr-1 mb-4').props('dark outlined'),
                                    'ciudad': ui.input('Ciudad').classes('w-1/2 inline-block pl-1 mb-4').props('dark outlined'),
                                    
                                    'p_usr': ui.checkbox('Puede crear/editar usuarios').classes('text-white mt-4'),
                                    'p_stat': ui.checkbox('Ver estadísticas de su organización').classes('text-white'),
                                    'p_comp': ui.checkbox('Ver comparativas anónimas sectoriales').classes('text-white mb-4'),
                                    
                                    'p_sape': ui.checkbox('Habilitar asignación de SAPE').classes('text-[#83ABF1] font-bold mt-2'),
                                    'p_sape_sectores': ui.select(SECTORES_SAPE, multiple=True, label='Sectores SAPE Permitidos').classes('w-full mb-4 ml-4').props('dark outlined use-chips'),
                                    
                                    'p_sapp': ui.checkbox('Habilitar asignación de SAPP').classes('text-green-400 font-bold mt-2'),
                                    'p_sapp_perfiles': ui.select(PERFILES_SAPP, multiple=True, label='Sectores SAPP Permitidos').classes('w-full mb-2 ml-4').props('dark outlined use-chips'),
                                    'p_sapp_comp': ui.select(COMPETENCIAS_SAPP, multiple=True, label='Competencias SAPP Permitidas').classes('w-full mb-4 ml-4').props('dark outlined use-chips'),
                                    
                                    'p_saiv': ui.checkbox('Habilitar Módulo SAIV (Prueba Completa)').classes('text-purple-400 font-bold border-t border-gray-800 pt-4 w-full')
                                }
                                
                                inputs['p_sape_sectores'].bind_visibility_from(inputs['p_sape'], 'value')
                                inputs['p_sapp_perfiles'].bind_visibility_from(inputs['p_sapp'], 'value')
                                inputs['p_sapp_comp'].bind_visibility_from(inputs['p_sapp'], 'value')

                            with ui.column().classes('w-full p-6 border border-[#83ABF1]/30 rounded-xl bg-[#161B22] shadow-lg'):
                                ui.label('CREDENCIALES DEL ADMINISTRADOR CLIENTE').classes('text-[#83ABF1] text-xs font-black tracking-widest mb-1')
                                inputs['admin_user'] = ui.input('Usuario Admin').props('dark outlined').classes('w-full mb-3')
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
                                            with ui.column().classes('gap-1 w-2/3'):
                                                with ui.row().classes('items-center gap-2'):
                                                    ui.label(o['name'].upper()).classes('text-white font-bold text-lg')
                                                    if o.get('privileges', {}).get('can_assign_saiv', False):
                                                        ui.badge('SAIV', color='purple').classes('ml-2')
                                                
                                                # Mostrar los tres saldos
                                                with ui.row().classes('gap-4 mt-1'):
                                                    ui.label(f"SAPE: {o.get('sape_balance',0)}").classes('text-blue-400 font-bold text-xs bg-blue-900/30 px-2 py-1 rounded')
                                                    ui.label(f"SAPP: {o.get('sapp_balance',0)}").classes('text-green-400 font-bold text-xs bg-green-900/30 px-2 py-1 rounded')
                                                    ui.label(f"SAIV: {o.get('saiv_balance',0)}").classes('text-purple-400 font-bold text-xs bg-purple-900/30 px-2 py-1 rounded')
                                            
                                            with ui.row().classes('gap-2 w-1/3 justify-end'):
                                                ui.button(icon='edit', on_click=lambda o=o: self.preparar_edicion(o, inputs)).props('flat round color=blue')
                            except Exception as e:
                                ui.label(f"Error cargando base de datos: {e}").classes('text-red-500')

                with ui.tab_panel(t_billing).classes('p-8'):
                    self.render_billing_panel()

                with ui.tab_panel(t_users).classes('p-8'):
                    with ui.row().classes('w-full gap-8 items-start'):
                        with ui.column().classes('w-1/3 bg-[#0E1117] p-6 rounded-xl border border-gray-800'):
                            ui.label('Carga Masiva Dirigida').classes('text-xl text-[#83ABF1] font-bold mb-4')
                            try:
                                orgs = supabase.table('organizations').select('id, name').order('name').execute().data
                                org_options = {o['id']: o['name'] for o in orgs} if orgs else {}
                            except: org_options = {}

                            target_org = ui.select(org_options, label='Selecciona Organización').classes('w-full mb-6').props('dark outlined')
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
                                        {'name': 'created_at', 'label': 'Fecha Alta', 'field': 'created_at', 'align': 'right'}
                                    ]
                                    for row in usr_data: row['created_at'] = row['created_at'][:10]
                                    ui.table(columns=cols_usr, rows=usr_data, row_key='username').classes('w-full bg-[#161B22] text-white')
                            except Exception as e: ui.label(f'Error: {e}')

                with ui.tab_panel(t_stats).classes('p-8'):
                    ui.label('Monitor de Actividad B2B').classes('text-xl text-[#83ABF1] font-bold mb-6')
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
                        except Exception: pass