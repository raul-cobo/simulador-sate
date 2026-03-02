import os
import pandas as pd
from nicegui import ui, app
from supabase import create_client, Client
from dotenv import load_dotenv
from admin_console import ConsolaAdmin
from sape_ui import SAPEInterface
from admin_console import ConsolaAdmin
from org_console import ConsolaOrganizacion # <--- Añadir esta línea
from sape_ui import SAPEInterface

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
    print(f"⚠️ Error Supabase: {e}")

BG_COLOR = "#0E1117"
CARD_COLOR = "#161B22"
ACCENT_COLOR = "#83ABF1"

# --- LECTURA DINÁMICA DE SECTORES ---
SECTORES_OFICIALES = [
    'TECH', 'CONSULTORIA', 'HOSTELERIA', 'INTRA', 'AUTOEMPLEO',
    'PSICOLOGIA_SANITARIA', 'PSICOLOGÍA_NO_SANITARIA', 'PYME', 'SALUD', 'SOCIAL'
]

try:
    df_sape = pd.read_csv('Prueba_SAPE.csv', sep=';', encoding='utf-8')
    SECTORES_DISPONIBLES = df_sape['SECTOR'].dropna().unique().tolist()
    if not SECTORES_DISPONIBLES:
        SECTORES_DISPONIBLES = SECTORES_OFICIALES
except Exception as e:
    print(f"⚠️ Aviso (CSV no encontrado): {e}")
    SECTORES_DISPONIBLES = SECTORES_OFICIALES

# ==========================================
# 2. GESTIÓN DE SEGURIDAD Y SESIÓN
# ==========================================
def inicializar_sesion():
    if 'authenticated' not in app.storage.user:
        app.storage.user.update({
            'authenticated': False, 
            'role': None, 
            'user_id': None, 
            'username': None,
            'org_id': None
        })

def logout():
    app.storage.user.clear()
    ui.navigate.to('/')

# ==========================================
# 3. PANTALLA DE LOGIN (Raíz)
# ==========================================
@ui.page('/')
def login_page():
    ui.query('body').style(f'background-color: {BG_COLOR}; color: white; margin: 0;')
    inicializar_sesion()

    # Redirección automática si ya está logueado
    if app.storage.user.get('authenticated'):
        rol = app.storage.user.get('role')
        if rol == 'ADMIN':
            ui.navigate.to('/admin')
        elif rol == 'ORG_ADMIN':
            ui.navigate.to('/org-admin')
        else:
            ui.navigate.to('/panel')
        return

    async def intentar_login():
        user = user_input.value.strip()
        pwd = pwd_input.value.strip()
        
        if not user or not pwd:
            ui.notify('Introduce credenciales', color='warning')
            return

        if not supabase:
            ui.notify('Error: Sin conexión a Base de Datos', color='negative')
            return

        try:
            # 1. INTENTO EN TABLA USERS (Usuarios, Org Admins y Admin espejo)
            res = supabase.table('users').select('*').eq('username', user).eq('password', pwd).eq('is_deleted', False).execute()
            
            user_data = None
            if res.data and len(res.data) > 0:
                user_data = res.data[0]
            else:
                # 2. INTENTO EN TABLA ADMINS (Seguridad redundante para Super-Admin)
                res_admin = supabase.table('admins').select('*').eq('username', user).eq('password', pwd).execute()
                if res_admin.data and len(res_admin.data) > 0:
                    user_data = res_admin.data[0]
                    user_data['role'] = 'ADMIN' # Forzamos rol si viene de esta tabla

            if user_data:
                rol = user_data.get('role', 'USER')
                app.storage.user.update({
                    'authenticated': True,
                    'role': rol,
                    'username': user_data.get('username'),
                    'org_id': user_data.get('org_id', 'sistema')
                })
                
                ui.notify(f'Bienvenido, {user_data.get("username")}', color='positive')
                
                # ENRUTAMIENTO POR ROLES
                if rol == 'ADMIN':
                    ui.navigate.to('/admin')
                elif rol == 'ORG_ADMIN':
                    ui.navigate.to('/org-admin')
                else:
                    ui.navigate.to('/panel')
            else:
                ui.notify('Credenciales no válidas', color='negative')
        except Exception as e:
            ui.notify(f'Error de sistema: {e}', color='negative')

    # UI LOGIN
    with ui.column().classes('w-full h-screen items-center justify-center gap-6'):
        with ui.card().classes('bg-white p-8 rounded-2xl shadow-2xl items-center w-[30vw] min-w-[320px]'):
            ui.image('logo_original.png').classes('w-64 mb-4')
            ui.label('ACCESO PLATAFORMA').classes('text-gray-500 font-bold tracking-widest text-xs mb-6')
            
            user_input = ui.input('Usuario').classes('w-full').props('outlined')
            pwd_input = ui.input('Contraseña', password=True, password_toggle_button=True).classes('w-full mb-4').props('outlined')
            pwd_input.on('keydown.enter', intentar_login)
            
            ui.button('INICIAR SESIÓN', on_click=intentar_login).classes(
                'w-full bg-[#0D248D] text-white font-bold py-4 rounded-xl hover:scale-105 transition-all shadow-lg'
            )

