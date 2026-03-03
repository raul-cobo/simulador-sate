import os
import ast
from datetime import datetime
from nicegui import ui, app
from supabase import create_client, Client
from dotenv import load_dotenv

from admin_console import ConsolaAdmin
from org_console import ConsolaOrganizacion
from sape_ui import SAPEInterface

# ==========================================
# 1. CONFIGURACIÓN DEL ENTORNO
# ==========================================
load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = None
try:
    if SUPABASE_URL and SUPABASE_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"⚠️ Error Supabase: {e}")

BG_COLOR = "#0E1117"

# ==========================================
# 2. FUNCIONES DE SESIÓN
# ==========================================
def inicializar_sesion():
    if not app.storage.user.get('authenticated'):
        app.storage.user.update({'authenticated': False, 'role': None, 'username': None, 'org_id': None})

def logout():
    app.storage.user.clear()
    ui.navigate.to('/')

# ==========================================
# 3. LOGIN RAÍZ
# ==========================================
@ui.page('/')
def login_page():
    ui.query('body').style(f'background-color: {BG_COLOR}; color: white; margin: 0;')
    inicializar_sesion()

    if app.storage.user.get('authenticated'):
        rol = app.storage.user.get('role')
        if rol == 'ADMIN': ui.navigate.to('/admin')
        elif rol == 'ORG_ADMIN': ui.navigate.to('/org-admin')
        else: ui.navigate.to('/panel')
        return

    with ui.column().classes('w-full h-screen items-center justify-center gap-6'):
        with ui.card().classes('bg-white p-8 rounded-2xl shadow-2xl items-center w-[30vw] min-w-[320px]'):
            ui.image('logo_original.png').classes('w-64 mb-4')
            ui.label('ACCESO PLATAFORMA').classes('text-gray-500 font-bold tracking-widest text-xs mb-6')
            
            user_input = ui.input('Usuario').classes('w-full').props('outlined')
            pwd_input = ui.input('Contraseña', password=True, password_toggle_button=True).classes('w-full mb-4').props('outlined')
            
            async def intentar_login(u, p):
                u_val = u or ""; p_val = p or ""
                user_str = u_val.strip(); pwd_str = p_val.strip()
                
                if not user_str or not pwd_str:
                    ui.notify('Introduce credenciales válidas', color='warning')
                    return
                if not supabase:
                    ui.notify('Error: Sin conexión a Base de Datos', color='negative')
                    return
                try:
                    res = supabase.table('users').select('*').eq('username', user_str).eq('password', pwd_str).eq('is_deleted', False).execute()
                    user_data = res.data[0] if res.data else None
                    
                    if not user_data:
                        res_admin = supabase.table('admins').select('*').eq('username', user_str).eq('password', pwd_str).execute()
                        if res_admin.data:
                            user_data = res_admin.data[0]
                            user_data['role'] = 'ADMIN'

                    if user_data:
                        rol = user_data.get('role', 'USER')
                        app.storage.user.update({
                            'authenticated': True, 'role': rol, 'username': user_data.get('username'), 'org_id': user_data.get('org_id', 'sistema')
                        })
                        ui.notify(f'Bienvenido, {user_data.get("username")}', color='positive')
                        if rol == 'ADMIN': ui.navigate.to('/admin')
                        elif rol == 'ORG_ADMIN': ui.navigate.to('/org-admin')
                        else: ui.navigate.to('/panel')
                    else: ui.notify('Credenciales no válidas', color='negative')
                except Exception as e: ui.notify(f'Error de sistema: {e}', color='negative')

            pwd_input.on('keydown.enter', lambda: intentar_login(user_input.value, pwd_input.value))
            ui.button('INICIAR SESIÓN', on_click=lambda: intentar_login(user_input.value, pwd_input.value)).classes(
                'w-full bg-[#0D248D] text-white font-bold py-4 rounded-xl hover:scale-105 transition-all shadow-lg'
            )

# ==========================================
# 4. CONSOLAS DE ADMINISTRACIÓN
# ==========================================
@ui.page('/admin')
def admin_page():
    ui.query('body').style(f'background-color: {BG_COLOR}; color: white; margin: 0;')
    inicializar_sesion()
    if not app.storage.user.get('authenticated') or app.storage.user.get('role') != 'ADMIN':
        ui.navigate.to('/'); return
    admin_console = ConsolaAdmin(); admin_console.render()

