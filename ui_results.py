from nicegui import ui
from typing import Dict, Any
from logic_sape_refinery import SAPERefinery

# Diccionario para traducir las variables internas al español
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

def render_dashboard_resultados(refined_data: Dict[str, Any]):
    """
    Renderiza el Dashboard final del SAPE siguiendo el Documento Maestro Audeo.
    """
    with ui.column().classes('w-full max-w-5xl mx-auto p-6 bg-[#0E1117] min-h-screen text-white'):
        
        # ==========================================================
        # CABECERA
        # ==========================================================
        with ui.row().classes('w-full justify-between items-center mb-8'):
            # Izquierda: Logo en recuadro blanco
            with ui.column().classes('bg-white rounded-xl p-3 justify-center items-center w-32 h-16'):
                ui.image('audeo_original.png').classes('w-full h-auto max-h-full object-contain')
                
            # Derecha: Títulos
            with ui.column().classes('items-end justify-center'):
                ui.label("Perfil Psicométrico S.A.P.E.").classes('text-white text-[14px] font-bold')
                ui.label("Sistema de Análisis de la Personalidad Emprendedora").classes('text-white text-[14px] mt-[4px]')

        # ==========================================================
        # BLOQUE 1: MACRO-MÉTRICAS (Cajas Cuadradas)
        # ==========================================================
        with ui.row().classes('w-full grid grid-cols-1 md:grid-cols-3 gap-6 mb-8'):
            
            # Caja 1: IRE
            with ui.column().classes('bg-[#161B22] border border-[#83ABF1] rounded-xl p-4 aspect-square justify-center items-center text-center shadow-lg'):
                ui.label("Índice de Resiliencia (IRE)").classes('text-[#83ABF1] text-[14px] font-bold mb-2')
                ui.label(f"{refined_data.get('ire', 0)}%").classes('text-white text-[18px] font-black mb-2')
                ui.label("Capacidad de Resiliencia durante las decisiones críticas de un emprendimiento").classes('text-[#83ABF1] text-[12px]')
            
            # Caja 2: Fricción
            with ui.column().classes('bg-[#161B22] border border-[#83ABF1] rounded-xl p-4 aspect-square justify-center items-center text-center shadow-lg'):
                friccion_str = f"-{refined_data.get('friccion_defecto', 0)} / +{refined_data.get('friccion_exceso', 0)}"
                ui.label("Fricción (Defecto/Exceso)").classes('text-[#83ABF1] text-[14px] font-bold mb-2')
                ui.label(friccion_str).classes('text-white text-[18px] font-black mb-2')
                ui.label("Índice de rasgos que interfieren en el emprendimiento").classes('text-[#83ABF1] text-[12px]')
            
            # Caja 3: Delta
            with ui.column().classes('bg-[#161B22] border border-[#83ABF1] rounded-xl p-4 aspect-square justify-center items-center text-center shadow-lg'):
                ui.label("Delta").classes('text-[#83ABF1] text-[14px] font-bold mb-2')
                ui.label(f"{refined_data.get('delta', 0)}").classes('text-white text-[18px] font-black mb-2')
                ui.label("Desviación del perfil óptimo").classes('text-[#83ABF1] text-[12px]')

        # ==========================================================
        # BLOQUE 2: OCTÓGONO Y PUNTUACIONES DETALLADAS
        # ==========================================================
        with ui.row().classes('w-full items-stretch gap-8 mb-8'):
            
            # Izquierda: Gráfico de Radar (Octógono) - Aprox 60% ancho
            with ui.column().classes('w-full md:w-[60%] bg-[#161B22] border border-[#83ABF1]/30 rounded-xl p-4 shadow-lg justify-center'):
                _render_octagon_chart(refined_data)

            # Derecha: Lista de Puntuaciones - Aprox 40% ancho
            with ui.column().classes('w-full md:flex-1 bg-[#161B22] border border-[#83ABF1]/30 rounded-xl p-6 shadow-lg justify-center'):
                for key, nombre_es in DIMENSION_LABELS.items():
                    valor = refined_data.get(key, 50.0)
                    with ui.row().classes('w-full justify-between items-center mb-3 border-b border-gray-700 pb-1'):
                        ui.label(nombre_es).classes('text-white text-[14px] font-bold')
                        ui.label(f"{valor}%").classes('text-white text-[14px] font-bold')

        # ==========================================================
        # BLOQUE 3: NOCIONES Y RECOMENDACIONES
        # ==========================================================
        with ui.column().classes('w-full bg-[#161B22] border border-[#83ABF1]/30 rounded-xl p-6 shadow-lg mb-4'):
            ui.label("Diagnóstico y Recomendaciones Clínicas").classes('text-white text-[14px] font-bold mb-4 border-b border-[#83ABF1] pb-2')
            
            # Extraemos las banderas de nuestro motor de refinamiento
            flags = SAPERefinery.get_clinical_flags(refined_data)
            
            if flags:
                for flag in flags:
                    ui.label(f"• {flag}").classes('text-white text-[12px] mb-2 leading-relaxed')
            else:
                ui.label("• Perfil equilibrado. No se detectan patrones de riesgo inminente ni descarriladores críticos que requieran intervención.").classes('text-white text-[12px] italic')
            
            # Recomendación base usando Delta
            delta = refined_data.get('delta', 0)
            if delta > 20:
                ui.label(f"• El Delta actual ({delta}) sugiere que el perfil requiere ajustes estructurales. Se recomienda descargar el informe técnico para auditar las áreas de desarrollo.").classes('text-white text-[12px] mt-2')
            else:
                ui.label("• El perfil se encuentra dentro de los márgenes de viabilidad técnica.").classes('text-white text-[12px] mt-2')

