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

# --- NUEVAS LIBRERÍAS PARA EL DASHBOARD DE ORYON ---
import pandas as pd
import numpy as np
import plotly.express as px
# ---------------------------------------------------

# --- GESTIÓN DE DEPENDENCIAS (PDF) ---
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Audeo | Oryon Edition", page_icon="🧬", layout="wide")

# --- 2. GESTIÓN DE ESTILOS (V50.8 MODIFICADA PARA ORYON) ---
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
    
    # --- AQUÍ ESTÁ LA LÍNEA AÑADIDA PARA ORYON ---
    elif mode == "dashboard":
        theme_css = """
            .stApp { background-color: #050A1F !important; color: #FFFFFF !important; }
            h1, h2, h3, h4, p, label { color: #FFFFFF !important; }
            .stDataFrame { border: 1px solid #5D5FEF; border-radius: 5px; }
        """
    # ---------------------------------------------

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

# --- 3. LÓGICA Y VARIABLES ---
LABELS_ES = { "achievement": "Necesidad de Logro", "risk_propensity": "Propensión al Riesgo", "innovativeness": "Innovatividad", "locus_control": "Locus de Control Interno", "self_efficacy": "Autoeficacia", "autonomy": "Autonomía", "ambiguity_tolerance": "Tol. Ambigüedad", "emotional_stability": "Estabilidad Emocional" }

ARCHETYPES_DB = {
    "tyrant": { "title": "Patrón de Liderazgo Coercitivo Reactivo", "desc": "Combinación de alta exigencia (Logro) con baja regulación emocional y bajo locus de control. Riesgo de gestión tóxica." },
    "false_prophet": { "title": "Patrón Visionario con Déficit de Ejecución", "desc": "Alta creatividad y confianza sin orientación a resultados. Generación de ideas sin cierre." },
    "micromanager": { "title": "Patrón Perfeccionista con Bloqueo de Delegación", "desc": "Alto Logro con aversión al riesgo y baja autonomía. Cuello de botella operativo." },
    "gambler": { "title": "Patrón de Riesgo Desmedido", "desc": "Riesgo alto con autoeficacia desbordada y bajo locus. Peligro de imprudencia legal/financiera." },
    "soldier": { "title": "Patrón Ejecutor Dependiente", "desc": "Alta estabilidad pero baja autonomía e innovatividad. Bueno para mantener, malo para crear." }
}

SECTOR_ADVICE_DB = {
    "TECH": "En Startup/Tech, la velocidad es vida. Evita la 'parálisis por análisis'.",
    "CONSULTORIA": "La reputación es el activo. Gestiona la presión sin sacrificar estabilidad.",
    "PYME": "Pragmatismo. La consistencia operativa supera a la disrupción constante.",
    "HOSTELERIA": "Reacción inmediata. Resolución de conflictos en tiempo real.",
    "AUTOEMPLEO": "Eres tu propio motor. Disciplina y autoeficacia son claves.",
    "SOCIAL": "Impacto tangible. No descuides la viabilidad económica.",
    "INTRA": "Diplomacia corporativa. Mano izquierda política y capacidad técnica.",
    "SALUD": "Tolerancia cero al error. Ética y meticulosidad."
}

