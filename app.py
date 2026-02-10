import streamlit as st
import csv
import os
import random
import string
import io
import math
import textwrap
import json
from datetime import datetime
import plotly.graph_objects as go
from PIL import Image

# --- LIBRERÍAS DE DATOS Y GRÁFICOS ---
import pandas as pd
import numpy as np
import plotly.express as px

# --- BLOQUE 1: CONEXIÓN SUPABASE (AÑADIR AQUÍ) ---
from supabase import create_client

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
    # CAMBIO: Apuntamos al archivo SATE_v3 (Escala Corta)
    filename = 'SATE_v3.csv'  
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

# ==========================================
# 🧩 BLOQUE 1: LÓGICA DEL SIMULADOR (EL JUEGO)
# ==========================================
def run_simulator_logic():
    """Contiene toda la lógica del juego para usuarios normales (STUDENT)"""
    # Inyectamos estilos
    st.markdown("""<style>
        .stApp { background-color: #0E1117; }
        div.stButton > button { width: 100%; border-radius: 8px; font-weight: bold; border: 1px solid #4A5568; }
        div.stButton > button:hover { border-color: #3182CE; color: #3182CE; }
    </style>""", unsafe_allow_html=True)
    
    # --- PANTALLA A: INSTRUCCIONES (ONBOARDING) ---
    if 'instructions_seen' not in st.session_state:
        st.session_state.instructions_seen = False

    if not st.session_state.instructions_seen:
        st.markdown("## 📜 Guía simulador S.A.P.E.")
        st.warning("**Bienvenido/a.** Estás a punto de asumir el rol de fundador/a de una empresa a lo largo de **40 meses virtuales**.")
        
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

    # --- PANTALLA B: DATOS DEL CANDIDATO ---
    elif not st.session_state.get('data_verified', False):
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
                    st.session_state.user_data.update({
                        "name": name, 
                        "age": age, 
                        "gender": gender, 
                        "experience": experience
                    })
                    st.session_state.data_verified = True
                    st.rerun()
                else:
                    st.error("Por favor, completa los campos obligatorios y acepta la política.")

    # --- PANTALLA C: SELECCIÓN DE SECTOR (CON PERMISOS) ---
    elif not st.session_state.started:
        st.markdown(f"#### 2. Selecciona el Sector del Proyecto:")
        
        # Función para cargar preguntas
        def go_sector(sec_name):
            all_q = load_questions()
            # Mapeo de nombres largos a cortos
            SECTOR_MAP = {
                "Startup Tecnológica (Scalable)": "TECH",
                "Pequeña y Mediana Empresa (PYME)": "RETAIL",
                "Autoempleo / Freelance": "CONSULTORIA",
                "Intraemprendimiento": "CONSULTORIA",
                "Psicología Sanitaria": "SALUD",
                "Consultoría / Servicios Profesionales": "CONSULTORIA",
                "Hostelería y Restauración": "TURISMO",
                "Emprendimiento Social": "SOCIAL",
                "Salud": "SALUD",
                "Psicología no sanitaria": "SALUD"
            }
            code = SECTOR_MAP.get(sec_name, "TECH")
            qs = [x for x in all_q if x['SECTOR'].strip().upper() == code]
            if not qs: qs = [x for x in all_q if x['SECTOR'].strip().upper() == "TECH"] 
            st.session_state.data = qs
            st.session_state.user_data["sector"] = code
            st.session_state.started = True
            st.rerun()

        # SISTEMA DE BLOQUEO DE BOTONES
        org_data = st.session_state.user_data.get('org_data', {})
        try:
            import ast
            allowed_sectors = ast.literal_eval(org_data.get('active_sectors', "['ALL']"))
        except:
            allowed_sectors = ["ALL"]

        def is_locked(tag):
            if "ALL" in allowed_sectors: return False
            return tag not in allowed_sectors

        # --- BLOQUE DE BOTONES DE ALTA PRECISIÓN ---
        c1, c2 = st.columns(2)
        with c1:
            # 1. TECH
            if st.button("Startup Tecnológica\n(Scalable)", disabled=is_locked("TECH"), use_container_width=True): 
                go_sector("Startup Tecnológica (Scalable)")
            
            # 2. RETAIL
            if st.button("Pequeña Empresa\n(PYME)", disabled=is_locked("RETAIL"), use_container_width=True): 
                go_sector("Pequeña y Mediana Empresa (PYME)")
            
            # 3. FREELANCE
            if st.button("Autoempleo / Freelance", disabled=is_locked("FREELANCE"), use_container_width=True): 
                go_sector("Autoempleo / Freelance")
            
            # 4. INTRA
            if st.button("Intraemprendimiento", disabled=is_locked("INTRA"), use_container_width=True): 
                go_sector("Intraemprendimiento")
            
            # 5. PSICO SANITARIA (Solo esta)
            if st.button("Psicología Sanitaria", disabled=is_locked("PSICO_SAN"), use_container_width=True): 
                go_sector("Psicología Sanitaria")

        with c2:
            # 6. CONSULTORIA
            if st.button("Consultoría / Servicios", disabled=is_locked("CONSULTORIA"), use_container_width=True): 
                go_sector("Consultoría / Servicios Profesionales")
            
            # 7. TURISMO
            if st.button("Hostelería y Turismo", disabled=is_locked("TURISMO"), use_container_width=True): 
                go_sector("Hostelería y Restauración")
            
            # 8. SOCIAL
            if st.button("Emprendimiento Social", disabled=is_locked("SOCIAL"), use_container_width=True): 
                go_sector("Emprendimiento Social")
            
            # 9. SALUD (Solo Salud y Bienestar)
            if st.button("Salud y Bienestar", disabled=is_locked("SALUD"), use_container_width=True): 
                go_sector("Salud")
            
            # 10. PSICO NO SANITARIA (Solo esta)
            if st.button("Psicología No Sanitaria", disabled=is_locked("PSICO_NO_SAN"), use_container_width=True): 
                go_sector("Psicología no sanitaria")

    # --- PANTALLA D: EL JUEGO (PREGUNTAS) ---
    elif not st.session_state.get('finished', False):
        if st.session_state.current_step >= len(st.session_state.data):
            st.session_state.finished = True
            st.rerun()
            
        row = st.session_state.data[st.session_state.current_step]
        st.progress((st.session_state.current_step + 1) / len(st.session_state.data))
        
        st.markdown(f"### {row.get('TITULO', 'Desafío')}")
        
        c_text, c_opt = st.columns([1.5, 1])
        with c_text:
            st.markdown(f'<div class="diag-text" style="font-size:1.2rem;"><p>{row.get("NARRATIVA","")}</p></div>', unsafe_allow_html=True)
        
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

    # --- PANTALLA E: RESULTADOS FINALES ---
    else:
        ire, avg, friction, triggers, fric_reasons, delta, octagon_norm, max_possibles = calculate_results()
        
        cerebro = cargar_cerebro_sape()
        diagnostico = diagnosticar_usuario_python(octagon_norm, cerebro)

        if diagnostico:
            titulo = diagnostico.get('name', 'Diagnóstico')
            nivel = diagnostico.get('risk_level', 'ALERTA')
            desc = diagnostico.get('description', '')
            color = "#E74C3C" if "CRÍTICO" in nivel else "#F1C40F" if "ALTO" in nivel else "#2ECC71"
            st.markdown(f"""<div style="padding: 20px; border-left: 6px solid {color}; background-color: #1A202C; margin-bottom: 25px;"><h3 style="color: {color}; margin:0;">{titulo}</h3><p>{desc}</p></div>""", unsafe_allow_html=True)

        st.markdown(f"## 📊 Informe Ejecutivo S.A.P.E. | {st.session_state.user_data.get('name','Usuario')}")
        k1, k2, k3 = st.columns(3)
        k1.metric("Índice IRE", f"{ire}/100")
        k2.metric("Potencial", f"{avg}/100")
        k3.metric("Fricción", f"{friction}%", delta_color="inverse")
        
        st.plotly_chart(radar_chart(), use_container_width=True)

        # GUARDADO EN SUPABASE
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

        st.markdown("---")
        st.info("Has completado la simulación. Puedes cerrar esta ventana.")


