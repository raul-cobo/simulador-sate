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

# --- LIBRERÍAS DE DATOS Y GRÁFICOS ---
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

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Audeo", page_icon="🧬", layout="wide")

# --- 2. FUNCIONES DE INTERFAZ (MOVIDAS AL PRINCIPIO PARA EVITAR ERRORES) ---

def render_header():
    """Dibuja la cabecera en la aplicación Streamlit"""
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
            h1, h2, h3, h4, p, label, div[data-testid="stMarkdownContainer"] p { 
                color: #0E1117 !important; font-family: 'Helvetica', sans-serif;
            }
            .stTabs [data-baseweb="tab-list"] { gap: 10px; justify-content: center; margin-bottom: 20px; }
            .stTabs [data-baseweb="tab"] {
                height: 50px; background-color: #F4F4F4; border-radius: 5px; color: #555555; 
                font-weight: bold; padding: 0 20px; border: 1px solid #DDDDDD;
            }
            .stTabs [aria-selected="true"] { 
                background-color: #11248A !important; border: 1px solid #11248A !important; color: #FFFFFF !important; 
            }
            .stTabs [aria-selected="true"] p { color: #FFFFFF !important; }
            .stTextInput input { background-color: #FFFFFF !important; color: #000000 !important; border: 1px solid #000000 !important; }
            .stButton > button {
                background-color: #FFFFFF !important; color: #000000 !important; border: 2px solid #000000 !important; 
                border-radius: 6px !important; font-weight: 800 !important; width: 100%; padding: 16px; 
                font-size: 1.1rem !important; text-transform: uppercase; transition: all 0.2s ease;
            }
            .stButton > button:hover, .stButton > button:active, .stButton > button:focus { 
                background-color: #11248A !important; color: #FFFFFF !important; border-color: #11248A !important; 
                box-shadow: none !important; transform: translateY(-1px);
            }
            .stButton > button:hover *, .stButton > button:active *, .stButton > button:focus * { color: #FFFFFF !important; }
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
            div[data-testid="column"] button {
                 height: 180px !important; min-height: 180px !important; background-color: #0F1629 !important; border: 2px solid #2D3748 !important;
                 color: white !important; font-size: 26px !important; font-weight: 700 !important; line-height: 1.3 !important; border-radius: 16px !important;
                 display: flex !important; align-items: center !important; justify-content: center !important; margin-bottom: 1rem !important; box-shadow: 0 4px 6px rgba(0,0,0,0.3) !important;
            }
            div[data-testid="column"] button:hover { border-color: #5D5FEF !important; background-color: #1a2236 !important; transform: translateY(-2px); }
            div[data-testid="column"] button:disabled { border-color: #2D3748 !important; opacity: 0.6; cursor: not-allowed; }
            .header-title-text { font-size: 3.5rem !important; font-weight: 800 !important; color: white !important; margin: 0; line-height: 1.1; }
            .header-sub-text { font-size: 1.5rem !important; color: #5D5FEF !important; margin: 0; font-weight: 500; }
            .diag-text { background-color: #0F1629; padding: 15px; border-radius: 8px; border-left: 4px solid #5D5FEF; }
            .stDownloadButton > button { background-color: #5D5FEF !important; color: white !important; border: none !important; font-weight: bold !important; }
        """
    st.markdown(f"<style>{base_css}\n{theme_css}</style>", unsafe_allow_html=True)

# --- 3. VARIABLES Y LÓGICA DE NORMALIZACIÓN ---
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
    "excitable": "excitable", "aggression": "excitable", "violence": "excitable", "anger": "excitable", "conflict": "excitable", "reaction": "excitable", "vengeance": "excitable", "impulsiveness": "excitable", "drama": "excitable",
    "skeptical": "skeptical", "skepticism": "skeptical", "cynicism": "skeptical", "distrust": "skeptical", "suspicion": "skeptical", "hostility": "skeptical",
    "cautious": "cautious", "caution": "cautious", "fear": "cautious", "anxiety": "cautious", "avoidance": "cautious", "prudence": "cautious", "security": "cautious", "safety": "cautious", "risk_aversion": "cautious", "conservatism": "cautious", "hesitation": "cautious", "paralysis": "cautious", "trust_risk": "cautious", "delay": "cautious",
    "reserved": "reserved", "introversion": "reserved", "isolation": "reserved", "secrecy": "reserved", "secretive": "reserved", "distance": "reserved",
    "passive_aggressive": "passive_aggressive", "resentment": "passive_aggressive", "obstruction": "passive_aggressive", "stubbornness": "passive_aggressive", "resistance": "passive_aggressive",
    "arrogant": "arrogant", "arrogance": "arrogant", "ego": "arrogant", "narcissism": "arrogant", "superiority": "arrogant", "elitism": "arrogant", "image": "arrogant", "spectacle": "arrogant", "vanity": "arrogant", "bluff": "arrogant", "pride": "arrogant", "class": "arrogant",
    "mischievous": "mischievous", "cunning": "mischievous", "deceit": "mischievous", "manipulation": "mischievous", "opportunist": "mischievous", "corruption": "mischievous", "exploitation": "mischievous", "greed": "mischievous", "illegal": "mischievous", "machiavellian": "mischievous", "artificial": "mischievous", "tactics": "mischievous",
    "melodramatic": "melodramatic", "victimism": "melodramatic", "complaint": "melodramatic", "fragility": "melodramatic", "delusion": "melodramatic", "attention_seeking": "melodramatic",
    "diligent": "diligent", "perfectionism": "diligent", "micromanagement": "diligent", "rigidity": "diligent", "obsession": "diligent", "bureaucracy": "diligent", "complexity": "diligent",
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
    # CAMBIO: Apuntamos al archivo v2 (Escala Corta)
    filename = 'SATE_v2.csv'  
    if not os.path.exists(filename): return []
    # 1. Intentar formato europeo (punto y coma)
    try:
        with open(filename, encoding='utf-8-sig', errors='replace') as f:
            data = list(csv.DictReader(f, delimiter=';'))
            if data and 'SECTOR' in data[0]: return data
    except: pass
    # 2. Intentar formato americano (comas)
    try:
        with open(filename, encoding='utf-8-sig', errors='replace') as f:
            data = list(csv.DictReader(f, delimiter=','))
            if data and 'SECTOR' in data[0]: return data
    except: pass
    return []

# --- PARSE LOGIC (USANDO solidos) ---
def parse_logic(logic_str):
    """Actualiza el estado sumando el valor directo (1, 2, 3)"""
    if not logic_str: return
    
    # Separamos por barra vertical
    for action in logic_str.split('|'):
        # Limpieza: quitamos los dos puntos y espacios extra
        parts = action.replace(":", " ").strip().split()
        if len(parts) < 2: continue
        
        var_code = parts[0].lower().strip()
        try: 
            # CAMBIO CRÍTICO: Leemos el entero DIRECTAMENTE. No dividimos.
            val = int(parts[1])
        except: continue
        
        target = VARIABLE_MAP.get(var_code)
        if target:
            if target in st.session_state.octagon:
                # Sumamos puntos al octógono
                st.session_state.octagon[target] = max(0, st.session_state.octagon[target] + val)
            elif target in st.session_state.flags:
                # Sumamos puntos a los descarriladores
                st.session_state.flags[target] = max(0, st.session_state.flags[target] + val)

# --- ALGORITMO DE NORMALIZACIÓN DINÁMICA ---
def get_sector_max_scores(sector_data):
    """Calcula máximos por rasgo Y máximo total del juego"""
    max_scores = {k: 0 for k in LABELS_ES.keys()}
    total_game_points = 0  # Nuevo acumulador escalar
    
    for row in sector_data:
        question_max_per_trait = {k: 0 for k in LABELS_ES.keys()}
        max_points_in_this_question = 0 # El máximo que se podía sacar en esta pregunta (sea cual sea el rasgo)
        
        for col in ['OPCION_A_LOGIC', 'OPCION_B_LOGIC', 'OPCION_C_LOGIC', 'OPCION_D_LOGIC']:
            logic = row.get(col)
            if not logic: continue
            
            # Calculamos cuántos puntos da esta opción en total
            option_points = 0
            
            for action in logic.split('|'):
                parts = action.replace(":", " ").strip().split()
                if len(parts) < 2: continue
                
                trait_key = parts[0].lower().strip()
                trait = VARIABLE_MAP.get(trait_key)
                try: val = int(parts[1])
                except: continue
                
                # Si es rasgo positivo, suma al máximo del rasgo
                if trait in question_max_per_trait and val > 0:
                    question_max_per_trait[trait] = max(question_max_per_trait[trait], val)
                
                # También sumamos para ver cuál es la "mejor opción" de la pregunta
                if val > 0: option_points += val
            
            max_points_in_this_question = max(max_points_in_this_question, option_points)
            
        # Acumulamos
        for k, v in question_max_per_trait.items():
            max_scores[k] += v
        total_game_points += max_points_in_this_question

    # Evitar div/0
    for k in max_scores:
        if max_scores[k] == 0: max_scores[k] = 1
    if total_game_points == 0: total_game_points = 1
        
    return max_scores, total_game_points
            
    # Evitar división por cero
    for k in max_scores:
        if max_scores[k] == 0: max_scores[k] = 1
        
    return max_scores

def calculate_results():
    max_possibles, total_game_points = get_sector_max_scores(st.session_state.data)
    
    # 1. Normalizamos el Octógono (para el dibujo del radar)
    octagon_norm = {}
    for k, raw_val in st.session_state.octagon.items():
        ratio = (raw_val / max_possibles[k]) * 100
        octagon_norm[k] = int(max(0, min(100, ratio)))
    
    # 2. POTENCIAL (NUEVA FÓRMULA: EFICIENCIA)
    # Sumamos todos tus puntos y los comparamos con el máximo posible del juego
    total_user_points = sum(st.session_state.octagon.values())
    avg = (total_user_points / total_game_points) * 100
    avg = round(max(0, min(100, avg)), 2)
    
    # 3. Fricción (Relajada)
    # Subimos el techo a 60 puntos. (Antes era 30 y por eso salía 100% enseguida)
    raw_friction = sum(st.session_state.flags.values())
    friction = min(100, (raw_friction / 60.0) * 100)
    
    # Cálculo IRE
    penalty_factor = friction / 200.0 
    ire = avg * (1 - penalty_factor)
    ire = min(100, max(0, ire))
    
    triggers = [k for k, v in st.session_state.flags.items() if v > 4]
    
    fric_reasons = []
    if friction > 25: fric_reasons.append("Se detectan patrones de comportamiento limitantes bajo presión.")
    if triggers: fric_reasons.append(f"Riesgos detectados: {', '.join(triggers)}.")
    
    delta = round(avg - ire, 2)
    
    return round(ire, 2), round(avg, 2), round(friction, 2), triggers, fric_reasons, delta, octagon_norm, max_possibles

def get_ire_text(s): 
    if s > 75: return "Nivel de Viabilidad: ALTO (Sostenible)"
    if s > 50: return "Nivel de Viabilidad: MEDIO (Requiere Ajustes)"
    return "Nivel de Viabilidad: BAJO (Riesgo Operativo)"

ddef radar_chart():
    if st.session_state.finished:
        # AQUÍ ESTABA EL ERROR:
        # Antes: _, _, _, _, _, _, octagon_data = calculate_results()
        # Ahora: Recogemos todo en una variable 'res' y sacamos lo que queremos por índice
        results = calculate_results()
        octagon_data = results[6] # El índice 6 es 'octagon_norm'
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
    
    # 1. PÁGINA 1
    draw_page_header(p, w, h)
    
    # DATOS
    y = h - 130
    p.setFillColorRGB(0,0,0)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(40, y, f"ID Usuario: {st.session_state.user_id}")
    p.drawString(40, y-15, f"Fecha de Análisis: {datetime.now().strftime('%d/%m/%Y')}")
    p.drawString(40, y-30, f"Sector: {user.get('sector', 'N/A')}")
    p.drawRightString(w-40, y, f"Candidato: {user.get('name', 'N/A')}")
    
    # SECCIÓN 1: MÉTRICAS
    y -= 70
    p.setFont("Helvetica-Bold", 12); p.drawString(40, y, "1. Métricas Principales")
    y -= 25
    
    p.setFont("Helvetica-Bold", 10); p.drawString(40, y, f"POTENCIAL ({avg}/100):")
    p.setFont("Helvetica", 9); 
    desc_pot = "Nivel Alto." if avg > 70 else "Nivel Medio." if avg > 50 else "Nivel Bajo."
    p.drawString(160, y, desc_pot)
    y -= 12
    p.setFillColorRGB(0.3, 0.3, 0.3)
    p.drawString(40, y, "Recursos cognitivos y actitudinales basales para afrontar la complejidad operativa.")
    
    y -= 30
    p.setFillColorRGB(0,0,0)
    p.setFont("Helvetica-Bold", 10); p.drawString(40, y, f"FRICCIÓN ({friction}/100):")
    p.setFont("Helvetica", 9);
    desc_fric = "Nivel crítico." if friction > 50 else "Nivel moderado." if friction > 20 else "Nivel bajo."
    p.drawString(160, y, desc_fric)
    y -= 12
    p.setFillColorRGB(0.3, 0.3, 0.3)
    p.drawString(40, y, "Presencia de conductas de comprobación, validación externa o cautela que ralentizan.")

    y -= 30
    p.setFillColorRGB(0,0,0)
    p.setFont("Helvetica-Bold", 10); p.drawString(40, y, f"DELTA (Diferencial) ({delta}):")
    p.setFont("Helvetica", 9); p.drawString(200, y, "Pérdida de eficiencia.")
    y -= 12
    p.setFillColorRGB(0.3, 0.3, 0.3)
    p.drawString(40, y, f"Discrepancia entre el Potencial ({avg}) y el IRE ({ire}). Coste operativo autoimpuesto.")

    y -= 30
    p.setFillColorRGB(0,0,0)
    p.setFont("Helvetica-Bold", 10); p.drawString(40, y, f"IRE FINAL ({ire}/100):")
    p.setFont("Helvetica", 9);
    desc_ire = "Viabilidad técnica confirmada." if ire > 50 else "Nivel comprometido. Riesgos de continuidad."
    p.drawString(160, y, desc_ire)

    y -= 20
    p.setLineWidth(1); p.setStrokeColorRGB(0.8, 0.8, 0.8)
    p.line(40, y, w-40, y)

    # SECCIÓN 2: ANÁLISIS DIMENSIONAL
    y -= 30
    p.setFillColorRGB(0,0,0); p.setFont("Helvetica-Bold", 12); p.drawString(40, y, "2. Análisis Dimensional (Perfil Competencial)")
    y -= 25

    # 2.1 BARRAS GRÁFICAS (AJUSTADAS V67)
    bar_x = 260
    bar_w = 250
    bar_h = 10
    seg1 = bar_w * 0.25; seg2 = bar_w * 0.35; seg3 = bar_w * 0.30; seg4 = bar_w * 0.10
    
    for k, score in stats.items():
        if y < 100: 
            p.showPage(); draw_page_header(p, w, h); y = h - 130
        
        lbl = LABELS_ES.get(k, k)
        p.setFillColorRGB(0,0,0); p.setFont("Helvetica-Bold", 9); p.drawString(40, y, lbl)
        p.drawRightString(bar_x - 10, y, f"{score}")
        
        p.setStrokeColorRGB(0.9,0.9,0.9); p.setFillColorRGB(0.95, 0.95, 0.95)
        p.rect(bar_x, y, bar_w, bar_h, fill=1, stroke=1)
        
        cur_x = bar_x
        w1 = min(score, 25) / 25 * seg1
        if w1 > 0:
            p.setFillColorRGB(0.9, 0.3, 0.23); p.rect(cur_x, y, w1, bar_h, fill=1, stroke=0)
            cur_x += w1
        if score > 25:
            rem_score2 = score - 25
            w2 = min(rem_score2, 35) / 35 * seg2
            p.setFillColorRGB(0.94, 0.76, 0.06); p.rect(bar_x + seg1, y, w2, bar_h, fill=1, stroke=0)
        if score > 60:
            rem_score3 = score - 60
            w3 = min(rem_score3, 30) / 30 * seg3
            p.setFillColorRGB(0.18, 0.8, 0.44); p.rect(bar_x + seg1 + seg2, y, w3, bar_h, fill=1, stroke=0)
        if score > 90:
            rem_score4 = score - 90
            w4 = min(rem_score4, 10) / 10 * seg4
            p.setFillColorRGB(0.9, 0.3, 0.23); p.rect(bar_x + seg1 + seg2 + seg3, y, w4, bar_h, fill=1, stroke=0)
        y -= 15

    y -= 15
    # 2.2 FORTALEZAS
    fortalezas = {k:v for k,v in stats.items() if v >= 60}
    mejoras = {k:v for k,v in stats.items() if v < 60}
    
    if y < 150: p.showPage(); draw_page_header(p, w, h); y = h - 130
    p.setFillColorRGB(0,0,0); p.setFont("Helvetica-Bold", 10); p.drawString(40, y, "Fortalezas Consolidadas")
    y -= 15
    p.setFont("Helvetica", 9)
    for k, v in fortalezas.items():
        lbl = LABELS_ES.get(k, k)
        desc = get_competency_desc(k, v)
        p.setFont("Helvetica-Bold", 9); p.drawString(40, y, f"• {lbl} ({v}/100):")
        text_obj = p.beginText(40, y - 10); text_obj.setFont("Helvetica", 8); text_obj.setFillColorRGB(0.3,0.3,0.3)
        lines = textwrap.wrap(desc, width=90)
        for line in lines: text_obj.textLine(line)
        p.drawText(text_obj)
        y -= (12 + (len(lines)*10))
        if y < 80: p.showPage(); draw_page_header(p, w, h); y = h - 130

    y -= 10
    # 2.3 ÁREAS DE DESARROLLO
    if y < 150: p.showPage(); draw_page_header(p, w, h); y = h - 130
    p.setFillColorRGB(0,0,0); p.setFont("Helvetica-Bold", 10); p.drawString(40, y, "Áreas de Desarrollo")
    y -= 15
    p.setFont("Helvetica", 9)
    for k, v in mejoras.items():
        lbl = LABELS_ES.get(k, k)
        desc = get_competency_desc(k, v)
        p.setFont("Helvetica-Bold", 9); p.drawString(40, y, f"• {lbl} ({v}/100):")
        text_obj = p.beginText(40, y - 10); text_obj.setFont("Helvetica", 8); text_obj.setFillColorRGB(0.3,0.3,0.3)
        lines = textwrap.wrap(desc, width=90)
        for line in lines: text_obj.textLine(line)
        p.drawText(text_obj)
        y -= (12 + (len(lines)*10))
        if y < 80: p.showPage(); draw_page_header(p, w, h); y = h - 130

    y -= 10
    p.setLineWidth(1); p.setStrokeColorRGB(0.8, 0.8, 0.8)
    p.line(40, y, w-40, y)

    # 3. FRICCIÓN
    y -= 30
    if y < 100: p.showPage(); draw_page_header(p, w, h); y = h - 130
    p.setFillColorRGB(0,0,0); p.setFont("Helvetica-Bold", 12); p.drawString(40, y, "3. Análisis de la Fricción")
    y -= 20
    if friction_reasons:
        p.setFont("Helvetica", 9); p.setFillColorRGB(0,0,0)
        for reason in friction_reasons:
            p.drawString(40, y, f"• {reason}")
            y -= 15
    else:
        p.setFont("Helvetica-Oblique", 9); p.setFillColorRGB(0.5,0.5,0.5)
        p.drawString(40, y, "No se han detectado bloqueos operativos significativos.")
        y -= 20

    y -= 10
    p.setLineWidth(1); p.setStrokeColorRGB(0.8, 0.8, 0.8)
    p.line(40, y, w-40, y)

    # 4. CONCLUSIÓN
    y -= 30
    if y < 100: p.showPage(); draw_page_header(p, w, h); y = h - 130
    p.setFillColorRGB(0,0,0); p.setFont("Helvetica-Bold", 12); p.drawString(40, y, "4. Conclusión y Recomendación")
    y -= 20
    
    p.setFont("Helvetica", 9)
    conc = f"El perfil presenta un IRE de {ire}/100. "
    if ire > 50:
        conc += "El perfil es técnicamente viable. "
        if delta > 30: conc += f"La discrepancia (Delta: {delta}) marca un margen de mejora operativa significativo."
    else:
        conc += "Se recomienda reevaluar el encaje del perfil o establecer medidas correctivas urgentes."
    
    text_obj = p.beginText(40, y)
    text_obj.setFont("Helvetica", 9)
    lines_conc = textwrap.wrap(conc, width=100)
    for line in lines_conc: text_obj.textLine(line)
    p.drawText(text_obj)
    y -= (len(lines_conc)*12 + 10)

    p.setFont("Helvetica-Bold", 9)
    p.drawString(40, y, "Recomendación: " + ("Trabajar en la reducción de tiempos de deliberación y aumentar velocidad." if friction > 30 else "Mantener el equilibrio actual."))
    y -= 30

    # RADAR FINAL
    if y < 180: 
        p.showPage(); draw_page_header(p, w, h); y = h - 130
    
    draw_radar_on_pdf(p, stats, w/2, y - 80, 70)

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

def render_oryon_dashboard():
    inject_style("dashboard")
    st.sidebar.markdown("### Configuración")
    logo = st.sidebar.file_uploader("Logo", type=['png', 'jpg'])
    
    c_logo, c_title = st.columns([1, 5])
    with c_logo:
        if logo: st.image(logo, width=100)
        else: st.markdown("## 🏢")
    with c_title:
        st.title("Talent Command Center")
        st.markdown("### Monitorización de Cohorte en Tiempo Real")
    st.divider()

    # DATOS DUMMY
    np.random.seed(42); n_candidatos = 25
    df = pd.DataFrame({
        'ID': [f'CND-{i:03d}' for i in range(1, n_candidatos + 1)],
        'Sector': np.random.choice(['TECH', 'SOCIAL', 'SALUD', 'CONSULTORIA'], n_candidatos),
        'IRE': np.random.randint(35, 98, n_candidatos),
        'Potencial': np.random.randint(45, 95, n_candidatos),
        'Friccion': np.random.randint(5, 75, n_candidatos)
    })

    k1, k2, k3 = st.columns(3)
    k1.metric("Candidatos", f"{n_candidatos}")
    k2.metric("IRE Promedio", f"{int(df['IRE'].mean())}/100")
    k3.metric("Riesgo Alto", f"{len(df[df['IRE'] < 50])}", delta_color="inverse")
    
    st.divider()

    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("Matriz de Riesgo")
        fig = px.scatter(df, x="Potencial", y="Friccion", color="Sector", size="IRE", hover_data=["ID"])
        fig.add_hrect(y0=60, y1=100, line_width=0, fillcolor="red", opacity=0.1)
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white'), height=350)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.subheader("Radar Promedio")
        fig_r = go.Figure(data=go.Scatterpolar(r=[75, 60, 85, 50, 70, 65, 55, 60], theta=['Logro', 'Riesgo', 'Innov.', 'Locus', 'Autoef.', 'Auton.', 'Ambig.', 'Estab.'], fill='toself'))
        fig_r.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100], showticklabels=False),
            ),
            showlegend=False, 
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)', 
            font=dict(color='white'), 
            height=350
        )
        st.plotly_chart(fig_r, use_container_width=True)

    st.subheader("Expedientes Detallados")
    def color_ire(val):
        color = '#2ECC71' if val > 75 else '#F1C40F' if val > 50 else '#E74C3C'
        return f'color: {color}; font-weight: bold;'
    st.dataframe(df.style.applymap(color_ire, subset=['IRE']), use_container_width=True)
    
    if st.button("Cerrar Sesión Corporativa"):
        st.session_state.oryon_auth = False
        st.rerun()

# --- 4. EJECUCIÓN PRINCIPAL ---
init_session()

if st.session_state.get('oryon_auth', False):
    render_oryon_dashboard()

elif st.session_state.get('auth', False):
    inject_style("app") 
    
    if not st.session_state.data_verified:
        render_header();
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

    elif not st.session_state.started:
        render_header();
        st.markdown(f"#### 2. Selecciona el Sector del Proyecto:")
        def go_sector(sec):
            all_q = load_questions();
            code = SECTOR_MAP.get(sec, "TECH")
            qs = [x for x in all_q if x['SECTOR'].strip().upper() == code]
            if not qs: qs = [x for x in all_q if x['SECTOR'].strip().upper() == "TECH"]
            st.session_state.data = qs;
            st.session_state.user_data["sector"] = sec; st.session_state.started = True; st.rerun()
        
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

    elif not st.session_state.finished:
        if st.session_state.current_step >= len(st.session_state.data): st.session_state.finished = True; st.rerun()
        render_header(); row = st.session_state.data[st.session_state.current_step]
        st.progress((st.session_state.current_step + 1) / len(st.session_state.data));
        st.markdown(f"### {row['TITULO']}")
        c_text, c_opt = st.columns([1.5, 1])
        with c_text: st.markdown(f'<div class="diag-text" style="font-size:1.2rem;"><p>{row["NARRATIVA"]}</p></div>', unsafe_allow_html=True)
        with c_opt:
            st.markdown("#### Tu decisión:")
            step = st.session_state.current_step
            if st.button(row.get('OPCION_A_TXT', 'A'), key=f"A_{step}", use_container_width=True):
                parse_logic(row.get('OPCION_A_LOGIC'))
                st.session_state.current_step += 1
                st.rerun()
            if st.button(row.get('OPCION_B_TXT', 'B'), key=f"B_{step}", use_container_width=True):
                parse_logic(row.get('OPCION_B_LOGIC'))
                st.session_state.current_step += 1
                st.rerun()
            if row.get('OPCION_C_TXT') and str(row.get('OPCION_C_TXT')).lower() != "none":
                if st.button(row.get('OPCION_C_TXT', 'C'), key=f"C_{step}", use_container_width=True):
                    parse_logic(row.get('OPCION_C_LOGIC'))
                    st.session_state.current_step += 1
                    st.rerun()
            if row.get('OPCION_D_TXT') and str(row.get('OPCION_D_TXT')).lower() != "none":
                if st.button(row.get('OPCION_D_TXT', 'D'), key=f"D_{step}", use_container_width=True):
                    parse_logic(row.get('OPCION_D_LOGIC'))
                    st.session_state.current_step += 1
                    st.rerun()

    else:
        render_header();
        ire, avg, friction, triggers, fric_reasons, delta, octagon_norm, max_possibles = calculate_results()
        
        st.markdown(f"## 📊 Informe Ejecutivo S.A.P.E. | {st.session_state.user_data['name']}")
        k1, k2, k3 = st.columns(3)
        k1.metric("Índice IRE (Viabilidad)", f"{ire}/100", help="Índice de Rendimiento Emprendedor Global")
        k2.metric("Potencial Competencial", f"{avg}/100", help="Puntuación media de las 8 competencias clave")
        k3.metric("Nivel de Fricción", f"{friction}%", "-Bajo es mejor", delta_color="inverse", help="Porcentaje de patrones de comportamiento limitantes detectados")
        
        st.divider()
        c_chart, c_desc = st.columns([1.2, 1])
        with c_chart:
            st.subheader("Mapa de Competencias")
            st.plotly_chart(radar_chart(), use_container_width=True)
        with c_desc:
            st.subheader("Diagnóstico Global")
            diag_color = "#2ECC71" if ire > 75 else "#F1C40F" if ire > 50 else "#E74C3C"
            st.markdown(f"""
                <div style="padding: 20px; border-radius: 10px; border-left: 5px solid {diag_color}; background-color: #1A202C; margin-bottom: 20px;">
                    <h3 style="color: {diag_color}; margin:0;">{get_ire_text(ire)}</h3>
                </div>
            """, unsafe_allow_html=True)
            if fric_reasons:
                st.markdown("### ⚠️ Alertas de Comportamiento")
                for alert in fric_reasons: st.error(alert)
            else:
                st.success("✅ Perfil Equilibrado: No se han detectado patrones de riesgo.")

        pdf = create_pdf_report(ire, avg, friction, triggers, fric_reasons, delta, st.session_state.user_data, octagon_norm)
        st.download_button("📥 DESCARGAR INFORME COMPLETO (PDF)", pdf, file_name=f"Informe_SAPE_{st.session_state.user_id}.pdf", mime="application/pdf", use_container_width=True)
        if st.button("Reiniciar"): st.session_state.clear(); st.rerun()

else:
    inject_style("login")
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if os.path.exists("logo_original.png"): 
            st.image("logo_original.png", use_container_width=True)
        else:
            st.markdown("<h1 style='text-align: center; font-size: 4rem; color: #000000; font-weight: 800;'>🧬 AUDEO</h1>", unsafe_allow_html=True)

        st.markdown('<p class="login-title">Simulador S.A.P.E.</p>', unsafe_allow_html=True)
        st.markdown('<p class="login-subtitle">Sistema de Análisis de la Personalidad Emprendedora</p>', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["👤 Login Emprendedor/a", "🏢 Login Entidad"])
        
        with tab1:
            st.markdown('<div class="login-card">', unsafe_allow_html=True)
            pwd = st.text_input("Clave de Candidato", type="password", key="pwd_cand")
            if st.button("ACCESO A EMPRENDEDOR/A", use_container_width=True):
                try: true_pwd = st.secrets["general"]["password"]
                except: true_pwd = "admin"
                if pwd == true_pwd: st.session_state.auth = True; st.rerun()
                else: st.error("Clave incorrecta")
            st.markdown('</div>', unsafe_allow_html=True)
            
        with tab2:
            st.markdown('<div class="login-card">', unsafe_allow_html=True)
            pwd_o = st.text_input("Clave Corporativa", type="password", key="pwd_oryon")
            if st.button("ACCESO ENTIDAD", use_container_width=True):
                if pwd_o == "ORYON2026": 
                    st.session_state.oryon_auth = True
                    st.rerun()
                else: 
                    st.error("Credenciales inválidas")
            st.markdown('</div>', unsafe_allow_html=True)