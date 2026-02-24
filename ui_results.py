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
    # CORTAFUEGOS: Si la versión de NiceGUI es antigua, mostramos un aviso sin romper la web
    if not hasattr(ui, 'echarts'):
        with ui.column().classes('w-full h-full items-center justify-center p-8 text-center bg-red-900/20 border border-red-500/50 rounded-xl'):
            ui.icon('warning', size='3rem', color='red')
            ui.label('⚠️ VERSIÓN DEL SERVIDOR OBSOLETA').classes('text-red-400 font-bold text-lg mt-2')
            ui.label('Para ver la gráfica de araña, necesitas actualizar la versión de NiceGUI.').classes('text-white text-sm')
            ui.label("Escribe 'nicegui>=1.4.0' en tu archivo requirements.txt").classes('text-gray-400 text-xs mt-2')
        return

    valores = [data.get(key, 50.0) for key in DIMENSION_LABELS.keys()]
    indicadores = [{"name": n, "max": 100} for n in list(DIMENSION_LABELS.values())]

    chart_options = {
        "backgroundColor": "transparent",
        "tooltip": {},
        "radar": {
            "indicator": indicadores,
            "shape": "polygon",
            "splitNumber": 10,
            "axisName": {"color": "#FFFFFF", "fontSize": 12, "fontWeight": "bold"},
            "splitArea": {
                "show": True,
                "areaStyle": {
                    "color": [
                        "rgba(200, 50, 50, 0.4)", "rgba(200, 50, 50, 0.4)", "rgba(200, 50, 50, 0.4)", # 0-30 Rojo
                        "rgba(230, 190, 50, 0.4)", "rgba(230, 190, 50, 0.4)", "rgba(230, 190, 50, 0.4)", "rgba(230, 190, 50, 0.4)", # 30-70 Amar
                        "rgba(50, 160, 80, 0.4)", "rgba(50, 160, 80, 0.4)", # 70-90 Verde
                        "rgba(200, 50, 50, 0.4)" # 90-100 Rojo
                    ]
                }
            },
            "axisLine": {"lineStyle": {"color": "rgba(255, 255, 255, 0.3)"}},
            "splitLine": {"lineStyle": {"color": "rgba(255, 255, 255, 0.1)"}}
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