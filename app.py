import streamlit as st
import csv
import os
import random
import string
import io
import math
import textwrap
import json
import ast 
from datetime import datetime
import plotly.graph_objects as go
from PIL import Image
import pandas as pd
import numpy as np
import plotly.express as px
from supabase import create_client

# --- 🎨 CONFIGURACIÓN VISUAL (SÓLO OCULTAR MENÚS) ---
def inject_custom_css():
    st.markdown("""
        <style>
        /* 1. OCULTAR BARRA SUPERIOR (GitHub, Deploy, Settings...) */
        header {visibility: hidden !important;}
        [data-testid="stToolbar"] {visibility: hidden !important;}
        [data-testid="stDecoration"] {visibility: hidden !important;}
        
        /* 2. OCULTAR PIE DE PÁGINA */
        footer {visibility: hidden !important;}
        </style>
    """, unsafe_allow_html=True)

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Audeo", page_icon="🧬", layout="wide")

# --- CONEXIÓN SUPABASE ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        return None

supabase = init_connection()

def check_if_user_finished(student_id):
    """Comprueba si este usuario ya tiene resultados en la BBDD"""
    if supabase:
        try:
            # Preguntamos a Supabase si existe este ID
            response = supabase.table("sape_results").select("student_id").eq("student_id", student_id).execute()
            # Si la lista 'data' no está vacía, es que ya existe
            if len(response.data) > 0:
                return True
        except Exception as e:
            print(f"Error comprobando usuario: {e}")
    return False

# --- 🔐 NUEVA FUNCIÓN DE LOGIN CONECTADA A SUPABASE ---
def login_supabase(username, password):
    """Verifica usuario y contraseña en la tabla 'users' de Supabase"""
    if not supabase:
        st.error("Error de conexión con la base de datos.")
        return None

    try:
        # Buscamos al usuario que coincida en nombre y contraseña
        response = supabase.table("users").select("*").eq("username", username).eq("password", password).execute()
        
        # Si encontramos algo, devolvemos los datos del usuario
        if len(response.data) > 0:
            user_info = response.data[0]
            
            # Buscamos también los datos de su organización para saber qué permisos tiene
            org_response = supabase.table("organizations").select("*").eq("id", user_info['org_id']).execute()
            
            if len(org_response.data) > 0:
                user_info['org_data'] = org_response.data[0] # Guardamos info de la empresa
            else:
                user_info['org_data'] = {"active_sectors": "[]"} # Por si acaso
                
            return user_info
            
        else:
            return None # Usuario o contraseña incorrectos
            
    except Exception as e:
        st.error(f"Error en login: {e}")
        return None

def save_result_to_db(student_id, sector, ire, friction, triggers, scores, history, organization="GENERICO"):
    """Guarda TODO: Rasgos individuales y las respuestas crudas para estadística"""
    if supabase:
        try:
            # Preparamos los triggers
            triggers_list = list(triggers) if isinstance(triggers, set) else triggers
            
            # Recuperamos organización
            if organization == "GENERICO" and 'user_data' in st.session_state:
                organization = st.session_state.user_data.get('organization', 'GENERICO')

            data = {
                "student_id": student_id,
                "sector": sector,
                "organization": organization,
                "created_at": datetime.now().isoformat(),

                # METRICAS GLOBALES
                "ire_score": float(ire),
                "friction_score": float(friction),
                "triggers": triggers_list,
                
                # EL OCTÓGONO (Para sacar descarriladores después)
                "achievement": scores.get('achievement', 0),
                "risk_propensity": scores.get('risk_propensity', 0),
                "innovativeness": scores.get('innovativeness', 0),
                "locus_control": scores.get('locus_control', 0),
                "self_efficacy": scores.get('self_efficacy', 0),
                "autonomy": scores.get('autonomy', 0),
                "ambiguity_tolerance": scores.get('ambiguity_tolerance', 0),
                "emotional_stability": scores.get('emotional_stability', 0),
                
                # LA JOYA DE LA CORONA (Para Validez y Fiabilidad)
                "raw_answers": history, # Guarda qué respondió en cada mes
                "raw_scores": scores    # Respaldo JSON
            }
            
            supabase.table("sape_results").insert(data).execute()
            print("✅ Datos completos guardados en Supabase")
            
        except Exception as e:
            print(f"❌ Error guardando: {e}")

# --- CONFIGURACIÓN DE CALIBRACIÓN ---
SCORE_MULTIPLIER = 1.5  # <--- SUBIDO A 1.5

