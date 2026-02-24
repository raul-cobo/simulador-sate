from nicegui import ui
from typing import Dict, Any
from logic_sape_refinery import SAPERefinery

DIMENSION_LABELS = {
    'achievement': 'Necesidad de Logro',
    'risk_propensity': 'Propensión al Riesgo',
    'innovativeness': 'Innovatividad',
    'locus_control': 'Locus de Control Interno',
    'self_efficacy': 'Autoeficacia',
    'autonomy': 'Autonomía',
    'ambiguity_tolerance': 'Tol. Ambigüedad',
    'emotional_stability': 'Estabilidad Emocional'
}

def render_dashboard_resultados(refined_data: Dict[str, Any], callback_pdf=None):
    with ui.column().classes('w-full max-w-5xl mx-auto p-6 bg-[#0E1117] min-h-screen text-white'):
        
        # ==========================================================
        # CABECERA
        # ==========================================================
        with ui.row().classes('w-full justify-between items-start mb-10'):
            # Izquierda: Logo tamaño 7x5 cm (aprox 265px x 189px)
            with ui.column().classes('bg-white rounded-xl items-center justify-center').style('width: 7cm; height: 5cm; overflow: hidden;'):
                ui.image('audeo_original.png').style('width: 100%; height: 100%; object-fit: contain; padding: 10px;')
                
            # Derecha: Títulos
            with ui.column().classes('items-end justify-start pt-4'):
                ui.label("Perfil Psicométrico S.A.P.E.").classes('text-white font-bold text-[18px]')
                ui.label("Sistema de Análisis de la Personalidad Emprendedora").classes('text-white text-[14px]').style('margin-top: 0.5rem;')

        # ==========================================================
        # BLOQUE 1: Cajas Cuadradas
        # ==========================================================
        with ui.row().classes('w-full flex-wrap justify-center gap-6 mb-10'):
            _render_caja_kpi("Índice de Resiliencia (IRE)", f"{refined_data.get('ire', 0)}", "Capacidad de Resiliencia durante las decisiones críticas de un emprendimiento")
            
            f_def = refined_data.get('friccion_defecto', 0)
            f_exc = refined_data.get('friccion_exceso', 0)
            _render_caja_kpi("Fricción (Defecto/Exceso)", f"-{f_def} / +{f_exc}", "Índice de rasgos que interfieren en el emprendimiento")
            
            _render_caja_kpi("Delta", f"{refined_data.get('delta', 0)}", "Desviación del perfil óptimo")

        # ==========================================================
        # BLOQUE 2: Gráfica de Araña y Rasgos
        # ==========================================================
        with ui.row().classes('w-full items-stretch gap-6 mb-10'):
            # Izquierda: Gráfica
            with ui.column().classes('flex-grow w-full md:w-7/12 bg-[#161B22] rounded-xl p-4 justify-center items-center'):
                _render_octagon_chart(refined_data)

            # Derecha: Lista de Rasgos
            with ui.column().classes('flex-grow w-full md:w-4/12 bg-[#161B22] rounded-xl p-8 justify-center'):
                for key, nombre in DIMENSION_LABELS.items():
                    val = refined_data.get(key, 50.0)
                    with ui.row().classes('w-full justify-between items-center mb-4'):
                        ui.label(nombre).classes('text-white font-bold text-[14px]')
                        ui.label(f"{val}%").classes('text-white text-[14px]')

        # ==========================================================
        # BLOQUE 3: Nociones, Recomendaciones y Botón
        # ==========================================================
        with ui.column().classes('w-full bg-[#161B22] rounded-xl p-8'):
            ui.label("Nociones y Recomendaciones").classes('text-white font-bold text-[16px] mb-4 border-b border-gray-600 pb-2 w-full')
            
            flags = SAPERefinery.get_clinical_flags(refined_data)
            if flags:
                for flag in flags:
                    ui.label(f"• {flag}").classes('text-white text-[12px] mb-2')
            else:
                ui.label("• Perfil equilibrado. No se detectan patrones de riesgo inminente.").classes('text-white text-[12px]')
            
            # BOTÓN DE DESCARGA
            if callback_pdf:
                with ui.row().classes('w-full justify-end mt-8'):
                    ui.button('DESCARGAR INFORME PDF', on_click=callback_pdf).classes(
                        'bg-[#0D248D] hover:bg-[#1534b5] text-white font-bold py-4 px-8 rounded-lg cursor-pointer transition-colors shadow-lg'
                    ).props('icon=picture_as_pdf')

def _render_caja_kpi(titulo, valor, desc):
    """Renderiza las cajas cuadradas del Bloque 1"""
    with ui.column().classes('bg-[#161B22] border border-[#83ABF1] rounded-xl p-6 items-center justify-center text-center').style('width: 280px; height: 280px;'):
        ui.label(titulo).classes('text-[#83ABF1] text-[14px] font-bold mb-4')
        ui.label(str(valor)).classes('text-white text-[18px] font-black mb-4')
        ui.label(desc).classes('text-[#83ABF1] text-[12px]')
        
def _render_octagon_chart(data: Dict[str, Any]):
    """Configura el gráfico ECharts en 10 anillos para pintar los colores exactos"""
    valores = [data.get(key, 50.0) for key in DIMENSION_LABELS.keys()]
    nombres = list(DIMENSION_LABELS.values())
    indicadores = [{"name": n, "max": 100} for n in nombres]

    chart_options = {
        "backgroundColor": "transparent",
        "tooltip": {},
        "radar": {
            "indicator": indicadores,
            "shape": "polygon",
            "splitNumber": 10,  # 10 anillos (de 10% cada uno) para poder clavar los colores
            "axisName": {
                "color": "#FFFFFF",
                "fontSize": 12,
                "fontWeight": "bold"
            },
            "splitArea": {
                "show": True,
                "areaStyle": {
                    "color": [
                        "rgba(200, 50, 50, 0.5)",  # 0-10% (Rojo)
                        "rgba(200, 50, 50, 0.5)",  # 10-20% (Rojo)
                        "rgba(200, 50, 50, 0.5)",  # 20-30% (Rojo - cubre hasta el 25%)
                        "rgba(230, 190, 50, 0.5)", # 30-40% (Amarillo)
                        "rgba(230, 190, 50, 0.5)", # 40-50% (Amarillo)
                        "rgba(230, 190, 50, 0.5)", # 50-60% (Amarillo)
                        "rgba(230, 190, 50, 0.5)", # 60-70% (Amarillo)
                        "rgba(50, 160, 80, 0.5)",  # 70-80% (Verde)
                        "rgba(50, 160, 80, 0.5)",  # 80-90% (Verde)
                        "rgba(200, 50, 50, 0.5)"   # 90-100% (Rojo)
                    ]
                }
            },
            "axisLine": {
                "lineStyle": {
                    "color": "rgba(255, 255, 255, 0.3)"
                }
            },
            "splitLine": {
                "lineStyle": {
                    "color": "rgba(255, 255, 255, 0.1)"
                }
            }
        },
        "series": [{
            "type": "radar",
            "data": [{
                "value": valores,
                "name": "Puntuaciones",
                "itemStyle": {"color": "#FFFFFF"},
                "lineStyle": {"width": 3, "color": "#FFFFFF"},
                "label": {
                    "show": True,
                    "color": "#FFFFFF",
                    "fontSize": 12,
                    "formatter": "{c}"
                }
            }]
        }]
    }
    
    # Altura fija para asegurar que se dibuje siempre
    ui.echarts(chart_options).classes('w-full h-[450px]')