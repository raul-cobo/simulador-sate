# pdf_generator.py
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
        
        # Intentar colocar logo si existe
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
    """Genera el PDF del informe Profesional SAPP replicando las barras visuales."""
    pdf = AudeoPDF()
    pdf.add_page()
    
    modulo = results.get('module', 'General').upper()
    comps = results.get('competencies', {})

    # Título del Documento
    pdf.set_y(40)
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, "INFORME DE EVALUACIÓN S.A.P.P.", 0, 1, 'C')
    
    pdf.set_font('Arial', 'I', 12)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, f"Módulo Evaluado: {modulo}", 0, 1, 'C')
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
    pdf.cell(40, 8, "ID Organización:", border=1, fill=True)
    pdf.set_font('Arial', '', 10)
    pdf.cell(150, 8, str(user_info.get('org_id', 'N/A')), border=1)
    pdf.ln(15)

    # Matriz de Competencias (Barras Horizontales)
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
            
            # Formateo del nombre
            nombre_limpio = SAPP_LABELS.get(comp_name, str(comp_name).replace('_', ' ').title())
            
            # Textos
            pdf.set_font('Arial', 'B', 11)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(120, 8, nombre_limpio, 0, 0, 'L')
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(0, 8, f"{pct}% (Puntos: {raw})", 0, 1, 'R')
            
            # Colores
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
    pdf.set_font('Arial', 'I', 9)
    pdf.set_text_color(150, 150, 150)
    pdf.multi_cell(0, 5, "Este informe ha sido generado mediante el motor psicométrico de Audeo. "
                         "Los resultados porcentuales reflejan la alineación del candidato con las conductas "
                         "esperadas para el módulo evaluado.")

    pdf.output(filepath)
    return filepath

# ==========================================
# 4. MOTOR GENERADOR SAPE
# ==========================================

def generar_informe_sape(user_info: Dict, results: Dict, filepath: str):
    """Genera el PDF del informe de Personalidad SAPE."""
    pdf = AudeoPDF()
    pdf.add_page()
    
    pdf.set_y(40)
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, "INFORME DE PERFIL EMPRENDEDOR S.A.P.E.", 0, 1, 'C')
    pdf.ln(10)
    
    potencial = results.get('potencial', 0)
    ire = results.get('ire', 0)
    patrones = results.get('patrones_clinicos', [])
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "MÉTRICAS PRINCIPALES", 0, 1, 'L')
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 8, f"Potencial Emprendedor: {potencial}/100", 0, 1)
    pdf.cell(0, 8, f"Índice de Resiliencia (IRE): {ire}", 0, 1)
    pdf.ln(5)

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

    pdf.output(filepath)
    return filepath

# ==========================================
# 4.5 MOTOR GENERADOR B2B (PROFORMAS)
# ==========================================

def generar_proforma(org_data: Dict, order_data: Dict, filepath: str):
    """Genera el PDF de la Factura Proforma Comercial alineada con los T&C"""
    pdf = AudeoPDF()
    pdf.add_page()
    
    azul_audeo = (13, 36, 141) # #0D248D

    # --- CABECERA FINANCIERA ---
    pdf.set_y(40)
    pdf.set_font('Arial', 'B', 20)
    pdf.set_text_color(*azul_audeo)
    pdf.cell(0, 10, "FACTURA PROFORMA", 0, 1, 'R')
    
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"Fecha de emision: {datetime.now().strftime('%d/%m/%Y')}", 0, 1, 'R')
    pdf.cell(0, 6, f"Referencia: AUD-{str(order_data.get('id', '000'))[:8].upper()}", 0, 1, 'R')
    pdf.ln(10)

    # --- DATOS FISCALES (EMISOR Y RECEPTOR) ---
    y_current = pdf.get_y()
    
    # Emisor (Audeo) - RELLENA ESTOS DATOS CON LOS TUYOS
    pdf.set_font('Arial', 'B', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(95, 6, "EMISOR:", 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    pdf.cell(95, 5, "TU NOMBRE O EMPRESA S.L.", 0, 1, 'L')
    pdf.cell(95, 5, "CIF: B-00000000", 0, 1, 'L')
    pdf.cell(95, 5, "Tu Direccion Fiscal", 0, 1, 'L')
    pdf.cell(95, 5, "Tu Ciudad y Codigo Postal", 0, 1, 'L')
    pdf.cell(95, 5, "facturacion@audeo.es", 0, 1, 'L')
    
    # Receptor (El Cliente B2B)
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

    # --- TABLA DE LICENCIAS ---
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
    
    # Texto unificado con los T&C
    pdf.cell(100, 10, " Licencia Audeo: Ciclo Evolutivo Completo (3 pasaciones)", 1, 0, 'L')
    pdf.cell(25, 10, f" {cantidad}", 1, 0, 'C')
    pdf.cell(30, 10, f" {precio_ud:.2f} EUR", 1, 0, 'C')
    pdf.cell(35, 10, f" {subtotal:.2f} EUR", 1, 1, 'R')

    pdf.ln(10)

    # --- DESGLOSE FINANCIERO TOTALES ---
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

    # --- INSTRUCCIONES DE PAGO Y CONDICIONES (Alineado con T&C) ---
    pdf.set_y(-65)
    pdf.set_text_color(50, 50, 50)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(0, 5, "INSTRUCCIONES DE PAGO Y CONDICIONES LEGALES:", 0, 1, 'L')
    pdf.set_font('Arial', '', 8)
    
    texto_pago = (
        "1. Pago mediante transferencia bancaria al IBAN: ES00 0000 0000 0000 0000 0000 (Sustituir por tu cuenta).\n"
        f"   (Indicar en el concepto la Referencia: AUD-{str(order_data.get('id', '000'))[:8].upper()}).\n"
        "2. Esta proforma tiene una validez de 15 dias naturales desde su emision.\n"
        "3. Las licencias adquiridas caducaran a los 12 meses de su activacion en plataforma.\n"
        "4. Al realizar el pago, el Cliente acepta los Terminos y Condiciones disponibles en audeo.es/terminos-y-condiciones-audeo"
    )
    pdf.multi_cell(0, 4, texto_pago)

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
    
    if test_type.upper() == 'PROFORMA':
        filename = f"Proforma_Audeo_{user_info.get('id', 'B2B')[:8]}_{datetime.now().strftime('%Y%m%d')}.pdf"
        filepath = os.path.join(os.getcwd(), filename)
        return generar_proforma(user_info, results, filepath)
        
    filename = f"Informe_{test_type}_{user_info.get('username', 'User')}_{datetime.now().strftime('%Y%m%d%H%M')}.pdf"
    filename = filename.replace(" ", "_").replace("/", "-")
    filepath = os.path.join(os.getcwd(), filename)
    
    if test_type.upper() == 'SAPP':
        return generar_informe_sapp(user_info, results, filepath)
    else:
        return generar_informe_sape(user_info, results, filepath)