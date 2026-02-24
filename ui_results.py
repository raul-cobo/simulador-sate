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

def render_dashboard_resultados(refined_data: Dict[str, Any]):
    with ui.column().classes('w-full max-w-5xl mx-auto p-6 bg-[#0E1117] text-white'):
        
        # CABECERA
        with ui.row().classes('w-full justify-between items-center mb-10'):
            with ui.row().classes('bg-white rounded-xl items-center justify-center').style('width: 265px; height: 189px; padding: 20px; box-sizing: border-box;'):
                ui.image('logo_original.png').style('max-width: 100%; max-height: 100%; object-fit: contain;')
                
            with ui.column().classes('items-end'):
                ui.label("Perfil Psicométrico S.A.P.E.").classes('text-white font-bold text-[18px]')
                ui.label("Sistema de Análisis de la Personalidad Emprendedora").classes('text-white text-[14px]').style('margin-top: 4px;')

        # BLOQUE 1: KPIs
        with ui.row().classes('w-full flex-wrap justify-center gap-6 mb-10'):
            _render_caja_kpi("Índice de Resiliencia (IRE)", f"{refined_data.get('ire', 0)}", "Capacidad de Resiliencia durante las decisiones críticas de un emprendimiento")
            f_def = refined_data.get('friccion_defecto', 0)
            f_exc = refined_data.get('friccion_exceso', 0)
            _render_caja_kpi("Fricción (Defecto/Exceso)", f"-{f_def} / +{f_exc}", "Índice de rasgos que interfieren en el emprendimiento")
            _render_caja_kpi("Delta", f"{refined_data.get('delta', 0)}", "Desviación del perfil óptimo")

        # BLOQUE 2: Gráfica y Rasgos
        with ui.row().classes('w-full items-stretch gap-8 mb-10 flex-nowrap'):
            with ui.column().classes('w-3/5 bg-[#161B22] border border-[#83ABF1]/30 rounded-xl p-4 shadow-lg justify-center'):
                _render_octagon_chart(refined_data)

            with ui.column().classes('w-2/5 bg-[#161B22] border border-[#83ABF1]/30 rounded-xl p-8 shadow-lg justify-center'):
                for key, nombre in DIMENSION_LABELS.items():
                    val = refined_data.get(key, 50.0)
                    with ui.row().classes('w-full justify-between items-center mb-4 border-b border-gray-700 pb-1'):
                        ui.label(nombre).classes('text-white font-bold text-[14px]')
                        ui.label(f"{val}%").classes('text-white text-[14px]')

        # BLOQUE 3: Nociones
        with ui.column().classes('w-full bg-[#161B22] border border-[#83ABF1]/30 rounded-xl p-8 shadow-lg mb-8'):
            ui.label("Nociones y Recomendaciones").classes('text-white font-bold text-[16px] mb-4 border-b border-[#83ABF1] pb-2 w-full')
            
            flags = SAPERefinery.get_clinical_flags(refined_data)
            if flags:
                for flag in flags:
                    ui.label(f"• {flag}").classes('text-white text-[12px] mb-2 leading-relaxed')
            else:
                ui.label("• Perfil equilibrado. No se detectan patrones de riesgo inminente.").classes('text-white text-[12px] italic')

def _render_caja_kpi(titulo, valor, desc):
    with ui.column().classes('bg-[#161B22] border border-[#83ABF1] rounded-xl p-6 items-center justify-center text-center shadow-lg').style('width: 280px; height: 280px;'):
        ui.label(titulo).classes('text-[#83ABF1] text-[14px] font-bold mb-4')
        ui.label(str(valor)).classes('text-white text-[18px] font-black mb-4')
        ui.label(desc).classes('text-[#83ABF1] text-[12px]')
        
def _render_octagon_chart(data: Dict[str, Any]):
    valores = [data.get(key, 50.0) for key in DIMENSION_LABELS.keys()]
    indicadores = [{"name": n, "max": 100} for n in list(DIMENSION_LABELS.values())]

    # Dividimos en 20 tramos de 5% cada uno para ajustar al píxel las fronteras clínicas
    colores_area = (
        ["rgba(200, 50, 50, 0.4)"] * 5 +    # 0% - 25% (Rojo)
        ["rgba(230, 190, 50, 0.4)"] * 9 +   # 26% - 70% (Amarillo)
        ["rgba(50, 160, 80, 0.4)"] * 4 +    # 71% - 90% (Verde)
        ["rgba(200, 50, 50, 0.4)"] * 2      # 91% - 100% (Rojo)
    )

    chart_options = {
        "backgroundColor": "transparent",
        "tooltip": {},
        "radar": {
            "indicator": indicadores,
            "shape": "polygon",
            "splitNumber": 20, # Cambiado a 20 para precisión absoluta
            "axisName": {"color": "#FFFFFF", "fontSize": 12, "fontWeight": "bold"},
            "splitArea": {
                "show": True,
                "areaStyle": {
                    "color": colores_area
                }
            },
            "axisLine": {"lineStyle": {"color": "rgba(255, 255, 255, 0.3)"}},
            "splitLine": {"lineStyle": {"color": "rgba(255, 255, 255, 0.05)"}} # Líneas sutiles
        },
        "series": [{
            "type": "radar",
            "data": [{
                "value": valores,
                "name": "Puntuaciones",
                "itemStyle": {"color": "#FFFFFF"},
                "lineStyle": {"width": 3, "color": "#FFFFFF"},
                "label": {"show": True, "color": "#FFFFFF", "fontSize": 12, "formatter": "{c}"}
            }]
        }]
    }
    
    try:
        ui.echarts(chart_options).classes('w-full').style('height: 450px;')
    except Exception as e:
        ui.label(f"Error gráfico interno: {e}").classes('text-red-500')