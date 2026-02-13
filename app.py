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

# ==========================================
# 📂 1. CARGA DE PREGUNTAS Y MOTOR MATEMÁTICO (BLOQUE MAESTRO v7.0)
# ==========================================
# --- A. CARGA DE DATOS ---
@st.cache_data(ttl=0)
def load_questions():
    file_path = "SATE_V4.csv"
    if not os.path.exists(file_path):
        st.error(f"❌ No encuentro el archivo: {file_path}")
        return []

    try:
        # Leemos CSV con ;
        df = pd.read_csv(file_path, sep=";", encoding="utf-8-sig", dtype=str, engine='python')
        # Limpieza agresiva de nombres de columnas
        df.columns = df.columns.str.replace('"', '').str.replace("'", "").str.strip()
        # Convertimos a lista de diccionarios
        return df.to_dict('records')
    except Exception as e:
        st.error(f"❌ Error leyendo CSV: {e}")
        return []

# --- B. CONFIGURACIÓN DE CLAVES ---
# Mapa de normalización: 'locuscontrol' -> 'locus_control'
OFFICIAL_KEYS = [
    "risk_propensity", "ambiguity_tolerance", "innovativeness", 
    "locus_control", "emotional_stability", "achievement", 
    "self_efficacy", "autonomy"
]

def normalize_key(k):
    """Quita todo lo que no sea letra/número para comparar (SOLUCIÓN NUCLEAR)"""
    if not k: return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(k)).lower()

def get_key_map():
    return {normalize_key(k): k for k in OFFICIAL_KEYS}

def parse_val_key(p):
    """Extrae (clave, valor) de un string tipo 'risk 3' de forma robusta"""
    try:
        tokens = p.split()
        if len(tokens) >= 2:
            val = float(tokens[-1])
            raw_key = " ".join(tokens[:-1]) # Todo lo anterior es la clave
            norm_key = normalize_key(raw_key)
            return norm_key, val
    except: pass
    return None, None

# --- C. FUNCIONES DE CÁLCULO ---
def parse_logic(logic_string):
    """Lee lógica y suma puntos al usuario"""
    if not logic_string or pd.isna(logic_string): return
    
    clean_str = str(logic_string).replace('"', '').replace("'", "")
    parts = clean_str.split('|')
    
    if 'octagon' not in st.session_state: st.session_state.octagon = {}
    key_map = get_key_map()
    
    for p in parts:
        p = p.strip()
        if not p: continue
        norm_key, val = parse_val_key(p)
        if norm_key and norm_key in key_map:
            official_key = key_map[norm_key]
            st.session_state.octagon[official_key] = st.session_state.octagon.get(official_key, 0) + val

def get_max_potential_for_row(row, valid_keys):
    """Calcula máximo posible por pregunta"""
    row_maxes = {k: 0 for k in valid_keys}
    key_map = get_key_map()
    
    for char in ['A', 'B', 'C', 'D']:
        logic_str = row.get(f'OPCION_{char}_LOGIC')
        if not logic_str or pd.isna(logic_str): continue
        
        clean_str = str(logic_str).replace('"', '').replace("'", "")
        parts = clean_str.split('|')
        
        for p in parts:
            p = p.strip()
            if not p: continue
            norm_key, val = parse_val_key(p)
            
            if norm_key and norm_key in key_map:
                off_key = key_map[norm_key]
                # Solo si es positivo cuenta para el máximo posible
                if val > row_maxes[off_key]:
                    row_maxes[off_key] = val
            
    return row_maxes

def calculate_results():
    """Calcula porcentajes REALES con Saturación (0.8)"""
    user_scores = st.session_state.get('octagon', {})
    
    # Calcular Máximos
    all_questions = st.session_state.get('data', [])
    total_max_possibles = {k: 0 for k in OFFICIAL_KEYS}
    
    for row in all_questions:
        row_maxs = get_max_potential_for_row(row, OFFICIAL_KEYS)
        for k in OFFICIAL_KEYS:
            total_max_possibles[k] += row_maxs[k]

    # Saturación
    SATURATION_FACTOR = 0.80
    octagon_norm = {}
    
    for k in OFFICIAL_KEYS:
        u_val = user_scores.get(k, 0)
        max_val = total_max_possibles.get(k, 0)
        
        if max_val > 0:
            saturated_max = max_val * SATURATION_FACTOR
            percentage = (u_val / saturated_max) * 100
        else:
            percentage = 0
        octagon_norm[k] = max(0, min(100, percentage))

    # KPIs
    if octagon_norm:
        avg = sum(octagon_norm.values()) / len(octagon_norm)
    else: avg = 0
    ire = avg
    friction = max(0, 100 - ire)
    
    return int(ire), int(avg), int(friction), [], [], 0, octagon_norm, {
        "raw_user": user_scores, "max_possible": total_max_possibles
    }

