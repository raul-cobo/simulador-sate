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
    """
    Recibe los datos de la fila seleccionada, extrae el JSON original
    y dispara el pdf_generator pasándole si es SAPE o SAPP.
    """
    ev_data = row_data.get('raw_data', {})
    test_type = ev_data.get('test_type', 'SAPE')
    
    # Extraemos los resultados según la estructura que tenga la DB
    if test_type == 'SAPP':
        results = ev_data.get('refined_metrics', ev_data.get('results', {}))
    else:
        results = ev_data.get('results', ev_data.get('calculated_scores', {}))
        
    user_info = {
        'user_id': ev_data.get('user_id', 'N/A'),
        'username': 'Candidato Evaluación' # Si tienes un cruce con la tabla users, se muestra aquí
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

    def solicitar_licencias(self):
        self.registrar_log('SOLICITUD_LICENCIAS', 'SAPE/SAPP', 'green')
        ui.notify("Solicitud enviada. Se emitirá la facturación posterior correspondiente.", type='positive', icon='check_circle')

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
        intentos = int(inputs['u_intentos'].value)
        
        sape_active = test_val in ["SAPE", "AMBAS"]
        sapp_active = test_val in ["SAPP", "AMBAS"]

        sectores_seleccionados = inputs['u_sectores'].value or []
        perfiles_seleccionados = inputs['u_perfil'].value or []

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
            if self.editing_user:
                supabase.table('users').update(payload).eq('username', self.editing_user).execute()
                self.registrar_log('EDIT_USER', payload['username'], 'green-yellow')
                ui.notify('Usuario actualizado', type='positive')
            else:
                supabase.table('users').insert(payload).execute()
                self.registrar_log('NEW_USER', payload['username'], 'green-blue')
                ui.notify('Usuario creado', type='positive')
            
            self.editing_user = None
            self.render()
        except Exception as e:
            self.registrar_log('ERROR', payload['username'], 'yellow-red', str(e))
            ui.notify(f'Error guardando usuario: {e}', type='negative')

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
                    ui.button('Solicitar + Licencias', on_click=self.solicitar_licencias, icon='add_shopping_cart').classes('bg-green-700 text-white font-bold rounded-lg')
                    ui.button('CERRAR SESIÓN', on_click=self.cerrar_sesion, color='red').classes('font-bold rounded-lg')

            # KPIs RÁPIDOS
            with ui.row().classes('w-full gap-4 mb-8'):
                ui.label(f"Licencias SAPE: {self.org_data.get('sape_licenses', 0)}").classes('bg-[#0E1117] text-[#83ABF1] px-6 py-3 rounded-xl border border-gray-800 font-bold')
                ui.label(f"Licencias SAPP: {self.org_data.get('sapp_licenses', 0)}").classes('bg-[#0E1117] text-[#83ABF1] px-6 py-3 rounded-xl border border-gray-800 font-bold')
                usuarios_activos = len([u for u in self.users_data if not u.get('is_deleted')])
                ui.label(f"Usuarios Activos: {usuarios_activos}").classes('bg-[#0E1117] text-white px-6 py-3 rounded-xl border border-gray-800 font-bold')

            # SISTEMA DE PESTAÑAS
            with ui.tabs().classes('w-full bg-[#161B22] text-[#83ABF1] rounded-t-2xl font-bold') as tabs:
                t_users = ui.tab('USUARIOS E HISTORIAL', icon='manage_accounts')
                t_stats = ui.tab('ESTADÍSTICAS', icon='analytics')

            with ui.tab_panels(tabs, value=t_users).classes('w-full bg-[#161B22] border border-gray-800 rounded-b-2xl shadow-2xl p-8'):
                
                with ui.tab_panel(t_users):
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
                                    
                                    if self.privilegios.get('can_assign_tests', False):
                                        inputs['u_tests'] = ui.select(['SAPE', 'SAPP', 'AMBAS'], label='Prueba Asignada', value='SAPE').classes('w-full mb-2').props('dark outlined')
                                        inputs['u_intentos'] = ui.number('Intentos permitidos', value=1, min=1).classes('w-full mb-2').props('dark outlined')
                                        
                                        inputs['u_sectores'] = ui.select(SECTORES_OFICIALES, multiple=True, label='Sectores SAPE Habilitados').classes('w-full mb-2').props('dark outlined use-chips')
                                        inputs['u_perfil'] = ui.select(PERFILES_SAPP, multiple=True, label='Perfiles SAPP Habilitados').classes('w-full mb-4').props('dark outlined use-chips')
                                    else:
                                        inputs['u_tests'] = ui.label('Prueba: SAPE (Por defecto)')
                                        inputs['u_intentos'] = ui.label('Intentos: 1')
                                        inputs['u_sectores'] = ui.label('')
                                        inputs['u_perfil'] = ui.label('')

                                    ui.button('GUARDAR USUARIO', on_click=lambda: self.guardar_usuario_manual(inputs)).classes('w-full bg-[#83ABF1] text-[#0E1117] font-bold mt-2')
                                    ui.button('LIMPIAR', on_click=self.render).classes('w-full mt-2').props('flat color=gray')

                                # Carga Masiva
                                with ui.column().classes('w-full bg-[#0E1117] p-6 rounded-2xl border border-gray-800'):
                                    ui.label('Carga Masiva (CSV / XLSX)').classes('text-lg text-[#83ABF1] font-bold mb-4')
                                    ui.button('Descargar Plantilla XLSX', icon='download', on_click=self.descargar_plantilla_org).classes('w-full mb-4 bg-green-700 text-white')
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

                # ----------------------------------------------------------------
                # PESTAÑA 2: ESTADÍSTICAS (POLIMÓRFICAS SAPE Y SAPP)
                # ----------------------------------------------------------------
                with ui.tab_panel(t_stats):
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