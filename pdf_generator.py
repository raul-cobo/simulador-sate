import matplotlib.pyplot as plt
import numpy as np
from fpdf import FPDF
import os

# Textos extraídos del Documento Maestro Audeo
TRAIT_INFO = {
    "achievement": {
        "titulo": "Necesidad de Logro", 
        "desc": "El impulso intrinseco de sobresalir, alcanzar estandares de excelencia y esforzarse por tener exito."
    },
    "risk_propensity": {
        "titulo": "Propension al Riesgo", 
        "desc": "La disposicion a comprometer recursos en escenarios de resultado incierto. Capacidad de calcular y actuar."
    },
    "innovativeness": {
        "titulo": "Innovatividad", 
        "desc": "La frecuencia y disposicion para participar en nuevas ideas, experimentos y procesos creativos."
    },
    "locus_control": {
        "titulo": "Locus de Control Interno", 
        "desc": "La creencia firme de que los eventos son causados principalmente por las propias acciones y decisiones."
    },
    "self_efficacy": {
        "titulo": "Autoeficacia", 
        "desc": "La conviccion personal en la propia capacidad para organizar y ejecutar las acciones necesarias."
    },
    "autonomy": {
        "titulo": "Autonomia", 
        "desc": "La necesidad de independencia y libertad para decidir como, cuando y con quien trabajar."
    },
    "ambiguity_tolerance": {
        "titulo": "Tolerancia a la Incertidumbre", 
        "desc": "La capacidad de mantener una expectativa favorable y funcionar eficazmente con informacion ambigua."
    },
    "emotional_stability": {
        "titulo": "Estabilidad Emocional", 
        "desc": "La capacidad de mantener el equilibrio psicologico, la calma y el foco cognitivo bajo presion."
    }
}

class InformeAudeo(FPDF):
    def header(self):
        # Franja oscura superior
        self.set_fill_color(14, 17, 23)
        self.rect(0, 0, 210, 25, 'F')
        
        # Logo (Si existe)
        if os.path.exists('logo_blanco.png'):
            self.image('logo_blanco.png', 10, 5, 30)
            
        self.set_font('Arial', 'B', 14)
        self.set_text_color(255, 255, 255)
        self.set_y(10)
        self.cell(0, 5, 'INFORME TECNICO S.A.P.E.', 0, 1, 'R')
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

def generar_pdf_sape(user_id, scores, alertas, demograficos):
    pdf = InformeAudeo()
    pdf.add_page()
    
    # --- DATOS DEMOGRÁFICOS ---
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(13, 36, 141)
    pdf.cell(0, 10, 'DATOS DEL CANDIDATO', 0, 1)
    
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 6, f"Candidato: {user_id}", 0, 1)
    pdf.cell(0, 6, f"Organizacion: {demograficos.get('org', 'N/A')}", 0, 1)
    
    exp_map = {'nunca': 'Nunca ha emprendido', 'sin_exito': 'He emprendido sin exito', 'con_exito': 'He emprendido con exito'}
    pdf.cell(0, 6, f"Historial: {exp_map.get(demograficos.get('exp'), 'N/A')}", 0, 1)
    pdf.ln(8)

    # --- NUEVO: RESUMEN EJECUTIVO ---
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(13, 36, 141)
    pdf.cell(0, 10, 'RESUMEN METRICAS AUDEO', 0, 1)
    
    pdf.set_font('Arial', 'B', 11)
    
    # Fila IRE
    pdf.set_text_color(50, 50, 50)
    pdf.cell(80, 7, "Indice de Resiliencia (IRE):", 0, 0)
    pdf.set_text_color(13, 36, 141)
    pdf.cell(0, 7, f"{scores.get('ire', 'N/A')}%", 0, 1)
    
    # Fila Fricción
    pdf.set_text_color(50, 50, 50)
    pdf.cell(80, 7, "Friccion (Defecto / Exceso):", 0, 0)
    pdf.set_text_color(13, 36, 141)
    pdf.cell(0, 7, f"{scores.get('friccion_defecto', 'N/A')} / {scores.get('friccion_exceso', 'N/A')}", 0, 1)

    # Fila Delta
    pdf.set_text_color(50, 50, 50)
    pdf.cell(80, 7, "Indice Delta (Desviacion):", 0, 0)
    pdf.set_text_color(13, 36, 141)
    pdf.cell(0, 7, f"{scores.get('delta', 'N/A')}", 0, 1)
    pdf.ln(8)

    # --- EL OCTÓGONO (Gráfico Araña) ---
    rasgos_keys = ['achievement', 'risk_propensity', 'innovativeness', 'locus_control', 
                   'self_efficacy', 'autonomy', 'ambiguity_tolerance', 'emotional_stability']
    
    # Filtramos solo los 8 rasgos para el gráfico
    scores_grafico = {k: scores.get(k, 50.0) for k in rasgos_keys}
    
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(13, 36, 141)
    pdf.cell(0, 10, 'EL OCTOGONO DE COMPETENCIAS', 0, 1)
    pdf.ln(2)

    labels = [TRAIT_INFO.get(k, {}).get("titulo", k) for k in rasgos_keys]
    values = list(scores_grafico.values())
    num_vars = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    values += values[:1]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
    ax.fill(angles, values, color='#83ABF1', alpha=0.4)
    ax.plot(angles, values, color='#0D248D', linewidth=2)
    
    ax.set_facecolor('white')
    fig.patch.set_facecolor('white')
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, color='black', fontsize=8)
    ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(['25', '50', '75', '100'], color='grey', size=7)
    ax.spines['polar'].set_color('#CCCCCC')
    
    plt.tight_layout()
    plt.savefig('radar.png', dpi=150)
    plt.close()
    
    pdf.image('radar.png', x=50, w=110)
    pdf.ln(5)

    # --- DESGLOSE DE DATOS REDACTADOS ---
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(13, 36, 141)
    pdf.cell(0, 10, 'ANALISIS DETALLADO DE RASGOS', 0, 1)
    pdf.ln(5)

    for trait in rasgos_keys:
        score = scores.get(trait, 50.0)
        info = TRAIT_INFO.get(trait, {"titulo": trait, "desc": "Sin descripcion."})
        
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(150, 8, info['titulo'], 0, 0)
        
        pdf.set_text_color(13, 36, 141)
        pdf.cell(40, 8, f"{score}%", 0, 1, 'R')
        
        pdf.set_font('Arial', '', 10)
        pdf.set_text_color(70, 70, 70)
        pdf.multi_cell(0, 6, info['desc'], 0, 1)
        
        pdf.set_fill_color(230, 230, 230)
        pdf.rect(pdf.get_x(), pdf.get_y() + 2, 190, 4, 'F')
        pdf.set_fill_color(131, 171, 241)
        pdf.rect(pdf.get_x(), pdf.get_y() + 2, 190 * (score / 100), 4, 'F')
        pdf.ln(10)

    # --- ALERTAS CRÍTICAS (DESCARRILADORES) ---
    if alertas:
        pdf.ln(5)
        pdf.set_font('Arial', 'B', 16)
        pdf.set_text_color(200, 50, 50)
        pdf.cell(0, 10, 'ALERTAS Y DESCARRILADORES', 0, 1)
        pdf.ln(5)
        
        for a in alertas:
            pdf.set_fill_color(255, 240, 240)
            pdf.set_font('Arial', 'B', 11)
            pdf.set_text_color(200, 0, 0)
            pdf.multi_cell(0, 8, f">> {a}", 0, 1, fill=True)
            pdf.ln(2)

    output = f"Informe_SAPE_{user_id}.pdf"
    pdf.output(output)
    return output