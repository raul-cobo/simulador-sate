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
        "HUSTLER": {"risk_propensity": 8, "achievement": 8, "locus_of_control": 5},
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

def calculate_results():
    """Calcula IRE, Fricción y normaliza puntuaciones"""
    oct_raw = st.session_state.get('octagon', {})
    
    # 1. Normalización simple (0-100)
    # Asumimos un rango teórico de -20 a +20 por dimensión tras 12 preguntas
    octagon_norm = {}
    valid_keys = ["risk_propensity", "ambiguity_tolerance", "innovativeness", "locus_of_control", 
                  "emotional_stability", "achievement", "leadership", "adaptability"]
    
    for k in valid_keys:
        raw = oct_raw.get(k, 0)
        # Transformación lineal: -10 es 0, +10 es 100 (aprox)
        norm = 50 + (raw * 4) 
        octagon_norm[k] = max(0, min(100, norm))

    # 2. Cálculo del IRE (Índice de Resiliencia Emprendedora)
    # Promedio de las competencias clave
    if octagon_norm:
        avg = sum(octagon_norm.values()) / len(octagon_norm)
    else:
        avg = 50
    
    ire = avg # En este modelo simplificado, el IRE es el promedio competencial
    
    # 3. Fricción (Inverso del IRE con factor de aleatoriedad para demo)
    friction = max(0, 100 - ire)
    
    return int(ire), int(avg), int(friction), [], [], 0, octagon_norm, {}

def radar_chart():
    """Genera el gráfico de araña"""
    data = st.session_state.get('octagon', {})
    if not data: return go.Figure()
    
    # Usamos los datos normalizados de calculate_results si es posible, si no, raw
    # Para simplificar, recalculamos rápido normalización visual
    categories = list(data.keys())
    values = [50 + (v*4) for v in data.values()] # Normalización visual rápida
    values = [max(0, min(100, v)) for v in values] # Clamp 0-100
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=values, theta=categories, fill='toself', name='Tú'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False)
    return fig

def save_result_to_db(student_id, sector, ire, friction, triggers, scores, history, organization):
    """Guarda en Supabase"""
    try:
        supabase.table("sape_results").insert({
            "student_id": student_id,
            "sector": sector,
            "ire": ire,
            "friction": friction,
            "octagon": str(scores),
            "organization": organization,
            "created_at": datetime.now().isoformat()
        }).execute()
    except Exception as e:
        print(f"Error guardando: {e}")

