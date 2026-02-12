import streamlit as st
import csv
import os
import random
import string
import io
import math
import textwrap
import json
import ast  # <--- YA ESTÁ AQUÍ ARRIBA, DONDE DEBE ESTAR
from datetime import datetime
import plotly.graph_objects as go
from PIL import Image
import pandas as pd
import numpy as np
import plotly.express as px
from supabase import create_client # <--- TAMBIÉN AQUÍ ARRIBA

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
def load_questions():
    """Carga las preguntas desde SATE_V4.csv con el formato correcto"""
    archivo = 'SATE_V4.csv'
    
    if os.path.exists(archivo):
        try:
            # Tu CSV usa punto y coma (;) como separador
            return pd.read_csv(archivo, sep=';', encoding='utf-8').to_dict('records')
        except Exception as e:
            st.error(f"Error leyendo {archivo}: {e}")
            return []
    else:
        st.error(f"⚠️ No encuentro el archivo {archivo}. Súbelo junto a app.py")
        return []

    # --- NUEVAS FUNCIONES SAPE (Cerebro + Diagnóstico) ---

@st.cache_data
def cargar_cerebro_sape():
    """Carga el diccionario de textos desde el JSON"""
    try:
        # Busca en la carpeta data, o en la raíz si no existe
        paths = ['data/sape_diccionario_riesgos.json', 'sape_diccionario_riesgos.json']
        for p in paths:
            if os.path.exists(p):
                with open(p, 'r', encoding='utf-8') as f:
                    return json.load(f)
        return None
    except Exception as e:
        st.error(f"Error cargando cerebro SAPE: {e}")
        return None

def diagnosticar_usuario_python(octagon, cerebro):
    """
    Recibe las puntuaciones (octagon) y el JSON (cerebro).
    Devuelve el bloque de texto correspondiente (Vector, Descarrilador o Verde).
    """
    if not cerebro: return None

    # Mapeamos tus nombres de variables (octagon) a los nombres del JSON
    # Tu código usa: 'achievement', 'risk_propensity', etc.
    logro = octagon.get('achievement', 0)
    riesgo = octagon.get('risk_propensity', 0)
    innov = octagon.get('innovativeness', 0)
    locus = octagon.get('locus_control', 0)
    autoeficacia = octagon.get('self_efficacy', 0)
    autonomia = octagon.get('autonomy', 0)
    estabilidad = octagon.get('emotional_stability', 0)
    
    vec = cerebro.get('vectors', {})
    der = cerebro.get('derailers', {})
    
    # --- FASE 1: VECTORES (Prioridad Alta) ---
    if logro > 90 and estabilidad < 30 and locus < 30: return vec.get('toxic_leadership')
    if logro < 30 and autonomia > 90 and locus < 30: return vec.get('passive_resistance')
    if innov > 90 and autoeficacia > 90 and logro < 30: return vec.get('false_prophet')
    if logro > 90 and riesgo < 30 and autonomia < 30: return vec.get('bottleneck')
    if innov < 30 and autonomia < 30 and estabilidad > 90: return vec.get('bureaucrat')
    if riesgo > 90 and autoeficacia > 90 and locus < 30: return vec.get('gambler')

    # --- FASE 2: DESCARRILADORES (Prioridad Media) ---
    # Si detectamos uno, devolvemos ese. Si hay varios, el sistema podría devolver una lista,
    # pero para simplificar el informe, devolvemos el más crítico o el primero que encuentre.
    
    if estabilidad < 30: return der.get('volatile')
    if innov < 30: return der.get('skeptical')
    if riesgo < 30: return der.get('cautious')
    if autonomia > 90: return der.get('reserved')
    if logro < 30: return der.get('passive_aggressive')
    if autoeficacia > 90: return der.get('arrogant')
    if riesgo > 90: return der.get('mischievous')
    if estabilidad < 30: return der.get('melodramatic') # Simplificado
    if logro > 90: return der.get('diligent')
    if autonomia < 30: return der.get('dependent')

    # --- FASE 3: PERFIL VERDE (Defecto) ---
    return cerebro.get('balanced_profile')

# --- FUNCIÓN AUXILIAR IMPRESCINDIBLE PARA EL JUEGO ---
def parse_logic(logic_string):
    """
    Traduce la lógica del CSV SATE_V4 (ej: 'risk_propensity 3 | achievement -1')
    y actualiza el Octógono del usuario.
    """
    if not isinstance(logic_string, str) or not logic_string.strip():
        return

    # 1. DICCIONARIO DE TRADUCCIÓN (CSV -> APP)
    # A la izquierda: Cómo se llama en tu Excel
    # A la derecha: Cómo se llama en la variable interna de la App
    MAPEO = {
        "risk_propensity": "risk_propensity",
        "ambiguity_tolerance": "ambiguity_tolerance",
        "innovativeness": "innovativeness",
        "locus_control": "locus_of_control",      # Nota la diferencia sutil
        "emotional_stability": "emotional_stability",
        "achievement": "achievement",
        "leadership": "leadership",
        "adaptability": "adaptability",
        # Mapeos extra por si acaso aparecen en el CSV:
        "self_efficacy": "leadership",  # Asignamos autoeficacia a liderazgo (ejemplo)
        "autonomy": "locus_of_control"  # Asignamos autonomía a control
    }

    # 2. SEPARAR INSTRUCCIONES (Tu Excel usa '|')
    # Ejemplo: "risk_propensity 3 | achievement -1"
    instrucciones = logic_string.split('|')
    
    for instruccion in instrucciones:
        partes = instruccion.strip().split() # Separa por espacio
        
        if len(partes) >= 2:
            key_csv = partes[0].strip() # Ej: risk_propensity
            try:
                val = int(partes[1].strip()) # Ej: 3 o -1
            except:
                continue # Si no es un número, saltamos

            # Buscamos la clave interna
            internal_key = MAPEO.get(key_csv)

            if internal_key:
                # Aseguramos que el octógono existe
                if 'octagon' not in st.session_state:
                    st.session_state.octagon = {k: 50 for k in MAPEO.values()}
                
                # Sumamos el valor (que puede ser negativo)
                st.session_state.octagon[internal_key] += val
                
                # Limitamos entre 0 y 100
                st.session_state.octagon[internal_key] = max(0, min(100, st.session_state.octagon[internal_key]))
            
            # Si es algo especial como IRE o FRICTION
            elif key_csv.upper() == "IRE":
                # Lo guardamos en flags por si acaso, aunque IRE se calcula al final
                if 'flags' not in st.session_state: st.session_state.flags = {}
                st.session_state.flags['IRE_BONUS'] = st.session_state.flags.get('IRE_BONUS', 0) + val

