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

# --- LIBRERÍAS DE ORYON ---
import pandas as pd
import numpy as np
import plotly.express as px

# --- GESTIÓN DE PDF ---
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Audeo | Oryon Edition", page_icon="🧬", layout="wide")

# --- 2. ESTILOS ---
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
            
            /* PESTAÑAS (TABS) */
            .stTabs [data-baseweb="tab-list"] { gap: 10px; justify-content: center; margin-bottom: 20px; }
            .stTabs [data-baseweb="tab"] {
                height: 50px; background-color: #F0F2F6; border-radius: 5px; color: #000000; font-weight: bold; padding: 0 20px; border: 1px solid #ddd;
            }
            .stTabs [aria-selected="true"] { background-color: #0F2489 !important; color: #FFFFFF !important; border: 1px solid #0F2489; }

            .stTextInput input { background-color: #F8F9FA !important; color: #000000 !important; border: 1px solid #E0E0E0 !important; }
            
            /* BOTONES AZULES (ORYON) */
            .stButton > button {
                background-color: #0F2489 !important; /* AZUL ORYON */
                color: #FFFFFF !important; 
                border: none !important;
                border-radius: 8px !important; 
                font-weight: 800 !important; 
                width: 100%; 
                padding: 16px;
                font-size: 1.1rem !important;
                transition: all 0.3s ease;
            }
            .stButton > button:hover { 
                background-color: #0a1860 !important; /* AZUL MÁS OSCURO AL PASAR EL RATÓN */
                transform: scale(1.02);
            }
            
            .login-title { color: #050A1F !important; font-size: 2.5rem !important; font-weight: 800 !important; text-align: center; margin: 0 !important; }
            .login-subtitle { color: #666666 !important; font-size: 1.2rem !important; text-align: center; margin-bottom: 2rem !important; }
            .login-card { padding: 2rem; text-align: center; border: 1px solid #eee; border-radius: 10px; margin-top: 10px; }
        """
    elif mode == "dashboard":
        theme_css = """
            .stApp { background-color: #050A1F !important; color: #FFFFFF !important; }
            h1, h2, h3, h4, p, label { color: #FFFFFF !important; }
            .stDataFrame { border: 1px solid #5D5FEF; border-radius: 5px; }
        """
    else: # APP MODE
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
        st.session_state.oryon_auth = False # NUEVA VARIABLE
        st.session_state.data = []
        st.session_state.user_id = generate_id()
        st.session_state.user_data = {}

@st.cache_data
def load_questions():
    filename = 'SATE_v1.csv'  
    if not os.path.exists(filename): return []
    for enc in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
        try:
            with open(filename, encoding=enc, errors='strict') as f:
                data = list(csv.DictReader(f, delimiter=';'))
                if data and 'SECTOR' in data[0]: return data
        except: continue
    return []

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
            if target in st.session_state.octagon: 
                st.session_state.octagon[target] = max(0, min(100, st.session_state.octagon[target] + val))
            elif target in st.session_state.flags: 
                st.session_state.flags[target] = max(0, st.session_state.flags[target] + val)

def calculate_results():
    raw_points = sum(st.session_state.octagon.values())
    avg = 100 * (1 - (1 / (1 + (raw_points / 150.0))))
    raw_friction = sum(st.session_state.flags.values())
    friction = min(100, (raw_friction / 50.0) * 100)
    penalty_factor = friction / 200.0 
    ire = avg * (1 - penalty_factor)
    ire = min(100, max(0, ire))
    avg = min(100, max(0, avg))
    triggers = [k for k, v in st.session_state.flags.items() if v > 10]
    fric_reasons = []
    if friction > 20: fric_reasons.append("Se detectan patrones de comportamiento limitantes bajo presión.")
    if "excitable" in triggers: fric_reasons.append("Riesgo de volatilidad emocional o reactividad.")
    if "cautious" in triggers: fric_reasons.append("Riesgo de parálisis por análisis o aversión al cambio.")
    if "skeptical" in triggers: fric_reasons.append("Dificultad para confiar y delegar.")
    if "arrogant" in triggers: fric_reasons.append("Posible exceso de confianza o subestimación de riesgos.")
    if "mischievous" in triggers: fric_reasons.append("Tendencia a tomar atajos éticos o riesgos imprudentes.")
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
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, showticklabels=False), bgcolor='rgba(0,0,0,0)', tickfont=dict(color='white')), paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'), showlegend=False, margin=dict(l=40, r=40, t=20, b=20), dragmode=False)
    return fig

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
    p.drawString(40, y, f"Candidato: {user.get('name', 'N/A')}"); p.drawString(300, y, f"ID: {st.session_state.user_id}"); y -= 20
    p.drawString(40, y, f"Sector: {user.get('sector', 'N/A')}"); p.drawString(300, y, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}"); y -= 40
    p.setFont("Helvetica-Bold", 12); p.drawString(40, y, f"IRE: {ire}/100"); y -= 30
    p.showPage(); p.save(); buffer.seek(0); return buffer

def render_oryon_dashboard():
    # 2. PANEL DE CONTROL (YA NO PIDE CONTRASEÑA AQUÍ, LA PIDE EN EL LOGIN GENERAL)
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

    # 3. DATOS Y GRÁFICOS
    np.random.seed(42); n_candidatos = 25
    df = pd.DataFrame({
        'ID': [f'CND-{i:03d}' for i in range(1, n_candidatos + 1)],
        'Sector': np.random.choice(['TECH', 'SOCIAL', 'SALUD', 'CONSULTORIA'], n_candidatos),
        'IRE': np.random.randint(35, 98, n_candidatos),
        'Potencial': np.random.randint(45, 95, n_candidatos),
        'Friccion': np.random.randint(5, 75, n_candidatos)
    })

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Candidatos", f"{n_candidatos}")
    k2.metric("IRE Promedio", f"{int(df['IRE'].mean())}/100")
    k3.metric("Riesgo Alto", f"{len(df[df['IRE'] < 50])}", delta_color="inverse")
    k4.metric("Capital Asignable", "450k €")
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
        fig_r.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100]), showticklabels=False), showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white'), height=350)
        st.plotly_chart(fig_r, use_container_width=True)

    st.subheader("Expedientes Detallados")
    def color_ire(val):
        color = '#2ECC71' if val > 75 else '#F1C40F' if val > 50 else '#E74C3C'
        return f'color: {color}; font-weight: bold;'
    st.dataframe(df.style.applymap(color_ire, subset=['IRE']), use_container_width=True)
    
    if st.button("Cerrar Sesión Corporativa"):
        st.session_state.oryon_auth = False
        st.rerun()

def render_header():
    c1, c2 = st.columns([1.5, 6])
    with c1:
        if os.path.exists("logo_blanco.png"): st.image("logo_blanco.png", use_container_width=True)
        elif os.path.exists("logo_original.png"): st.image("logo_original.png", use_container_width=True)
        else: st.warning("Logo no encontrado")
    with c2: st.markdown("""<div style="margin-top: 10px;"><p class="header-title-text">Simulador S.A.P.E.</p><p class="header-sub-text">Sistema de Análisis de la Personalidad Emprendedora</p></div>""", unsafe_allow_html=True)
    st.markdown("---")

# --- 4. EJECUCIÓN PRINCIPAL (LÓGICA FINAL) ---
init_session()

# 1. SI YA HAY SESIÓN DE ORYON -> PANEL
if st.session_state.get('oryon_auth', False):
    render_oryon_dashboard()

# 2. SI YA HAY SESIÓN DE CANDIDATO -> TEST
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
        
        # LÓGICA CORREGIDA AQUÍ
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
            if st.button(row.get('OPCION_A_TXT', 'A'), key=f"A_{step}", use_container_width=True): parse_logic(row.get('OPCION_A_LOGIC')); st.session_state.current_step += 1; st.rerun()
            if st.button(row.get('OPCION_B_TXT', 'B'), key=f"B_{step}", use_container_width=True): parse_logic(row.get('OPCION_B_LOGIC')); st.session_state.current_step += 1; st.rerun()
            if row.get('OPCION_C_TXT') and row.get('OPCION_C_TXT') != "None":
                if st.button(row.get('OPCION_C_TXT', 'C'), key=f"C_{step}", use_container_width=True): parse_logic(row.get('OPCION_C_LOGIC')); st.session_state.current_step += 1; st.rerun()
            if row.get('OPCION_D_TXT') and row.get('OPCION_D_TXT') != "None":
                if st.button(row.get('OPCION_D_TXT', 'D'), key=f"D_{step}", use_container_width=True): parse_logic(row.get('OPCION_D_LOGIC')); st.session_state.current_step += 1; st.rerun()

    else:
        render_header();
        ire, avg, friction, triggers, fric_reasons, delta = calculate_results()
        st.header(f"Informe S.A.P.E. | {st.session_state.user_data['name']}")
        k1, k2, k3 = st.columns(3);
        k1.metric("Índice IRE", f"{ire}/100"); k2.metric("Potencial", f"{avg}/100"); k3.metric("Fricción", friction, delta_color="inverse")
        c_chart, c_desc = st.columns([1, 1])
        with c_chart: st.plotly_chart(radar_chart(), use_container_width=True)
        with c_desc:
            st.markdown("### Diagnóstico");
            st.markdown(f'<div class="diag-text"><p>{get_ire_text(ire)}</p></div>', unsafe_allow_html=True)
            if triggers: st.error("Alertas: Se han detectado patrones de riesgo.")
            else: st.success("Perfil sin patrones de riesgo críticos.")
        pdf = create_pdf_report(ire, avg, friction, triggers, fric_reasons, delta, st.session_state.user_data, st.session_state.octagon)
        st.download_button("📥 DESCARGAR INFORME COMPLETO (PDF)", pdf, file_name=f"Informe_SAPE_{st.session_state.user_id}.pdf", mime="application/pdf", use_container_width=True)
        if st.button("Reiniciar"): st.session_state.clear(); st.rerun()

# 3. SI NO HAY SESIÓN -> PANTALLA DE LOGIN UNIFICADA
else:
    inject_style("login")
    
    # CABECERA LOGIN
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if os.path.exists("logo_original.png"): st.image("logo_original.png", use_container_width=True)
        st.markdown('<p class="login-title">Simulador S.A.P.E.</p>', unsafe_allow_html=True)
        st.markdown('<p class="login-subtitle">Sistema de Análisis de la Personalidad Emprendedora</p>', unsafe_allow_html=True)
        
        # --- SOLUCIÓN: PESTAÑAS (TABS) ---
        tab1, tab2 = st.tabs(["👤 Login Emprendedor/a", "🏢 Login Entidad"])
        
        with tab1:
            st.markdown('<div class="login-card">', unsafe_allow_html=True)
            pwd = st.text_input("Clave de Candidato", type="password", key="pwd_cand")
            if st.button("ACCESO EMPRENDEDOR", use_container_width=True):
                # INTENTA ACCEDER A SECRETS, SI FALLA USA UNA CLAVE POR DEFECTO PARA NO ROMPER LA DEMO
                try:
                    true_pwd = st.secrets["general"]["password"]
                except:
                    true_pwd = "admin" # Clave de emergencia por si no tienes secrets.toml
                
                if pwd == true_pwd: 
                    st.session_state.auth = True; st.rerun()
                else: st.error("Clave incorrecta")
            st.markdown('</div>', unsafe_allow_html=True)
            
        with tab2:
            st.markdown('<div class="login-card">', unsafe_allow_html=True)
            pwd_o = st.text_input("Clave Corporativa (Oryon)", type="password", key="pwd_oryon")
            if st.button("ACCESO ENTIDAD", use_container_width=True):
                if pwd_o == "ORYON2026": 
                    st.session_state.oryon_auth = True; st.rerun()
                else: st.error("Credenciales inválidas")
            st.markdown('</div>', unsafe_allow_html=True)