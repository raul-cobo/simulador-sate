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
# 5. PORTAL DEL CANDIDATO (ONBOARDING PRO)
# ==========================================
@ui.page('/panel')
async def panel_page():
    ui.query('body').style(f'background-color: {BG_COLOR}; color: white; margin: 0;')
    inicializar_sesion()
    
    if not app.storage.user.get('authenticated') or app.storage.user.get('role') not in ['USER', 'STUDENT']:
        ui.navigate.to('/')
        return

    username = app.storage.user.get('username')
    
    # --- 1. CARGA DE DATOS (Usuario y Privilegios de su Organización) ---
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

    # --- 2. LISTAS DESPLEGABLES OFICIALES ---
    LISTA_GENERO = ['Masculino', 'Femenino', 'No binario', 'Prefiero no decirlo']
    LISTA_ESTUDIOS = ['Sin estudios', 'Educación Primaria', 'ESO / Secundaria', 'Bachillerato', 'FP Grado Medio', 'FP Grado Superior', 'Grado Universitario', 'Postgrado / Máster', 'Doctorado']
    LISTA_EMPLEO = ['Empleado por cuenta ajena', 'Autónomo / Emprendedor', 'Desempleado', 'Estudiante', 'Jubilado / Inactivo']
    LISTA_PROVINCIAS = sorted(["Álava", "Albacete", "Alicante", "Almería", "Asturias", "Ávila", "Badajoz", "Baleares", "Barcelona", "Burgos", "Cáceres", "Cádiz", "Cantabria", "Castellón", "Ciudad Real", "Córdoba", "Cuenca", "Gerona", "Granada", "Guadalajara", "Guipúzcoa", "Huelva", "Huesca", "Jaén", "La Coruña", "La Rioja", "Las Palmas", "León", "Lérida", "Lugo", "Madrid", "Málaga", "Murcia", "Navarra", "Orense", "Palencia", "Pontevedra", "Salamanca", "Segovia", "Sevilla", "Soria", "Tarragona", "Santa Cruz de Tenerife", "Teruel", "Toledo", "Valencia", "Valladolid", "Vizcaya", "Zamora", "Zaragoza", "Ceuta", "Melilla"])
    LISTA_HISTORIAL = ['Nunca he emprendido', 'He emprendido sin éxito', 'He emprendido con éxito']

    # --- 3. CONTROLADOR DE ESTADO DEL FLUJO ---
    class OnboardingManager:
        def __init__(self):
            # Lógica de salto: Si ya aceptó RGPD, va al paso 1. Si no, empieza en 0.
            self.step = 0 if not user_db.get('rgpd_accepted_at') else 1
            
            self.age = user_db.get('age')
            self.gender = user_db.get('gender')
            self.province = user_db.get('province')
            self.education = user_db.get('education_level')
            self.employment = user_db.get('employment_status')
            self.entrepreneurship = user_db.get('entrepreneurship_status')
            
            # Selector de pruebas basado en privilegios de la org
            self.test_type = 'SAPE' if privs.get('can_assign_sape') else ('SAPP' if privs.get('can_assign_sapp') else None)
            self.sector_sape = None
            self.perfil_sapp = None

    state = OnboardingManager()

    # Cabecera Simple para el Candidato
    with ui.row().classes('w-full items-center justify-between p-6 bg-[#161B22] border-b border-gray-800 shadow-md'):
        ui.image('logo_blanco.png').classes('w-32')
        with ui.row().classes('items-center gap-6'):
            ui.label(f"{username} | {user_db.get('org_id', '').upper()}").classes('text-gray-400 text-sm font-bold')
            ui.button(icon='logout', on_click=logout).props('flat round color=white')

    # --- 4. RENDERIZADO REACTIVO ---
    @ui.refreshable
    def render_stepper():
        with ui.column().classes('w-full max-w-2xl mx-auto p-4 items-center mt-6'):
            
            # Indicador de Progreso Visual (Solo visible tras RGPD)
            if state.step > 0:
                with ui.row().classes('w-full justify-center gap-4 mb-8'):
                    ui.icon('person', color='#83ABF1' if state.step >= 1 else 'gray').classes('text-3xl transition-colors')
                    ui.label('—').classes('text-gray-600 self-center font-bold')
                    ui.icon('work', color='#83ABF1' if state.step >= 2 else 'gray').classes('text-3xl transition-colors')
                    ui.label('—').classes('text-gray-600 self-center font-bold')
                    ui.icon('flag', color='#83ABF1' if state.step >= 3 else 'gray').classes('text-3xl transition-colors')

            # ==========================================
            # PASO 0: CONSENTIMIENTO RGPD
            # ==========================================
            if state.step == 0:
                with ui.column().classes('w-full bg-[#161B22] p-10 rounded-3xl border border-[#83ABF1]/50 shadow-2xl'):
                    ui.icon('security', size='4rem', color='#83ABF1').classes('mb-4 self-center')
                    ui.label('Protección de Datos (RGPD)').classes('text-2xl font-bold mb-6 text-center w-full')
                    
                    with ui.scroll_area().classes('h-48 w-full bg-[#0E1117] p-4 rounded-lg mb-6 border border-gray-800 text-sm text-gray-400'):
                        ui.label("AUDEO PROCESSOR garantiza el cumplimiento estricto del Reglamento General de Protección de Datos (RGPD).")
                        ui.label("1. Sus datos serán tratados de forma totalmente confidencial.")
                        ui.label("2. La información demográfica recogida se utilizará exclusivamente para generar su informe individual y para crear modelos estadísticos agregados y anónimos para su organización.")
                        ui.label("3. Usted tiene derecho a solicitar el acceso, rectificación o eliminación de sus datos contactando con la administración de su entidad.")
                    
                    check_rgpd = ui.checkbox('He leído, comprendo y acepto el tratamiento de mis datos personales.').classes('text-white font-bold mb-8')
                    
                    async def aceptar_rgpd():
                        if not check_rgpd.value:
                            ui.notify('Debe aceptar el consentimiento legal para continuar.', type='warning')
                            return
                        from datetime import datetime
                        await supabase.table('users').update({'rgpd_accepted_at': datetime.now().isoformat()}).eq('username', username).execute()
                        state.step = 1
                        render_stepper.refresh()
                    
                    ui.button('ACEPTAR Y CONTINUAR', on_click=aceptar_rgpd).classes('w-full bg-[#83ABF1] text-[#0E1117] font-black py-4 rounded-xl')

            # ==========================================
            # PASO 1: BLOQUE A (Datos Demográficos)
            # ==========================================
            elif state.step == 1:
                with ui.column().classes('w-full bg-[#161B22] p-10 rounded-3xl border border-gray-800 shadow-2xl'):
                    ui.label('BLOQUE A: Datos Personales').classes('text-xl font-bold mb-8 text-[#83ABF1]')
                    
                    age_in = ui.number('Edad actual', value=state.age, min=16, max=99).classes('w-full mb-4').props('dark outlined')
                    gen_in = ui.select(LISTA_GENERO, label='Género', value=state.gender).classes('w-full mb-4').props('dark outlined')
                    prov_in = ui.select(LISTA_PROVINCIAS, label='Provincia de residencia', value=state.province).classes('w-full mb-8').props('dark outlined')
                    
                    def ir_a_bloque_b():
                        if not age_in.value or not gen_in.value or not prov_in.value:
                            ui.notify('Por favor, completa todos los campos demográficos.', type='warning')
                            return
                        state.age, state.gender, state.province = age_in.value, gen_in.value, prov_in.value
                        state.step = 2
                        render_stepper.refresh()
                        
                    ui.button('SIGUIENTE PASO', on_click=ir_a_bloque_b).classes('w-full bg-[#83ABF1] text-[#0E1117] font-bold py-4 rounded-xl')

            # ==========================================
            # PASO 2: BLOQUE B (Contexto Profesional)
            # ==========================================
            elif state.step == 2:
                with ui.column().classes('w-full bg-[#161B22] p-10 rounded-3xl border border-gray-800 shadow-2xl'):
                    ui.label('BLOQUE B: Perfil Profesional').classes('text-xl font-bold mb-8 text-[#83ABF1]')
                    
                    edu_in = ui.select(LISTA_ESTUDIOS, label='Nivel de estudios finalizados', value=state.education).classes('w-full mb-4').props('dark outlined')
                    emp_in = ui.select(LISTA_EMPLEO, label='Situación laboral actual', value=state.employment).classes('w-full mb-4').props('dark outlined')
                    hist_in = ui.select(LISTA_HISTORIAL, label='Historial de emprendimiento', value=state.entrepreneurship).classes('w-full mb-8').props('dark outlined')
                    
                    async def ir_a_bloque_c():
                        if not edu_in.value or not emp_in.value or not hist_in.value:
                            ui.notify('Por favor, completa todo tu perfil profesional.', type='warning')
                            return
                            
                        # Guardado masivo y persistente en Supabase
                        await supabase.table('users').update({
                            'age': int(state.age), 'gender': state.gender, 'province': state.province,
                            'education_level': edu_in.value, 'employment_status': emp_in.value, 'entrepreneurship_status': hist_in.value
                        }).eq('username', username).execute()
                        
                        state.education, state.employment, state.entrepreneurship = edu_in.value, emp_in.value, hist_in.value
                        state.step = 3
                        render_stepper.refresh()

                    with ui.row().classes('w-full gap-4'):
                        ui.button('ATRÁS', on_click=lambda: [setattr(state, 'step', 1), render_stepper.refresh()]).classes('flex-1 bg-gray-700 text-white py-4 rounded-xl')
                        ui.button('GUARDAR Y CONTINUAR', on_click=ir_a_bloque_c).classes('flex-1 bg-[#83ABF1] text-[#0E1117] font-bold py-4 rounded-xl')

            # ==========================================
            # PASO 3: BLOQUE C (Selección de Prueba)
            # ==========================================
            elif state.step == 3:
                with ui.column().classes('w-full bg-[#161B22] p-10 rounded-3xl border border-green-500/50 shadow-[0_0_30px_rgba(34,197,94,0.1)]'):
                    ui.label('BLOQUE C: Configuración de la Evaluación').classes('text-xl font-bold mb-6 text-white')
                    
                    if not state.test_type:
                        ui.label('No tienes pruebas asignadas por tu organización.').classes('text-red-400 font-bold mb-8')
                        return

                    opciones_radio = []
                    if privs.get('can_assign_sape'): opciones_radio.append('SAPE')
                    if privs.get('can_assign_sapp'): opciones_radio.append('SAPP')
                    
                    tipo_radio = ui.radio(opciones_radio, value=state.test_type).classes('text-white mb-6 font-bold text-lg').props('dark inline')
                    
                    # MAGIA B2B: Extraer SOLAMENTE lo que el Super-Admin le permitió a esta empresa
                    sectores_habilitados = privs.get('allowed_sape_sectors', [])
                    perfiles_habilitados = privs.get('allowed_sapp_profiles', [])
                    
                    sel_sector = ui.select(sectores_habilitados, label='Selecciona el sector de tu proyecto', value=state.sector_sape).classes('w-full mb-8').props('dark outlined')
                    sel_perfil = ui.select(perfiles_habilitados, label='Selecciona tu perfil a analizar', value=state.perfil_sapp).classes('w-full mb-8').props('dark outlined')
                    
                    # Mostrar y ocultar campos según la prueba seleccionada
                    sel_sector.bind_visibility_from(tipo_radio, 'value', value=lambda v: v == 'SAPE')
                    sel_perfil.bind_visibility_from(tipo_radio, 'value', value=lambda v: v == 'SAPP')
                    
                    # Instrucciones Dinámicas
                    ui.label('Instrucciones Importantes:').classes('text-sm text-gray-400 font-bold mb-2')
                    ui.label('• Sé sincero, no hay respuestas correctas o incorrectas.').classes('text-xs text-gray-500 mb-1')
                    ui.label('• Asegúrate de tener 15 minutos sin interrupciones.').classes('text-xs text-gray-500 mb-8')
                    
                    def comenzar():
                        if tipo_radio.value == 'SAPE':
                            if not sel_sector.value:
                                ui.notify('Debes seleccionar un sector para la prueba SAPE.', type='warning')
                                return
                            ui.navigate.to(f'/sape-test?sector={sel_sector.value}')
                        elif tipo_radio.value == 'SAPP':
                            if not sel_perfil.value:
                                ui.notify('Debes seleccionar un perfil para la prueba SAPP.', type='warning')
                                return
                            ui.notify('Motor SAPP en construcción.', type='info') # Placeholder

                    with ui.row().classes('w-full gap-4'):
                        ui.button('ATRÁS', on_click=lambda: [setattr(state, 'step', 2), render_stepper.refresh()]).classes('w-1/3 bg-gray-700 text-white py-4 rounded-xl')
                        ui.button('INICIAR EVALUACIÓN', on_click=comenzar).classes('flex-1 bg-green-600 text-white font-black py-4 rounded-xl hover:scale-105 transition-transform shadow-lg')

    render_stepper()

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