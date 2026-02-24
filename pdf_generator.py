from fpdf import FPDF
import os

TEXTOS_RASGOS = {
    'achievement': {'nombre': 'Necesidad de Logro', 'fortaleza': 'Clara orientación a resultados y estándares de excelencia. Prioriza la finalización de tareas.', 'area': 'Bajo impulso de ejecución. Puede mostrar conformismo o falta de ambición para escalar el proyecto.'},
    'risk_propensity': {'nombre': 'Propensión al Riesgo', 'fortaleza': 'Alta tolerancia al riesgo. Disposición a actuar en escenarios de incertidumbre financiera u operativa.', 'area': 'Aversión al riesgo. Lentitud en la toma de decisiones por miedo a comprometer recursos.'},
    'innovativeness': {'nombre': 'Innovatividad', 'fortaleza': 'Alta capacidad para proponer soluciones disruptivas y visualizar nuevos modelos de negocio.', 'area': 'Visión tradicional. Dificultad para pivotar o salir de los procesos establecidos.'},
    'locus_control': {'nombre': 'Locus de Control Interno', 'fortaleza': 'Asume la responsabilidad total de los resultados. Fuerte proactividad correctiva ante el fracaso.', 'area': 'Tendencia a atribuir resultados a factores externos. Puede reducir la proactividad correctiva.'},
    'self_efficacy': {'nombre': 'Autoeficacia', 'fortaleza': 'Firme convicción en sus propias capacidades para superar obstáculos técnicos y comerciales.', 'area': 'Dudas sobre la propia capacidad que pueden llevar a la parálisis por análisis.'},
    'autonomy': {'nombre': 'Autonomía', 'fortaleza': 'Alta independencia operativa. Capacidad para avanzar sin supervisión ni directrices externas.', 'area': 'Dependencia operativa. Requiere validación constante y directrices claras para avanzar.'},
    'ambiguity_tolerance': {'nombre': 'Tol. Ambigüedad', 'fortaleza': 'Navega eficazmente en el caos. Mantiene el foco aunque la información sea incompleta.', 'area': 'Necesidad excesiva de certezas. Se bloquea en entornos de alta volatilidad.'},
    'emotional_stability': {'nombre': 'Estabilidad Emocional', 'fortaleza': 'Capacidad absoluta para mantener la regulación bajo presión. Nula reactividad impulsiva.', 'area': 'Reactividad emocional alta. Dificultad para mantener la calma en situaciones de crisis.'}
}

class InformeAudeo(FPDF):
    def header(self):
        self.set_fill_color(13, 36, 141)
        self.rect(0, 0, 210, 40, 'F')
        
        self.set_fill_color(255, 255, 255)
        self.rect(20, 20, 40, 15, 'F') 
        
        if os.path.exists('logo_original.png'):
            self.image('logo_original.png', 22, 22, 36)
            
        self.set_y(20)
        self.set_font('Arial', 'B', 14)
        self.set_text_color(255, 255, 255)
        self.cell(0, 6, 'INFORME TECNICO S.A.P.E.', 0, 1, 'R')
        self.set_font('Arial', '', 10)
        self.cell(0, 6, 'Sistema de Analisis de la Personalidad Emprendedora', 0, 1, 'R')
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

    def draw_section_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.set_text_color(0, 0, 0)
        self.cell(0, 8, title, 0, 1, 'L')
        self.set_draw_color(13, 36, 141)
        self.line(self.get_x(), self.get_y(), self.get_x() + 190, self.get_y())
        self.ln(5)

