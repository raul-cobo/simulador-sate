# ui_results_sapp.py
from nicegui import ui
from typing import Dict, Any

# Mapeo de IDs técnicos a nombres legibles según Documento Maestro
SAPP_LABELS = {
    # Competencias Personales
    "ethical_integrity": "Ética e Integridad",
    "strategic_vision": "Visión Estratégica",
    "influence_negotiation": "Influencia y Negociación",
    "adaptability": "Adaptabilidad Organizacional",
    "professionalism": "Profesionalismo",
    "therapeutic_alliance": "Alianza Terapéutica",
    "reflective_practice": "Práctica Reflexiva",
    "child_advocacy": "Defensa del Menor",
    "family_collaboration": "Colaboración Familiar",
    "interdisciplinary_work": "Trabajo Interdisciplinar",
    "diversity_sensitivity": "Sensibilidad a la Diversidad",
    "resilience_selfcare": "Resiliencia y Autocuidado",
    "social_justice_ethics": "Justicia Social y Ética",
    "political_skills": "Habilidades Políticas",
    
    # Competencias Profesionales
    "selection_evaluation": "Selección y Evaluación",
    "organizational_development": "Desarrollo Organizacional",
    "performance_management": "Gestión del Desempeño",
    "occupational_health": "Salud Ocupacional",
    "psychoeducational_assessment": "Evaluación Psicoeducativa",
    "intervention_design": "Diseño de Intervención",
    "vocational_guidance": "Orientación Vocacional",
    "curricular_adaptation": "Adaptación Curricular",
    "crisis_intervention": "Intervención en Crisis",
    "program_evaluation": "Evaluación de Programas",
    "community_engagement": "Dinamización Comunitaria",
    "mediation_conflict": "Mediación de Conflictos",
    "case_formulation": "Formulación de Casos",
    "differential_diagnosis": "Diagnóstico Diferencial",
    "evidence_based_treatment": "Tratamiento basado en Evidencia",
    "risk_management": "Gestión de Riesgos",
    
    # Competencias Técnicas
    "people_analytics": "People Analytics",
    "psychometrics": "Psicometría",
    "hr_technology": "Tecnología de RRHH",
    "legal_compliance": "Normativa Legal",
    "standardized_instruments": "Instrumentos Estandarizados",
    "educational_platforms": "Plataformas Educativas",
    "telepractice": "Telepráctica",
    "technical_reports": "Redacción de Informes",
    "grant_management": "Gestión de Subvenciones",
    "qualitative_analysis": "Análisis Cualitativo",
    "systemic_tools": "Instrumentos Sistémicos",
    "social_reports": "Informes Periciales/Sociales",
    "diagnostic_manuals": "Sistemas de Clasificación (DSM/CIE)",
    "clinical_psychometrics": "Psicometría Clínica",
    "health_records": "Historia Clínica Digital"
}