# ==========================================
# 🛠️ BLOQUE DE HERRAMIENTAS (CÁLCULOS Y GRÁFICOS)
# ==========================================

def load_questions():
    """Carga las preguntas desde el archivo CSV"""
    # Lista de posibles nombres de archivo
    files = ['SAPE_DATA.csv', 'sape_data.csv', 'dataset.csv']
    for f in files:
        if os.path.exists(f):
            try:
                return pd.read_csv(f).to_dict('records')
            except: pass
    return [] # Si falla devuelve lista vacía

def calculate_results():
    """Calcula las métricas finales (IRE, Fricción, Octágono)"""
    
    # 1. Recuperar datos del Octágono
    # Aseguramos que existan valores, si no ponemos 50 por defecto
    raw = st.session_state.get('octagon', {})
    keys = ["risk_propensity", "ambiguity_tolerance", "innovativeness", "locus_of_control", "emotional_stability", "achievement", "leadership", "adaptability"]
    octagon_norm = {k: min(100, max(0, raw.get(k, 50))) for k in keys}
    
    # 2. Calcular IRE (Índice de Resiliencia) -> Promedio
    avg = sum(octagon_norm.values()) / len(octagon_norm) if len(octagon_norm) > 0 else 0
    ire = round(avg, 1)
    
    # 3. Calcular Fricción
    friction = st.session_state.get('flags', {}).get('FRICTION', 0)
    friction = min(100, max(0, friction)) # Topes 0-100
    
    # 4. Variables extra (Triggers)
    triggers = []
    fric_reasons = []
    delta = 0
    max_possibles = 100
    
    return ire, avg, friction, triggers, fric_reasons, delta, octagon_norm, max_possibles

def radar_chart():
    """Genera el gráfico de araña con Plotly"""
    data = st.session_state.get('octagon', {})
    
    # Etiquetas bonitas para el gráfico
    labels_map = {
        "risk_propensity": "Riesgo", "ambiguity_tolerance": "Ambigüedad",
        "innovativeness": "Innovación", "locus_of_control": "Control",
        "emotional_stability": "Estabilidad", "achievement": "Logro",
        "leadership": "Liderazgo", "adaptability": "Adaptabilidad"
    }
    
    # Ordenamos los valores
    r_val = [data.get(k, 50) for k in labels_map.keys()]
    theta_val = list(labels_map.values())
    
    # Cerramos el círculo repitiendo el primero
    r_val.append(r_val[0])
    theta_val.append(theta_val[0])
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=r_val, theta=theta_val,
        fill='toself', name='Tu Perfil',
        line_color='#0D248D', opacity=0.8
    ))
    
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=False,
        margin=dict(l=40, r=40, t=40, b=40),
        font=dict(color="black") # Texto negro para fondo blanco
    )
    return fig

def save_result_to_db(student_id, sector, ire, friction, triggers, scores, history, organization):
    """Guarda los resultados en Supabase"""
    try:
        payload = {
            "student_id": student_id,
            "sector": sector,
            "ire": float(ire),
            "friction": int(friction),
            "octagon": str(scores), # Guardamos como texto/JSON
            "history": str(history),
            "organization": organization,
            "created_at": datetime.now().isoformat()
        }
        supabase.table("sape_results").insert(payload).execute()
    except Exception as e:
        print(f"Error guardando DB: {e}")

# Funciones Auxiliares de Diagnóstico
def cargar_cerebro_sape():
    return {} # Placeholder por si no hay archivo JSON

def diagnosticar_usuario_python(octagon, cerebro):
    """Genera un diagnóstico textual simple basado en la puntuación"""
    avg = sum(octagon.values()) / len(octagon) if octagon else 0
    
    if avg >= 75:
        return {"name": "Perfil Sólido", "risk_level": "BAJO", "description": "Tus competencias muestran una gran preparación para el reto."}
    elif avg >= 50:
        return {"name": "Perfil Promedio", "risk_level": "MEDIO", "description": "Tienes bases sólidas, pero vigila las áreas de menor puntuación."}
    else:
        return {"name": "Perfil en Riesgo", "risk_level": "ALTO", "description": "Se detectan vulnerabilidades importantes. Recomendamos formación previa."}

