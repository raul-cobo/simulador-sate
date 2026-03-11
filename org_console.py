import os
import pandas as pd
import io
import json
from datetime import datetime
from nicegui import ui, app
from supabase import create_client, Client
from dotenv import load_dotenv
import pdf_generator
import pdf_generator_saiv 

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

SECTORES_OFICIALES = ['TECH', 'CONSULTORIA', 'HOSTELERIA', 'INTRA', 'AUTOEMPLEO', 'PYME', 'SALUD', 'SOCIAL']
PERFILES_SAPP = ['Organizacional', 'Educativo', 'Social', 'Sanitario']

def descargar_informe_desde_consola(row_data):
    ev_data = row_data.get('raw_data', {})
    test_type = ev_data.get('test_type', 'SAPE')
    
    user_info = {
        'user_id': ev_data.get('user_id', 'N/A'),
        'username': 'Candidato Evaluación'
    }
    
    try:
        ui.notify(f"Generando informe {test_type}...", color="info")
        
        # Enrutamiento según el tipo de test
        if test_type == 'SAIV':
            results = ev_data.get('refined_metrics', {})
            ruta_pdf = pdf_generator_saiv.generar_informe_saiv(user_info, results)
        else:
            if test_type == 'SAPP':
                results = ev_data.get('refined_metrics', ev_data.get('results', {}))
            else:
                results = ev_data.get('results', ev_data.get('calculated_scores', {}))
            ruta_pdf = pdf_generator.generar_informe(user_info, results, test_type=test_type)
            
        ui.download(ruta_pdf)
    except Exception as e:
        ui.notify(f"Error generando PDF: {e}", color="negative")

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
        self.qr_events_data = [] 
        self.editing_user = None
        self.dialogo_checkout = None

    def cargar_datos(self):
        if not supabase or not self.org_id: return
        try:
            res_org = supabase.table('organizations').select('*').eq('id', self.org_id).execute()
            if res_org.data: 
                self.org_data = res_org.data[0]
                self.privilegios = self.org_data.get('privileges', {}) or {}

            res_usr = supabase.table('users').select('*').eq('org_id', self.org_id).order('created_at', desc=True).execute()
            if res_usr.data: self.users_data = res_usr.data

            res_eval = supabase.table('evaluations').select('*').eq('org_id', self.org_id).execute()
            if res_eval.data: self.evals_data = res_eval.data
            
            res_logs = supabase.table('action_logs').select('*').eq('org_id', self.org_id).order('created_at', desc=True).limit(50).execute()
            if res_logs.data: self.logs_data = res_logs.data
            
            res_qr = supabase.table('qr_events').select('*').eq('org_id', self.org_id).order('created_at', desc=True).execute()
            if res_qr.data: self.qr_events_data = res_qr.data
            
        except Exception as e:
            ui.notify(f"Error cargando datos: {e}", type='negative')

    def registrar_log(self, action_type, target_user, color, error_msg=""):
        if not supabase: return
        try:
            supabase.table('action_logs').insert({
                'org_id': self.org_id,
                'action_type': action_type,
                'target_user': target_user,
                'performed_by': self.username,
                'status_color': color,
                'metadata': {'error': error_msg} if error_msg else {}
            }).execute()
        except: pass

    def cerrar_sesion(self):
        app.storage.user.clear()
        ui.navigate.to('/')

    # ==========================================
    # NUEVO: PANEL DE EVENTOS QR (Con 3 Cajones)
    # ==========================================
    def render_panel_qr(self):
        # Leemos los tres saldos
        sape_bal = self.org_data.get('sape_balance', 0)
        sapp_bal = self.org_data.get('sapp_balance', 0)
        saiv_bal = self.org_data.get('saiv_balance', 0)
        
        opciones_pruebas = []
        if self.privilegios.get('can_assign_sape'): opciones_pruebas.append('SAPE')
        if self.privilegios.get('can_assign_sapp'): opciones_pruebas.append('SAPP')
        if self.privilegios.get('can_assign_saiv'): opciones_pruebas.append('SAIV')

        if not opciones_pruebas:
            with ui.column().classes('w-full items-center justify-center p-12 bg-[#0E1117] rounded-xl border border-gray-800'):
                ui.icon('block', size='4rem', color='gray')
                ui.label('No tienes pruebas habilitadas para generar eventos masivos.').classes('text-gray-400 font-bold mt-4')
            return

        with ui.row().classes('w-full gap-8 items-start'):
            
            with ui.column().classes('w-1/3 min-w-[350px] bg-[#0E1117] p-6 rounded-2xl border border-gray-800'):
                ui.label('Generar Nuevo Evento Masivo').classes('text-xl text-[#83ABF1] font-bold mb-4')
                ui.label('Crea un enlace y código QR para que tus alumnos se registren al instante desde su móvil.').classes('text-sm text-gray-400 mb-6')
                
                inputs_qr = {
                    'nombre': ui.input('Nombre de la sesión (Ej: Clase 1B)').classes('w-full mb-4').props('dark outlined'),
                    'tipo_test': ui.select(opciones_pruebas, label='Prueba a realizar', value=opciones_pruebas[0]).classes('w-full mb-4').props('dark outlined'),
                    'plazas': ui.number('Plazas Reservadas (Máx. alumnos)', value=10, min=1).classes('w-full mb-6').props('dark outlined')
                }

                def crear_evento():
                    plazas = int(inputs_qr['plazas'].value)
                    tipo = inputs_qr['tipo_test'].value
                    
                    if not inputs_qr['nombre'].value:
                        ui.notify('Debes ponerle un nombre al evento', type='warning')
                        return
                    
                    # Verificamos si hay saldo en el cajón correspondiente
                    if tipo == 'SAPE' and plazas > sape_bal:
                        ui.notify(f'No tienes licencias suficientes. Saldo SAPE: {sape_bal}', type='negative')
                        return
                    if tipo == 'SAPP' and plazas > sapp_bal:
                        ui.notify(f'No tienes licencias suficientes. Saldo SAPP: {sapp_bal}', type='negative')
                        return
                    if tipo == 'SAIV' and plazas > saiv_bal:
                        ui.notify(f'No tienes licencias suficientes. Saldo SAIV: {saiv_bal}', type='negative')
                        return
                         
                    try:
                        supabase.table('qr_events').insert({
                            'org_id': self.org_id,
                            'event_name': inputs_qr['nombre'].value.strip(),
                            'test_type': tipo,
                            'max_slots': plazas,
                            'used_slots': 0,
                            'is_active': True
                        }).execute()
                        
                        self.registrar_log('QR_EVENT_CREATED', f"{inputs_qr['nombre'].value} ({plazas} plazas)", 'blue')
                        ui.notify('Evento creado correctamente.', type='positive')
                        self.render() 
                    except Exception as e:
                        ui.notify(f'Error creando evento: {e}', type='negative')

                ui.button('CREAR ACCESO QR', on_click=crear_evento).classes('w-full bg-[#83ABF1] text-black font-bold py-3 shadow-lg')

            with ui.column().classes('flex-1'):
                if not self.qr_events_data:
                    with ui.column().classes('w-full p-10 items-center border border-dashed border-gray-700 rounded-xl'):
                        ui.label('Aún no has creado ningún evento masivo.').classes('text-gray-500 italic')
                else:
                    for evento in self.qr_events_data:
                        is_active = evento['is_active']
                        bg_card = "bg-[#161B22] border-[#83ABF1]" if is_active else "bg-[#0A0C10] border-gray-800 opacity-70"
                        
                        with ui.card().classes(f'w-full flex-row items-center justify-between p-6 mb-4 rounded-xl border {bg_card} shadow-xl'):
                            with ui.column().classes('gap-1 w-1/3'):
                                ui.label(evento['event_name']).classes('text-lg font-black text-white')
                                ui.label(f"Prueba: {evento['test_type']}").classes('text-[#83ABF1] font-bold text-sm')
                                ui.label(f"Fecha: {evento['created_at'][:10]}").classes('text-gray-500 text-xs')
                            
                            with ui.column().classes('items-center gap-2 w-1/3'):
                                progreso = evento['used_slots'] / evento['max_slots'] if evento['max_slots'] > 0 else 0
                                color_progreso = "green" if progreso < 0.8 else "orange" if progreso < 1 else "red"
                                
                                ui.label(f"{evento['used_slots']} / {evento['max_slots']} Plazas Usadas").classes('text-white font-bold font-mono')
                                ui.linear_progress(value=progreso, show_value=False).props(f'color="{color_progreso}"').classes('w-full h-3 rounded-full')
                            
                            with ui.column().classes('items-end gap-2 w-1/3'):
                                if is_active:
                                    url_registro = f"https://tu-dominio.com/join/{evento['id']}"
                                    with ui.row().classes('gap-2'):
                                        ui.button('VER QR', icon='qr_code', on_click=lambda url=url_registro: self.mostrar_qr_grande(url)).props('outline color=white')
                                        ui.button('COPIAR LINK', icon='content_copy', on_click=lambda url=url_registro: ui.run_javascript(f'navigator.clipboard.writeText("{url}")')).props('flat color=blue')
                                    
                                    ui.button('CERRAR ACCESO', icon='block', on_click=lambda e_id=evento['id']: self.toggle_evento(e_id, False)).classes('bg-red-900/50 text-red-400 font-bold mt-2 shadow-none hover:bg-red-800')
                                else:
                                    ui.label('FINALIZADO').classes('text-red-500 font-bold tracking-widest border border-red-500 px-4 py-1 rounded')
                                    ui.button('REABRIR', icon='restart_alt', on_click=lambda e_id=evento['id']: self.toggle_evento(e_id, True)).props('flat color=gray').classes('mt-2')

    def mostrar_qr_grande(self, url):
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={url}"
        
        with ui.dialog() as dialog, ui.card().classes('p-8 bg-white items-center rounded-2xl'):
            ui.label('ESCANEA PARA ACCEDER').classes('text-2xl font-black text-black tracking-widest mb-4')
            ui.image(qr_url).classes('w-64 h-64 border-4 border-black p-2 rounded')
            ui.label(url).classes('text-blue-600 font-mono text-xs mt-4 mb-4 select-all')
            ui.button('CERRAR', on_click=dialog.close).classes('bg-black text-white font-bold w-full')
        dialog.open()

    def toggle_evento(self, event_id, nuevo_estado):
        try:
            supabase.table('qr_events').update({'is_active': nuevo_estado}).eq('id', event_id).execute()
            estado_txt = "Abierto" if nuevo_estado else "Cerrado"
            self.registrar_log('QR_EVENT_TOGGLED', f"ID: {str(event_id)[:8]} -> {estado_txt}", 'yellow')
            ui.notify(f'Evento marcado como {estado_txt}', type='info')
            self.render()
        except Exception as e:
            ui.notify(f'Error al cambiar estado: {e}', type='negative')


    # ==========================================
    # GESTIÓN INDIVIDUAL DE USUARIOS
    # ==========================================
    def limpiar_formulario(self, inputs):
        self.editing_user = None
        inputs['u_nom'].value = ""
        inputs['u_pwd'].value = ""
        inputs['u_sectores'].value = []
        inputs['u_perfil'].value = []
        ui.notify("Formulario en modo CREACIÓN", type="info")

    def preparar_edicion_usuario(self, user, inputs):
        self.editing_user = user['username']
        inputs['u_nom'].value = user['username']
        inputs['u_pwd'].value = user['password']
        
        p_data = user.get('profile_data', {})
        sape_data = p_data.get('sape', {})
        sapp_data = p_data.get('sapp', {})
        saiv_data = p_data.get('saiv', {})
        
        asignados = []
        if sape_data.get('attempts', 0) > 0: asignados.append("SAPE")
        if sapp_data.get('attempts', 0) > 0: asignados.append("SAPP")
        if saiv_data.get('attempts', 0) > 0: asignados.append("SAIV")
        
        if "SAPE" in asignados and "SAPP" in asignados: inputs['u_tests'].value = "AMBAS"
        elif asignados: inputs['u_tests'].value = asignados[0]
        else: inputs['u_tests'].value = "SAPE" 
        
        inputs['u_sectores'].value = sape_data.get('sectors', [])
        
        perfil_guardado = sapp_data.get('profile', '')
        inputs['u_perfil'].value = [p.strip() for p in perfil_guardado.split(',') if p.strip()] if perfil_guardado else []
        
        ui.notify(f"Modo EDICIÓN: {user['username']}", type='info')

    def guardar_usuario_manual(self, inputs):
        if not inputs['u_nom'].value or not inputs['u_pwd'].value:
            ui.notify('Usuario y Contraseña requeridos', type='warning')
            return

        test_val = inputs['u_tests'].value
        if test_val == 'NINGUNA':
            ui.notify('Error: No puedes crear usuarios sin licencias de pruebas asignadas.', type='negative')
            return

        sape_active = test_val in ["SAPE", "AMBAS"]
        sapp_active = test_val in ["SAPP", "AMBAS"]
        saiv_active = test_val == "SAIV"

        sectores_seleccionados = inputs['u_sectores'].value if inputs['u_sectores'].value else []
        perfiles_seleccionados = inputs['u_perfil'].value if inputs['u_perfil'].value else []

        # REGLA DE NEGOCIO: 3 Intentos para Evolutivas, 1 Intento para SAIV
        profile_data = {
            "sape_attempts_allowed": 3 if sape_active else 0,
            "sapp_attempts_allowed": 3 if sapp_active else 0,
            "sape": {
                "attempts": 3 if sape_active else 0,
                "sectors": sectores_seleccionados
            },
            "sapp": {
                "attempts": 3 if sapp_active else 0,
                "profile": ", ".join(perfiles_seleccionados),
                "groups": [] 
            },
            "saiv": {
                "attempts": 1 if saiv_active else 0
            }
        }

        username_limpio = inputs['u_nom'].value.strip()

        payload = {
            "username": username_limpio,
            "password": inputs['u_pwd'].value.strip(),
            "org_id": self.org_id,
            "role": "USER",
            "is_deleted": False,
            "profile_data": profile_data,
            "intentos_disponibles": 3 if (sape_active or sapp_active) else 1, 
            "max_intentos": 3 if (sape_active or sapp_active) else 1
        }

        try:
            if getattr(self, 'editing_user', None):
                supabase.table('users').update(payload).eq('username', self.editing_user).execute()
                self.registrar_log('EDIT_USER', payload['username'], 'green-yellow')
                ui.notify('Usuario actualizado correctamente', type='positive')
                self.limpiar_formulario(inputs)
            else:
                # COMPROBACIÓN DE CAJONES
                bal_sape = self.org_data.get('sape_balance', 0)
                bal_sapp = self.org_data.get('sapp_balance', 0)
                bal_saiv = self.org_data.get('saiv_balance', 0)
                
                if sape_active and bal_sape <= 0:
                    ui.notify('❌ Saldo de licencias SAPE insuficiente.', type='negative')
                    return
                if sapp_active and bal_sapp <= 0:
                    ui.notify('❌ Saldo de licencias SAPP insuficiente.', type='negative')
                    return
                if saiv_active and bal_saiv <= 0:
                    ui.notify('❌ Saldo de licencias SAIV insuficiente.', type='negative')
                    return

                res_insert = supabase.table('users').insert(payload).execute()
                
                # DESCUENTO DE CAJONES
                update_payload = {}
                if sape_active: update_payload['sape_balance'] = bal_sape - 1
                if sapp_active: update_payload['sapp_balance'] = bal_sapp - 1
                if saiv_active: update_payload['saiv_balance'] = bal_saiv - 1

                if update_payload:
                    supabase.table('organizations').update(update_payload).eq('id', self.org_id).execute()
                    self.org_data.update(update_payload)
                    self.registrar_log('LICENSE_CONSUMED', payload['username'], 'green-yellow', 'Creación Manual')

                self.registrar_log('NEW_USER', payload['username'], 'green-blue')
                ui.notify('Usuario creado con éxito', type='positive')
                self.limpiar_formulario(inputs) 
            
            self.render()
        except Exception as e:
            err_str = str(e)
            if "duplicate key value" in err_str.lower():
                ui.notify(f'El usuario "{username_limpio}" ya existe. Elige otro nombre.', type='negative')
            else:
                self.registrar_log('ERROR', payload['username'], 'yellow-red', err_str)
                ui.notify(f'Error de base de datos: {err_str}', type='negative')

    def eliminar_usuario(self, username):
        try:
            supabase.table('users').update({'is_deleted': True}).eq('username', username).execute()
            self.registrar_log('DELETE_USER', username, 'red')
            ui.notify(f'Usuario {username} eliminado', type='positive')
            self.render()
        except Exception as e:
            ui.notify(f'Error al eliminar: {e}', type='negative')

    # ==========================================
    # CARGA MASIVA Y PLANTILLAS
    # ==========================================
    def descargar_plantilla_org(self):
        df = pd.DataFrame({
            "username": ["usuario_01", "usuario_02"],
            "password": ["Pass123*", "Pass456*"],
            "tests": ["SAPE", "SAIV"],
            "sape_sectors": ["TECH, SOCIAL", ""],
            "sapp_profile": ["", "Sanitario, Educativo"],
            "sapp_groups": ["", "competencias personales, técnicas"]
        })
        file_path = f"Plantilla_Carga_{self.org_id}.xlsx"
        df.to_excel(file_path, index=False)
        ui.download(file_path)
        ui.notify('Plantilla corporativa descargada', type='positive')

    async def procesar_carga_masiva(self, e):
        ui.notify('Procesando archivo masivo...', type='info')
        try:
            content = io.BytesIO(e.content.read())
            df = pd.read_excel(content) if e.name.endswith('.xlsx') else pd.read_csv(content, sep=None, engine='python')
            df.columns = df.columns.str.lower().str.strip()
            
            req = ['username', 'password', 'tests']
            if not all(col in df.columns for col in req):
                raise ValueError("Faltan columnas requeridas (username, password, tests)")

            bal_sape = self.org_data.get('sape_balance', 0)
            bal_sapp = self.org_data.get('sapp_balance', 0)
            bal_saiv = self.org_data.get('saiv_balance', 0)
            can_assign_saiv = self.privilegios.get('can_assign_saiv', False)

            # Contar licencias requeridas por test
            req_sape = sum(1 for _, r in df.iterrows() if any(x in str(r['tests']).upper() for x in ["SAPE", "AMBAS", "TODAS"]))
            req_sapp = sum(1 for _, r in df.iterrows() if any(x in str(r['tests']).upper() for x in ["SAPP", "AMBAS", "TODAS"]))
            req_saiv = sum(1 for _, r in df.iterrows() if any(x in str(r['tests']).upper() for x in ["SAIV", "TODAS"]))

            if req_sape > bal_sape or req_sapp > bal_sapp or req_saiv > bal_saiv:
                ui.notify(f'❌ Saldo insuficiente. Requerido: {req_sape} SAPE, {req_sapp} SAPP, {req_saiv} SAIV. Disponible: {bal_sape} SAPE, {bal_sapp} SAPP, {bal_saiv} SAIV.', type='negative', timeout=10000)
                return

            count_creados = 0
            errores = 0
            
            for _, row in df.iterrows():
                tests = str(row['tests']).upper()
                sape_active = any(x in tests for x in ["SAPE", "AMBAS", "TODAS"])
                sapp_active = any(x in tests for x in ["SAPP", "AMBAS", "TODAS"])
                saiv_active = any(x in tests for x in ["SAIV", "TODAS"])
                
                if saiv_active and not can_assign_saiv:
                    saiv_active = False

                profile_data = {
                    "sape": {
                        "attempts": 3 if sape_active else 0,
                        "sectors": [s.strip().upper() for s in str(row.get('sape_sectors', '')).split(',')] if pd.notna(row.get('sape_sectors')) else []
                    },
                    "sapp": {
                        "attempts": 3 if sapp_active else 0,
                        "profile": str(row.get('sapp_profile', '')).strip().title(),
                        "groups": [g.strip() for g in str(row.get('sapp_groups', '')).split(',')] if pd.notna(row.get('sapp_groups')) else []
                    },
                    "saiv": {
                        "attempts": 1 if saiv_active else 0
                    }
                }

                payload = {
                    "username": str(row['username']).strip(),
                    "password": str(row['password']).strip(),
                    "org_id": self.org_id, 
                    "role": "USER",
                    "is_deleted": False,
                    "profile_data": profile_data,
                    "intentos_disponibles": 3 if (sape_active or sapp_active) else 1,
                    "max_intentos": 3 if (sape_active or sapp_active) else 1
                }
                
                try:
                    existente = supabase.table("users").select("id").eq("username", payload["username"]).execute()
                    if existente.data:
                        supabase.table("users").update(payload).eq("username", payload["username"]).execute()
                    else:
                        supabase.table("users").insert(payload).execute()
                        count_creados += 1
                except Exception as ex_u:
                    print(f"Error insertando {payload['username']}: {ex_u}")
                    errores += 1

            # Descontar los tres cajones a la vez
            nuevo_sape = bal_sape - req_sape
            nuevo_sapp = bal_sapp - req_sapp
            nuevo_saiv = bal_saiv - req_saiv

            supabase.table('organizations').update({
                'sape_balance': nuevo_sape,
                'sapp_balance': nuevo_sapp,
                'saiv_balance': nuevo_saiv
            }).eq('id', self.org_id).execute()
            
            self.org_data['sape_balance'] = nuevo_sape
            self.org_data['sapp_balance'] = nuevo_sapp
            self.org_data['saiv_balance'] = nuevo_saiv
            
            self.registrar_log('LICENSE_CONSUMED', f'Carga Masiva: -{req_sape}S -{req_sapp}P -{req_saiv}V', 'green-yellow')
            self.registrar_log('BULK_UPLOAD', f'{count_creados} creados', 'green-blue')

            ui.notify(f'Proceso finalizado: {count_creados} creados.', type='positive' if errores==0 else 'warning')
            self.render()

        except Exception as ex:
            self.registrar_log('ERROR_BULK', 'Archivo', 'yellow-red', str(ex))
            ui.notify(f'Error procesando el archivo: {ex}', type='negative')


    # ==========================================
    # TIENDA Y FACTURACIÓN B2B (PROFORMAS)
    # ==========================================
    def abrir_checkout(self, cantidad_str, precio_unitario, plan_nombre):
        try:
            cantidad = int(cantidad_str)
        except ValueError:
            ui.notify("Introduce una cantidad válida.", type="warning")
            return

        if cantidad <= 0:
            ui.notify("La cantidad debe ser mayor a 0.", type="warning")
            return

        subtotal = cantidad * precio_unitario
        iva = subtotal * 0.21
        total = subtotal + iva

        if self.dialogo_checkout:
            self.dialogo_checkout.clear()
        
        with ui.dialog() as self.dialogo_checkout, ui.card().classes('p-8 bg-[#161B22] border border-[#83ABF1] shadow-2xl rounded-2xl w-[500px]'):
            ui.label('RESUMEN DE PEDIDO').classes('text-xl font-black text-[#83ABF1] tracking-widest mb-6 border-b border-gray-800 pb-2 w-full')
            
            with ui.column().classes('w-full gap-2 mb-6'):
                with ui.row().classes('w-full justify-between'):
                    ui.label(f'Plan seleccionado:').classes('text-gray-400')
                    ui.label(f'{plan_nombre}').classes('text-white font-bold')
                with ui.row().classes('w-full justify-between'):
                    ui.label(f'Licencias solicitadas:').classes('text-gray-400')
                    ui.label(f'{cantidad} uds.').classes('text-white font-bold')
                with ui.row().classes('w-full justify-between'):
                    ui.label(f'Precio unitario:').classes('text-gray-400')
                    ui.label(f'{precio_unitario:.2f} €').classes('text-white font-bold')
                
                ui.separator().classes('bg-gray-800 my-2')
                
                with ui.row().classes('w-full justify-between'):
                    ui.label('Base Imponible:').classes('text-gray-400')
                    ui.label(f'{subtotal:.2f} €').classes('text-white font-mono')
                with ui.row().classes('w-full justify-between'):
                    ui.label('I.V.A. (21%):').classes('text-gray-400')
                    ui.label(f'{iva:.2f} €').classes('text-white font-mono')
                
                with ui.row().classes('w-full justify-between items-end mt-4 pt-2 border-t border-gray-800'):
                    ui.label('TOTAL A FACTURAR:').classes('text-gray-300 font-bold')
                    ui.label(f'{total:.2f} €').classes('text-3xl text-[#22C55E] font-black font-mono')

            check_legal = ui.checkbox('Acepto los Términos de Contratación y el tratamiento de datos según el RGPD.').classes('text-xs text-gray-500 mb-6')
            
            ui.label('Autorización de Compra').classes('text-sm text-[#83ABF1] font-bold mb-2')
            pin_input = ui.input('Introduce tu PIN de Seguridad', password=True).props('dark outlined').classes('w-full mb-6')

            def procesar_compra_final():
                if not check_legal.value:
                    ui.notify('Debes aceptar los términos legales.', type='warning')
                    return
                
                pin_real = self.org_data.get('pin_seguridad', '1234')
                if pin_input.value != pin_real:
                    ui.notify('PIN incorrecto. Operación denegada.', type='negative')
                    self.registrar_log('SECURITY_ALERT', 'Intento de compra con PIN erróneo', 'red')
                    return

                try:
                    res_order = supabase.table('orders').insert({
                        'org_id': self.org_id,
                        'cantidad_licencias': cantidad,
                        'precio_unitario': precio_unitario,
                        'subtotal': subtotal,
                        'iva': iva,
                        'total': total,
                        'status': 'PENDING'
                    }).execute()
                    
                    order_data = res_order.data[0]
                    self.registrar_log('ORDER_PLACED', f'{cantidad} licencias ({total:.2f}€)', 'blue')
                    
                    ui.notify('✅ Pedido registrado. Descargando Factura Proforma...', type='positive', timeout=5000)
                    self.dialogo_checkout.close()
                    
                    try:
                        ruta_proforma = pdf_generator.generar_informe(
                            user_info=self.org_data,
                            results=order_data,
                            test_type='PROFORMA'
                        )
                        ui.download(ruta_proforma)
                    except Exception as pdf_error:
                        ui.notify(f'El pedido se registró, pero falló el PDF: {pdf_error}', type='warning')
                    
                except Exception as ex:
                    ui.notify(f'Error en el servidor: {ex}', type='negative')

            with ui.row().classes('w-full gap-4'):
                ui.button('CANCELAR', on_click=self.dialogo_checkout.close).classes('flex-1 bg-gray-800 text-white font-bold')
                ui.button('CONFIRMAR PEDIDO', on_click=procesar_compra_final).classes('flex-1 bg-[#22C55E] text-[#0E1117] font-black')

        self.dialogo_checkout.open()

    def render_tienda(self):
        with ui.column().classes('w-full items-center p-8'):
            ui.label('AMPLÍA EL POTENCIAL DE TU EQUIPO').classes('text-3xl text-[#83ABF1] font-black tracking-widest mb-2 text-center')
            ui.label('Todos los planes incluyen 1 Licencia por Usuario con 3 Mediciones (Ciclo Evolutivo Completo).').classes('text-gray-400 mb-10 text-center')

            cif_registrado = self.org_data.get('cif_nif')
            razon_social = self.org_data.get('razon_social')
            
            if not cif_registrado or not razon_social:
                with ui.column().classes('w-full max-w-3xl bg-red-900/20 border-2 border-red-500 rounded-2xl p-8 items-center text-center shadow-xl'):
                    ui.icon('receipt_long', size='4rem', color='red').classes('mb-4')
                    ui.label('PERFIL FISCAL INCOMPLETO').classes('text-2xl text-red-400 font-black tracking-widest mb-2')
                    ui.label('Por normativas de facturación B2B, no puedes generar un pedido de licencias sin tener tu CIF/NIF y Razón Social registrados en el sistema.').classes('text-gray-300 mb-6')
                    ui.label('Por favor, contacta con tu administrador o soporte técnico de Audeo para que actualicen los datos de tu institución.').classes('text-sm text-gray-500 italic')
                return 

            with ui.row().classes('w-full max-w-6xl justify-center gap-8 items-stretch'):
                
                with ui.card().classes('w-80 bg-[#161B22] border border-gray-800 hover:border-[#83ABF1] transition-all p-8 flex flex-col shadow-xl'):
                    ui.label('Grupo Pequeño').classes('text-lg font-bold text-white mb-2')
                    ui.label('De 10 a 50 usuarios').classes('text-xs text-gray-500 mb-6')
                    with ui.row().classes('items-end gap-1 mb-6'):
                        ui.label('7.00').classes('text-4xl text-[#83ABF1] font-black')
                        ui.label('€ / usuario').classes('text-sm text-gray-400 mb-1')
                    
                    ui.separator().classes('bg-gray-800 mb-6')
                    ui.label('✓ 3 pasaciones (Medición, Progreso, Final)').classes('text-sm text-gray-300 mb-2')
                    ui.label('✓ Informes individuales SAPP/SAPE').classes('text-sm text-gray-300 mb-2')
                    ui.label('✓ Comparativa evolutiva básica').classes('text-sm text-gray-300 mb-8')
                    
                    ui.space()
                    qty_peq = ui.input('Nº Licencias').props('dark outlined type=number').classes('w-full mb-4')
                    ui.button('INICIAR COMPRA', on_click=lambda: self.abrir_checkout(qty_peq.value, 7.00, 'Grupo Pequeño')).classes('w-full bg-[#0D248D] text-white font-bold py-3 rounded-lg')

                with ui.card().classes('w-80 bg-[#0E1117] border-2 border-[#22C55E] p-8 flex flex-col shadow-2xl relative transform hover:-translate-y-2 transition-transform'):
                    ui.label('RECOMENDADO').classes('absolute -top-3 left-1/2 transform -translate-x-1/2 bg-[#22C55E] text-[#0E1117] text-[10px] font-black px-4 py-1 rounded-full tracking-widest')
                    
                    ui.label('Centros / Facultades').classes('text-xl font-bold text-white mb-2')
                    ui.label('De 51 a 200 usuarios').classes('text-xs text-gray-500 mb-6')
                    with ui.row().classes('items-end gap-1 mb-6'):
                        ui.label('5.00').classes('text-5xl text-[#22C55E] font-black')
                        ui.label('€ / usuario').classes('text-sm text-gray-400 mb-1')
                    
                    ui.separator().classes('bg-gray-800 mb-6')
                    ui.label('✓ Todo lo del plan anterior').classes('text-sm text-gray-300 mb-2')
                    ui.label('✓ Dashboard Analítico Avanzado').classes('text-sm text-gray-300 mb-2')
                    ui.label('✓ Informe Global de Centro (PDF)').classes('text-sm text-[#22C55E] font-bold mb-8')
                    
                    ui.space()
                    qty_cen = ui.input('Nº Licencias').props('dark outlined type=number').classes('w-full mb-4')
                    ui.button('INICIAR COMPRA', on_click=lambda: self.abrir_checkout(qty_cen.value, 5.00, 'Centros')).classes('w-full bg-[#22C55E] text-[#0E1117] font-black py-4 rounded-lg shadow-[0_0_15px_rgba(34,197,94,0.4)]')

                with ui.card().classes('w-80 bg-[#161B22] border border-gray-800 hover:border-[#83ABF1] transition-all p-8 flex flex-col shadow-xl'):
                    ui.label('Evaluación Masiva').classes('text-lg font-bold text-white mb-2')
                    ui.label('+500 usuarios').classes('text-xs text-gray-500 mb-6')
                    with ui.row().classes('items-end gap-1 mb-6'):
                        ui.label('3.00').classes('text-4xl text-white font-black')
                        ui.label('€ / usuario').classes('text-sm text-gray-400 mb-1')
                    
                    ui.separator().classes('bg-gray-800 mb-6')
                    ui.label('✓ Todo lo del plan anterior').classes('text-sm text-gray-300 mb-2')
                    ui.label('✓ Soporte técnico prioritario').classes('text-sm text-gray-300 mb-2')
                    ui.label('✓ API / Integración LMS (Moodle)').classes('text-sm text-gray-300 mb-8')
                    
                    ui.space()
                    qty_mas = ui.input('Nº Licencias').props('dark outlined type=number').classes('w-full mb-4')
                    ui.button('INICIAR COMPRA', on_click=lambda: self.abrir_checkout(qty_mas.value, 3.00, 'Masivo')).classes('w-full bg-transparent border border-gray-600 text-white font-bold py-3 rounded-lg hover:bg-gray-800')

            with ui.row().classes('w-full max-w-6xl mt-12 bg-blue-900/20 border border-blue-900/50 p-6 rounded-xl flex items-center gap-6'):
                ui.icon('lock', color='#83ABF1', size='2rem')
                with ui.column().classes('gap-1'):
                    ui.label('Transacción Segura B2B').classes('text-[#83ABF1] font-bold text-sm')
                    ui.label(f'Para aprobar cualquier compra, necesitarás el PIN de Seguridad de tu organización. Si no lo recuerdas, contacta con tu administrador.').classes('text-blue-300 text-xs')

    # ==========================================
    # RENDER PRINCIPAL
    # ==========================================
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
                    ui.label(f"PORTAL B2B | {self.org_data.get('name', self.org_id).upper()}").classes('text-2xl text-white font-black tracking-tight')
                with ui.row().classes('items-center gap-4'):
                    ui.button('CERRAR SESIÓN', on_click=self.cerrar_sesion, color='red').classes('font-bold rounded-lg px-8 py-2')

            # KPIs RÁPIDOS: LOS 3 CAJONES
            with ui.row().classes('w-full gap-4 mb-8'):
                ui.label(f"SAPE: {self.org_data.get('sape_balance', 0)} licencias").classes('bg-[#0E1117] text-blue-400 px-6 py-3 rounded-xl border border-blue-900/50 font-black shadow-[0_0_10px_rgba(59,130,246,0.1)]')
                ui.label(f"SAPP: {self.org_data.get('sapp_balance', 0)} licencias").classes('bg-[#0E1117] text-green-400 px-6 py-3 rounded-xl border border-green-900/50 font-black shadow-[0_0_10px_rgba(34,197,94,0.1)]')
                ui.label(f"SAIV: {self.org_data.get('saiv_balance', 0)} licencias").classes('bg-[#0E1117] text-purple-400 px-6 py-3 rounded-xl border border-purple-900/50 font-black shadow-[0_0_10px_rgba(168,85,247,0.1)]')
                
                usuarios_activos = len([u for u in self.users_data if not u.get('is_deleted')])
                ui.label(f"Usuarios Activos: {usuarios_activos}").classes('bg-[#0E1117] text-white px-6 py-3 rounded-xl border border-gray-800 font-bold ml-auto')

            # SISTEMA DE PESTAÑAS
            with ui.tabs().classes('w-full bg-[#161B22] text-[#83ABF1] rounded-t-2xl font-bold') as tabs:
                t_users = ui.tab('USUARIOS E HISTORIAL', icon='manage_accounts')
                t_qr = ui.tab('EVENTOS EN VIVO (QR)', icon='qr_code_scanner') 
                t_store = ui.tab('TIENDA Y LICENCIAS', icon='storefront')
                t_stats = ui.tab('ESTADÍSTICAS', icon='analytics')

            with ui.tab_panels(tabs, value=t_users).classes('w-full bg-[#161B22] border border-gray-800 rounded-b-2xl shadow-2xl p-0'):
                
                # PESTAÑA 1: USUARIOS
                with ui.tab_panel(t_users).classes('p-8'):
                    with ui.row().classes('w-full gap-8 items-start'):
                        
                        with ui.column().classes('w-1/3 min-w-[350px]'):
                            if self.privilegios.get('can_create_users', False):
                                with ui.column().classes('w-full bg-[#0E1117] p-6 rounded-2xl border border-gray-800 mb-6'):
                                    ui.label('Gestión Individual').classes('text-lg text-[#83ABF1] font-bold mb-4')
                                    inputs = {
                                        'u_nom': ui.input('Nombre de Usuario').classes('w-full mb-2').props('dark outlined'),
                                        'u_pwd': ui.input('Contraseña', password=True, password_toggle_button=True).classes('w-full mb-4').props('dark outlined'),
                                    }
                                    
                                    can_sape = self.privilegios.get('can_assign_sape', False)
                                    can_sapp = self.privilegios.get('can_assign_sapp', False)
                                    can_saiv = self.privilegios.get('can_assign_saiv', False)
                                    
                                    opciones_test = []
                                    if can_sape: opciones_test.append('SAPE')
                                    if can_sapp: opciones_test.append('SAPP')
                                    if can_saiv: opciones_test.append('SAIV')
                                    if can_sape and can_sapp: opciones_test.append('AMBAS')
                                    
                                    if opciones_test:
                                        inputs['u_tests'] = ui.select(opciones_test, label='Prueba Asignada', value=opciones_test[0]).classes('w-full mb-2').props('dark outlined')
                                        # Ya no pedimos intentos, el backend lo fuerza a 3 (SAPE/SAPP) o 1 (SAIV)
                                        inputs['u_intentos'] = ui.number(value=3).classes('hidden') 
                                        
                                        if can_sape:
                                            sectores_permitidos = self.privilegios.get('allowed_sape_sectors', SECTORES_OFICIALES)
                                            if not sectores_permitidos: sectores_permitidos = SECTORES_OFICIALES
                                            inputs['u_sectores'] = ui.select(sectores_permitidos, multiple=True, label='Sectores SAPE Permitidos').classes('w-full mb-2').props('dark outlined use-chips')
                                        else:
                                            inputs['u_sectores'] = ui.select([], multiple=True).classes('hidden')

                                        if can_sapp:
                                            perfiles_permitidos = self.privilegios.get('allowed_sapp_profiles', PERFILES_SAPP)
                                            if not perfiles_permitidos: perfiles_permitidos = PERFILES_SAPP
                                            inputs['u_perfil'] = ui.select(perfiles_permitidos, multiple=True, label='Perfiles SAPP Permitidos').classes('w-full mb-4').props('dark outlined use-chips')
                                        else:
                                            inputs['u_perfil'] = ui.select([], multiple=True).classes('hidden')
                                    else:
                                        ui.label('Tu organización no tiene pruebas asignadas. Contacta con Audeo.').classes('text-red-400 text-sm mb-4 font-bold')
                                        inputs['u_tests'] = ui.select(['NINGUNA'], value='NINGUNA').classes('hidden')
                                        inputs['u_intentos'] = ui.number(value=0).classes('hidden')
                                        inputs['u_sectores'] = ui.select([], multiple=True).classes('hidden')
                                        inputs['u_perfil'] = ui.select([], multiple=True).classes('hidden')

                                    with ui.row().classes('w-full gap-2 mt-2'):
                                        ui.button('LIMPIAR', on_click=lambda: self.limpiar_formulario(inputs)).classes('w-1/3 bg-gray-700 text-white font-bold')
                                        ui.button('GUARDAR', on_click=lambda: self.guardar_usuario_manual(inputs)).classes('flex-1 bg-[#83ABF1] text-[#0E1117] font-bold hover:scale-105 transition-all')

                                with ui.column().classes('w-full bg-[#0E1117] p-6 rounded-2xl border border-gray-800'):
                                    ui.label('Carga Masiva (CSV / XLSX)').classes('text-lg text-[#83ABF1] font-bold mb-4')
                                    ui.button('Descargar Plantilla XLSX', icon='download', on_click=self.descargar_plantilla_org).classes('w-full mb-4 bg-green-700 text-white font-bold')
                                    ui.upload(on_upload=self.procesar_carga_masiva, label="Subir Archivo", auto_upload=True).classes('w-full')
                            else:
                                with ui.column().classes('w-full bg-[#0E1117] p-6 rounded-2xl border border-red-900/50 items-center text-center'):
                                    ui.icon('lock', size='3rem', color='red').classes('mb-4 opacity-50')
                                    ui.label('Privilegios insuficientes').classes('text-red-400 font-bold mb-2')
                                    ui.label('No puedes registrar ni editar usuarios. Contacta con Administración.').classes('text-sm text-gray-500')

                        with ui.column().classes('flex-1'):
                            with ui.column().classes('w-full bg-[#0E1117] p-6 rounded-2xl border border-gray-800 mb-6'):
                                ui.label('Directorio de Usuarios').classes('text-xl text-[#83ABF1] font-bold mb-4')
                                if not self.users_data:
                                    ui.label('No hay usuarios registrados.').classes('text-gray-500')
                                else:
                                    for u in self.users_data:
                                        if u.get('role') == 'ORG_ADMIN' or u.get('is_deleted'): continue
                                        with ui.row().classes('w-full justify-between items-center p-3 border-b border-gray-800 hover:bg-[#161B22]'):
                                            with ui.column().classes('gap-0'):
                                                ui.label(u['username']).classes('text-white font-bold')
                                                
                                                p_data = u.get('profile_data', {})
                                                chips = []
                                                if p_data.get('sape', {}).get('attempts', 0) > 0: chips.append('SAPE')
                                                if p_data.get('sapp', {}).get('attempts', 0) > 0: chips.append('SAPP')
                                                if p_data.get('saiv', {}).get('attempts', 0) > 0: chips.append('SAIV')
                                                ui.label(" | ".join(chips)).classes('text-xs text-gray-500')

                                            if self.privilegios.get('can_create_users', False):
                                                with ui.row().classes('gap-2'):
                                                    ui.button(icon='edit', on_click=lambda u=u: self.preparar_edicion_usuario(u, inputs)).props('flat round color=blue size=sm')
                                                    ui.button(icon='delete', on_click=lambda user=u['username']: self.eliminar_usuario(user)).props('flat round color=red size=sm')

                            with ui.column().classes('w-full bg-[#0E1117] p-6 rounded-2xl border border-gray-800'):
                                ui.label('Historial de Registros').classes('text-xl text-[#83ABF1] font-bold mb-4')
                                
                                with ui.row().classes('gap-4 mb-4 text-xs font-bold bg-[#161B22] p-3 rounded-lg w-full justify-center'):
                                    ui.label('🟢 Activas').classes('text-green-500')
                                    ui.label('🟢🔵 Nuevas').classes('text-blue-400')
                                    ui.label('🟢🟡 Editadas').classes('text-yellow-400')
                                    ui.label('🟡🔴 Error').classes('text-orange-500')
                                    ui.label('🔴 Eliminadas').classes('text-red-500')

                                if not self.logs_data:
                                    ui.label('Sin actividad reciente.').classes('text-gray-500')
                                else:
                                    for log in self.logs_data:
                                        c = log.get('status_color')
                                        bg = "bg-green-500" if c=="green" else "bg-blue-400" if c=="green-blue" else "bg-yellow-400" if c=="green-yellow" else "bg-orange-500" if c=="yellow-red" else "bg-red-500"
                                        
                                        with ui.row().classes('w-full items-center gap-4 py-2 border-b border-gray-800/30'):
                                            ui.element('div').classes(f'w-3 h-3 rounded-full {bg} shadow-sm')
                                            ui.label(log.get('created_at', '')[:16].replace('T', ' ')).classes('text-gray-500 text-xs w-32')
                                            ui.label(log.get('action_type')).classes('text-white text-xs font-bold w-24')
                                            ui.label(log.get('target_user')).classes('text-[#83ABF1] text-sm')

                # NUEVA PESTAÑA: EVENTOS QR
                with ui.tab_panel(t_qr).classes('p-8'):
                    self.render_panel_qr()

                # PESTAÑA 2: TIENDA B2B
                with ui.tab_panel(t_store).classes('p-0'):
                    self.render_tienda()

                # PESTAÑA 3: ESTADÍSTICAS
                with ui.tab_panel(t_stats).classes('p-8'):
                    if not self.privilegios.get('can_view_org_stats', False):
                        with ui.column().classes('w-full items-center text-center py-10'):
                            ui.icon('visibility_off', size='4rem', color='gray').classes('mb-4')
                            ui.label('Estadísticas bloqueadas').classes('text-xl text-gray-400 font-bold')
                    else:
                        with ui.column().classes('w-full bg-[#0E1117] p-8 rounded-2xl border border-gray-800'):
                            ui.label('Panel Analítico').classes('text-2xl text-[#83ABF1] font-bold mb-6')
                            
                            with ui.row().classes('w-full gap-4 mb-8 bg-[#161B22] p-4 rounded-xl'):
                                ui.select(['Todas', 'SAPE', 'SAPP', 'SAIV'], label='Por Prueba', value='Todas').classes('w-48').props('dark outlined')
                                ui.select(['Todos'] + SECTORES_OFICIALES, label='Por Sector', value='Todos').classes('w-48').props('dark outlined')
                                ui.input('Filtrar Fecha').classes('w-48').props('dark outlined type=date')
                                ui.select(['Todos los usuarios'], label='Por Usuario', value='Todos los usuarios').classes('w-64').props('dark outlined')

                            if not self.evals_data:
                                ui.label('No hay evaluaciones completadas para mostrar estadísticas.').classes('text-gray-500 italic')
                            else:
                                ui.label('Evaluaciones Completadas:').classes('text-lg text-[#83ABF1] font-bold mb-4 tracking-widest uppercase')
                                filas_ev = []
                                
                                for ev in self.evals_data:
                                    test_type = ev.get('test_type', 'SAPE')
                                    sector = ev.get('sector_profile', 'N/A')
                                    fecha = ev.get('created_at', '')[:10]
                                    user_id = ev.get('user_id', 'Desconocido')
                                    
                                    if test_type == 'SAPP':
                                        res_sapp = ev.get('refined_metrics', ev.get('results', {})) 
                                        is_apt = res_sapp.get('global_compliance', False)
                                        score_str = "🟢 APTO" if is_apt else "🔴 NO APTO (Riesgo)"
                                    elif test_type == 'SAIV':
                                        res_saiv = ev.get('refined_metrics', {})
                                        codigo = res_saiv.get('riasec_code', 'N/A')
                                        score_str = f"🟣 Perfil {codigo}"
                                    else:
                                        res_sape = ev.get('results', ev.get('calculated_scores', {}))
                                        potencial = res_sape.get('potencial', 0)
                                        score_str = f"🚀 {potencial}% Potencial"

                                    # Aquí intentaremos buscar el nombre del usuario si coincide con el ID
                                    nombre_usr = next((u['username'] for u in self.users_data if u['username'] == user_id or u.get('id') == user_id), user_id)

                                    filas_ev.append({
                                        'user': nombre_usr, 
                                        'test': f"{test_type} - {sector}",
                                        'score': score_str,
                                        'date': fecha,
                                        'raw_data': ev 
                                    })

                                cols_ev = [
                                    {'name': 'user', 'label': 'Candidato', 'field': 'user', 'align': 'left'},
                                    {'name': 'test', 'label': 'Prueba y Sector', 'field': 'test', 'align': 'left'},
                                    {'name': 'score', 'label': 'Resultado', 'field': 'score', 'align': 'center'},
                                    {'name': 'date', 'label': 'Fecha', 'field': 'date', 'align': 'right'},
                                    {'name': 'actions', 'label': 'Acciones', 'field': 'actions', 'align': 'center'}
                                ]

                                with ui.table(columns=cols_ev, rows=filas_ev, row_key='user').classes('w-full bg-[#161B22] text-white border border-[#83ABF1]/20 rounded-xl shadow-lg') as table:
                                    table.add_slot('body-cell-score', '''
                                        <q-td :props="props">
                                            <span :class="
                                                props.value.includes('APTO') && !props.value.includes('NO') ? 'text-green-400 font-bold' : 
                                                props.value.includes('NO APTO') ? 'text-red-400 font-bold' : 
                                                props.value.includes('Perfil') ? 'text-purple-400 font-bold tracking-widest' :
                                                'text-blue-300 font-bold'">
                                                {{ props.value }}
                                            </span>
                                        </q-td>
                                    ''')
                                    table.add_slot('body-cell-actions', '''
                                        <q-td :props="props">
                                            <q-btn flat icon="picture_as_pdf" color="primary" @click="$parent.$emit('download_pdf', props.row)" />
                                        </q-td>
                                    ''')
                                    table.on('download_pdf', lambda e: descargar_informe_desde_consola(e.args))