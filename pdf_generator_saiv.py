# pdf_generator_saiv.py
from fpdf import FPDF
import os
from datetime import datetime
from typing import Dict, Any

# ==========================================\r
# 1. DICCIONARIO DE DEFINICIONES RIASEC (TCASEO)\r
# ==========================================\r
RIASEC_DESC = {
    'T': {
        'nombre': 'Realista (Técnico)',
        'desc': 'Preferencia por actividades prácticas y tangibles. Disfrutas trabajando con herramientas, máquinas, o en entornos físicos y operativos.',
        'roles': 'Ingeniería, Operaciones, Mantenimiento, Arquitectura de Hardware.'
    },
    'C': {
        'nombre': 'Investigador (Científico)',
        'desc': 'Fuerte inclinación hacia la observación, el análisis y la resolución de problemas complejos o abstractos mediante la lógica.',
        'roles': 'Data Science, I+D, Estrategia Analítica, Investigación.'
    },
    'A': {
        'nombre': 'Artístico',
        'desc': 'Alta necesidad de expresión creativa, innovación y diseño. Prefieres entornos de trabajo no estructurados donde fluya la imaginación.',
        'roles': 'Diseño UX/UI, Dirección Creativa, Creación de Contenido, Marketing Visual.'
    },
    'S': {
        'nombre': 'Social',
        'desc': 'Motivación genuina por informar, formar, desarrollar, curar o guiar a otras personas. Tu foco principal es el bienestar y la interacción humana.',
        'roles': 'Recursos Humanos, Mentoría, Customer Success, Gestión de Comunidades.'
    },
    'E': {
        'nombre': 'Emprendedor',
        'desc': 'Disfrutas asumiendo riesgos, liderando equipos, persuadiendo a otros y gestionando proyectos para alcanzar metas económicas u organizacionales.',
        'roles': 'Desarrollo de Negocio, Dirección General (CEO), Ventas, Management.'
    },
    'O': {
        'nombre': 'Convencional (Organizativo)',
        'desc': 'Habilidad para el orden, la sistematización, el trabajo con datos precisos y el cumplimiento de procedimientos establecidos.',
        'roles': 'Finanzas, Administración, Control de Calidad, Auditoría.'
    }
}

class PDF_SAIV(FPDF):
    def header(self):
        # Fondo oscuro para la cabecera
        self.set_fill_color(14, 17, 23) # #0E1117
        self.rect(0, 0, 210, 30, 'F')
        
        self.set_y(12)
        self.set_font('Arial', 'B', 20)
        self.set_text_color(131, 171, 241) # #83ABF1
        self.cell(0, 10, 'INFORME VOCACIONAL S.A.I.V.', 0, 1, 'C')

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Generado por Audeo - Plataforma de Evaluación - Página {self.page_no()}', 0, 0, 'C')