# ==========================================
# 4. CONSOLA DE ADMINISTRACIÓN (SUPER-ADMIN)
# ==========================================
@ui.page('/admin')
def admin_page():
    ui.query('body').style(f'background-color: {BG_COLOR}; color: white; margin: 0;')
    inicializar_sesion()
    
    # Verificación de Seguridad
    if not app.storage.user.get('authenticated') or app.storage.user.get('role') != 'ADMIN':
        ui.navigate.to('/')
        return

    # Instanciamos y renderizamos la consola que ya programamos
    admin_console = ConsolaAdmin()
    admin_console.render()
# ==========================================
# 4.5 CONSOLA DE ORGANIZACIÓN (CLIENTES B2B)
# ==========================================
@ui.page('/org-admin')
def org_admin_page():
    ui.query('body').style(f'background-color: {BG_COLOR}; color: white; margin: 0;')
    inicializar_sesion()
    
    # Verificación estricta de seguridad: Solo ORG_ADMIN puede entrar
    if not app.storage.user.get('authenticated') or app.storage.user.get('role') != 'ORG_ADMIN':
        ui.navigate.to('/')
        return

    # Importación dinámica para evitar bucles circulares en el inicio
    from org_console import ConsolaOrganizacion
    
    # Instanciamos y renderizamos
    org_console = ConsolaOrganizacion()
    org_console.render()    

