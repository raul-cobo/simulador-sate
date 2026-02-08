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

def check_credentials_from_csv(org_input, user_code, user_pass):
    """Verifica Organización + Usuario + Contraseña (Devuelve 3 valores)"""
    try:
        if not os.path.exists("usuarios.csv"):
            return False, "Error: No se encuentra usuarios.csv", None
            
        # INTENTO 1: Leer como UTF-8
        try:
            df_users = pd.read_csv("usuarios.csv", sep=";", dtype=str, encoding='utf-8')
        except UnicodeDecodeError:
            # INTENTO 2: Leer como Latin-1 (Windows)
            df_users = pd.read_csv("usuarios.csv", sep=";", dtype=str, encoding='latin-1')
        
        # Limpieza
        df_users.columns = [c.strip().lower() for c in df_users.columns]
        org_clean = org_input.strip().upper()
        user_clean = user_code.strip().upper()
        pass_clean = user_pass.strip()
        
        # Normalizamos la columna organización en el CSV
        if 'organizacion' in df_users.columns:
            df_users['organizacion'] = df_users['organizacion'].str.strip().str.upper()
        else:
            # Si no existe la columna en el CSV, creamos una genérica
            df_users['organizacion'] = 'GENERICO'

        df_users['usuario'] = df_users['usuario'].str.strip().str.upper()
        df_users['password'] = df_users['password'].str.strip()
        
        # 1. Buscamos fila que coincida en ORGANIZACIÓN y USUARIO
        match = df_users[
            (df_users['organizacion'] == org_clean) & 
            (df_users['usuario'] == user_clean)
        ]
        
        if match.empty:
            return False, "No se encuentra esa combinación de Organización y Usuario.", None
            
        # 2. Comprobamos contraseña
        correct_pass = match.iloc[0]['password']
        
        if str(correct_pass) == str(pass_clean):
            # AQUÍ ESTÁ LA CLAVE: Devolvemos 3 cosas
            return True, "OK", org_clean 
        else:
            return False, "Contraseña incorrecta.", None
            
    except Exception as e:
        return False, f"Error de sistema: {e}", None

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
    """Calcula máximos por rasgo Y máximo total del juego (CORREGIDO)"""
    max_scores = {k: 0 for k in LABELS_ES.keys()}
    total_game_points = 0 
    
    for row in sector_data:
        question_max_per_trait = {k: 0 for k in LABELS_ES.keys()}
        max_points_in_this_question = 0 
        
        for col in ['OPCION_A_LOGIC', 'OPCION_B_LOGIC', 'OPCION_C_LOGIC', 'OPCION_D_LOGIC']:
            logic = row.get(col)
            if not logic: continue
            
            # Calculamos cuántos puntos de COMPETENCIA da esta opción
            option_points = 0
            
            for action in logic.split('|'):
                parts = action.replace(":", " ").strip().split()
                if len(parts) < 2: continue
                
                trait_key = parts[0].lower().strip()
                trait = VARIABLE_MAP.get(trait_key)
                try: val = int(parts[1])
                except: continue
                
                # 1. Si es rasgo del octógono, actualizamos su máximo individual
                if trait in question_max_per_trait and val > 0:
                    question_max_per_trait[trait] = max(question_max_per_trait[trait], val)
                
                # 2. CAMBIO CLAVE: Solo sumamos al "bote total" si es una COMPETENCIA (no descarrilador)
                if val > 0 and trait in LABELS_ES: 
                    option_points += val
            
            # El máximo de esta pregunta es la opción que más puntos de competencia daba
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
    # 1. Obtener datos y normalizar
    max_possibles, total_game_points = get_sector_max_scores(st.session_state.data)
    
    octagon_norm = {}
    for k, raw_val in st.session_state.octagon.items():
        techo = max_possibles.get(k, 1)
        if techo == 0: techo = 1
        # Aplicamos factor de calibración x1.4 y limitamos a 100
        ratio = (raw_val / techo) * 100 * SCORE_MULTIPLIER
        ratio = min(100, ratio)
        octagon_norm[k] = int(max(0, min(100, ratio)))

    scores = octagon_norm 
    
    # Inicializamos banderas
    inferred_flags = {
        "excitable": 0, "skeptical": 0, "cautious": 0, "reserved": 0,
        "passive_aggressive": 0, "arrogant": 0, "mischievous": 0,
        "melodramatic": 0, "diligent": 0, "dependent": 0
    }
    
    special_observations = [] # Cambiamos nombre de variable interna también

    # ---------------------------------------------------------
    # A) REGLA ESTÁNDAR (Semáforo Verde hasta 90%)
    # Solo marca si > 90 (Exceso) o < 30 (Defecto)
    # ---------------------------------------------------------
    
    # Logro
    if scores["achievement"] >= 90: inferred_flags["diligent"] = 8
    if scores["achievement"] <= 30: inferred_flags["passive_aggressive"] = 6
    
    # Riesgo
    if scores["risk_propensity"] >= 90: inferred_flags["mischievous"] = 8
    if scores["risk_propensity"] <= 30: inferred_flags["cautious"] = 8
    
    # Innovación
    if scores["innovativeness"] >= 90: inferred_flags["excitable"] = 8
    if scores["innovativeness"] <= 30: inferred_flags["skeptical"] = 6
    
    # Autonomía
    if scores["autonomy"] >= 90: inferred_flags["reserved"] = 8
    if scores["autonomy"] <= 30: inferred_flags["dependent"] = 8
    
    # Autoeficacia
    if scores["self_efficacy"] >= 90: inferred_flags["arrogant"] = 8
    
    # Estabilidad
    if scores["emotional_stability"] <= 30: inferred_flags["melodramatic"] = 8

    # ---------------------------------------------------------
    # B) COMBINATORIAS EXTREMAS (Umbral especial 75/30)
    # Detecta perfiles complejos antes de llegar al 90
    # ---------------------------------------------------------

    # 1. LIDERAZGO TÓXICO
    if (scores["achievement"] >= 75 and 
        scores["emotional_stability"] <= 30 and 
        scores["locus_control"] <= 30):
        special_observations.append("LIDERAZGO TÓXICO")
        inferred_flags["excitable"] = 10 
        inferred_flags["diligent"] = 10

    # 2. IDEÓLOGO SIN ACCIÓN
    if (scores["innovativeness"] >= 75 and 
        scores["self_efficacy"] >= 75 and 
        scores["achievement"] <= 30):
        special_observations.append("IDEÓLOGO SIN ACCIÓN")
        inferred_flags["arrogant"] = 10
        inferred_flags["mischievous"] = 8

    # 3. MICROMANAGER EXCESIVO
    if (scores["risk_propensity"] <= 30 and 
        scores["autonomy"] <= 30 and 
        scores["achievement"] >= 75):
        special_observations.append("MICROMANAGER EXCESIVO")
        inferred_flags["cautious"] = 10
        inferred_flags["diligent"] = 10

    # 4. EXCESIVAMENTE ARRIESGADO
    if (scores["risk_propensity"] >= 75 and 
        scores["self_efficacy"] >= 75 and 
        scores["locus_control"] <= 30):
        special_observations.append("EXCESIVAMENTE ARRIESGADO")
        inferred_flags["mischievous"] = 10

    # 5. EJECUCIÓN MECÁNICA
    # (Usamos Estabilidad como proxy de tolerancia al estrés/presión positiva aquí)
    if (scores["innovativeness"] <= 30 and 
        scores["autonomy"] <= 30 and 
        scores["emotional_stability"] >= 75):
        special_observations.append("EJECUCIÓN MECÁNICA")
        inferred_flags["dependent"] = 10
        inferred_flags["skeptical"] = 8

    # 6. RESISTENCIA PASIVA
    if (scores["achievement"] <= 30 and 
        scores["autonomy"] >= 75 and 
        scores["locus_control"] <= 30):
        special_observations.append("RESISTENCIA PASIVA")
        inferred_flags["passive_aggressive"] = 10

    # Guardamos banderas
    st.session_state.flags = inferred_flags

    # --- CÁLCULO FINAL DE MÉTRICAS (NORMALIZADO POR SECTOR) ---
    
    # 1. Promedio (Potencial)
    avg = sum(scores.values()) / 8
    
    # 2. Fricción
    raw_friction = sum(inferred_flags.values())
    friction = min(100, (raw_friction / 40.0) * 100)
    
    # 3. IRE Base (Bruto)
    penalty_factor = friction / 200.0 
    raw_ire = avg * (1 - penalty_factor)
    
    # 4. ESCALADO DINÁMICO (Aquí ocurre la magia 0-100)
    # Recuperamos el sector del usuario (o default TECH)
    user_sector = st.session_state.get("sector", "TECH")
    
    # Buscamos los límites de ese sector
    limits = SECTOR_LIMITS.get(user_sector, SECTOR_LIMITS["TECH"])
    
    # Fórmula: (Valor - Min) / (Max - Min) * 100
    range_span = limits['max'] - limits['min']
    if range_span == 0: range_span = 1 # Evitar división por cero
    
    scaled_ire = ((raw_ire - limits['min']) / range_span) * 100
    
    # Aseguramos que esté entre 0 y 100 final
    ire = max(0, min(100, scaled_ire))
    
    # --- FIN CÁLCULO ---

    # Preparar textos para el return
    triggers = [k for k, v in inferred_flags.items() if v > 0]
    fric_reasons = []
    if special_observations:
        fric_reasons.append(f"ℹ️ Observación: {', '.join(special_observations)}")
    elif friction > 20:
        fric_reasons.append("Se observan áreas de desarrollo por descompensación.")
        
    delta = round(avg - ire, 2)
    
    return round(ire, 2), round(avg, 2), round(friction, 2), triggers, fric_reasons, delta, scores, max_possibles

