import streamlit as st
import csv
import os
import random
import string
import io
import math
import textwrap
from datetime import datetime
import plotly.graph_objects as go
from PIL import Image
import pandas as pd
import numpy as np
import plotly.express as px

# --- GESTIÓN DE PDF AVANZADA ---
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    from reportlab.lib import colors
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Audeo | Oryon Edition", page_icon="🧬", layout="wide")

# --- 2. FUNCIONES DE INTERFAZ Y ESTILOS ---
def render_header():
    c1, c2 = st.columns([1.5, 6])
    with c1:
        if os.path.exists("logo_blanco.png"): st.image("logo_blanco.png", use_container_width=True)
        elif os.path.exists("logo_original.png"): st.image("logo_original.png", use_container_width=True)
        else: st.warning("Logo no encontrado")
    with c2: 
        st.markdown("""<div style="margin-top: 10px;"><p class="header-title-text">Simulador S.A.P.E.</p><p class="header-sub-text">Sistema de Análisis de la Personalidad Emprendedora</p></div>""", unsafe_allow_html=True)
    st.markdown("---")

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
            h1, h2, h3, h4, p, label, div[data-testid="stMarkdownContainer"] p { color: #0E1117 !important; font-family: 'Helvetica', sans-serif; }
            .stTabs [data-baseweb="tab-list"] { gap: 10px; justify-content: center; margin-bottom: 20px; }
            .stTabs [data-baseweb="tab"] { height: 50px; background-color: #F4F4F4; border-radius: 5px; color: #555555; font-weight: bold; border: 1px solid #DDDDDD; }
            .stTabs [aria-selected="true"] { background-color: #11248A !important; color: #FFFFFF !important; }
            .stTabs [aria-selected="true"] p { color: #FFFFFF !important; }
            .stTextInput input { background-color: #FFFFFF !important; color: #000000 !important; border: 1px solid #000000 !important; }
            .stButton > button { background-color: #FFFFFF !important; color: #000000 !important; border: 2px solid #000000 !important; border-radius: 6px !important; font-weight: 800 !important; width: 100%; padding: 16px; font-size: 1.1rem !important; transition: all 0.2s ease; }
            .stButton > button:hover { background-color: #11248A !important; color: #FFFFFF !important; transform: translateY(-1px); }
            .stButton > button:hover * { color: #FFFFFF !important; }
            .login-title { color: #000000 !important; font-size: 3rem !important; font-weight: 900 !important; text-align: center; margin: 0 !important; }
            .login-subtitle { color: #666666 !important; font-size: 1.2rem !important; text-align: center; margin-bottom: 2rem !important; }
            .login-card { padding: 2rem; text-align: center; border: 1px solid #EEEEEE; border-radius: 12px; margin-top: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
        """
    elif mode == "dashboard":
        theme_css = """
            .stApp { background-color: #050A1F !important; color: #FFFFFF !important; }
            h1, h2, h3, h4, p, label { color: #FFFFFF !important; }
            .stDataFrame { border: 1px solid #5D5FEF; border-radius: 5px; }
            .stButton > button { background-color: #FFFFFF !important; color: #000000 !important; border: 2px solid #FFFFFF !important; font-weight: bold !important; border-radius: 6px !important; }
            .stButton > button:hover { background-color: #E0E0E0 !important; border-color: #E0E0E0 !important; }
        """
    else: 
        theme_css = """
            .stApp { background-color: #050A1F !important; color: #FFFFFF !important; }
            h1, h2, h3, h4, p, label, span, div[data-testid="stMarkdownContainer"] p { color: #FFFFFF !important; }
            .stTextInput input, .stNumberInput input, .stSelectbox > div > div { background-color: #0F1629 !important; color: #FFFFFF !important; border: 1px solid #5D5FEF !important; }
            div[role="listbox"] div { background-color: #0F1629 !important; color: white !important; }
            .stCheckbox label p { color: white !important; }
            .stButton > button { background-color: #1A202C !important; color: white !important; border: 1px solid #5D5FEF !important; border-radius: 8px; }
            .stButton > button:hover { border-color: white !important; background-color: #5D5FEF !important; }
            div[data-testid="column"] button { height: 180px !important; min-height: 180px !important; background-color: #0F1629 !important; border: 2px solid #2D3748 !important; color: white !important; font-size: 26px !important; font-weight: 700 !important; line-height: 1.3 !important; border-radius: 16px !important; display: flex !important; align-items: center !important; justify-content: center !important; margin-bottom: 1rem !important; box-shadow: 0 4px 6px rgba(0,0,0,0.3) !important; }
            div[data-testid="column"] button:hover { border-color: #5D5FEF !important; background-color: #1a2236 !important; transform: translateY(-2px); }
            div[data-testid="column"] button:disabled { border-color: #2D3748 !important; opacity: 0.6; cursor: not-allowed; }
            .header-title-text { font-size: 3.5rem !important; font-weight: 800 !important; color: white !important; margin: 0; line-height: 1.1; }
            .header-sub-text { font-size: 1.5rem !important; color: #5D5FEF !important; margin: 0; font-weight: 500; }
            .diag-text { background-color: #0F1629; padding: 15px; border-radius: 8px; border-left: 4px solid #5D5FEF; }
            .stDownloadButton > button { background-color: #5D5FEF !important; color: white !important; border: none !important; font-weight: bold !important; }
        """
    st.markdown(f"<style>{base_css}\n{theme_css}</style>", unsafe_allow_html=True)

# --- 3. VARIABLES Y LÓGICA ---
LABELS_ES = { "achievement": "Necesidad de Logro", "risk_propensity": "Propensión al Riesgo", "innovativeness": "Innovatividad", "locus_control": "Locus de Control Interno", "self_efficacy": "Autoeficacia", "autonomy": "Autonomía", "ambiguity_tolerance": "Tol. Ambigüedad", "emotional_stability": "Estabilidad Emocional" }

VARIABLE_MAP = {
    "achievement": "achievement", "logro": "achievement", "pragmatism": "achievement", "focus": "achievement", "discipline": "achievement", "tenacity": "achievement", "persistence": "achievement", "results": "achievement", "efficiency": "achievement", "profit": "achievement", "growth": "achievement", "scale": "achievement", "ambition": "achievement", "cost_saving": "achievement", "financial_focus": "achievement", "valuation": "achievement", "business_acumen": "achievement", "business": "achievement",
    "risk_propensity": "risk_propensity", "riesgo": "risk_propensity", "risk": "risk_propensity", "courage": "risk_propensity", "audacity": "risk_propensity", "action": "risk_propensity", "speed": "risk_propensity", "investment": "risk_propensity", "debt": "risk_propensity", "financial_risk": "risk_propensity", "boldness": "risk_propensity", "bravery": "risk_propensity", "experimentation": "risk_propensity",
    "innovativeness": "innovativeness", "innovacion": "innovativeness", "strategy": "innovativeness", "vision": "innovativeness", "creativity": "innovativeness", "adaptability": "innovativeness", "flexibility": "innovativeness", "resourcefulness": "innovativeness", "curiosity": "innovativeness", "open_minded": "innovativeness", "learning": "innovativeness", "differentiation": "innovativeness", "pivot": "innovativeness", "change": "innovativeness", "reframing": "innovativeness", "forward": "innovativeness", "imaginative": "innovativeness",
    "locus_control": "locus_control", "locus": "locus_control", "responsibility": "locus_control", "ownership": "locus_control", "realism": "locus_control", "accountability": "locus_control", "problem_solving": "locus_control", "decision_making": "locus_control", "internal_locus": "locus_control", "proactivity": "locus_control", "self_awareness": "locus_control", "analysis": "locus_control",
    "self_efficacy": "self_efficacy", "autoeficacia": "self_efficacy", "confidence": "self_efficacy", "assertiveness": "self_efficacy", "leadership": "self_efficacy", "negotiation": "self_efficacy", "persuasion": "self_efficacy", "influence": "self_efficacy", "sales": "self_efficacy", "communication": "self_efficacy", "management": "self_efficacy", "networking": "self_efficacy", "pricing_power": "self_efficacy", "confrontation": "self_efficacy", "collaboration": "self_efficacy", "team_focus": "self_efficacy", "mentorship": "self_efficacy", "delegation": "self_efficacy",
    "autonomy": "autonomy", "autonomia": "autonomy", "independence": "autonomy", "freedom": "autonomy", "boundaries": "autonomy", "sovereignty": "autonomy", "identity": "autonomy", "lifestyle": "autonomy", "refusal": "autonomy", "detachment": "autonomy",
    "ambiguity_tolerance": "ambiguity_tolerance", "tolerancia": "ambiguity_tolerance", "patience": "ambiguity_tolerance", "resilience": "ambiguity_tolerance", "calm": "ambiguity_tolerance", "stoicism": "ambiguity_tolerance", "hope": "ambiguity_tolerance", "optimism": "ambiguity_tolerance", "acceptance": "ambiguity_tolerance", "endurance": "ambiguity_tolerance", "trust": "ambiguity_tolerance",
    "emotional_stability": "emotional_stability", "estabilidad": "emotional_stability", "integrity": "emotional_stability", "ethics": "emotional_stability", "values": "emotional_stability", "justice": "emotional_stability", "fairness": "emotional_stability", "transparency": "emotional_stability", "honesty": "emotional_stability", "humility": "emotional_stability", "empathy": "emotional_stability", "humanity": "emotional_stability", "culture": "emotional_stability", "loyalty": "emotional_stability", "balance": "emotional_stability", "self_care": "emotional_stability", "coherence": "emotional_stability", "respect": "emotional_stability",
    "excitable": "excitable", "aggression": "excitable", "violence": "excitable", "anger": "excitable", "conflict": "excitable", "reaction": "excitable", "vengeance": "excitable", "impulsiveness": "excitable", "drama": "excitable", "panic": "excitable",
    "skeptical": "skeptical", "skepticism": "skeptical", "cynicism": "skeptical", "distrust": "skeptical", "suspicion": "skeptical", "hostility": "skeptical", "pessimism": "skeptical",
    "cautious": "cautious", "caution": "cautious", "fear": "cautious", "anxiety": "cautious", "avoidance": "cautious", "prudence": "cautious", "security": "cautious", "safety": "cautious", "risk_aversion": "cautious", "conservatism": "cautious", "hesitation": "cautious", "paralysis": "cautious", "trust_risk": "cautious", "delay": "cautious", "inaction": "cautious",
    "reserved": "reserved", "introversion": "reserved", "isolation": "reserved", "secrecy": "reserved", "secretive": "reserved", "distance": "reserved", "silence": "reserved",
    "passive_aggressive": "passive_aggressive", "resentment": "passive_aggressive", "obstruction": "passive_aggressive", "stubbornness": "passive_aggressive", "resistance": "passive_aggressive", "sabotage": "passive_aggressive",
    "arrogant": "arrogant", "arrogance": "arrogant", "ego": "arrogant", "narcissism": "arrogant", "superiority": "arrogant", "elitism": "arrogant", "image": "arrogant", "spectacle": "arrogant", "vanity": "arrogant", "bluff": "arrogant", "pride": "arrogant", "class": "arrogant",
    "mischievous": "mischievous", "cunning": "mischievous", "deceit": "mischievous", "manipulation": "mischievous", "opportunist": "mischievous", "corruption": "mischievous", "exploitation": "mischievous", "greed": "mischievous", "illegal": "mischievous", "machiavellian": "mischievous", "artificial": "mischievous", "tactics": "mischievous", "cheat": "mischievous", "lie": "mischievous",
    "melodramatic": "melodramatic", "victimism": "melodramatic", "complaint": "melodramatic", "fragility": "melodramatic", "delusion": "melodramatic", "attention_seeking": "melodramatic", "victim": "melodramatic",
    "diligent": "diligent", "perfectionism": "diligent", "micromanagement": "diligent", "rigidity": "diligent", "obsession": "diligent", "bureaucracy": "diligent", "complexity": "diligent", "rules": "diligent", "compliance": "diligent",
    "dependent": "dependent", "dependency": "dependent", "submission": "dependent", "pleaser": "dependent", "conformity": "dependent", "obedience": "dependent", "external_validation": "dependent", "reassurance": "dependent", "imitation": "dependent", "external_locus": "dependent", "weakness": "dependent", "surrender": "dependent"
}

SECTOR_MAP = {
    "Startup Tecnológica (Scalable)": "TECH", "Consultoría / Servicios Profesionales": "CONSULTORIA",
    "Pequeña y Mediana Empresa (PYME)": "PYME", "Hostelería y Restauración": "HOSTELERIA",
    "Autoempleo / Freelance": "AUTOEMPLEO", "Emprendimiento Social": "SOCIAL",
    "Intraemprendimiento": "INTRA", "Salud": "SALUD",
    "Psicología Sanitaria": "PSICOLOGIA_SANITARIA", "Psicología no sanitaria": "PSICOLOGÍA_NO_SANITARIA"
}

def generate_id(): return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def init_session():
    if 'octagon' not in st.session_state:
        st.session_state.octagon = {k: 0 for k in LABELS_ES.keys()}
        st.session_state.flags = {k: 0 for k in ["excitable", "skeptical", "cautious", "reserved", "passive_aggressive", "arrogant", "mischievous", "melodramatic", "diligent", "dependent"]}
        st.session_state.current_step = 0
        st.session_state.finished = False
        st.session_state.started = False
        st.session_state.data_verified = False
        st.session_state.auth = False 
        st.session_state.oryon_auth = False
        st.session_state.data = []
        st.session_state.user_id = generate_id()
        st.session_state.user_data = {}

@st.cache_data
def load_questions():
    filename = 'SATE_v2.csv'  # <--- CAMBIO IMPORTANTE: Apunta al nuevo archivo
    if not os.path.exists(filename): return []
    # Intentamos leer con punto y coma (formato europeo)
    try:
        with open(filename, encoding='utf-8-sig', errors='replace') as f:
            data = list(csv.DictReader(f, delimiter=';'))
            if data and 'SECTOR' in data[0]: return data
    except: pass
    return []
    
    # 1. Intentar con punto y coma (el formato original)
    try:
        with open(filename, encoding='utf-8-sig', errors='replace') as f:
            data = list(csv.DictReader(f, delimiter=';'))
            if data and 'SECTOR' in data[0]: return data
    except: pass
    
    # 2. Intentar con coma (por si acaso se guardó como CSV normal)
    try:
        with open(filename, encoding='utf-8-sig', errors='replace') as f:
            data = list(csv.DictReader(f, delimiter=','))
            if data and 'SECTOR' in data[0]: return data
    except: pass
    
    # 3. Intentar codificación latina
    try:
        with open(filename, encoding='latin-1', errors='replace') as f:
            data = list(csv.DictReader(f, delimiter=';'))
            if data and 'SECTOR' in data[0]: return data
    except: pass
    
    return []

# --- PARSE LOGIC (DIRECTA 1-3) ---
def parse_logic(logic_str):
    if not logic_str: return
    # Separa por barra vertical
    for action in logic_str.split('|'):
        parts = action.strip().split()
        if len(parts) < 2: continue
        
        # Limpieza del nombre (quita los dos puntos si los hay)
        var_code = parts[0].lower().replace(":", "").strip()
        
        try: 
            val = int(parts[1]) # <--- CAMBIO: Leemos DIRECTAMENTE (sin dividir)
        except: continue
        
        target = VARIABLE_MAP.get(var_code)
        if target:
            if target in st.session_state.octagon: 
                st.session_state.octagon[target] = max(0, st.session_state.octagon[target] + val)
            elif target in st.session_state.flags: 
                st.session_state.flags[target] = max(0, st.session_state.flags[target] + val)

# --- ALGORITMO DE NORMALIZACIÓN DINÁMICA ---
def get_sector_max_scores(sector_data):
    """Calcula el máximo posible leyendo los valores 1-3 del Excel"""
    max_scores = {k: 0 for k in LABELS_ES.keys()}
    
    for row in sector_data:
        question_max = {k: 0 for k in LABELS_ES.keys()}
        
        # Revisamos las 4 opciones
        for col in ['OPCION_A_LOGIC', 'OPCION_B_LOGIC', 'OPCION_C_LOGIC', 'OPCION_D_LOGIC']:
            logic = row.get(col)
            if not logic: continue
            
            for action in logic.split('|'):
                parts = action.strip().split()
                if len(parts) < 2: continue
                
                # Nombre limpio y valor directo
                trait_key = parts[0].lower().replace(":", "").strip()
                trait = VARIABLE_MAP.get(trait_key)
                try: val = int(parts[1])
                except: continue
                
                # Si es un rasgo positivo, es candidato a sumar al "techo"
                if trait in question_max and val > 0:
                    question_max[trait] = max(question_max[trait], val)
        
        # Acumulamos los máximos de esta pregunta
        for k, v in question_max.items():
            max_scores[k] += v
            
    # Evitar divisiones por cero
    for k in max_scores:
        if max_scores[k] == 0: max_scores[k] = 1
        
    return max_scores

def calculate_results():
    max_possibles = get_sector_max_scores(st.session_state.data)
    
    # 1. Normalizar Puntuaciones (Tus puntos / Máximo posible * 100)
    octagon_norm = {}
    for k, raw_val in st.session_state.octagon.items():
        # Aquí está la magia: dividimos peras con peras
        ratio = (raw_val / max_possibles[k]) * 100
        octagon_norm[k] = int(max(0, min(100, ratio)))
    
    avg = round(np.mean(list(octagon_norm.values())), 2)
    
    # 2. Fricción (Ajustada a escala corta)
    raw_friction = sum(st.session_state.flags.values())
    # En escala 1-3, acumular 30 puntos de "toxicidad" es muchísimo. Ese es el nuevo 100%.
    friction = min(100, (raw_friction / 30.0) * 100)
    
    penalty_factor = friction / 200.0 
    ire = avg * (1 - penalty_factor)
    ire = min(100, max(0, ire))
    
    # Triggers: Haber elegido lo "malo" más de 4 puntos (ej: 2 veces fuerte o 4 veces leve)
    triggers = [k for k, v in st.session_state.flags.items() if v > 4]
    
    fric_reasons = []
    if friction > 25: fric_reasons.append("Se detectan patrones de comportamiento limitantes bajo presión.")
    if triggers: fric_reasons.append(f"Riesgos detectados: {', '.join(triggers)}.")
    
    delta = round(avg - ire, 2)
    
    # Devolvemos octagon_norm (que ya está en %) para que el gráfico salga lleno
    return round(ire, 2), round(avg, 2), round(friction, 2), triggers, fric_reasons, delta, octagon_norm

def get_ire_text(s): 
    if s > 75: return "Nivel de Viabilidad: ALTO (Sostenible)"
    if s > 50: return "Nivel de Viabilidad: MEDIO (Requiere Ajustes)"
    return "Nivel de Viabilidad: BAJO (Riesgo Operativo)"

def radar_chart():
    if st.session_state.finished:
        # Extraemos solo octagon_norm (índice 6)
        results = calculate_results()
        octagon_data = results[6]
    else:
        octagon_data = {k:0 for k in LABELS_ES.keys()}
        
    data = octagon_data
    cat = [LABELS_ES.get(k) for k in data.keys()]
    val = list(data.values())
    cat += [cat[0]]
    val += [val[0]]
    
    fig = go.Figure(go.Scatterpolar(r=val, theta=cat, fill='toself', line=dict(color='#5D5FEF'), fillcolor='rgba(93, 95, 239, 0.2)'))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, showticklabels=False, range=[0, 100]),
            bgcolor='rgba(0,0,0,0)'
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        showlegend=False,
        margin=dict(l=40, r=40, t=20, b=20),
        dragmode=False
    )
    return fig

# --- DESCRIPCIONES ---
def get_competency_desc(key, score):
    texts = {
        "achievement": {
            "high": "Nivel alto. Clara orientación a resultados y estándares de excelencia. Prioriza la finalización de tareas.",
            "low": "Baja orientación a resultados. Puede diluirse en procesos sin cerrar etapas críticas."
        },
        "risk_propensity": {
            "high": "Alta tolerancia al riesgo. Disposición a actuar en escenarios de incertidumbre financiera u operativa.",
            "low": "Perfil conservador. Tendencia a evitar decisiones sin garantías totales."
        },
        "innovativeness": {
            "high": "Visión estratégica y creatividad diferencial.",
            "low": "Resistencia al cambio o preferencia por métodos tradicionales."
        },
        "locus_control": {
            "high": "Alta responsabilidad personal sobre los resultados. Enfoque proactivo.",
            "low": "Tendencia a atribuir resultados a factores externos. Puede reducir la proactividad correctiva."
        },
        "self_efficacy": {
            "high": "Confianza sólida en las propias capacidades para ejecutar el plan.",
            "low": "Dudas sobre la propia capacidad que pueden llevar a la parálisis por análisis."
        },
        "autonomy": {
            "high": "Puntuación muy alta. Fuerte independencia operativa y de criterio. No requiere supervisión.",
            "low": "Dependencia operativa. Requiere validación constante y directrices claras para avanzar."
        },
        "ambiguity_tolerance": {
            "high": "Capacidad de operar sin información completa.",
            "low": "Nivel medio-bajo. Requiere información estructurada antes de proceder. En fases iniciales deriva en retrasos."
        },
        "emotional_stability": {
            "high": "Capacidad absoluta para mantener la regulación emocional bajo presión. Gestión óptima del estrés.",
            "low": "Vulnerabilidad ante presión. Riesgo de reactividad impulsiva."
        }
    }
    cat = texts.get(key, {"high": "Competencia desarrollada.", "low": "Área de mejora."})
    return cat["high"] if score > 60 else cat["low"]

# --- GENERACIÓN DE PDF PROFESIONAL ---
def draw_page_header(p, w, h):
    p.setFillColorRGB(0.02, 0.04, 0.12)
    p.rect(0, h-100, w, 100, fill=1, stroke=0)
    p.setFillColorRGB(1, 1, 1)
    p.rect(30, h-85, 140, 70, fill=1, stroke=0)
    if os.path.exists("logo_original.png"):
        try: img = ImageReader("logo_original.png"); p.drawImage(img, 40, h-80, width=120, height=60, preserveAspectRatio=True, mask='auto')
        except: pass
    else:
        p.setFillColorRGB(0,0,0); p.setFont("Helvetica-Bold", 24); p.drawString(50, h-50, "AUDEO")
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 16)
    p.drawRightString(w-30, h-40, "INFORME TÉCNICO S.A.P.E.")
    p.setFont("Helvetica", 10)
    p.drawRightString(w-30, h-55, "Sistema de Análisis de la Personalidad Emprendedora")

def draw_radar_on_pdf(p, data, x, y, r):
    keys = list(data.keys())
    values = list(data.values())
    n = len(keys)
    angle_step = (2 * math.pi) / n
    p.setLineWidth(0.5)
    p.setStrokeColorRGB(0.8, 0.8, 0.8)
    for i in range(n):
        angle = i * angle_step + (math.pi/2)
        ex = x + r * math.cos(angle)
        ey = y + r * math.sin(angle)
        p.line(x, y, ex, ey)
        lbl_x = x + (r + 15) * math.cos(angle)
        lbl_y = y + (r + 15) * math.sin(angle)
        p.setFont("Helvetica", 6)
        p.setFillColorRGB(0.3,0.3,0.3)
        lbl = LABELS_ES.get(keys[i], keys[i])[:10]
        p.drawCentredString(lbl_x, lbl_y, lbl)
    p.setLineWidth(2)
    p.setStrokeColorRGB(0.36, 0.37, 0.93)
    p.setFillColorRGB(0.36, 0.37, 0.93, 0.2)
    path = p.beginPath()
    first = True
    for i in range(n):
        val_r = (values[i] / 100) * r
        angle = i * angle_step + (math.pi/2)
        px = x + val_r * math.cos(angle)
        py = y + val_r * math.sin(angle)
        if first:
            path.moveTo(px, py)
            first = False
        else:
            path.lineTo(px, py)
    path.close()
    p.drawPath(path, fill=1, stroke=1)

def create_pdf_report(ire, avg, friction, triggers, friction_reasons, delta, user, stats):
    if not PDF_AVAILABLE: return None
    
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    
    draw_page_header(p, w, h)
    
    y = h - 130
    p.setFillColorRGB(0,0,0)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(40, y, f"ID Usuario: {st.session_state.user_id}")
    p.drawString(40, y-15, f"Fecha de Análisis: {datetime.now().strftime('%d/%m/%Y')}")
    p.drawString(40, y-30, f"Sector: {user.get('sector', 'N/A')}")
    p.drawRightString(w-40, y, f"Candidato: {user.get('name', 'N/A')}")
    
    # 1. MÉTRICAS
    y -= 70
    p.setFont("Helvetica-Bold", 12); p.drawString(40, y, "1. Métricas Principales")
    y -= 25
    
    p.setFont("Helvetica-Bold", 10); p.drawString(40, y, f"POTENCIAL ({avg}/100):")
    p.setFont("Helvetica", 9); 
    desc_pot = "Nivel Alto." if avg > 70 else "Nivel Medio." if avg > 50 else "Nivel Bajo."
    p.drawString(160, y, desc_pot)
    y -= 12
    p.setFillColorRGB(0.3, 0.3, 0.3)
    p.drawString(40, y, "Recursos cognitivos y actitudinales basales.")
    
    y -= 30
    p.setFillColorRGB(0,0,0)
    p.setFont("Helvetica-Bold", 10); p.drawString(40, y, f"FRICCIÓN ({friction}/100):")
    p.setFont("Helvetica", 9);
    desc_fric = "Nivel crítico." if friction > 50 else "Nivel moderado." if friction > 20 else "Nivel bajo."
    p.drawString(160, y, desc_fric)
    y -= 12
    p.setFillColorRGB(0.3, 0.3, 0.3)
    p.drawString(40, y, "Resistencia operativa (Miedos, dudas y bloqueos).")

    y -= 30
    p.setFillColorRGB(0,0,0)
    p.setFont("Helvetica-Bold", 10); p.drawString(40, y, f"IRE FINAL ({ire}/100):")
    p.setFont("Helvetica", 9);
    p.drawString(160, y, get_ire_text(ire))

    y -= 20
    p.setLineWidth(1); p.setStrokeColorRGB(0.8, 0.8, 0.8)
    p.line(40, y, w-40, y)

    # 2. DETALLE
    y -= 30
    p.setFillColorRGB(0,0,0); p.setFont("Helvetica-Bold", 12); p.drawString(40, y, "2. PERFIL COMPETENCIAL (DETALLE)")
    y -= 25

    bar_x = 260
    bar_w = 250
    bar_h = 10
    seg1 = bar_w * 0.25; seg2 = bar_w * 0.35; seg3 = bar_w * 0.30; seg4 = bar_w * 0.10
    
    sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)

    for k, score in sorted_stats:
        if y < 100: p.showPage(); draw_page_header(p, w, h); y = h - 130
        
        lbl = LABELS_ES.get(k, k)
        p.setFillColorRGB(0,0,0); p.setFont("Helvetica-Bold", 9); p.drawString(40, y, lbl)
        p.drawRightString(bar_x - 10, y, f"{score}")
        
        p.setStrokeColorRGB(0.9,0.9,0.9); p.setFillColorRGB(0.95, 0.95, 0.95)
        p.rect(bar_x, y, bar_w, bar_h, fill=1, stroke=1)
        
        cur_x = bar_x
        w1 = min(score, 25) / 25 * seg1
        if w1 > 0: p.setFillColorRGB(0.9, 0.3, 0.23); p.rect(cur_x, y, w1, bar_h, fill=1, stroke=0); cur_x += w1
        if score > 25:
            rem2 = score - 25; w2 = min(rem2, 35) / 35 * seg2
            p.setFillColorRGB(0.94, 0.76, 0.06); p.rect(bar_x+seg1, y, w2, bar_h, fill=1, stroke=0)
        if score > 60:
            rem3 = score - 60; w3 = min(rem3, 30) / 30 * seg3
            p.setFillColorRGB(0.18, 0.8, 0.44); p.rect(bar_x+seg1+seg2, y, w3, bar_h, fill=1, stroke=0)
        if score > 90:
            rem4 = score - 90; w4 = min(rem4, 10) / 10 * seg4
            p.setFillColorRGB(0.9, 0.3, 0.23); p.rect(bar_x+seg1+seg2+seg3, y, w4, bar_h, fill=1, stroke=0)
            
        advice = "FORTALEZA" if score > 75 else "RIESGO" if score < 40 else "MEJORA"
        p.setFillColorRGB(0.4, 0.4, 0.4); p.setFont("Helvetica", 8)
        p.drawString(bar_x + bar_w + 10, y, f"{advice}: {get_competency_desc(k, score)[:30]}...")
        
        y -= 25

    y -= 10
    p.setLineWidth(1); p.setStrokeColorRGB(0.8, 0.8, 0.8); p.line(40, y, w-40, y)

    # 3. DIAGNÓSTICO
    y -= 30
    if y < 100: p.showPage(); draw_page_header(p, w, h); y = h - 130
    p.setFillColorRGB(0,0,0); p.setFont("Helvetica-Bold", 12); p.drawString(40, y, "3. DIAGNÓSTICO DE RIESGOS")
    y -= 20
    
    if friction_reasons:
        for r in friction_reasons:
            p.setFont("Helvetica", 9); p.drawString(40, y, f"• {r}"); y -= 15
    else:
        p.setFont("Helvetica-Oblique", 9); p.drawString(40, y, "Sin riesgos críticos detectados.")
        y -= 15

    y -= 10
    p.line(40, y, w-40, y)

    # 4. CONCLUSIÓN
    y -= 30
    if y < 100: p.showPage(); draw_page_header(p, w, h); y = h - 130
    p.setFont("Helvetica-Bold", 12); p.drawString(40, y, "4. CONCLUSIÓN Y RECOMENDACIÓN")
    y -= 20
    
    conc = f"Contexto Sectorial: {user.get('sector','General')}. El perfil muestra un IRE de {ire}/100. "
    if ire > 50: conc += "Perfil apto con áreas de optimización."
    else: conc += "Perfil con bloqueos significativos."
    
    text_obj = p.beginText(40, y)
    text_obj.setFont("Helvetica", 9)
    lines = textwrap.wrap(conc, width=100)
    for l in lines: text_obj.textLine(l)
    p.drawText(text_obj)
    y -= (len(lines)*12 + 20)

    # RADAR
    if y < 180: p.showPage(); draw_page_header(p, w, h); y = h - 130
    draw_radar_on_pdf(p, stats, w/2, y - 80, 70)

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

def render_oryon_dashboard():
    inject_style("dashboard")
    st.title("Talent Command Center")
    st.write("Panel de Control para Entidades (Simulado)")

# --- 6. EJECUCIÓN PRINCIPAL ---
init_session()

if st.session_state.get('oryon_auth', False):
    render_oryon_dashboard()

elif st.session_state.get('auth', False):
    inject_style("app")
    
    if not st.session_state.data_verified:
        render_header()
        st.markdown("#### 1. Identificación del/a Candidato/a")
        c1, c2 = st.columns(2)
        name = c1.text_input("Nombre Completo")
        age = c2.number_input("Edad", 18, 99)
        c3, c4 = st.columns(2)
        gender = c3.selectbox("Género", ["Masculino", "Femenino", "Otro"])
        sector = c4.selectbox("Sector", list(SECTOR_MAP.keys()))
        
        if st.button("COMENZAR"):
            if name:
                st.session_state.user_data = {"name": name, "age": age, "gender": gender, "sector": sector}
                all_q = load_questions()
                code = SECTOR_MAP.get(sector, "TECH")
                qs = [x for x in all_q if x['SECTOR'].strip().upper() == code]
                st.session_state.data = qs
                st.session_state.data_verified = True
                st.session_state.started = True
                st.rerun()
            else:
                st.error("Falta el nombre")

    elif not st.session_state.finished:
        render_header()
        row = st.session_state.data[st.session_state.current_step]
        st.progress((st.session_state.current_step + 1) / len(st.session_state.data))
        st.markdown(f"### {row['TITULO']}")
        st.markdown(f'<div class="diag-text">{row["NARRATIVA"]}</div>', unsafe_allow_html=True)
        
        st.write("")
        c1, c2 = st.columns(2)
        if c1.button(row.get('OPCION_A_TXT', 'A'), use_container_width=True):
            parse_logic(row.get('OPCION_A_LOGIC'))
            st.session_state.current_step += 1
            st.rerun()
        if c2.button(row.get('OPCION_B_TXT', 'B'), use_container_width=True):
            parse_logic(row.get('OPCION_B_LOGIC'))
            st.session_state.current_step += 1
            st.rerun()
            
        c3, c4 = st.columns(2)
        if row.get('OPCION_C_TXT') and c3.button(row.get('OPCION_C_TXT', 'C'), use_container_width=True):
            parse_logic(row.get('OPCION_C_LOGIC'))
            st.session_state.current_step += 1
            st.rerun()
        if row.get('OPCION_D_TXT') and c4.button(row.get('OPCION_D_TXT', 'D'), use_container_width=True):
            parse_logic(row.get('OPCION_D_LOGIC'))
            st.session_state.current_step += 1
            st.rerun()
            
        if st.session_state.current_step >= len(st.session_state.data):
            st.session_state.finished = True
            st.rerun()

    else:
        render_header()
        ire, avg, friction, triggers, fric_reasons, delta, octagon_norm, max_possibles = calculate_results()
        
        st.markdown(f"## 📊 Informe Ejecutivo | {st.session_state.user_data['name']}")
        k1, k2, k3 = st.columns(3)
        k1.metric("IRE (Viabilidad)", f"{ire}/100")
        k2.metric("Potencial", f"{avg}/100")
        k3.metric("Fricción", f"{friction}%", delta_color="inverse")
        
        st.divider()
        c_chart, c_desc = st.columns([1, 1])
        with c_chart: st.plotly_chart(radar_chart(), use_container_width=True)
        with c_desc:
            st.subheader("Diagnóstico")
            if ire > 50: st.success(f"Perfil Viable. {get_ire_text(ire)}")
            else: st.error(f"Perfil de Riesgo. {get_ire_text(ire)}")
            
        pdf = create_pdf_report(ire, avg, friction, triggers, fric_reasons, delta, st.session_state.user_data, octagon_norm)
        st.download_button("📥 DESCARGAR PDF", pdf, file_name="Informe_SAPE.pdf", mime="application/pdf", use_container_width=True)
        
        # --- DEBUG MODE (Para ver por qué salen pequeños) ---
        with st.expander("🛠️ DEBUG - Ver Matemáticas"):
            st.write("Si los resultados son pequeños, compara 'Tus Puntos' con 'Máximo Posible'.")
            st.json({
                "Tus Puntos (Raw)": st.session_state.octagon,
                "Máximo Posible (Denominador)": max_possibles,
                "Normalizados (%)": octagon_norm
            })

        if st.button("Reiniciar"): st.session_state.clear(); st.rerun()

else:
    inject_style("login")
    st.markdown("<h1 style='text-align: center;'>🧬 AUDEO</h1>", unsafe_allow_html=True)
    
    t1, t2 = st.tabs(["Candidato", "Entidad"])
    with t1:
        pwd = st.text_input("Clave", type="password")
        if st.button("ENTRAR") and pwd == "admin":
            st.session_state.auth = True
            st.rerun()
    with t2:
        pwd_o = st.text_input("Clave Corp", type="password")
        if st.button("ACCESO CORP") and pwd_o == "ORYON2026":
            st.session_state.oryon_auth = True
            st.rerun()