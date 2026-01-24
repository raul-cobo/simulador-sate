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
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Audeo | Simulador S.A.P.E.", page_icon="🧬", layout="wide")

# --- 2. GESTIÓN DE ESTILOS (VERSIÓN 21: SIN ERRORES DE SINTAXIS) ---
def inject_style(mode):
    """
    Genera un ÚNICO bloque <style> para evitar errores visuales.
    """
    
    # CSS BASE (Común: Quitar header nativo y reducir márgenes al mínimo)
    base_css = """
        header, [data-testid="stHeader"], .stAppHeader { display: none !important; }
        div[data-testid="stDecoration"] { display: none !important; }
        footer { display: none !important; }
        /* MARGEN SUPERIOR MÍNIMO */
        .main .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; max-width: 90% !important; }
    """
    
    if mode == "login":
        # --- MODO LOGIN (BLANCO) ---
        theme_css = """
            .stApp { background-color: #FFFFFF !important; color: #000000 !important; }
            h1, h2, h3, h4, p, label, div[data-testid="stMarkdownContainer"] p { 
                color: #0E1117 !important; font-family: 'Helvetica', sans-serif;
            }
            .stTextInput input {
                background-color: #F8F9FA !important;
                color: #000000 !important;
                border: 1px solid #E0E0E0 !important;
            }
            
            /* BOTÓN LOGIN CORREGIDO (Visible) */
            .stButton > button {
                background-color: #050A1F !important;
                color: #FFFFFF !important;
                border: 1px solid #050A1F !important;
                border-radius: 8px !important;
                font-weight: bold !important;
                width: 100%;
                padding: 0.5rem 1rem;
            }
            .stButton > button:hover { 
                background-color: #5D5FEF !important; 
                border-color: #5D5FEF !important;
            }
            /* Forzar color blanco en texto del botón */
            .stButton > button p { color: #FFFFFF !important; }
            
            .login-title {
                color: #050A1F !important;
                font-size: 2rem !important;
                font-weight: 800 !important;
                text-align: center;
                margin: 0 !important;
            }
            .login-subtitle {
                color: #666666 !important;
                font-size: 1rem !important;
                text-align: center;
                margin-bottom: 2rem !important;
            }
            .login-card { padding: 1rem; text-align: center; }
        """
    else:
        # --- MODO APP INTERNA (NAVY) ---
        theme_css = """
            .stApp { background-color: #050A1F !important; color: #FFFFFF !important; }
            h1, h2, h3, h4, p, label, span, div[data-testid="stMarkdownContainer"] p { 
                color: #FFFFFF !important; 
            }
            .stTextInput input, .stNumberInput input, .stSelectbox > div > div {
                background-color: #0F1629 !important;
                color: #FFFFFF !important;
                border: 1px solid #5D5FEF !important;
            }
            div[role="listbox"] div { background-color: #0F1629 !important; color: white !important; }
            .stCheckbox label p { color: white !important; }
            
            /* Botones Generales */
            .stButton > button {
                background-color: #1A202C !important;
                color: white !important;
                border: 1px solid #5D5FEF !important;
                border-radius: 8px;
            }
            .stButton > button:hover { border-color: white !important; background-color: #5D5FEF !important; }
            
            /* Botones Sector (Gigantes) */
            div[data-testid="column"] button {
                 height: 140px !important;
                 width: 100% !important;
                 background-color: #0F1629 !important;
                 border: 2px solid #2D3748 !important;
                 color: white !important;
                 font-size: 1.1rem !important;
                 border-radius: 15px !important;
                 white-space: normal !important;
                 display: flex;
                 align-items: center;
                 justify-content: center;
                 margin-bottom: 10px !important;
            }
            div[data-testid="column"] button:hover { border-color: #5D5FEF !important; transform: scale(1.02); }
            
            /* Header Interno */
            .header-title-text { font-size: 1.8rem !important; font-weight: bold !important; color: white !important; margin: 0; line-height: 1.1; }
            .header-sub-text { font-size: 0.9rem !important; color: #5D5FEF !important; margin: 0; }
            
            .diag-text { background-color: #0F1629; padding: 15px; border-radius: 8px; border-left: 4px solid #5D5FEF; }
            .stDownloadButton > button { background-color: #5D5FEF !important; color: white !important; border: none !important; font-weight: bold !important; }
        """
    
    # UNIFICACIÓN DE ESTILOS AL FINAL DE LA FUNCIÓN
    st.markdown(f"<style>{base_css}\n{theme_css}</style>", unsafe_allow_html=True)