@ui.page('/org-admin')
def org_admin_page():
    ui.query('body').style(f'background-color: {BG_COLOR}; color: white; margin: 0;')
    inicializar_sesion()
    if not app.storage.user.get('authenticated') or app.storage.user.get('role') != 'ORG_ADMIN':
        ui.navigate.to('/'); return
    org_console = ConsolaOrganizacion(); org_console.render()

# ==========================================
# 5. PORTAL DEL CANDIDATO (ONBOARDING PRO)
# ==========================================
@ui.page('/panel')
def panel_page():
    ui.query('body').style(f'background-color: {BG_COLOR}; color: white; margin: 0;')
    inicializar_sesion()
    
    if not app.storage.user.get('authenticated') or app.storage.user.get('role') not in ['USER', 'STUDENT']:
        ui.navigate.to('/')
        return

    username = app.storage.user.get('username')
    
    if not supabase: return
    try:
        res_u = supabase.table('users').select('*').eq('username', username).execute()
        if not res_u.data: return
        user_db = res_u.data[0]
        
        res_o = supabase.table('organizations').select('*').eq('id', user_db['org_id']).execute()
        org_db = res_o.data[0] if res_o.data else {}
        privs = org_db.get('privileges', {})
    except Exception as e:
        ui.notify(f'Error de conexión: {e}', type='negative')
        return

    profile_data = user_db.get('profile_data', {})
    sape_data = profile_data.get('sape', {})
    sapp_data = profile_data.get('sapp', {})
    
    sape_allowed = profile_data.get('sape_attempts_allowed', 0) > 0 or sape_data.get('attempts', 0) > 0
    sapp_allowed = profile_data.get('sapp_attempts_allowed', 0) > 0 or sapp_data.get('attempts', 0) > 0

    # 1. DEPURADOR ULTRA-SEGURO DE LISTAS
    def safe_list(data):
        if not data: return []
        if isinstance(data, str):
            try:
                eval_data = ast.literal_eval(data)
                if isinstance(eval_data, list):
                    return [str(x).strip() for x in eval_data if str(x).strip()]
            except: pass
            cleaned = data.replace('[', '').replace(']', '').replace('"', '').replace("'", '')
            return [x.strip() for x in cleaned.split(',') if x.strip() and x.strip().lower() not in ['none', 'null', '']]
        if isinstance(data, list):
            return [str(x).strip() for x in data if str(x).strip() and str(x).strip().lower() not in ['none', 'null', '']]
        return []

    sec_user = safe_list(sape_data.get('sectors'))
    sec_org = safe_list(privs.get('allowed_sape_sectors'))
    perf_user = safe_list(sapp_data.get('profile'))
    perf_org = safe_list(privs.get('allowed_sapp_profiles'))

    # Listas por defecto
    SECTORES_SAPE_DEFAULT = ['TECH', 'CONSULTORIA', 'PYME', 'HOSTELERIA', 'AUTOEMPLEO', 'SOCIAL', 'INTRA', 'SALUD', 'PSICOLOGIA_SANITARIA', 'PSICOLOGÍA_NO_SANITARIA']
    PERFILES_SAPP_DEFAULT = ['Psicología educativa', 'Psicología organizacional', 'Psicología sanitaria', 'Psicología social']

    # BLINDAJE ABSOLUTO (Triple Fallback)
    sectores_finales = sec_user if sec_user else (sec_org if sec_org else SECTORES_SAPE_DEFAULT)
    if not sectores_finales or len(sectores_finales) == 0:
        sectores_finales = SECTORES_SAPE_DEFAULT

    perfiles_finales = perf_user if perf_user else (perf_org if perf_org else PERFILES_SAPP_DEFAULT)
    if not perfiles_finales or len(perfiles_finales) == 0:
        perfiles_finales = PERFILES_SAPP_DEFAULT

    # Listas Demográficas
    LISTA_GENERO = ['Masculino', 'Femenino', 'No binario', 'Prefiero no decirlo']
    LISTA_ESTUDIOS = ['Sin estudios', 'Educación Primaria', 'ESO / Secundaria', 'Bachillerato', 'FP Grado Medio', 'FP Grado Superior', 'Grado Universitario', 'Postgrado / Máster', 'Doctorado']
    LISTA_EMPLEO = ['Empleado por cuenta ajena', 'Autónomo / Emprendedor', 'Desempleado', 'Estudiante', 'Jubilado / Inactivo']
    LISTA_PROVINCIAS = sorted(["Álava", "Albacete", "Alicante", "Almería", "Asturias", "Ávila", "Badajoz", "Baleares", "Barcelona", "Burgos", "Cáceres", "Cádiz", "Cantabria", "Castellón", "Ciudad Real", "Córdoba", "Cuenca", "Gerona", "Granada", "Guadalajara", "Guipúzcoa", "Huelva", "Huesca", "Jaén", "La Coruña", "La Rioja", "Las Palmas", "León", "Lérida", "Lugo", "Madrid", "Málaga", "Murcia", "Navarra", "Orense", "Palencia", "Pontevedra", "Salamanca", "Segovia", "Sevilla", "Soria", "Tarragona", "Santa Cruz de Tenerife", "Teruel", "Toledo", "Valencia", "Valladolid", "Vizcaya", "Zamora", "Zaragoza", "Ceuta", "Melilla"])
    LISTA_HISTORIAL = ['Nunca he emprendido', 'He emprendido sin éxito', 'He emprendido con éxito']

    class OnboardingManager:
        def __init__(self):
            if not user_db.get('rgpd_accepted_at'): self.step = 0
            elif not user_db.get('age') or not user_db.get('province'): self.step = 1
            elif not user_db.get('education_level') or not user_db.get('entrepreneurship_status'): self.step = 2
            else: self.step = 3 
            
            self.age = user_db.get('age')
            self.gender = user_db.get('gender')
            self.province = user_db.get('province')
            self.education = user_db.get('education_level')
            self.employment = user_db.get('employment_status')
            self.entrepreneurship = user_db.get('entrepreneurship_status')
            
            self.test_type = 'SAPE' if sape_allowed else ('SAPP' if sapp_allowed else None)
            self.sector_sape = sectores_finales[0] if sectores_finales else None
            self.perfil_sapp = perfiles_finales[0] if perfiles_finales else None

    state = OnboardingManager()

    # Función de Debug/Reset para probar
    def resetear_onboarding():
        try:
            supabase.table('users').update({
                'rgpd_accepted_at': None, 'age': None, 'gender': None, 'province': None,
                'education_level': None, 'employment_status': None, 'entrepreneurship_status': None
            }).eq('username', username).execute()
            ui.navigate.to('/')
        except Exception as e: ui.notify(f"Error: {e}")

    with ui.row().classes('w-full items-center justify-between p-6 bg-[#161B22] border-b border-gray-800 shadow-md'):
        ui.image('logo_blanco.png').classes('w-32')
        with ui.row().classes('items-center gap-4'):
            ui.label(f"{username} | {user_db.get('org_id', '').upper()}").classes('text-gray-400 text-sm font-bold')
            ui.button(icon='restart_alt', on_click=resetear_onboarding).props('flat round color=orange').tooltip('Resetear mi Perfil')
            ui.button(icon='logout', on_click=logout).props('flat round color=white').tooltip('Cerrar Sesión')

    @ui.refreshable
    def render_stepper():
        with ui.column().classes('w-full max-w-2xl mx-auto p-4 items-center mt-6'):
            
            if state.step > 0:
                with ui.row().classes('w-full justify-center gap-4 mb-8'):
                    ui.icon('person', color='#83ABF1' if state.step >= 1 else 'gray').classes('text-3xl transition-colors')
                    ui.label('—').classes('text-gray-600 self-center font-bold')
                    ui.icon('work', color='#83ABF1' if state.step >= 2 else 'gray').classes('text-3xl transition-colors')
                    ui.label('—').classes('text-gray-600 self-center font-bold')
                    ui.icon('flag', color='#83ABF1' if state.step >= 3 else 'gray').classes('text-3xl transition-colors')

            # PASO 0
            if state.step == 0:
                with ui.column().classes('w-full bg-[#161B22] p-10 rounded-3xl border border-[#83ABF1]/50 shadow-2xl'):
                    ui.icon('security', size='4rem', color='#83ABF1').classes('mb-4 self-center')
                    ui.label('Protección de Datos (RGPD)').classes('text-2xl font-bold mb-6 text-center w-full')
                    with ui.scroll_area().classes('h-48 w-full bg-[#0E1117] p-4 rounded-lg mb-6 border border-gray-800 text-sm text-gray-400'):
                        ui.label("AUDEO PROCESSOR garantiza el cumplimiento estricto del Reglamento General de Protección de Datos (RGPD).")
                    check_rgpd = ui.checkbox('He leído y acepto el tratamiento de mis datos personales.').classes('text-white font-bold mb-8')
                    def aceptar_rgpd():
                        if not check_rgpd.value: return ui.notify('Acepta los términos para continuar.', type='warning')
                        try:
                            supabase.table('users').update({'rgpd_accepted_at': datetime.now().isoformat()}).eq('username', username).execute()
                            state.step = 1; render_stepper.refresh()
                        except Exception as e: ui.notify(f'Error BD: {e}', type='negative')
                    ui.button('ACEPTAR Y CONTINUAR', on_click=aceptar_rgpd).classes('w-full bg-[#83ABF1] text-[#0E1117] font-black py-4 rounded-xl')

            # PASO 1
            elif state.step == 1:
                with ui.column().classes('w-full bg-[#161B22] p-10 rounded-3xl border border-gray-800 shadow-2xl'):
                    ui.label('BLOQUE A: Datos Personales').classes('text-xl font-bold mb-8 text-[#83ABF1]')
                    age_in = ui.number('Edad actual', value=state.age, min=16, max=99).classes('w-full mb-4').props('dark outlined')
                    gen_in = ui.select(LISTA_GENERO, label='Género', value=state.gender).classes('w-full mb-4').props('dark outlined')
                    prov_in = ui.select(LISTA_PROVINCIAS, label='Provincia', value=state.province).classes('w-full mb-8').props('dark outlined')
                    def ir_a_bloque_b():
                        if not age_in.value or not gen_in.value or not prov_in.value: return ui.notify('Completa todos los campos.', type='warning')
                        state.age, state.gender, state.province = age_in.value, gen_in.value, prov_in.value
                        state.step = 2; render_stepper.refresh()
                    ui.button('SIGUIENTE PASO', on_click=ir_a_bloque_b).classes('w-full bg-[#83ABF1] text-[#0E1117] font-bold py-4 rounded-xl')

            # PASO 2
            elif state.step == 2:
                with ui.column().classes('w-full bg-[#161B22] p-10 rounded-3xl border border-gray-800 shadow-2xl'):
                    ui.label('BLOQUE B: Perfil Profesional').classes('text-xl font-bold mb-8 text-[#83ABF1]')
                    edu_in = ui.select(LISTA_ESTUDIOS, label='Nivel de estudios', value=state.education).classes('w-full mb-4').props('dark outlined')
                    emp_in = ui.select(LISTA_EMPLEO, label='Situación laboral', value=state.employment).classes('w-full mb-4').props('dark outlined')
                    hist_in = ui.select(LISTA_HISTORIAL, label='Historial de emprendimiento', value=state.entrepreneurship).classes('w-full mb-8').props('dark outlined')
                    def ir_a_bloque_c():
                        if not edu_in.value or not emp_in.value or not hist_in.value: return ui.notify('Completa tu perfil.', type='warning')
                        try:
                            supabase.table('users').update({
                                'age': int(state.age) if state.age else 0, 'gender': state.gender, 'province': state.province,
                                'education_level': edu_in.value, 'employment_status': emp_in.value, 'entrepreneurship_status': hist_in.value
                            }).eq('username', username).execute()
                            state.education, state.employment, state.entrepreneurship = edu_in.value, emp_in.value, hist_in.value
                            state.step = 3; ui.notify('Perfil guardado', type='positive'); render_stepper.refresh()
                        except Exception as e: ui.notify(f'Error BD: {e}', type='negative')
                    with ui.row().classes('w-full gap-4'):
                        ui.button('ATRÁS', on_click=lambda: [setattr(state, 'step', 1), render_stepper.refresh()]).classes('flex-1 bg-gray-700 text-white py-4 rounded-xl')
                        ui.button('GUARDAR Y CONTINUAR', on_click=ir_a_bloque_c).classes('flex-1 bg-[#83ABF1] text-[#0E1117] font-bold py-4 rounded-xl')

            # PASO 3
            elif state.step == 3:
                with ui.column().classes('w-full bg-[#161B22] p-10 rounded-3xl border border-green-500/50 shadow-[0_0_30px_rgba(34,197,94,0.1)]'):
                    ui.label('BLOQUE C: Configuración de la Evaluación').classes('text-xl font-bold mb-6 text-white')
                    
                    if not state.test_type:
                        ui.label('No tienes pruebas asignadas.').classes('text-red-400 font-bold mb-8')
                        return

                    opciones_radio = []
                    if sape_allowed: opciones_radio.append('SAPE')
                    if sapp_allowed: opciones_radio.append('SAPP')
                    
                    tipo_radio = ui.radio(opciones_radio, value=state.test_type).classes('text-white mb-6 font-bold text-lg').props('dark inline')
                    
                    sel_sector = ui.select(sectores_finales, label='Selecciona el sector', value=state.sector_sape).classes('w-full mb-8').props('dark outlined')
                    sel_perfil = ui.select(perfiles_finales, label='Selecciona tu perfil', value=state.perfil_sapp).classes('w-full mb-8').props('dark outlined')
                    
                    sel_sector.bind_visibility_from(tipo_radio, 'value', value=lambda v: v == 'SAPE')
                    sel_perfil.bind_visibility_from(tipo_radio, 'value', value=lambda v: v == 'SAPP')
                    
                    ui.label('Instrucciones: Sé sincero. Asegúrate de tener 15 min sin interrupciones.').classes('text-xs text-gray-400 mb-8')
                    
                    def comenzar():
                        if tipo_radio.value == 'SAPE':
                            if not sel_sector.value: return ui.notify('Selecciona un sector SAPE.', type='warning')
                            app.storage.user.update({'current_sector': sel_sector.value})
                            ui.navigate.to(f'/sape-test?sector={sel_sector.value}')
                        elif tipo_radio.value == 'SAPP':
                            if not sel_perfil.value: return ui.notify('Selecciona un perfil SAPP.', type='warning')
                            ui.notify('Motor SAPP en construcción.', type='info')

                    with ui.row().classes('w-full gap-4'):
                        ui.button('EDITAR PERFIL', on_click=lambda: [setattr(state, 'step', 1), render_stepper.refresh()]).classes('w-1/3 bg-gray-700 text-white py-4 rounded-xl')
                        ui.button('INICIAR EVALUACIÓN', on_click=comenzar).classes('flex-1 bg-green-600 text-white font-black py-4 rounded-xl hover:scale-105 transition-transform shadow-lg')

    render_stepper()

# ==========================================
# 6. ENRUTAMIENTO HACIA LOS MOTORES (CORREGIDO)
# ==========================================
@ui.page('/sape-test')
def sape_test(sector: str = 'TECH'):
    ui.query('body').style(f'background-color: {BG_COLOR}; color: white; margin: 0;')
    inicializar_sesion()
    
    if not app.storage.user.get('authenticated'):
        ui.navigate.to('/')
        return
    
    # Nombre del archivo donde están tus 160 preguntas (cambiar si es necesario)
    archivo_preguntas = 'preguntas_sape.csv' 
    
    try:
        # Instanciamos el motor inyectándole los parámetros correctos
        interfaz = SAPEInterface(df_path=archivo_preguntas, sector=sector)
        interfaz.render()
    except Exception as e:
        ui.label(f'Error crítico al cargar el motor SAPE: {e}').classes('text-red-500 font-bold text-2xl p-10')

# ==========================================
# INICIADOR DEL SERVIDOR
# ==========================================
if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title='Audeo Processor', storage_secret='audeo_secret_key_2026', port=8080)