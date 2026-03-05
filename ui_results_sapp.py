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
        return "#EF4444"  # Rojo intenso (Tailwind red-500)
        
    elif pct <= 50:
        # Transición de Rojo (#EF4444) a Amarillo (#EAB308)
        f = pct / 50.0
        r = int(239 - f * (239 - 234))
        g = int(68 + f * (179 - 68))
        b = int(68 - f * (68 - 8))
        return f"#{r:02X}{g:02X}{b:02X}"
        
    elif pct <= 75:
        # Transición de Amarillo (#EAB308) a Verde Suave (#4ADE80)
        f = (pct - 50) / 25.0
        r = int(234 - f * (234 - 74))
        g = int(179 + f * (222 - 179))
        b = int(8 + f * (128 - 8))
        return f"#{r:02X}{g:02X}{b:02X}"
        
    else:
        # Transición de Verde Suave (#4ADE80) a Verde Intenso (#16A34A)
        f = (pct - 75) / 25.0
        r = int(74 - f * (74 - 22))
        g = int(222 - f * (222 - 163))
        b = int(128 - f * (128 - 74))
        return f"#{r:02X}{g:02X}{b:02X}"

def render_dashboard_sapp(results: dict):
    """
    Dibuja la matriz de resultados sin etiquetas de APTO/NO APTO.
    """
    ui.label('RESULTADOS DE COMPETENCIAS').classes('text-2xl text-[#83ABF1] font-black mb-8 tracking-widest uppercase')
    
    comps = results.get('competencies', {})
    
    if not comps:
        ui.label('No se registraron competencias en esta prueba.').classes('text-red-500 font-bold')
        return

    with ui.column().classes('w-full max-w-4xl gap-6'):
        for comp_name, data in comps.items():
            pct = data['percentage']
            color_hex = get_color_for_percentage(pct)
            
            # Formateo del nombre (de 'ethical_integrity' a 'Ethical Integrity')
            nombre_limpio = str(comp_name).replace('_', ' ').title()
            
            with ui.card().classes('w-full bg-[#161B22] border border-gray-800 p-6 rounded-2xl shadow-xl'):
                with ui.row().classes('w-full justify-between items-end mb-4'):
                    ui.label(nombre_limpio).classes('text-white font-bold text-xl tracking-wide')
                    ui.label(f"{pct}%").classes('font-black text-3xl').style(f'color: {color_hex}; text-shadow: 0 0 10px {color_hex}40;')
                
                # --- Barra de Progreso Customizada ---
                with ui.element('div').classes('w-full h-4 bg-gray-900 rounded-full overflow-hidden relative'):
                    if pct > 0:
                        # Barra normal hacia la derecha
                        ui.element('div').classes('h-full rounded-full').style(
                            f'width: {pct}%; background-color: {color_hex}; transition: width 1s ease-out;'
                        )
                    else:
                        # Si es negativo o cero, mostramos una barra llena pero muy tenue en rojo oscuro para indicar déficit
                        ui.element('div').classes('h-full w-full opacity-20').style(f'background-color: {color_hex};')

                # Detalles matemáticos en pequeño
                ui.label(f"Puntuación bruta: {data['raw_score']} puntos").classes('text-xs text-gray-500 mt-3')

    # Botón de salida
    with ui.row().classes('w-full justify-center mt-12'):
        ui.button('FINALIZAR Y VOLVER', on_click=lambda: ui.navigate.to('/')).classes(
            'bg-[#83ABF1] text-[#0E1117] font-bold px-10 py-4 rounded-xl hover:scale-105 transition-all'
        )