NARRATIVES_DB = {
    "emotional_stability": { "excess": "ALERTA: Frialdad emocional excesiva.", "optimal": "FORTALEZA: Regulación emocional óptima.", "moderate": "MEJORA: Vulnerabilidad ante presión.", "low": "RIESGO: Reactividad impulsiva." },
    "autonomy": { "excess": "ALERTA: Aislamiento y falta de delegación.", "optimal": "FORTALEZA: Independencia operativa sana.", "moderate": "MEJORA: Búsqueda de validación externa.", "low": "RIESGO: Dependencia operativa severa." },
    "achievement": { "excess": "ALERTA: Obsesión y riesgo de burnout.", "optimal": "FORTALEZA: Foco en objetivos y excelencia.", "moderate": "MEJORA: Inconstancia en resultados.", "low": "RIESGO: Falta de ambición crítica." },
    "risk_propensity": { "excess": "ALERTA: Imprudencia temeraria.", "optimal": "FORTALEZA: Asunción de riesgos calculados.", "moderate": "MEJORA: Perfil conservador.", "low": "RIESGO: Parálisis por miedo." },
    "ambiguity_tolerance": { "excess": "ALERTA: Desorden operativo.", "optimal": "FORTALEZA: Gestión eficaz de incertidumbre.", "moderate": "MEJORA: Necesidad de estructura.", "low": "RIESGO: Rigidez y bloqueo ante cambios." },
    "innovativeness": { "excess": "ALERTA: Dispersión ('Shiny Object').", "optimal": "FORTALEZA: Creatividad aplicada.", "moderate": "MEJORA: Enfoque tradicional.", "low": "RIESGO: Resistencia al cambio." },
    "locus_control": { "excess": "ALERTA: Asunción excesiva de culpa.", "optimal": "FORTALEZA: Responsabilidad proactiva.", "moderate": "MEJORA: Atribución externa ocasional.", "low": "RIESGO: Victimismo sistemático." },
    "self_efficacy": { "excess": "ALERTA: Arrogancia y subestimación de retos.", "optimal": "FORTALEZA: Confianza sólida.", "moderate": "MEJORA: Dudas sobre capacidad.", "low": "RIESGO: Inseguridad paralizante." }
}
# --- 1.2 MAPA DE VARIABLES (CORREGIDO Y COMPLETO) ---
VARIABLE_MAP = {
    # --- RASGOS POSITIVOS (SUMAN POTENCIAL) ---
    "achievement": "achievement", "logro": "achievement", "pragmatism": "achievement", 
    "focus": "achievement", "discipline": "achievement", "tenacity": "achievement",
    "persistence": "achievement", "results": "achievement", "efficiency": "achievement", 
    "profit": "achievement", "growth": "achievement", "scale": "achievement",
    "ambition": "achievement", "cost_saving": "achievement", "financial_focus": "achievement", 
    "valuation": "achievement", "business_acumen": "achievement", "business": "achievement",

    "risk_propensity": "risk_propensity", "riesgo": "risk_propensity", "risk": "risk_propensity", 
    "courage": "risk_propensity", "audacity": "risk_propensity", "action": "risk_propensity", 
    "speed": "risk_propensity", "investment": "risk_propensity", "debt": "risk_propensity", 
    "financial_risk": "risk_propensity", "boldness": "risk_propensity", "bravery": "risk_propensity", 
    "experimentation": "risk_propensity",

    "innovativeness": "innovativeness", "innovacion": "innovativeness", "strategy": "innovativeness", 
    "vision": "innovativeness", "creativity": "innovativeness", "adaptability": "innovativeness", 
    "flexibility": "innovativeness", "resourcefulness": "innovativeness", "curiosity": "innovativeness", 
    "open_minded": "innovativeness", "learning": "innovativeness", "differentiation": "innovativeness", 
    "pivot": "innovativeness", "change": "innovativeness", "reframing": "innovativeness", 
    "forward": "innovativeness", "imaginative": "innovativeness",

    "locus_control": "locus_control", "locus": "locus_control", "responsibility": "locus_control", 
    "ownership": "locus_control", "realism": "locus_control", "accountability": "locus_control", 
    "problem_solving": "locus_control", "decision_making": "locus_control", 
    "internal_locus": "locus_control", "proactivity": "locus_control", "self_awareness": "locus_control", 
    "analysis": "locus_control",

    "self_efficacy": "self_efficacy", "autoeficacia": "self_efficacy", "confidence": "self_efficacy", 
    "assertiveness": "self_efficacy", "leadership": "self_efficacy", "negotiation": "self_efficacy", 
    "persuasion": "self_efficacy", "influence": "self_efficacy", "sales": "self_efficacy", 
    "communication": "self_efficacy", "management": "self_efficacy", "networking": "self_efficacy", 
    "pricing_power": "self_efficacy", "confrontation": "self_efficacy", "collaboration": "self_efficacy", 
    "team_focus": "self_efficacy", "mentorship": "self_efficacy", "delegation": "self_efficacy",

    "autonomy": "autonomy", "autonomia": "autonomy", "independence": "autonomy", "freedom": "autonomy", 
    "boundaries": "autonomy", "sovereignty": "autonomy", "identity": "autonomy", "lifestyle": "autonomy", 
    "refusal": "autonomy", "detachment": "autonomy",

    "ambiguity_tolerance": "ambiguity_tolerance", "tolerancia": "ambiguity_tolerance", 
    "patience": "ambiguity_tolerance", "resilience": "ambiguity_tolerance", "calm": "ambiguity_tolerance", 
    "stoicism": "ambiguity_tolerance", "hope": "ambiguity_tolerance", "optimism": "ambiguity_tolerance", 
    "acceptance": "ambiguity_tolerance", "endurance": "ambiguity_tolerance", "trust": "ambiguity_tolerance", 

    "emotional_stability": "emotional_stability", "estabilidad": "emotional_stability", 
    "integrity": "emotional_stability", "ethics": "emotional_stability", "values": "emotional_stability", 
    "justice": "emotional_stability", "fairness": "emotional_stability", "transparency": "emotional_stability", 
    "honesty": "emotional_stability", "humility": "emotional_stability", "empathy": "emotional_stability", 
    "humanity": "emotional_stability", "culture": "emotional_stability", "loyalty": "emotional_stability", 
    "balance": "emotional_stability", "self_care": "emotional_stability", "coherence": "emotional_stability", 
    "respect": "emotional_stability",

    # --- RASGOS NEGATIVOS (SUMAN FRICCIÓN) ---
    "excitable": "excitable", "aggression": "excitable", "violence": "excitable", "anger": "excitable", 
    "conflict": "excitable", "reaction": "excitable", "vengeance": "excitable", "impulsiveness": "excitable", 
    "drama": "excitable", 
    "skeptical": "skeptical", "skepticism": "skeptical", "cynicism": "skeptical", "distrust": "skeptical", 
    "suspicion": "skeptical", "hostility": "skeptical", 
    "cautious": "cautious", "caution": "cautious", "fear": "cautious", "anxiety": "cautious", "avoidance": "cautious", 
    "prudence": "cautious", "security": "cautious", "safety": "cautious", "risk_aversion": "cautious", 
    "conservatism": "cautious", "hesitation": "cautious", "paralysis": "cautious", "trust_risk": "cautious", 
    "delay": "cautious", 
    "reserved": "reserved", "introversion": "reserved", "isolation": "reserved", "secrecy": "reserved", 
    "secretive": "reserved", "distance": "reserved", 
    "passive_aggressive": "passive_aggressive", "resentment": "passive_aggressive", "obstruction": "passive_aggressive", 
    "stubbornness": "passive_aggressive", "resistance": "passive_aggressive", 
    "arrogant": "arrogant", "arrogance": "arrogant", "ego": "arrogant", "narcissism": "arrogant", 
    "superiority": "arrogant", "elitism": "arrogant", "image": "arrogant", "spectacle": "arrogant", 
    "vanity": "arrogant", "bluff": "arrogant", "pride": "arrogant", "class": "arrogant", 
    "mischievous": "mischievous", "cunning": "mischievous", "deceit": "mischievous", "manipulation": "mischievous", 
    "opportunist": "mischievous", "corruption": "mischievous", "exploitation": "mischievous", "greed": "mischievous", 
    "illegal": "mischievous", "machiavellian": "mischievous", "artificial": "mischievous", "tactics": "mischievous", 
    "melodramatic": "melodramatic", "victimism": "melodramatic", "complaint": "melodramatic", "fragility": "melodramatic", 
    "delusion": "melodramatic", "attention_seeking": "melodramatic", 
    "diligent": "diligent", "perfectionism": "diligent", "micromanagement": "diligent", "rigidity": "diligent", 
    "obsession": "diligent", "bureaucracy": "diligent", "complexity": "diligent", 
    "dependent": "dependent", "dependency": "dependent", "submission": "dependent", "pleaser": "dependent", 
    "conformity": "dependent", "obedience": "dependent", "external_validation": "dependent", "reassurance": "dependent", 
    "imitation": "dependent", "external_locus": "dependent", "weakness": "dependent", "surrender": "dependent"
}
# --- 1.1 MAPA DE SECTORES (ACTUALIZADO) ---
SECTOR_MAP = {
    "Startup Tecnológica (Scalable)": "TECH",
    "Consultoría / Servicios Profesionales": "CONSULTORIA",
    "Pequeña y Mediana Empresa (PYME)": "PYME",
    "Hostelería y Restauración": "HOSTELERIA",
    "Autoempleo / Freelance": "AUTOEMPLEO",
    "Emprendimiento Social": "SOCIAL",
    "Intraemprendimiento": "INTRA",
    "Salud": "SALUD",
    "Psicología Sanitaria": "PSICOLOGIA_SANITARIA",
    "Psicología no sanitaria": "PSICOLOGÍA_NO_SANITARIA"
}
def generate_id(): return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# --- INICIALIZACIÓN (BASE CERO PARA SATE V2) ---
def init_session():
    if 'octagon' not in st.session_state:
        # CAMBIO CLAVE: Base 0 porque el nuevo Excel ya da muchos puntos.
        st.session_state.octagon = {k: 0 for k in LABELS_ES.keys()}
        st.session_state.flags = {k: 0 for k in ["excitable", "skeptical", "cautious", "reserved", "passive_aggressive", "arrogant", "mischievous", "melodramatic", "diligent", "dependent"]}
        st.session_state.current_step = 0
        st.session_state.finished = False
        st.session_state.started = False
        st.session_state.data_verified = False
        st.session_state.auth = False # Inicializamos auth
        st.session_state.data = []
        st.session_state.user_id = generate_id()
        st.session_state.user_data = {}

