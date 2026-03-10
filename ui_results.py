from nicegui import ui
import plotly.graph_objects as go
from typing import Dict, Any
from logic_sape_refinery import SAPERefinery

DIMENSION_LABELS = {
    'achievement': 'Logro',
    'risk_propensity': 'Riesgo',
    'innovativeness': 'Innovación',
    'locus_control': 'Locus Control',
    'self_efficacy': 'Autoeficacia',
    'autonomy': 'Autonomía',
    'ambiguity_tolerance': 'Incertidumbre',
    'emotional_stability': 'Estabilidad'
}

def render_dashboard_resultados(refined_data: Dict[str, Any]):
    with ui.column().classes('w-full max-w-5xl mx-auto p-6 bg-[#0E1117] text-white'):
        
        # CABECERA
        with ui.row().classes('w-full justify-between items-center mb-10'):
            with ui.row().classes('bg-white rounded-xl items-center justify-center p-4').style('width: 265px; height: 180px;'):
                ui.image('logo_original.png').style('max-width: 100%; max-height: 100%; object-fit: contain;')
                
            with ui.column().classes('items-end'):
                ui.label("Perfil Psicométrico S.A.P.E.").classes('text-white font-bold text-[18px]')
                ui.label("Sistema de Análisis de la Personalidad Emprendedora").classes('text-white text-[14px]')

        # BLOQUE 1: KPIs (AHORA SON 4 CAJAS)
        with ui.row().classes('w-full flex-wrap justify-center gap-4 mb-10'):
            # Añadido el Potencial Emprendedor como métrica principal
            _render_caja_kpi("Potencial", f"{refined_data.get('potencial', 0)}", "Alineación con el perfil de éxito")
            _render_caja_kpi("Índice Resiliencia (IRE)", f"{refined_data.get('ire', 0)}", "Capacidad de respuesta ante crisis")
            
            # Fricción unificada para mayor claridad visual
            _render_caja_kpi("Fricción", f"{refined_data.get('friccion', 0)}", "Interferencias en el desempeño")
            _render_caja_kpi("Delta", f"{refined_data.get('delta', 0)}", "Desviación del perfil ideal")

        # BLOQUE 2: Gráfica Octogonal (AHORA CON PLOTLY)
        with ui.row().classes('w-full items-stretch gap-8 mb-10 flex-nowrap'):
            with ui.column().classes('w-3/5 bg-[#161B22] border border-[#83ABF1]/30 rounded-xl p-4 shadow-lg'):
                _render_plotly_radar(refined_data)

            with ui.column().classes('w-2/5 bg-[#161B22] border border-[#83ABF1]/30 rounded-xl p-8 shadow-lg justify-center'):
                for key, nombre in DIMENSION_LABELS.items():
                    val = refined_data.get(key, 50.0)
                    with ui.row().classes('w-full justify-between items-center mb-4 border-b border-gray-700 pb-1'):
                        ui.label(nombre).classes('text-white font-bold text-[14px]')
                        ui.label(f"{val}%").classes('text-white text-[14px]')

        # BLOQUE 3: Nociones
        with ui.column().classes('w-full bg-[#161B22] border border-[#83ABF1]/30 rounded-xl p-8 shadow-lg mb-8'):
            ui.label("Nociones y Recomendaciones").classes('text-[#83ABF1] font-bold text-[16px] mb-4 border-b border-[#83ABF1]/30 pb-2 w-full')
            flags = SAPERefinery.get_clinical_flags(refined_data)
            if flags:
                for flag in flags:
                    ui.label(f"• {flag}").classes('text-white text-[12px] mb-2')
            else:
                ui.label("• Perfil equilibrado. No se detectan descarriladores graves.").classes('text-white text-[12px] italic')

def _render_caja_kpi(titulo, valor, desc):
    # Reducido el ancho a 230px para que quepan las 4 cajas en línea sin romper el diseño
    with ui.column().classes('bg-[#161B22] border border-[#83ABF1] rounded-xl p-4 items-center justify-center text-center shadow-lg').style('width: 230px; height: 230px;'):
        ui.label(titulo).classes('text-[#83ABF1] text-[14px] font-bold mb-4')
        ui.label(str(valor)).classes('text-white text-[32px] font-black mb-4') # Aumentado el tamaño del número
        ui.label(desc).classes('text-gray-400 text-[11px]')

def _render_plotly_radar(data: Dict[str, Any]):
    # Preparamos los datos
    categories = list(DIMENSION_LABELS.values())
    values = [data.get(k, 50.0) for k in DIMENSION_LABELS.keys()]
    
    # Cerramos el círculo de la gráfica
    categories += [categories[0]]
    values += [values[0]]

    fig = go.Figure()

    # Añadimos la traza del perfil
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name='Perfil',
        line=dict(color='#FFFFFF', width=3),
        fillcolor='rgba(131, 171, 241, 0.5)', # Color #83ABF1 con opacidad
        marker=dict(color='#FFFFFF', size=8)
    ))

    # Configuración estética corporativa Audeo
    fig.update_layout(
        polar=dict(
            bgcolor="#161B22",
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(color="white", size=10),
                gridcolor="rgba(131, 171, 241, 0.2)",
                linecolor="rgba(131, 171, 241, 0.2)"
            ),
            angularaxis=dict(
                tickfont=dict(color="white", size=12, family="Arial Black"),
                gridcolor="rgba(131, 171, 241, 0.2)",
                linecolor="rgba(131, 171, 241, 0.2)"
            )
        ),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)", # Transparente para que luzca el fondo de NiceGUI
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=60, r=60, t=40, b=40),
        height=450
    )

    # Renderizado con ui.plotly (Mucho más estable que echarts)
    ui.plotly(fig).classes('w-full')