# Límites matemáticos (Mínimo y Máximo posible) calculados con x1.5
# Esto permite que el IRE se escale de 0 a 100 real en cada sector.
SECTOR_LIMITS = {
    'TECH': {'min': 5.05, 'max': 61.35},
    'CONSULTORIA': {'min': 4.46, 'max': 63.54},
    'PYME': {'min': 8.12, 'max': 64.25},
    'HOSTELERIA': {'min': 5.05, 'max': 68.96},
    'AUTOEMPLEO': {'min': 9.21, 'max': 68.10},
    'SOCIAL': {'min': 10.31, 'max': 62.42},
    'INTRA': {'min': 8.60, 'max': 60.32},
    'SALUD': {'min': 11.10, 'max': 61.82},
    'PSICOLOGIA_SANITARIA': {'min': 12.72, 'max': 57.93},
    'PSICOLOGÍA_NO_SANITARIA': {'min': 11.18, 'max': 62.69}
}

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
# ==========================================
# 📂 CARGA DE PREGUNTAS (ARREGLADO PARA PUNTO Y COMA)
# ==========================================
@st.cache_data
# ==========================================
# 📂 CARGA DE PREGUNTAS (CORREGIDO SATE_V4)
# ==========================================
# Quitamos el cache un momento (ttl=0) para forzar que recargue el archivo nuevo
@st.cache_data(ttl=0)
# ==========================================
# 📂 1. CARGA DE PREGUNTAS (VERSIÓN BLINDADA)
# ==========================================
@st.cache_data(ttl=0)
def load_questions():
    file_path = "SATE_V4.csv"
    if not os.path.exists(file_path):
        st.error(f"❌ No encuentro el archivo: {file_path}")
        return []

    try:
        # Motor 'python' para leer comillas complejas y punto y coma
        df = pd.read_csv(file_path, sep=";", encoding="utf-8-sig", dtype=str, engine='python', on_bad_lines='skip')
        
        # Limpieza de cabeceras
        df.columns = df.columns.str.replace('"', '').str.replace("'", "").str.strip()
        
        # Fallback si leyó mal las columnas
        if len(df.columns) < 2:
            df = pd.read_csv(file_path, sep=",", encoding="utf-8-sig", dtype=str, engine='python')
            df.columns = df.columns.str.replace('"', '').str.replace("'", "").str.strip()

        if 'SECTOR' not in df.columns:
            st.error(f"❌ Falta la columna 'SECTOR'. Leído: {list(df.columns)}")
            return []

        # Limpieza de valores (quita comillas de todo)
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.replace('"', '').str.replace("'", "").str.strip()

        return df.to_dict('records')

    except Exception as e:
        st.error(f"💥 Error leyendo CSV: {e}")
        return []

# ==========================================
# 🧠 2. LÓGICA DE JUEGO Y CÁLCULOS
# ==========================================
def parse_logic(logic_string):
    """Interpreta strings como: 'risk_propensity 3 | achievement -1'"""
    if not logic_string or pd.isna(logic_string): return
    
    parts = str(logic_string).split('|')
    if 'octagon' not in st.session_state: st.session_state.octagon = {}
    
    for p in parts:
        p = p.strip()
        if not p: continue
        try:
            # Separamos por el último espacio (ej: "risk_propensity" y "3")
            key, val = p.rsplit(' ', 1)
            key = key.strip()
            val = float(val)
            st.session_state.octagon[key] = st.session_state.octagon.get(key, 0) + val
        except: pass

def cargar_cerebro_sape():
    """Define los arquetipos psicológicos"""
    return {
        "HUSTLER": {"risk_propensity": 8, "achievement": 8, "locus_control": 5},
        "VISIONARY": {"innovativeness": 9, "ambiguity_tolerance": 8, "autonomy": 7},
        "MANAGER": {"emotional_stability": 8, "leadership": 7, "self_efficacy": 6},
        "SOCIAL": {"adaptability": 8, "emotional_stability": 6, "leadership": 5}
    }

def diagnosticar_usuario_python(octagon, cerebro):
    """Compara al usuario con los arquetipos"""
    best_match = None
    min_dist = float('inf')
    
    # Normalizamos el octágono del usuario para comparar
    user_profile = {k: v for k, v in octagon.items()}
    
    # Aquí iría una lógica más compleja, pero para demo devolvemos un genérico
    # si no hay coincidencia exacta.
    return {
        "name": "PERFIL EMPRENDEDOR",
        "description": "Basado en tus decisiones, muestras un equilibrio entre riesgo y control.",
        "risk_level": "MEDIO"
    }

