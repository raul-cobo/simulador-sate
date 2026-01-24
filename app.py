import streamlit as st
import csv
import os
import random
import string
import io
import textwrap
from datetime import datetime
import plotly.graph_objects as go
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Audeo | Simulador S.A.P.E.", page_icon="🧬", layout="wide")

# --- 2. GESTIÓN DE ESTILOS (V35) ---
def inject_style(mode):
    # CSS BASE
    base_css = """
        header, [data-testid="stHeader"], .stAppHeader { display: none !important; }
        div[data-testid="stDecoration"] { display: none !important; }
        footer { display: none !important; }
        .main .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; max-width: 95% !important; }
    """
    
    if mode == "login":
        theme_css = """
            .stApp { background-color: #FFFFFF !important; color: #000000 !important; }
            h1, h2, h3, h4, p, label, div[data-testid="stMarkdownContainer"] p { 
                color: #0E1117 !important; font-family: 'Helvetica', sans-serif;
            }
            .stTextInput input { background-color: #F8F9FA !important; color: #000000 !important; border: 1px solid #E0E0E0 !important; }
            .stButton > button {
                background-color: #050A1F !important; color: #FFFFFF !important; border: 1px solid #050A1F !important;
                border-radius: 8px !important; font-weight: bold !important; width: 100%; padding: 0.5rem 1rem;
            }
            .stButton > button:hover { background-color: #5D5FEF !important; border-color: #5D5FEF !important; }
            .stButton > button p { color: #FFFFFF !important; }
            .login-title { color: #050A1F !important; font-size: 2rem !important; font-weight: 800 !important; text-align: center; margin: 0 !important; }
            .login-subtitle { color: #666666 !important; font-size: 1rem !important; text-align: center; margin-bottom: 2rem !important; }
            .login-card { padding: 1rem; text-align: center; }
        """
    else:
        theme_css = """
            .stApp { background-color: #050A1F !important; color: #FFFFFF !important; }
            h1, h2, h3, h4, p, label, span, div[data-testid="stMarkdownContainer"] p { color: #FFFFFF !important; }
            .stTextInput input, .stNumberInput input, .stSelectbox > div > div {
                background-color: #0F1629 !important; color: #FFFFFF !important; border: 1px solid #5D5FEF !important;
            }
            div[role="listbox"] div { background-color: #0F1629 !important; color: white !important; }
            .stCheckbox label p { color: white !important; }
            .stButton > button { background-color: #1A202C !important; color: white !important; border: 1px solid #5D5FEF !important; border-radius: 8px; }
            .stButton > button:hover { border-color: white !important; background-color: #5D5FEF !important; }
            
            div[data-testid="column"] button {
                 height: 180px !important; min-height: 180px !important;
                 background-color: #0F1629 !important; border: 2px solid #2D3748 !important;
                 color: white !important; font-size: 26px !important; font-weight: 700 !important; line-height: 1.3 !important;
                 border-radius: 16px !important; white-space: pre-wrap !important; 
                 display: flex !important; align-items: center !important; justify-content: center !important;
                 margin-bottom: 1rem !important; box-shadow: 0 4px 6px rgba(0,0,0,0.3) !important;
            }
            div[data-testid="column"] button:hover { border-color: #5D5FEF !important; background-color: #1a2236 !important; transform: translateY(-2px); }
            div[data-testid="column"] button:disabled { border-color: #2D3748 !important; opacity: 0.6; cursor: not-allowed; }

            .header-title-text { font-size: 3.5rem !important; font-weight: 800 !important; color: white !important; margin: 0; line-height: 1.1; }
            .header-sub-text { font-size: 1.5rem !important; color: #5D5FEF !important; margin: 0; font-weight: 500; }
            .diag-text { background-color: #0F1629; padding: 15px; border-radius: 8px; border-left: 4px solid #5D5FEF; }
            .stDownloadButton > button { background-color: #5D5FEF !important; color: white !important; border: none !important; font-weight: bold !important; }
        """
    st.markdown(f"<style>{base_css}\n{theme_css}</style>", unsafe_allow_html=True)

