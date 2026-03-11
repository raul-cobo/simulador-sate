from nicegui import ui

def render_dashboard_saiv(results: dict):
    """
    Renderiza el dashboard final con el hexágono RIASEC y el top de intereses.
    """
    metrics = results.get('metrics', {})
    riasec_code = results.get('riasec_code', '---')
    top_interests = results.get('top_interests', [])

    # Extraer los datos en orden para el gráfico radar
    # El orden tradicional RIASEC (adaptado a Audeo TCASEO)
    orden_letras = ['T', 'C', 'A', 'S', 'E', 'O']
    
    nombres_indicadores = []
    valores_porcentajes = []
    
    for letra in orden_letras:
        if letra in metrics:
            nombres_indicadores.append({'name': metrics[letra]['nombre'], 'max': 100})
            valores_porcentajes.append(metrics[letra]['percentage'])

    # Contenedor Principal
    with ui.column().classes('w-full items-center gap-8 p-8 min-h-[70vh] justify-center bg-[#0E1117]'):
        
        # Título
        with ui.column().classes('items-center gap-2'):
            ui.label('TU PERFIL VOCACIONAL').classes('text-3xl font-black text-[#83ABF1] tracking-tighter')
            ui.label('Modelo de Intereses RIASEC').classes('text-lg text-gray-400 font-semibold tracking-widest uppercase')
        
        # Layout dividido: Gráfico (Izquierda) | Resultados (Derecha)
        with ui.row().classes('w-full max-w-6xl justify-center gap-12 items-center flex-nowrap'):
            
            # --- IZQUIERDA: GRÁFICO DE RADAR ---
            with ui.card().classes('bg-[#161B22] p-6 rounded-2xl border border-gray-800 shadow-2xl'):
                ui.echart({
                    'tooltip': {},
                    'radar': {
                        'indicator': nombres_indicadores,
                        'splitArea': {
                            'areaStyle': {
                                'color': ['rgba(22, 27, 34, 0.8)', 'rgba(30, 36, 45, 0.8)']
                            }
                        },
                        'axisLine': {'lineStyle': {'color': 'rgba(255, 255, 255, 0.2)'}},
                        'splitLine': {'lineStyle': {'color': 'rgba(255, 255, 255, 0.2)'}},
                        'axisName': {'color': '#83ABF1', 'fontWeight': 'bold', 'fontSize': 12}
                    },
                    'series': [{
                        'name': 'Perfil RIASEC',
                        'type': 'radar',
                        'data': [{
                            'value': valores_porcentajes,
                            'name': 'Interés Vocacional',
                            'areaStyle': {'color': 'rgba(131, 171, 241, 0.4)'},
                            'lineStyle': {'color': '#83ABF1', 'width': 3},
                            'itemStyle': {'color': '#83ABF1'}
                        }]
                    }]
                }).classes('w-[500px] h-[450px]')

            # --- DERECHA: RESUMEN Y TOP 3 ---
            with ui.column().classes('flex-1 gap-6 w-[400px]'):
                
                # Caja del Código
                with ui.row().classes('w-full items-center justify-between bg-[#161B22] border border-[#83ABF1] p-6 rounded-2xl'):
                    ui.label('CÓDIGO DOMINANTE').classes('text-sm font-bold text-gray-400 tracking-widest')
                    ui.label(riasec_code).classes('text-4xl font-black text-[#83ABF1] tracking-widest')

                ui.label('ÁREAS DE MAYOR INTERÉS').classes('text-sm font-bold text-gray-500 uppercase tracking-widest mt-4')
                
                # Lista Top 3
                for idx, interest in enumerate(top_interests):
                    # El primero (Top 1) resalta más
                    is_top = (idx == 0)
                    border_color = 'border-[#83ABF1]' if is_top else 'border-gray-700'
                    text_color = 'text-white' if is_top else 'text-gray-300'
                    bg_color = 'bg-[#1a233a]' if is_top else 'bg-[#161B22]'
                    
                    with ui.row().classes(f'items-center gap-6 {bg_color} p-4 rounded-xl border-l-4 {border_color} w-full shadow-lg'):
                        ui.label(f"0{idx+1}").classes('text-2xl font-black text-[#83ABF1] opacity-80')
                        ui.label(interest).classes(f'text-lg font-bold {text_color}')