@st.cache_data
@st.cache_data
def load_questions():
    # Nombre exacto del archivo en GitHub
    filename = 'SATE_v1.csv'  
    
    if not os.path.exists(filename):
        st.error(f"Error: No se encuentra el archivo '{filename}'. Asegúrate de haberlo subido a GitHub con ese nombre.")
        return []
    
    # 1. Intentar primero con UTF-8-SIG (Excel moderno con BOM)
    try:
        with open(filename, encoding='utf-8-sig', errors='strict') as f:
            data = list(csv.DictReader(f, delimiter=';'))
            return data
    except UnicodeDecodeError:
        pass  # Si falla, seguimos al siguiente

    # 2. Intentar con UTF-8 normal (Estándar web)
    try:
        with open(filename, encoding='utf-8', errors='strict') as f:
            data = list(csv.DictReader(f, delimiter=';'))
            return data
    except UnicodeDecodeError:
        pass

    # 3. Intentar con Latin-1 (Excel antiguo / Windows Europa)
    try:
        with open(filename, encoding='latin-1', errors='strict') as f:
            data = list(csv.DictReader(f, delimiter=';'))
            return data
    except UnicodeDecodeError:
        pass

    # 4. Último recurso: CP1252 (Windows occidental específico)
    try:
        with open(filename, encoding='cp1252', errors='replace') as f:
            data = list(csv.DictReader(f, delimiter=';'))
            return data
    except Exception as e:
        st.error(f"Error crítico de codificación: {e}")
        return []

