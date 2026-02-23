from nicegui import ui
from typing import Dict, Any
from logic_sape_refinery import SAPERefinery

# Diccionario para traducir las variables internas al español en el gráfico
DIMENSION_LABELS = {
    'achievement': 'Logro',
    'risk_propensity': 'Riesgo',
    'innovativeness': 'Innovación',
    'locus_control': 'Locus de Control',
    'self_efficacy': 'Autoeficacia',
    'autonomy': 'Autonomía',
    'ambiguity_tolerance': 'Tol. Incertidumbre',
    'emotional_stability': 'Estabilidad Emoc.'
}

def render_dashboard_resultados(refined_data: Dict[str, Any]):
    """
    Renderiza el Dashboard final del SAPE usando NiceGUI y Tailwind.
    Espera los datos procesados por logic_sape_refinery.py
    """
    with ui.column().classes('w-full max-w-5xl mx-auto p-6 bg-[#0E1117] min-h-screen text-white'):
        
        # --- CABECERA ---
        ui.label("Perfil Psicométrico SAPE").classes('text-3xl font-bold text-white mb-2')
        ui.label("Análisis de Competencias Emprendedoras y Estructura Latente").classes('text-gray-400 mb-8')

        # --- 1. SECCIÓN DE MACRO-CLÚSTERES (KPIs) ---
        with ui.row().classes('w-full gap-4 mb-8'):
            _render_kpi_card("Autoevaluación Central (CSE)", refined_data.get('cluster_cse', 0), "Resiliencia base")
            _render_kpi_card("Agencia Proactiva", refined_data.get('cluster_agency', 0), "Motor de ejecución")
            _render_kpi_card("Exploración Estratégica", refined_data.get('cluster_exploration', 0), "Adaptabilidad")

        # --- 2. EL OCTÓGONO Y LOS INSIGHTS CLINICOS ---
        with ui.row().classes('w-full items-stretch gap-6'):
            
            # Gráfico de Radar (Octógono) - Izquierda (60%)
            with ui.column().classes('w-full md:w-[60%] bg-[#161B22] border border-[#83ABF1]/30 rounded-xl p-6 shadow-lg'):
                ui.label("Octógono de Rasgos Nucleares").classes('text-xl font-semibold mb-4 text-[#83ABF1]')
                _render_octagon_chart(refined_data)

            # Insights y Flags - Derecha (40%)
            with ui.column().classes('w-full md:flex-1 bg-[#161B22] border border-[#83ABF1]/30 rounded-xl p-6 shadow-lg'):
                ui.label("Insights Clínicos").classes('text-xl font-semibold mb-4 text-[#83ABF1]')
                
                flags = SAPERefinery.get_clinical_flags(refined_data)
                
                if flags:
                    for flag in flags:
                        # Estilos dinámicos: Rojo para alertas, Azul/Verde para positivos
                        is_alert = "Burnout" in flag
                        bg_color = "bg-red-900/20" if is_alert else "bg-[#83ABF1]/10"
                        border_color = "border-red-500/50" if is_alert else "border-[#83ABF1]/50"
                        icon = "warning" if is_alert else "psychology"
                        icon_color = "text-red-400" if is_alert else "text-[#83ABF1]"
                        
                        with ui.row().classes(f'w-full items-start p-4 mb-3 rounded-lg border {border_color} {bg_color}'):
                            ui.icon(icon).classes(f'{icon_color} text-2xl mr-3 mt-1')
                            ui.label(flag).classes('text-sm text-gray-200 leading-relaxed flex-1')
                else:
                    ui.label("Perfil equilibrado. No se detectaron descarriladores ni alertas críticas bajo presión.").classes('text-gray-400 italic text-sm')

        # --- BOTÓN DE ACCIÓN ---
        with ui.row().classes('w-full justify-end mt-8'):
            ui.button("Descargar Reporte (PDF)", icon="picture_as_pdf").classes(
                'bg-[#83ABF1] hover:bg-[#5b8deb] text-[#0E1117] font-bold px-6 py-3 rounded-lg'
            )

# --- FUNCIONES AUXILIARES DE RENDERIZADO ---

def _render_kpi_card(title: str, value: float, subtitle: str):
    """Renderiza una tarjeta para los clústeres macro."""
    with ui.column().classes('flex-1 bg-[#161B22] border border-[#83ABF1]/50 rounded-xl p-5 items-center justify-center text-center shadow-md'):
        ui.label(title).classes('text-sm text-gray-400 font-medium uppercase tracking-wider mb-1')
        ui.label(f"{value:.1f}").classes('text-4xl font-black text-white mb-1')
        ui.label(subtitle).classes('text-xs text-[#83ABF1]')

def _render_octagon_chart(data: Dict[str, Any]):
    """Configura e inyecta el gráfico de ECharts."""
    
    # Extraer los 8 valores en el orden del diccionario DIMENSION_LABELS
    valores = [data.get(key, 50.0) for key in DIMENSION_LABELS.keys()]
    nombres = list(DIMENSION_LABELS.values())
    
    # Construcción de los indicadores para ECharts (max 100)
    indicadores = [{"name": nombre, "max": 100} for nombre in nombres]

    # Configuración JSON pura de ECharts adaptada al Dark Mode de Audeo
    chart_options = {
        "backgroundColor": "transparent",
        "tooltip": {},
        "radar": {
            "indicator": indicadores,
            "shape": "polygon", # Octógono literal
            "splitNumber": 5,
            "axisName": {
                "color": "#E0E0E0",
                "fontSize": 12,
                "fontWeight": "bold"
            },
            "splitLine": {
                "lineStyle": {
                    "color": ["rgba(131, 171, 241, 0.1)", "rgba(131, 171, 241, 0.2)", "rgba(131, 171, 241, 0.3)", "rgba(131, 171, 241, 0.4)", "rgba(131, 171, 241, 0.5)"]
                }
            },
            "splitArea": {
                "show": False
            },
            "axisLine": {
                "lineStyle": {
                    "color": "rgba(255, 255, 255, 0.2)"
                }
            }
        },
        "series": [{
            "type": "radar",
            "data": [
                {
                    "value": valores,
                    "name": "Perfil del Candidato",
                    "itemStyle": {
                        "color": "#83ABF1"
                    },
                    "areaStyle": {
                        "color": "rgba(131, 171, 241, 0.3)" # Transparencia azulada
                    },
                    "lineStyle": {
                        "width": 2,
                        "color": "#83ABF1"
                    }
                }
            ]
        }]
    }

    ui.echarts(chart_options).classes('w-full h-80')