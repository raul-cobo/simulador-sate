# pdf_generator.py
from fpdf import FPDF
import os
from datetime import datetime
from typing import Dict, Any

# ==========================================
# 1. DICCIONARIOS DE DATOS (SAPE, SAPP & SAIV)
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

RIASEC_DESC = {
    'R': {'nombre': 'Realista (Técnico)', 'desc': 'Preferencia por actividades prácticas y tangibles. Disfrutas trabajando con herramientas, máquinas, o en entornos físicos y operativos.', 'roles': 'Ingeniería, Operaciones, Arquitectura de Hardware.'},
    'I': {'nombre': 'Investigador (Científico)', 'desc': 'Fuerte inclinación hacia la observación, el análisis y la resolución de problemas complejos mediante la lógica.', 'roles': 'Data Science, I+D, Investigación.'},
    'A': {'nombre': 'Artístico', 'desc': 'Alta necesidad de expresión creativa, innovación y diseño. Prefieres entornos de trabajo no estructurados.', 'roles': 'Diseño UX/UI, Dirección Creativa, Contenido.'},
    'S': {'nombre': 'Social', 'desc': 'Motivación genuina por informar, formar, desarrollar, curar o guiar a otras personas. Foco en el bienestar humano.', 'roles': 'RRHH, Mentoría, Customer Success.'},
    'E': {'nombre': 'Emprendedor', 'desc': 'Disfrutas asumiendo riesgos, liderando equipos, persuadiendo a otros y gestionando proyectos para alcanzar metas.', 'roles': 'Business Dev, Ventas, Management.'},
    'C': {'nombre': 'Convencional (Organizativo)', 'desc': 'Habilidad para el orden, la sistematización, el trabajo con datos precisos y el cumplimiento de procedimientos.', 'roles': 'Finanzas, Administración, Auditoría.'}
}

# ==========================================
# 2. CLASE BASE: IDENTIDAD CORPORATIVA
# ==========================================

class AudeoPDF(FPDF):
    def header(self):
        self.set_fill_color(14, 17, 23) # #0E1117
        self.rect(0, 0, 210, 30, 'F')
        
        if os.path.exists("logo_blanco.png"):
            self.image("logo_blanco.png", x=10, y=5, w=40)
        else:
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
# 3. MOTOR GENERADOR SAPP
# ==========================================

def generar_informe_sapp(user_info: Dict, results: Dict, filepath: str):
    pdf = AudeoPDF()
    pdf.add_page()
    
    modulo = results.get('module', 'General').upper()
    comps = results.get('competencies', {})

    pdf.set_y(40)
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, "INFORME DE EVALUACIÓN S.A.P.P.", 0, 1, 'C')
    
    pdf.set_font('Arial', 'I', 12)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, f"Módulo Evaluado: {modulo}", 0, 1, 'C')
    pdf.ln(10)

    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('Arial', 'B', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(40, 8, "Candidato:", border=1, fill=True)
    pdf.set_font('Arial', '', 10)
    pdf.cell(150, 8, str(user_info.get('username', 'Anónimo')), border=1)
    pdf.ln(8)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(40, 8, "ID Organización:", border=1, fill=True)
    pdf.set_font('Arial', '', 10)
    pdf.cell(150, 8, str(user_info.get('org_id', 'N/A')), border=1)
    pdf.ln(15)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, "RESULTADOS POR COMPETENCIA", 0, 1, 'L')
    pdf.ln(5)

    if not comps:
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 10, "No se encontraron competencias registradas.", 0, 1, 'L')
    else:
        for comp_name, data in comps.items():
            pct = data.get('percentage', 0)
            raw = data.get('raw_score', 0)
            
            nombre_limpio = SAPP_LABELS.get(comp_name, str(comp_name).replace('_', ' ').title())
            
            pdf.set_font('Arial', 'B', 11)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(120, 8, nombre_limpio, 0, 0, 'L')
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(0, 8, f"{pct}% (Puntos: {raw})", 0, 1, 'R')
            
            if pct <= 0:
                r, g, b = 239, 68, 68    
            elif pct <= 50:
                r, g, b = 234, 179, 8    
            elif pct <= 75:
                r, g, b = 150, 200, 50    
            else:
                r, g, b = 22, 163, 74    
                
            x_start = 10
            y_bar = pdf.get_y()
            max_width = 190
            pdf.set_fill_color(230, 230, 230)
            pdf.rect(x_start, y_bar, max_width, 6, 'F')
            
            if pct > 0:
                bar_width = (pct / 100.0) * max_width
                pdf.set_fill_color(r, g, b)
                pdf.rect(x_start, y_bar, bar_width, 6, 'F')
            else:
                pdf.set_fill_color(239, 68, 68)
                pdf.rect(x_start, y_bar, 2, 6, 'F')
                
            pdf.ln(12)

    pdf.ln(10)
    pdf.set_fill_color(245, 245, 245)
    pdf.set_draw_color(200, 200, 200)
    pdf.rect(10, pdf.get_y(), 190, 25, 'FD')
    pdf.set_y(pdf.get_y() + 2)
    pdf.set_font('Arial', 'B', 8)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 5, "AVISO LEGAL Y DEONTOLÓGICO (Art. 22 RGPD):", 0, 1, 'L')
    pdf.set_font('Arial', '', 8)
    pdf.multi_cell(186, 4, "Los resultados de este informe se basan en un procesamiento automatizado. Constituyen una herramienta de apoyo al diagnóstico profesional y no tienen efectos jurídicos vinculantes por sí mismos. Queda terminantemente prohibido su uso como único criterio en procesos de selección o evaluación sin la validación e intervención directa de un profesional humano cualificado.")

    pdf.output(filepath)
    return filepath