# --- LÓGICA DE PUNTOS (PURA) ---
def parse_logic(logic_str):
    if not logic_str: return
    for action in logic_str.split('|'):
        parts = action.strip().split()
        if len(parts) < 2: continue
        
        var_code = parts[0].lower().strip()
        try: 
            # CAMBIO CLAVE: Sin multiplicador. Confiamos en el Excel.
            val = int(parts[1])
        except: continue
        
        target = VARIABLE_MAP.get(var_code)
        if target:
            if target in st.session_state.octagon: 
                st.session_state.octagon[target] = max(0, min(100, st.session_state.octagon[target] + val))
            elif target in st.session_state.flags: 
                st.session_state.flags[target] = max(0, st.session_state.flags[target] + val)

def calculate_results():
    # 1. CÁLCULO DE POTENCIAL (Curva Logística Suavizada)
    # Evita que la puntuación se dispare a 100 con pocas respuestas.
    raw_points = sum(st.session_state.traits.values())
    # Fórmula matemática: 100 * (1 - 1/(1 + Puntos/150))
    avg = 100 * (1 - (1 / (1 + (raw_points / 150.0))))
    
    # 2. CÁLCULO DE FRICCIÓN (Solo Flags Reales)
    # Sumamos SOLO las banderas rojas, no la ambición ni el riesgo.
    raw_friction = sum(st.session_state.flags.values())
    
    # Escala: 50 puntos de banderas rojas = 100% de fricción (muy peligroso)
    friction = min(100, (raw_friction / 50.0) * 100)
    
    # 3. ÍNDICE DE RENDIMIENTO (IRE)
    # La fricción penaliza el potencial. Si Fricción=100, IRE baja a la mitad.
    penalty_factor = friction / 200.0 
    ire = avg * (1 - penalty_factor)
    
    # Limpieza final de rangos
    ire = min(100, max(0, ire))
    avg = min(100, max(0, avg))
    
    # Detección de alertas (>10 puntos en un rasgo negativo)
    triggers = [k for k, v in st.session_state.flags.items() if v > 10]
    
    # Generación de textos explicativos para el PDF
    fric_reasons = []
    if friction > 20: fric_reasons.append("Se detectan patrones de comportamiento limitantes bajo presión.")
    if "excitable" in triggers: fric_reasons.append("Riesgo de volatilidad emocional o reactividad.")
    if "cautious" in triggers: fric_reasons.append("Riesgo de parálisis por análisis o aversión al cambio.")
    if "skeptical" in triggers: fric_reasons.append("Dificultad para confiar y delegar.")
    if "arrogant" in triggers: fric_reasons.append("Posible exceso de confianza o subestimación de riesgos.")
    if "mischievous" in triggers: fric_reasons.append("Tendencia a tomar atajos éticos o riesgos imprudentes.")
    
    # Retornamos 6 valores para mantener compatibilidad con tu código actual
    return round(ire, 2), round(avg, 2), round(friction, 2), triggers, fric_reasons, 0

