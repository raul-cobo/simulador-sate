import os
from nicegui import ui
from nicegui import ui, app
from supabase import create_client
import os
from datetime import datetime

# --- 1. CONFIGURACIÓN Y CONEXIÓN ---
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key) if url and key else None

# --- 2. DATOS DEL JUEGO (SIMULACIÓN) ---
# En el futuro, esto vendrá de tu CSV o Base de Datos
GAME_DATA = [
    {
        "id": 1, 
        "month": 1,
        "story": "Acabas de recibir la ronda de inversión inicial (50k). Tu equipo está motivado pero desorganizado. El desarrollador principal te pide comprar licencias de software caras.",
        "question": "¿Qué decides hacer con el presupuesto?",
        "options": [
            {"txt": "Aprobar todo para mantener la moral alta.", "scores": {"team": 10, "cash": -20}},
            {"txt": "Negociar versiones gratuitas y ahorrar.", "scores": {"team": -5, "cash": 10}},
            {"txt": "Posponer la decisión y ver cómo avanzan.", "scores": {"team": -10, "cash": 0}}
        ]
    },
    {
        "id": 2, 
        "month": 2,
        "story": "Un competidor ha lanzado una funcionalidad similar a la tuya. Los clientes empiezan a preguntar en redes sociales.",
        "question": "¿Cuál es tu estrategia de comunicación?",
        "options": [
            {"txt": "Ignorarlo y seguir nuestro roadmap.", "scores": {"focus": 10, "market": -10}},
            {"txt": "Pivotar rápido para diferenciarnos.", "scores": {"focus": -20, "innovation": 20}},
            {"txt": "Atacar al competidor públicamente.", "scores": {"reputation": -50, "market": 10}}
        ]
    }
    # ... Aquí irían los 40 meses ...
]

# --- 3. LÓGICA DE NEGOCIO ---

def handle_login(u, p):
    try:
        res = supabase.table("users").select("*").eq("username", u).execute()
        if res.data and res.data[0]['password'] == p:
            user = res.data[0]
            app.storage.user['user'] = user
            
            # Ruteo inteligente
            if user['role'] == 'MANAGER':
                ui.navigate.to(f'/manager/{user["org_id"]}')
            else:
                ui.navigate.to('/sape/intro') # Los alumnos van al juego
        else:
            ui.notify('Credenciales incorrectas', type='negative')
    except Exception as e:
        ui.notify(f'Error: {e}', type='negative')

def save_results(score_history):
    """Guarda la partida en Supabase al terminar"""
    user = app.storage.user.get('user')
    if not user: return
    
    # Aquí calculamos el perfil final (Simulado por ahora)
    final_profile = "Emprendedor Equilibrado" 
    
    try:
        # Guardamos en una tabla 'results' (Asegúrate de crearla en Supabase si no existe)
        # O actualizamos el usuario
        ui.notify('Guardando resultados...', type='info')
        # supabase.table("results").insert({...}).execute() (Descomentar cuando tengas la tabla)
    except Exception as e:
        print(f"Error guardando: {e}")

# --- 4. INTERFAZ: LOGIN ---
@ui.page('/')
def login_page():
    # Si ya está logueado, redirigir
    if app.storage.user.get('user'):
        ui.navigate.to('/sape/intro')
        return

    with ui.column().classes('w-full h-screen items-center justify-center bg-slate-100'):
        with ui.card().classes('w-96 p-8 shadow-xl rounded-xl'):
            ui.label('🧬 AUDEO').classes('text-4xl font-bold text-blue-900 text-center w-full mb-6')
            u = ui.input('Usuario').classes('w-full')
            p = ui.input('Contraseña', password=True).classes('w-full')
            ui.button('ACCEDER', on_click=lambda: handle_login(u.value, p.value))\
                .classes('w-full mt-6 bg-blue-900 text-white')

# --- 5. INTERFAZ: MANAGER ---
@ui.page('/manager/{org_id}')
def manager_page(org_id: str):
    # (El código del manager que ya verificaste va aquí - Resumido para no ocupar mucho)
    with ui.column().classes('p-8 w-full'):
        ui.label(f'Manager: {org_id}').classes('text-2xl font-bold')
        try:
            users = supabase.table("users").select("*").eq("org_id", org_id).execute().data
            ui.table(
                columns=[{'name': 'username', 'label': 'Usuario', 'field': 'username'}], 
                rows=users
            ).classes('w-full mt-4')
        except: pass

