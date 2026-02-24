import os
import pandas as pd
from nicegui import ui, app
from supabase import create_client, Client
from dotenv import load_dotenv

from admin_console import ConsolaAdmin
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
    'TECH', 
    'CONSULTORIA', 
    'HOSTELERIA', 
    'INTRA', 
    'AUTOEMPLEO',
    'PSICOLOGIA_SANITARIA', 
    'PSICOLOGÍA_NO_SANITARIA', 
    'PYME', 
    'SALUD', 
    'SOCIAL'
]

try:
    df_sape = pd.read_csv('Prueba_SAPE.csv', sep=';', encoding='utf-8')
    SECTORES_DISPONIBLES = df_sape['SECTOR'].dropna().unique().tolist()
    if not SECTORES_DISPONIBLES:
        SECTORES_DISPONIBLES = SECTORES_OFICIALES
except Exception as e:
    print(f"⚠️ Aviso (CSV no encontrado al iniciar, usando lista oficial): {e}")
    SECTORES_DISPONIBLES = SECTORES_OFICIALES

# ==========================================
# 2. GESTIÓN DE SEGURIDAD Y SESIÓN
# ==========================================
def inicializar_sesion():
    if 'authenticated' not in app.storage.user:
        app.storage.user.update({'authenticated': False, 'role': None, 'user_id': None, 'username': None})

def logout():
    app.storage.user.clear()
    ui.navigate.to('/')

# ==========================================
# 3. PANTALLA DE LOGIN (Raíz)
# ==========================================
# ==========================================
# 3. PANTALLA DE LOGIN (Raíz)
# ==========================================
@ui.page('/')
def login_page():
    ui.query('body').style(f'background-color: {BG_COLOR}; color: white; margin: 0;')
    inicializar_sesion()

    if app.storage.user.get('authenticated'):
        ui.navigate.to('/admin' if app.storage.user.get('role') == 'ADMIN' else '/panel')
        return

    def intentar_login():
        user = user_input.value.strip()
        pwd = pwd_input.value.strip()
        
        if not user or not pwd:
            ui.notify('Por favor, introduce usuario y contraseña.', color='warning')
            return

        if supabase:
            try:
                # 1. Consultamos la tabla 'users' real de tu Supabase
                response = supabase.table('users').select('*').eq('username', user).eq('password', pwd).eq('is_deleted', False).execute()
                
                if response.data and len(response.data) > 0:
                    user_data = response.data[0]
                    
                    # 2. Guardamos los datos vitales en la sesión
                    app.storage.user.update({
                        'authenticated': True, 
                        'role': user_data.get('role', 'STUDENT'), 
                        'username': user_data.get('username'),
                        'org_id': user_data.get('org_id') # Muy importante para luego guardar la evaluación
                    })
                    
                    # 3. Redirigimos según el rol
                    if user_data.get('role') == 'ADMIN':
                        ui.navigate.to('/admin')
                    else:
                        ui.navigate.to('/panel')
                else:
                    ui.notify('Usuario o contraseña incorrectos.', color='negative', position='top')
            except Exception as e:
                ui.notify(f'Error de conexión con la base de datos: {e}', color='negative')
        else:
            ui.notify('No hay conexión con Supabase configurada.', color='negative')

    # CONTENEDOR LOGIN (Corregido fiel al Doc Maestro)
    with ui.column().classes('w-full h-screen items-center justify-center'):
        
        # 1. Recuadro blanco con el logo (1/4 de la pantalla = w-[25vw])
        with ui.row().classes('bg-white p-6 rounded-2xl mb-8 justify-center items-center shadow-lg w-[25vw] min-w-[300px]'):
            ui.image('logo_original.png').classes('w-full object-contain')
            
        # 2. Reglones de login debajo del logo
        with ui.column().classes('items-center w-[25vw] min-w-[300px]'):
            user_input = ui.input('Usuario / Email').classes('w-full mb-4 text-white').props('dark outlined')
            pwd_input = ui.input('Contraseña', password=True, password_toggle_button=True).classes('w-full mb-8 text-white').props('dark outlined')
            
            # 3. Botón color #0D248D con ampliación del 10% en hover
            ui.button('ENTRAR', on_click=intentar_login).classes(
                'w-full bg-[#0D248D] text-white font-bold py-3 rounded-lg hover:scale-110 transition-transform duration-300 shadow-xl border-none'
            )