def generar_pdf_sape(user_id, scores, alertas, demograficos):
    pdf = InformeAudeo()
    pdf.add_page()
    
    pdf.set_y(45)
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(0, 0, 0)
    
    col1_x, col2_x = 20, 110
    pdf.set_xy(col1_x, pdf.get_y())
    pdf.cell(90, 6, f"Usuario/a: {user_id}", 0, 0)
    pdf.set_xy(col2_x, pdf.get_y())
    pdf.cell(90, 6, f"Organizacion: {demograficos.get('org', 'N/A')}", 0, 1)
    pdf.set_xy(col1_x, pdf.get_y())
    pdf.cell(90, 6, f"Sector: {demograficos.get('sector', 'N/A')}", 0, 0)
    pdf.set_xy(col2_x, pdf.get_y())
    pdf.cell(90, 6, f"Fecha: {demograficos.get('fecha', 'N/A')}", 0, 1)
    pdf.ln(10)

    pdf.draw_section_title("1. METRICAS PRINCIPALES")
    metricas = [
        ("Potencial", scores.get('potencial', 0), "Capacidad basal (Recursos cognitivos y actitudinales)."),
        ("IRE", scores.get('ire', 0), "Indice de Resiliencia Emprendedora."),
        ("Friccion por defecto", scores.get('friccion_defecto', 0), "Valor de la carga sobre el IRE de los rasgos por defecto."),
        ("Friccion por exceso", scores.get('friccion_exceso', 0), "Valor de la carga sobre el IRE de los rasgos por exceso."),
        ("Delta", scores.get('delta', 0), "Distancia de la puntuacion obtenida a la puntuacion ideal.")
    ]
    for nombre, valor, desc in metricas:
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(45, 6, f"{nombre}: {valor}", 0, 0)
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 6, desc, 0, 1)
    pdf.ln(10)

    pdf.draw_section_title("2. PERFIL COMPETENCIAL (DETALLE)")
    orden_rasgos = ['achievement', 'risk_propensity', 'innovativeness', 'self_efficacy', 'autonomy', 'emotional_stability', 'locus_control', 'ambiguity_tolerance']
    descarriladores_dict = {d['rasgo']: d for d in scores.get('descarriladores', [])}

    for rasgo in orden_rasgos:
        valor = scores.get(rasgo, 50.0)
        nombre_es = TEXTOS_RASGOS[rasgo]['nombre']
        
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(50, 6, nombre_es, 0, 0)
        
        bar_x, bar_y, bar_width, bar_height = 75, pdf.get_y() + 1, 100, 4
        pdf.set_fill_color(240, 240, 240)
        pdf.rect(bar_x, bar_y, bar_width, bar_height, 'F')
        
        if valor > 0:
            pdf.set_fill_color(200, 50, 50)
            pdf.rect(bar_x, bar_y, min(valor, 25) * (bar_width / 100), bar_height, 'F')
        if valor > 25:
            pdf.set_fill_color(230, 190, 50)
            pdf.rect(bar_x + (25 * bar_width/100), bar_y, (min(valor, 70) - 25) * (bar_width / 100), bar_height, 'F')
        if valor > 70:
            pdf.set_fill_color(50, 160, 80)
            pdf.rect(bar_x + (70 * bar_width/100), bar_y, (min(valor, 90) - 70) * (bar_width / 100), bar_height, 'F')
        if valor > 90:
            pdf.set_fill_color(200, 50, 50)
            pdf.rect(bar_x + (90 * bar_width/100), bar_y, (valor - 90) * (bar_width / 100), bar_height, 'F')
            
        pdf.set_xy(bar_x + bar_width + 5, pdf.get_y())
        pdf.cell(20, 6, f"{valor}%", 0, 1)
        
        if rasgo in descarriladores_dict:
            tipo = descarriladores_dict[rasgo]['tipo']
            pdf.set_font('Arial', 'B', 9)
            pdf.set_text_color(200, 50, 50)
            pdf.set_x(75)
            pdf.cell(0, 5, f"ALERTA: Descarrilador por {tipo.upper()}", 0, 1)
            pdf.set_text_color(0, 0, 0)
        else:
            pdf.ln(2)
    pdf.ln(5)
    
    fortalezas = scores.get('fortalezas', [])
    if fortalezas:
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 6, "Fortalezas Consolidadas", 0, 1)
        pdf.set_font('Arial', '', 10)
        for i, f in enumerate(fortalezas[:3]):
            rasgo_k = f[0][0] if isinstance(f[0], tuple) else f[0]
            texto = TEXTOS_RASGOS[rasgo_k]
            pdf.multi_cell(0, 5, f"{i+1}. {texto['nombre']}: {texto['fortaleza']}")
        pdf.ln(3)
    
    areas = scores.get('areas_desarrollo', [])
    if areas:
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 6, "Areas de Desarrollo", 0, 1)
        pdf.set_font('Arial', '', 10)
        for i, a in enumerate(areas[:3]):
            rasgo_k = a[0][0] if isinstance(a[0], tuple) else a[0]
            texto = TEXTOS_RASGOS[rasgo_k]
            pdf.multi_cell(0, 5, f"{i+1}. {texto['nombre']}: {texto['area']}")
    
    pdf.add_page()
    pdf.draw_section_title("3. DIAGNOSTICO DE PATRONES Y RIESGOS")
    
    patrones = scores.get('patrones_clinicos', [])
    if not patrones:
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 6, "No existen patrones de riesgo detectados en este perfil.", 0, 1)
    else:
        for p in patrones:
            pdf.set_font('Arial', 'B', 11)
            pdf.set_text_color(200, 50, 50)
            pdf.cell(0, 6, p['nombre'].upper(), 0, 1)
            pdf.set_font('Arial', 'I', 10)
            pdf.set_text_color(80, 80, 80)
            pdf.multi_cell(0, 5, f"Combinacion: {p['combo']}")
            pdf.set_font('Arial', '', 10)
            pdf.set_text_color(0, 0, 0)
            pdf.multi_cell(0, 5, p['desc'])
            pdf.ln(4)

    pdf.ln(5)
    pdf.draw_section_title("4. CONCLUSION Y RECOMENDACION")
    
    pot, ire, delta = scores.get('potencial', 0), scores.get('ire', 0), scores.get('delta', 0)
    estado = "tecnicamente viable" if delta <= 20 else "con alto riesgo estructural"
    conclusion = f"El perfil es {estado}. La discrepancia entre Potencial ({pot}) e IRE ({ire}) marca el margen de mejora indicado en un Delta de ({delta}) repartido en varios rasgos."
    
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 5, conclusion)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.ln(2)
    pdf.cell(0, 6, "Recomendacion:", 0, 1)
    pdf.set_font('Arial', '', 10)
    
    if patrones:
        pdf.multi_cell(0, 5, f"Intervencion urgente requerida sobre el patron '{patrones[0]['nombre']}'. Se recomienda coaching focalizado para mitigar el impacto negativo de esta combinacion en el entorno de la startup.")
    elif areas:
        peor_area = TEXTOS_RASGOS[areas[0][0]]['nombre'] if not isinstance(areas[0], tuple) else TEXTOS_RASGOS[areas[0][0][0]]['nombre']
        pdf.multi_cell(0, 5, f"Se debe trabajar de forma prioritaria en reforzar: {peor_area}. El objetivo es equilibrar el perfil para evitar bloqueos operativos a medio plazo.")
    else:
        pdf.multi_cell(0, 5, "Mantener el equilibrio actual. Se recomienda monitorizacion periodica preventiva.")

    output = f"Informe_SAPE_{user_id}.pdf"
    pdf.output(output)
    return output