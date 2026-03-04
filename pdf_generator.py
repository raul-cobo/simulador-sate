from fpdf import FPDF
import os
from datetime import datetime
from typing import Dict, Any

# ==========================================
# 1. DICCIONARIOS DE DATOS (SAPE & SAPP)
# ==========================================

TEXTOS_RASGOS = {
    'achievement': {'nombre': 'Necesidad de Logro', 'fortaleza': 'Clara orientación a resultados y estándares de excelencia.', 'area': 'Bajo impulso de ejecución.'},
    'risk_propensity': {'nombre': 'Propensión al Riesgo', 'fortaleza': 'Alta tolerancia al riesgo e incertidumbre.', 'area': 'Aversión al riesgo. Lentitud en decisiones.'},
    'innovativeness': {'nombre': 'Innovatividad', 'fortaleza': 'Alta capacidad para proponer soluciones disruptivas.', 'area': 'Visión tradicional. Dificultad para pivotar.'},
    'locus_control': {'nombre': 'Locus de Control', 'fortaleza': 'Asume la responsabilidad total de los resultados.', 'area': 'Tendencia a atribuir resultados a factores externos.'},
    'self_efficacy': {'nombre': 'Autoeficacia', 'fortaleza': 'Firme convicción en sus propias capacidades.', 'area': 'Dudas sobre la propia capacidad.'},
    'autonomy': {'nombre': 'Autonomía', 'fortaleza': 'Alta independencia operativa.', 'area': 'Dependencia de validación constante.'},
    'ambiguity_tolerance': {'nombre': 'Tolerancia a la Incertidumbre', 'fortaleza': 'Opera bien en entornos caóticos.', 'area': 'Necesidad de estructuras rígidas.'},
    'emotional_stability': {'nombre': 'Estabilidad Emocional', 'fortaleza': 'Manejo óptimo del estrés.', 'area': 'Alta reactividad emocional.'}
}

SAPP_LABELS = {
    # (Mapeo resumido para el generador PDF)
    "ethical_integrity": "Ética e Integridad",
    "strategic_vision": "Visión Estratégica",
    "influence_negotiation": "Influencia y Negociación",
    "adaptability": "Adaptabilidad Organizacional",
    "professionalism": "Profesionalismo",
    "therapeutic_alliance": "Alianza Terapéutica",
    "reflective_practice": "Práctica Reflexiva",
    "case_formulation": "Formulación de Casos",
    "differential_diagnosis": "Diagnóstico Diferencial",
    "evidence_based_treatment": "Tratamiento Basado en Evidencia",
    "risk_management": "Gestión de Riesgos",
    "clinical_psychometrics": "Psicometría Clínica",
    "diagnostic_manuals": "Sistemas de Clasificación",
    "health_records": "Historia Clínica Digital",
    "telepractice": "Telepráctica"
}

# ==========================================
# 2. CLASE BASE: IDENTIDAD CORPORATIVA
# ==========================================

class AudeoPDF(FPDF):
    def header(self):
        # Fondo oscuro corporativo para la cabecera
        self.set_fill_color(14, 17, 23) # #0E1117
        self.rect(0, 0, 210, 30, 'F')
        
        self.set_y(10)
        self.set_font('Arial', 'B', 18)
        self.set_text_color(131, 171, 241) # #83ABF1
        self.cell(0, 10, 'AUDEO PLATFORM', 0, 1, 'L')
        
        self.set_font('Arial', '', 10)
        self.set_text_color(255, 255, 255)
        self.set_y(12)
        self.cell(0, 10, 'Corporate Psychometric Intelligence', 0, 1, 'R')

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Generado el {datetime.now().strftime("%d/%m/%Y %H:%M")} - Documento Estrictamente Confidencial', 0, 0, 'C')

# ==========================================
# 3. MOTOR GENERADOR SAPP (NUEVO)
# ==========================================