# --- 3. LÓGICA Y VARIABLES (BASE DE DATOS ENRIQUECIDA) ---
LABELS_ES = { "achievement": "Necesidad de Logro", "risk_propensity": "Propensión al Riesgo", "innovativeness": "Innovatividad", "locus_control": "Locus de Control Interno", "self_efficacy": "Autoeficacia", "autonomy": "Autonomía", "ambiguity_tolerance": "Tol. Ambigüedad", "emotional_stability": "Estabilidad Emocional" }

SECTOR_ADVICE_DB = {
    "TECH": "En el ecosistema Startup/Scalable, la velocidad de iteración es el activo crítico. Tu perfil debe priorizar la 'Innovatividad' y la 'Tolerancia a la Ambigüedad' para pivotar ágilmente. Vigila no caer en 'parálisis por análisis' técnico.",
    "CONSULTORIA": "En Servicios Profesionales, la 'Estabilidad Emocional' y el 'Logro' son fundamentales para gestionar la presión del cliente y los plazos. La reputación personal es el activo; cuida la fricción relacional.",
    "PYME": "La gestión PYME requiere un equilibrio pragmático entre 'Autonomía' y control financiero. La consistencia operativa diaria supera a la disrupción constante. Se recomienda foco en la sostenibilidad.",
    "HOSTELERIA": "Sector de alta reactividad inmediata. Requiere máxima 'Estabilidad Emocional' y capacidad de resolución de conflictos en tiempo real. El equipo es el pilar; el liderazgo debe ser cercano pero firme.",
    "AUTOEMPLEO": "Como profesional independiente, tu 'Autoeficacia' y 'Locus de Control' son el motor único. No hay estructura externa que empuje. Cuidado con el aislamiento y la dilución de objetivos.",
    "SOCIAL": "El impacto social requiere resiliencia a largo plazo. Tu 'Necesidad de Logro' debe medirse en impacto tangible, no solo financiero, manteniendo la viabilidad económica del proyecto.",
    "INTRA": "El intraemprendimiento exige diplomacia corporativa. La 'Innovatividad' debe ir acompañada de inteligencia política para navegar la burocracia interna sin perder tracción.",
    "SALUD": "Sector de tolerancia cero al error. La 'Propensión al Riesgo' debe ser moderada y controlada. La 'Diligencia' y la ética profesional son innegociables para generar confianza en el paciente."
}