# --- D. GRÁFICOS Y GUARDADO ---
def radar_chart():
    """Gráfico con etiquetas visuales"""
    _, _, _, _, _, _, scores, _ = calculate_results()
    if not scores: return go.Figure()
    
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
        r=values, theta=categories, fill='toself', name='Perfil',
        line_color='#0D248D', fillcolor='rgba(13, 36, 141, 0.2)'
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=10)),
                   angularaxis=dict(tickfont=dict(size=12, weight="bold"))),
        showlegend=False, margin=dict(l=40, r=40, t=20, b=20), height=350,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
    )
    return fig

def save_result_to_db(student_id, sector, ire, friction, triggers, scores, history, organization):
    try:
        supabase.table("sape_results").insert({
            "student_id": student_id, "sector": sector, "ire": ire, "friction": friction,
            "octagon": json.dumps(scores), "organization": organization,
            "created_at": datetime.now().isoformat()
        }).execute()
    except Exception as e: print(f"Error BD: {e}")

# ==========================================
# 🎮 3. INTERFAZ SIMULADOR (CORREGIDO)
# ==========================================
def normalize_key(k):
    """Quita todo lo que no sea letra/número para comparar (SOLUCIÓN NUCLEAR)"""
    import re
    if not k: return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(k)).lower()
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
# ==========================================
# 🕵️‍♂️ ESCÁNER DE DATOS (PEGAR AL FINAL DEL ARCHIVO PARA DIAGNÓSTICO)
# ==========================================
st.sidebar.markdown("---")
st.sidebar.header("🕵️‍♂️ ESCÁNER DE LOCUS")

# 1. Recuperamos el sector actual
current_sector = st.session_state.user_data.get('sector', 'TECH') # Por defecto TECH si no hay nada
st.sidebar.write(f"**Analizando Sector:** {current_sector}")

# 2. Buscamos oportunidades de puntos en el CSV
if st.sidebar.button("ESCANEAR EXCEL AHORA"):
    # Cargamos datos frescos
    try:
        df_debug = pd.read_csv("SATE_V4.csv", sep=";", encoding="utf-8-sig", dtype=str, engine='python')
        # Filtramos por el sector del usuario
        df_sector = df_debug[df_debug['SECTOR'] == current_sector]
        
        found_positive = False
        total_puntos = 0
        
        st.sidebar.write(f"📝 Preguntas en sector: {len(df_sector)}")
        
        for idx, row in df_sector.iterrows():
            # Revisamos las 4 opciones
            for char in ['A', 'B', 'C', 'D']:
                logic = str(row.get(f'OPCION_{char}_LOGIC', ''))
                # Normalizamos para buscar "locus"
                if "locus" in logic.lower().replace("_", "").replace(" ", ""):
                    # Extraemos el número
                    import re
                    # Busca cualquier número (ej: 3, -2, 4.5)
                    nums = re.findall(r'-?\d+', logic)
                    if nums:
                        val = float(nums[-1]) # Asumimos que el número está al final
                        icon = "🟢" if val > 0 else "🔴"
                        st.sidebar.code(f"{icon} Fila {idx} Opción {char}: {val} pts\nLogic: {logic}")
                        
                        if val > 0:
                            found_positive = True
                            total_puntos += val
                            
        if not found_positive:
            st.sidebar.error("🚨 ¡ALERTA! En este sector, Locus de Control NUNCA suma puntos positivos. Solo resta o no existe.")
            st.sidebar.info("Solución: El código funciona bien, pero debes editar el Excel para que alguna opción dé Locus positivo (ej: 'locus_control 3').")
        else:
            st.sidebar.success(f"✅ Se han encontrado {total_puntos} puntos posibles de Locus. El fallo está en el código.")
            
    except Exception as e:
        st.sidebar.error(f"Error leyendo archivo: {e}")