# ==========================================
# 4. MOTOR GENERADOR SAPE
# ==========================================

def generar_informe_sape(user_info: Dict, results: Dict, filepath: str):
    pdf = AudeoPDF()
    pdf.add_page()
    
    pdf.set_y(40)
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, "INFORME DE PERFIL EMPRENDEDOR S.A.P.E.", 0, 1, 'C')
    
    pdf.set_font('Arial', 'I', 11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, f"Candidato: {user_info.get('username', 'Anónimo')} | Org: {user_info.get('org_id', 'N/A').upper()}", 0, 1, 'C')
    pdf.ln(10)
    
    potencial = results.get('potencial', 0.0)
    ire = results.get('ire', 0.0)
    friccion = results.get('friccion', 0.0)
    delta = results.get('delta', 0.0)
    
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, "MÉTRICAS PRINCIPALES (KPIs)", 0, 1, 'L')
    
    pdf.set_font('Arial', 'B', 11)
    
    y_kpi = pdf.get_y()
    pdf.set_fill_color(240, 240, 245)
    
    pdf.rect(10, y_kpi, 90, 20, 'F')
    pdf.set_xy(10, y_kpi + 5)
    pdf.cell(45, 10, "Potencial:", 0, 0, 'C')
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(13, 36, 141) 
    pdf.cell(45, 10, f"{potencial}%", 0, 0, 'C')
    
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.rect(110, y_kpi, 90, 20, 'F')
    pdf.set_xy(110, y_kpi + 5)
    pdf.cell(45, 10, "IRE (Resiliencia):", 0, 0, 'C')
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(34, 197, 94) 
    pdf.cell(45, 10, f"{ire}%", 0, 1, 'C')
    
    pdf.ln(5)
    y_kpi = pdf.get_y()
    
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.rect(10, y_kpi, 90, 20, 'F')
    pdf.set_xy(10, y_kpi + 5)
    pdf.cell(45, 10, "Fricción:", 0, 0, 'C')
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(239, 68, 68) 
    pdf.cell(45, 10, f"{friccion}", 0, 0, 'C')
    
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.rect(110, y_kpi, 90, 20, 'F')
    pdf.set_xy(110, y_kpi + 5)
    pdf.cell(45, 10, "Delta:", 0, 0, 'C')
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(234, 179, 8) 
    pdf.cell(45, 10, f"{delta}", 0, 1, 'C')

    pdf.ln(10)
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, "DESGLOSE POR DIMENSIÓN", 0, 1, 'L')
    pdf.ln(2)
    
    for key, dict_textos in TEXTOS_RASGOS.items():
        valor = results.get(key, 50.0) 
        
        pdf.set_font('Arial', 'B', 10)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(120, 6, dict_textos['nombre'], 0, 0, 'L')
        pdf.cell(0, 6, f"{valor}%", 0, 1, 'R')
        
        pdf.set_fill_color(230, 230, 230)
        pdf.rect(10, pdf.get_y(), 190, 3, 'F')
        if valor > 0:
            pdf.set_fill_color(131, 171, 241) 
            pdf.rect(10, pdf.get_y(), (valor/100)*190, 3, 'F')
        pdf.ln(5)

    patrones = results.get('patrones_clinicos', [])
    if patrones:
        pdf.ln(5)
        pdf.set_font('Arial', 'B', 14)
        pdf.set_text_color(200, 0, 0)
        pdf.cell(0, 10, "RIESGOS Y PATRONES DETECTADOS", 0, 1, 'L')
        pdf.set_text_color(0, 0, 0)
        for pat in patrones:
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(0, 6, f"Patrón: {pat.get('nombre', 'Desconocido')}", 0, 1)
            pdf.set_font('Arial', '', 9)
            pdf.multi_cell(0, 5, pat.get('desc', ''))
            pdf.ln(2)

    pdf.set_y(-45)
    pdf.set_fill_color(245, 245, 245)
    pdf.set_draw_color(200, 200, 200)
    pdf.rect(10, pdf.get_y(), 190, 25, 'FD')
    pdf.set_y(pdf.get_y() + 2)
    pdf.set_font('Arial', 'B', 8)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 5, "AVISO LEGAL Y DEONTOLÓGICO (Art. 22 RGPD):", 0, 1, 'L')
    pdf.set_font('Arial', '', 8)
    pdf.multi_cell(186, 4, "Los resultados de este informe se basan en un procesamiento automatizado. Constituyen una herramienta de apoyo al diagnóstico profesional y no tienen efectos jurídicos vinculantes por sí mismos. Queda terminantemente prohibido su uso como único criterio en procesos de selección o evaluación sin la validación e intervención directa de un profesional humano cualificado.")

    pdf.output(filepath)
    return filepath