def get_ire_text(s): 
    if s > 75: return "Nivel de Viabilidad: ALTO (Sostenible)"
    if s > 50: return "Nivel de Viabilidad: MEDIO (Requiere Ajustes)"
    return "Nivel de Viabilidad: BAJO (Riesgo Operativo)"

def radar_chart():
    data = st.session_state.octagon
    cat = [LABELS_ES.get(k) for k in data.keys()]
    val = list(data.values())
    cat += [cat[0]]
    val += [val[0]]
    fig = go.Figure(go.Scatterpolar(r=val, theta=cat, fill='toself', line=dict(color='#5D5FEF'), fillcolor='rgba(93, 95, 239, 0.2)'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, showticklabels=False), bgcolor='rgba(0,0,0,0)'), paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'), showlegend=False, margin=dict(l=40, r=40, t=20, b=20), dragmode=False)
    return fig

# --- PDF GENERATOR ---
def draw_segmented_bar(c, x, y, width, height, value):
    w_red1 = width * 0.25; w_yel = width * 0.35; w_grn = width * 0.15; w_red2 = width * 0.25
    c.setStrokeColorRGB(0.8, 0.8, 0.8); c.setLineWidth(0.5); c.setFillColorRGB(0.95, 0.95, 0.95)
    c.rect(x, y, w_red1, height, fill=1, stroke=1); c.rect(x + w_red1, y, w_yel, height, fill=1, stroke=1)
    c.rect(x + w_red1 + w_yel, y, w_grn, height, fill=1, stroke=1); c.rect(x + w_red1 + w_yel + w_grn, y, w_red2, height, fill=1, stroke=1)
    if value > 0: c.setFillColorRGB(0.8, 0.2, 0.2); c.rect(x, y, min(value, 25)/25*w_red1, height, fill=1, stroke=0)
    if value > 25: c.setFillColorRGB(0.9, 0.7, 0.0); c.rect(x + w_red1, y, min(value-25, 35)/35*w_yel, height, fill=1, stroke=0)
    if value > 60: c.setFillColorRGB(0.2, 0.6, 0.2); c.rect(x + w_red1 + w_yel, y, min(value-60, 15)/15*w_grn, height, fill=1, stroke=0)
    if value > 75: c.setFillColorRGB(0.8, 0.2, 0.2); c.rect(x + w_red1 + w_yel + w_grn, y, min(value-75, 25)/25*w_red2, height, fill=1, stroke=0)

def draw_wrapped_text(c, text, x, y, max_width, font_name, font_size, line_spacing=12):
    c.setFont(font_name, font_size); words = text.split(); lines = []; current_line = []
    for word in words:
        current_line.append(word); width = c.stringWidth(" ".join(current_line), font_name, font_size)
        if width > max_width: current_line.pop(); lines.append(" ".join(current_line)); current_line = [word]
    lines.append(" ".join(current_line))
    for line in lines: c.drawString(x, y, line); y -= line_spacing
    return y 

def check_page_break(c, y, h, w):
    if y < 80: c.showPage(); draw_pdf_header(c, w, h); return h - 140
    return y

