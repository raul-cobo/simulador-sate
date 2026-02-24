from nicegui import ui
import plotly.graph_objects as go
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
    with ui.column().classes('w-full max-w-5xl mx-auto p-6 bg-[#0E1117] min-h-screen text-white'):
        
        # CABECERA
        with ui.row().classes('w-full justify-between items-center mb-10'):
            # Caja blanca con centrado forzado para el logo
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
                _render_octagon_plotly(refined_data)

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
        
def _render_octagon_plotly(data: Dict[str, Any]):
    valores = [data.get(key, 50.0) for key in DIMENSION_LABELS.keys()]
    nombres = list(DIMENSION_LABELS.values())
    
    # Cerramos el polígono para que la línea conecte el último punto con el primero
    valores.append(valores[0])
    nombres.append(nombres[0])
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=valores,
        theta=nombres,
        fill='toself',
        fillcolor='rgba(131, 171, 241, 0.4)',
        line=dict(color='#83ABF1', width=3),
        name='Perfil'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], gridcolor='rgba(255, 255, 255, 0.2)', linecolor='rgba(255, 255, 255, 0.2)', tickfont=dict(color='rgba(255, 255, 255, 0.5)')),
            angularaxis=dict(gridcolor='rgba(255, 255, 255, 0.2)', linecolor='rgba(255, 255, 255, 0.2)', tickfont=dict(color='#FFFFFF', size=11)),
            bgcolor='transparent'
        ),
        showlegend=False,
        paper_bgcolor='transparent',
        plot_bgcolor='transparent',
        margin=dict(l=30, r=30, t=30, b=30),
        height=450
    )
    ui.plotly(fig).classes('w-full').style('height: 450px;')