# --- 3. VARIABLES Y LÓGICA ---
LABELS_ES = { "achievement": "Necesidad de Logro", "risk_propensity": "Propensión al Riesgo", "innovativeness": "Innovatividad", "locus_control": "Locus de Control Interno", "self_efficacy": "Autoeficacia", "autonomy": "Autonomía", "ambiguity_tolerance": "Tol. Ambigüedad", "emotional_stability": "Estabilidad Emocional" }
NARRATIVES_DB = {
    "emotional_stability": { "high": "Puntuación muy alta. Capacidad absoluta para mantener la regulación emocional bajo presión.", "low": "Nivel bajo. Vulnerabilidad ante la presión sostenida." },
    "autonomy": { "high": "Puntuación muy alta. Fuerte independencia operativa.", "low": "Dependencia operativa. Requiere validación constante." },
    "achievement": { "high": "Nivel alto. Clara orientación a resultados.", "low": "Baja orientación a resultados." },
    "risk_propensity": { "high": "Alta tolerancia al riesgo.", "low": "Perfil conservador. Prioriza la seguridad." },
    "ambiguity_tolerance": { "high": "Alta capacidad de gestión del caos.", "low": "Nivel medio-bajo. Requiere información estructurada." },
    "innovativeness": { "high": "Perfil disruptivo.", "low": "Nivel medio. Tiende a la optimización de procesos." },
    "locus_control": { "high": "Locus Interno fuerte.", "low": "Tendencia a atribuir resultados a factores externos." },
    "self_efficacy": { "high": "Confianza sólida en las propias capacidades.", "low": "Dudas sobre la propia capacidad." }
}
VARIABLE_MAP = { "achievement": "achievement", "logro": "achievement", "risk_propensity": "risk_propensity", "riesgo": "risk_propensity", "innovativeness": "innovativeness", "innovacion": "innovativeness", "locus_control": "locus_control", "locus": "locus_control", "self_efficacy": "self_efficacy", "autoeficacia": "self_efficacy", "collaboration": "self_efficacy", "autonomy": "autonomy", "autonomia": "autonomy", "ambiguity_tolerance": "ambiguity_tolerance", "tolerancia": "ambiguity_tolerance", "imaginative": "ambiguity_tolerance", "emotional_stability": "emotional_stability", "estabilidad": "emotional_stability", "excitable": "excitable", "skeptical": "skeptical", "cautious": "cautious", "reserved": "reserved", "passive_aggressive": "passive_aggressive", "arrogant": "arrogant", "mischievous": "mischievous", "melodramatic": "melodramatic", "diligent": "diligent", "dependent": "dependent" }
SECTOR_MAP = { "Startup Tecnológica (Scalable)": "TECH", "Consultoría / Servicios Profesionales": "CONSULTORIA", "Pequeña y Mediana Empresa (PYME)": "PYME", "Hostelería y Restauración": "HOSTELERIA", "Autoempleo / Freelance": "AUTOEMPLEO", "Emprendimiento Social": "SOCIAL", "Intraemprendimiento": "INTRA", "Salud": "SALUD" }

def generate_id(): return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
def init_session():
    if 'octagon' not in st.session_state:
        st.session_state.octagon = {k: 50 for k in LABELS_ES.keys()}
        st.session_state.flags = {k: 0 for k in ["excitable", "skeptical", "cautious", "reserved", "passive_aggressive", "arrogant", "mischievous", "melodramatic", "diligent", "dependent"]}
        st.session_state.current_step = 0; st.session_state.finished = False; st.session_state.started = False; st.session_state.data_verified = False; st.session_state.data = []; st.session_state.user_id = generate_id(); st.session_state.user_data = {}

def load_questions():
    try:
        filename = 'SATE_v1.csv'
        if not os.path.exists(filename): return []
        with open(filename, encoding='utf-8-sig') as f: return list(csv.DictReader(f, delimiter=';'))
    except: return []

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
            if target in st.session_state.octagon: st.session_state.octagon[target] = max(0, min(100, st.session_state.octagon[target] + val))
            elif target in st.session_state.flags: st.session_state.flags[target] = max(0, st.session_state.flags[target] + val)