def render_dashboard_sapp(results: Dict[str, Any]):
    """
    Renderiza el panel de resultados de la prueba SAPP.
    Recibe el diccionario 'refined_metrics' generado por SAPPRefinery.
    """
    is_apt = results.get('global_compliance', False)
    puntuaciones = results.get('puntuaciones_competencias', {})
    grupo = results.get('grupo_evaluado', 'Evaluación Profesional')
    flags = results.get('critical_flags', [])

    with ui.column().classes('w-full max-w-5xl mx-auto p-6 bg-[#0E1117] text-white'):
        
        # --- CABECERA ---
        with ui.row().classes('w-full justify-between items-center mb-10'):
            with ui.row().classes('bg-white rounded-xl items-center justify-center p-4').style('width: 265px; height: 100px;'):
                ui.image('logo_original.png').style('max-width: 100%; max-height: 100%; object-fit: contain;')
                
            with ui.column().classes('items-end'):
                ui.label("EVALUACIÓN DE COMPETENCIAS S.A.P.P.").classes('text-[#83ABF1] font-bold text-xl')
                ui.label(grupo.upper()).classes('text-white text-sm tracking-widest')

        # --- BLOQUE 1: STATUS DE APTITUD (EL SEMÁFORO) ---
        color_status = '#22C55E' if is_apt else '#EF4444'
        bg_status = 'rgba(34, 197, 94, 0.1)' if is_apt else 'rgba(239, 68, 68, 0.1)'
        
        with ui.card().classes('w-full p-8 mb-10 items-center justify-center border-2 shadow-2xl').style(f'background-color: {bg_status}; border-color: {color_status}'):
            ui.label('DICTAMEN DE CUMPLIMIENTO').classes('text-xs font-black tracking-[.3em] mb-2')
            ui.label('APTO' if is_apt else 'NO APTO').classes(f'text-6xl font-black').style(f'color: {color_status}')
            if not is_apt:
                ui.label('Se han detectado desviaciones críticas en áreas de cumplimiento obligatorio.').classes('text-red-400 mt-2 text-center')

        # --- BLOQUE 2: MATRIZ DE COMPETENCIAS ---
        ui.label('MATRIZ DE DESEMPEÑO').classes('text-[#83ABF1] font-bold mb-4 ml-2')
        
        with ui.row().classes('w-full gap-4 mb-10'):
            for comp_id, score in puntuaciones.items():
                nombre_comp = SAPP_LABELS.get(comp_id, comp_id)
                
                # Lógica de color por competencia
                if score < 0: 
                    badge_color = 'bg-red-500'
                    desc = "Riesgo Detectado"
                elif score >= 2: 
                    badge_color = 'bg-green-500'
                    desc = "Fortaleza Consolidada"
                else: 
                    badge_color = 'bg-yellow-500'
                    desc = "En Desarrollo"

                with ui.card().classes('flex-1 min-w-[200px] bg-[#161B22] border border-gray-800 p-6 items-center shadow-lg'):
                    ui.element('div').classes(f'w-3 h-3 rounded-full {badge_color} mb-4 shadow-[0_0_10px_rgba(255,255,255,0.2)]')
                    ui.label(nombre_comp).classes('text-center font-bold text-sm mb-2 h-10 overflow-hidden')
                    ui.label(f"{'+' if score > 0 else ''}{score}").classes('text-3xl font-black text-white')
                    ui.label(desc).classes('text-[10px] text-gray-500 uppercase mt-2')

        # --- BLOQUE 3: ALERTAS Y BANDERAS ROJAS ---
        if flags:
            with ui.column().classes('w-full bg-red-950/20 border border-red-500/50 rounded-xl p-8 mb-8'):
                with ui.row().classes('items-center gap-3 mb-4'):
                    ui.icon('report_problem', color='red').classes('text-2xl')
                    ui.label("BANDERAS ROJAS (RESTRICCIONES DE COMPLIANCE)").classes('text-red-500 font-black')
                
                for flag in flags:
                    with ui.row().classes('w-full items-start gap-2 mb-2'):
                        ui.label("•").classes('text-red-500 font-bold')
                        with ui.column():
                            ui.label(f"{flag['competency']}:").classes('text-white font-bold text-sm')
                            ui.label(flag['message']).classes('text-gray-400 text-xs')

        # --- BLOQUE 4: ACCIONES FINALES ---
        with ui.row().classes('w-full justify-center gap-6 mt-6 pb-10'):
            ui.button('VOLVER AL PANEL', on_click=lambda: ui.navigate.to('/')).classes('bg-gray-800 text-white px-10 py-4 rounded-xl font-bold hover:bg-gray-700')
            
            # El botón de PDF se conectará en el siguiente hito
            ui.button('DESCARGAR INFORME SAPP', icon='picture_as_pdf').classes('bg-[#0D248D] text-white px-10 py-4 rounded-xl font-bold shadow-xl hover:scale-105 transition-all')