generar_pdf_sape = generar_informe_sape 

# ==========================================
# 4.5 MOTOR GENERADOR B2B (PROFORMAS)
# ==========================================

def generar_proforma(org_data: Dict, order_data: Dict, filepath: str):
    pdf = AudeoPDF()
    pdf.add_page()
    
    azul_audeo = (13, 36, 141) # #0D248D

    pdf.set_y(40)
    pdf.set_font('Arial', 'B', 20)
    pdf.set_text_color(*azul_audeo)
    pdf.cell(0, 10, "FACTURA PROFORMA", 0, 1, 'R')
    
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"Fecha de emision: {datetime.now().strftime('%d/%m/%Y')}", 0, 1, 'R')
    pdf.cell(0, 6, f"Referencia: AUD-{str(order_data.get('id', '000'))[:8].upper()}", 0, 1, 'R')
    pdf.ln(10)

    y_current = pdf.get_y()
    
    pdf.set_font('Arial', 'B', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(95, 6, "EMISOR:", 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    pdf.cell(95, 5, "Raúl Cobo Palomino", 0, 1, 'L')
    pdf.cell(95, 5, "CIF: **********", 0, 1, 'L')
    pdf.cell(95, 5, "Direccion Fiscal: **********", 0, 1, 'L')
    pdf.cell(95, 5, "Ciudad y Codigo Postal: **********", 0, 1, 'L')
    pdf.cell(95, 5, "facturacion@audeo.es", 0, 1, 'L')
    
    pdf.set_y(y_current)
    pdf.set_x(110)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(95, 6, "CLIENTE / FACTURAR A:", 0, 1, 'L')
    pdf.set_x(110)
    pdf.set_font('Arial', '', 10)
    pdf.cell(95, 5, str(org_data.get('razon_social', org_data.get('name', 'N/A'))), 0, 1, 'L')
    pdf.set_x(110)
    pdf.cell(95, 5, f"CIF/NIF: {org_data.get('cif_nif', 'PENDIENTE DE DATOS')}", 0, 1, 'L')
    pdf.set_x(110)
    pdf.cell(95, 5, str(org_data.get('direccion_fiscal', 'Direccion no facilitada')), 0, 1, 'L')
    pdf.set_x(110)
    pdf.cell(95, 5, f"{org_data.get('codigo_postal', '')} {org_data.get('ciudad', '')}", 0, 1, 'L')
    
    pdf.ln(15)

    pdf.set_fill_color(*azul_audeo)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 10)
    
    pdf.cell(100, 8, " Concepto", 1, 0, 'L', fill=True)
    pdf.cell(25, 8, " Cantidad", 1, 0, 'C', fill=True)
    pdf.cell(30, 8, " Precio Ud.", 1, 0, 'C', fill=True)
    pdf.cell(35, 8, " Subtotal", 1, 1, 'R', fill=True)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 10)
    
    cantidad = order_data.get('cantidad_licencias', 0)
    precio_ud = order_data.get('precio_unitario', 0.0)
    subtotal = order_data.get('subtotal', 0.0)
    
    pdf.cell(100, 10, " Licencia Audeo: Ciclo Evolutivo Completo (3 pasaciones)", 1, 0, 'L')
    pdf.cell(25, 10, f" {cantidad}", 1, 0, 'C')
    pdf.cell(30, 10, f" {precio_ud:.2f} EUR", 1, 0, 'C')
    pdf.cell(35, 10, f" {subtotal:.2f} EUR", 1, 1, 'R')

    pdf.ln(10)

    pdf.set_x(130)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(35, 8, "Base Imponible:", 0, 0, 'R')
    pdf.set_font('Arial', '', 10)
    pdf.cell(35, 8, f"{subtotal:.2f} EUR", 0, 1, 'R')
    
    iva = order_data.get('iva', 0.0)
    pdf.set_x(130)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(35, 8, "I.V.A. (21%):", 0, 0, 'R')
    pdf.set_font('Arial', '', 10)
    pdf.cell(35, 8, f"{iva:.2f} EUR", 0, 1, 'R')
    
    total = order_data.get('total', 0.0)
    pdf.set_x(130)
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(*azul_audeo)
    pdf.cell(35, 10, "TOTAL A PAGAR:", 0, 0, 'R')
    pdf.cell(35, 10, f"{total:.2f} EUR", 0, 1, 'R')

    pdf.set_y(-65)
    pdf.set_text_color(50, 50, 50)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(0, 5, "INSTRUCCIONES DE PAGO Y CONDICIONES LEGALES:", 0, 1, 'L')
    pdf.set_font('Arial', '', 8)
    
    texto_pago = (
        "1. Pago mediante transferencia bancaria al IBAN: ES***************.\n"
        f"   (Indicar en el concepto la Referencia: AUD-{str(order_data.get('id', '000'))[:8].upper()}).\n"
        "2. Esta proforma tiene una validez de 15 dias naturales desde su emision.\n"
        "3. Las licencias adquiridas caducaran a los 12 meses de su activacion en plataforma.\n"
        "4. Al realizar el pago, el Cliente acepta los Terminos y Condiciones disponibles en audeo.es/terminos-y-condiciones-audeo"
    )
    pdf.multi_cell(0, 4, texto_pago)

    pdf.output(filepath)
    return filepath