# NARRATIVAS TÉCNICAS/CLÍNICAS (MEJORADAS V35)
NARRATIVES_DB = {
    "emotional_stability": { 
        "high": "El sujeto demuestra una capacidad absoluta para mantener la regulación emocional bajo presión. Indica una gestión óptima del estrés alostático y una nula reactividad impulsiva ante crisis.", 
        "low": "Se detecta vulnerabilidad ante la presión sostenida. Existe riesgo de desbordamiento cognitivo en situaciones de crisis, lo que podría afectar a la toma de decisiones críticas en caliente." 
    },
    "autonomy": { 
        "high": "El sujeto muestra una fuerte independencia operativa y de criterio. No requiere supervisión externa y posee la iniciativa necesaria para liderar sin directrices previas.", 
        "low": "Dependencia operativa significativa. El perfil tiende a buscar validación externa o consenso antes de actuar, lo que puede ralentizar la velocidad de ejecución." 
    },
    "achievement": { 
        "high": "Existe una clara orientación a resultados y estándares de excelencia. El sujeto prioriza la finalización de tareas y la consecución de objetivos sobre la mera actividad.", 
        "low": "Baja orientación a resultados finales. Puede haber tendencia a la dispersión o a la satisfacción con estándares medios, comprometiendo la competitividad del proyecto." 
    },
    "risk_propensity": { 
        "high": "Alta tolerancia a la incertidumbre financiera y operativa. El sujeto está dispuesto a comprometer recursos actuales por expectativas futuras, asumiendo la posibilidad de pérdida.", 
        "low": "Perfil conservador. El sujeto prioriza la seguridad y la preservación de recursos. Puede mostrar aversión a decisiones que impliquen volatilidad no controlada." 
    },
    "ambiguity_tolerance": { 
        "high": "Alta capacidad de gestión del caos y la falta de información. El sujeto opera con eficacia en entornos donde las reglas no están definidas o cambian constantemente.", 
        "low": "Necesidad de estructura clara. En fases iniciales de alta volatilidad, esta necesidad de certeza puede derivar en bloqueos operativos o ansiedad por falta de datos." 
    },
    "innovativeness": { 
        "high": "Perfil disruptivo y creativo. Tendencia natural a cuestionar el status quo y buscar soluciones no convencionales. Motor de diferenciación en el mercado.", 
        "low": "Orientación a procesos establecidos. El perfil tiende a la optimización de lo existente más que a la creación de nuevos paradigmas. Eficaz en gestión, cauto en disrupción." 
    },
    "locus_control": { 
        "high": "Locus Interno fuerte. El sujeto asume la responsabilidad total de los resultados, atribuyendo el éxito o fracaso a su propia gestión y no a factores externos.", 
        "low": "Tendencia a atribuir resultados a factores externos (suerte, mercado, terceros). Esto puede limitar la capacidad de aprendizaje y corrección de errores." 
    },
    "self_efficacy": { 
        "high": "Confianza sólida en las propias capacidades técnicas y de gestión. El sujeto se percibe capaz de afrontar los desafíos del sector, lo que favorece la persistencia.", 
        "low": "Dudas sobre la propia capacidad. Puede manifestarse como síndrome del impostor o vacilación ante retos de gran envergadura." 
    }
}
VARIABLE_MAP = { "achievement": "achievement", "logro": "achievement", "risk_propensity": "risk_propensity", "riesgo": "risk_propensity", "innovativeness": "innovativeness", "innovacion": "innovativeness", "locus_control": "locus_control", "locus": "locus_control", "self_efficacy": "self_efficacy", "autoeficacia": "self_efficacy", "collaboration": "self_efficacy", "autonomy": "autonomy", "autonomia": "autonomy", "ambiguity_tolerance": "ambiguity_tolerance", "tolerancia": "ambiguity_tolerance", "imaginative": "ambiguity_tolerance", "emotional_stability": "emotional_stability", "estabilidad": "emotional_stability", "excitable": "excitable", "skeptical": "skeptical", "cautious": "cautious", "reserved": "reserved", "passive_aggressive": "passive_aggressive", "arrogant": "arrogant", "mischievous": "mischievous", "melodramatic": "melodramatic", "diligent": "diligent", "dependent": "dependent" }
SECTOR_MAP = { "Startup Tecnológica (Scalable)": "TECH", "Consultoría / Servicios Profesionales": "CONSULTORIA", "Pequeña y Mediana Empresa (PYME)": "PYME", "Hostelería y Restauración": "HOSTELERIA", "Autoempleo / Freelance": "AUTOEMPLEO", "Emprendimiento Social": "SOCIAL", "Intraemprendimiento": "INTRA", "Salud": "SALUD" }

def generate_id(): return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
def init_session():
    if 'octagon' not in st.session_state:
        st.session_state.octagon = {k: 50 for k in LABELS_ES.keys()}
        st.session_state.flags = {k: 0 for k in ["excitable", "skeptical", "cautious", "reserved", "passive_aggressive", "arrogant", "mischievous", "melodramatic", "diligent", "dependent"]}
        st.session_state.current_step = 0; st.session_state.finished = False; st.session_state.started = False; st.session_state.data_verified = False; st.session_state.data = []; st.session_state.user_id = generate_id(); st.session_state.user_data = {}

def load_questions():
    try:
        filename = 'SATE_v1.csv'
        if not os.path.exists(filename): return []
        with open(filename, encoding='utf-8-sig') as f: return list(csv.DictReader(f, delimiter=';'))
    except: return []

def parse_logic(logic_str):
    if not logic_str: return
    for action in logic_str.split('|'):
        parts = action.strip().split()
        if len(parts) < 2: continue
        var_code = parts[0].lower().strip()
        try: val = int(parts[1])
        except: continue
        target = VARIABLE_MAP.get(var_code)
        if target:
            if target in st.session_state.octagon: st.session_state.octagon[target] = max(0, min(100, st.session_state.octagon[target] + val))
            elif target in st.session_state.flags: st.session_state.flags[target] = max(0, st.session_state.flags[target] + val)