# ==========================================
# 🎮 3. INTERFAZ SIMULADOR (CON TRADUCTOR)
# ==========================================
def run_simulator_logic():
    st.markdown("<style>.stApp { background-color: white; }</style>", unsafe_allow_html=True)
    
    # Inicialización de variables
    keys = ['instructions_seen', 'data_verified', 'started', 'finished', 'current_step', 'history', 'user_data', 'octagon']
    for k in keys:
        if k not in st.session_state: 
            st.session_state[k] = {} if k in ['history', 'user_data', 'octagon'] else (False if k != 'current_step' else 0)
    if isinstance(st.session_state.history, dict): st.session_state.history = []

    # PANTALLA 1: Bienvenida
    if not st.session_state.instructions_seen:
        c1, c2, c3 = st.columns([1, 2, 1]) 
        with c2:
            if os.path.exists("logo_original.png"): st.image("logo_original.png", use_container_width=True)
            else: st.markdown("<h2 style='text-align: center; color: #0D248D;'>🧬 AUDEO</h1>", unsafe_allow_html=True)
        st.info("**Bienvenido/a.** Estás a punto de asumir el rol de fundador/a.")
        if st.button("✅ COMENZAR", use_container_width=True):
            st.session_state.instructions_seen = True
            st.rerun()

    # PANTALLA 2: Datos
    elif not st.session_state.data_verified:
        st.markdown("#### 1. Identificación")
        with st.form("user_data_form"):
            name = st.text_input("Nombre", value=st.session_state.user_data.get('username', '')) 
            if st.form_submit_button("CONTINUAR"):
                st.session_state.user_data.update({"name": name})
                st.session_state.data_verified = True
                st.rerun()

    # PANTALLA 3: Sector
    elif not st.session_state.started:
        st.markdown(f"#### 2. Selecciona tu Sector:")
        
        # 1. Recuperar permisos (Sectores activos de la empresa)
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

        # 2. Mapa de Botones (CÓDIGO ADMIN -> TEXTO BOTÓN)
        BUTTON_MAP = {
            "TECH": "Startup Tecnológica", 
            "RETAIL": "Pequeña Empresa (PYME)",
            "FREELANCE": "Autoempleo", 
            "INTRA": "Intraemprendimiento",
            "PSICOLOGÍA_SANITARIA": "Psicología Sanitaria", 
            "CONSULTORÍA": "Consultoría",
            "HOSTELERÍA": "Hostelería", 
            "SOCIAL": "Social",
            "SALUD": "Salud", 
            "PSICOLOGÍA_NO_SANITARIA": "Psicología No Sanitaria"
        }

        # 3. TRADUCTOR (CÓDIGO ADMIN -> CÓDIGO EN EL CSV) 
        # Esto es lo que arregla el error "No encontrado"
        CSV_TRANSLATOR = {
            "RETAIL": ["PYME", "PEQUEÑA EMPRESA", "RETAIL"],     # Si busca RETAIL, acepta PYME
            "FREELANCE": ["AUTOEMPLEO", "FREELANCE", "AUTONOMO"],
            "CONSULTORÍA": ["CONSULTORIA", "CONSULTORÍA"],       # Arregla acentos
            "HOSTELERÍA": ["HOSTELERIA", "HOSTELERÍA", "TURISMO"],
            "TECH": ["TECH", "STARTUP", "TECNOLOGIA"],
            "PSICOLOGÍA_SANITARIA": ["PSICOLOGIA_SANITARIA", "PSICOLOGÍA_SANITARIA"],
            "PSICOLOGÍA_NO_SANITARIA": ["PSICOLOGIA_NO_SANITARIA", "PSICOLOGÍA_NO_SANITARIA"]
        }

        all_q = load_questions() 

        def go(label, code_admin):
            # Buscar sinónimos válidos para este código
            valid_names = CSV_TRANSLATOR.get(code_admin, [code_admin])
            
            # Filtramos preguntas que coincidan con ALGUNO de los nombres válidos
            qs = []
            for row in all_q:
                sector_csv = str(row.get('SECTOR','')).strip().replace('"','').upper()
                if sector_csv in valid_names or sector_csv == code_admin:
                    qs.append(row)
            
            if not qs:
                # Intento final parcial
                qs = [x for x in all_q if code_admin in str(x.get('SECTOR','')).upper()]

            if not qs:
                st.error(f"⚠️ No hay preguntas para: {code_admin} (Buscado en CSV como: {valid_names})")
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

    # PANTALLA 4: Juego
    elif not st.session_state.finished:
        if not st.session_state.data:
            st.error("Error de datos."); st.session_state.started = False; st.rerun()
            
        if st.session_state.current_step >= len(st.session_state.data):
            st.session_state.finished = True; st.rerun()
            
        row = st.session_state.data[st.session_state.current_step]
        st.progress((st.session_state.current_step+1)/len(st.session_state.data))
        
        st.markdown("""<style>.stApp {background-color: #050A1F !important;} p,h1,h2,h3,div,span {color:white !important}</style>""", unsafe_allow_html=True)
        
        st.markdown(f"### {row.get('TITULO','')}")
        st.write(row.get('NARRATIVA',''))
        
        opts = []
        for c in ['A','B','C','D']:
            txt = row.get(f'OPCION_{c}_TXT')
            if txt and str(txt).strip():
                opts.append({'t': txt, 'l': row.get(f'OPCION_{c}_LOGIC'), 'id': c})
        
        random.shuffle(opts)
        for o in opts:
            if st.button(o['t'], key=f"{st.session_state.current_step}_{o['id']}", use_container_width=True):
                parse_logic(o['l'])
                st.session_state.history.append({'op': o['id'], 'txt': o['t']})
                st.session_state.current_step += 1
                st.rerun()

    # PANTALLA 5: Resultados
    else:
        st.markdown("""<style>.stApp {background-color: white !important;} p,h1,h2,h3,div,span {color:black !important}</style>""", unsafe_allow_html=True)
        ire, avg, fric, _, _, _, scores, _ = calculate_results()
        
        st.title(f"Resultados: {st.session_state.user_data.get('name')}")
        k1, k2, k3 = st.columns(3)
        k1.metric("IRE", ire); k2.metric("Potencial", avg); k3.metric("Fricción", fric)
        st.plotly_chart(radar_chart(), use_container_width=True)
        
        if 'saved' not in st.session_state:
            save_result_to_db(st.session_state.user_data.get('username'), st.session_state.user_data.get('sector'), ire, fric, [], scores, st.session_state.history, st.session_state.user_data.get('org_id'))
            st.session_state.saved = True
            st.success("Guardado.")