# ==========================================
# 4. PANEL DE SELECCIÓN (Usuario normal)
# ==========================================
@ui.page('/panel')
def panel_page():
    ui.query('body').style(f'background-color: {BG_COLOR}; color: white; margin: 0;')
    inicializar_sesion()
    
    rol_actual = app.storage.user.get('role')
    username = app.storage.user.get('username')
    org_id = app.storage.user.get('org_id')
    
    if not app.storage.user.get('authenticated') or rol_actual not in ['USER', 'STUDENT']:
        ui.navigate.to('/')
        return

    # COMPROBAR LICENCIAS EN SUPABASE
    puede_hacer_sape = False
    mensaje_bloqueo = "Verificando accesos..."
    
    if supabase:
        try:
            # 1. ¿La empresa tiene licencias?
            res_org = supabase.table('organizations').select('sape_licenses').eq('id', org_id).execute()
            licencias_org = res_org.data[0].get('sape_licenses', 0) if res_org.data else 0
            
            # 2. ¿El usuario tiene intentos asignados en su profile_data jsonb?
            res_user = supabase.table('users').select('profile_data').eq('username', username).execute()
            profile = res_user.data[0].get('profile_data') if res_user.data and res_user.data[0].get('profile_data') else {}
            intentos_user = profile.get('sape_attempts_allowed', 0)

            if licencias_org <= 0:
                mensaje_bloqueo = "Tu organización no tiene licencias SAPE disponibles."
            elif intentos_user <= 0:
                mensaje_bloqueo = "Has agotado tus intentos para realizar esta prueba."
            else:
                puede_hacer_sape = True
        except Exception as e:
            mensaje_bloqueo = "Error verificando permisos con el servidor."
            print(e)

    # Header Panel
    with ui.row().classes('w-full items-center justify-between p-6 border-b border-gray-800'):
        ui.image('logo_blanco.png').classes('w-48')
        with ui.row().classes('items-center gap-4'):
            ui.label(f"Hola, {username}").classes('text-gray-300')
            ui.button('Salir', on_click=logout, color='red').props('flat')

    with ui.column().classes('w-full max-w-4xl mx-auto pt-16 items-center'):
        ui.label("Panel de Selección").classes('text-3xl font-bold mb-12')
        
        with ui.row().classes('w-full gap-8 justify-center'):
            with ui.column().classes(f'w-80 bg-[{CARD_COLOR}] p-8 rounded-xl border border-[{ACCENT_COLOR}]/50 hover:border-[{ACCENT_COLOR}] transition-colors items-center text-center group relative'):
                ui.icon('psychology', size='4rem', color=ACCENT_COLOR).classes('mb-4 group-hover:scale-110 transition-transform')
                ui.label("Prueba S.A.P.E.").classes('text-xl font-bold text-white mb-2')
                ui.label("Sistema de Análisis de la Personalidad Emprendedora").classes('text-sm text-gray-400 mb-6')
                
                if puede_hacer_sape:
                    sector_select = ui.select(SECTORES_DISPONIBLES, value=SECTORES_DISPONIBLES[0] if SECTORES_DISPONIBLES else None, label='Selecciona tu sector').classes('w-full mb-4').props('dark outlined popup-content-style="background-color: #0F2592; color: white;"')
                    ui.button('INICIAR SAPE', on_click=lambda: ui.navigate.to(f'/sape-test?sector={sector_select.value}')).classes(f'w-full bg-[{ACCENT_COLOR}] text-[{BG_COLOR}] font-bold')
                else:
                    ui.label(mensaje_bloqueo).classes('text-red-400 font-bold text-sm mb-4')
                    ui.button('BLOQUEADO', color='red').classes('w-full font-bold opacity-50 cursor-not-allowed').props('disable')

            # Prueba SAPP...
            with ui.column().classes(f'w-80 bg-[{CARD_COLOR}] p-8 rounded-xl border border-gray-700 opacity-60 items-center text-center'):
                ui.icon('health_and_safety', size='4rem', color='gray').classes('mb-4')
                ui.label("Prueba S.A.P.P.").classes('text-xl font-bold text-white mb-2')
                ui.label("Próximamente").classes('text-sm text-gray-400 mb-6')
                ui.button('PRÓXIMAMENTE', color='gray').classes('w-full font-bold').props('disable')
# ==========================================
# 5. EL ENTORNO DE EXAMEN (SAPE)
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
            ui.label("Error al cargar la prueba").classes('text-red-500 text-2xl')
            ui.label(str(e)).classes('text-gray-400')
            ui.button('Volver', on_click=lambda: ui.navigate.to('/panel'))

if __name__ in {"__main__", "__mp_main__"}:
    port = int(os.environ.get("PORT", 8080))
    ui.run(host="0.0.0.0", port=port, title="Audeo Platform", storage_secret="audeo_super_secret_key_2026")