import ast # Necesario para leer la lista de sectores

# ==========================================
# 🎛️ BLOQUE 2: TU CONSOLA DE ADMINISTRADOR (VERSIÓN EDITAR/BORRAR)
# ==========================================
def render_admin_dashboard():
    st.title("🎛️ Consola de Mando: AUDEO HQ")
    st.info(f"Bienvenido, {st.session_state.user_data['username']}. Modo Dios activado.")
    
    tab1, tab2, tab3 = st.tabs(["👥 Usuarios (Alta/Edición)", "🏢 Organizaciones (Alta/Edición)", "📊 Estadísticas"])
    
    # ==========================================
    # PESTAÑA 1: GESTIÓN DE USUARIOS
    # ==========================================
    with tab1:
        st.markdown("### 1️⃣ Crear Nuevo Usuario")
        with st.expander("➕ Desplegar Formulario de Alta", expanded=False):
            with st.form("new_user_form"):
                c1, c2 = st.columns(2)
                new_user = c1.text_input("Nuevo Usuario (Login)")
                new_pass = c2.text_input("Contraseña", type="password")
                
                c3, c4 = st.columns(2)
                try:
                    orgs_db = supabase.table("organizations").select("id").execute()
                    lista_orgs = [o['id'] for o in orgs_db.data]
                except: lista_orgs = ["Audeo"]
                    
                new_org = c3.selectbox("Asignar Organización", lista_orgs)
                new_role = c4.selectbox("Rol", ["STUDENT", "MANAGER", "ADMIN"])
                
                if st.form_submit_button("💾 Crear Usuario"):
                    try:
                        supabase.table("users").insert({
                            "username": new_user, "password": new_pass, "org_id": new_org, "role": new_role
                        }).execute()
                        st.success(f"Usuario {new_user} creado."); st.rerun()
                    except Exception as e: st.error(f"Error: {e}")

        st.divider()
        st.markdown("### 2️⃣ Editar o Borrar Usuario Existente")
        
        # Cargar usuarios para el selector
        try:
            users_db = supabase.table("users").select("*").execute()
            df_users = pd.DataFrame(users_db.data)
            lista_users_ids = df_users['username'].tolist() if not df_users.empty else []
        except: lista_users_ids = []

        # SELECTOR DE USUARIO A EDITAR
        user_to_edit = st.selectbox("🔍 Selecciona Usuario para Editar/Borrar", ["Seleccionar..."] + lista_users_ids)

        if user_to_edit != "Seleccionar...":
            # Buscamos los datos actuales de ese usuario
            user_info = df_users[df_users['username'] == user_to_edit].iloc[0]
            
            st.info(f"Editando a: **{user_to_edit}**")
            
            with st.form("edit_user_form"):
                col_e1, col_e2 = st.columns(2)
                # Cargamos los valores actuales
                edit_pass = col_e1.text_input("Contraseña", value=user_info['password'])
                edit_role = col_e2.selectbox("Rol", ["STUDENT", "MANAGER", "ADMIN"], index=["STUDENT", "MANAGER", "ADMIN"].index(user_info['role']))
                
                edit_org = st.selectbox("Organización", lista_orgs, index=lista_orgs.index(user_info['org_id']) if user_info['org_id'] in lista_orgs else 0)
                
                c_btn1, c_btn2 = st.columns([1,1])
                
                # BOTÓN ACTUALIZAR
                if c_btn1.form_submit_button("💾 GUARDAR CAMBIOS"):
                    supabase.table("users").update({
                        "password": edit_pass, "role": edit_role, "org_id": edit_org
                    }).eq("username", user_to_edit).execute()
                    st.success("Usuario actualizado."); st.rerun()
                
                # BOTÓN BORRAR
                if c_btn2.form_submit_button("🗑️ BORRAR USUARIO", type="primary"):
                    if user_to_edit == "admin": st.error("No puedes borrar al admin.")
                    else:
                        supabase.table("users").delete().eq("username", user_to_edit).execute()
                        st.success("Usuario eliminado."); st.rerun()

    # ==========================================
    # PESTAÑA 2: GESTIÓN DE ORGANIZACIONES
    # ==========================================
    with tab2:
        st.markdown("### 1️⃣ Crear Nueva Organización")
        with st.expander("➕ Desplegar Formulario de Alta", expanded=False):
            with st.form("new_org_form"):
                org_id = st.text_input("ID (Sin espacios, ej: UNIV_VALENCIA)")
                org_name = st.text_input("Nombre Real (Ej: Universidad de Valencia)")
                
                lista_opciones = ["TECH", "RETAIL", "FREELANCE", "INTRA", "PSICO_SAN", "CONSULTORIA", "TURISMO", "SOCIAL", "SALUD", "PSICO_NO_SAN"]
                sectores = st.multiselect("Sectores Permitidos", lista_opciones, default=["TECH"])
                
                if st.form_submit_button("🏢 Crear Organización"):
                    try:
                        supabase.table("organizations").insert({
                            "id": org_id, "name": org_name, "active_sectors": str(sectores), "is_active": True
                        }).execute()
                        st.success(f"Org {org_name} creada."); st.rerun()
                    except Exception as e: st.error(f"Error: {e}")

        st.divider()
        st.markdown("### 2️⃣ Editar o Borrar Organización")

        # Selector de Organización
        org_to_edit_id = st.selectbox("🔍 Selecciona Organización", ["Seleccionar..."] + lista_orgs)

        if org_to_edit_id != "Seleccionar..." and org_to_edit_id != "Audeo":
            # Cargar datos actuales de Supabase
            current_org_data = supabase.table("organizations").select("*").eq("id", org_to_edit_id).execute().data[0]
            
            # Convertir el string de sectores "['TECH']" a lista real Python
            try:
                current_sectors_list = ast.literal_eval(current_org_data['active_sectors'])
            except: current_sectors_list = []

            with st.form("edit_org_form"):
                st.write(f"Editando: **{current_org_data['name']}**")
                
                # Campos editables
                new_name_edit = st.text_input("Nombre Real", value=current_org_data['name'])
                new_sectors_edit = st.multiselect("Sectores Permitidos", 
                                                  ["TECH", "RETAIL", "FREELANCE", "INTRA", "PSICO_SAN", "CONSULTORIA", "TURISMO", "SOCIAL", "SALUD", "PSICO_NO_SAN"],
                                                  default=current_sectors_list)
                
                c_btn_o1, c_btn_o2 = st.columns([1,1])
                
                # BOTÓN ACTUALIZAR
                if c_btn_o1.form_submit_button("💾 ACTUALIZAR PERMISOS"):
                    supabase.table("organizations").update({
                        "name": new_name_edit,
                        "active_sectors": str(new_sectors_edit)
                    }).eq("id", org_to_edit_id).execute()
                    st.success("Organización actualizada."); st.rerun()
                
                # BOTÓN BORRAR
                if c_btn_o2.form_submit_button("🗑️ BORRAR ORGANIZACIÓN", type="primary"):
                    try:
                        supabase.table("organizations").delete().eq("id", org_to_edit_id).execute()
                        st.success("Organización eliminada."); st.rerun()
                    except:
                        st.error("Error: Probablemente tenga usuarios dentro. Borra los usuarios primero.")

    # ==========================================
    # PESTAÑA 3: ESTADÍSTICAS
    # ==========================================
    with tab3:
        st.subheader("📊 Vista Global")
        try:
            # Traemos todos los resultados de golpe
            all_results = supabase.table("sape_results").select("*").execute()
            df_res = pd.DataFrame(all_results.data)
            
            if not df_res.empty:
                m1, m2 = st.columns(2)
                m1.metric("Total Simulaciones", len(df_res))
                avg_ire = df_res['ire'].mean()
                m2.metric("Promedio IRE Global", f"{avg_ire:.1f}")
                
                st.write("Últimos registros:")
                st.dataframe(df_res.tail(10))
            else:
                st.info("Aún no hay partidas jugadas.")
        except:
            st.warning("No se pudo cargar la tabla de resultados.")

