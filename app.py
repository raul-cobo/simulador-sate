import streamlit as st
import csv
import os
import random
import string
import io
import textwrap
from datetime import datetime
import plotly.graph_objects as go
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Audeo | Simulador S.A.P.E.", page_icon="🧬", layout="wide")

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
            h1, h2, h3, h4, p { color: #FAFAFA !important; }
            .stButton button { 
                background-color: #262730; color: white; border: 1px solid #41444C; 
                border-radius: 8px; transition: all 0.3s ease;
            }
            .stButton button:hover { border-color: #FAFAFA; transform: translateY(-2px); }
            .metric-card { background-color: #1F2937; padding: 20px; border-radius: 12px; border: 1px solid #374151; }
        """
    else:
        theme_css = ""

    st.markdown(f"<style>{base_css}{theme_css}</style>", unsafe_allow_html=True)

# --- 3. MAPAS DE DATOS (SUPER-REGULADOS) ---

# 3.1 MAPA DE SECTORES ACTUALIZADO
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

# 3.2 MAPA DE VARIABLES COMPLETO (CORRIGE EL TECHO DE CRISTAL)
VARIABLE_MAP = {
    # --- DIMENSIONES POSITIVAS (SUMAN POTENCIAL) ---
    
    # 1. ACHIEVEMENT
    "achievement": "achievement", "logro": "achievement",
    "pragmatism": "achievement", "focus": "achievement", 
    "discipline": "achievement", "tenacity": "achievement",
    "persistence": "achievement", "results": "achievement",
    "efficiency": "achievement", "profit": "achievement",
    "growth": "achievement", "scale": "achievement",
    "ambition": "achievement", "cost_saving": "achievement",
    "financial_focus": "achievement", "valuation": "achievement",
    "business_acumen": "achievement", "business": "achievement",

    # 2. RISK PROPENSITY
    "risk_propensity": "risk_propensity", "riesgo": "risk_propensity",
    "risk": "risk_propensity", "courage": "risk_propensity",
    "audacity": "risk_propensity", "action": "risk_propensity",
    "speed": "risk_propensity", "investment": "risk_propensity",
    "debt": "risk_propensity", "financial_risk": "risk_propensity",
    "boldness": "risk_propensity", "bravery": "risk_propensity",
    "experimentation": "risk_propensity",

    # 3. INNOVATIVENESS
    "innovativeness": "innovativeness", "innovacion": "innovativeness",
    "strategy": "innovativeness", "vision": "innovativeness",
    "creativity": "innovativeness", "adaptability": "innovativeness",
    "flexibility": "innovativeness", "resourcefulness": "innovativeness",
    "curiosity": "innovativeness", "open_minded": "innovativeness",
    "learning": "innovativeness", "differentiation": "innovativeness",
    "pivot": "innovativeness", "change": "innovativeness",
    "reframing": "innovativeness", "forward": "innovativeness",

    # 4. LOCUS OF CONTROL
    "locus_control": "locus_control", "locus": "locus_control",
    "responsibility": "locus_control", "ownership": "locus_control",
    "realism": "locus_control", "accountability": "locus_control",
    "problem_solving": "locus_control", "decision_making": "locus_control",
    "internal_locus": "locus_control", "proactivity": "locus_control",
    "self_awareness": "locus_control", "analysis": "locus_control",

    # 5. SELF-EFFICACY
    "self_efficacy": "self_efficacy", "autoeficacia": "self_efficacy",
    "confidence": "self_efficacy", "assertiveness": "self_efficacy",
    "leadership": "self_efficacy", "negotiation": "self_efficacy",
    "persuasion": "self_efficacy", "influence": "self_efficacy",
    "sales": "self_efficacy", "communication": "self_efficacy",
    "management": "self_efficacy", "networking": "self_efficacy",
    "pricing_power": "self_efficacy", "confrontation": "self_efficacy",
    "collaboration": "self_efficacy", "team_focus": "self_efficacy",
    "mentorship": "self_efficacy", "delegation": "self_efficacy",

    # 6. AUTONOMY
    "autonomy": "autonomy", "autonomia": "autonomy",
    "independence": "autonomy", "freedom": "autonomy",
    "boundaries": "autonomy", "sovereignty": "autonomy",
    "identity": "autonomy", "lifestyle": "autonomy",
    "refusal": "autonomy", "detachment": "autonomy",

    # 7. AMBIGUITY TOLERANCE
    "ambiguity_tolerance": "ambiguity_tolerance", "tolerancia": "ambiguity_tolerance",
    "patience": "ambiguity_tolerance", "resilience": "ambiguity_tolerance",
    "calm": "ambiguity_tolerance", "stoicism": "ambiguity_tolerance",
    "hope": "ambiguity_tolerance", "optimism": "ambiguity_tolerance",
    "acceptance": "ambiguity_tolerance", "endurance": "ambiguity_tolerance",
    "trust": "ambiguity_tolerance", "imaginative": "ambiguity_tolerance",

    # 8. EMOTIONAL STABILITY
    "emotional_stability": "emotional_stability", "estabilidad": "emotional_stability",
    "integrity": "emotional_stability", "ethics": "emotional_stability",
    "values": "emotional_stability", "justice": "emotional_stability",
    "fairness": "emotional_stability", "transparency": "emotional_stability",
    "honesty": "emotional_stability", "humility": "emotional_stability",
    "empathy": "emotional_stability", "humanity": "emotional_stability",
    "culture": "emotional_stability", "loyalty": "emotional_stability",
    "balance": "emotional_stability", "self_care": "emotional_stability",
    "coherence": "emotional_stability", "respect": "emotional_stability",

    # --- FLAGS DE FRICCIÓN (RESTAN PUNTOS) ---

    # A. EXCITABLE
    "excitable": "excitable", "aggression": "excitable",
    "violence": "excitable", "anger": "excitable",
    "conflict": "excitable", "reaction": "excitable",
    "vengeance": "excitable", "impulsiveness": "excitable",
    "drama": "excitable",

    # B. SKEPTICAL
    "skeptical": "skeptical", "skepticism": "skeptical",
    "cynicism": "skeptical", "distrust": "skeptical",
    "suspicion": "skeptical", "hostility": "skeptical",

    # C. CAUTIOUS
    "cautious": "cautious", "caution": "cautious",
    "fear": "cautious", "anxiety": "cautious",
    "avoidance": "cautious", "prudence": "cautious",
    "security": "cautious", "safety": "cautious",
    "risk_aversion": "cautious", "conservatism": "cautious",
    "hesitation": "cautious", "paralysis": "cautious",
    "trust_risk": "cautious", "delay": "cautious",

    # D. RESERVED
    "reserved": "reserved", "introversion": "reserved",
    "isolation": "reserved", "secrecy": "reserved",
    "secretive": "reserved", "distance": "reserved",

    # E. PASSIVE AGGRESSIVE
    "passive_aggressive": "passive_aggressive",
    "resentment": "passive_aggressive", "obstruction": "passive_aggressive",
    "stubbornness": "passive_aggressive", "resistance": "passive_aggressive",

    # F. ARROGANT
    "arrogant": "arrogant", "arrogance": "arrogant",
    "ego": "arrogant", "narcissism": "arrogant",
    "superiority": "arrogant", "elitism": "arrogant",
    "image": "arrogant", "spectacle": "arrogant",
    "vanity": "arrogant", "bluff": "arrogant",
    "pride": "arrogant", "class": "arrogant",

    # G. MISCHIEVOUS
    "mischievous": "mischievous", "cunning": "mischievous",
    "deceit": "mischievous", "manipulation": "mischievous",
    "opportunist": "mischievous", "corruption": "mischievous",
    "exploitation": "mischievous", "greed": "mischievous",
    "illegal": "mischievous", "machiavellian": "mischievous",
    "artificial": "mischievous", "tactics": "mischievous",

    # H. MELODRAMATIC
    "melodramatic": "melodramatic", "victimism": "melodramatic",
    "complaint": "melodramatic", "fragility": "melodramatic",
    "delusion": "melodramatic", "attention_seeking": "melodramatic",

    # I. DILIGENT
    "diligent": "diligent", "perfectionism": "diligent",
    "micromanagement": "diligent", "rigidity": "diligent",
    "obsession": "diligent", "bureaucracy": "diligent",
    "complexity": "diligent",

    # J. DEPENDENT
    "dependent": "dependent", "dependency": "dependent",
    "submission": "dependent", "pleaser": "dependent",
    "conformity": "dependent", "obedience": "dependent",
    "external_validation": "dependent", "reassurance": "dependent",
    "imitation": "dependent", "external_locus": "dependent",
    "weakness": "dependent", "surrender": "dependent"
}

# --- 4. CARGA DE DATOS (ROBUSTA PARA ENCODING) ---
@st.cache_data
def load_questions():
    filename = 'SATE_v1.csv'  # Nombre del archivo en GitHub
    
    if not os.path.exists(filename):
        st.error(f"Error: No se encuentra el archivo '{filename}'. Asegúrate de haberlo subido a GitHub con ese nombre.")
        return []
    
    # 1. Intentar primero con UTF-8-SIG (Excel moderno)
    try:
        with open(filename, encoding='utf-8-sig', errors='strict') as f:
            data = list(csv.DictReader(f, delimiter=';'))
            if data and 'SECTOR' in data[0]: return data
    except UnicodeDecodeError:
        pass 

    # 2. Intentar con UTF-8
    try:
        with open(filename, encoding='utf-8', errors='strict') as f:
            data = list(csv.DictReader(f, delimiter=';'))
            if data and 'SECTOR' in data[0]: return data
    except UnicodeDecodeError:
        pass

    # 3. Intentar con Latin-1 (Windows Europa)
    try:
        with open(filename, encoding='latin-1', errors='strict') as f:
            data = list(csv.DictReader(f, delimiter=';'))
            if data and 'SECTOR' in data[0]: return data
    except UnicodeDecodeError:
        pass

    # 4. Último recurso: CP1252
    try:
        with open(filename, encoding='cp1252', errors='replace') as f:
            data = list(csv.DictReader(f, delimiter=';'))
            return data
    except Exception as e:
        st.error(f"Error crítico de codificación: {e}")
        return []

# --- 5. LOGICA DEL SIMULADOR ---
if 'traits' not in st.session_state:
    st.session_state.traits = {k: 0 for k in ['achievement', 'risk_propensity', 'innovativeness', 'locus_control', 'self_efficacy', 'autonomy', 'ambiguity_tolerance', 'emotional_stability']}
if 'flags' not in st.session_state:
    st.session_state.flags = {k: 0 for k in ['excitable', 'skeptical', 'cautious', 'reserved', 'passive_aggressive', 'arrogant', 'mischievous', 'melodramatic', 'diligent', 'dependent']}
if 'current_step' not in st.session_state: st.session_state.current_step = 0
if 'user_data' not in st.session_state: st.session_state.user_data = {}
if 'sector_data' not in st.session_state: st.session_state.sector_data = []
if 'history' not in st.session_state: st.session_state.history = []

def parse_logic(logic_str):
    if not logic_str or not isinstance(logic_str, str): return
    parts = logic_str.split('|')
    for part in parts:
        try:
            # Separamos por espacios: "palabra valor"
            tokens = part.strip().split()
            if len(tokens) < 2: continue
            
            # La clave es la primera palabra (en minúsculas)
            key_raw = tokens[0].lower().strip()
            # El valor es la segunda
            val = int(tokens[1])
            
            # Buscamos en el mapa
            target_key = VARIABLE_MAP.get(key_raw)
            
            if target_key:
                if target_key in st.session_state.traits:
                    st.session_state.traits[target_key] += val
                elif target_key in st.session_state.flags:
                    st.session_state.flags[target_key] += val
        except:
            continue

def calculate_results():
    # Promedio de rasgos positivos (0-100)
    # Suponemos un máximo teórico por rasgo de ~40-50 puntos acumulados, normalizamos.
    # Para simplificar y evitar techos bajos, usamos la suma directa suavizada.
    
    raw_avg = sum(st.session_state.traits.values()) / 8.0
    # Ajuste de escala: Si el usuario saca 30 puntos de media, es un 60/100 aprox.
    avg = min(100, max(0, raw_avg * 1.5)) 
    
    # Fricción (Flags)
    raw_friction = sum(st.session_state.flags.values())
    friction = min(100, max(0, raw_friction)) # La fricción resta directamente
    
    # IRE Final
    ire = avg - (friction * 0.5) # La fricción penaliza la mitad de su valor
    ire = min(100, max(0, ire))
    
    # Textos de diagnóstico
    triggers = [k for k, v in st.session_state.flags.items() if v > 15]
    return round(ire, 2), round(avg, 2), round(friction, 2), triggers, [], 0

def get_ire_text(score):
    if score >= 80: return "Nivel ÉLITE: Alta viabilidad y resiliencia."
    if score >= 60: return "Nivel SÓLIDO: Buen potencial, requiere ajustes menores."
    if score >= 40: return "Nivel MEDIO: Riesgos operativos detectados."
    return "Nivel CRÍTICO: Alta probabilidad de bloqueo o burnout."

# --- 6. INTERFAZ DE USUARIO ---
def render_header():
    c1, c2 = st.columns([1, 6])
    with c1: st.markdown("### 🧬")
    with c2: st.markdown("**Simulador S.A.P.E.** | Sistema de Análisis de la Personalidad Emprendedora")
    st.divider()

# FASE 1: LOGIN
if st.session_state.current_step == 0:
    inject_style("login")
    st.markdown("<div style='text-align: center; margin-top: 50px;'><h1>Audeo</h1><p>Sistema de Inteligencia Emprendedora</p></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        name = st.text_input("Nombre / ID de Candidato", placeholder="Ej: Juan Pérez")
        email = st.text_input("Email Corporativo", placeholder="juan@empresa.com")
        if st.button("INICIAR EVALUACIÓN"):
            if name and email:
                st.session_state.user_data = {'name': name, 'email': email, 'id': ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}
                st.session_state.current_step = 1
                st.rerun()

# FASE 2: SELECTOR DE SECTOR (BOTONES ACTUALIZADOS)
elif st.session_state.current_step == 1:
    inject_style("dark")
    render_header()
    st.markdown("### Selecciona el Sector del Proyecto")
    
    def go_sector(sec_name):
        code = SECTOR_MAP.get(sec_name)
        raw_data = load_questions()
        # Filtramos por sector
        st.session_state.sector_data = [row for row in raw_data if row['SECTOR'] == code]
        # Ordenamos por mes (asumiendo que viene en orden, pero por si acaso)
        try:
            st.session_state.sector_data.sort(key=lambda x: int(x['MES']))
        except:
            pass # Si falla el orden, usamos el del CSV
            
        st.session_state.current_step = 2
        st.rerun()

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

# FASE 3: PREGUNTAS (LOOP)
elif st.session_state.current_step == 2:
    inject_style("dark")
    render_header()
    
    # Índice de pregunta actual (empezamos en 0)
    # Usamos len(history) para saber por dónde vamos
    q_idx = len(st.session_state.history)
    
    if q_idx >= len(st.session_state.sector_data):
        st.session_state.current_step = 3
        st.rerun()
    
    row = st.session_state.sector_data[q_idx]
    
    # Barra de progreso
    progress = (q_idx + 1) / len(st.session_state.sector_data)
    st.progress(progress)
    
    st.caption(f"Mes {row['MES']} | {row['TITULO']}")
    st.markdown(f"#### {row['NARRATIVA']}")
    
    def next_q(opt_letter, logic_str, text_str):
        parse_logic(logic_str)
        st.session_state.history.append({
            'mes': row['MES'], 'titulo': row['TITULO'], 'opcion': opt_letter, 'texto': text_str
        })
        st.rerun()

    # Botones de respuesta
    st.write("")
    if row.get('OPCION_A_TXT') and row.get('OPCION_A_TXT') != "None":
        if st.button(f"A) {row['OPCION_A_TXT']}", use_container_width=True): 
            next_q('A', row.get('OPCION_A_LOGIC'), row.get('OPCION_A_TXT'))
            
    if row.get('OPCION_B_TXT') and row.get('OPCION_B_TXT') != "None":
        if st.button(f"B) {row['OPCION_B_TXT']}", use_container_width=True): 
            next_q('B', row.get('OPCION_B_LOGIC'), row.get('OPCION_B_TXT'))
            
    if row.get('OPCION_C_TXT') and row.get('OPCION_C_TXT') != "None":
        if st.button(f"C) {row['OPCION_C_TXT']}", use_container_width=True): 
            next_q('C', row.get('OPCION_C_LOGIC'), row.get('OPCION_C_TXT'))
            
    if row.get('OPCION_D_TXT') and row.get('OPCION_D_TXT') != "None":
        if st.button(f"D) {row['OPCION_D_TXT']}", use_container_width=True): 
            next_q('D', row.get('OPCION_D_LOGIC'), row.get('OPCION_D_TXT'))

# FASE 4: RESULTADOS
elif st.session_state.current_step == 3:
    inject_style("dark")
    render_header()
    
    ire, avg, friction, triggers, _, _ = calculate_results()
    
    st.header(f"Informe S.A.P.E. | {st.session_state.user_data['name']}")
    
    k1, k2, k3 = st.columns(3)
    k1.metric("Índice IRE", f"{ire}/100")
    k2.metric("Potencial", f"{avg}/100")
    k3.metric("Fricción", f"{friction}/100", delta_color="inverse")
    
    # Radar Chart
    categories = list(st.session_state.traits.keys())
    values = list(st.session_state.traits.values())
    # Normalizamos para el gráfico (simple visualización)
    values_norm = [min(10, v / 3) for v in values] # Escala aprox 0-10
    
    fig = go.Figure(data=go.Scatterpolar(
      r=values_norm,
      theta=[k.replace('_', ' ').title() for k in categories],
      fill='toself',
      name='Perfil'
    ))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])), showlegend=False, 
                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                      font=dict(color='white'))
    
    c_chart, c_desc = st.columns([1, 1])
    with c_chart: st.plotly_chart(fig, use_container_width=True)
    with c_desc:
        st.markdown("### Diagnóstico")
        st.info(get_ire_text(ire))
        if triggers:
            st.warning(f"**Alertas de Fricción detectadas:** {', '.join([t.title() for t in triggers])}")
        else:
            st.success("No se han detectado patrones de riesgo críticos.")

    # Generación de PDF
    def create_pdf():
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        # Cabecera
        c.setFont("Helvetica-Bold", 24)
        c.drawString(50, height - 50, "Informe S.A.P.E.")
        c.setFont("Helvetica", 12)
        c.drawString(50, height - 70, f"Candidato: {st.session_state.user_data['name']}")
        c.drawString(50, height - 85, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}")
        
        # Métricas
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 130, f"IRE: {ire}/100")
        c.drawString(200, height - 130, f"Potencial: {avg}")
        c.drawString(350, height - 130, f"Fricción: {friction}")
        
        # Diagnóstico texto
        c.setFont("Helvetica", 12)
        text_y = height - 180
        c.drawString(50, text_y, f"Diagnóstico: {get_ire_text(ire)}")
        
        if triggers:
            c.setFillColorRGB(0.8, 0, 0)
            c.drawString(50, text_y - 20, f"Riesgos: {', '.join(triggers)}")
            c.setFillColorRGB(0, 0, 0)
        
        c.showPage()
        c.save()
        buffer.seek(0)
        return buffer

    if st.button("Descargar Informe PDF"):
        pdf_bytes = create_pdf()
        st.download_button(label="Guardar PDF", data=pdf_bytes, file_name="Informe_SAPE.pdf", mime="application/pdf")
        
    if st.button("Reiniciar Evaluación"):
        st.session_state.clear()
        st.rerun()