def calculate_results():
    o, f = st.session_state.octagon, st.session_state.flags
    avg = sum(o.values()) / 8
    friction = sum(f.values()) * 0.5
    triggers = []
    friction_reasons = []
    if f["cautious"] > 10 or f["diligent"] > 10: friction_reasons.append("Prudencia Administrativa: Prioriza seguridad jurídica.")
    if f["dependent"] > 10 or f["skeptical"] > 10: friction_reasons.append("Exceso de Validación: Busca confirmación externa.")
    if f["arrogant"] > 20: friction_reasons.append("Rigidez Cognitiva: Dificultad para pivotar.")
    if f["mischievous"] > 25: triggers.append("Riesgo de Desalineamiento Normativo")
    if f["arrogant"] > 25: triggers.append("Estilo Dominante")
    if f["passive_aggressive"] > 20: triggers.append("Fricción Relacional")
    if o["achievement"] > 85 and o["emotional_stability"] < 40: triggers.append("Riesgo de Burnout")
    if o["risk_propensity"] > 85 and f["cautious"] < 10: triggers.append("Perfil de Riesgo Desmedido")
    ire = max(0, min(100, avg - (friction * 0.8) - (len(triggers) * 3)))
    delta = round(avg - ire, 2)
    return round(ire, 2), round(avg, 2), round(friction, 2), triggers, friction_reasons, delta

# --- FUNCIONES GRÁFICAS Y TEXTOS ---
def get_ire_text(s): return "Nivel de Viabilidad Positivo" if s > 75 else "Nivel de Viabilidad Medio" if s > 50 else "Nivel Comprometido"
def get_potential_text(s): return "Nivel Notable" if s > 75 else "Nivel Medio" if s > 50 else "Nivel Bajo"
def get_friction_text(s): return "Bajo" if s < 20 else "Medio" if s < 40 else "Alto"

def radar_chart():
    data = st.session_state.octagon
    cat = [LABELS_ES.get(k) for k in data.keys()]
    val = list(data.values())
    cat += [cat[0]]; val += [val[0]]
    fig = go.Figure(go.Scatterpolar(r=val, theta=cat, fill='toself', line=dict(color='#5D5FEF'), fillcolor='rgba(93, 95, 239, 0.2)'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, showticklabels=False), bgcolor='rgba(0,0,0,0)'), paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'), showlegend=False, margin=dict(l=40, r=40, t=20, b=20), dragmode=False)
    return fig

# --- PDF GENERATOR (V35 - PROFESIONAL) ---
def draw_wrapped_text(c, text, x, y, max_width, font_name, font_size, line_spacing=12):
    c.setFont(font_name, font_size)
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        width = c.stringWidth(" ".join(current_line), font_name, font_size)
        if width > max_width: current_line.pop(); lines.append(" ".join(current_line)); current_line = [word]
    lines.append(" ".join(current_line))
    for line in lines: 
        c.drawString(x, y, line)
        y -= line_spacing
    return y 

def check_page_break(c, y, h, w):
    if y < 80:
        c.showPage()
        draw_pdf_header(c, w, h)
        return h - 140
    return y

def draw_pdf_header(p, w, h):
    p.setFillColorRGB(0.02, 0.04, 0.12)
    p.rect(0, h-100, w, 100, fill=1, stroke=0)
    p.setFillColorRGB(1, 1, 1)
    p.rect(30, h-85, 140, 70, fill=1, stroke=0)
    if os.path.exists("logo_original.png"):
        try: 
            img = ImageReader("logo_original.png")
            p.drawImage(img, 40, h-80, width=120, height=60, preserveAspectRatio=True, mask='auto')
        except: pass
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 16)
    p.drawRightString(w-30, h-40, "INFORME TÉCNICO S.A.P.E.")
    p.setFont("Helvetica", 10)
    p.drawRightString(w-30, h-55, "Sistema de Análisis de la Personalidad Emprendedora")

