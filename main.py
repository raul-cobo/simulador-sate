from nicegui import ui, app
from supabase import create_client
import os
import pandas as pd
from datetime import datetime

# --- 1. CONEXIÓN A SUPABASE ---
# Usamos las variables de entorno de Railway
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key) if url and key else None

# --- 2. ESTILOS GLOBALES (TAILWIND) ---
# Definimos colores corporativos de Audeo (Azul oscuro y acentos)
APP_BG = 'bg-slate-50'
CARD_STYLE = 'p-8 rounded-xl shadow-lg bg-white border border-gray-100'
BTN_PRIMARY = 'bg-blue-900 text-white hover:bg-blue-800'

# --- 3. GESTIÓN DE ESTADO (SESSION) ---
# NiceGUI gestiona la sesión por usuario conectado automáticamente
def init_session():
    if 'user' not in app.storage.user:
        app.storage.user['user'] = None

# --- 4. PÁGINA: LOGIN ---
@ui.page('/')
def login_page():
    def handle_login():
        u = username.value
        p = password.value
        if not supabase:
            ui.notify('Error: Falta conexión a Supabase', type='negative'); return

        try:
            # Consulta a la tabla 'users'
            res = supabase.table("users").select("*").eq("username", u).execute()
            if res.data and res.data[0]['password'] == p:
                user_data = res.data[0]
                app.storage.user['user'] = user_data
                ui.notify(f'Bienvenido, {u}', type='positive')
                
                # RUTEADOR DE ROLES
                if user_data['role'] == 'ADMIN':
                    ui.navigate.to('/admin')
                elif user_data['role'] == 'MANAGER':
                    ui.navigate.to(f'/manager/{user_data["org_id"]}')
                else:
                    ui.navigate.to('/sape/intro')
            else:
                ui.notify('Credenciales incorrectas', type='negative')
        except Exception as e:
            ui.notify(f'Error de conexión: {str(e)}', type='negative')

    with ui.column().classes('w-full h-screen items-center justify-center ' + APP_BG):
        with ui.card().classes(CARD_STYLE + ' w-96'):
            ui.label('🧬 AUDEO').classes('text-4xl font-bold text-blue-900 text-center w-full mb-2')
            ui.label('Platform Access').classes('text-gray-400 text-center w-full mb-6 text-sm')
            
            username = ui.input('Usuario').classes('w-full mb-4')
            password = ui.input('Contraseña', password=True).classes('w-full mb-6')
            
            ui.button('ACCEDER', on_click=handle_login).classes('w-full ' + BTN_PRIMARY)

# --- 5. PÁGINA: MANAGER DASHBOARD ---
@ui.page('/manager/{org_id}')
def manager_dashboard(org_id: str):
    # Verificación de seguridad básica
    user = app.storage.user.get('user')
    if not user or user.get('role') not in ['MANAGER', 'ADMIN']:
        ui.navigate.to('/')
        return

    # Recuperar usuarios de la organización
    try:
        res = supabase.table("users").select("*").eq("org_id", org_id).execute()
        users_list = res.data if res.data else []
    except:
        users_list = []

    with ui.column().classes('w-full min-h-screen ' + APP_BG):
        # HEADER
        with ui.row().classes('w-full bg-white shadow-sm p-4 items-center justify-between'):
            ui.label(f'🏢 Panel de Control: {org_id}').classes('text-xl font-bold text-blue-900')
            ui.button('Cerrar Sesión', on_click=lambda: (app.storage.user.clear(), ui.navigate.to('/'))).props('flat color=grey')

        # CONTENIDO
        with ui.column().classes('w-full max-w-6xl mx-auto p-6'):
            
            # KPI CARDS
            with ui.row().classes('w-full gap-4 mb-6'):
                with ui.card().classes('flex-1 p-4 bg-white shadow-sm border-l-4 border-blue-900'):
                    ui.label('Total Usuarios').classes('text-gray-500 text-sm')
                    ui.label(str(len(users_list))).classes('text-3xl font-bold text-blue-900')
                with ui.card().classes('flex-1 p-4 bg-white shadow-sm border-l-4 border-green-500'):
                    ui.label('Licencias Activas').classes('text-gray-500 text-sm')
                    ui.label('ILIMITADO').classes('text-xl font-bold text-green-600')

            # TABLA DE USUARIOS (Reemplaza al st.dataframe)
            ui.label('Gestión de Equipo').classes('text-lg font-bold text-gray-700 mb-2')
            
            # Definición de columnas para AG Grid (NiceGUI usa esto por defecto, es muy potente)
            cols = [
                {'name': 'username', 'label': 'Usuario', 'field': 'username', 'sortable': True, 'align': 'left'},
                {'name': 'role', 'label': 'Rol', 'field': 'role', 'sortable': True, 'align': 'left'},
                {'name': 'password', 'label': 'Clave (Visible)', 'field': 'password', 'align': 'left'},
            ]
            
            table = ui.table(columns=cols, rows=users_list, pagination=10).classes('w-full bg-white shadow-sm rounded-lg')
            table.add_slot('top-right', """
                <q-input borderless dense debounce="300" v-model="props.filter" placeholder="Buscar usuario...">
                    <template v-slot:append>
                        <q-icon name="search" />
                    </template>
                </q-input>
            """)

