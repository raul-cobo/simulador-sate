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

# --- 2. GESTIÓN DE ESTILOS (V37) ---
def inject_style(mode):
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

# --- 3. LÓGICA Y VARIABLES CALIBRADAS ---
LABELS_ES = { "achievement": "Necesidad de Logro", "risk_propensity": "Propensión al Riesgo", "innovativeness": "Innovatividad", "locus_control": "Locus de Control Interno", "self_efficacy": "Autoeficacia", "autonomy": "Autonomía", "ambiguity_tolerance": "Tol. Ambigüedad", "emotional_stability": "Estabilidad Emocional" }

# TRADUCCIÓN PROFESIONAL DE ARQUETIPOS ("CÓCTELES")
ARCHETYPES_DB = {
    "tyrant": {
        "title": "Patrón de Liderazgo Coercitivo Reactivo",
        "desc": "La combinación de alta exigencia (Logro) con baja regulación emocional (Estabilidad) y bajo locus de control genera un estilo de gestión propenso a la frustración proyectada hacia el equipo. Riesgo de alta rotación de personal y clima laboral tóxico."
    },
    "false_prophet": {
        "title": "Patrón Visionario con Déficit de Ejecución",
        "desc": "La alta capacidad creativa (Innovatividad) y confianza (Autoeficacia) sin el respaldo de una orientación a resultados (Logro) puede derivar en la generación constante de ideas sin cierre. Riesgo de pérdida de credibilidad ante inversores."
    },
    "micromanager": {
        "title": "Patrón Perfeccionista con Bloqueo de Delegación",
        "desc": "El alto deseo de excelencia (Logro) sumado a la aversión al riesgo y baja autonomía del equipo genera cuellos de botella operativos. El líder se convierte en el límite del crecimiento de la organización."
    },
    "gambler": {
        "title": "Patrón de Riesgo Desmedido y Exceso de Confianza",
        "desc": "La disposición al riesgo combinada con una autoeficacia desbordada y la atribución externa de fallos (Bajo Locus) puede precipitar decisiones legales o financieras imprudentes. Riesgo de inviabilidad súbita."
    },
    "soldier": {
        "title": "Patrón Ejecutor Dependiente",
        "desc": "La estabilidad emocional alta, sin autonomía ni innovatividad, configura un perfil excelente para la gestión de procesos estables, pero insuficiente para liderar fases de incertidumbre o crecimiento disruptivo."
    }
}

SECTOR_ADVICE_DB = {
    "TECH": "En Startup/Tech, la velocidad es vida. Tu perfil debe pivotar rápido. Vigila no caer en 'parálisis por análisis' o en el perfeccionismo técnico.",
    "CONSULTORIA": "En Servicios Profesionales, la reputación es el activo. Gestiona la presión del cliente sin sacrificar tu estabilidad emocional.",
    "PYME": "La gestión PYME requiere pragmatismo. La consistencia operativa diaria supera a la disrupción constante. Foco en la caja y la sostenibilidad.",
    "HOSTELERIA": "Sector de reacción inmediata. Requiere resolución de conflictos en tiempo real y liderazgo cercano. El equipo es tu pilar.",
    "AUTOEMPLEO": "Eres tu propio motor. Sin estructura externa, tu disciplina y autoeficacia lo son todo. Cuidado con el aislamiento.",
    "SOCIAL": "El impacto requiere paciencia. Mide tu éxito en impacto tangible, pero no descuides la viabilidad económica o el proyecto morirá.",
    "INTRA": "Requiere diplomacia corporativa. Innovar dentro de una estructura exige tanta mano izquierda política como capacidad técnica.",
    "SALUD": "Tolerancia cero al error. La ética y la meticulosidad generan la confianza del paciente. El riesgo debe ser mínimo y controlado."
}