def draw_pdf_header(p, w, h):
    p.setFillColorRGB(0.02, 0.04, 0.12); p.rect(0, h-100, w, 100, fill=1, stroke=0)
    p.setFillColorRGB(1, 1, 1); p.rect(30, h-85, 140, 70, fill=1, stroke=0)
    if os.path.exists("logo_original.png"):
        try: img = ImageReader("logo_original.png"); p.drawImage(img, 40, h-80, width=120, height=60, preserveAspectRatio=True, mask='auto')
        except: pass
    p.setFillColorRGB(1, 1, 1); p.setFont("Helvetica-Bold", 16); p.drawRightString(w-30, h-40, "INFORME TÉCNICO S.A.P.E.")
    p.setFont("Helvetica", 10); p.drawRightString(w-30, h-55, "Sistema de Análisis de la Personalidad Emprendedora")

def create_pdf_report(ire, avg, friction, triggers, friction_reasons, delta, user, stats):
    buffer = io.BytesIO(); p = canvas.Canvas(buffer, pagesize=A4); w, h = A4; draw_pdf_header(p, w, h)
    y = h - 130
    p.setFillColorRGB(0,0,0); p.setFont("Helvetica-Bold", 10)
    p.drawString(40, y, f"Candidato: {user.get('name', 'N/A')}"); p.drawString(300, y, f"ID: {st.session_state.user_id}"); y -= 15
    p.drawString(40, y, f"Sector: {user.get('sector', 'N/A')}"); p.drawString(300, y, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}"); y -= 40
    
    p.setFont("Helvetica-Bold", 12); p.setFillColorRGB(0.02, 0.04, 0.12); p.drawString(40, y, "1. MÉTRICAS PRINCIPALES"); p.line(40, y-5, w-40, y-5); y -= 30
    p.setFont("Helvetica-Bold", 10); p.drawString(50, y, f"POTENCIAL ({avg}/100):"); p.setFont("Helvetica", 10); p.drawString(200, y, "Capacidad basal (Recursos cognitivos y actitudinales)."); y-=20
    p.setFont("Helvetica-Bold", 10); p.drawString(50, y, f"FRICCIÓN ({friction}):"); p.setFont("Helvetica", 10); p.drawString(200, y, "Resistencia operativa (Miedos, dudas y bloqueos)."); y-=20
    p.setFont("Helvetica-Bold", 10); p.drawString(50, y, f"IRE FINAL ({ire}/100):"); p.setFont("Helvetica", 10); p.drawString(200, y, get_ire_text(ire)); y-=30
    
    y = check_page_break(p, y, h, w); p.setFont("Helvetica-Bold", 12); p.drawString(40, y, "2. PERFIL COMPETENCIAL (DETALLE)"); p.line(40, y-5, w-40, y-5); y -= 30
    sorted_stats = sorted(stats.items(), key=lambda item: item[1], reverse=True)
    for k, v in sorted_stats:
        y = check_page_break(p, y, h, w); p.setFont("Helvetica-Bold", 9); p.setFillColorRGB(0,0,0); p.drawString(50, y, LABELS_ES.get(k, k))
        draw_segmented_bar(p, 200, y, 150, 8, v); p.setFillColorRGB(0,0,0); p.drawString(360, y, str(round(v, 1)))
        narrative_key = "low"
        if v > 75: narrative_key = "excess"
        elif v >= 60: narrative_key = "optimal"
        elif v >= 25: narrative_key = "moderate"
        y -= 12; narrative = NARRATIVES_DB.get(k, {}).get(narrative_key, "Sin datos."); y = draw_wrapped_text(p, narrative, 50, y, 480, "Helvetica", 8); y -= 15

    y -= 10; y = check_page_break(p, y, h, w); p.setFont("Helvetica-Bold", 12); p.setFillColorRGB(0.02, 0.04, 0.12); p.drawString(40, y, "3. DIAGNÓSTICO DE PATRONES Y RIESGOS"); p.line(40, y-5, w-40, y-5); y -= 30
    if triggers:
        p.setFont("Helvetica-Bold", 10); p.setFillColorRGB(0.8, 0, 0); p.drawString(50, y, "ALERTA DE PATRONES COMBINATORIOS:"); y -= 20
        p.setFillColorRGB(0, 0, 0); p.setFont("Helvetica", 9)
        for t in triggers:
            desc = ""
            for arch_key, arch_val in ARCHETYPES_DB.items():
                if arch_val['title'] == t: desc = arch_val['desc']; break
            p.setFont("Helvetica-Bold", 9); p.drawString(60, y, f"• {t}"); y -= 12
            if desc: y = draw_wrapped_text(p, desc, 70, y, 460, "Helvetica-Oblique", 9)
            y -= 10; y = check_page_break(p, y, h, w)
    else: p.setFont("Helvetica", 10); p.drawString(50, y, "No se han detectado patrones de riesgo combinatorio críticos."); y -= 20
    
    y -= 20; y = check_page_break(p, y, h, w); p.setFont("Helvetica-Bold", 12); p.setFillColorRGB(0.02, 0.04, 0.12); p.drawString(40, y, "4. CONCLUSIÓN Y CONTEXTO SECTORIAL"); p.line(40, y-5, w-40, y-5); y -= 30
    sector_code = SECTOR_MAP.get(user.get('sector'), "TECH"); advice = SECTOR_ADVICE_DB.get(sector_code, "")
    y = draw_wrapped_text(p, f"Contexto Sectorial: {advice}", 50, y, 480, "Helvetica-Oblique", 10); y -= 15
    conclusion = f"El perfil presenta un IRE de {ire}/100. "; conclusion += "Perfil altamente viable." if ire > 75 else "Perfil viable con acompañamiento." if ire > 50 else "Se recomienda reevaluar el encaje del perfil."
    y = draw_wrapped_text(p, conclusion, 50, y, 480, "Helvetica", 10)
    p.showPage(); p.save(); buffer.seek(0); return buffer