# ==========================================
# 5. PORTAL DEL CANDIDATO (ONBOARDING Y SELECCIÓN)
# ==========================================
@ui.page('/panel')
def panel_page():
    ui.query('body').style(f'background-color: {BG_COLOR}; color: white; margin: 0;')
    inicializar_sesion()
    
    if not app.storage.user.get('authenticated'):
        ui.navigate.to('/')
        return

    username = app.storage.user.get('username')
    
    # 1. Extraer todos los datos frescos del usuario desde Supabase
    if not supabase: return
    try:
        res = supabase.table('users').select('*').eq('username', username).execute()
        if not res.data: return
        user_db = res.data[0]
    except Exception as e:
        ui.label(f'Error de lectura: {e}').classes('text-red-500 m-8')
        return

    org_id = user_db.get('org_id', 'Desconocida')
    profile_data = user_db.get('profile_data', {})
    
    # Evaluar permisos de SAPE
    sape_data = profile_data.get('sape', {})
    sape_allowed = profile_data.get('sape_attempts_allowed', 0) > 0 or sape_data.get('attempts', 0) > 0
    sape_sectors = sape_data.get('sectors', [])
    
    # Evaluar permisos de SAPP
    sapp_data = profile_data.get('sapp', {})
    sapp_allowed = profile_data.get('sapp_attempts_allowed', 0) > 0 or sapp_data.get('attempts', 0) > 0
    sapp_profiles_raw = sapp_data.get('profile', '')
    sapp_profiles_list = [p.strip() for p in sapp_profiles_raw.split(',') if p.strip()] if sapp_profiles_raw else []

    # 2. Clase para controlar el estado del flujo (Stepper Manual)
    class OnboardingState:
        def __init__(self):
            self.step = 1
            self.edad = user_db.get('age')
            self.estado_emp = user_db.get('entrepreneurship_status')
            
            # Pre-selecciones automáticas basadas en lo que tenga habilitado
            self.test_type = 'SAPE' if sape_allowed else ('SAPP' if sapp_allowed else None)
            self.sector_sape = sape_sectors[0] if sape_sectors else None
            self.perfil_sapp = sapp_profiles_list[0] if sapp_profiles_list else None

    estado = OnboardingState()

    # HEADER SUPERIOR (Botón de Salida)
    with ui.row().classes('w-full items-center justify-between p-6 bg-[#161B22] border-b border-gray-800 shadow-md'):
        ui.image('logo_blanco.png').classes('w-32')
        with ui.row().classes('items-center gap-6'):
            ui.label(f"{username}").classes('text-gray-400 text-sm')
            ui.button(icon='logout', on_click=logout).props('flat round color=white')

    # 3. RENDERIZADO REACTIVO DE LOS PASOS
    @ui.refreshable
    def render_onboarding():
        with ui.column().classes('w-full max-w-3xl mx-auto p-8 items-center mt-4'):
            
            # Indicador de Progreso Visual
            with ui.row().classes('w-full justify-center gap-4 mb-10'):
                ui.icon('person', color='#83ABF1' if estado.step >= 1 else 'gray').classes('text-4xl transition-colors')
                ui.label('—').classes('text-gray-600 self-center font-bold')
                ui.icon('tune', color='#83ABF1' if estado.step >= 2 else 'gray').classes('text-4xl transition-colors')
                ui.label('—').classes('text-gray-600 self-center font-bold')
                ui.icon('flag', color='#83ABF1' if estado.step >= 3 else 'gray').classes('text-4xl transition-colors')

            # ==========================================
            # PASO 1: RECOGIDA DE DATOS
            # ==========================================
            if estado.step == 1:
                with ui.column().classes('w-full bg-[#161B22] p-10 rounded-3xl border border-gray-800 shadow-2xl items-center'):
                    ui.label('Paso 1: Datos de Perfil').classes('text-2xl text-[#83ABF1] font-bold mb-4')
                    ui.label(f'Pertences a la organización: {org_id.upper()}').classes('text-gray-400 mb-8 font-mono text-sm bg-[#0E1117] px-4 py-2 rounded-lg')
                    
                    edad_in = ui.number('¿Cuál es tu edad actual?', value=estado.edad, min=16, max=99).classes('w-full max-w-sm mb-6').props('dark outlined')
                    
                    opciones_emp = ['Nunca he emprendido', 'He emprendido sin éxito', 'He emprendido con éxito']
                    emp_in = ui.select(opciones_emp, label='Historial de Emprendimiento', value=estado.estado_emp).classes('w-full max-w-sm mb-10').props('dark outlined')
                    
                    def guardar_paso_1():
                        if not edad_in.value or not emp_in.value:
                            ui.notify('Por favor completa todos los campos para continuar.', type='warning')
                            return
                        try:
                            # Guardamos en base de datos para futuras analíticas
                            supabase.table('users').update({
                                'age': int(edad_in.value),
                                'entrepreneurship_status': emp_in.value
                            }).eq('username', username).execute()
                            
                            estado.edad = edad_in.value
                            estado.estado_emp = emp_in.value
                            estado.step = 2
                            render_onboarding.refresh()
                        except Exception as e:
                            ui.notify(f'Error de red: {e}', type='negative')

                    ui.button('CONTINUAR', on_click=guardar_paso_1).classes('w-full max-w-sm bg-[#83ABF1] text-[#0E1117] font-black py-4 rounded-xl hover:scale-105 transition-transform')

            # ==========================================
            # PASO 2: CONFIGURACIÓN DE LA PRUEBA
            # ==========================================
            elif estado.step == 2:
                with ui.column().classes('w-full bg-[#161B22] p-10 rounded-3xl border border-gray-800 shadow-2xl items-center'):
                    ui.label('Paso 2: Selección de Prueba').classes('text-2xl text-[#83ABF1] font-bold mb-8')
                    
                    if not estado.test_type:
                        ui.label('No tienes pruebas asignadas.').classes('text-red-400 font-bold mb-4')
                        ui.label('Contacta con el administrador de tu organización.').classes('text-gray-500 mb-8')
                        ui.button('VOLVER AL INICIO', on_click=logout).classes('w-full max-w-sm bg-gray-600 text-white font-bold py-3 rounded-xl')
                        return

                    opciones_test = []
                    if sape_allowed: opciones_test.append('SAPE')
                    if sapp_allowed: opciones_test.append('SAPP')
                    
                    ui.label('Selecciona la prueba a realizar:').classes('text-gray-400 mb-2')
                    test_radio = ui.radio(opciones_test, value=estado.test_type).classes('text-white mb-8 font-bold text-lg').props('dark inline')
                    
                    sector_sel = ui.select(sape_sectors, label='Sector SAPE Habilitado', value=estado.sector_sape).classes('w-full max-w-sm mb-10').props('dark outlined')
                    perfil_sel = ui.select(sapp_profiles_list, label='Perfil SAPP Habilitado', value=estado.perfil_sapp).classes('w-full max-w-sm mb-10').props('dark outlined')
                    
                    # Mostrar el desplegable correcto según la prueba elegida
                    sector_sel.bind_visibility_from(test_radio, 'value', value=lambda v: v == 'SAPE')
                    perfil_sel.bind_visibility_from(test_radio, 'value', value=lambda v: v == 'SAPP')
                    
                    def guardar_paso_2():
                        estado.test_type = test_radio.value
                        estado.sector_sape = sector_sel.value
                        estado.perfil_sapp = perfil_sel.value
                        
                        if estado.test_type == 'SAPE' and not estado.sector_sape:
                            ui.notify('Selecciona el sector para la prueba SAPE.', type='warning')
                            return
                        if estado.test_type == 'SAPP' and not estado.perfil_sapp:
                            ui.notify('Selecciona el perfil para la prueba SAPP.', type='warning')
                            return
                            
                        estado.step = 3
                        render_onboarding.refresh()

                    with ui.row().classes('w-full max-w-sm gap-4'):
                        ui.button('ATRÁS', on_click=lambda: [setattr(estado, 'step', 1), render_onboarding.refresh()]).classes('flex-1 bg-[#0E1117] text-white border border-gray-600 font-bold py-4 rounded-xl')
                        ui.button('CONTINUAR', on_click=guardar_paso_2).classes('flex-1 bg-[#83ABF1] text-[#0E1117] font-black py-4 rounded-xl')

            # ==========================================
            # PASO 3: INSTRUCCIONES
            # ==========================================
            elif estado.step == 3:
                with ui.column().classes('w-full bg-[#161B22] p-10 rounded-3xl border border-[#83ABF1] shadow-[0_0_30px_rgba(131,171,241,0.1)] items-center text-center'):
                    ui.icon('info', size='4rem', color='#83ABF1').classes('mb-4')
                    ui.label('Instrucciones Finales').classes('text-3xl text-white font-black mb-8')
                    
                    if estado.test_type == 'SAPE':
                        with ui.column().classes('text-gray-300 text-base gap-6 text-left max-w-xl bg-[#0E1117] p-8 rounded-xl border border-gray-800 mb-8'):
                            ui.markdown('**1. Sinceridad ante todo:** No pienses demasiado, la primera respuesta que te venga a la mente suele ser la más precisa.')
                            ui.markdown('**2. Sin respuestas correctas:** Aquí no se aprueba ni se suspende. Se evalúa tu perfil natural y potencial de emprendimiento.')
                            ui.markdown('**3. Sin interrupciones:** Asegúrate de tener unos 15 minutos libres y buena conexión a internet para completar la prueba.')
                    else:
                        with ui.column().classes('text-gray-300 text-base gap-6 text-left max-w-xl bg-[#0E1117] p-8 rounded-xl border border-gray-800 mb-8'):
                            ui.markdown('**1. Casos Prácticos:** Responderás a escenarios reales del ejercicio profesional en psicología.')
                            ui.markdown('**2. Base Científica:** Tus respuestas se contrastarán con el *Cubo de Competencias* (Rodolfa et al.).')
                            ui.markdown('**3. Tiempo Estimado:** Este cuestionario requiere concentración. Tomará aproximadamente unos 25 minutos.')

                    def iniciar_prueba():
                        if estado.test_type == 'SAPE':
                            ui.navigate.to(f'/sape-test?sector={estado.sector_sape}')
                        else:
                            ui.notify('Módulo SAPP en construcción.', type='info') # Aquí enlazaremos sapp-test en el futuro

                    with ui.row().classes('w-full max-w-md gap-4'):
                        ui.button('ATRÁS', on_click=lambda: [setattr(estado, 'step', 2), render_onboarding.refresh()]).classes('w-1/3 bg-[#0E1117] text-white border border-gray-600 font-bold py-4 rounded-xl')
                        ui.button('¡COMENZAR PRUEBA!', on_click=iniciar_prueba).classes('flex-1 bg-green-500 text-white font-black py-4 rounded-xl shadow-[0_0_15px_rgba(34,197,94,0.3)] hover:scale-105 transition-transform')

    # Ejecutar el renderizado
    render_onboarding()

# ==========================================
# 6. ENTORNO DE EXAMEN (SAPE)
# ==========================================
@ui.page('/sape-test')
def test_sape_page(sector: str = 'TECH'):
    ui.query('body').style(f'background-color: {BG_COLOR}; color: white;')
    inicializar_sesion()
    
    if not app.storage.user.get('authenticated'):
        ui.navigate.to('/')
        return

    try:
        interfaz = SAPEInterface(df_path='Prueba_SAPE.csv', sector=sector, supabase_client=supabase)
        interfaz.render()
    except Exception as e:
        with ui.column().classes('w-full h-screen items-center justify-center'):
            ui.label("⚠️ Error en el motor de examen").classes('text-red-500 text-2xl mb-4')
            ui.label(str(e)).classes('text-gray-500 italic mb-8')
            ui.button('VOLVER AL PANEL', on_click=lambda: ui.navigate.to('/panel'), color='blue')

# ==========================================
# 7. EJECUCIÓN
# ==========================================
if __name__ in {"__main__", "__mp_main__"}:
    port = int(os.environ.get("PORT", 8080))
    # Importante: storage_secret para mantener sesiones en Railway
    ui.run(host="0.0.0.0", port=port, title="Audeo Platform", storage_secret="audeo_master_key_2026")