NARRATIVES_DB = {
    "emotional_stability": { 
        "excess": "ALERTA DE RIGIDEZ: El control emocional excesivo puede derivar en frialdad o falta de empatía, dificultando la conexión con el equipo en momentos de crisis.",
        "optimal": "FORTALEZA CLAVE: Capacidad óptima para mantener la calma y la claridad mental bajo presión, sin bloquearse ni reaccionar impulsivamente.",
        "moderate": "ÁREA DE MEJORA: Se detecta cierta vulnerabilidad ante la presión sostenida. Necesario reforzar herramientas de gestión del estrés.",
        "low": "RIESGO CRÍTICO: Alta reactividad emocional. Riesgo de bloqueo o decisiones impulsivas en situaciones de crisis."
    },
    "autonomy": { 
        "excess": "ALERTA DE AISLAMIENTO: La independencia extrema puede dificultar la delegación y el trabajo en equipo, generando cuellos de botella en la toma de decisiones.",
        "optimal": "FORTALEZA CLAVE: Independencia operativa sana. Capacidad para liderar y decidir sin requerir validación constante, pero sabiendo pedir apoyo.",
        "moderate": "ÁREA DE MEJORA: Tendencia a buscar consenso o aprobación antes de actuar, lo que puede ralentizar la ejecución.",
        "low": "RIESGO CRÍTICO: Dependencia operativa. Dificultad para avanzar sin directrices claras o supervisión externa."
    },
    "achievement": { 
        "excess": "ALERTA DE BURNOUT: La obsesión por los resultados puede llevar al agotamiento propio y del equipo, sacrificando la sostenibilidad a largo plazo.",
        "optimal": "FORTALEZA CLAVE: Clara orientación a objetivos. Persistencia y foco en la finalización de tareas con estándares de calidad adecuados.",
        "moderate": "ÁREA DE MEJORA: La orientación a resultados es inconstante. Puede haber dispersión o conformismo con estándares medios.",
        "low": "RIESGO CRÍTICO: Falta de ambición o foco. Riesgo de no alcanzar los hitos necesarios para la supervivencia del proyecto."
    },
    "risk_propensity": { 
        "excess": "ALERTA DE IMPRUDENCIA: Tendencia a asumir riesgos desmedidos o innecesarios ('jugador'). Posible subestimación de las consecuencias negativas.",
        "optimal": "FORTALEZA CLAVE: Relación sana con la incertidumbre. Disposición a asumir riesgos calculados cuando el beneficio potencial lo justifica.",
        "moderate": "ÁREA DE MEJORA: Perfil conservador. Preferencia por la seguridad que puede llevar a perder oportunidades de crecimiento.",
        "low": "RIESGO CRÍTICO: Aversión al riesgo. Parálisis por miedo a perder, impidiendo cualquier innovación o apuesta estratégica."
    },
    "ambiguity_tolerance": { 
        "excess": "ALERTA DE CAOS: Tolerancia excesiva a la falta de estructura. Puede llevar a trabajar en desorden constante y dificultar la consolidación de procesos.",
        "optimal": "FORTALEZA CLAVE: Gestión eficaz de la incertidumbre. Capacidad para operar y decidir con información incompleta sin sufrir ansiedad.",
        "moderate": "ÁREA DE MEJORA: Necesidad de cierta estructura para operar. Los cambios constantes o la falta de claridad generan estrés.",
        "low": "RIESGO CRÍTICO: Rigidez cognitiva. Bloqueo operativo si no existen reglas claras o datos precisos (imposible en fases iniciales)."
    },
    "innovativeness": { 
        "excess": "ALERTA DE DISPERSIÓN: Búsqueda constante de la novedad ('Shiny Object Syndrome'). Riesgo de no terminar lo que se empieza por buscar siempre algo nuevo.",
        "optimal": "FORTALEZA CLAVE: Creatividad aplicada. Capacidad para encontrar soluciones nuevas a problemas viejos y diferenciarse en el mercado.",
        "moderate": "ÁREA DE MEJORA: Enfoque tradicional. Tendencia a replicar lo existente. Eficaz en gestión pero limitado en diferenciación.",
        "low": "RIESGO CRÍTICO: Resistencia al cambio. Dificultad para adaptarse a nuevas tecnologías o paradigmas del mercado."
    },
    "locus_control": { 
        "excess": "ALERTA DE CULPA: Asunción desmedida de responsabilidad. Creer que todo depende de uno mismo puede generar frustración ante variables incontrolables.",
        "optimal": "FORTALEZA CLAVE: Responsabilidad proactiva. Foco en lo que sí se puede controlar y cambiar, sin victimismo.",
        "moderate": "ÁREA DE MEJORA: Tendencia ocasional a culpar a factores externos (suerte, mercado) ante los fallos, limitando el aprendizaje.",
        "low": "RIESGO CRÍTICO: Victimismo. Atribución sistemática de los resultados a la suerte o a terceros. Incapacidad para corregir el rumbo."
    },
    "self_efficacy": { 
        "excess": "ALERTA DE ARROGANCIA: Exceso de confianza que puede llevar a ignorar consejos, subestimar dificultades o no prepararse adecuadamente.",
        "optimal": "FORTALEZA CLAVE: Confianza sólida en las propias capacidades. Motor de la persistencia ante las dificultades inevitables.",
        "moderate": "ÁREA DE MEJORA: Dudas sobre la propia capacidad ('Síndrome del Impostor'). Puede llevar a no atreverse a dar pasos grandes.",
        "low": "RIESGO CRÍTICO: Inseguridad paralizante. La falta de fe en uno mismo impide vender el proyecto o liderar con convicción."
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
    
    # 1. CÁLCULO DE FRICCIÓN NORMALIZADO
    # Dividimos entre 10 para que sea un índice 0-100 realista
    # Ejemplo: 250 puntos de flags -> 25 de fricción (Moderada)
    raw_friction = sum(f.values())
    friction = min(100, raw_friction / 10) 
    
    triggers = []
    
    # Detección de Arquetipos / Cócteles (Professional Translation)
    # Tyrant: High Achievement + Low Stability + Low Locus
    if o['achievement'] > 75 and o['emotional_stability'] < 40 and o['locus_control'] < 40:
        triggers.append(ARCHETYPES_DB['tyrant']['title'])
    
    # False Prophet: High Innov + High Self-Eff + Low Achievement
    if o['innovativeness'] > 75 and o['self_efficacy'] > 75 and o['achievement'] < 40:
        triggers.append(ARCHETYPES_DB['false_prophet']['title'])
        
    # Micromanager: High Achievement + Low Risk + Low Autonomy
    if o['achievement'] > 75 and o['risk_propensity'] < 40 and o['autonomy'] < 40:
        triggers.append(ARCHETYPES_DB['micromanager']['title'])

    # Gambler: High Risk + High Self-Eff + Low Locus
    if o['risk_propensity'] > 75 and o['self_efficacy'] > 75 and o['locus_control'] < 40:
        triggers.append(ARCHETYPES_DB['gambler']['title'])

    # Soldier: Low Innov + Low Autonomy + High Stability
    if o['innovativeness'] < 40 and o['autonomy'] < 40 and o['emotional_stability'] > 75:
        triggers.append(ARCHETYPES_DB['soldier']['title'])

    # Triggers individuales clásicos (mantener como soporte)
    if f["arrogant"] > 30: triggers.append("Riesgo de Rigidez Cognitiva (Dificultad de escucha)")
    if f["mischievous"] > 30: triggers.append("Riesgo de Desalineamiento Normativo (Compliance)")
    
    # 2. CÁLCULO DE IRE SUAVIZADO
    # IRE = Potencial - (Fricción / 2). Penalización suave.
    ire = max(0, min(100, avg - (friction * 0.5)))
    
    # Si hay un patrón de descarrilador fuerte, penalización extra
    if len(triggers) > 0:
        ire -= 5 # Pequeño ajuste adicional si hay cócteles tóxicos

    delta = round(avg - ire, 2)
    return round(ire, 2), round(avg, 2), round(friction, 2), triggers, [], delta

def get_ire_text(s): 
    if s > 75: return "Nivel de Viabilidad: ALTO (Sostenible)"
    if s > 50: return "Nivel de Viabilidad: MEDIO (Requiere Ajustes)"
    return "Nivel de Viabilidad: BAJO (Riesgo Operativo)"

def radar_chart():
    data = st.session_state.octagon
    cat = [LABELS_ES.get(k) for k in data.keys()]
    val = list(data.values())
    cat += [cat[0]]; val += [val[0]]
    fig = go.Figure(go.Scatterpolar(r=val, theta=cat, fill='toself', line=dict(color='#5D5FEF'), fillcolor='rgba(93, 95, 239, 0.2)'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, showticklabels=False), bgcolor='rgba(0,0,0,0)'), paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'), showlegend=False, margin=dict(l=40, r=40, t=20, b=20), dragmode=False)
    return fig

# --- PDF GENERATOR (V37 - SEGMENTED BARS) ---
def draw_segmented_bar(c, x, y, width, height, value):
    """
    Dibuja una barra segmentada tricolor acumulativa:
    0-25: Rojo (Defecto)
    25-60: Amarillo (Desarrollo)
    60-75: Verde (Óptimo)
    75-100: Rojo (Exceso)
    """
    # Definir anchos de segmentos
    w_red1 = width * 0.25
    w_yel = width * 0.35  # 60-25 = 35
    w_grn = width * 0.15  # 75-60 = 15
    w_red2 = width * 0.25 # 100-75 = 25
    
    # Dibujar Background (Marcos vacíos)
    c.setStrokeColorRGB(0.8, 0.8, 0.8)
    c.setLineWidth(0.5)
    c.setFillColorRGB(0.95, 0.95, 0.95)
    
    c.rect(x, y, w_red1, height, fill=1, stroke=1)
    c.rect(x + w_red1, y, w_yel, height, fill=1, stroke=1)
    c.rect(x + w_red1 + w_yel, y, w_grn, height, fill=1, stroke=1)
    c.rect(x + w_red1 + w_yel + w_grn, y, w_red2, height, fill=1, stroke=1)
    
    # Lógica de Llenado Acumulativo
    
    # 1. Segmento Rojo 1 (0-25)
    if value > 0:
        fill_w = min(value, 25) / 25 * w_red1
        c.setFillColorRGB(0.8, 0.2, 0.2) # Rojo
        c.rect(x, y, fill_w, height, fill=1, stroke=0)
        
    # 2. Segmento Amarillo (25-60)
    if value > 25:
        fill_w = min(value - 25, 35) / 35 * w_yel
        c.setFillColorRGB(0.9, 0.7, 0.0) # Amarillo
        c.rect(x + w_red1, y, fill_w, height, fill=1, stroke=0)
        
    # 3. Segmento Verde (60-75)
    if value > 60:
        fill_w = min(value - 60, 15) / 15 * w_grn
        c.setFillColorRGB(0.2, 0.6, 0.2) # Verde
        c.rect(x + w_red1 + w_yel, y, fill_w, height, fill=1, stroke=0)
        
    # 4. Segmento Rojo 2 (75-100)
    if value > 75:
        fill_w = min(value - 75, 25) / 25 * w_red2
        c.setFillColorRGB(0.8, 0.2, 0.2) # Rojo Exceso
        c.rect(x + w_red1 + w_yel + w_grn, y, fill_w, height, fill=1, stroke=0)

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
    
    y = h - 130
    p.setFillColorRGB(0,0,0); p.setFont("Helvetica-Bold", 10)
    p.drawString(40, y, f"Candidato: {user.get('name', 'N/A')}"); p.drawString(300, y, f"ID: {st.session_state.user_id}")
    y -= 15
    p.drawString(40, y, f"Sector: {user.get('sector', 'N/A')}"); p.drawString(300, y, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}")
    y -= 40
    
    # 1. MÉTRICAS
    p.setFont("Helvetica-Bold", 12); p.setFillColorRGB(0.02, 0.04, 0.12)
    p.drawString(40, y, "1. MÉTRICAS PRINCIPALES")
    p.line(40, y-5, w-40, y-5); y -= 30
    
    p.setFont("Helvetica-Bold", 10); p.drawString(50, y, f"POTENCIAL ({avg}/100):")
    p.setFont("Helvetica", 10); p.drawString(200, y, "Capacidad basal (Recursos cognitivos y actitudinales)."); y-=20
    
    p.setFont("Helvetica-Bold", 10); p.drawString(50, y, f"FRICCIÓN ({friction}):")
    p.setFont("Helvetica", 10); p.drawString(200, y, "Resistencia operativa (Miedos, dudas y bloqueos)."); y-=20
    
    p.setFont("Helvetica-Bold", 10); p.drawString(50, y, f"IRE FINAL ({ire}/100):")
    p.setFont("Helvetica", 10); p.drawString(200, y, get_ire_text(ire)); y-=30
    
    # 2. ANÁLISIS DETALLADO
    y = check_page_break(p, y, h, w)
    p.setFont("Helvetica-Bold", 12); p.drawString(40, y, "2. PERFIL COMPETENCIAL (DETALLE)")
    p.line(40, y-5, w-40, y-5); y -= 30
    
    sorted_stats = sorted(stats.items(), key=lambda item: item[1], reverse=True)
    
    for k, v in sorted_stats:
        y = check_page_break(p, y, h, w)
        p.setFont("Helvetica-Bold", 9); p.setFillColorRGB(0,0,0)
        p.drawString(50, y, LABELS_ES.get(k, k))
        
        # --- NUEVA BARRA SEGMENTADA ---
        draw_segmented_bar(p, 200, y, 150, 8, v)
        
        p.setFillColorRGB(0,0,0)
        p.drawString(360, y, str(round(v, 1)))
        
        narrative_key = "low"
        if v > 75: narrative_key = "excess"
        elif v >= 60: narrative_key = "optimal"
        elif v >= 25: narrative_key = "moderate"
        
        y -= 12
        narrative = NARRATIVES_DB.get(k, {}).get(narrative_key, "Sin datos.")
        y = draw_wrapped_text(p, narrative, 50, y, 480, "Helvetica", 8)
        y -= 15

    # 3. FRICCIÓN Y PATRONES
    y -= 10
    y = check_page_break(p, y, h, w)
    p.setFont("Helvetica-Bold", 12); p.setFillColorRGB(0.02, 0.04, 0.12)
    p.drawString(40, y, "3. DIAGNÓSTICO DE PATRONES Y RIESGOS")
    p.line(40, y-5, w-40, y-5); y -= 30
    
    # ALERTAS COMBINATORIAS (Arquetipos)
    if triggers:
        p.setFont("Helvetica-Bold", 10); p.setFillColorRGB(0.8, 0, 0)
        p.drawString(50, y, "ALERTA DE PATRONES COMBINATORIOS:"); y -= 20
        p.setFillColorRGB(0, 0, 0); p.setFont("Helvetica", 9)
        for t in triggers:
            # Buscar descripción del arquetipo
            desc = ""
            for arch_key, arch_val in ARCHETYPES_DB.items():
                if arch_val['title'] == t:
                    desc = arch_val['desc']
                    break
            
            p.setFont("Helvetica-Bold", 9)
            p.drawString(60, y, f"• {t}"); y -= 12
            if desc:
                y = draw_wrapped_text(p, desc, 70, y, 460, "Helvetica-Oblique", 9)
            y -= 10
            y = check_page_break(p, y, h, w)
    else:
        p.setFont("Helvetica", 10)
        p.drawString(50, y, "No se han detectado patrones de riesgo combinatorio críticos."); y -= 20
    
    # 4. CONCLUSIÓN
    y -= 20; y = check_page_break(p, y, h, w)
    p.setFont("Helvetica-Bold", 12); p.setFillColorRGB(0.02, 0.04, 0.12)
    p.drawString(40, y, "4. CONCLUSIÓN Y CONTEXTO SECTORIAL")
    p.line(40, y-5, w-40, y-5); y -= 30
    
    sector_code = SECTOR_MAP.get(user.get('sector'), "TECH")
    advice = SECTOR_ADVICE_DB.get(sector_code, "")
    y = draw_wrapped_text(p, f"Contexto Sectorial: {advice}", 50, y, 480, "Helvetica-Oblique", 10)
    y -= 15
    
    conclusion = f"El perfil presenta un IRE de {ire}/100. "
    if ire > 75: conclusion += "Perfil altamente viable."
    elif ire > 50: conclusion += "Perfil viable con acompañamiento."
    else: conclusion += "Se recomienda reevaluar el encaje del perfil."
    
    y = draw_wrapped_text(p, conclusion, 50, y, 480, "Helvetica", 10)
    
    p.showPage(); p.save(); buffer.seek(0); return buffer

def render_header():
    c1, c2 = st.columns([1.5, 6])
    with c1:
        if os.path.exists("logo_blanco.png"): st.image("logo_blanco.png", use_container_width=True)
        elif os.path.exists("logo_original.png"): st.image("logo_original.png", use_container_width=True)
        else: st.warning("Logo no encontrado")
    with c2:
        st.markdown("""<div style="margin-top: 10px;"><p class="header-title-text">Simulador S.A.P.E.</p><p class="header-sub-text">Sistema de Análisis de la Personalidad Emprendedora</p></div>""", unsafe_allow_html=True)
    st.markdown("---")

# --- 5. APP PRINCIPAL ---
init_session()

# PANTALLA 0: LOGIN
if not st.session_state.get("auth", False):
    inject_style("login") 
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if os.path.exists("logo_original.png"): st.image("logo_original.png", use_container_width=True)
        st.markdown('<p class="login-title">Simulador S.A.P.E.</p>', unsafe_allow_html=True)
        st.markdown('<p class="login-subtitle">Sistema de Análisis de la Personalidad Emprendedora</p>', unsafe_allow_html=True)
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        pwd = st.text_input("Clave de acceso", type="password")
        if st.button("ENTRAR AL SISTEMA", use_container_width=True):
            if pwd == st.secrets["general"]["password"]: st.session_state.auth = True; st.rerun()
            else: st.error("Acceso denegado")
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
            st.session_state.data_verified = True; st.rerun()
        else: st.error("Por favor, completa los campos obligatorios.")

# FASE 2: SECTOR
elif not st.session_state.started:
    render_header()
    st.markdown(f"#### 2. Selecciona el Sector del Proyecto:")
    def go_sector(sec):
        all_q = load_questions()
        code = SECTOR_MAP.get(sec, "TECH")
        qs = [x for x in all_q if x['SECTOR'].strip().upper() == code]
        if not qs: qs = [x for x in all_q if x['SECTOR'].strip().upper() == "TECH"]
        st.session_state.data = qs; st.session_state.user_data["sector"] = sec; st.session_state.started = True; st.rerun()

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
    if st.session_state.current_step >= len(st.session_state.data): st.session_state.finished = True; st.rerun()
    render_header()
    row = st.session_state.data[st.session_state.current_step]
    st.progress((st.session_state.current_step + 1) / len(st.session_state.data))
    st.markdown(f"### {row['TITULO']}")
    c_text, c_opt = st.columns([1.5, 1])
    with c_text: st.markdown(f'<div class="diag-text" style="font-size:1.2rem;"><p>{row["NARRATIVA"]}</p></div>', unsafe_allow_html=True)
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
    k1.metric("Índice IRE", f"{ire}/100"); k2.metric("Potencial", f"{avg}/100"); k3.metric("Fricción", friction, delta_color="inverse")
    c_chart, c_desc = st.columns([1, 1])
    with c_chart: st.plotly_chart(radar_chart(), use_container_width=True)
    with c_desc:
        st.markdown("### Diagnóstico")
        st.markdown(f'<div class="diag-text"><p>{get_ire_text(ire)}</p></div>', unsafe_allow_html=True)
        if triggers: st.error("Alertas: Se han detectado patrones de riesgo combinatorio.")
        else: st.success("Perfil sin patrones de riesgo combinatorio críticos.")
    pdf = create_pdf_report(ire, avg, friction, triggers, fric_reasons, delta, st.session_state.user_data, st.session_state.octagon)
    st.download_button("📥 DESCARGAR INFORME COMPLETO (PDF)", pdf, file_name=f"Informe_SAPE_{st.session_state.user_id}.pdf", mime="application/pdf", use_container_width=True)
    if st.button("Reiniciar"): st.session_state.clear(); st.rerun()