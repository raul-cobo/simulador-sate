import matplotlib.pyplot as plt
import numpy as np
from fpdf import FPDF
import os

# Textos extraídos del Documento Maestro Audeo
TRAIT_INFO = {
    "achievement": {
        "titulo": "Necesidad de Logro", 
        "desc": "El impulso intrínseco de sobresalir, alcanzar estándares de excelencia y esforzarse por tener éxito. No es ambición por poder, sino por superar retos."
    },
    "risk_propensity": {
        "titulo": "Propensión al Riesgo", 
        "desc": "La disposición a comprometer recursos en escenarios de resultado incierto. Es la capacidad cognitiva de calcular una oportunidad y actuar."
    },
    "innovativeness": {
        "titulo": "Innovatividad", 
        "desc": "La frecuencia y disposición para participar en nuevas ideas, experimentos y procesos creativos que resulten en innovación."
    },
    "locus_control": {
        "titulo": "Locus de Control Interno", 
        "desc": "La creencia firme de que los eventos son causados principalmente por las propias acciones y decisiones, asumiendo la responsabilidad."
    },
    "self_efficacy": {
        "titulo": "Autoeficacia", 
        "desc": "La convicción personal en la propia capacidad para organizar y ejecutar las acciones necesarias para gestionar situaciones futuras."
    },
    "autonomy": {
        "titulo": "Autonomía", 
        "desc": "La necesidad de independencia y libertad para decidir cómo, cuándo y con quién trabajar, evitando la microgestión."
    },
    "ambiguity_tolerance": {
        "titulo": "Tolerancia a la Incertidumbre", 
        "desc": "La capacidad de mantener una expectativa favorable y funcionar eficazmente en situaciones con información ambigua o incompleta."
    },
    "emotional_stability": {
        "titulo": "Estabilidad Emocional", 
        "desc": "La capacidad de mantener el equilibrio psicológico, la calma y el foco cognitivo bajo presión intensa o adversidad."
    }
}

class InformeAudeo(FPDF):
    def header(self):
        # 1. Franja oscura superior en todas las páginas
        self.set_fill_color(14, 17, 23) # #0E1117
        self.rect(0, 0, 210, 25, 'F')
        
        # Logo en la esquina izquierda del encabezado
        if os.path.exists('logo_blanco.png'):
            self.image('logo_blanco.png', 10, 5, 30)
            
        # Título a la derecha
        self.set_font('Arial', 'B', 14)
        self.set_text_color(255, 255, 255)
        self.set_y(10)
        self.cell(0, 5, 'INFORME TECNICO S.A.P.E.', 0, 1, 'R')
        self.ln(15) # Espacio de margen después del encabezado

    def footer(self):
        # Número de página abajo
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

def generar_pdf_sape(user_id, scores, alertas, demograficos):
    pdf = InformeAudeo()
    pdf.add_page()
    
    # --- DATOS DEMOGRÁFICOS ---
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(13, 36, 141) # Azul oscuro corporativo #0D248D
    pdf.cell(0, 10, 'DATOS DEL CANDIDATO', 0, 1)
    
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 6, f"Candidato: {user_id}", 0, 1)
    pdf.cell(0, 6, f"Organizacion: {demograficos.get('org', 'N/A')}", 0, 1)
    pdf.cell(0, 6, f"Edad: {demograficos.get('edad', 'N/A')} anos", 0, 1)
    
    exp_map = {'nunca': 'Nunca ha emprendido', 'sin_exito': 'He emprendido sin exito', 'con_exito': 'He emprendido con exito'}
    pdf.cell(0, 6, f"Historial: {exp_map.get(demograficos.get('exp'), 'N/A')}", 0, 1)
    pdf.ln(10)

    # --- EL OCTÓGONO (Gráfico Araña) ---
    if scores:
        pdf.set_font('Arial', 'B', 16)
        pdf.set_text_color(13, 36, 141)
        pdf.cell(0, 10, 'EL OCTOGONO DE COMPETENCIAS', 0, 1)
        pdf.ln(5)

        # Configuración del gráfico en fondo BLANCO
        labels = [TRAIT_INFO.get(k, {}).get("titulo", k) for k in scores.keys()]
        values = list(scores.values())
        num_vars = len(labels)
        angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
        values += values[:1]
        angles += angles[:1]

        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
        ax.fill(angles, values, color='#83ABF1', alpha=0.4)
        ax.plot(angles, values, color='#0D248D', linewidth=2)
        
        # Fondos claros
        ax.set_facecolor('white')
        fig.patch.set_facecolor('white')
        
        # Ajuste de etiquetas
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels, color='black', fontsize=9)
        ax.set_yticks([25, 50, 75, 100])
        ax.set_yticklabels(['25', '50', '75', '100'], color='grey', size=7)
        ax.spines['polar'].set_color('#CCCCCC')
        
        plt.tight_layout()
        plt.savefig('radar.png', dpi=150)
        plt.close()
        
        # Insertar imagen centrada
        pdf.image('radar.png', x=45, w=120)
        pdf.ln(5)

    # --- DESGLOSE DE DATOS REDACTADOS ---
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(13, 36, 141)
    pdf.cell(0, 10, 'ANALISIS DETALLADO DE RASGOS', 0, 1)
    pdf.ln(5)

    for trait, score in scores.items():
        info = TRAIT_INFO.get(trait, {"titulo": trait, "desc": "Sin descripcion."})
        
        # Título del rasgo + Puntuación
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(150, 8, info['titulo'], 0, 0)
        
        # Puntuación a la derecha
        pdf.set_text_color(13, 36, 141)
        pdf.cell(40, 8, f"{score}% de potencial", 0, 1, 'R')
        
        # Texto descriptivo
        pdf.set_font('Arial', '', 10)
        pdf.set_text_color(70, 70, 70)
        pdf.multi_cell(0, 6, info['desc'], 0, 1)
        
        # Barra de progreso visual
        pdf.set_fill_color(230, 230, 230)
        pdf.rect(pdf.get_x(), pdf.get_y() + 2, 190, 4, 'F') # Fondo gris
        pdf.set_fill_color(131, 171, 241) # Acento azul
        pdf.rect(pdf.get_x(), pdf.get_y() + 2, 190 * (score / 100), 4, 'F') # Relleno
        pdf.ln(10)

    # --- ALERTAS CRÍTICAS ---
    if alertas:
        pdf.ln(5)
        pdf.set_font('Arial', 'B', 16)
        pdf.set_text_color(200, 50, 50) # Rojo
        pdf.cell(0, 10, 'ALERTAS DE RIESGO DETECTADAS', 0, 1)
        pdf.ln(5)
        
        for a in alertas:
            pdf.set_fill_color(255, 240, 240) # Fondo rojizo claro
            pdf.set_font('Arial', 'B', 12)
            pdf.set_text_color(200, 0, 0)
            pdf.cell(0, 8, f">> {a['titulo']}", 0, 1, fill=True)
            
            pdf.set_font('Arial', '', 11)
            pdf.set_text_color(50, 50, 50)
            pdf.multi_cell(0, 6, a['desc'], 0, 1, fill=True)
            pdf.ln(4)

    output = f"Informe_SAPE_{user_id}.pdf"
    pdf.output(output)
    return output