# --- FUNCIONES AUXILIARES DE RENDERIZADO ---

def _render_octagon_chart(data: Dict[str, Any]):
    """Configura e inyecta el gráfico de ECharts con las zonas de color."""
    
    valores = [data.get(key, 50.0) for key in DIMENSION_LABELS.keys()]
    nombres = list(DIMENSION_LABELS.values())
    
    indicadores = [{"name": nombre, "max": 100} for nombre in nombres]

    chart_options = {
        "backgroundColor": "transparent",
        "tooltip": {},
        "radar": {
            "indicator": indicadores,
            "shape": "polygon",
            "splitNumber": 5, # Divide en 5 anillos (20, 40, 60, 80, 100)
            "axisName": {
                "color": "#FFFFFF", # Letras en blanco
                "fontSize": 12,
                "fontWeight": "bold"
            },
            "splitArea": {
                "show": True,
                "areaStyle": {
                    # Aproximación visual a tus rangos: 0-25 (Rojo), 26-70 (Amar), 71-90 (Verde), 91-100 (Rojo)
                    "color": [
                        "rgba(200, 50, 50, 0.2)",    # Anillo interior (aprox 0-20) ROJO
                        "rgba(230, 190, 50, 0.2)",   # Anillo 2 (aprox 20-40) AMARILLO
                        "rgba(230, 190, 50, 0.2)",   # Anillo 3 (aprox 40-60) AMARILLO
                        "rgba(50, 160, 80, 0.2)",    # Anillo 4 (aprox 60-80) VERDE
                        "rgba(200, 50, 50, 0.2)"     # Anillo exterior (aprox 80-100) ROJO
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
            "data": [
                {
                    "value": valores,
                    "name": "Puntuaciones",
                    "itemStyle": {
                        "color": "#FFFFFF" # Puntos en blanco
                    },
                    "lineStyle": {
                        "width": 3,
                        "color": "#FFFFFF" # Línea principal en blanco
                    },
                    "label": {
                        "show": True,
                        "color": "#FFFFFF", # Números en blanco
                        "fontSize": 12,
                        "formatter": "{c}"
                    }
                }
            ]
        }]
    }

    ui.echarts(chart_options).classes('w-full h-96')