def calculate_results():
    o, f = st.session_state.octagon, st.session_state.flags
    avg = sum(o.values()) / 8
    friction = sum(f.values()) * 0.5
    triggers = []
    friction_reasons = []
    if f["cautious"] > 10 or f["diligent"] > 10: friction_reasons.append("Prudencia Administrativa: Prioriza seguridad jurídica.")
    if f["dependent"] > 10 or f["skeptical"] > 10: friction_reasons.append("Exceso de Validación: Busca confirmación externa.")
    if f["arrogant"] > 20: friction_reasons.append("Rigidez Cognitiva: Dificultad para pivotar.")
    if f["mischievous"] > 25: triggers.append("Riesgo de Desalineamiento Normativo")
    if f["arrogant"] > 25: triggers.append("Estilo Dominante")
    if f["passive_aggressive"] > 20: triggers.append("Fricción Relacional")
    if o["achievement"] > 85 and o["emotional_stability"] < 40: triggers.append("Riesgo de Burnout")
    if o["risk_propensity"] > 85 and f["cautious"] < 10: triggers.append("Perfil de Riesgo Desmedido")
    ire = max(0, min(100, avg - (friction * 0.8) - (len(triggers) * 3)))
    delta = round(avg - ire, 2)
    return round(ire, 2), round(avg, 2), round(friction, 2), triggers, friction_reasons, delta

# --- PDF GENERATOR (COMPLETO) ---
def draw_wrapped_text(c, text, x, y, max_width, font_name, font_size, line_spacing=12):
    c.setFont(font_name, font_size)
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        width = c.stringWidth(" ".join(current_line), font_name, font_size)
        if width > max_width: current_line.pop(); lines.append(" ".join(current_line)); current_line = [word]
    lines.append(" ".join(current_line))
    for line in lines: c.drawString(x, y, line); y -= line_spacing
    return y 

def draw_pdf_header(p, w, h):
    p.setFillColorRGB(0.02, 0.04, 0.12); p.rect(0, h-120, w, 120, fill=1, stroke=0)
    p.setFillColorRGB(1, 1, 1); p.rect(30, h-100, 160, 80, fill=1, stroke=0)
    if os.path.exists("logo_original.png"):
        try: img = ImageReader("logo_original.png"); p.drawImage(img, 40, h-95, width=140, height=70, preserveAspectRatio=True, mask='auto')
        except: pass
    p.setFillColorRGB(1, 1, 1); p.setFont("Helvetica-Bold", 18); p.drawRightString(w-30, h-50, "INFORME TÉCNICO S.A.P.E."); p.setFont("Helvetica", 10); p.drawRightString(w-30, h-65, "Sistema de Análisis de la Personalidad Emprendedora")