def render_header():
    c1, c2 = st.columns([1.5, 6])
    with c1:
        if os.path.exists("logo_blanco.png"): st.image("logo_blanco.png", use_container_width=True)
        elif os.path.exists("logo_original.png"): st.image("logo_original.png", use_container_width=True)
        else: st.warning("Logo no encontrado")
    with c2: st.markdown("""<div style="margin-top: 10px;"><p class="header-title-text">Simulador S.A.P.E.</p><p class="header-sub-text">Sistema de Análisis de la Personalidad Emprendedora</p></div>""", unsafe_allow_html=True)
    st.markdown("---")

# --- 5. APP PRINCIPAL ---
init_session()

# LOGIN
if not st.session_state.get("auth", False):
    inject_style("login"); c1, c2, c3 = st.columns([1, 2, 1])
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

inject_style("app") 

# FASE 1
if not st.session_state.data_verified:
    render_header(); st.markdown("#### 1. Identificación del/a Candidato/a")
    col1, col2 = st.columns(2); name = col1.text_input("Nombre Completo", key="name_input"); age = col2.number_input("Edad", 18, 99, key="age_input")
    col3, col4 = st.columns(2); gender = col3.selectbox("Género", ["Masculino", "Femenino", "Prefiero no decirlo"], key="gender_input"); country = col4.selectbox("País", ["España", "LATAM", "Europa", "Otros"], key="country_input")
    col5, col6 = st.columns(2); situation = col5.selectbox("Situación", ["Solo", "Con Socios", "Intraemprendimiento"], key="sit_input"); experience = col6.selectbox("Experiencia", ["Primer emprendimiento", "Con éxito previo", "Sin éxito previo"], key="exp_input")
    st.markdown("<br>", unsafe_allow_html=True); consent = st.checkbox("He leído y acepto la Política de Privacidad.")
    if st.button("VALIDAR DATOS Y CONTINUAR"):
        if name and age and consent: st.session_state.user_data = {"name": name, "age": age, "gender": gender, "sector": "", "experience": experience}; st.session_state.data_verified = True; st.rerun()
        else: st.error("Por favor, completa los campos obligatorios.")