# ==========================================
# 🧠 CÁLCULOS MATEMÁTICOS (100% REAL BASADO EN 40 MESES)
# ==========================================

def get_max_potential_for_row(row, valid_keys):
    """
    Analiza una sola pregunta (fila) y devuelve cuánto es lo MÁXIMO 
    que se podía sumar a cada rasgo en esa pregunta concreta.
    """
    row_maxes = {k: 0 for k in valid_keys}
    
    # Revisamos las 4 opciones (A, B, C, D)
    for char in ['A', 'B', 'C', 'D']:
        logic_str = row.get(f'OPCION_{char}_LOGIC')
        if not logic_str or pd.isna(logic_str): continue
        
        # Parseamos la lógica de esta opción
        # Ej: "risk_propensity 3 | achievement -1"
        parts = str(logic_str).split('|')
        for p in parts:
            p = p.strip()
            if not p: continue
            try:
                # Separamos clave y valor
                # "risk_propensity 3" -> key="risk_propensity", val=3.0
                if ' ' in p:
                    key, val = p.rsplit(' ', 1)
                    key = key.strip()
                    val = float(val)
                    
                    # Si esta opción da más puntos que las anteriores para este rasgo, actualizamos el máximo de esta pregunta
                    if key in row_maxes:
                        if val > row_maxes[key]:
                            row_maxes[key] = val
            except: pass
            
    return row_maxes

# ==========================================
# 🧠 MOTOR MATEMÁTICO Y LÓGICO (CORREGIDO: LIDERAZGO Y ADAPTABILIDAD)
# ==========================================

def parse_logic(logic_string):
    """Interpreta strings del CSV y suma puntos."""
    if not logic_string or pd.isna(logic_string): return
    
    parts = str(logic_string).split('|')
    if 'octagon' not in st.session_state: st.session_state.octagon = {}
    
    for p in parts:
        p = p.strip()
        if not p: continue
        try:
            if ' ' in p:
                key, val = p.rsplit(' ', 1)
                key = key.strip()
                val = float(val)
                st.session_state.octagon[key] = st.session_state.octagon.get(key, 0) + val
        except: pass

def get_max_potential_for_row(row, valid_keys):
    """Mira cuánto era lo máximo posible a sumar en una pregunta"""
    row_maxes = {k: 0 for k in valid_keys}
    
    for char in ['A', 'B', 'C', 'D']:
        logic_str = row.get(f'OPCION_{char}_LOGIC')
        if not logic_str or pd.isna(logic_str): continue
        
        parts = str(logic_str).split('|')
        for p in parts:
            p = p.strip()
            if not p: continue
            try:
                if ' ' in p:
                    key, val = p.rsplit(' ', 1)
                    key = key.strip()
                    val = float(val)
                    if key in row_maxes and val > row_maxes[key]:
                        row_maxes[key] = val
            except: pass
    return row_maxes

# ==========================================
# 🧠 CÁLCULOS (CON FACTOR DE SATURACIÓN PARA DESCARRILADORES)
# ==========================================
def calculate_results():
    """
    Calcula porcentajes REALES aplicando un FACTOR DE SATURACIÓN.
    Si el usuario alcanza el 80% del máximo posible, ya se le da el 100%.
    Esto facilita que aparezcan los 'descarriladores' (>90%).
    """
    
    # 1. CLAVES EXACTAS DEL CSV
    valid_keys = [
        "risk_propensity",      # Riesgo
        "ambiguity_tolerance",  # Ambigüedad
        "innovativeness",       # Innovación
        "locus_control",        # Locus de Control
        "emotional_stability",  # Estabilidad
        "achievement",          # Logro
        "self_efficacy",        # Autoeficacia (Liderazgo)
        "autonomy"              # Autonomía (Adaptabilidad)
    ]
    
    user_scores = st.session_state.get('octagon', {})
    
    # 2. CALCULAR EL MÁXIMO TEÓRICO
    all_questions = st.session_state.get('data', [])
    total_max_possibles = {k: 0 for k in valid_keys}
    
    for row in all_questions:
        row_maxs = get_max_potential_for_row(row, valid_keys)
        for k in valid_keys:
            total_max_possibles[k] += row_maxs[k]

    # 3. CÁLCULO DE PORCENTAJES CON SATURACIÓN
    # ---------------------------------------------------------
    SATURATION_FACTOR = 0.80  # <--- LA CLAVE MÁGICA
    # Significa que si obtienes el 80% de los puntos posibles, 
    # tu nota ya será de 100/100.
    # ---------------------------------------------------------

    octagon_norm = {}
    
    for k in valid_keys:
        u_val = user_scores.get(k, 0)
        max_val = total_max_possibles.get(k, 0)
        
        if max_val > 0:
            # El nuevo "100%" es el 80% del máximo real
            saturated_max = max_val * SATURATION_FACTOR
            
            percentage = (u_val / saturated_max) * 100
        else:
            percentage = 0
            
        # Clamp: Aseguramos que no pase de 100 ni baje de 0
        octagon_norm[k] = max(0, min(100, percentage))

    # 4. KPI GLOBALES
    if octagon_norm:
        avg = sum(octagon_norm.values()) / len(octagon_norm)
    else:
        avg = 0
    
    ire = avg 
    friction = max(0, 100 - ire)
    
    return int(ire), int(avg), int(friction), [], [], 0, octagon_norm, {}

