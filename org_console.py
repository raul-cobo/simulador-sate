import os
import pandas as pd
import io
import json
from datetime import datetime
from nicegui import ui, app
from supabase import create_client, Client
from dotenv import load_dotenv
import pdf_generator

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

# Listas Oficiales de Audeo
SECTORES_OFICIALES = ['TECH', 'CONSULTORIA', 'HOSTELERIA', 'INTRA', 'AUTOEMPLEO', 'PYME', 'SALUD', 'SOCIAL']
PERFILES_SAPP = ['Organizacional', 'Educativo', 'Social', 'Sanitario']

# ==========================================
# FUNCIÓN CONECTORA PARA PDF
# ==========================================
def descargar_informe_desde_consola(row_data):
    ev_data = row_data.get('raw_data', {})
    test_type = ev_data.get('test_type', 'SAPE')
    
    if test_type == 'SAPP':
        results = ev_data.get('refined_metrics', ev_data.get('results', {}))
    else:
        results = ev_data.get('results', ev_data.get('calculated_scores', {}))
        
    user_info = {
        'user_id': ev_data.get('user_id', 'N/A'),
        'username': 'Candidato Evaluación'
    }
    
    try:
        ui.notify(f"Generando informe {test_type}...", color="info")
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
        self.editing_user = None

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
    # GESTIÓN INDIVIDUAL DE USUARIOS
    # ==========================================
    def preparar_edicion_usuario(self, user, inputs):
        self.editing_user = user['username']
        inputs['u_nom'].value = user['username']
        inputs['u_pwd'].value = user['password']
        
        p_data = user.get('profile_data', {})
        sape_data = p_data.get('sape', {})
        sapp_data = p_data.get('sapp', {})
        
        inputs['u_tests'].value = 'AMBAS' if sape_data.get('attempts',0)>0 and sapp_data.get('attempts',0)>0 else 'SAPE' if sape_data.get('attempts',0)>0 else 'SAPP' if sapp_data.get('attempts',0)>0 else 'SAPE'
        inputs['u_intentos'].value = max(sape_data.get('attempts', 0), sapp_data.get('attempts', 0))
        
        inputs['u_sectores'].value = sape_data.get('sectors', [])
        
        perfil_guardado = sapp_data.get('profile', '')
        inputs['u_perfil'].value = [p.strip() for p in perfil_guardado.split(',') if p.strip()] if perfil_guardado else []
        
        ui.notify(f"Editando usuario: {user['username']}", type='info')

    def guardar_usuario_manual(self, inputs):
        if not inputs['u_nom'].value or not inputs['u_pwd'].value:
            ui.notify('Usuario y Contraseña requeridos', type='warning')
            return

        test_val = inputs['u_tests'].value
        if test_val == 'NINGUNA':
            ui.notify('Error: No puedes crear usuarios sin licencias de pruebas asignadas.', type='negative')
            return

        intentos = int(inputs['u_intentos'].value)
        sape_active = test_val in ["SAPE", "AMBAS"]
        sapp_active = test_val in ["SAPP", "AMBAS"]

        sectores_seleccionados = inputs['u_sectores'].value if inputs['u_sectores'].value else []
        perfiles_seleccionados = inputs['u_perfil'].value if inputs['u_perfil'].value else []

        profile_data = {
            "sape_attempts_allowed": intentos if sape_active else 0,
            "sapp_attempts_allowed": intentos if sapp_active else 0,
            "sape": {
                "attempts": intentos if sape_active else 0,
                "sectors": sectores_seleccionados
            },
            "sapp": {
                "attempts": intentos if sapp_active else 0,
                "profile": ", ".join(perfiles_seleccionados),
                "groups": [] 
            }
        }

        payload = {
            "username": inputs['u_nom'].value.strip(),
            "password": inputs['u_pwd'].value.strip(),
            "org_id": self.org_id,
            "role": "USER",
            "is_deleted": False,
            "profile_data": profile_data
        }

        try:
            if getattr(self, 'editing_user', None):
                supabase.table('users').update(payload).eq('username', self.editing_user).execute()
                self.registrar_log('EDIT_USER', payload['username'], 'green-yellow')
                ui.notify('Usuario actualizado correctamente', type='positive')
            else:
                supabase.table('users').insert(payload).execute()
                self.registrar_log('NEW_USER', payload['username'], 'green-blue')
                ui.notify('Usuario creado con éxito', type='positive')
            
            self.editing_user = None
            self.render()
        except Exception as e:
            self.registrar_log('ERROR', payload['username'], 'yellow-red', str(e))
            ui.notify(f'Error de base de datos: {e}', type='negative')

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
            "tests": ["SAPE", "AMBAS"],
            "sape_sectors": ["TECH, SOCIAL", "SALUD"],
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

            count = 0
            for _, row in df.iterrows():
                tests = str(row['tests']).upper()
                sape_active = any(x in tests for x in ["SAPE", "AMBAS"])
                sapp_active = any(x in tests for x in ["SAPP", "AMBAS"])

                profile_data = {
                    "sape": {
                        "attempts": 1 if sape_active else 0,
                        "sectors": [s.strip().upper() for s in str(row.get('sape_sectors', '')).split(',')] if pd.notna(row.get('sape_sectors')) else []
                    },
                    "sapp": {
                        "attempts": 1 if sapp_active else 0,
                        "profile": str(row.get('sapp_profile', '')).strip().title(),
                        "groups": [g.strip() for g in str(row.get('sapp_groups', '')).split(',')] if pd.notna(row.get('sapp_groups')) else []
                    }
                }

                payload = {
                    "username": str(row['username']).strip(),
                    "password": str(row['password']).strip(),
                    "org_id": self.org_id, 
                    "role": "USER",
                    "is_deleted": False,
                    "profile_data": profile_data
                }
                
                supabase.table("users").upsert(payload).execute()
                count += 1

            self.registrar_log('BULK_UPLOAD', f'{count} usuarios', 'green-blue')
            ui.notify(f'Éxito: {count} usuarios sincronizados.', type='positive')
            self.render()

        except Exception as ex:
            self.registrar_log('ERROR_BULK', 'Archivo', 'yellow-red', str(ex))
            ui.notify(f'Error en archivo: {ex}', type='negative')

    # ==========================================
    # TIENDA Y FACTURACIÓN (B2B CLIENTE)
    # ==========================================
    def procesar_solicitud_compra(self, cantidad_str, plan_nombre):
        """Envía la solicitud al SuperAdmin o notifica al equipo de ventas"""
        try:
            cantidad = int(cantidad_str)
        except ValueError:
            ui.notify("Por favor, introduce una cantidad válida.", type="warning")
            return

        if cantidad <= 0:
            ui.notify("La cantidad debe ser mayor a 0.", type="warning")
            return

        # Registramos la solicitud de compra en los logs (para que el SuperAdmin lo vea)
        self.registrar_log(
            'SOLICITUD_COMPRA', 
            f'Solicitados {cantidad} ciclos', 
            'blue', 
            f'Plan seleccionado: {plan_nombre}'
        )
        
        ui.notify(
            f"✅ Solicitud de {cantidad} licencias enviada. El equipo de Audeo contactará contigo para la facturación y activación.", 
            type="positive", 
            position="top", 
            timeout=5000
        )

    def render_tienda(self):
        with ui.column().classes('w-full items-center p-8'):
            ui.label('AMPLÍA EL POTENCIAL DE TU EQUIPO').classes('text-3xl text-[#83ABF1] font-black tracking-widest mb-2 text-center')
            ui.label('Todos los planes incluyen 1 Licencia por Usuario con 3 Mediciones (Ciclo Evolutivo Completo).').classes('text-gray-400 mb-10 text-center')

            with ui.row().classes('w-full max-w-6xl justify-center gap-8 items-stretch'):
                
                # PLAN: Grupo Pequeño
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
                    
                    ui.space() # Empuja el input abajo
                    qty_peq = ui.input('Nº Licencias').props('dark outlined type=number').classes('w-full mb-4')
                    ui.button('SOLICITAR', on_click=lambda: self.procesar_solicitud_compra(qty_peq.value, 'Grupo Pequeño')).classes('w-full bg-[#0D248D] text-white font-bold py-3 rounded-lg')

                # PLAN: Centros (Destacado)
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
                    ui.button('SOLICITAR', on_click=lambda: self.procesar_solicitud_compra(qty_cen.value, 'Centros')).classes('w-full bg-[#22C55E] text-[#0E1117] font-black py-4 rounded-lg shadow-[0_0_15px_rgba(34,197,94,0.4)]')

                # PLAN: Masivo
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
                    ui.button('SOLICITAR', on_click=lambda: self.procesar_solicitud_compra(qty_mas.value, 'Masivo')).classes('w-full bg-transparent border border-gray-600 text-white font-bold py-3 rounded-lg hover:bg-gray-800')

            with ui.row().classes('w-full max-w-6xl mt-12 bg-blue-900/20 border border-blue-900/50 p-6 rounded-xl flex items-center gap-6'):
                ui.icon('info', color='#83ABF1', size='2rem')
                ui.label('¿Necesitas evaluar a una sola persona? Puedes comprar 1 Licencia Individual por 9.90€ contactando directamente con nuestro soporte.').classes('text-blue-300 text-sm')

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

            # KPIs RÁPIDOS
            with ui.row().classes('w-full gap-4 mb-8'):
                licencias_disponibles = self.org_data.get('licencias_compradas', 0)
                ui.label(f"Saldo de Ciclos Evolutivos: {licencias_disponibles}").classes('bg-[#0E1117] text-[#22C55E] px-6 py-3 rounded-xl border border-green-900/50 font-black shadow-[0_0_10px_rgba(34,197,94,0.1)]')
                usuarios_activos = len([u for u in self.users_data if not u.get('is_deleted')])
                ui.label(f"Usuarios Activos: {usuarios_activos}").classes('bg-[#0E1117] text-white px-6 py-3 rounded-xl border border-gray-800 font-bold')

            # SISTEMA DE PESTAÑAS (NUEVO ORDEN)
            with ui.tabs().classes('w-full bg-[#161B22] text-[#83ABF1] rounded-t-2xl font-bold') as tabs:
                t_users = ui.tab('USUARIOS E HISTORIAL', icon='manage_accounts')
                t_store = ui.tab('TIENDA Y LICENCIAS', icon='storefront') # <-- NUEVA PESTAÑA AQUÍ
                t_stats = ui.tab('ESTADÍSTICAS', icon='analytics')

            with ui.tab_panels(tabs, value=t_users).classes('w-full bg-[#161B22] border border-gray-800 rounded-b-2xl shadow-2xl p-0'):
                
                # PESTAÑA 1: USUARIOS
                with ui.tab_panel(t_users).classes('p-8'):
                    with ui.row().classes('w-full gap-8 items-start'):
                        
                        # COLUMNA IZQUIERDA: CREACIÓN Y CARGA
                        with ui.column().classes('w-1/3 min-w-[350px]'):
                            if self.privilegios.get('can_create_users', False):
                                # Gestión Manual
                                with ui.column().classes('w-full bg-[#0E1117] p-6 rounded-2xl border border-gray-800 mb-6'):
                                    ui.label('Gestión Individual').classes('text-lg text-[#83ABF1] font-bold mb-4')
                                    inputs = {
                                        'u_nom': ui.input('Nombre de Usuario').classes('w-full mb-2').props('dark outlined'),
                                        'u_pwd': ui.input('Contraseña', password=True, password_toggle_button=True).classes('w-full mb-4').props('dark outlined'),
                                    }
                                    
                                    can_sape = self.privilegios.get('can_assign_sape', False)
                                    can_sapp = self.privilegios.get('can_assign_sapp', False)
                                    
                                    opciones_test = []
                                    if can_sape: opciones_test.append('SAPE')
                                    if can_sapp: opciones_test.append('SAPP')
                                    if can_sape and can_sapp: opciones_test.append('AMBAS')
                                    
                                    if opciones_test:
                                        inputs['u_tests'] = ui.select(opciones_test, label='Prueba Asignada', value=opciones_test[0]).classes('w-full mb-2').props('dark outlined')
                                        inputs['u_intentos'] = ui.number('Intentos permitidos', value=1, min=1).classes('w-full mb-2').props('dark outlined')
                                        
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

                                    ui.button('GUARDAR USUARIO', on_click=lambda: self.guardar_usuario_manual(inputs)).classes('w-full bg-[#83ABF1] text-[#0E1117] font-bold mt-2 hover:scale-105 transition-all')
                                    ui.button('LIMPIAR', on_click=self.render).classes('w-full mt-2').props('flat color=gray')

                                # Carga Masiva
                                with ui.column().classes('w-full bg-[#0E1117] p-6 rounded-2xl border border-gray-800'):
                                    ui.label('Carga Masiva (CSV / XLSX)').classes('text-lg text-[#83ABF1] font-bold mb-4')
                                    ui.button('Descargar Plantilla XLSX', icon='download', on_click=self.descargar_plantilla_org).classes('w-full mb-4 bg-green-700 text-white font-bold')
                                    ui.upload(on_upload=self.procesar_carga_masiva, label="Subir Archivo", auto_upload=True).classes('w-full')
                            else:
                                with ui.column().classes('w-full bg-[#0E1117] p-6 rounded-2xl border border-red-900/50 items-center text-center'):
                                    ui.icon('lock', size='3rem', color='red').classes('mb-4 opacity-50')
                                    ui.label('Privilegios insuficientes').classes('text-red-400 font-bold mb-2')
                                    ui.label('No puedes registrar ni editar usuarios. Contacta con Administración.').classes('text-sm text-gray-500')

                        # COLUMNA DERECHA: DIRECTORIO E HISTORIAL
                        with ui.column().classes('flex-1'):
                            # Tabla de Usuarios
                            with ui.column().classes('w-full bg-[#0E1117] p-6 rounded-2xl border border-gray-800 mb-6'):
                                ui.label('Directorio de Usuarios').classes('text-xl text-[#83ABF1] font-bold mb-4')
                                if not self.users_data:
                                    ui.label('No hay usuarios registrados.').classes('text-gray-500')
                                else:
                                    for u in self.users_data:
                                        if u.get('role') == 'ORG_ADMIN' or u.get('is_deleted'): continue
                                        with ui.row().classes('w-full justify-between items-center p-3 border-b border-gray-800 hover:bg-[#161B22]'):
                                            ui.label(u['username']).classes('text-white font-bold')
                                            if self.privilegios.get('can_create_users', False):
                                                with ui.row().classes('gap-2'):
                                                    ui.button(icon='edit', on_click=lambda u=u: self.preparar_edicion_usuario(u, inputs)).props('flat round color=blue size=sm')
                                                    ui.button(icon='delete', on_click=lambda user=u['username']: self.eliminar_usuario(user)).props('flat round color=red size=sm')

                            # Historial de Registros
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
                                ui.select(['Todas', 'SAPE', 'SAPP'], label='Por Prueba', value='Todas').classes('w-48').props('dark outlined')
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
                                    else:
                                        res_sape = ev.get('results', ev.get('calculated_scores', {}))
                                        potencial = res_sape.get('potencial', 0)
                                        score_str = f"🚀 {potencial}% Potencial"

                                    filas_ev.append({
                                        'user': user_id, 
                                        'test': f"{test_type} - {sector}",
                                        'score': score_str,
                                        'date': fecha,
                                        'raw_data': ev 
                                    })

                                cols_ev = [
                                    {'name': 'user', 'label': 'ID Usuario', 'field': 'user', 'align': 'left'},
                                    {'name': 'test', 'label': 'Prueba y Sector', 'field': 'test', 'align': 'left'},
                                    {'name': 'score', 'label': 'Resultado', 'field': 'score', 'align': 'center'},
                                    {'name': 'date', 'label': 'Fecha', 'field': 'date', 'align': 'right'},
                                    {'name': 'actions', 'label': 'Acciones', 'field': 'actions', 'align': 'center'}
                                ]

                                with ui.table(columns=cols_ev, rows=filas_ev, row_key='user').classes('w-full bg-[#161B22] text-white border border-[#83ABF1]/20 rounded-xl shadow-lg') as table:
                                    table.add_slot('body-cell-score', '''
                                        <q-td :props="props">
                                            <span :class="props.value.includes('APTO') && !props.value.includes('NO') ? 'text-green-400 font-bold' : props.value.includes('NO APTO') ? 'text-red-400 font-bold' : 'text-blue-300 font-bold'">
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