def get_ire_text(s): 
    if s > 75: return "Nivel de Viabilidad: ALTO (Sostenible)"
    if s > 50: return "Nivel de Viabilidad: MEDIO (Requiere Ajustes)"
    return "Nivel de Viabilidad: BAJO (Riesgo Operativo)"

def radar_chart():
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

# --- DICCIONARIO MAESTRO DE RIESGOS (INDICE CONDUCTUAL) ---
# Copiado de tu documento "Índice Maestro de Riesgos Conductuales.docx"
RISK_MASTER_INDEX = {
    "EXCITABLE": {
        "alias": "El Ciclotímico (Volátil)",
        "desc": "Energía explosiva seguida de abandono.",
        "risk": "Inconsistencia Estratégica: Cambios de rumbo por estado de ánimo, no por datos."
    },
    "SKEPTICAL": {
        "alias": "El Desconfiado (Escéptico)",
        "desc": "Ve amenazas y conspiraciones donde hay oportunidades.",
        "risk": "Bloqueo de Innovación: Rechazo sistemático a nuevas ideas y creación de silos."
    },
    "CAUTIOUS": {
        "alias": "El Temeroso (Cauteloso)",
        "desc": "Miedo paralizante al error y al mercado.",
        "risk": "Coste de Oportunidad: Pérdida de ventanas de mercado por parálisis."
    },
    "RESERVED": {
        "alias": "La Caja Negra (Reservado)",
        "desc": "Se aísla y corta la comunicación bajo presión.",
        "risk": "Desalineamiento: El equipo y los inversores operan a ciegas ante crisis."
    },
    "PASSIVE_AGGRESSIVE": {
        "alias": "El Saboteador (Pasivo-Agresivo)",
        "desc": "Falsa cooperación. Dice 'sí' pero ejecuta 'no'.",
        "risk": "Toxicidad Cultural: Erosión de la autoridad y agendas ocultas."
    },
    "ARROGANT": {
        "alias": "El Dios (Arrogante)",
        "desc": "Exceso de confianza. Cree que las reglas no aplican a él.",
        "risk": "Ceguera de Mercado: Ignora el feedback del cliente hasta que es tarde."
    },
    "MISCHIEVOUS": {
        "alias": "El Jugador (Travieso)",
        "desc": "Toma riesgos irracionales por pura adrenalina.",
        "risk": "Mortalidad Súbita: Riesgo de quiebra por apuestas 'Todo o Nada'."
    },
    "MELODRAMATIC": {
        "alias": "El Actor (Melodramático)",
        "desc": "Necesita ser el centro de atención. Crea crisis para resolverlas.",
        "risk": "Distracción Operativa: La empresa gira en torno al ego del fundador."
    },
    "DILIGENT": {
        "alias": "El Perfeccionista (Diligente)",
        "desc": "Obsesión por el detalle y el micro-management.",
        "risk": "Parálisis por Análisis: Incapacidad para delegar o lanzar productos mínimos."
    },
    "DEPENDENT": {
        "alias": "El Seguidor (Dependiente)",
        "desc": "Incapaz de tomar decisiones sin consenso o aprobación.",
        "risk": "Cuello de Botella: El fundador se convierte en el freno del crecimiento."
    },
    # Patrones Complejos
    "LIDERAZGO TÓXICO": {
        "alias": "Patrón: Liderazgo Tóxico",
        "desc": "Combinación de alta exigencia, baja empatía y culpa externa.",
        "risk": "Alta Rotación: Destrucción del talento clave en tiempo récord."
    },
    "IDEÓLOGO SIN ACCIÓN": {
        "alias": "Patrón: Ideólogo sin Acción",
        "desc": "Mucha visión y creatividad, pero nula capacidad de cierre.",
        "risk": "Burnout de Caja: Se gasta el dinero en ideas que nunca salen al mercado."
    },
    "MICROMANAGER EXCESIVO": {
        "alias": "Patrón: Micromanager",
        "desc": "Control absoluto por miedo al error ajeno.",
        "risk": "Techo de Escalabilidad: La empresa no crece más allá de las horas del fundador."
    },
    "EXCESIVAMENTE ARRIESGADO": {
        "alias": "Patrón: Kamikaze",
        "desc": "Confianza ciega + Riesgo extremo + Cero culpa.",
        "risk": "Colapso Estructural: Probabilidad de fraude o quiebra por negligencia."
    },
    "EJECUCIÓN MECÁNICA": {
        "alias": "Patrón: El Burócrata",
        "desc": "Obediencia ciega al proceso. Cero innovación.",
        "risk": "Obsolescencia: Incapacidad para pivotar ante cambios del mercado."
    },
    "PERFIL DELIRANTE": {
        "alias": "Patrón: Delirante",
        "desc": "Desconexión total de la realidad operativa.",
        "risk": "Inviabilidad Absoluta: El proyecto es una fantasía del fundador."
    }
}