def create_pdf_report(ire, avg, friction, triggers, friction_reasons, delta, user, stats):
    buffer = io.BytesIO(); p = canvas.Canvas(buffer, pagesize=A4); w, h = A4
    draw_pdf_header(p, w, h)
    y_start = h - 160; p.setFillColorRGB(0,0,0); p.setFont("Helvetica-Bold", 10)
    p.drawString(40, y_start, f"ID Usuario: {st.session_state.user_id}"); p.drawString(200, y_start, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}"); p.drawString(400, y_start, f"Sector: {user.get('sector', 'N/A')}")
    y = y_start - 40; p.setFont("Helvetica-Bold", 12); p.setFillColorRGB(0.02, 0.04, 0.12); p.drawString(40, y, "1. Métricas Principales"); p.line(40, y-5, w-40, y-5); y -= 30
    
    def print_metric(label, val, desc): nonlocal y; p.setFont("Helvetica-Bold", 10); p.drawString(50, y, f"{label} ({val} / 100):"); p.setFont("Helvetica", 10); p.drawString(190, y, desc); y -= 25
    print_metric("POTENCIAL", avg, get_potential_text(avg))
    print_metric("FRICCIÓN", friction, get_friction_text(friction))
    print_metric("IRE FINAL", ire, get_ire_text(ire))
    p.setFont("Helvetica-Bold", 10); p.drawString(50, y, f"DELTA ({delta}):"); p.setFont("Helvetica", 10); p.drawString(190, y, "Pérdida de eficiencia por fricción operativa."); y -= 40
    
    p.setFont("Helvetica-Bold", 12); p.drawString(40, y, "2. Análisis Dimensional"); p.line(40, y-5, w-40, y-5); y -= 30
    sorted_stats = sorted(stats.items(), key=lambda item: item[1], reverse=True)
    for k, v in stats.items():
        p.setFont("Helvetica-Bold", 9); p.setFillColorRGB(0,0,0); p.drawString(50, y, LABELS_ES.get(k, k)); p.setFillColorRGB(0.9, 0.9, 0.9); p.rect(250, y, 200, 8, fill=1, stroke=0); bar_len = (v/100)*200
        if v <= 75: p.setFillColorRGB(0.2, 0.6, 0.4); p.rect(250, y, bar_len, 8, fill=1, stroke=0)
        else: safe = (75/100)*200; exc = bar_len - safe; p.setFillColorRGB(0.2, 0.6, 0.4); p.rect(250, y, safe, 8, fill=1, stroke=0); p.setFillColorRGB(0.8, 0.2, 0.2); p.rect(250 + safe, y, exc, 8, fill=1, stroke=0)
        p.setFillColorRGB(0,0,0); p.drawString(460, y, str(round(v, 1))); y -= 15
    y -= 15; p.setFont("Helvetica-Bold", 10); p.drawString(40, y, "Fortalezas"); y -= 15; p.setFont("Helvetica", 9)
    for i, (k, v) in enumerate(sorted_stats[:3]): y = draw_wrapped_text(p, f"{i+1}. {LABELS_ES.get(k)} ({round(v)}): {NARRATIVES_DB.get(k, {}).get('high', '')}", 50, y, 480, "Helvetica", 9); y -= 5
    y -= 10
    if y < 150: p.showPage(); draw_pdf_header(p, w, h); y = h - 160 
    p.setFont("Helvetica-Bold", 10); p.drawString(40, y, "Áreas de Desarrollo"); y -= 15; p.setFont("Helvetica", 9)
    for i, (k, v) in enumerate(sorted_stats[-3:]): mode = "low" if v < 60 else "high"; y = draw_wrapped_text(p, f"{i+1}. {LABELS_ES.get(k)} ({round(v)}): {NARRATIVES_DB.get(k, {}).get(mode, '')}", 50, y, 480, "Helvetica", 9); y -= 5
    y -= 30
    if y < 150: p.showPage(); draw_pdf_header(p, w, h); y = h - 160 
    p.setFont("Helvetica-Bold", 12); p.drawString(40, y, "3. Fricción y Alertas"); p.line(40, y-5, w-40, y-5); y -= 30
    p.setFont("Helvetica", 9)
    if friction_reasons: 
        p.drawString(50, y, "Factores de Fricción detectados:"); y -= 15
        for r in friction_reasons: p.drawString(60, y, f"- {r}"); y -= 15
    else: p.drawString(50, y, "• Sin fricción significativa."); y -= 15
    
    if triggers:
        y -= 10; p.setFont("Helvetica-Bold", 9); p.setFillColorRGB(0.8, 0, 0)
        p.drawString(50, y, "ALERTAS (TRIGGERS):"); y -= 15; p.setFillColorRGB(0, 0, 0); p.setFont("Helvetica", 9)
        for t in triggers: p.drawString(60, y, f"• {t}"); y -= 15
        
    y -= 20
    if y < 100: p.showPage(); draw_pdf_header(p, w, h); y = h - 160
    p.setFont("Helvetica-Bold", 12); p.drawString(40, y, "4. Conclusión"); p.line(40, y-5, w-40, y-5); y -= 30
    y = draw_wrapped_text(p, f"El perfil es técnicamente viable. Delta de eficiencia: {delta}.", 40, y, 480, "Helvetica", 9); y -= 10
    p.setFont("Helvetica-Bold", 9); p.drawString(40, y, "Recomendación:"); y -= 15
    y = draw_wrapped_text(p, "Se recomienda reducir los tiempos de validación externa y agilizar la toma de decisiones críticas.", 40, y, 480, "Helvetica", 9)
    p.showPage(); p.save(); buffer.seek(0); return buffer