# FASE 2
elif not st.session_state.started:
    render_header(); st.markdown(f"#### 2. Selecciona el Sector del Proyecto:")
    def go_sector(sec):
        all_q = load_questions(); code = SECTOR_MAP.get(sec, "TECH")
        qs = [x for x in all_q if x['SECTOR'].strip().upper() == code]
        # Fallback si no encuentra el sector (usa TECH)
        if not qs: qs = [x for x in all_q if x['SECTOR'].strip().upper() == "TECH"]
        
        st.session_state.data = qs; st.session_state.user_data["sector"] = sec; st.session_state.started = True; st.rerun()
    c1, c2 = st.columns(2)
    with c1: 
        if st.button("Startup Tecnológica\n(Scalable)", use_container_width=True): go_sector("Startup Tecnológica (Scalable)")
        if st.button("Pequeña y Mediana\nEmpresa (PYME)", use_container_width=True): go_sector("Pequeña y Mediana Empresa (PYME)")
        if st.button("Autoempleo /\nFreelance", use_container_width=True): go_sector("Autoempleo / Freelance")
        if st.button("Intraemprendimiento", use_container_width=True): go_sector("Intraemprendimiento")
        if st.button("Psicología Sanitaria", use_container_width=True): go_sector("Psicología Sanitaria")
    with c2:
        if st.button("Consultoría /\nServicios Profesionales", use_container_width=True): go_sector("Consultoría / Servicios Profesionales")
        if st.button("Hostelería y\nRestauración", use_container_width=True): go_sector("Hostelería y Restauración")
        if st.button("Emprendimiento\nSocial", use_container_width=True): go_sector("Emprendimiento Social")
        if st.button("Emprendimiento en\nServicios de Salud", use_container_width=True): go_sector("Salud")
        if st.button("Psicología no sanitaria", use_container_width=True): go_sector("Psicología no sanitaria")

# FASE 3
elif not st.session_state.finished:
    if st.session_state.current_step >= len(st.session_state.data): st.session_state.finished = True; st.rerun()
    render_header(); row = st.session_state.data[st.session_state.current_step]
    st.progress((st.session_state.current_step + 1) / len(st.session_state.data)); st.markdown(f"### {row['TITULO']}")
    c_text, c_opt = st.columns([1.5, 1])
    with c_text: st.markdown(f'<div class="diag-text" style="font-size:1.2rem;"><p>{row["NARRATIVA"]}</p></div>', unsafe_allow_html=True)
    with c_opt:
        st.markdown("#### Tu decisión:")
        step = st.session_state.current_step
        if st.button(row.get('OPCION_A_TXT', 'A'), key=f"A_{step}", use_container_width=True): parse_logic(row.get('OPCION_A_LOGIC')); st.session_state.current_step += 1; st.rerun()
        if st.button(row.get('OPCION_B_TXT', 'B'), key=f"B_{step}", use_container_width=True): parse_logic(row.get('OPCION_B_LOGIC')); st.session_state.current_step += 1; st.rerun()
        if row.get('OPCION_C_TXT') and row.get('OPCION_C_TXT') != "None":
            if st.button(row.get('OPCION_C_TXT', 'C'), key=f"C_{step}", use_container_width=True): parse_logic(row.get('OPCION_C_LOGIC')); st.session_state.current_step += 1; st.rerun()
        if row.get('OPCION_D_TXT') and row.get('OPCION_D_TXT') != "None":
            if st.button(row.get('OPCION_D_TXT', 'D'), key=f"D_{step}", use_container_width=True): parse_logic(row.get('OPCION_D_LOGIC')); st.session_state.current_step += 1; st.rerun()

# FASE 4
else:
    render_header(); ire, avg, friction, triggers, fric_reasons, delta = calculate_results()
    st.header(f"Informe S.A.P.E. | {st.session_state.user_data['name']}")
    k1, k2, k3 = st.columns(3); k1.metric("Índice IRE", f"{ire}/100"); k2.metric("Potencial", f"{avg}/100"); k3.metric("Fricción", friction, delta_color="inverse")
    c_chart, c_desc = st.columns([1, 1])
    with c_chart: st.plotly_chart(radar_chart(), use_container_width=True)
    with c_desc:
        st.markdown("### Diagnóstico"); st.markdown(f'<div class="diag-text"><p>{get_ire_text(ire)}</p></div>', unsafe_allow_html=True)
        if triggers: st.error("Alertas: Se han detectado patrones de riesgo.")
        else: st.success("Perfil sin patrones de riesgo críticos.")
    pdf = create_pdf_report(ire, avg, friction, triggers, fric_reasons, delta, st.session_state.user_data, st.session_state.octagon)
    st.download_button("📥 DESCARGAR INFORME COMPLETO (PDF)", pdf, file_name=f"Informe_SAPE_{st.session_state.user_id}.pdf", mime="application/pdf", use_container_width=True)
    if st.button("Reiniciar"): st.session_state.clear(); st.rerun()