def create_pdf_report(ire, avg, friction, triggers, friction_reasons, delta, user, stats):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    
    draw_pdf_header(p, w, h)
    
    # INFO CABECERA
    y = h - 130
    p.setFillColorRGB(0,0,0)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(40, y, f"Candidato: {user.get('name', 'N/A')}")
    p.drawString(300, y, f"ID: {st.session_state.user_id}")
    y -= 15
    p.drawString(40, y, f"Sector: {user.get('sector', 'N/A')}")
    p.drawString(300, y, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}")
    y -= 40
    
    # 1. MÉTRICAS
    p.setFont("Helvetica-Bold", 12)
    p.setFillColorRGB(0.02, 0.04, 0.12)
    p.drawString(40, y, "1. MÉTRICAS PRINCIPALES")
    p.line(40, y-5, w-40, y-5)
    y -= 30
    
    # Textos ricos para métricas
    p.setFont("Helvetica-Bold", 10); p.drawString(50, y, f"POTENCIAL ({avg}/100):"); p.setFont("Helvetica", 10); 
    desc_pot = "Capacidad basal superior a la media." if avg > 75 else "Recursos cognitivos y actitudinales adecuados." if avg > 50 else "Se sugiere refuerzo en competencias clave."
    p.drawString(200, y, desc_pot); y-=20
    
    p.setFont("Helvetica-Bold", 10); p.drawString(50, y, f"FRICCIÓN ({friction}):"); p.setFont("Helvetica", 10); 
    desc_fric = "Resistencia operativa moderada/baja." if friction < 30 else "Resistencia operativa significativa que puede lastrar la ejecución."
    p.drawString(200, y, desc_fric); y-=20
    
    p.setFont("Helvetica-Bold", 10); p.drawString(50, y, f"IRE FINAL ({ire}/100):"); p.setFont("Helvetica", 10); 
    desc_ire = "El índice confirma viabilidad y sostenibilidad." if ire > 60 else "El índice sugiere precaución en la viabilidad a largo plazo."
    p.drawString(200, y, desc_ire); y-=30
    
    # 2. ANÁLISIS VISUAL
    y = check_page_break(p, y, h, w)
    p.setFont("Helvetica-Bold", 12)
    p.drawString(40, y, "2. PERFIL COMPETENCIAL (VISUAL)")
    p.line(40, y-5, w-40, y-5)
    y -= 30
    
    sorted_stats = sorted(stats.items(), key=lambda item: item[1], reverse=True)
    
    for k, v in sorted_stats:
        y = check_page_break(p, y, h, w)
        p.setFont("Helvetica-Bold", 9)
        p.setFillColorRGB(0,0,0)
        p.drawString(50, y, LABELS_ES.get(k, k))
        
        # Barra de progreso
        p.setFillColorRGB(0.9, 0.9, 0.9)
        p.rect(200, y, 150, 8, fill=1, stroke=0)
        bar_len = (v/100)*150
        
        # Color Semáforo (Rango Óptimo: 60-75)
        if v > 75: p.setFillColorRGB(0.8, 0.2, 0.2) # Exceso
        elif v >= 60: p.setFillColorRGB(0.2, 0.6, 0.2) # Óptimo
        elif v >= 25: p.setFillColorRGB(0.9, 0.7, 0.0) # Alerta
        else: p.setFillColorRGB(0.8, 0.2, 0.2) # Defecto
            
        p.rect(200, y, bar_len, 8, fill=1, stroke=0)
        p.setFillColorRGB(0,0,0)
        p.drawString(360, y, str(round(v, 1)))
        y -= 15
        
    y -= 20
    
    # 2.1 ANÁLISIS CUALITATIVO (TEXTO DETALLADO)
    y = check_page_break(p, y, h, w)
    p.setFont("Helvetica-Bold", 12)
    p.setFillColorRGB(0.02, 0.04, 0.12)
    p.drawString(40, y, "3. INTERPRETACIÓN CUALITATIVA")
    p.line(40, y-5, w-40, y-5)
    y -= 30
    
    # Fortalezas (Top 3)
    p.setFont("Helvetica-Bold", 11); p.setFillColorRGB(0,0,0); p.drawString(40, y, "Fortalezas Consolidadas"); y -= 20
    p.setFont("Helvetica", 10)
    for k, v in sorted_stats[:3]:
        y = check_page_break(p, y, h, w)
        p.setFont("Helvetica-Bold", 10)
        p.drawString(50, y, f"{LABELS_ES.get(k)} ({round(v)}):")
        y -= 12
        narrative = NARRATIVES_DB.get(k, {}).get('high', '')
        y = draw_wrapped_text(p, narrative, 50, y, 480, "Helvetica", 9)
        y -= 10
        
    y -= 10
    # Áreas de Desarrollo (Bottom 3)
    y = check_page_break(p, y, h, w)
    p.setFont("Helvetica-Bold", 11); p.drawString(40, y, "Áreas Críticas de Desarrollo"); y -= 20
    for k, v in sorted_stats[-3:]:
        y = check_page_break(p, y, h, w)
        p.setFont("Helvetica-Bold", 10)
        p.drawString(50, y, f"{LABELS_ES.get(k)} ({round(v)}):")
        y -= 12
        narrative = NARRATIVES_DB.get(k, {}).get('low' if v < 60 else 'high', '') # Si es alto pero está al final, muestra high
        y = draw_wrapped_text(p, narrative, 50, y, 480, "Helvetica", 9)
        y -= 10

    # 4. DIAGNÓSTICO DE FRICCIÓN (NUEVO BLOQUE INTELIGENTE)
    y -= 10
    y = check_page_break(p, y, h, w)
    p.setFont("Helvetica-Bold", 12)
    p.setFillColorRGB(0.02, 0.04, 0.12)
    p.drawString(40, y, "4. DIAGNÓSTICO DE FRICCIÓN OPERATIVA")
    p.line(40, y-5, w-40, y-5)
    y -= 30
    
    p.setFont("Helvetica", 10)
    if friction > 0:
        if stats['emotional_stability'] > 70 and friction > 10:
             diag = "La penalización en Fricción, combinada con una alta Estabilidad Emocional, permite descartar el miedo paralizante. El origen es operativo: exceso de validación o prudencia administrativa."
        else:
             diag = "La fricción detectada podría estar vinculada a inseguridad operativa o falta de certeza en la toma de decisiones."
             
        y = draw_wrapped_text(p, diag, 50, y, 480, "Helvetica", 10)
        y -= 15
        p.drawString(50, y, "Factores detectados:"); y -= 15
        for r in friction_reasons: 
            y = check_page_break(p, y, h, w)
            p.drawString(60, y, f"- {r}"); y -= 15
    else:
        p.drawString(50, y, "No se han detectado fricciones operativas significativas. El flujo de decisión es ágil.")
        y -= 15
        
    if triggers:
        y -= 5
        y = check_page_break(p, y, h, w)
        p.setFont("Helvetica-Bold", 10)
        p.setFillColorRGB(0.8, 0, 0)
        p.drawString(50, y, "ALERTAS CRÍTICAS (TRIGGERS):"); y -= 15
        p.setFillColorRGB(0, 0, 0)
        p.setFont("Helvetica", 10)
        for t in triggers: 
            y = check_page_break(p, y, h, w)
            p.drawString(60, y, f"• {t}"); y -= 15
    
    # 5. RECOMENDACIÓN Y CONCLUSIÓN
    y -= 20
    y = check_page_break(p, y, h, w)
    p.setFont("Helvetica-Bold", 12)
    p.setFillColorRGB(0.02, 0.04, 0.12)
    p.drawString(40, y, "5. CONCLUSIÓN Y RECOMENDACIÓN")
    p.line(40, y-5, w-40, y-5)
    y -= 30
    
    # Sectorial
    sector_code = SECTOR_MAP.get(user.get('sector'), "TECH")
    advice = SECTOR_ADVICE_DB.get(sector_code, "")
    y = draw_wrapped_text(p, f"Contexto Sectorial: {advice}", 50, y, 480, "Helvetica-Oblique", 10)
    y -= 15
    
    # Final
    conclusion = f"El perfil WJ-PJ (ID: {st.session_state.user_id}) es técnicamente viable. La discrepancia entre Potencial ({avg}) e IRE ({ire}) refleja el coste operativo de las fricciones detectadas. "
    if ire > 75: conclusion += "Se recomienda proceder con el itinerario de aceleración estándar."
    else: conclusion += "Se recomienda intervención específica para reducir tiempos de validación y aumentar la eficiencia ejecutiva."
    
    y = draw_wrapped_text(p, conclusion, 50, y, 480, "Helvetica", 10)

    p.setFont("Helvetica", 8)
    p.setFillColorRGB(0.5, 0.5, 0.5)
    p.drawCentredString(w/2, 30, "Documento Confidencial | Generado por Audeo S.A.P.E.")
    
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