# ==========================================
# 🧩 BLOQUE 1: LÓGICA DEL SIMULADOR (EL JUEGO)
# ==========================================
def run_simulator_logic():
    """Contiene toda la lógica del juego para usuarios normales (STUDENT)"""
    
    # ==========================================================
    # 🎨 1. ESTILO BASE (Para pantallas Blancas: A, B, C y E)
    # ==========================================================
    st.markdown("""
    <style>
    /* Reset por si venimos del modo oscuro */
    .stApp { background-color: white; }
    h1, h2, h3, p, div, span, label { color: black; }
    
    /* Botones Estándar */
    div.stButton > button:not([disabled]) {
        background-color: #0D248D; color: white; border: 1px solid #0D248D;
    }
    div.stButton > button[kind="primary"] {
        background-color: #0D248D; border-color: #0D248D; color: white;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # ------------------------------------------------------------------
    # 1️⃣ PANTALLA A: INSTRUCCIONES
    # ------------------------------------------------------------------
    if 'instructions_seen' not in st.session_state:
        st.session_state.instructions_seen = False

    if not st.session_state.instructions_seen:
        c_spacer1, c_logo, c_spacer2 = st.columns([1, 2, 1]) 
        with c_logo:
            if os.path.exists("logo_original.png"): st.image("logo_original.png", use_container_width=True)
            elif os.path.exists("logo_blanco.png"): 
                st.markdown('<style>img {background-color: #0D248D; padding: 10px; border-radius: 10px;}</style>', unsafe_allow_html=True)
                st.image("logo_blanco.png", use_container_width=True)
            else: st.markdown("<h2 style='text-align: center; color: #0D248D;'>🧬 AUDEO</h1>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("## 📜 Guía simulador S.A.P.E.")
        st.info("**Bienvenido/a.** Estás a punto de asumir el rol de fundador/a de una empresa a lo largo de **40 meses virtuales**.")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### ⚙️ Mecánica")
            st.markdown("* 40 Meses / 40 Decisiones.\n* No hay respuestas correctas, solo consecuencias.\n* Elige lo que **realmente harías**.")
        with c2:
            st.markdown("### ⚠️ Reglas")
            st.markdown("* 🚫 NO uses el botón 'Atrás'.\n* 🚫 NO refresques la página.\n* ⏳ Sin límite de tiempo.")
            
        st.divider()
        if st.button("✅ HE LEÍDO LAS REGLAS. COMENZAR", use_container_width=True, type="primary"):
            st.session_state.instructions_seen = True
            st.rerun()

    # ------------------------------------------------------------------
    # 2️⃣ PANTALLA B: DATOS
    # ------------------------------------------------------------------
    elif not st.session_state.get('data_verified', False):
        c_spacer1, c_logo, c_spacer2 = st.columns([1, 2, 1]) 
        with c_logo:
            if os.path.exists("logo_original.png"): st.image("logo_original.png", use_container_width=True)
            elif os.path.exists("logo_blanco.png"): 
                st.markdown('<style>img {background-color: #0D248D; padding: 10px; border-radius: 10px;}</style>', unsafe_allow_html=True)
                st.image("logo_blanco.png", use_container_width=True)
            else: st.markdown("<h2 style='text-align: center; color: #0D248D;'>🧬 AUDEO</h1>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown("#### 1. Identificación del/a Candidato/a")
        with st.form("user_data_form"):
            col1, col2 = st.columns(2)
            name = col1.text_input("Nombre Completo / Alias", key="final_name_input") 
            age = col2.number_input("Edad", 18, 99, key="final_age_input")
            col3, col4 = st.columns(2)
            gender = col3.selectbox("Género", ["Masculino", "Femenino", "Prefiero no decirlo"], key="final_gender")
            experience = col4.selectbox("Experiencia Previa", ["Primer emprendimiento", "Con éxito previo", "Sin éxito previo"], key="final_exp")
            st.markdown("<br>", unsafe_allow_html=True)
            consent = st.checkbox("He leído y acepto la Política de Privacidad.")
            
            if st.form_submit_button("VALIDAR DATOS Y CONTINUAR"):
                if name and age and consent:
                    if 'user_data' not in st.session_state: st.session_state.user_data = {}
                    st.session_state.user_data.update({"name": name, "age": age, "gender": gender, "experience": experience})
                    st.session_state.data_verified = True
                    st.rerun()
                else: st.error("Por favor, completa los campos obligatorios y acepta la política.")

    # ------------------------------------------------------------------
    # 3️⃣ PANTALLA C: SELECCIÓN DE SECTOR
    # ------------------------------------------------------------------
    elif not st.session_state.started:
        c_spacer1, c_logo, c_spacer2 = st.columns([1, 2, 1]) 
        with c_logo:
            if os.path.exists("logo_original.png"): st.image("logo_original.png", use_container_width=True)
            elif os.path.exists("logo_blanco.png"): 
                st.markdown('<style>img {background-color: #0D248D; padding: 10px; border-radius: 10px;}</style>', unsafe_allow_html=True)
                st.image("logo_blanco.png", use_container_width=True)
            else: st.markdown("<h2 style='text-align: center; color: #0D248D;'>🧬 AUDEO</h1>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown(f"#### 2. Selecciona el Sector del Proyecto:")
        
        def go_sector(sec_name):
            all_q = load_questions()
            SECTOR_MAP = {
                "Startup Tecnológica (Scalable)": "TECH",
                "Pequeña y Mediana Empresa (PYME)": "RETAIL",
                "Autoempleo / Freelance": "FREELANCE",
                "Intraemprendimiento": "INTRA",
                "Psicología Sanitaria": "PSICOLOGÍA_SANITARIA", 
                "Consultoría / Servicios Profesionales": "CONSULTORÍA",
                "Hostelería y Restauración": "HOSTELERÍA",
                "Emprendimiento Social": "SOCIAL",
                "Salud": "SALUD",
                "Psicología no sanitaria": "PSICOLOGÍA_NO_SANITARIA"
            }

            code = SECTOR_MAP.get(sec_name, "TECH")
            qs = [x for x in all_q if x['SECTOR'].strip().upper() == code]
            if not qs: qs = [x for x in all_q if x['SECTOR'].strip().upper() == "TECH"] 
            st.session_state.data = qs
            st.session_state.user_data["sector"] = code
            st.session_state.started = True
            st.rerun()

        org_data = st.session_state.user_data.get('org_data', {})
        try: allowed_sectors = ast.literal_eval(org_data.get('active_sectors', "['ALL']"))
        except: allowed_sectors = ["ALL"]
        def is_locked(tag): return tag not in allowed_sectors if "ALL" not in allowed_sectors else False

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Startup Tecnológica\n(Scalable)", disabled=is_locked("TECH"), use_container_width=True): go_sector("Startup Tecnológica (Scalable)")
            if st.button("Pequeña Empresa\n(PYME)", disabled=is_locked("RETAIL"), use_container_width=True): go_sector("Pequeña y Mediana Empresa (PYME)")
            if st.button("Autoempleo / Freelance", disabled=is_locked("FREELANCE"), use_container_width=True): go_sector("Autoempleo / Freelance")
            if st.button("Intraemprendimiento", disabled=is_locked("INTRA"), use_container_width=True): go_sector("Intraemprendimiento")
            if st.button("Psicología Sanitaria", disabled=is_locked("PSICO_SAN"), use_container_width=True): go_sector("Psicología Sanitaria")
        with c2:
            if st.button("Consultoría / Servicios", disabled=is_locked("CONSULTORIA"), use_container_width=True): go_sector("Consultoría / Servicios Profesionales")
            if st.button("Hostelería y Turismo", disabled=is_locked("TURISMO"), use_container_width=True): go_sector("Hostelería y Restauración")
            if st.button("Emprendimiento Social", disabled=is_locked("SOCIAL"), use_container_width=True): go_sector("Emprendimiento Social")
            if st.button("Salud y Bienestar", disabled=is_locked("SALUD"), use_container_width=True): go_sector("Salud")
            if st.button("Psicología No Sanitaria", disabled=is_locked("PSICO_NO_SAN"), use_container_width=True): go_sector("Psicología no sanitaria")

    # ------------------------------------------------------------------
    # 4️⃣ PANTALLA D: EL JUEGO ( MODO INMERSIVO OSCURO )
    # ------------------------------------------------------------------
    elif not st.session_state.get('finished', False):
        if st.session_state.current_step >= len(st.session_state.data):
            st.session_state.finished = True
            st.rerun()
            
        row = st.session_state.data[st.session_state.current_step]
        st.progress((st.session_state.current_step + 1) / len(st.session_state.data))
        
        # --- 🎨 CSS RADICAL PARA EL MODO JUEGO ---
        st.markdown("""
        <style>
        .stApp { background-color: #050A1F !important; }
        h1, h2, h3, h4, h5, h6, p, div, span, label, li { color: #FFFFFF !important; }
        .narrative-text {
            font-size: 1.3rem; line-height: 1.6; padding: 15px;
            border-left: 4px solid #0D248D; background-color: rgba(255, 255, 255, 0.05);
            border-radius: 8px; margin-bottom: 20px;
        }
        div.stButton > button {
            background-color: #0D248D !important; color: white !important;
            border: 2px solid #0D248D !important; border-radius: 12px !important;
            padding: 20px !important; height: auto !important; min_height: 90px !important;
            font-size: 1.1rem !important; transition: all 0.3s ease !important;
        }
        div.stButton > button:hover {
            transform: scale(1.05) !important; background-color: #1530A0 !important;
            box-shadow: 0 0 20px rgba(21, 48, 160, 0.6) !important; border-color: white !important; z-index: 100;
        }
        </style>
        """, unsafe_allow_html=True)
        
        c_spacer1, c_logo, c_spacer2 = st.columns([1, 2, 1]) 
        with c_logo:
            if os.path.exists("logo_blanco.png"): st.image("logo_blanco.png", use_container_width=True)
            else: st.markdown("<h2 style='text-align: center; color: white;'>🧬 AUDEO</h1>", unsafe_allow_html=True)
        
        st.markdown(f"### {row.get('TITULO', 'Desafío')}")
        
        c_text, c_opt = st.columns([1.5, 1])
        with c_text:
            st.markdown(f'<div class="narrative-text">{row.get("NARRATIVA","")}</div>', unsafe_allow_html=True)
        
        with c_opt:
            st.markdown("#### Tu decisión:")
            options = []
            if pd.notna(row.get('OPCION_A_TXT')): options.append({'txt': row['OPCION_A_TXT'], 'logic': row.get('OPCION_A_LOGIC'), 'id': 'A'})
            if pd.notna(row.get('OPCION_B_TXT')): options.append({'txt': row['OPCION_B_TXT'], 'logic': row.get('OPCION_B_LOGIC'), 'id': 'B'})
            if pd.notna(row.get('OPCION_C_TXT')): options.append({'txt': row['OPCION_C_TXT'], 'logic': row.get('OPCION_C_LOGIC'), 'id': 'C'})
            if pd.notna(row.get('OPCION_D_TXT')): options.append({'txt': row['OPCION_D_TXT'], 'logic': row.get('OPCION_D_LOGIC'), 'id': 'D'})
            
            random.shuffle(options)
            step = st.session_state.current_step
            for opt in options:
                if st.button(opt['txt'], key=f"btn_{step}_{opt['id']}", use_container_width=True):
                    parse_logic(opt['logic'])
                    if 'history' not in st.session_state: st.session_state.history = []
                    st.session_state.history.append({"mes": row.get('MES'), "opcion": opt['id'], "texto": opt['txt']})
                    st.session_state.current_step += 1
                    st.rerun()

    # ------------------------------------------------------------------
    # 5️⃣ PANTALLA E: RESULTADOS (CON SEMÁFORO VISUAL)
    # ------------------------------------------------------------------
    else:
        # Volver al modo blanco limpio
        st.markdown("""
        <style>
        .stApp { background-color: white !important; }
        h1, h2, h3, h4, p, li, span, div { color: black !important; }
        </style>
        """, unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns([1,1,1])
        with c2:
            if os.path.exists("logo_original.png"): st.image("logo_original.png", use_container_width=True)

        # CÁLCULO DE RESULTADOS
        ire, avg, friction, triggers, fric_reasons, delta, octagon_norm, max_possibles = calculate_results()
        
        cerebro = cargar_cerebro_sape()
        diagnostico = diagnosticar_usuario_python(octagon_norm, cerebro)

        # CUADRO DE DIAGNÓSTICO
        if diagnostico:
            titulo = diagnostico.get('name', 'Diagnóstico')
            nivel = diagnostico.get('risk_level', 'ALERTA')
            desc = diagnostico.get('description', '')
            color = "#E74C3C" if "CRÍTICO" in nivel else "#F1C40F" if "ALTO" in nivel else "#2ECC71"
            st.markdown(f"""<div style="padding: 20px; border-left: 6px solid {color}; background-color: #f8f9fa; color: #333; margin-bottom: 25px;"><h3 style="color: {color}; margin:0;">{titulo}</h3><p>{desc}</p></div>""", unsafe_allow_html=True)

        st.markdown(f"## 📊 Informe Ejecutivo S.A.P.E. | {st.session_state.user_data.get('name','Usuario')}")
        
        # MÉTRICAS PRINCIPALES
        k1, k2, k3 = st.columns(3)
        k1.metric("Índice IRE", f"{ire}/100")
        k2.metric("Potencial", f"{avg}/100")
        k3.metric("Fricción", f"{friction}%", delta_color="inverse")
        
        st.divider()

        # COLUMNA IZQUIERDA: GRÁFICO DE ARAÑA
        col_chart, col_bars = st.columns([1, 1.2])
        
        with col_chart:
            st.plotly_chart(radar_chart(), use_container_width=True)

        # COLUMNA DERECHA: BARRAS CON SEMÁFORO (DÉFICIT - ALERTA - ÓPTIMO - EXCESO)
        with col_bars:
            st.markdown("### Detalle de Competencias")
            
            # Mapeo de nombres para mostrar
            labels_map = {
                "risk_propensity": "Propensión al Riesgo", "ambiguity_tolerance": "Tolerancia Ambigüedad",
                "innovativeness": "Innovación", "locus_of_control": "Locus de Control",
                "emotional_stability": "Estabilidad Emocional", "achievement": "Orientación al Logro",
                "leadership": "Liderazgo", "adaptability": "Adaptabilidad"
            }

            for key, label_text in labels_map.items():
                val = octagon_norm.get(key, 0)
                
                # --- LÓGICA DE SEMÁFORO (LA CLAVE DEL DISEÑO SÓLIDO) ---
                if val < 25:
                    bar_color = "#E74C3C" # ROJO (Déficit Crítico)
                elif val < 60:
                    bar_color = "#F1C40F" # AMARILLO (Alerta / En desarrollo)
                elif val <= 90:
                    bar_color = "#2ECC71" # VERDE (Óptimo)
                else:
                    bar_color = "#E74C3C" # ROJO (Exceso / Peligro) - ¡IMPORTANTE!

                # Renderizamos la barra con HTML/CSS puro
                st.markdown(f"""
                <div style="margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                        <span style="font-weight: 600; font-size: 0.9rem;">{label_text}</span>
                        <span style="font-weight: 700; color: {bar_color};">{int(val)}/100</span>
                    </div>
                    <div style="background-color: #E2E8F0; border-radius: 10px; height: 12px; width: 100%;">
                        <div style="background-color: {bar_color}; width: {val}%; height: 100%; border-radius: 10px; transition: width 1s ease-in-out;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        st.divider()

        # GUARDADO
        if 'data_saved' not in st.session_state:
            try:
                org_name = st.session_state.user_data.get('org_data', {}).get('name', 'GENERICO')
                save_result_to_db(
                    student_id=st.session_state.user_data.get('username', 'ANON'), 
                    sector=st.session_state.user_data.get('sector', 'GEN'), 
                    ire=ire, friction=friction, triggers=triggers, 
                    scores=octagon_norm,   
                    history=st.session_state.history,  
                    organization=org_name
                )
                st.session_state.data_saved = True
                st.success(f"✅ Resultados registrados correctamente en {org_name}.")
            except Exception as e:
                st.error(f"Error guardando resultados: {e}")
        else:
             st.success("✅ Resultados ya registrados.")

        st.info("Has completado la simulación. Puedes cerrar esta ventana.")

# ==========================================
# 👑 PANEL ADMIN (VERSIÓN 4.0: EL INSPECTOR DE EMPRESAS)
# ==========================================
def render_admin_dashboard():
    st.title("👑 Panel de Administración")
    
    # 1. KPIs Globales
    try:
        count_users = supabase.table("users").select("*", count="exact").execute().count
        count_results = supabase.table("sape_results").select("*", count="exact").execute().count
        count_orgs = supabase.table("organizations").select("*", count="exact").execute().count
        
        # Obtenemos IDs para los selectores
        res_orgs = supabase.table("organizations").select("id", "name").execute()
        valid_ids = [o['id'] for o in res_orgs.data]
        org_names = {o['id']: o['name'] for o in res_orgs.data} # Diccionario ID -> Nombre
    except: 
        count_users = count_results = count_orgs = 0
        valid_ids = []
        org_names = {}

    k1, k2, k3 = st.columns(3)
    k1.metric("👥 Usuarios Totales", count_users)
    k2.metric("📊 Tests Realizados", count_results)
    k3.metric("🏢 Empresas", count_orgs)
    
    # AHORA 4 PESTAÑAS
    tab1, tab2, tab3, tab4 = st.tabs(["🔎 INSPECTOR", "👥 USUARIOS", "📈 RESULTADOS", "🏢 EMPRESAS"])
    
    # --- PESTAÑA 1: INSPECTOR DE EMPRESA (LO NUEVO) ---
    with tab1:
        st.markdown("### 🕵️ Visión Detallada por Empresa")
        st.caption("Selecciona una organización para ver el estado de todos sus alumnos.")
        
        if valid_ids:
            col_sel, col_kpis = st.columns([1, 2])
            with col_sel:
                selected_org = st.selectbox("Selecciona Organización:", valid_ids, format_func=lambda x: f"{x} ({org_names.get(x, '')})")
            
            # LÓGICA DE CRUCE DE DATOS (JOIN)
            if selected_org:
                try:
                    # 1. Bajamos TODOS los usuarios de esa empresa
                    users_response = supabase.table("users").select("*").eq("org_id", selected_org).execute()
                    df_users = pd.DataFrame(users_response.data)
                    
                    # 2. Bajamos TODOS los resultados de esa empresa
                    results_response = supabase.table("sape_results").select("*").eq("organization", selected_org).execute()
                    df_results = pd.DataFrame(results_response.data)
                    
                    if not df_users.empty:
                        # 3. CRUZAMOS (Merge Left) -> Queremos todos los usuarios, tengan o no resultado
                        # Asumimos que 'username' en users coincide con 'student_id' en results
                        if not df_results.empty:
                            # Preparamos resultados para el cruce (nos quedamos con lo importante)
                            df_results_clean = df_results[['student_id', 'ire', 'friction', 'created_at']].copy()
                            df_results_clean.rename(columns={'created_at': 'fecha_test', 'student_id': 'student_join_id'}, inplace=True)
                            
                            # Hacemos el MERGE
                            df_final = pd.merge(
                                df_users, 
                                df_results_clean, 
                                left_on='username', 
                                right_on='student_join_id', 
                                how='left'
                            )
                        else:
                            # Si nadie ha hecho el test, el final es igual al de usuarios + columnas vacías
                            df_final = df_users.copy()
                            df_final['ire'] = None
                            df_final['friction'] = None
                            df_final['fecha_test'] = None

                        # 4. LIMPIEZA Y FORMATO VISUAL
                        # Calculamos estado
                        df_final['Estado'] = df_final['fecha_test'].apply(lambda x: "✅ Completado" if pd.notnull(x) else "❌ Pendiente")
                        
                        # KPIs de la Empresa Seleccionada
                        total_org = len(df_final)
                        hechos = len(df_final[df_final['Estado'] == "✅ Completado"])
                        pendientes = total_org - hechos
                        avance = (hechos / total_org) * 100 if total_org > 0 else 0
                        
                        with col_kpis:
                            sk1, sk2, sk3 = st.columns(3)
                            sk1.metric("Alumnos", total_org)
                            sk2.metric("Completados", f"{hechos} ({int(avance)}%)")
                            sk3.metric("Pendientes", pendientes)
                        
                        st.divider()
                        
                        # 5. TABLA DE DETALLE
                        # Seleccionamos y renombramos columnas para que sea bonito
                        cols_visual = ['username', 'password', 'role', 'Estado', 'ire', 'friction', 'fecha_test']
                        df_show = df_final[cols_visual].copy()
                        df_show.columns = ['Usuario', 'Password', 'Rol', 'Estado', 'Nota IRE', 'Fricción', 'Fecha Realización']
                        
                        # Formato condicional (Truco visual)
                        st.dataframe(
                            df_show,
                            column_config={
                                "Estado": st.column_config.TextColumn("Estado", width="medium"),
                                "Fecha Realización": st.column_config.DatetimeColumn("Fecha", format="D MMM YYYY, HH:mm"),
                                "Nota IRE": st.column_config.ProgressColumn("IRE", format="%.1f", min_value=0, max_value=100),
                            },
                            use_container_width=True
                        )
                        
                        # Botón descarga
                        csv = df_show.to_csv(index=False).encode('utf-8')
                        st.download_button(f"📥 Descargar Informe {selected_org}", csv, f"informe_{selected_org}.csv", "text/csv")
                        
                    else:
                        st.warning(f"La empresa '{selected_org}' existe pero no tiene usuarios asignados todavía.")
                        
                except Exception as e:
                    st.error(f"Error cruzando datos: {e}")
        else:
            st.info("No hay empresas registradas.")

# --- PESTAÑA 2: GESTIÓN DE USUARIOS (AHORA CON TABLA Y BORRADO) ---
    with tab2:
        c_form, c_view = st.columns([1, 1.5])
        
        # IZQUIERDA: FORMULARIOS DE ALTA
        with c_form:
            st.markdown("### ➕ Alta de Usuarios")
            type_add = st.radio("Método:", ["Uno a Uno", "Carga CSV"], horizontal=True)
            
            if type_add == "Uno a Uno":
                with st.form("new_user_admin"):
                    new_user = st.text_input("Username / Email")
                    new_pass = st.text_input("Password", value="1234")
                    new_role = st.selectbox("Rol", ["STUDENT", "MANAGER", "ADMIN"])
                    
                    # Selector inteligente de empresa
                    if valid_ids: new_org_id = st.selectbox("Org ID", valid_ids)
                    else: new_org_id = st.text_input("Org ID")
                    
                    if st.form_submit_button("Crear Usuario"):
                        try:
                            supabase.table("users").insert({
                                "username": new_user, "password": new_pass, 
                                "role": new_role, "org_id": new_org_id
                            }).execute()
                            st.success(f"Usuario {new_user} creado.")
                            st.rerun()
                        except Exception as e: st.error(f"Error: {e}")

            else: # CARGA CSV
                st.info("CSV: `username`, `password`, `role`, `org_id`")
                uploaded = st.file_uploader("Sube tu archivo", type=["csv"])
                if uploaded:
                    if st.button("Procesar Archivo"):
                        try:
                            uploaded.seek(0)
                            try: df = pd.read_csv(uploaded, sep=';')
                            except: 
                                uploaded.seek(0)
                                df = pd.read_csv(uploaded, sep=',')
                            
                            # Limpieza anti-fallos
                            df.columns = df.columns.str.replace('"','').str.strip()
                            for c in df.columns: 
                                if df[c].dtype == object: df[c] = df[c].astype(str).str.replace('"','').str.strip()
                                
                            count = 0
                            progress = st.progress(0)
                            for i, r in df.iterrows():
                                try:
                                    supabase.table("users").insert({
                                        "username": r['username'], "password": r['password'],
                                        "role": r['role'].upper(), "org_id": r['org_id']
                                    }).execute()
                                    count += 1
                                except: pass
                                progress.progress((i+1)/len(df))
                            st.success(f"✅ {count} usuarios importados.")
                            st.rerun()
                        except Exception as e: st.error(f"Error en CSV: {e}")

        # DERECHA: LISTADO Y GESTIÓN (¡LO QUE FALTABA!)
        with c_view:
            st.markdown("### 📋 Usuarios en Base de Datos")
            
            # Filtros para encontrar gente rápido
            f_role = st.selectbox("Filtrar por Rol:", ["TODOS", "STUDENT", "MANAGER", "ADMIN"])
            
            try:
                # Consulta base
                query = supabase.table("users").select("*").order("created_at", desc=True)
                if f_role != "TODOS": query = query.eq("role", f_role)
                
                res = query.execute()
                df_users = pd.DataFrame(res.data)
                
                if not df_users.empty:
                    # Mostramos tabla limpia
                    st.dataframe(
                        df_users[['username', 'role', 'org_id', 'password']], 
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    st.divider()
                    
                    # ZONA DE BORRADO
                    st.markdown("#### 🗑️ Eliminar Usuario")
                    col_del_1, col_del_2 = st.columns([2, 1])
                    user_to_del = col_del_1.selectbox("Selecciona usuario a borrar:", df_users['username'])
                    
                    if col_del_2.button("Borrar Definitivamente"):
                        try:
                            supabase.table("users").delete().eq("username", user_to_del).execute()
                            st.warning(f"Usuario {user_to_del} eliminado.")
                            st.rerun()
                        except Exception as e: st.error(f"Error borrando: {e}")
                else:
                    st.info("No se encontraron usuarios.")
            except Exception as e: st.error("Error cargando lista.")
    # --- PESTAÑA 3: RESULTADOS GLOBALES ---
    with tab3:
        st.markdown("### 🌍 Resultados Globales")
        try:
            all_res = supabase.table("sape_results").select("*").execute()
            df = pd.DataFrame(all_res.data)
            if not df.empty:
                st.dataframe(df, use_container_width=True)
                st.download_button("📥 CSV Global", df.to_csv(index=False).encode('utf-8'), "global.csv", "text/csv")
            else: st.info("Sin datos.")
        except: pass

    # --- PESTAÑA 4: EMPRESAS ---
    with tab4:
        st.markdown("### 🏢 Gestión de Empresas")
        c1, c2 = st.columns([1, 1.5])
        with c1:
            with st.form("new_org"):
                oid = st.text_input("ID (sin espacios)").strip()
                oname = st.text_input("Nombre").strip()
                opass = st.text_input("Password", type="password").strip()
                sects = st.multiselect("Sectores", ["TECH", "RETAIL", "FREELANCE", "INTRA", "PSICOLOGÍA_SANITARIA", "CONSULTORÍA", "HOSTELERÍA", "SOCIAL", "SALUD", "PSICOLOGÍA_NO_SANITARIA"], default=["TECH"])
                if st.form_submit_button("Guardar"):
                    try:
                        supabase.table("organizations").insert({"id": oid, "name": oname, "password": opass, "active_sectors": str(sects)}).execute()
                        st.success("Creada.")
                        st.rerun()
                    except Exception as e: st.error(f"Error: {e}")
        with c2:
            try:
                res = supabase.table("organizations").select("*").execute()
                df = pd.DataFrame(res.data)
                if not df.empty:
                    st.dataframe(df[['id', 'name']], use_container_width=True)
                    to_del = st.selectbox("Borrar empresa:", df['id'])
                    if st.button("🗑️ Eliminar Empresa"):
                        try:
                            supabase.table("organizations").delete().eq("id", to_del).execute()
                            st.rerun()
                        except: st.error("No se puede borrar si tiene usuarios.")
            except: pass

# ==========================================
# 🏢 PANEL CLIENTE (MANAGER) - FINAL
# ==========================================
def render_manager_dashboard():
    # 1. Recuperar datos
    user = st.session_state.user_data
    org_id = user.get('org_id') # Aquí cogemos el ID de la empresa
    
    # 2. Cabecera
    c1, c2 = st.columns([1, 6])
    with c1:
        if os.path.exists("logo_original.png"): st.image("logo_original.png", use_container_width=True)
    with c2:
        # TÍTULO DINÁMICO: Si hay empresa, pone su nombre. Si no, avisa.
        if org_id and org_id != "None":
            titulo = org_id.upper()
        else:
            titulo = "⚠️ SIN EMPRESA ASIGNADA"
            
        st.markdown(f"<h1 style='color: #0D248D;'>Panel de Control: {titulo}</h1>", unsafe_allow_html=True)
        st.caption(f"👋 Hola, {user.get('username')}.")
    st.divider()

    # 3. BLOQUEO DE SEGURIDAD
    # Si el usuario no tiene empresa, paramos aquí para no dar errores feos
    if not org_id or org_id == "None":
        st.error("❌ ERROR DE USUARIO: Este manager no tiene organización asignada.")
        st.info("💡 SOLUCIÓN: Entra como ADMIN, borra este usuario y créalo de nuevo seleccionando una empresa válida en el campo 'Org ID'.")
        return # STOP

    # 4. DASHBOARD (Solo carga si pasamos el bloqueo anterior)
    try:
        # A. Cargar datos
        users_resp = supabase.table("users").select("*").eq("org_id", org_id).eq("role", "STUDENT").execute()
        df_users = pd.DataFrame(users_resp.data)
        
        results_resp = supabase.table("sape_results").select("*").eq("organization", org_id).execute()
        df_results = pd.DataFrame(results_resp.data)
        
        # B. Comprobar si hay alumnos
        if not df_users.empty:
            # Cruce de datos
            if not df_results.empty:
                res_clean = df_results[['student_id', 'ire', 'friction', 'octagon', 'created_at']].copy()
                df_final = pd.merge(df_users, res_clean, left_on='username', right_on='student_id', how='left')
            else:
                df_final = df_users.copy()
                for c in ['ire', 'friction', 'octagon', 'created_at']: df_final[c] = None
                
            df_final['Estado'] = df_final['created_at'].apply(lambda x: "✅ Completado" if pd.notnull(x) else "❌ Pendiente")
            df_final['Fecha'] = pd.to_datetime(df_final['created_at']).dt.strftime('%d/%m/%Y %H:%M')
            
            # KPIs
            total = len(df_final)
            completed = len(df_final[df_final['Estado'] == "✅ Completado"])
            avg_ire = df_final['ire'].mean() if completed > 0 else 0
            
            k1, k2, k3 = st.columns(3)
            k1.metric("Total Alumnos", total)
            k2.metric("Completados", f"{completed} ({int(completed/total*100) if total else 0}%)")
            k3.metric("Nota Media (IRE)", f"{avg_ire:.1f}")
            
            # Pestañas
            tab1, tab2, tab3 = st.tabs(["🚦 SEGUIMIENTO", "📊 GRUPO", "⭐ TALENTO"])
            
            with tab1: # TABLA
                filtro = st.radio("Ver:", ["Todos", "Pendientes", "Completados"], horizontal=True)
                df_view = df_final
                if filtro == "Pendientes": df_view = df_final[df_final['Estado'] == "❌ Pendiente"]
                elif filtro == "Completados": df_view = df_final[df_final['Estado'] == "✅ Completado"]
                st.dataframe(df_view[['username', 'Estado', 'ire', 'friction', 'Fecha']], use_container_width=True)

            with tab2: # RADAR
                if completed > 0:
                    try:
                        valid_octs = df_final['octagon'].dropna().apply(lambda x: eval(x) if isinstance(x, str) else x).tolist()
                        if valid_octs:
                            avg_oct = {}
                            keys = ["risk_propensity", "ambiguity_tolerance", "innovativeness", "locus_of_control", "emotional_stability", "achievement", "leadership", "adaptability"]
                            for k in keys: avg_oct[k] = sum([o.get(k,0) for o in valid_octs])/len(valid_octs)
                            st.plotly_chart(radar_chart(avg_oct, "Media del Grupo"), use_container_width=True)
                    except: pass
                else: st.info("Faltan datos para la gráfica.")

            with tab3: # SCATTER
                if completed > 0:
                    fig = px.scatter(df_final[df_final['Estado']=="✅ Completado"], x="ire", y="friction", color="ire", hover_data=["username"], text="username", color_continuous_scale="RdYlGn", title="Mapa de Talento")
                    fig.add_hrect(y0=80, y1=100, line_width=0, fillcolor="red", opacity=0.1)
                    st.plotly_chart(fig, use_container_width=True)
                else: st.info("Faltan datos para el mapa.")

        else: 
            st.warning(f"La organización **{org_id}** no tiene alumnos registrados todavía.")
            
    except Exception as e: st.error(f"Error cargando dashboard: {e}")

# ==========================================
# 🚀 BLOQUE 3: EL ROUTER PRINCIPAL (MAIN)
# ==========================================
def main():
    # 1. INYECTAR ESTILO LO PRIMERO (Modo Oscuro + Ocultar Barras)
    inject_custom_css() 

    # Inicialización Segura
    if 'octagon' not in st.session_state:
        st.session_state.octagon = {k: 50 for k in ["risk_propensity", "ambiguity_tolerance", "innovativeness", "locus_of_control", "emotional_stability", "achievement", "leadership", "adaptability"]}
    if 'flags' not in st.session_state: st.session_state.flags = {}
    if 'history' not in st.session_state: st.session_state.history = []
    if 'current_step' not in st.session_state: st.session_state.current_step = 0
    if 'started' not in st.session_state: st.session_state.started = False
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False

    # A. SI NO ESTÁ LOGUEADO -> PANTALLA DE LOGIN
    # A. SI NO ESTÁ LOGUEADO -> PANTALLA DE LOGIN
    if not st.session_state.logged_in:
        
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            
            # --- LÓGICA DEL LOGO CORREGIDA ---
            # Prioridad 1: Logo Original (Color #0D248D y Negro) -> Ideal para fondo blanco
            if os.path.exists("logo_original.png"): 
                st.image("logo_original.png", use_container_width=True)
            # Prioridad 2: Logo Blanco (Por si acaso falta el otro)
            elif os.path.exists("logo_blanco.png"): 
                # Le ponemos un fondo oscuro temporal con CSS solo a la imagen si toca usar el blanco
                st.markdown('<style>img {background-color: #0D248D; padding: 10px; border-radius: 10px;}</style>', unsafe_allow_html=True)
                st.image("logo_blanco.png", use_container_width=True)
            # Prioridad 3: Texto (Si no hay imágenes) -> Usamos tu color corporativo
            else: 
                st.markdown("<h1 style='text-align: center; color: #0D248D !important;'>🧬 AUDEO</h1>", unsafe_allow_html=True)
            
            # Subtítulo en Gris Oscuro (para que se lea en fondo blanco)
            st.markdown("<h3 style='text-align: center; color: #333333 !important;'>Sistema de Análisis de la Personalidad Emprendedora</h3>", unsafe_allow_html=True)
            
            with st.form("login_form_supabase"):
                user_in = st.text_input("USUARIO")
                pass_in = st.text_input("CONTRASEÑA", type="password")
                
                submitted = st.form_submit_button("ENTRAR 🚀", use_container_width=True)
                
                if submitted:
                    user_data = login_supabase(user_in, pass_in)
                    if user_data:
                        st.session_state.logged_in = True
                        st.session_state.user_data = user_data
                        st.rerun()
                    else:
                        st.error("❌ Usuario o contraseña incorrectos")

    # B. SI YA ESTÁ LOGUEADO -> DISTRIBUIR SEGÚN ROL
    else:
        with st.sidebar:
            st.write(f"👤 **{st.session_state.user_data.get('username')}**")
            st.caption(f"Rol: {st.session_state.user_data.get('role')}")
            if st.button("Cerrar Sesión"):
                st.session_state.logged_in = False
                st.session_state.user_data = {}
                st.rerun()
        
        # 1. ES EL JEFE (TÚ)
        if st.session_state.user_data.get('role') == 'ADMIN':
            render_admin_dashboard()
            
       # 2. ES UN MANAGER (CLIENTE)
        elif st.session_state.user_data.get('role') == 'MANAGER':
            
            # LOGO CORPORATIVO TAMBIÉN AQUÍ
            c1, c2 = st.columns([1, 6])
            with c1:
                if os.path.exists("logo_original.png"): st.image("logo_original.png")
            with c2:
                org_name = st.session_state.user_data.get('organization', 'Tu Organización')
                st.markdown(f"<h1 style='color: #0D248D;'>Panel de Control: {org_name}</h1>", unsafe_allow_html=True)
            
            st.divider()

            # TRAER SOLO DATOS DE SU EMPRESA
            try:
                my_org = st.session_state.user_data.get('organization')
                response = supabase.table("sape_results").select("*").eq("organization", my_org).execute()
                df = pd.DataFrame(response.data)
                
                if not df.empty:
                    # Métricas Resumen
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Participantes", len(df))
                    m2.metric("Media IRE", f"{df['ire'].mean():.1f}")
                    m3.metric("Fricción Media", f"{df['friction'].mean():.1f}%")
                    
                    st.markdown("### 📋 Detalle de Evaluados")
                    st.dataframe(
                        df[['student_id', 'sector', 'ire', 'friction', 'created_at']], 
                        use_container_width=True
                    )
                    
                    # Gráfico simple de distribución
                    if 'ire' in df.columns:
                        fig = px.histogram(df, x="ire", nbins=10, title="Distribución de Puntuaciones IRE", color_discrete_sequence=['#0D248D'])
                        st.plotly_chart(fig, use_container_width=True)

                else:
                    st.info(f"👋 Hola. Aún no hay resultados registrados para **{my_org}**.")
                    
            except Exception as e:
                st.error(f"Error conectando con base de datos: {e}")
            
        # 3. ES UN ALUMNO (JUGADOR)
        else:
            run_simulator_logic()

# EJECUTAR APLICACIÓN
if __name__ == "__main__":
    main()