def get_ire_text(s): return "Nivel positivo." if s > 75 else "Nivel medio." if s > 50 else "Nivel comprometido."
def get_potential_text(s): return "Nivel Notable." if s > 75 else "Nivel Medio." if s > 50 else "Nivel Bajo."
def get_friction_text(s): return "Nivel bajo." if s < 20 else "Nivel medio." if s < 40 else "Nivel alto."
def radar_chart():
    data = st.session_state.octagon; cat = [LABELS_ES.get(k) for k in data.keys()]; val = list(data.values()); cat += [cat[0]]; val += [val[0]]
    fig = go.Figure(go.Scatterpolar(r=val, theta=cat, fill='toself', line=dict(color='#5D5FEF'), fillcolor='rgba(93, 95, 239, 0.2)'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, showticklabels=False), bgcolor='rgba(0,0,0,0)'), paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'), showlegend=False, margin=dict(l=40, r=40, t=20, b=20), dragmode=False)
    return fig

# --- FUNCIÓN HEADER MEJORADA (Logo Izquierda + Título Derecha) ---
def render_header():
    # 1. Lógica inteligente para el logo: Intenta el blanco, si no, usa el original
    if os.path.exists("logo_blanco.png"):
        logo_path = "logo_blanco.png"
    elif os.path.exists("logo_original.png"):
        logo_path = "logo_original.png"
    else:
        logo_path = None

    # 2. Columnas ajustadas: [1.5] para logo (más espacio) | [4.5] para texto
    c1, c2 = st.columns([1.5, 4.5])
    
    with c1:
        if logo_path:
            st.image(logo_path, use_container_width=True)
        else:
            # Si no hay ninguna imagen, pone texto para que no quede vacío
            st.markdown("### AUDEO", unsafe_allow_html=True)
            
    with c2:
        # Usamos HTML directo con un poco de margen superior para alinear verticalmente con el logo
        st.markdown("""
            <div style="margin-top: 15px;">
                <p class="header-title-text">Simulador S.A.P.E.</p>
                <p class="header-sub-text">Sistema de Análisis de la Personalidad Emprendedora</p>
            </div>
        """, unsafe_allow_html=True)
    st.markdown("---")

# --- 5. APP PRINCIPAL ---
init_session()

# PANTALLA 0: LOGIN (Mantenemos la que ya funciona, no la toques en tu código si está bien)
if not st.session_state.get("auth", False):
    inject_style("login") 
    st.write("")
    st.write("")
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if os.path.exists("logo_original.png"):
            st.image("logo_original.png", use_container_width=True)
        st.markdown('<p class="login-title">Simulador S.A.P.E.</p>', unsafe_allow_html=True)
        st.markdown('<p class="login-subtitle">Sistema de Análisis de la Personalidad Emprendedora</p>', unsafe_allow_html=True)
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        pwd = st.text_input("Clave de acceso", type="password")
        if st.button("ENTRAR AL SISTEMA", use_container_width=True):
            if pwd == st.secrets["general"]["password"]: 
                st.session_state.auth = True
                st.rerun()
            else: 
                st.error("Acceso denegado")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- APP INTERNA (NAVY) ---
inject_style("app") 

# FASE 1: DATOS (REEMPLAZAR ESTE BLOQUE ENTERO)
if not st.session_state.data_verified:
    # FORZAMOS EL HEADER AQUÍ
    render_header()
    
    st.markdown("#### 1. Identificación del/a Candidato/a")
    
    col1, col2 = st.columns(2)
    name = col1.text_input("Nombre Completo")
    age = col2.number_input("Edad", 18, 99)
    
    col3, col4 = st.columns(2)
    gender = col3.selectbox("Género", ["Masculino", "Femenino", "Prefiero no decirlo"])
    country = col4.selectbox("País", ["España", "LATAM", "Europa", "Otros"])
    
    col5, col6 = st.columns(2)
    situation = col5.selectbox("Situación", ["Solo", "Con Socios", "Intraemprendimiento"])
    experience = col6.selectbox("Experiencia", ["Primer emprendimiento", "Con éxito previo", "Sin éxito previo"])
    
    st.markdown("<br>", unsafe_allow_html=True)
    consent = st.checkbox("He leído y acepto la Política de Privacidad.")
    
    if st.button("VALIDAR DATOS Y CONTINUAR"):
        if name and age and consent:
            st.session_state.user_data = {"name": name, "age": age, "gender": gender, "sector": "", "experience": experience}
            st.session_state.data_verified = True
            st.rerun()
        else:
            st.error("Por favor, completa los campos obligatorios.")