# ==========================================
# 4.8 MOTOR GENERADOR SAIV (NUEVO)
# ==========================================

def generar_informe_saiv(user_info: Dict, results: Dict, filepath: str):
    """Genera el PDF del informe de Orientación Vocacional SAIV usando FPDF."""
    pdf = AudeoPDF()
    pdf.add_page()
    
    riasec_code = results.get('riasec_code', '---')
    scores = results.get('scores', {})
    
    pdf.set_y(40)
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, "INFORME DE ORIENTACIÓN VOCACIONAL S.A.I.V.", 0, 1, 'C')
    
    pdf.set_font('Arial', 'I', 11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, f"Candidato: {user_info.get('username', 'Anónimo').upper()}", 0, 1, 'C')
    pdf.ln(10)
    
    # Destacado RIASEC
    pdf.set_fill_color(13, 36, 141) # Azul corporativo #0D248D
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 15, f"  TU CÓDIGO VOCACIONAL DOMINANTE: {riasec_code}", 0, 1, 'C', 1)
    pdf.ln(10)
    
    # Gráfico de Barras RIASEC
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, "Distribución de Intereses", 0, 1, 'L')
    pdf.ln(2)
    
    for letra in ['R', 'I', 'A', 'S', 'E', 'C']:
        nombre = RIASEC_DESC[letra]['nombre']
        
        # Extracción segura de datos
        pct = 0
        if isinstance(results.get('metrics', {}).get(letra), dict):
            pct = results['metrics'][letra].get('percentage', 0)
        elif scores:
            max_val = max(scores.values()) if scores.values() else 1
            pct = int((scores.get(letra, 0) / max_val) * 100) if max_val > 0 else 0
            
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(60, 8, nombre, 0, 0)
        
        x_start = pdf.get_x()
        y_bar = pdf.get_y() + 2
        
        pdf.set_fill_color(230, 230, 230)
        pdf.rect(x_start, y_bar, 100, 4, 'F')
        
        if pct > 0:
            pct_draw = min(pct, 100)
            pdf.set_fill_color(131, 171, 241)
            pdf.rect(x_start, y_bar, pct_draw, 4, 'F')
            
        pdf.set_x(x_start + 105)
        pdf.set_font('Arial', '', 10)
        pdf.cell(20, 8, f"{pct}%", 0, 1)

    # Detalle de Roles (Top 3)
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, "Análisis de tu Perfil Principal", "B", 1, 'L')
    pdf.ln(5)
    
    if len(riasec_code) >= 1 and riasec_code != '---':
        for idx, letra in enumerate(riasec_code):
            if letra in RIASEC_DESC:
                pdf.set_font('Arial', 'B', 12)
                pdf.set_text_color(13, 36, 141)
                pdf.cell(0, 8, f"{idx+1}. {RIASEC_DESC[letra]['nombre']} ({letra})", 0, 1)
                
                pdf.set_text_color(0, 0, 0)
                pdf.set_font('Arial', '', 11)
                pdf.multi_cell(0, 6, RIASEC_DESC[letra]['desc'])
                
                pdf.set_font('Arial', 'I', 10)
                pdf.set_text_color(100, 100, 100)
                pdf.multi_cell(0, 6, f"Roles afines: {RIASEC_DESC[letra]['roles']}")
                pdf.ln(4)
                
    # Legal
    pdf.set_y(-50)
    pdf.set_fill_color(245, 245, 245)
    pdf.set_draw_color(200, 200, 200)
    pdf.rect(10, pdf.get_y(), 190, 25, 'FD')
    pdf.set_y(pdf.get_y() + 2)
    pdf.set_font('Arial', 'B', 8)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 5, "AVISO LEGAL Y DEONTOLÓGICO (Art. 22 RGPD):", 0, 1, 'L')
    pdf.set_font('Arial', '', 8)
    pdf.multi_cell(186, 4, "Este informe ha sido generado de forma automatizada. Los resultados son orientativos y no determinan habilidades innatas ni garantizan el éxito profesional. No constituye una decisión vinculante y debe usarse como herramienta de apoyo.")

    pdf.output(filepath)
    return filepath

# ==========================================
# 5. ENRUTADOR PRINCIPAL (POLIMORFISMO TOTAL)
# ==========================================

def generar_informe(user_info: Dict, results: Dict, test_type: str = 'SAPE') -> str:
    """
    Función de entrada unificada. Determina qué generador llamar.
    """
    if test_type.upper() == 'PROFORMA':
        filename = f"Proforma_Audeo_{user_info.get('id', 'B2B')[:8]}_{datetime.now().strftime('%Y%m%d')}.pdf"
        filepath = os.path.join(os.getcwd(), filename)
        return generar_proforma(user_info, results, filepath)
        
    os.makedirs('temp_reports', exist_ok=True)
    filename = f"Informe_{test_type.upper()}_{user_info.get('username', 'User')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    filename = filename.replace(" ", "_").replace("/", "-")
    filepath = os.path.join(os.getcwd(), 'temp_reports', filename)
    
    if test_type.upper() == 'SAPP':
        return generar_informe_sapp(user_info, results, filepath)
    elif test_type.upper() == 'SAIV':
        return generar_informe_saiv(user_info, results, filepath)
    else:
        # Por defecto siempre será SAPE (Mantiene compatibilidad con ORYON)
        return generar_informe_sape(user_info, results, filepath)