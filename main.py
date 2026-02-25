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
            pwd_input = ui.input('Contraseña', password=True).classes('w-full mb-4').props('outlined')
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
# 5. PANEL DE SELECCIÓN (USUARIO)
# ==========================================
@ui.page('/panel')
def panel_page():
    ui.query('body').style(f'background-color: {BG_COLOR}; color: white; margin: 0;')
    inicializar_sesion()
    
    if not app.storage.user.get('authenticated'):
        ui.navigate.to('/')
        return

    username = app.storage.user.get('username')
    org_id = app.storage.user.get('org_id')

    # HEADER
    with ui.row().classes('w-full items-center justify-between p-6 bg-[#161B22] border-b border-gray-800 shadow-md'):
        ui.image('logo_blanco.png').classes('w-40')
        with ui.row().classes('items-center gap-6'):
            ui.label(f"Sesión: {username}").classes('text-[#83ABF1] font-medium')
            ui.button(icon='logout', on_click=logout).props('flat round color=white')

    # GRID DE PRUEBAS
    with ui.column().classes('w-full max-w-6xl mx-auto p-12 items-center'):
        ui.label("MIS EVALUACIONES").classes('text-4xl font-black text-white mb-16 tracking-tight')
        
        with ui.row().classes('w-full justify-center gap-10'):
            # TARJETA SAPE
            with ui.column().classes(f'w-96 bg-[#161B22] p-10 rounded-3xl border border-[#83ABF1]/30 hover:border-[#83ABF1] transition-all duration-500 shadow-2xl items-center text-center group'):
                ui.icon('insights', size='5rem', color='83ABF1').classes('mb-6 group-hover:scale-110 transition-transform')
                ui.label("EVALUACIÓN SAPE").classes('text-2xl font-bold text-white mb-4')
                ui.label("Análisis de Personalidad Emprendedora").classes('text-gray-400 mb-10')
                
                sector_select = ui.select(SECTORES_DISPONIBLES, value='TECH', label='Sector').classes('w-full mb-6').props('dark outlined')
                ui.button('COMENZAR PRUEBA', 
                          on_click=lambda: ui.navigate.to(f'/sape-test?sector={sector_select.value}')).classes(
                              'w-full bg-[#83ABF1] text-[#0E1117] font-black py-4 rounded-2xl shadow-xl'
                          )

            # TARJETA SAPP (Próximamente)
            with ui.column().classes('w-96 bg-[#161B22]/50 p-10 rounded-3xl border border-gray-800 opacity-40 items-center text-center grayscale'):
                ui.icon('workspace_premium', size='5rem', color='gray').classes('mb-6')
                ui.label("EVALUACIÓN SAPP").classes('text-2xl font-bold text-gray-500 mb-4')
                ui.label("Certificación de Competencia Profesional").classes('text-gray-600 mb-10')
                ui.button('PRÓXIMAMENTE', color='gray').classes('w-full py-4 rounded-2xl').props('disabled')

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