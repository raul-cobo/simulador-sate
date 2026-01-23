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

# --- 2. CSS "CAMUFLAJE" (SOLUCIÓN AL RECUADRO BLANCO) ---
def local_css():
    st.markdown("""
    <style>
        /* 1. CAMUFLAR EL HEADER NATIVO (Hacerlo del color del fondo) */
        header, [data-testid="stHeader"], .stAppHeader { 
            background-color: #050A1F !important; /* Mismo color que el fondo */
            border-bottom: none !important;
        }
        
        /* Ocultar la barra de decoración de colores */
        div[data-testid="stDecoration"] { 
            visibility: hidden !important; 
            height: 0px !important;
        }

        /* 2. SUBIR EL CONTENIDO (Pegado arriba) */
        .main .block-container { 
            padding-top: 2rem !important; 
            margin-top: 0 !important;
            max-width: 95% !important;
        }

        /* FONDO GLOBAL */
        .stApp { background-color: #050A1F; color: #FFFFFF; }
        html, body { background-color: #050A1F !important; }
        
        /* TEXTOS BLANCOS */
        h1, h2, h3, h4, h5, h6, p, label, span, div[data-testid="stMarkdownContainer"] p { 
            color: #FFFFFF !important; 
        }

        /* INPUTS */
        .stTextInput input, .stNumberInput input, .stSelectbox > div > div {
            background-color: #0F1629 !important; color: #FFFFFF !important; border: 1px solid #5D5FEF !important;
        }
        div[role="listbox"] div { color: #FFFFFF !important; background-color: #0F1629 !important; }
        .stCheckbox label p { color: #FFFFFF !important; }

        /* BOTONES */
        .stButton > button {
            background-color: #1A202C !important; color: #FFFFFF !important; border: 1px solid #5D5FEF !important; border-radius: 8px !important;
        }
        .stButton > button:hover { background-color: #5D5FEF !important; border-color: #FFFFFF !important; }
        
        /* LOGIN CARD (Blanca) */
        .login-card { 
            background-color: white; 
            padding: 3rem; 
            border-radius: 20px; 
            text-align: center; 
            box-shadow: 0 0 50px rgba(0,0,0,0.5);
            margin-top: 20px;
        }
        .login-card h3, .login-card p, .login-card div, .login-card label { color: #000000 !important; }
        .login-card input { background-color: #f0f2f6 !important; color: #000000 !important; border: 1px solid #ccc !important; }

        /* HEADER INTERNO (Logo Izq + Texto Der) */
        .header-title-text { font-size: 2.2rem !important; font-weight: bold !important; margin: 0 !important; line-height: 1.2; }
        .header-sub-text { font-size: 1.1rem !important; color: #5D5FEF !important; margin: 0 !important; }

        /* RESULTADOS */
        .diag-text { background-color: #0F1629; padding: 15px; border-radius: 8px; border-left: 4px solid #5D5FEF; }
        .diag-text p { color: #E2E8F0 !important; margin: 0; }
        
        /* BOTÓN DESCARGA */
        .stDownloadButton > button {
            background-color: #5D5FEF !important; color: white !important; border: 1px solid white !important; font-weight: bold !important;
        }
        
        /* SECTORES GIGANTES */
        div[data-testid="column"] button {
             width: 100% !important; border: 2px solid #2D3748 !important; background-color: #0F1629 !important; color: white !important; border-radius: 15px !important;
        }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- 3. LÓGICA ---
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
SECTOR_MAP = { "Startup Tecnológica (Scalable)": "TECH", "Consultoría / Servicios Profesionales": "CONSULTORIA", "Pequeña y Mediana Empresa (PYME)": "PYME", "Hostelería y Restauración": "HOSTELERIA", "Autoempleo / Freelance": "AUTOEMPLEO", "Emprendimiento Social": "SOCIAL", "Intraemprendimiento": "INTRA" }

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

# --- PDF HELPERS ---
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
    draw_pdf_header(p, w, h) # PÁGINA 1
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
    if y < 150: p.showPage(); draw_pdf_header(p, w, h); y = h - 160 # SALTO PAGINA
    p.setFont("Helvetica-Bold", 10); p.drawString(40, y, "Áreas de Desarrollo"); y -= 15; p.setFont("Helvetica", 9)
    for i, (k, v) in enumerate(sorted_stats[-3:]): mode = "low" if v < 60 else "high"; y = draw_wrapped_text(p, f"{i+1}. {LABELS_ES.get(k)} ({round(v)}): {NARRATIVES_DB.get(k, {}).get(mode, '')}", 50, y, 480, "Helvetica", 9); y -= 5
    y -= 30
    if y < 150: p.showPage(); draw_pdf_header(p, w, h); y = h - 160 # SALTO PAGINA
    p.setFont("Helvetica-Bold", 12); p.drawString(40, y, "3. Fricción"); p.line(40, y-5, w-40, y-5); y -= 30; p.setFont("Helvetica", 9)
    if friction_reasons: 
        for r in friction_reasons: p.drawString(50, y, f"• {r}"); y -= 15
    else: p.drawString(50, y, "• Sin fricción significativa.")
    y -= 20
    if y < 100: p.showPage(); draw_pdf_header(p, w, h); y = h - 160 # SALTO PAGINA
    p.setFont("Helvetica-Bold", 12); p.drawString(40, y, "4. Conclusión"); p.line(40, y-5, w-40, y-5); y -= 30
    y = draw_wrapped_text(p, f"El perfil es técnicamente viable. Delta de eficiencia: {delta}.", 40, y, 480, "Helvetica", 9); y -= 10
    p.setFont("Helvetica-Bold", 9); p.drawString(40, y, "Recomendación:"); y -= 15
    y = draw_wrapped_text(p, "Reducir tiempos de deliberación y comprobaciones redundantes.", 40, y, 480, "Helvetica", 9)
    p.showPage(); p.save(); buffer.seek(0); return buffer

def get_ire_text(s): return "Nivel positivo." if s > 75 else "Nivel medio." if s > 50 else "Nivel comprometido."
def get_potential_text(s): return "Nivel Notable." if s > 75 else "Nivel Medio." if s > 50 else "Nivel Bajo."
def get_friction_text(s): return "Nivel bajo." if s < 20 else "Nivel medio." if s < 40 else "Nivel alto."
def radar_chart():
    data = st.session_state.octagon; cat = [LABELS_ES.get(k) for k in data.keys()]; val = list(data.values()); cat += [cat[0]]; val += [val[0]]
    fig = go.Figure(go.Scatterpolar(r=val, theta=cat, fill='toself', line=dict(color='#5D5FEF'), fillcolor='rgba(93, 95, 239, 0.2)'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, showticklabels=False), bgcolor='rgba(0,0,0,0)'), paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'), showlegend=False, margin=dict(l=40, r=40, t=20, b=20), dragmode=False)
    return fig

# --- FUNCIÓN RENDERIZADO HEADER WEB (Logo + Texto) ---
def render_header():
    # Logo blanco a la izquierda, Título grande a la derecha
    c1, c2 = st.columns([1, 4])
    with c1:
        if os.path.exists("logo_blanco.png"):
            st.image("logo_blanco.png", use_container_width=True)
    with c2:
        st.markdown('<p class="header-title-text">Simulador S.A.P.E.</p>', unsafe_allow_html=True)
        st.markdown('<p class="header-sub-text">Sistema de Análisis de la Personalidad Emprendedora</p>', unsafe_allow_html=True)
    st.markdown("---")

# --- 5. APP PRINCIPAL ---
init_session()

# LOGIN
if not st.session_state.get("auth", False):
    # 1. LOGO GRANDE CENTRADO (En la zona superior, sobre el fondo azul)
    # Usamos logo_blanco.png para que contraste con el fondo azul oscuro que ahora cubre todo
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if os.path.exists("logo_blanco.png"):
            st.image("logo_blanco.png", use_container_width=True)
        else:
            st.header("AUDEO")

    # 2. TARJETA LOGIN (Debajo del logo)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("<h3>Acceso Corporativo</h3>", unsafe_allow_html=True)
        pwd = st.text_input("Clave de acceso", type="password")
        if st.button("ENTRAR", use_container_width=True):
            if pwd == st.secrets["general"]["password"]: st.session_state.auth = True; st.rerun()
            else: st.error("Error")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- HEADER GLOBAL TRAS LOGIN ---
render_header()

# FASE 1: DATOS
if not st.session_state.data_verified:
    st.markdown("#### 1. Identificación")
    col1, col2 = st.columns(2); name = col1.text_input("Nombre"); age = col2.number_input("Edad", 18, 99)
    col3, col4 = st.columns(2); gender = col3.selectbox("Género", ["Masculino", "Femenino"]); country = col4.selectbox("País", ["España", "LATAM", "Otros"])
    col5, col6 = st.columns(2); situation = col5.selectbox("Situación", ["Solo", "Socios"]); experience = col6.selectbox("Experiencia", ["Primera", "Con éxito", "Sin éxito"])
    consent = st.checkbox("Acepto Política de Privacidad.")
    if st.button("VALIDAR"):
        if name and age and consent: st.session_state.user_data = {"name": name, "sector": ""}; st.session_state.data_verified = True; st.rerun()

# FASE 2: SECTOR
elif not st.session_state.started:
    st.markdown("<style>div[data-testid='column'] button {height: 200px !important; font-size: 1.4rem !important; font-weight: bold !important; background-color: #0F1629; color: white; border: 2px solid #2D3748; border-radius: 15px;}</style>", unsafe_allow_html=True)
    st.markdown("#### 2. Selecciona Sector")
    def go(sec):
        all_q = load_questions(); code = SECTOR_MAP[sec]
        qs = [x for x in all_q if x['SECTOR'].strip().upper() == code]
        st.session_state.data = qs if qs else [x for x in all_q if x['SECTOR'].strip().upper() == "TECH"]
        st.session_state.user_data["sector"] = sec; st.session_state.started = True; st.rerun()

    c1, c2, c3, c4 = st.columns(4)
    with c1: 
        if st.button("Startup Tecnológica"): go("Startup Tecnológica (Scalable)")
    with c2: 
        if st.button("Consultoría"): go("Consultoría / Servicios Profesionales")
    with c3: 
        if st.button("PYME"): go("Pequeña y Mediana Empresa (PYME)")
    with c4: 
        if st.button("Hostelería"): go("Hostelería y Restauración")
    
    st.markdown("<br>", unsafe_allow_html=True)
    c5, c6, c7, c8 = st.columns(4)
    with c5: 
        if st.button("Freelance"): go("Autoempleo / Freelance")
    with c6: 
        if st.button("Social"): go("Emprendimiento Social")
    with c7: 
        if st.button("Intraemprendimiento"): go("Intraemprendimiento")

# FASE 3: PREGUNTAS
elif not st.session_state.finished:
    row = st.session_state.data[st.session_state.current_step]
    st.progress((st.session_state.current_step + 1) / len(st.session_state.data))
    st.markdown(f"### {row['TITULO']}")
    c1, c2 = st.columns([1.5, 1])
    with c1: st.markdown(f'<div class="diag-text"><p>{row["NARRATIVA"]}</p></div>', unsafe_allow_html=True)
    with c2:
        step = st.session_state.current_step
        if st.button(row.get('OPCION_A_TXT', 'A'), key=f"A_{step}"): parse_logic(row.get('OPCION_A_LOGIC')); st.session_state.current_step += 1; st.rerun()
        if st.button(row.get('OPCION_B_TXT', 'B'), key=f"B_{step}"): parse_logic(row.get('OPCION_B_LOGIC')); st.session_state.current_step += 1; st.rerun()
        if row.get('OPCION_C_TXT') and row.get('OPCION_C_TXT') != "None": 
            if st.button(row.get('OPCION_C_TXT', 'C'), key=f"C_{step}"): parse_logic(row.get('OPCION_C_LOGIC')); st.session_state.current_step += 1; st.rerun()
        if row.get('OPCION_D_TXT') and row.get('OPCION_D_TXT') != "None": 
            if st.button(row.get('OPCION_D_TXT', 'D'), key=f"D_{step}"): parse_logic(row.get('OPCION_D_LOGIC')); st.session_state.current_step += 1; st.rerun()
        if st.session_state.current_step >= len(st.session_state.data): st.session_state.finished = True; st.rerun()

# FASE 4: RESULTADOS
else:
    ire, avg, friction, triggers, friction_reasons, delta = calculate_results()
    st.header(f"Informe S.A.P.E. | {st.session_state.user_data['name']}")
    k1, k2, k3 = st.columns(3); k1.metric("IRE", f"{ire}/100"); k2.metric("Potencial", f"{avg}/100"); k3.metric("Fricción", friction)
    c1, c2 = st.columns([1, 1])
    with c1: st.plotly_chart(radar_chart(), use_container_width=True)
    with c2: 
        st.markdown(f'<div class="diag-text"><p>{get_ire_text(ire)}</p></div>', unsafe_allow_html=True)
        if triggers: st.error("Alertas: " + ", ".join(triggers))
        else: st.success("Sin alertas.")
    
    pdf = create_pdf_report(ire, avg, friction, triggers, friction_reasons, delta, st.session_state.user_data, st.session_state.octagon)
    st.download_button("📥 DESCARGAR INFORME (PDF)", pdf, f"Informe_{st.session_state.user_id}.pdf", "application/pdf", use_container_width=True)
    if st.button("Reiniciar"): st.session_state.clear(); st.rerun()