def render_header():
    c1, c2 = st.columns([1.5, 6])
    with c1:
        if os.path.exists("logo_blanco.png"):
            st.image("logo_blanco.png", use_container_width=True)
        elif os.path.exists("logo_original.png"):
            st.image("logo_original.png", use_container_width=True)
        else:
            st.warning("Logo no encontrado")
    with c2:
        st.markdown("""
            <div style="margin-top: 10px;">
                <p class="header-title-text">Simulador S.A.P.E.</p>
                <p class="header-sub-text">Sistema de Análisis de la Personalidad Emprendedora</p>
            </div>
        """, unsafe_allow_html=True)
    st.markdown("---")

# --- 5. APP PRINCIPAL ---
init_session()

# PANTALLA 0: LOGIN
if not st.session_state.get("auth", False):
    inject_style("login") 
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if os.path.exists("logo_original.png"):
            st.image("logo_original.png", use_container_width=True)
        st.markdown('<p class="login-title">Simulador S.A.P.E.</p>', unsafe_allow_html=True)
        st.markdown('<p class="login-subtitle">Sistema de Análisis de la Personalidad Emprendedora</p>', unsafe_allow_html=True)
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        pwd = st.text_input("Clave de acceso", type="password")
        if st.button("ENTRAR AL SISTEMA", use_container_width=True):
            if pwd == st.secrets["general"]["password"]: 
                st.session_state.auth = True
                st.rerun()
            else: 
                st.error("Acceso denegado")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- APP INTERNA (NAVY) ---