# --- 6. INTERFAZ: JUEGO SAPE (VISUAL NOVEL) ---
@ui.page('/sape/intro')
def sape_intro():
    with ui.column().classes('w-full h-screen items-center justify-center bg-gray-900 text-white'):
        ui.label('SIMULADOR S.A.P.E.').classes('text-6xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-teal-400 mb-4')
        ui.label('Tu empresa. 40 Meses. Tus decisiones.').classes('text-xl text-gray-400 mb-8')
        ui.button('COMENZAR LA AVENTURA', on_click=lambda: ui.navigate.to('/sape/play'))\
            .classes('px-8 py-4 bg-blue-600 rounded-full text-xl font-bold shadow-lg shadow-blue-500/50 hover:scale-105 transition')

@ui.page('/sape/play')
def sape_play():
    # Estado de la partida actual
    state = {'idx': 0, 'score_history': []}
    
    # Contenedor principal que se limpiará en cada paso
    main_container = ui.column().classes('w-full min-h-screen items-center justify-center bg-slate-900 p-4')

    def next_step(option_selected):
        # 1. Guardar puntuación
        state['score_history'].append(option_selected['scores'])
        state['idx'] += 1
        
        # 2. Renderizar siguiente paso
        render()

    def render():
        main_container.clear() # ¡Magia! Borra lo anterior sin recargar la página
        
        with main_container:
            # A. FIN DEL JUEGO
            if state['idx'] >= len(GAME_DATA):
                save_results(state['score_history'])
                ui.label('SIMULACIÓN FINALIZADA').classes('text-4xl font-bold text-white mb-4')
                ui.label('Calculando tu perfil psicológico...').classes('text-gray-400 animate-pulse')
                ui.button('VER INFORME', on_click=lambda: ui.navigate.to('/sape/results')).classes('mt-8 bg-green-600 text-white px-6 py-3 rounded')
                return

            # B. JUEGO EN CURSO
            data = GAME_DATA[state['idx']]
            
            # Barra de progreso
            progress = (state['idx'] + 1) / len(GAME_DATA)
            with ui.row().classes('w-full max-w-4xl mb-6 items-center gap-4'):
                ui.label(f'MES {data["month"]}').classes('text-blue-400 font-bold whitespace-nowrap')
                ui.linear_progress(progress).props('color=blue-500 track-color=grey-800').classes('flex-1')

            # Escenario (Layout tipo Visual Novel)
            with ui.card().classes('w-full max-w-5xl bg-slate-800 border border-slate-700 shadow-2xl rounded-2xl overflow-hidden flex flex-row'):
                
                # Columna Izquierda: El "Coach" o Contexto (Imagen)
                with ui.column().classes('w-1/3 bg-slate-900 items-center justify-center p-6 border-r border-slate-700'):
                    # Aquí pondremos tu avatar animado más adelante
                    ui.icon('psychology', size='6rem', color='blue-400').classes('mb-4') 
                    ui.label('SITUACIÓN').classes('text-gray-500 text-sm tracking-widest')
                
                # Columna Derecha: Narrativa y Opciones
                with ui.column().classes('w-2/3 p-8'):
                    ui.markdown(f"### {data['story']}").classes('text-white text-xl leading-relaxed mb-6')
                    
                    ui.label(data['question']).classes('text-blue-200 font-bold mb-6 italic')
                    
                    # Opciones como botones grandes
                    with ui.column().classes('w-full gap-3'):
                        for opt in data['options']:
                            ui.button(opt['txt'], on_click=lambda o=opt: next_step(o))\
                                .classes('w-full text-left bg-slate-700 hover:bg-slate-600 text-white p-4 rounded-lg border border-slate-600 transition-all')

    render() # Arrancar primera vez

# --- 7. ARRANQUE ---
ui.run(
    host='0.0.0.0', 
    port=int(os.environ.get("PORT", 8080)), 
    storage_secret='secreto-audeo-b2b',
    title="Audeo Platform",
    reload=False
)