def radar_chart():
    """Genera el gráfico con las etiquetas CORRECTAS (Liderazgo/Adaptabilidad)"""
    _, _, _, _, _, _, scores, _ = calculate_results()
    
    if not scores: return go.Figure()
    
    # MAPEO DE CLAVES CSV -> ETIQUETAS VISUALES
    LABELS = {
        "risk_propensity": "Propensión al riesgo", 
        "ambiguity_tolerance": "Tolerancia a la ambigüedad",
        "innovativeness": "Innovación", 
        "locus_control": "Locus de control",
        "emotional_stability": "Estabilidad emocional", 
        "achievement": "Orientación al logro",
        "self_efficacy": "Autoeficacia",
        "autonomy": "Autonomía"
    }
    
    categories = [LABELS.get(k, k) for k in scores.keys()]
    values = list(scores.values())
    
    categories.append(categories[0])
    values.append(values[0])
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name='Tu Perfil',
        line_color='#0D248D',
        fillcolor='rgba(13, 36, 141, 0.2)'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=10, color="gray")),
            angularaxis=dict(tickfont=dict(size=12, color="black", weight="bold"))
        ),
        showlegend=False,
        margin=dict(l=40, r=40, t=20, b=20),
        height=350,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    return fig

def save_result_to_db(student_id, sector, ire, friction, triggers, scores, history, organization):
    """Guarda en Supabase"""
    try:
        scores_json = json.dumps(scores)
        history_json = json.dumps(history)
        supabase.table("sape_results").insert({
            "student_id": student_id,
            "sector": sector,
            "ire": ire,
            "friction": friction,
            "octagon": scores_json,
            "organization": organization,
            "created_at": datetime.now().isoformat()
        }).execute()
    except Exception as e:
        print(f"Error guardando: {e}")