# ==========================================
# 👑 PANEL ADMIN (CON GESTIÓN DE SECTORES)
# ==========================================
def render_admin_dashboard():
    st.title("👑 Panel de Administración")
    
    # 1. DEFINIR EL MAPA DE SECTORES (Nombre Visible -> Código Interno)
    # Esto asegura que lo que guardes coincida con lo que el simulador espera.
    SECTOR_OPTIONS = {
        "Startup Tecnológica (Scalable)": "TECH",
        "Pequeña y Mediana Empresa (PYME)": "RETAIL", # Ojo: en tu CSV vi "PYME", aquí unificamos.
        "Autoempleo / Freelance": "FREELANCE", 
        "Intraemprendimiento": "INTRA",
        "Psicología Sanitaria": "PSICOLOGÍA_SANITARIA", 
        "Consultoría / Servicios": "CONSULTORÍA",
        "Hostelería y Turismo": "HOSTELERÍA", 
        "Emprendimiento Social": "SOCIAL",
        "Salud": "SALUD", 
        "Psicología No Sanitaria": "PSICOLOGÍA_NO_SANITARIA"
    }
    
    # Lista solo de códigos para validar
    VALID_CODES = list(SECTOR_OPTIONS.values())

    try:
        # KPIs Básicos
        count_users = supabase.table("users").select("*", count="exact").execute().count
        count_results = supabase.table("sape_results").select("*", count="exact").execute().count
        count_orgs = supabase.table("organizations").select("*", count="exact").execute().count
        
        # Recuperar datos de empresas
        res_orgs = supabase.table("organizations").select("id", "name", "active_sectors").execute()
        org_data_list = res_orgs.data
        valid_ids = [o['id'] for o in org_data_list]
    except: 
        count_users = count_results = count_orgs = 0
        valid_ids = []
        org_data_list = []

    k1, k2, k3 = st.columns(3)
    k1.metric("👥 Usuarios", count_users)
    k2.metric("📊 Simulaciones", count_results)
    k3.metric("🏢 Empresas", count_orgs)
    
    tab1, tab2, tab3, tab4 = st.tabs(["🔎 INSPECTOR", "👥 USUARIOS", "📈 RESULTADOS", "🏢 EMPRESAS"])
    
    # --- PESTAÑA 1: INSPECTOR ---
    with tab1:
        st.markdown("### 🕵️ Inspector de Empresas")
        if valid_ids:
            sel_org = st.selectbox("Selecciona Organización:", valid_ids)
            if sel_org:
                try:
                    u_data = supabase.table("users").select("*").eq("org_id", sel_org).execute().data
                    r_data = supabase.table("sape_results").select("*").eq("organization", sel_org).execute().data
                    
                    if u_data:
                        df_u = pd.DataFrame(u_data)
                        df_r = pd.DataFrame(r_data) if r_data else pd.DataFrame()
                        
                        if not df_r.empty:
                            df_r = df_r[['student_id', 'ire', 'friction', 'created_at']].rename(columns={'created_at': 'fecha'})
                            df_final = pd.merge(df_u, df_r, left_on='username', right_on='student_id', how='left')
                        else:
                            df_final = df_u
                            df_final['fecha'] = None; df_final['ire'] = None

                        df_final['Estado'] = df_final['fecha'].apply(lambda x: "✅ Hecho" if pd.notnull(x) else "❌ Pendiente")
                        st.dataframe(df_final[['username', 'role', 'Estado', 'ire', 'fecha']], use_container_width=True)
                    else:
                        st.info("Esta empresa no tiene usuarios.")
                except Exception as e: st.error(f"Error: {e}")
        else: st.warning("No hay empresas.")

    # --- PESTAÑA 2: USUARIOS ---
    with tab2:
        c1, c2 = st.columns([1, 1.5])
        with c1: 
            st.markdown("### ➕ Nuevo Usuario")
            with st.form("add_user"):
                u = st.text_input("Usuario"); p = st.text_input("Password", "1234")
                r = st.selectbox("Rol", ["STUDENT", "MANAGER", "ADMIN"])
                o = st.selectbox("Org ID", valid_ids) if valid_ids else st.text_input("Org ID")
                if st.form_submit_button("Crear"):
                    try:
                        supabase.table("users").insert({"username": u, "password": p, "role": r, "org_id": o}).execute()
                        st.success(f"Creado: {u}"); st.rerun()
                    except Exception as e: st.error(f"Error: {e}")

        with c2: 
            st.markdown("### 📋 Listado"); 
            try:
                res = supabase.table("users").select("*").execute()
                df = pd.DataFrame(res.data)
                if not df.empty:
                    st.dataframe(df, use_container_width=True)
                    st.divider()
                    to_del = st.selectbox("Borrar usuario:", df['username'])
                    if st.button("Confirmar Borrado"):
                        supabase.table("users").delete().eq("username", to_del).execute(); st.rerun()
            except: pass

    # --- PESTAÑA 3: RESULTADOS ---
    with tab3:
        try:
            res = supabase.table("sape_results").select("*").execute()
            st.dataframe(pd.DataFrame(res.data), use_container_width=True)
        except: pass

    # --- PESTAÑA 4: EMPRESAS Y SECTORES (EL CÓDIGO NUEVO) ---
    with tab4:
        col_create, col_edit = st.columns(2)
        
        # 1. CREAR EMPRESA
        with col_create:
            st.markdown("### ➕ Nueva Empresa")
            with st.form("new_org"):
                oid = st.text_input("ID (sin espacios)").strip()
                oname = st.text_input("Nombre").strip()
                # Multiselector con nombres bonitos
                sectores_seleccionados = st.multiselect("Sectores Habilitados", list(SECTOR_OPTIONS.keys()), default=list(SECTOR_OPTIONS.keys()))
                
                if st.form_submit_button("Crear Empresa"):
                    if oid and oname:
                        try:
                            # Convertimos nombres bonitos -> CÓDIGOS
                            codigos_a_guardar = [SECTOR_OPTIONS[s] for s in sectores_seleccionados]
                            supabase.table("organizations").insert({
                                "id": oid, "name": oname,
                                "active_sectors": json.dumps(codigos_a_guardar)
                            }).execute()
                            st.success(f"Empresa {oname} creada."); st.rerun()
                        except Exception as e: st.error(f"Error: {e}")

        # 2. EDITAR SECTORES
        with col_edit:
            st.markdown("### ✏️ Configurar Sectores")
            if org_data_list:
                # Selector de empresa
                org_map = {o['id']: o['name'] for o in org_data_list}
                sel_id = st.selectbox("Editar Empresa:", list(org_map.keys()), format_func=lambda x: f"{x} ({org_map[x]})")
                
                # Obtener datos actuales
                curr_org = next((x for x in org_data_list if x['id'] == sel_id), None)
                
                if curr_org:
                    # Lógica inteligente para leer la columna 'active_sectors'
                    raw = curr_org.get('active_sectors', '[]')
                    current_codes = []
                    if raw:
                        try:
                            # Intenta JSON normal
                            current_codes = json.loads(raw)
                        except:
                            try:
                                # Intenta formato Python (comillas simples) con ast
                                import ast
                                current_codes = ast.literal_eval(raw)
                            except:
                                current_codes = []
                    
                    # Filtramos solo códigos válidos para evitar errores
                    current_codes = [c for c in current_codes if c in VALID_CODES]
                    
                    # Convertimos CÓDIGOS -> NOMBRES para mostrar en el selector
                    inv_map = {v: k for k, v in SECTOR_OPTIONS.items()}
                    default_names = [inv_map[c] for c in current_codes if c in inv_map]

                    st.info(f"Sectores actuales de **{curr_org['name']}**")
                    
                    with st.form("edit_sectors"):
                        new_names = st.multiselect("Sectores Permitidos:", list(SECTOR_OPTIONS.keys()), default=default_names)
                        
                        if st.form_submit_button("Guardar Cambios"):
                            # Guardamos CÓDIGOS
                            new_codes = [SECTOR_OPTIONS[n] for n in new_names]
                            supabase.table("organizations").update({
                                "active_sectors": json.dumps(new_codes)
                            }).eq("id", sel_id).execute()
                            st.success("✅ Actualizado."); st.rerun()
            else:
                st.info("Crea una empresa primero.")

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