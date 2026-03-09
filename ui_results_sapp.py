# ui_results_sapp.py
from nicegui import ui
import json

def get_color_for_percentage(pct: int) -> str:
    """Calcula el gradiente de color exacto según las reglas de Audeo."""
    if pct <= 0: return "#EF4444"
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

def render_dashboard_sapp(grupo_seleccionado: str, user_data: dict, supabase_client):
    """
    Dibuja el Informe Evolutivo consultando el histórico del usuario en Supabase.
    """
    if not supabase_client or not user_data.get('user_id'):
        ui.label('Error de sesión.').classes('text-red-500 m-8')
        return

    # 1. TRADUCTOR
    traductor = {
        'child_advocacy': 'Defensa del menor',
        'family_collaboration': 'Colaboración familiar',
        'diversity_sensitivity': 'Sensibilidad a la diversidad',
        'interdisciplinary_work': 'Trabajo interdisciplinar',
        'ethical_integrity': 'Integridad Ética',
        'emotional_regulation': 'Regulación Emocional'
    }

    username = user_data.get('username', 'Candidato')
    
    # --- EXTRACCIÓN DEL HISTÓRICO ---
    # Buscamos todas las evaluaciones de este usuario para este módulo específico
    # Usamos like para que "Psicología educativa - Competencias personales" encaje con "Competencias personales"
    historial = []
    try:
        res = supabase_client.table('evaluations').select('attempt_number, refined_metrics, created_at')\
            .eq('user_id', user_data['user_id'])\
            .ilike('sector_profile', f'%{grupo_seleccionado}%')\
            .order('attempt_number', desc=False).execute()
        historial = res.data
    except Exception as e:
        print(f"Error consultando histórico evolutivo: {e}")

    # --- PROCESADO DE DATOS EVOLUTIVOS ---
    # Queremos organizar los datos así: { "competencia_x": { 1: 50%, 2: 70%, 3: 85% } }
    datos_evolutivos = {}
    ultimo_intento = 0
    fecha_ultima = ""

    for record in historial:
        att_num = record.get('attempt_number')
        if not att_num: continue
        
        ultimo_intento = max(ultimo_intento, att_num)
        
        # Formateo de fecha
        raw_date = record.get('created_at', '')
        if raw_date:
            fecha_ultima = raw_date[:10] # Solo YYYY-MM-DD
            
        metrics = record.get('refined_metrics', {})
        if isinstance(metrics, str):
            try: metrics = json.loads(metrics)
            except: continue
            
        comps = metrics.get('competencies', metrics)
        
        for comp_id, info in comps.items():
            pct = info.get('percentage', 0) if isinstance(info, dict) else info
            if comp_id not in datos_evolutivos:
                datos_evolutivos[comp_id] = {}
            datos_evolutivos[comp_id][att_num] = pct

    # --- UI: RENDERIZADO DEL INFORME ---
    with ui.column().classes('w-full max-w-2xl mx-auto p-4 md:p-8 bg-[#0E1117] text-white min-h-screen animate-fade-in'):
        
        # CABECERA
        with ui.column().classes('w-full items-center mb-8 gap-4'):
            with ui.row().classes('bg-white rounded-2xl items-center justify-center p-4 w-48 h-32 shadow-lg'):
                ui.image('logo_original.png').classes('w-40 object-contain')
            
            ui.label('INFORME DE EVOLUCIÓN COMPETENCIAL').classes('text-[#83ABF1] font-black tracking-[.2em] text-xs mt-4 text-center')
            ui.label(username.upper()).classes('text-white text-2xl font-light italic')
            ui.label(f"Módulo: {grupo_seleccionado.upper()}").classes('text-gray-500 text-sm font-bold tracking-widest')
            
            if ultimo_intento > 0:
                ui.label(f"Mediciones registradas: {ultimo_intento}/3 (Última: {fecha_ultima})").classes('text-xs text-green-400 font-mono bg-green-900/20 px-3 py-1 rounded-full')

        # SECCIÓN DE COMPETENCIAS (Trazabilidad)
        if not datos_evolutivos:
            ui.label('No hay datos evolutivos registrados.').classes('text-red-400 text-center w-full')
        else:
            with ui.column().classes('w-full gap-8'):
                for comp_id, history_data in datos_evolutivos.items():
                    nombre_amigable = traductor.get(comp_id, str(comp_id).replace('_', ' ').title())
                    
                    # El valor actual es el de la pasación más alta registrada
                    pct_actual = history_data.get(ultimo_intento, 0)
                    color_actual = get_color_for_percentage(pct_actual)

                    # Tarjeta Evolutiva
                    with ui.card().classes('w-full bg-[#161B22] border border-gray-800 p-5 rounded-3xl shadow-xl overflow-hidden'):
                        # Cabecera de la tarjeta
                        with ui.row().classes('w-full justify-between items-center mb-4 border-b border-gray-800 pb-2'):
                            ui.label(nombre_amigable).classes('text-white font-bold text-lg')
                            ui.label(f"Actual: {pct_actual}%").classes('font-black text-xl').style(f'color: {color_actual};')

                        # Bloque Comparativo (Las 3 barras)
                        with ui.column().classes('w-full gap-3 mt-4'):
                            # Dibujamos las 3 posibles pasaciones
                            for att in [1, 2, 3]:
                                pct_historico = history_data.get(att)
                                
                                with ui.row().classes('w-full items-center gap-3'):
                                    # Etiqueta de la medición
                                    ui.label(f"Medición {att}").classes('text-[10px] text-gray-500 font-mono w-16')
                                    
                                    # Contenedor de la barra
                                    with ui.element('div').classes('flex-grow h-2 bg-gray-900 rounded-full overflow-hidden relative'):
                                        if pct_historico is not None:
                                            # Si hay dato, pintamos la barra
                                            color_hist = get_color_for_percentage(pct_historico)
                                            ancho = max(2, pct_historico) if pct_historico > 0 else 2
                                            # Destacamos la barra si es la medición actual (más opaca)
                                            opacidad = "1" if att == ultimo_intento else "0.5"
                                            ui.element('div').classes('h-full transition-all duration-1000').style(
                                                f'width: {ancho}%; background-color: {color_hist}; opacity: {opacidad};'
                                            )
                                        else:
                                            # Si no hay dato (aún no ha hecho esa pasación), mostramos hueco vacío
                                            ui.label("Pdte.").classes('text-[8px] text-gray-700 absolute inset-0 flex items-center justify-center')
                                            
                                    # Porcentaje al final de la barra
                                    lbl_pct = f"{pct_historico}%" if pct_historico is not None else "-"
                                    ui.label(lbl_pct).classes('text-[10px] text-gray-400 font-mono w-8 text-right')

        # CIERRE Y DESPEDIDA
        with ui.column().classes('w-full items-center mt-12 gap-6 pb-20'):
            ui.separator().classes('bg-gray-800 opacity-20 w-1/2')
            ui.label('Audeo Processor - Analítica de Talento Sostenible').classes('text-gray-500 text-xs text-center italic')
            
            ui.button('CERRAR INFORME', on_click=lambda: ui.navigate.to('/')).classes(
                'w-full max-w-xs bg-[#0D248D] text-white font-bold py-4 rounded-xl hover:scale-105 transition-all shadow-xl'
            )

# Estilo para animación suave
ui.add_head_html('''
    <style>
        .nicegui-content { padding: 0 !important; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .animate-fade-in { animation: fadeIn 0.8s ease-out forwards; }
    </style>
''')