inject_style("app") 

# FASE 1: DATOS
if not st.session_state.data_verified:
    render_header()
    st.markdown("#### 1. Identificación del/a Candidato/a")
    col1, col2 = st.columns(2)
    name = col1.text_input("Nombre Completo", key="name_input")
    age = col2.number_input("Edad", 18, 99, key="age_input")
    col3, col4 = st.columns(2)
    gender = col3.selectbox("Género", ["Masculino", "Femenino", "Prefiero no decirlo"], key="gender_input")
    country = col4.selectbox("País", ["España", "LATAM", "Europa", "Otros"], key="country_input")
    col5, col6 = st.columns(2)
    situation = col5.selectbox("Situación", ["Solo", "Con Socios", "Intraemprendimiento"], key="sit_input")
    experience = col6.selectbox("Experiencia", ["Primer emprendimiento", "Con éxito previo", "Sin éxito previo"], key="exp_input")
    st.markdown("<br>", unsafe_allow_html=True)
    consent = st.checkbox("He leído y acepto la Política de Privacidad.")
    if st.button("VALIDAR DATOS Y CONTINUAR"):
        if name and age and consent:
            st.session_state.user_data = {"name": name, "age": age, "gender": gender, "sector": "", "experience": experience}
            st.session_state.data_verified = True
            st.rerun()
        else:
            st.error("Por favor, completa los campos obligatorios.")