def generar_informe_saiv(user_info: Dict[str, Any], results: Dict[str, Any]) -> str:
    """
    Genera el PDF del informe vocacional SAIV.
    Retorna la ruta absoluta del archivo generado.
    """
    pdf = PDF_SAIV()
    pdf.add_page()
    
    metrics = results.get('metrics', {})
    riasec_code = results.get('riasec_code', '---')
    
    # ---------------------------------------------------------
    # SECCIÓN 1: DATOS DEL USUARIO
    # ---------------------------------------------------------
    pdf.set_y(40)
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(50, 8, 'Candidato / Usuario:', 0, 0)
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 8, str(user_info.get('username', 'Usuario_Demo')), 0, 1)
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(50, 8, 'Fecha de Evaluacion:', 0, 0)
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 8, datetime.now().strftime('%d/%m/%Y'), 0, 1)
    pdf.ln(5)

    # ---------------------------------------------------------
    # SECCIÓN 2: EL CÓDIGO RIASEC DOMINANTE
    # ---------------------------------------------------------
    pdf.set_fill_color(13, 36, 141) # #0D248D
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 15, f'  TU CODIGO VOCACIONAL DOMINANTE: {riasec_code}', 0, 1, 'C', 1)
    pdf.ln(10)

    # ---------------------------------------------------------
    # SECCIÓN 3: DISTRIBUCIÓN DE INTERESES (BARRAS)
    # ---------------------------------------------------------
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'Distribucion de Intereses (0% - 100%)', 0, 1, 'L')
    pdf.set_font('Arial', '', 11)
    
    # Orden tradicional para mostrar
    orden_letras = ['T', 'C', 'A', 'S', 'E', 'O']
    
    for letra in orden_letras:
        if letra in metrics:
            nombre = RIASEC_DESC[letra]['nombre']
            pct = metrics[letra]['percentage']
            
            # Fila de texto
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(60, 8, nombre, 0, 0)
            
            # Barra visual (simulada con rectángulos en FPDF)
            x_start = pdf.get_x()
            y_start = pdf.get_y() + 2
            
            # Fondo de la barra (gris claro)
            pdf.set_fill_color(230, 230, 230)
            pdf.rect(x_start, y_start, 100, 4, 'F')
            
            # Relleno de la barra (azul)
            if pct > 0:
                pdf.set_fill_color(131, 171, 241)
                pdf.rect(x_start, y_start, pct, 4, 'F')
            
            pdf.set_x(x_start + 105)
            pdf.set_font('Arial', '', 10)
            pdf.cell(20, 8, f'{pct}%', 0, 1)

    pdf.ln(10)

    # ---------------------------------------------------------
    # SECCIÓN 4: ANÁLISIS DE LAS 3 DIMENSIONES TOP
    # ---------------------------------------------------------
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'Analisis de tu Perfil Principal', 'B', 1, 'L')
    pdf.ln(5)

    if len(riasec_code) == 3:
        for idx, letra in enumerate(riasec_code):
            desc_data = RIASEC_DESC.get(letra, {})
            nombre = desc_data.get('nombre', '')
            desc = desc_data.get('desc', '')
            roles = desc_data.get('roles', '')
            
            pdf.set_font('Arial', 'B', 12)
            pdf.set_text_color(13, 36, 141)
            pdf.cell(0, 8, f"{idx+1}. {nombre} ({letra})", 0, 1)
            
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Arial', '', 11)
            pdf.multi_cell(0, 6, desc)
            
            pdf.set_font('Arial', 'I', 10)
            pdf.set_text_color(100, 100, 100)
            pdf.multi_cell(0, 6, f"Roles afines: {roles}")
            pdf.ln(4)

    # ---------------------------------------------------------
    # SECCIÓN 5: LEGAL Y METODOLOGÍA
    # ---------------------------------------------------------
    pdf.set_y(-50)
    pdf.set_font('Arial', 'B', 8)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, 'NOTA METODOLOGICA Y LEGAL', 0, 1)
    pdf.set_font('Arial', '', 7)
    legal_text = (
        "Este informe ha sido generado de forma automatizada mediante el Sistema de Actitudes e Intereses Vocacionales (SAIV), "
        "basado en el modelo tipologico de John Holland (RIASEC). Los resultados son de caracter orientativo e indican preferencias "
        "o tendencias vocacionales, no habilidades innatas ni pronosticos definitivos de exito profesional.\n"
        "De conformidad con el Art. 22 del RGPD, este informe no constituye una decision automatizada con efectos juridicos "
        "vinculantes y debe ser interpretado como una herramienta de apoyo al desarrollo personal y profesional."
    )
    pdf.multi_cell(0, 4, legal_text)

    # ---------------------------------------------------------
    # GUARDADO DEL ARCHIVO
    # ---------------------------------------------------------
    filename = f"Informe_SAIV_{user_info.get('username', 'User')}_{datetime.now().strftime('%Y%m%d%H%M')}.pdf"
    filename = filename.replace(" ", "_").replace("/", "-")
    filepath = os.path.join(os.getcwd(), filename)
    
    pdf.output(filepath)
    return filepath