# ==========================================
# 🎮 3. INTERFAZ SIMULADOR (CORREGIDO)
# ==========================================
def run_simulator_logic():
    # --- CSS: Estilos específicos para el Juego ---
    st.markdown("""
    <style>
        /* Fondo General */
        .stApp { background-color: #050A1F; }
        
        /* Textos Blancos */
        h1, h2, h3, h4, p, div, span, label, li { color: white !important; }
        
        /* CAJA DE NARRATIVA (Izquierda) */
        .narrative-box {
            background-color: transparent; 
            padding-right: 20px;
            font-size: 1.25rem; 
            line-height: 1.6;
            border-left: 4px solid #0D248D; 
            padding-left: 15px;
        }

        /* BOTONES DE RESPUESTA (Derecha) */
        div.stButton > button {
            background-color: #02040B !important; 
            color: white !important;
            border: 1px solid #0D248D !important; 
            border-radius: 15px !important; 
            padding: 20px !important;
            font-size: 1rem !important;
            width: 100%;
            margin-bottom: 12px;
            transition: all 0.2s ease-in-out !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }

        /* EFECTO HOVER */
        div.stButton > button:hover {
            transform: scale(1.05) !important; 
            background-color: #0D248D !important; 
            border-color: white !important;
            z-index: 99;
            cursor: pointer;
        }
        
        div[data-testid="column"] {
            display: flex;
            flex-direction: column;
            justify-content: center; 
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Inicialización de variables
    keys = ['instructions_seen', 'data_verified', 'started', 'finished', 'current_step', 'history', 'user_data', 'octagon']
    for k in keys:
        if k not in st.session_state: 
            st.session_state[k] = {} if k in ['history', 'user_data', 'octagon'] else (False if k != 'current_step' else 0)
    if isinstance(st.session_state.history, dict): st.session_state.history = []

    # ----------------------------------------------------
    # PANTALLA 1: Bienvenida
    # ----------------------------------------------------
    if not st.session_state.instructions_seen:
        c1, c2, c3 = st.columns([1, 2, 1]) 
        with c2:
            if os.path.exists("logo_blanco.png"): st.image("logo_blanco.png", use_container_width=True)
            elif os.path.exists("logo_original.png"): st.image("logo_original.png", use_container_width=True)
            else: st.markdown("<h1 style='text-align: center;'>🧬 AUDEO</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center;'>Bienvenido/a Fundador/a</h3>", unsafe_allow_html=True)
        st.markdown("---")
        if st.button("✅ COMENZAR", use_container_width=True):
            st.session_state.instructions_seen = True
            st.rerun()

    # ----------------------------------------------------
    # PANTALLA 2: Datos
    # ----------------------------------------------------
    elif not st.session_state.data_verified:
        st.markdown("### 👤 Identificación")
        with st.form("user_data_form"):
            name = st.text_input("Nombre", value=st.session_state.user_data.get('username', '')) 
            if st.form_submit_button("CONTINUAR"):
                st.session_state.user_data.update({"name": name})
                st.session_state.data_verified = True
                st.rerun()

    # ----------------------------------------------------
    # PANTALLA 3: Selección de Sector
    # ----------------------------------------------------
    elif not st.session_state.started:
        st.markdown(f"### 🚀 Selecciona tu Sector:")
        
        user_org = st.session_state.user_data.get('org_id')
        allowed = []
        try:
            r = supabase.table("organizations").select("active_sectors").eq("id", user_org).execute()
            if r.data:
                raw = r.data[0].get('active_sectors', '[]')
                try: allowed = json.loads(raw)
                except: 
                    try: allowed = ast.literal_eval(raw)
                    except: allowed = []
        except: allowed = []

        BUTTON_MAP = {
            "TECH": "Startup Tecnológica", "RETAIL": "Pequeña Empresa (PYME)",
            "FREELANCE": "Autoempleo", "INTRA": "Intraemprendimiento",
            "PSICOLOGÍA_SANITARIA": "Psicología Sanitaria", "CONSULTORÍA": "Consultoría",
            "HOSTELERÍA": "Hostelería", "SOCIAL": "Social",
            "SALUD": "Salud", "PSICOLOGÍA_NO_SANITARIA": "Psicología No Sanitaria"
        }

        CSV_TRANSLATOR = {
            "RETAIL": ["PYME", "PEQUEÑA EMPRESA", "RETAIL"],
            "FREELANCE": ["AUTOEMPLEO", "FREELANCE", "AUTONOMO"],
            "CONSULTORÍA": ["CONSULTORIA", "CONSULTORÍA"],
            "HOSTELERÍA": ["HOSTELERIA", "HOSTELERÍA", "TURISMO"],
            "TECH": ["TECH", "STARTUP", "TECNOLOGIA"],
            "PSICOLOGÍA_SANITARIA": ["PSICOLOGIA_SANITARIA", "PSICOLOGÍA_SANITARIA"],
            "PSICOLOGÍA_NO_SANITARIA": ["PSICOLOGIA_NO_SANITARIA", "PSICOLOGÍA_NO_SANITARIA"]
        }

        all_q = load_questions() 

        def go(label, code_admin):
            valid_names = CSV_TRANSLATOR.get(code_admin, [code_admin])
            qs = []
            for row in all_q:
                sector_csv = str(row.get('SECTOR','')).strip().replace('"','').upper()
                if sector_csv in valid_names or sector_csv == code_admin:
                    qs.append(row)
            if not qs: qs = [x for x in all_q if code_admin in str(x.get('SECTOR','')).upper()]

            if not qs:
                st.error(f"⚠️ No hay preguntas para: {code_admin}")
                return
            
            st.session_state.data = qs
            st.session_state.user_data["sector"] = code_admin
            st.session_state.started = True
            st.rerun()

        if not allowed: st.error("Sin sectores asignados.")
        else:
            cols = st.columns(2)
            valid = [c for c in allowed if c in BUTTON_MAP]
            for i, code in enumerate(valid):
                with cols[i%2]:
                    if st.button(BUTTON_MAP[code], key=code, use_container_width=True):
                        go(BUTTON_MAP[code], code)

    # ----------------------------------------------------
    # PANTALLA 4: EL JUEGO (CORREGIDO)
    # ----------------------------------------------------
    elif not st.session_state.finished:
        if not st.session_state.data:
            st.error("Error de datos."); st.session_state.started = False; st.rerun()
            
        if st.session_state.current_step >= len(st.session_state.data):
            st.session_state.finished = True; st.rerun()
            
        row = st.session_state.data[st.session_state.current_step]
        
        # 1. LOGO
        if os.path.exists("logo_blanco.png"): 
            st.image("logo_blanco.png", width=120)
        else:
            st.markdown("## 🧬 AUDEO")

        # 2. BARRA DE PROGRESO SEGMENTADA
        total_steps = len(st.session_state.data)
        current = st.session_state.current_step
        
        bar_html = f"""<div style="display: flex; gap: 3px; margin-bottom: 20px;">"""
        for i in range(total_steps):
            if i < current: bg = "#0D248D" # Completado
            elif i == current: bg = "#FFFFFF" # Actual
            else: bg = "rgba(255,255,255,0.2)" # Pendiente
            bar_html += f'<div style="flex: 1; height: 6px; background-color: {bg}; border-radius: 2px;"></div>'
        bar_html += "</div>"
        st.markdown(bar_html, unsafe_allow_html=True)
        
        # 3. TÍTULO
        st.markdown(f"<h3 style='margin-bottom: 5px;'>{row.get('TITULO','Desafío')}</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: #ccc !important; font-size: 0.9rem;'>Mes {row.get('MES', current+1)}</p>", unsafe_allow_html=True)
        st.write("") 

        # 4. COLUMNAS
        col_narrativa, col_opciones = st.columns([0.55, 0.45], gap="large")
        
        with col_narrativa:
            st.markdown(f"""<div class="narrative-box">{row.get('NARRATIVA','')}</div>""", unsafe_allow_html=True)

        with col_opciones:
            opts = []
            for c in ['A','B','C','D']:
                txt = row.get(f'OPCION_{c}_TXT')
                if txt and str(txt).strip():
                    opts.append({'t': txt, 'l': row.get(f'OPCION_{c}_LOGIC'), 'id': c})
            random.shuffle(opts)
            
            for o in opts:
                if st.button(o['t'], key=f"{current}_{o['id']}", use_container_width=True):
                    parse_logic(o['l'])
                    st.session_state.history.append({'op': o['id'], 'txt': o['t']})
                    st.session_state.current_step += 1
                    st.rerun()

# ----------------------------------------------------
    # PANTALLA 5: RESULTADOS (MATEMÁTICAS Y ETIQUETAS CORRECTAS)
    # ----------------------------------------------------
    else:
        # 1. ESTILOS
        st.markdown("""
        <style>
            .stApp { background-color: #FFFFFF !important; }
            h1, h2, h3, h4, p, li, span, div, label { color: #050A1F !important; }
            .metric-card {
                background-color: #F8F9FA;
                border: 1px solid #E9ECEF;
                border-radius: 12px;
                padding: 20px;
                text-align: center;
                box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            }
            .metric-value { font-size: 2.5rem; font-weight: 800; color: #0D248D; margin: 10px 0; }
            .metric-label { font-size: 0.9rem; color: #666; text-transform: uppercase; letter-spacing: 1.2px; font-weight: 600; }
        </style>
        """, unsafe_allow_html=True)

        # 2. CÁLCULOS
        ire, avg, fric, _, _, _, scores, _ = calculate_results()
        
        # 3. CABECERA
        c_logo, c_info = st.columns([1, 4])
        with c_logo:
            if os.path.exists("logo_original.png"): st.image("logo_original.png", width=130)
            else: st.markdown("## 🧬 AUDEO")
        with c_info:
            st.markdown(f"# Informe de Perfil Emprendedor")
            st.markdown(f"**Usuario:** {st.session_state.user_data.get('name', 'Anónimo')} | **Sector:** {st.session_state.user_data.get('sector', 'General')}")
        st.markdown("---")

        # 4. KPIs
        k1, k2, k3 = st.columns(3)
        c_ire = "#2ECC71" if ire >= 70 else "#F1C40F" if ire >= 50 else "#E74C3C"
        c_fric = "#E74C3C" if fric >= 50 else "#F1C40F" if fric >= 30 else "#2ECC71"
        
        with k1: st.markdown(f"""<div class="metric-card"><div class="metric-label">Índice Resiliencia (IRE)</div><div class="metric-value" style="color: {c_ire}">{int(ire)}/100</div></div>""", unsafe_allow_html=True)
        with k2: st.markdown(f"""<div class="metric-card"><div class="metric-label">Potencial Competencial</div><div class="metric-value">{int(avg)}/100</div></div>""", unsafe_allow_html=True)
        with k3: st.markdown(f"""<div class="metric-card"><div class="metric-label">Nivel de Fricción</div><div class="metric-value" style="color: {c_fric}">{int(fric)}%</div></div>""", unsafe_allow_html=True)

        st.write("") 

        # 5. GRÁFICO Y BARRAS
        col_radar, col_skills = st.columns([1, 1.2], gap="large")
        
        with col_radar:
            st.markdown("### 🕸️ Mapa de Talento")
            st.plotly_chart(radar_chart(), use_container_width=True)
            if ire > 75: diag = "Tu perfil muestra una **alta alineación** con las exigencias del emprendimiento."
            elif ire > 50: diag = "Tienes una base sólida, pero hay **áreas de fricción** que debes trabajar."
            else: diag = "Se detectan **riesgos significativos**. Recomendamos formación antes de emprender."
            st.info(diag)

        with col_skills:
            st.markdown("### 📊 Detalle de Competencias")
            
            # DICCIONARIO CORREGIDO (COINCIDE CON CSV)
            LABELS = {
                "risk_propensity": "Propensión al Riesgo", 
                "ambiguity_tolerance": "Tolerancia Ambigüedad",
                "innovativeness": "Innovación", 
                "locus_control": "Locus de Control",       # Corregido
                "emotional_stability": "Estabilidad Emocional", 
                "achievement": "Orientación al Logro",
                "self_efficacy": "Autoeficacia",           # Corregido (Antes Liderazgo)
                "autonomy": "Autonomía"                    # Corregido (Antes Adaptabilidad)
            }
            
            for key, val in scores.items():
                nombre = LABELS.get(key, key.capitalize())
                mask_width = 100 - val 
                
                barra_html = f"""
                <div style="margin-bottom: 18px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                        <span style="font-weight:600; font-size:0.95rem; color: #333;">{nombre}</span>
                        <span style="font-weight:700; color: #333;">{int(val)}%</span>
                    </div>
                    <div style="width: 100%; height: 14px; background-color: #E9ECEF; border-radius: 7px; position: relative; overflow: hidden; border: 1px solid #ddd;">
                        <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(to right, #E74C3C 0%, #E74C3C 25%, #F1C40F 25%, #F1C40F 60%, #2ECC71 60%, #2ECC71 90%, #E74C3C 90%, #E74C3C 100%);"></div>
                        <div style="position: absolute; top: 0; right: 0; width: {mask_width}%; height: 100%; background-color: #E9ECEF;"></div>
                        <div style="position: absolute; top: 0; right: {mask_width}%; width: 2px; height: 100%; background-color: rgba(0,0,0,0.2);"></div>
                    </div>
                </div>
                """
                st.markdown(barra_html, unsafe_allow_html=True)

        # 6. GUARDAR
        if 'saved' not in st.session_state:
            save_result_to_db(st.session_state.user_data.get('username'), st.session_state.user_data.get('sector'), ire, fric, [], scores, st.session_state.history, st.session_state.user_data.get('org_id'))
            st.session_state.saved = True
            st.success("✅ Resultados guardados en tu expediente.")
        
# ==========================================
# 🏢 PANEL CLIENTE (MANAGER) - DINÁMICO
# ==========================================
def render_manager_dashboard():
    user = st.session_state.user_data
    org_id = user.get('org_id')
    
    # CABECERA
    c1, c2 = st.columns([1, 6])
    with c1:
        if os.path.exists("logo_original.png"): st.image("logo_original.png", use_container_width=True)
    with c2:
        # Título dinámico: Muestra el nombre de la empresa O avisa del error
        titulo = org_id.upper() if (org_id and org_id != "None") else "⚠️ ERROR: SIN EMPRESA"
        st.markdown(f"<h1 style='color: #0D248D;'>Panel de Control: {titulo}</h1>", unsafe_allow_html=True)
        st.caption(f"👋 Hola, {user.get('username')}")
    st.divider()

    # BLOQUEO DE SEGURIDAD
    if not org_id or org_id == "None":
        st.error("❌ ERROR DE CONFIGURACIÓN")
        st.warning("Tu usuario no tiene una organización asignada correctamente.")
        st.info("Por favor, contacta con el Administrador para que corrija tu usuario (campo org_id).")
        return

    # DASHBOARD
    try:
        # 1. Cargar Datos
        df_users = pd.DataFrame(supabase.table("users").select("*").eq("org_id", org_id).eq("role", "STUDENT").execute().data)
        df_res = pd.DataFrame(supabase.table("sape_results").select("*").eq("organization", org_id).execute().data)
        
        if df_users.empty:
            st.warning("No hay alumnos registrados en tu organización todavía.")
            return

        # 2. Cruce de Datos
        if not df_res.empty:
            df_res = df_res[['student_id', 'ire', 'friction', 'octagon', 'created_at']]
            df_final = pd.merge(df_users, df_res, left_on='username', right_on='student_id', how='left')
        else:
            df_final = df_users.copy()
            for c in ['ire', 'friction', 'octagon', 'created_at']: df_final[c] = None

        df_final['Estado'] = df_final['created_at'].apply(lambda x: "✅ Completado" if pd.notnull(x) else "❌ Pendiente")
        df_final['Fecha'] = pd.to_datetime(df_final['created_at']).dt.strftime('%d/%m/%Y')

        # 3. KPIs
        hechos = len(df_final[df_final['Estado'] == "✅ Completado"])
        avg_ire = df_final['ire'].mean() if hechos > 0 else 0
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Alumnos Total", len(df_final))
        k2.metric("Completados", f"{hechos}")
        k3.metric("Nota Media", f"{avg_ire:.1f}")

        # 4. Pestañas
        t1, t2, t3 = st.tabs(["🚦 Seguimiento", "📊 Grupo", "⭐ Talento"])
        
        with t1:
            st.dataframe(df_final[['username', 'Estado', 'ire', 'Fecha']], use_container_width=True)
        
        with t2:
            if hechos > 0:
                try:
                    valid = df_final['octagon'].dropna().apply(lambda x: eval(x) if isinstance(x, str) else x).tolist()
                    if valid:
                        avg = {}
                        for k in valid[0].keys(): avg[k] = sum(d.get(k,0) for d in valid)/len(valid)
                        st.plotly_chart(radar_chart(avg, "Media Clase"), use_container_width=True)
                except: pass
            else: st.info("Faltan datos para la gráfica.")

        with t3:
            if hechos > 0:
                fig = px.scatter(df_final[df_final['Estado']=="✅ Completado"], x="ire", y="friction", color="ire", hover_data=["username"], title="Mapa Talento")
                st.plotly_chart(fig, use_container_width=True)
            else: st.info("Faltan datos para el mapa.")

    except Exception as e: st.error(f"Error cargando datos: {e}")

# ==========================================
# 🚀 MAIN (ROUTER)
# ==========================================
def main():
    inject_custom_css()
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if 'user_data' not in st.session_state: st.session_state.user_data = {}

    if not st.session_state.logged_in:
        c1, c2, c3 = st.columns([1, 1, 1])
        with c2:
            if os.path.exists("logo_original.png"): st.image("logo_original.png", use_container_width=True)
            st.markdown("<h2 style='text-align: center; color: #0D248D;'>ACCESO CORPORATIVO</h2>", unsafe_allow_html=True)
            with st.form("login_form"):
                u = st.text_input("Usuario")
                p = st.text_input("Contraseña", type="password")
                if st.form_submit_button("ENTRAR", use_container_width=True):
                    try:
                        res = supabase.table("users").select("*").eq("username", u).eq("password", p).execute()
                        if res.data:
                            st.session_state.logged_in = True
                            st.session_state.user_data = res.data[0]
                            st.rerun()
                        else: st.error("❌ Credenciales incorrectas")
                    except Exception as e: st.error(f"Error de conexión: {e}")
    else:
        with st.sidebar:
            st.write(f"👤 **{st.session_state.user_data.get('username')}**")
            if st.button("Cerrar Sesión"):
                st.session_state.logged_in = False
                st.session_state.user_data = {}
                st.rerun()

        role = st.session_state.user_data.get('role')
        if role == 'ADMIN': render_admin_dashboard()
        elif role == 'MANAGER': render_manager_dashboard()
        else: run_simulator_logic()

if __name__ == "__main__":
    main()