# FASE 2: SECTOR
elif not st.session_state.started:
    render_header()
    st.markdown(f"#### 2. Selecciona el Sector del Proyecto:")
    def go_sector(sec):
        all_q = load_questions()
        code = SECTOR_MAP.get(sec, "TECH")
        qs = [x for x in all_q if x['SECTOR'].strip().upper() == code]
        if not qs: qs = [x for x in all_q if x['SECTOR'].strip().upper() == "TECH"]
        st.session_state.data = qs
        st.session_state.user_data["sector"] = sec
        st.session_state.started = True
        st.rerun()

    c1, c2 = st.columns(2)
    with c1: 
        if st.button("Startup Tecnológica\n(Scalable)", use_container_width=True): go_sector("Startup Tecnológica (Scalable)")
        if st.button("Pequeña y Mediana\nEmpresa (PYME)", use_container_width=True): go_sector("Pequeña y Mediana Empresa (PYME)")
        if st.button("Autoempleo /\nFreelance", use_container_width=True): go_sector("Autoempleo / Freelance")
        if st.button("Intraemprendimiento", use_container_width=True): go_sector("Intraemprendimiento")
    with c2:
        if st.button("Consultoría /\nServicios Profesionales", use_container_width=True): go_sector("Consultoría / Servicios Profesionales")
        if st.button("Hostelería y\nRestauración", use_container_width=True): go_sector("Hostelería y Restauración")
        if st.button("Emprendimiento\nSocial", use_container_width=True): go_sector("Emprendimiento Social")
        if st.button("Emprendimiento en\nServicios de Salud", use_container_width=True): go_sector("Salud")

# FASE 3: PREGUNTAS
elif not st.session_state.finished:
    if st.session_state.current_step >= len(st.session_state.data):
        st.session_state.finished = True
        st.rerun()
    render_header()
    row = st.session_state.data[st.session_state.current_step]
    st.progress((st.session_state.current_step + 1) / len(st.session_state.data))
    st.markdown(f"### {row['TITULO']}")
    c_text, c_opt = st.columns([1.5, 1])
    with c_text:
        st.markdown(f'<div class="diag-text" style="font-size:1.2rem;"><p>{row["NARRATIVA"]}</p></div>', unsafe_allow_html=True)
    with c_opt:
        st.markdown("#### Tu decisión:")
        step = st.session_state.current_step
        if st.button(row.get('OPCION_A_TXT', 'A'), key=f"A_{step}", use_container_width=True):
            parse_logic(row.get('OPCION_A_LOGIC')); st.session_state.current_step += 1; st.rerun()
        if st.button(row.get('OPCION_B_TXT', 'B'), key=f"B_{step}", use_container_width=True):
            parse_logic(row.get('OPCION_B_LOGIC')); st.session_state.current_step += 1; st.rerun()
        if row.get('OPCION_C_TXT') and row.get('OPCION_C_TXT') != "None":
            if st.button(row.get('OPCION_C_TXT', 'C'), key=f"C_{step}", use_container_width=True):
                parse_logic(row.get('OPCION_C_LOGIC')); st.session_state.current_step += 1; st.rerun()
        if row.get('OPCION_D_TXT') and row.get('OPCION_D_TXT') != "None":
            if st.button(row.get('OPCION_D_TXT', 'D'), key=f"D_{step}", use_container_width=True):
                parse_logic(row.get('OPCION_D_LOGIC')); st.session_state.current_step += 1; st.rerun()

# FASE 4: RESULTADOS
else:
    render_header()
    ire, avg, friction, triggers, fric_reasons, delta = calculate_results()
    st.header(f"Informe S.A.P.E. | {st.session_state.user_data['name']}")
    k1, k2, k3 = st.columns(3)
    k1.metric("Índice IRE", f"{ire}/100")
    k2.metric("Potencial", f"{avg}/100")
    k3.metric("Fricción", friction, delta_color="inverse")
    c_chart, c_desc = st.columns([1, 1])
    with c_chart: st.plotly_chart(radar_chart(), use_container_width=True)
    with c_desc:
        st.markdown("### Diagnóstico")
        st.markdown(f'<div class="diag-text"><p>{get_ire_text(ire)}</p></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if triggers: st.error("Alertas: " + ", ".join(triggers))
        else: st.success("Perfil sin alertas críticas.")
    st.markdown("<br>", unsafe_allow_html=True)
    pdf = create_pdf_report(ire, avg, friction, triggers, fric_reasons, delta, st.session_state.user_data, st.session_state.octagon)
    st.download_button("📥 DESCARGAR INFORME COMPLETO (PDF)", pdf, file_name=f"Informe_SAPE_{st.session_state.user_id}.pdf", mime="application/pdf", use_container_width=True)
    if st.button("Reiniciar"): st.session_state.clear(); st.rerun()