# --- 6. PÁGINA: SAPE ENGINE (INTRO) ---
@ui.page('/sape/intro')
def sape_intro():
    user = app.storage.user.get('user')
    if not user: ui.navigate.to('/')

    with ui.column().classes('w-full h-screen items-center justify-center bg-gray-900 text-white'):
        # Estética "Inmersiva"
        ui.label('SIMULADOR S.A.P.E.').classes('text-5xl font-black mb-4 tracking-widest text-blue-400')
        ui.label('Sistema de Análisis de la Personalidad Emprendedora').classes('text-xl text-gray-400 mb-12')
        
        with ui.card().classes('w-full max-w-2xl bg-gray-800 border border-gray-700 p-8'):
            ui.markdown("""
            **Bienvenido/a.** Estás a punto de asumir el rol de fundador/a de una empresa a lo largo de **40 meses virtuales**.
            
            * 🚫 No hay respuestas correctas.
            * 🧠 El algoritmo analiza tus patrones de decisión.
            * ⚡ Tus decisiones tienen consecuencias.
            """).classes('text-lg leading-relaxed text-gray-300')
            
            ui.button('INICIAR SIMULACIÓN 🚀', on_click=lambda: ui.navigate.to('/sape/play'))\
                .classes('w-full mt-8 bg-blue-600 hover:bg-blue-500 text-white font-bold py-4 text-xl rounded-xl shadow-lg shadow-blue-900/50')

# --- 7. PÁGINA: SAPE GAMEPLAY (LÓGICA REACTIVA) ---
# Aquí cargaremos las preguntas simuladas (Placeholder para demo)
QUESTIONS = [
    {"id": 1, "text": "Mes 1: Tienes 10.000€. ¿Qué haces?", "options": [
        {"txt": "Invierto todo en producto", "score": {"risk": 10}},
        {"txt": "Guardo la mitad por seguridad", "score": {"risk": -5}}
    ]},
    {"id": 2, "text": "Mes 2: Un cliente se queja en redes sociales.", "options": [
        {"txt": "Le contesto públicamente defendiéndome", "score": {"emotional": -10}},
        {"txt": "Le contacto por privado para solucionar", "score": {"emotional": 10}}
    ]}
]

@ui.page('/sape/play')
def sape_play():
    # Estado local de la partida (NiceGUI usa contenedores que se limpian)
    state = {'step': 0, 'history': []}
    
    container = ui.column().classes('w-full h-screen items-center justify-center bg-gray-900')

    def next_step(option_chosen):
        # Guardar decisión
        state['history'].append(option_chosen)
        state['step'] += 1
        render_step() # <--- RECURSIVIDAD VISUAL

    def render_step():
        container.clear() # Limpiamos la pantalla anterior
        
        with container:
            # CHECK DE FINALIZACIÓN
            if state['step'] >= len(QUESTIONS):
                ui.label('SIMULACIÓN COMPLETADA').classes('text-4xl font-bold text-green-400 mb-4')
                ui.label('Generando informe de perfil...').classes('text-gray-400 animate-pulse')
                ui.button('VER RESULTADOS', on_click=lambda: ui.navigate.to('/manager/' + app.storage.user['user']['org_id'])).classes('mt-8 ' + BTN_PRIMARY)
                return

            # RENDERIZAR PREGUNTA ACTUAL
            q = QUESTIONS[state['step']]
            
            # Barra de progreso
            prog = (state['step'] + 1) / len(QUESTIONS)
            ui.linear_progress(prog).classes('w-full max-w-2xl mb-8').props('color=blue-500 track-color=gray-800')

            # Tarjeta de Pregunta
            with ui.card().classes('w-full max-w-3xl bg-gray-800 border-l-4 border-blue-500 p-8 shadow-2xl'):
                ui.label(f'MES {state["step"]+1}').classes('text-blue-400 font-bold mb-2 tracking-widest')
                ui.label(q['text']).classes('text-2xl text-white font-medium leading-relaxed mb-8')
                
                # Opciones
                with ui.column().classes('w-full gap-4'):
                    for opt in q['options']:
                        ui.button(opt['txt'], on_click=lambda o=opt: next_step(o))\
                            .classes('w-full text-left p-6 bg-gray-700 hover:bg-gray-600 text-white rounded-xl border border-gray-600 transition-all hover:scale-[1.02]')

    render_step() # Primera llamada

# --- 8. ARRANQUE ---
# Configuración necesaria para Railway
ui.run(
    host='0.0.0.0', 
    port=int(os.environ.get("PORT", 8080)), 
    title="Audeo Platform",
    storage_secret='audeo_super_secret_key' # Necesario para app.storage.user
)