# ==========================================
# 🚀 BLOQUE 3: EL ROUTER PRINCIPAL (MAIN)
# ==========================================
def main():
    # Inicialización Segura (Autocontenida)
    if 'octagon' not in st.session_state:
        st.session_state.octagon = {k: 50 for k in ["risk_propensity", "ambiguity_tolerance", "innovativeness", "locus_of_control", "emotional_stability", "achievement", "leadership", "adaptability"]}
    if 'flags' not in st.session_state: st.session_state.flags = {}
    if 'history' not in st.session_state: st.session_state.history = []
    if 'current_step' not in st.session_state: st.session_state.current_step = 0
    if 'started' not in st.session_state: st.session_state.started = False
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False

    # A. SI NO ESTÁ LOGUEADO -> PANTALLA DE LOGIN
    if not st.session_state.logged_in:
        st.markdown("""<style>.stApp {background-color: white; color: black;}</style>""", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown("<h1 style='text-align: center; color: black !important;'>🧬 AUDEO</h1>", unsafe_allow_html=True)
            st.markdown("<h3 style='text-align: center; color: #555 !important;'>Acceso Corporativo</h3>", unsafe_allow_html=True)
            
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
            st.title("Panel de Cliente")
            st.info("🚧 El Dashboard de gestión de talento está en construcción.")
            
        # 3. ES UN ALUMNO (JUGADOR)
        else:
            run_simulator_logic()

# EJECUTAR APLICACIÓN
if __name__ == "__main__":
    main()