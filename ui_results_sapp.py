# ui_results_sapp.py
from nicegui import ui

def get_color_for_percentage(pct: int) -> str:
    """
    Calcula el gradiente de color exacto según las reglas de Audeo:
    - Negativo (<0%): Rojo intenso
    - 0% a 50%: De Rojo a Amarillo
    - 50% a 75%: De Amarillo a Verde Suave
    - 75% a 100%: De Verde Suave a Verde Intenso
    """
    if pct <= 0:
        return "#EF4444"
    elif pct <= 50:
        f = pct / 50.0
        r = int(239 - f * (239 - 234))
        g = int(68 + f * (179 - 68))
        b = int(68 - f * (68 - 8))
        return f"#{r:02X}{g:02X}{b:02X}"
    elif pct <= 75:
        f = (pct - 50) / 25.0
        r = int(234 - f * (234 - 74))
        g = int(179 + f * (222 - 179))
        b = int(8 + f * (128 - 8))
        return f"#{r:02X}{g:02X}{b:02X}"
    else:
        f = (pct - 75) / 25.0
        r = int(74 - f * (74 - 22))
        g = int(222 - f * (222 - 163))
        b = int(128 - f * (128 - 74))
        return f"#{r:02X}{g:02X}{b:02X}"

def render_dashboard_sapp(results: dict, user_data: dict = None):
    """
    Dibuja la matriz de resultados individual optimizada para la dinámica UMA.
    """
    # 1. DICCIONARIO DE TRADUCCIÓN (Crucial para la profesionalidad)
    traductor = {
        'child_advocacy': 'Defensa del menor',
        'family_collaboration': 'Colaboración familiar',
        'diversity_sensitivity': 'Sensibilidad a la diversidad',
        'interdisciplinary_work': 'Trabajo interdisciplinar',
        'ethical_integrity': 'Integridad Ética',
        'emotional_regulation': 'Regulación Emocional'
    }

    # 2. EXTRACCIÓN Y LIMPIEZA
    modulo = results.get('module', 'Evaluación S.A.P.P.').upper()
    comps = results.get('competencies', {})
    username = user_data.get('username', 'Candidato') if user_data else "Candidato"

    # 3. CONTENEDOR PRINCIPAL
    with ui.column().classes('w-full max-w-2xl mx-auto p-4 md:p-8 bg-[#0E1117] text-white min-h-screen'):
        
        # --- CABECERA ---
        with ui.column().classes('w-full items-center mb-8 gap-4'):
            # Contenedor del logo con fondo blanco (estilo SAPE)
            with ui.row().classes('bg-white rounded-2xl items-center justify-center p-4 w-48 h-32 shadow-lg'):
                ui.image('logo_original.png').classes('w-40 object-contain')
            
            ui.label('RESULTADOS INDIVIDUALES').classes('text-[#83ABF1] font-black tracking-[.3em] text-xs mt-4')
            ui.label(username.upper()).classes('text-white text-2xl font-light italic')
            ui.label(f"Módulo: {modulo}").classes('text-gray-500 text-sm font-bold tracking-widest')

        # --- SECCIÓN DE COMPETENCIAS ---
        if not comps:
            ui.label('No se han procesado métricas.').classes('text-red-400 text-center w-full')
        else:
            with ui.column().classes('w-full gap-4'):
                for comp_id, data in comps.items():
                    # Extraemos el porcentaje (manejando el dict del Refinery)
                    pct = data.get('percentage', 0) if isinstance(data, dict) else data
                    raw = data.get('raw_score', 0) if isinstance(data, dict) else 0
                    
                    color_hex = get_color_for_percentage(pct)
                    nombre_amigable = traductor.get(comp_id, str(comp_id).replace('_', ' ').title())

                    # Tarjeta de Competencia
                    with ui.card().classes('w-full bg-[#161B22] border border-gray-800 p-5 rounded-3xl shadow-xl overflow-hidden'):
                        with ui.row().classes('w-full justify-between items-center mb-4'):
                            ui.label(nombre_amigable).classes('text-white font-bold text-lg md:text-xl')
                            ui.label(f"{pct}%").classes('font-black text-2xl md:text-3xl').style(f'color: {color_hex};')
                        
                        # Barra de progreso customizada
                        with ui.element('div').classes('w-full h-3 bg-gray-900 rounded-full overflow-hidden relative'):
                            # Si es negativo o 0, mostramos una pequeña muesca roja
                            ancho = max(5, pct) if pct > 0 else 5
                            ui.element('div').classes('h-full transition-all duration-1000').style(
                                f'width: {ancho}%; background-color: {color_hex};'
                            )
                        
                        # Info adicional sutil
                        ui.label(f"Puntuación directa: {raw} pts").classes('text-[10px] text-gray-600 mt-3 font-mono uppercase tracking-tighter')

        # --- CIERRE Y DESPEDIDA ---
        with ui.column().classes('w-full items-center mt-12 gap-6 pb-20'):
            ui.separator().classes('bg-gray-800 opacity-20 w-1/2')
            ui.label('Gracias por participar en la dinámica Audeo').classes('text-gray-500 text-xs text-center italic')
            
            ui.button('FINALIZAR SESIÓN', on_click=lambda: ui.navigate.to('/')).classes(
                'w-full max-w-xs bg-[#0D248D] text-white font-bold py-4 rounded-xl hover:scale-105 transition-all shadow-xl'
            )

# Estilo para animación suave de entrada
ui.add_head_html('''
    <style>
        .nicegui-content { padding: 0 !important; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .animate-fade-in { animation: fadeIn 0.8s ease-out forwards; }
    </style>
''')