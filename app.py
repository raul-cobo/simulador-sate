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

# --- GESTIÓN DE DEPENDENCIAS OPCIONALES (PDF) ---
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Audeo | Simulador S.A.P.E.", page_icon="🧬", layout="wide")

# Función de compatibilidad para rerun
def safe_rerun():
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()

# --- 2. GESTIÓN DE ESTILOS ---
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
                color: #0E1117 !important; font-family: 'Helvetica Neue', sans-serif;
            }
            .stTextInput input { border: 1px solid #E0E0E0; border-radius: 8px; padding: 12px; }
            .stButton button { 
                background-color: #000000; color: white; border-radius: 8px; 
                padding: 12px 24px; font-weight: 600; border: none; width: 100%;
            }
            .stButton button:hover { background-color: #333333; color: white; }
        """
    elif mode == "dark":
        theme_css = """
            .stApp { background-color: #0E1117 !important; color: #FAFAFA !important; }
            h1, h2, h3, h4, p { color: #FAFAFA !important; font-family: 'Helvetica Neue', sans-serif; }
            .stButton button { 
                background-color: #262730; color: white; border: 1px solid #41444C; 
                border-radius: 8px; padding: 16px 24px; font-size: 16px; transition: all 0.3s ease;
            }
            .stButton button:hover { 
                border-color: #FAFAFA; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(255,255,255,0.1); 
            }
            .metric-card { background-color: #1F2937; padding: 20px; border-radius: 12px; border: 1px solid #374151; text-align: center; }
        """
    else:
        theme_css = ""

    st.markdown(f"<style>{base_css}{theme_css}</style>", unsafe_allow_html=True)

# --- 3. MAPAS DE DATOS ---

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

# MAPA DE VARIABLES (SUPER-REGULADO V53)
VARIABLE_MAP = {
    # POSITIVOS
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

    # NEGATIVOS (FLAGS)
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

# 3.3 ESTADO INICIAL
if 'traits' not in st.session_state:
    st.session_state.traits = {k: 0 for k in ['achievement', 'risk_propensity', 'innovativeness', 'locus_control', 'self_efficacy', 'autonomy', 'ambiguity_tolerance', 'emotional_stability']}
if 'flags' not in st.session_state:
    st.session_state.flags = {k: 0 for k in ['excitable', 'skeptical', 'cautious', 'reserved', 'passive_aggressive', 'arrogant', 'mischievous', 'melodramatic', 'diligent', 'dependent']}
if 'current_step' not in st.session_state: st.session_state.current_step = 0
if 'user_data' not in st.session_state: st.session_state.user_data = {}
if 'sector_data' not in st.session_state: st.session_state.sector_data = []
if 'history' not in st.session_state: st.session_state.history = []

# --- 4. FUNCIONES DE LÓGICA (CORE) ---

@st.cache_data
def load_questions():
    filename = 'SATE_v1.csv'
    if not os.path.exists(filename):
        st.error(f"Error: No se encuentra el archivo '{filename}'.")
        return []
    
    encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']
    for enc in encodings:
        try:
            with open(filename, encoding=enc, errors='strict') as f:
                data = list(csv.DictReader(f, delimiter=';'))
                if data and 'SECTOR' in data[0]: return data
        except:
            continue
    st.error("Error crítico de codificación del CSV.")
    return []

def parse_logic(logic_str):
    if not logic_str or not isinstance(logic_str, str): return
    parts = logic_str.split('|')
    for part in parts:
        try:
            tokens = part.strip().split()
            if len(tokens) < 2: continue
            key_raw = tokens[0].lower().strip()
            val = int(tokens[1])
            target_key = VARIABLE_MAP.get(key_raw)
            if target_key:
                if target_key in st.session_state.traits:
                    st.session_state.traits[target_key] += val
                elif target_key in st.session_state.flags:
                    st.session_state.flags[target_key] += val
        except:
            continue

# CÁLCULO DE RESULTADOS LOGARÍTMICO (V54)
def calculate_results():
    # 1. POTENCIAL (Curva Logística)
    raw_points = sum(st.session_state.traits.values())
    # Esta fórmula hace que sea fácil llegar a 50, pero muy difícil llegar a 100
    avg = 100 * (1 - (1 / (1 + (raw_points / 150.0))))
    
    # 2. FRICCIÓN (Solo Flags Reales)
    raw_friction = sum(st.session_state.flags.values())
    friction = min(100, (raw_friction / 50.0) * 100)
    
    # 3. IRE FINAL
    penalty_factor = friction / 200.0 
    ire = avg * (1 - penalty_factor)
    
    triggers = [k for k, v in st.session_state.flags.items() if v > 10]
    
    # Explicaciones para PDF
    fric_reasons = []
    if friction > 20: fric_reasons.append("Patrones de comportamiento limitantes bajo estrés.")
    if "excitable" in triggers: fric_reasons.append("Volatilidad emocional.")
    if "cautious" in triggers: fric_reasons.append("Parálisis por análisis.")
    if "arrogant" in triggers: fric_reasons.append("Exceso de confianza.")
    
    return round(ire, 2), round(avg, 2), round(friction, 2), triggers, fric_reasons, 0

def get_ire_text(score):
    if score >= 75: return "Nivel ÉLITE: Alta viabilidad."
    if score >= 60: return "Nivel SÓLIDO: Buen potencial."
    if score >= 40: return "Nivel MEDIO: Riesgos operativos."
    return "Nivel CRÍTICO: Alta probabilidad de bloqueo."

# --- 5. INTERFAZ GRÁFICA ---

def render_header():
    c1, c2 = st.columns([1, 6])
    with c1:
        # LOGO RESTAURADO: Busca logo.png, si no usa emoji
        if os.path.exists("logo.png"):
            st.image("logo.png", width=60)
        else:
            st.markdown("### 🧬")
    with c2: st.markdown("**Simulador S.A.P.E.** | Sistema de Análisis")
    st.divider()

# FASE 1: LOGIN (DISEÑO RESTAURADO)
if st.session_state.current_step == 0:
    inject_style("login")
    
    # Logo en Login
    c_logo, c_title = st.columns([1, 5])
    with c_logo:
        if os.path.exists("logo.png"): st.image("logo.png", width=80)
    with c_title:
        st.markdown("<div style='margin-top: 20px;'><h1>Audeo</h1><p>Sistema de Inteligencia Emprendedora</p></div>", unsafe_allow_html=True)
    
    st.divider()
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        name = st.text_input("Nombre / ID de Candidato", placeholder="Ej: Juan Pérez")
        if st.button("INICIAR EVALUACIÓN"):
            if name:
                st.session_state.user_data = {'name': name, 'id': ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}
                st.session_state.current_step = 1
                safe_rerun()

# FASE 2: SECTOR
elif st.session_state.current_step == 1:
    inject_style("dark")
    render_header()
    st.markdown("### Selecciona el Sector del Proyecto")
    
    def go_sector(sec_name):
        code = SECTOR_MAP.get(sec_name)
        raw_data = load_questions()
        st.session_state.sector_data = [row for row in raw_data if row['SECTOR'] == code]
        try: st.session_state.sector_data.sort(key=lambda x: int(x['MES']))
        except: pass
        
        if not st.session_state.sector_data:
            st.error(f"No hay preguntas para {code}.")
        else:
            st.session_state.current_step = 2
            safe_rerun()

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

# FASE 3: PREGUNTAS
elif st.session_state.current_step == 2:
    inject_style("dark")
    render_header()
    
    q_idx = len(st.session_state.history)
    if q_idx >= len(st.session_state.sector_data):
        st.session_state.current_step = 3
        safe_rerun()
    
    row = st.session_state.sector_data[q_idx]
    st.progress((q_idx + 1) / len(st.session_state.sector_data))
    st.caption(f"Mes {row['MES']} | {row['TITULO']}")
    st.markdown(f"#### {row['NARRATIVA']}")
    
    def next_q(opt, logic, txt):
        parse_logic(logic)
        st.session_state.history.append({'opcion': opt})
        safe_rerun()

    if row.get('OPCION_A_TXT'):
        if st.button(f"A) {row['OPCION_A_TXT']}", use_container_width=True): next_q('A', row.get('OPCION_A_LOGIC'), row.get('OPCION_A_TXT'))
    if row.get('OPCION_B_TXT'):
        if st.button(f"B) {row['OPCION_B_TXT']}", use_container_width=True): next_q('B', row.get('OPCION_B_LOGIC'), row.get('OPCION_B_TXT'))
    if row.get('OPCION_C_TXT'):
        if st.button(f"C) {row['OPCION_C_TXT']}", use_container_width=True): next_q('C', row.get('OPCION_C_LOGIC'), row.get('OPCION_C_TXT'))
    if row.get('OPCION_D_TXT'):
        if st.button(f"D) {row['OPCION_D_TXT']}", use_container_width=True): next_q('D', row.get('OPCION_D_LOGIC'), row.get('OPCION_D_TXT'))

# FASE 4: RESULTADOS
elif st.session_state.current_step == 3:
    inject_style("dark")
    render_header()
    
    ire, avg, friction, triggers, fric_reasons, _ = calculate_results()
    
    st.header(f"Informe S.A.P.E. | {st.session_state.user_data['name']}")
    k1, k2, k3 = st.columns(3)
    k1.metric("Índice IRE", f"{ire}/100")
    k2.metric("Potencial", f"{avg}/100")
    k3.metric("Fricción", f"{friction}/100", delta_color="inverse")
    
    # Radar Chart
    vals = [min(10, (v / 50.0) * 10) for v in st.session_state.traits.values()]
    fig = go.Figure(data=go.Scatterpolar(
        r=vals, theta=[k.replace('_', ' ').title() for k in st.session_state.traits.keys()],
        fill='toself', name='Perfil'
    ))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])), showlegend=False, 
                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
    
    c_chart, c_desc = st.columns([1, 1])
    with c_chart: st.plotly_chart(fig, use_container_width=True)
    with c_desc:
        st.markdown("### Diagnóstico")
        st.info(get_ire_text(ire))
        if triggers: st.warning(f"**Alertas:** {', '.join([t.title() for t in triggers])}")
    
    if PDF_AVAILABLE:
        def create_pdf_file():
            b = io.BytesIO()
            c = canvas.Canvas(b, pagesize=A4)
            c.drawString(50, 800, f"Audeo - Informe S.A.P.E.")
            c.drawString(50, 780, f"Candidato: {st.session_state.user_data['name']}")
            c.drawString(50, 760, f"IRE: {ire} | Potencial: {avg} | Fricción: {friction}")
            if triggers: c.drawString(50, 740, f"Riesgos: {', '.join(triggers)}")
            
            # Dibujar gráfico simple (barras simuladas)
            y = 700
            for k, v in st.session_state.traits.items():
                c.drawString(50, y, f"{k.title()}: {int(v)}")
                y -= 15
                
            c.save()
            b.seek(0)
            return b
            
        st.download_button("Descargar Informe PDF", data=create_pdf_file(), file_name="Informe_SAPE.pdf", mime="application/pdf")
        
    if st.button("Reiniciar Evaluación"):
        st.session_state.clear()
        safe_rerun()