# FASE 2: SECTOR (REDRISEÑADO: 2 FILAS x 4 COLUMNAS)
elif not st.session_state.started:
    render_header() # <--- LOGO
    st.markdown(f"#### 2. Selecciona el Sector del Proyecto:")
    
    def go_sector(sec):
        all_q = load_questions()
        code = SECTOR_MAP.get(sec, "TECH")
        qs = [x for x in all_q if x['SECTOR'].strip().upper() == code]
        if not qs: qs = [x for x in all_q if x['SECTOR'].strip().upper() == "TECH"]
        st.session_state.data = qs
        st.session_state.user_data["sector"] = sec
        st.session_state.started = True
        st.rerun()

    # FILA 1
    c1, c2, c3, c4 = st.columns(4)
    with c1: 
        if st.button("Startup Tecnológica\n(Scalable)"): go_sector("Startup Tecnológica (Scalable)")
    with c2:
        if st.button("Consultoría /\nServicios Prof."): go_sector("Consultoría / Servicios Profesionales")
    with c3:
        if st.button("Pequeña y Mediana\nEmpresa (PYME)"): go_sector("Pequeña y Mediana Empresa (PYME)")
    with c4:
        if st.button("Hostelería y\nRestauración"): go_sector("Hostelería y Restauración")
        
    st.markdown("") # Pequeño espacio
    
    # FILA 2
    c5, c6, c7, c8 = st.columns(4)
    with c5:
        if st.button("Autoempleo /\nFreelance"): go_sector("Autoempleo / Freelance")
    with c6:
        if st.button("Emprendimiento\nSocial"): go_sector("Emprendimiento Social")
    with c7:
        if st.button("Intraemprendimiento"): go_sector("Intraemprendimiento")
    with c8:
        if st.button("Emprendimiento en\nServicios de Salud"): go_sector("Salud")

# FASE 3: PREGUNTAS
elif not st.session_state.finished:
    # Freno de seguridad
    if st.session_state.current_step >= len(st.session_state.data):
        st.session_state.finished = True
        st.rerun()
        
    render_header() # <--- LOGO
    row = st.session_state.data[st.session_state.current_step]
    st.progress((st.session_state.current_step + 1) / len(st.session_state.data))
    
    st.markdown(f"### {row['TITULO']}")
    
    c_text, c_opt = st.columns([1.5, 1])
    with c_text:
        st.markdown(f'<div class="diag-text" style="font-size:1.2rem;"><p>{row["NARRATIVA"]}</p></div>', unsafe_allow_html=True)
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
            
        if row.get('OPCION_C_TXT') and row.get('OPCION_C_TXT') != "None":
            if st.button(row.get('OPCION_C_TXT', 'C'), key=f"C_{step}", use_container_width=True):
                parse_logic(row.get('OPCION_C_LOGIC'))
                st.session_state.current_step += 1
                st.rerun()
        
        if row.get('OPCION_D_TXT') and row.get('OPCION_D_TXT') != "None":
            if st.button(row.get('OPCION_D_TXT', 'D'), key=f"D_{step}", use_container_width=True):
                parse_logic(row.get('OPCION_D_LOGIC'))
                st.session_state.current_step += 1
                st.rerun()

# FASE 4: RESULTADOS
else:
    render_header() # <--- LOGO
    ire, avg, friction, triggers, fric_reasons, delta = calculate_results()
    
    st.header(f"Informe S.A.P.E. | {st.session_state.user_data['name']}")
    
    k1, k2, k3 = st.columns(3)
    k1.metric("Índice IRE", f"{ire}/100")
    k2.metric("Potencial", f"{avg}/100")
    k3.metric("Fricción", friction, delta_color="inverse")
    
    c_chart, c_desc = st.columns([1, 1])
    with c_chart:
        st.plotly_chart(radar_chart(), use_container_width=True)
    with c_desc:
        st.markdown("### Diagnóstico")
        st.markdown(f'<div class="diag-text"><p>{get_ire_text(ire)}</p></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if triggers:
             st.error("Alertas: " + ", ".join(triggers))
        else:
             st.success("Perfil sin alertas críticas.")

    st.markdown("<br>", unsafe_allow_html=True)
    
    pdf = create_pdf_report(ire, avg, friction, triggers, fric_reasons, delta, st.session_state.user_data, st.session_state.octagon)
    st.download_button(
        "📥 DESCARGAR INFORME COMPLETO (PDF)",
        pdf,
        file_name=f"Informe_SAPE_{st.session_state.user_id}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
    
    if st.button("Reiniciar"):
        st.session_state.clear()
        st.rerun()