def generar_informe_sapp(user_info: Dict, results: Dict, filepath: str):
    """Genera el PDF del informe Profesional SAPP."""
    pdf = AudeoPDF()
    pdf.add_page()
    
    is_apt = results.get('global_compliance', False)
    grupo = results.get('grupo_evaluado', 'Evaluación Profesional')
    puntuaciones = results.get('puntuaciones_competencias', {})
    flags = results.get('critical_flags', [])

    # Título del Documento
    pdf.set_y(40)
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, "INFORME DE EVALUACIÓN S.A.P.P.", 0, 1, 'C')
    
    pdf.set_font('Arial', 'I', 12)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, f"Módulo Evaluado: {grupo.upper()}", 0, 1, 'C')
    pdf.ln(10)

    # Bloque de Identificación
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('Arial', 'B', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(40, 8, "Candidato:", border=1, fill=True)
    pdf.set_font('Arial', '', 10)
    pdf.cell(150, 8, str(user_info.get('username', 'Anónimo')), border=1)
    pdf.ln(8)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(40, 8, "ID Usuario:", border=1, fill=True)
    pdf.set_font('Arial', '', 10)
    pdf.cell(150, 8, str(user_info.get('user_id', 'N/A')), border=1)
    pdf.ln(15)

    # Dictamen de Compliance (El Semáforo)
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, "1. DICTAMEN DE CUMPLIMIENTO", 0, 1, 'L')
    
    if is_apt:
        pdf.set_fill_color(220, 255, 220) # Verde pastel
        pdf.set_text_color(0, 100, 0)
        texto_dictamen = "APTO - Cumple con los estándares requeridos."
    else:
        pdf.set_fill_color(255, 220, 220) # Rojo pastel
        pdf.set_text_color(150, 0, 0)
        texto_dictamen = "NO APTO - Se han detectado riesgos críticos o desviaciones éticas."

    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 20, texto_dictamen, border=1, ln=1, align='C', fill=True)
    pdf.ln(10)

    # Matriz de Competencias
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, "2. MATRIZ DE COMPETENCIAS", 0, 1, 'L')
    pdf.set_font('Arial', 'B', 10)
    pdf.set_fill_color(131, 171, 241) # Corporativo #83ABF1
    pdf.set_text_color(255, 255, 255)
    
    # Cabeceras de tabla
    pdf.cell(80, 10, "Competencia", border=1, fill=True)
    pdf.cell(30, 10, "Puntuación", border=1, fill=True, align='C')
    pdf.cell(80, 10, "Diagnóstico", border=1, fill=True, align='C')
    pdf.ln(10)
    
    # Filas de la tabla
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 10)
    for comp_id, score in puntuaciones.items():
        nombre_comp = SAPP_LABELS.get(comp_id, comp_id.replace('_', ' ').title())
        
        if score < 0:
            diag = "Riesgo Detectado"
            pdf.set_fill_color(255, 200, 200) # Rojo claro
        elif score >= 2:
            diag = "Fortaleza Consolidada"
            pdf.set_fill_color(200, 255, 200) # Verde claro
        else:
            diag = "En Desarrollo"
            pdf.set_fill_color(255, 255, 200) # Amarillo claro
            
        pdf.cell(80, 10, nombre_comp, border=1)
        pdf.cell(30, 10, f"{score}", border=1, align='C')
        pdf.cell(80, 10, diag, border=1, align='C', fill=True)
        pdf.ln(10)
        
    pdf.ln(10)

    # Banderas Rojas (Solo si existen)
    if flags:
        pdf.set_text_color(200, 0, 0)
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, "3. ALERTAS CRÍTICAS (BANDERAS ROJAS)", 0, 1, 'L')
        pdf.set_font('Arial', '', 11)
        pdf.set_text_color(0, 0, 0)
        
        for flag in flags:
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(0, 8, f"• {flag['competency']}:", 0, 1, 'L')
            pdf.set_font('Arial', '', 11)
            pdf.multi_cell(0, 6, f"  {flag['message']}")
            pdf.ln(2)

    pdf.output(filepath)
    return filepath

# ==========================================
# 4. MOTOR GENERADOR SAPE (LEGADO ADAPTADO)
# ==========================================

def generar_informe_sape(user_info: Dict, results: Dict, filepath: str):
    """Genera el PDF del informe de Personalidad SAPE."""
    pdf = AudeoPDF()
    pdf.add_page()
    
    # --- CABECERA SAPE ---
    pdf.set_y(40)
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, "INFORME DE PERFIL EMPRENDEDOR S.A.P.E.", 0, 1, 'C')
    pdf.ln(10)
    
    potencial = results.get('potencial', 0)
    ire = results.get('ire', 0)
    patrones = results.get('patrones_clinicos', [])
    
    # Bloque de Métricas
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "MÉTRICAS PRINCIPALES", 0, 1, 'L')
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 8, f"Potencial Emprendedor: {potencial}/100", 0, 1)
    pdf.cell(0, 8, f"Índice de Resiliencia (IRE): {ire}", 0, 1)
    pdf.ln(5)

    # Patrones y Descarriladores
    if patrones:
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(200, 0, 0)
        pdf.cell(0, 10, "RIESGOS ESTRUCTURALES DETECTADOS", 0, 1, 'L')
        pdf.set_text_color(0, 0, 0)
        for pat in patrones:
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(0, 6, f"Patrón: {pat.get('nombre', '')}", 0, 1)
            pdf.set_font('Arial', '', 10)
            pdf.multi_cell(0, 6, pat.get('desc', ''))
            pdf.ln(4)

    # (Aquí puedes mantener la lógica exacta de tu dibujo del octógono si la tienes mapeada
    # o simplemente listar los rasgos con TEXTOS_RASGOS como tabla para estandarizar).
    
    pdf.output(filepath)
    return filepath

# ==========================================
# 5. ENRUTADOR PRINCIPAL (POLIMORFISMO)
# ==========================================

def generar_informe(user_info: Dict, results: Dict, test_type: str = 'SAPE') -> str:
    """
    Función de entrada unificada. Determina qué generador llamar.
    Retorna la ruta absoluta del archivo generado.
    """
    filename = f"Informe_{test_type}_{user_info.get('username', 'User')}_{datetime.now().strftime('%Y%m%d%H%M')}.pdf"
    filename = filename.replace(" ", "_").replace("/", "-")
    filepath = os.path.join(os.getcwd(), filename)
    
    if test_type.upper() == 'SAPP':
        return generar_informe_sapp(user_info, results, filepath)
    else:
        return generar_informe_sape(user_info, results, filepath)