# --- FUNCIÓN PDF CORREGIDA (V65) ---
def create_pdf_report(ire, avg, friction, triggers, friction_reasons, delta, user, stats, diagnostico=None):
    if not PDF_AVAILABLE: return None
    
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    
    # --- PÁGINA 1 ---
    draw_page_header(p, w, h)
    
    # DATOS CABECERA
    y = h - 130
    p.setFillColorRGB(0,0,0)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(40, y, f"ID Usuario: {st.session_state.user_id}")
    p.drawString(40, y-15, f"Fecha de Análisis: {datetime.now().strftime('%d/%m/%Y')}")
    p.drawString(40, y-30, f"Sector: {user.get('sector', 'N/A')}")
    p.drawRightString(w-40, y, f"Candidato: {user.get('name', 'N/A')}")
    
    # -------------------------------------------------------
    # BLOQUE DIAGNÓSTICO
    # -------------------------------------------------------
    y -= 50
    if diagnostico:
        titulo = diagnostico.get('name', 'Diagnóstico')
        if 'risk_level' in diagnostico: nivel = diagnostico['risk_level']
        elif 'verdict' in diagnostico: nivel = diagnostico['verdict']
        else: nivel = "ALERTA"
            
        desc = diagnostico.get('description') or diagnostico.get('risk_summary') or ""
        
        # Color según riesgo
        if "CRÍTICO" in nivel: r,g,b = 0.9, 0.3, 0.23 # Rojo
        elif "ALTO" in nivel or "ALERTA" in nivel: r,g,b = 0.94, 0.76, 0.06 # Amarillo
        else: r,g,b = 0.18, 0.8, 0.44 # Verde
        
        box_height = 80 
        p.saveState() 
        p.setStrokeColorRGB(r,g,b)
        try: p.setFillColorRGB(r,g,b, 0.1) 
        except: p.setFillColorRGB(0.95, 0.95, 0.95)
        p.roundRect(40, y-box_height, w-80, box_height+10, 4, fill=1, stroke=1)
        p.restoreState()
        
        p.setFillColorRGB(r,g,b); p.rect(40, y-box_height, 5, box_height+10, fill=1, stroke=0)
        p.setFont("Helvetica-Bold", 12); p.drawString(55, y-15, titulo)
        p.setFillColorRGB(0,0,0); p.setFont("Helvetica-Bold", 10); p.drawString(55, y-30, f"Nivel: {nivel}")
        p.setFont("Helvetica", 9); p.setFillColorRGB(0.3, 0.3, 0.3)
        
        text_obj = p.beginText(55, y - 45)
        lines = textwrap.wrap(desc, width=95)
        for line in lines[:3]: text_obj.textLine(line)
        p.drawText(text_obj)
        y -= (box_height + 30)

    # -------------------------------------------------------
    # SECCIÓN 1: MÉTRICAS
    # -------------------------------------------------------
    p.setFillColorRGB(0, 0, 0)
    if y < 100: p.showPage(); draw_page_header(p, w, h); y = h - 130
    
    p.setFont("Helvetica-Bold", 12); p.drawString(40, y, "1. Métricas Principales")
    y -= 25
    
    # Potencial
    p.setFont("Helvetica-Bold", 10); p.drawString(40, y, f"POTENCIAL ({avg}/100):")
    p.setFont("Helvetica", 9); 
    desc_pot = "Nivel Superior." if avg > 70 else "Perfil Generalista / Ejecutor Equilibrado." if avg > 50 else "En Desarrollo."
    p.drawString(160, y, desc_pot)
    y -= 12
    p.setFillColorRGB(0.3, 0.3, 0.3); p.drawString(40, y, "Recursos cognitivos basales.")
    
    # Fricción
    y -= 25
    p.setFillColorRGB(0,0,0)
    p.setFont("Helvetica-Bold", 10); p.drawString(40, y, f"FRICCIÓN ({friction}/100):")
    p.setFont("Helvetica", 9);
    desc_fric = "Nivel crítico." if friction > 50 else "Nivel moderado." if friction > 20 else "Nivel bajo."
    p.drawString(160, y, desc_fric)
    y -= 12
    p.setFillColorRGB(0.3, 0.3, 0.3)
    p.drawString(40, y, "Conductas que ralentizan la ejecución (Ver Detalle en Sección 3).")

    # IRE
    y -= 25
    p.setFillColorRGB(0,0,0)
    p.setFont("Helvetica-Bold", 10); p.drawString(40, y, f"IRE FINAL ({ire}/100):")
    p.setFont("Helvetica", 9);
    desc_ire = "Viabilidad Operativa Sólida." if ire > 50 else "Requiere Revisión Estructural."
    p.drawString(160, y, desc_ire)

    y -= 20
    p.setLineWidth(1); p.setStrokeColorRGB(0.8, 0.8, 0.8); p.line(40, y, w-40, y)

    # -------------------------------------------------------
    # SECCIÓN 2: ANÁLISIS DIMENSIONAL
    # -------------------------------------------------------
    y -= 30
    if y < 100: p.showPage(); draw_page_header(p, w, h); y = h - 130
    p.setFillColorRGB(0,0,0); p.setFont("Helvetica-Bold", 12); p.drawString(40, y, "2. Análisis Dimensional")
    y -= 25

    bar_x = 260; bar_w = 250; bar_h = 10
    seg1 = bar_w * 0.25; seg2 = bar_w * 0.35; seg3 = bar_w * 0.30; seg4 = bar_w * 0.10
    
    for k, score in stats.items():
        if y < 60: p.showPage(); draw_page_header(p, w, h); y = h - 130
        lbl = LABELS_ES.get(k, k)
        p.setFillColorRGB(0,0,0); p.setFont("Helvetica-Bold", 9); p.drawString(40, y, lbl)
        p.drawRightString(bar_x - 10, y, f"{score}")
        p.setStrokeColorRGB(0.9,0.9,0.9); p.setFillColorRGB(0.95, 0.95, 0.95); p.rect(bar_x, y, bar_w, bar_h, fill=1, stroke=1)
        cur_x = bar_x
        w1 = min(score, 25) / 25 * seg1
        if w1 > 0: p.setFillColorRGB(0.9, 0.3, 0.23); p.rect(cur_x, y, w1, bar_h, fill=1, stroke=0); cur_x += w1
        if score > 25:
            w2 = min(score-25, 35)/35*seg2; p.setFillColorRGB(0.94, 0.76, 0.06); p.rect(bar_x+seg1, y, w2, bar_h, fill=1, stroke=0)
        if score > 60:
            w3 = min(score-60, 30)/30*seg3; p.setFillColorRGB(0.18, 0.8, 0.44); p.rect(bar_x+seg1+seg2, y, w3, bar_h, fill=1, stroke=0)
        if score > 90:
            w4 = min(score-90, 10)/10*seg4; p.setFillColorRGB(0.9, 0.3, 0.23); p.rect(bar_x+seg1+seg2+seg3, y, w4, bar_h, fill=1, stroke=0)
        y -= 15

    y -= 15
    p.setLineWidth(1); p.setStrokeColorRGB(0.8, 0.8, 0.8); p.line(40, y, w-40, y)

    # -------------------------------------------------------
    # SECCIÓN 2.2 / 2.3 (Fortalezas / Mejoras)
    # -------------------------------------------------------
    fortalezas = {k:v for k,v in stats.items() if v >= 60}
    mejoras = {k:v for k,v in stats.items() if v < 60}

    y -= 30
    if y < 100: p.showPage(); draw_page_header(p, w, h); y = h - 130
    p.setFillColorRGB(0,0,0); p.setFont("Helvetica-Bold", 12); p.drawString(40, y, "2.2 Fortalezas Consolidadas")
    y -= 20
    if not fortalezas: p.setFont("Helvetica-Oblique", 9); p.drawString(40, y, "No se detectan fortalezas destacadas (>60)."); y -= 20
    else:
        for k, v in fortalezas.items():
            lbl = LABELS_ES.get(k, k); desc = get_competency_desc(k, v)
            lines = textwrap.wrap(desc, width=90)
            if y < (len(lines)*10 + 30): p.showPage(); draw_page_header(p, w, h); y = h - 130
            p.setFillColorRGB(0,0,0); p.setFont("Helvetica-Bold", 10); p.drawString(40, y, f"• {lbl} ({v}/100)"); y -= 12
            text_obj = p.beginText(40, y); text_obj.setFont("Helvetica", 9); text_obj.setFillColorRGB(0.3,0.3,0.3)
            for line in lines: text_obj.textLine(line)
            p.drawText(text_obj); y -= (len(lines)*10 + 10)

    y -= 20
    if y < 100: p.showPage(); draw_page_header(p, w, h); y = h - 130
    p.setFillColorRGB(0,0,0); p.setFont("Helvetica-Bold", 12); p.drawString(40, y, "2.3 Áreas de Desarrollo")
    y -= 20
    if not mejoras: p.setFont("Helvetica-Oblique", 9); p.drawString(40, y, "Perfil muy equilibrado."); y -= 20
    else:
        for k, v in mejoras.items():
            lbl = LABELS_ES.get(k, k); desc = get_competency_desc(k, v)
            lines = textwrap.wrap(desc, width=90)
            if y < (len(lines)*10 + 30): p.showPage(); draw_page_header(p, w, h); y = h - 130
            p.setFillColorRGB(0,0,0); p.setFont("Helvetica-Bold", 10); p.drawString(40, y, f"• {lbl} ({v}/100)"); y -= 12
            text_obj = p.beginText(40, y); text_obj.setFont("Helvetica", 9); text_obj.setFillColorRGB(0.3,0.3,0.3)
            for line in lines: text_obj.textLine(line)
            p.drawText(text_obj); y -= (len(lines)*10 + 10)

    p.setLineWidth(1); p.setStrokeColorRGB(0.8, 0.8, 0.8); p.line(40, y, w-40, y)

    # -------------------------------------------------------
    # SECCIÓN 3: FRICCIÓN (CON ÍNDICE MAESTRO) - CORREGIDO
    # -------------------------------------------------------
    y -= 30
    if y < 150: p.showPage(); draw_page_header(p, w, h); y = h - 130
    
    p.setFillColorRGB(0,0,0); p.setFont("Helvetica-Bold", 12)
    p.drawString(40, y, "3. Análisis de la Fricción (Bloqueos Operativos)")
    y -= 25
    
    if friction_reasons:
        p.setFont("Helvetica", 9); p.setFillColorRGB(0,0,0)
        for reason in friction_reasons:
            if y < 80: p.showPage(); draw_page_header(p, w, h); y = h - 130
            
            # Intentamos extraer el KEY del razón (ej: "Conducta EXCITABLE (8/10)")
            # Buscamos qué key del RISK_MASTER_INDEX está en el string 'reason'
            risk_info = None
            for key, info in RISK_MASTER_INDEX.items():
                if key in reason.upper():
                    risk_info = info
                    break
            
            # Título (Razón original + Alias bonito si existe)
            titulo_mostrar = reason
            if risk_info: titulo_mostrar = f"• {risk_info['alias']} - (Nivel Detectado)"
            
            p.setFont("Helvetica-Bold", 9); p.setFillColorRGB(0.2, 0.2, 0.2)
            p.drawString(40, y, titulo_mostrar)
            y -= 12
            
            # Descripción y Riesgo (Del Índice Maestro)
            if risk_info:
                desc_text = f"Perfil: {risk_info['desc']}"
                risk_text = f"RIESGO DE NEGOCIO: {risk_info['risk']}"
                
                # Pintamos Descripción
                lines_d = textwrap.wrap(desc_text, width=95)
                p.setFont("Helvetica", 9); p.setFillColorRGB(0.3, 0.3, 0.3)
                for line in lines_d:
                    p.drawString(55, y, line); y -= 12
                
                # Pintamos Riesgo (En rojo oscuro o negrita)
                y -= 2
                lines_r = textwrap.wrap(risk_text, width=95)
                p.setFont("Helvetica-BoldOblique", 9); p.setFillColorRGB(0.6, 0.2, 0.2)
                for line in lines_r:
                    p.drawString(55, y, line); y -= 12
            else:
                # Si no está en el índice maestro, usamos texto genérico
                p.setFont("Helvetica-Oblique", 8); p.setFillColorRGB(0.4, 0.4, 0.4)
                p.drawString(55, y, "Impacto: Fricción operativa general.")
                y -= 12
                
            y -= 8 # Espacio entre items
            
    elif friction > 0:
        p.setFont("Helvetica", 9); p.setFillColorRGB(0,0,0)
        p.drawString(40, y, "• Fricción basal detectada (Nivel Bajo).")
        y -= 12
        p.setFont("Helvetica-Oblique", 8); p.setFillColorRGB(0.4, 0.4, 0.4)
        p.drawString(55, y, "Impacto: Pequeñas vacilaciones sin bloqueo crítico.")
        y -= 20
    else:
        p.setFont("Helvetica-Oblique", 9); p.setFillColorRGB(0.5,0.5,0.5)
        p.drawString(40, y, "Flujo operativo limpio. No se han detectado conductas limitantes.")
        y -= 20

    y -= 10
    p.setLineWidth(1); p.setStrokeColorRGB(0.8, 0.8, 0.8); p.line(40, y, w-40, y)

    # -------------------------------------------------------
    # SECCIÓN 4: CONCLUSIÓN (CORREGIDO OVERFLOW)
    # -------------------------------------------------------
    y -= 30
    if y < 150: p.showPage(); draw_page_header(p, w, h); y = h - 130
    p.setFillColorRGB(0,0,0); p.setFont("Helvetica-Bold", 12); p.drawString(40, y, "4. Conclusión y Recomendación")
    y -= 25
    
    sorted_mejoras = sorted([(k,v) for k,v in stats.items() if v < 60], key=lambda x: x[1])
    top_ajustes = [LABELS_ES.get(k[0], k[0]) for k in sorted_mejoras[:2]]
    
    conc_text = f"El perfil presenta un IRE de {ire}/100. "
    rec_text = ""
    
    if ire > 75:
        conc_text += "El perfil es sólido y sostenible (Nivel Alto). La estructura de personalidad favorece la escalabilidad del proyecto sin riesgos estructurales."
        rec_text = "Recomendación: Mantener el equilibrio actual y potenciar las fortalezas detectadas."
    elif ire > 50:
        conc_text += "El perfil presenta una viabilidad operativa sólida (Nivel Competitivo). Su configuración es funcional para la etapa actual, aunque se beneficiaría de optimizaciones puntuales. "
        if top_ajustes: conc_text += f"Es necesario trabajar el desarrollo de: {', '.join(top_ajustes)}."
        else: conc_text += "Se recomienda reforzar la consistencia entre visión y ejecución."
        rec_text = "Recomendación: Priorizar el plan de desarrollo competencial en las áreas señaladas."
    else:
        conc_text += "El nivel de viabilidad requiere atención (Nivel de Alerta). Se detectan fricciones operativas que podrían afectar la velocidad de crecimiento si no se gestionan."
        rec_text = "Recomendación: Reevaluar el encaje del rol o activar un plan de choque urgente en las áreas críticas."

    # Pintar Conclusión (Wrapped)
    p.setFont("Helvetica", 9)
    lines_conc = textwrap.wrap(conc_text, width=100)
    for line in lines_conc:
        if y < 50: p.showPage(); draw_page_header(p, w, h); y = h - 130
        p.drawString(40, y, line)
        y -= 12
    
    y -= 10
    
    # Pintar Recomendación (Wrapped - FIX OVERFLOW)
    p.setFont("Helvetica-Bold", 9)
    if friction > 30: 
        rec_text += " (Foco adicional: Reducción de tiempos de deliberación)."
    
    # AQUÍ ESTABA EL ERROR: Usar textwrap también para la recomendación
    lines_rec = textwrap.wrap(rec_text, width=100)
    for line in lines_rec:
        if y < 50: p.showPage(); draw_page_header(p, w, h); y = h - 130
        p.drawString(40, y, line)
        y -= 12
        
    y -= 40

    # -------------------------------------------------------
    # GRÁFICO RADAR
    # -------------------------------------------------------
    if y < 160: p.showPage(); draw_page_header(p, w, h); y = h - 130
    draw_radar_on_pdf(p, stats, w/2, y - 80, 70)

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# --- FUNCIÓN PDF DEFINITIVA (Con Fricción Detallada e Implicaciones) ---

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
    
    # --- PANTALLA DE INSTRUCCIONES (ONBOARDING) ---
    if 'instructions_seen' not in st.session_state:
        st.session_state.instructions_seen = False

    if not st.session_state.instructions_seen:
        # Usamos el estilo limpio para leer
        inject_style("login") 
        
        st.markdown("## 📜 Guía de Supervivencia: Simulador S.A.P.E.")
        
        st.info("""
        **Bienvenido/a al simulador.** Estás a punto de asumir el rol de fundador/a de una empresa a lo largo de **40 meses virtuales**.
        Tu objetivo no es "ganar", sino tomar decisiones coherentes con tu forma de ser.
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### ⚙️ Mecánica")
            st.markdown("""
            * Cada mes te enfrentarás a un **desafío crítico**.
            * Tendrás **4 opciones** de respuesta.
            * **No hay respuestas correctas o incorrectas**: cada decisión tiene consecuencias y moldea tu perfil.
            * Elige lo que **realmente harías**, no lo que "queda bien".
            """)
            
        with col2:
            st.markdown("### ⚠️ Reglas de Oro")
            st.markdown("""
            * 🚫 **NO uses el botón 'Atrás'** del navegador (perderás el progreso).
            * 🚫 **NO refresques la página** a mitad de la partida.
            * ⏳ **Sin prisa:** Tómate tu tiempo para leer el contexto.
            * 🔄 **Irreversible:** Una vez tomada una decisión, no hay vuelta atrás.
            """)
            
        st.divider()
        
        st.markdown("### 🏁 Finalización")
        st.caption("Al terminar el mes 40, el sistema guardará automáticamente tu perfil competencial y lo enviará a la dirección académica de tu organización. Recibirás un feedback inmediato sobre tu estilo de liderazgo.")
        
        st.write("") # Espacio
        
        # EL BOTÓN PARA EMPEZAR DE VERDAD
        if st.button("✅ HE LEÍDO LAS REGLAS. COMENZAR SIMULACIÓN", use_container_width=True, type="primary"):
            st.session_state.instructions_seen = True
            st.rerun()

    # --- SI YA VIO LAS INSTRUCCIONES, ENTRA AL APP NORMAL ---
    else:
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
                
                # --- CÓDIGO NUEVO: RESPUESTAS ALEATORIAS ---
                step = st.session_state.current_step
                # 1. Empaquetamos Texto + Lógica (Las "Cartas")
                options = []
                if pd.notna(row.get('OPCION_A_TXT')) and str(row.get('OPCION_A_TXT')).strip():
                    options.append({'txt': row['OPCION_A_TXT'], 'logic': row.get('OPCION_A_LOGIC'), 'id': 'A'})
                if pd.notna(row.get('OPCION_B_TXT')) and str(row.get('OPCION_B_TXT')).strip():
                    options.append({'txt': row['OPCION_B_TXT'], 'logic': row.get('OPCION_B_LOGIC'), 'id': 'B'})
                if pd.notna(row.get('OPCION_C_TXT')) and str(row.get('OPCION_C_TXT')).strip():
                    options.append({'txt': row['OPCION_C_TXT'], 'logic': row.get('OPCION_C_LOGIC'), 'id': 'C'})
                if pd.notna(row.get('OPCION_D_TXT')) and str(row.get('OPCION_D_TXT')).strip():
                    options.append({'txt': row['OPCION_D_TXT'], 'logic': row.get('OPCION_D_LOGIC'), 'id': 'D'})

                # 2. BARAJAMOS LAS CARTAS 🎲
                random.shuffle(options)

                # 3. PINTAMOS LOS BOTONES BARAJADOS
                st.markdown("""
                <style>
                div.stButton > button {
                    height: auto;
                    min_height: 80px;
                    white-space: normal;
                    text-align: left;
                    padding: 15px;
                }
                </style>
                """, unsafe_allow_html=True)

                for opt in options:
                    # Clave única para que Streamlit no se líe
                    btn_key = f"btn_{step}_{opt['id']}"
                    
                    if st.button(opt['txt'], key=btn_key, use_container_width=True):
                        # AL PULSAR: Leemos la lógica que venía en ESTA carta específica
                        parse_logic(opt['logic'])
                        
                        # --- RED DE SEGURIDAD (NUEVO) ---
                        if 'history' not in st.session_state:
                            st.session_state.history = []
                        
                        st.session_state.history.append({
                            "mes": row['MES'],
                            "opcion": opt['id'], 
                            "texto": opt['txt']
                        })
                        
                        st.session_state.current_step += 1
                        st.rerun()

        else:
            render_header()
            # 1. Calculamos resultados numéricos
            ire, avg, friction, triggers, fric_reasons, delta, octagon_norm, max_possibles = calculate_results()
            
            # 2. DIAGNÓSTICO INTELIGENTE (Cerebro SAPE)
            cerebro = cargar_cerebro_sape()
            diagnostico = diagnosticar_usuario_python(octagon_norm, cerebro)

            if diagnostico:
                titulo = diagnostico.get('name', 'Diagnóstico')
                if 'risk_level' in diagnostico: nivel = diagnostico['risk_level']
                elif 'verdict' in diagnostico: nivel = diagnostico['verdict']
                else: nivel = "ALERTA"
                
                desc = diagnostico.get('description') or diagnostico.get('risk_summary') or diagnostico.get('summary')
                raw_impact = diagnostico.get('business_impact') or diagnostico.get('business_risk') or diagnostico.get('assets')
                impacto = raw_impact[0] if isinstance(raw_impact, list) else raw_impact

                if "CRÍTICO" in nivel: color_caja = "#E74C3C" 
                elif "ALTO" in nivel or "ALERTA" in nivel: color_caja = "#F1C40F" 
                else: color_caja = "#2ECC71" 
                
                st.markdown(f"""
                <div style="padding: 20px; border-radius: 10px; border-left: 6px solid {color_caja}; background-color: #1A202C; margin-bottom: 25px; margin-top: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                    <h3 style="color: {color_caja}; margin:0; font-family: sans-serif;">{titulo}</h3>
                    <p style="color: white; font-weight: bold; margin-top: 8px;">{nivel}</p>
                    <p style="color: #DDDDDD; font-size: 15px; margin-top: 10px; line-height: 1.4;">{desc}</p>
                    <hr style="border-color: #444; margin: 15px 0;">
                    <p style="color: #AAAAAA; font-size: 14px;"><strong>Impacto/Clave:</strong> {impacto}</p>
                </div>
                """, unsafe_allow_html=True)

            st.markdown(f"## 📊 Informe Ejecutivo S.A.P.E. | {st.session_state.user_data['name']}")
            k1, k2, k3 = st.columns(3)
            k1.metric("Índice IRE (Viabilidad)", f"{ire}/100", help="Índice de Rendimiento Emprendedor Global")
            k2.metric("Potencial Competencial", f"{avg}/100", help="Puntuación media de las 8 competencias clave")
            k3.metric("Nivel de Fricción", f"{friction}%", "-Bajo es mejor", delta_color="inverse", help="Porcentaje de patrones limitantes")
            
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

            # --- BLOQUE DE CIERRE Y GUARDADO (VERSIÓN SEGURA) ---
            safe_student_id = st.session_state.get('student_id', 'UNKNOWN')
            safe_sector = st.session_state.user_data.get('sector', 'GEN')
            
            safe_ire = locals().get('ire', 0)
            safe_friction = locals().get('friction', 0)
            safe_triggers = locals().get('triggers', [])
            safe_scores = locals().get('octagon_norm', {})

            if 'data_saved' not in st.session_state:
                org_to_save = st.session_state.user_data.get('organization', 'GENERICO')
                
                save_result_to_db(
                    student_id=safe_student_id, 
                    sector=safe_sector, 
                    ire=safe_ire, 
                    friction=safe_friction, 
                    triggers=safe_triggers, 
                    scores=st.session_state.octagon,   
                    history=st.session_state.history,  
                    organization=org_to_save           
                )
                st.session_state.data_saved = True

            st.divider()
            org_name = st.session_state.user_data.get('organization', 'tu organización')
            st.success(f"✅ Tus resultados han sido registrados y enviados al equipo de {org_name}.")
            
            st.markdown("""
            <div style="background-color: #11268C; padding: 20px; border-radius: 10px; text-align: center;">
                <h3>¡Gracias por tu participación!</h3>
                <p>Ya puedes cerrar esta pestaña.</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.stop()