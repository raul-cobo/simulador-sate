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

# --- 2. INYECCIÓN CSS (CORRECCIONES VISUALES DEFINITIVAS) ---
def local_css():
    st.markdown("""
    <style>
        /* Ocultar elementos nativos de Streamlit */
        header, [data-testid="stHeader"], .stAppHeader, [data-testid="stToolbar"] { display: none !important; }
        footer, .stDeployButton { display: none !important; }
        
        /* Eliminar márgenes superiores para quitar el hueco blanco */
        .main .block-container { padding-top: 1rem !important; margin-top: 0 !important; }

        /* FONDO GLOBAL */
        .stApp { background-color: #050A1F; color: #FFFFFF; }
        
        /* TEXTOS BLANCOS (Global) */
        h1, h2, h3, h4, h5, h6, p, label, span, div[data-testid="stMarkdownContainer"] p { 
            color: #FFFFFF !important; 
        }

        /* INPUTS (Oscuros con texto blanco) */
        .stTextInput input, .stNumberInput input, .stSelectbox > div > div {
            background-color: #0F1629 !important; color: #FFFFFF !important; border: 1px solid #5D5FEF !important;
        }
        div[role="listbox"] div { color: #FFFFFF !important; background-color: #0F1629 !important; }
        .stCheckbox label p { color: #FFFFFF !important; }

        /* BOTONES DE RESPUESTA Y NAVEGACIÓN */
        .stButton > button {
            background-color: #1A202C !important; color: #FFFFFF !important; border: 1px solid #5D5FEF !important; border-radius: 8px !important;
        }
        .stButton > button:hover { background-color: #5D5FEF !important; border-color: #FFFFFF !important; }
        
        /* BOTÓN DE DESCARGA */
        .stDownloadButton > button {
            background-color: #5D5FEF !important;
            color: white !important;
            border: 1px solid white !important;
            font-weight: bold !important;
        }
        .stDownloadButton > button:hover { background-color: #4B4DCE !important; }

        /* BOTONES DE SECTOR (GIGANTES) */
        .sector-card button {
            height: 250px !important; /* Altura forzada */
            width: 100% !important;
            white-space: normal !important; /* Texto en varias líneas */
            font-size: 1.5rem !important;
            font-weight: bold !important;
            background-color: #0F1629 !important;
            color: white !important;
            border: 2px solid #2D3748 !important;
            border-radius: 15px !important;
            display: flex;
            align-items: center;
            justify_content: center;
            line-height: 1.5 !important;
        }
        .sector-card button:hover {
            border-color: #5D5FEF !important;
            background-color: #1A202C !important;
            transform: scale(1.02);
        }

        /* CAJA DE LOGIN (Centrado perfecto con Flexbox) */
        .login-container {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 80vh; /* Ocupa casi toda la pantalla vertical */
        }
        .login-card { 
            background-color: white; 
            padding: 3rem; 
            border-radius: 20px; 
            text-align: center; 
            box-shadow: 0 0 50px rgba(0,0,0,0.5);
            width: 100%;
            max-width: 500px;
        }
        /* Forzamos negro SOLO dentro de la login-card */
        .login-card h1, .login-card h2, .login-card h3, .login-card p, .login-card div, .login-card span {
            color: #000000 !important;
        }
        .login-card input { 
            background-color: #f0f2f6 !important; 
            color: #000000 !important; 
            border: 1px solid #ccc !important; 
        }
        
        /* HEADER EN APP (Logo izquierda, Titulo derecha) */
        .custom-header-title { font-size: 2.2rem; font-weight: bold; color: white !important; margin: 0; line-height: 1.2;}
        .custom-header-sub { font-size: 1.1rem; color: #5D5FEF !important; margin: 0; }

        /* TEXTO RESULTADOS */
        .diag-text { background-color: #0F1629; padding: 15px; border-radius: 8px; border-left: 4px solid #5D5FEF; margin-bottom: 10px; }
        .diag-text p { color: #E2E8F0 !important; margin: 0; }
        
        /* VALIDAR BTN */
        .validate-btn button { background-color: #5D5FEF !important; font-size: 1.2rem !important; border: none !important; margin-top: 20px;}
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- 3. VARIABLES Y LÓGICA ---
LABELS_ES = {
    "achievement": "Necesidad de Logro", "risk_propensity": "Propensión al Riesgo",
    "innovativeness": "Innovatividad", "locus_control": "Locus de Control Interno",
    "self_efficacy": "Autoeficacia", "autonomy": "Autonomía",
    "ambiguity_tolerance": "Tol. Ambigüedad",
    "emotional_stability": "Estabilidad Emocional"
}

NARRATIVES_DB = {
    "emotional_stability": {
        "high": "Puntuación muy alta. Capacidad absoluta para mantener la regulación emocional bajo presión. Indica una gestión óptima del estrés y nula reactividad impulsiva.",
        "low": "Nivel bajo. Vulnerabilidad ante la presión sostenida. Puede presentar bloqueos operativos en situaciones de crisis."
    },
    "autonomy": {
        "high": "Puntuación muy alta. Fuerte independencia operativa y de criterio. No requiere supervisión externa y posee iniciativa para liderar.",
        "low": "Dependencia operativa. Requiere validación constante y directrices claras para avanzar."
    },
    "achievement": {
        "high": "Nivel alto. Clara orientación a resultados y estándares de excelencia. Prioriza la finalización de tareas.",
        "low": "Baja orientación a resultados. Puede diluirse en procesos sin cerrar etapas críticas."
    },
    "risk_propensity": {
        "high": "Alta tolerancia al riesgo. Disposición a actuar en escenarios de incertidumbre financiera u operativa.",
        "low": "Perfil conservador. Prioriza la seguridad. Puede incurrir en costes de oportunidad por falta de decisión."
    },
    "ambiguity_tolerance": {
        "high": "Alta capacidad de gestión del caos. Opera con confort sin tener toda la información disponible.",
        "low": "Nivel medio-bajo. Requiere información estructurada antes de proceder. En fases iniciales deriva en retrasos."
    },
    "innovativeness": {
        "high": "Perfil disruptivo. Tendencia a generar nuevos enfoques y modelos de negocio.",
        "low": "Nivel medio. Tiende a la optimización de procesos existentes más que a la disrupción creativa."
    },
    "locus_control": {
        "high": "Locus Interno fuerte. Asume la responsabilidad de los resultados y cree en su capacidad de influir.",
        "low": "Tendencia a atribuir resultados a factores externos. Puede reducir la proactividad correctiva."
    },
    "self_efficacy": {
        "high": "Confianza sólida en las propias capacidades técnicas y de gestión.",
        "low": "Dudas sobre la propia capacidad que pueden llevar a la parálisis por análisis."
    }
}

VARIABLE_MAP = {
    "achievement": "achievement", "logro": "achievement", "risk_propensity": "risk_propensity", "riesgo": "risk_propensity",
    "innovativeness": "innovativeness", "innovacion": "innovativeness", "locus_control": "locus_control", "locus": "locus_control",
    "self_efficacy": "self_efficacy", "autoeficacia": "self_efficacy", "collaboration": "self_efficacy",
    "autonomy": "autonomy", "autonomia": "autonomy", "ambiguity_tolerance": "ambiguity_tolerance", "tolerancia": "ambiguity_tolerance", "imaginative": "ambiguity_tolerance",
    "emotional_stability": "emotional_stability", "estabilidad": "emotional_stability", "excitable": "excitable", "skeptical": "skeptical", "cautious": "cautious", 
    "reserved": "reserved", "passive_aggressive": "passive_aggressive", "arrogant": "arrogant", "mischievous": "mischievous", 
    "melodramatic": "melodramatic", "diligent": "diligent", "dependent": "dependent"
}

SECTOR_MAP = {
    "Startup Tecnológica (Scalable)": "TECH", "Consultoría / Servicios Profesionales": "CONSULTORIA",
    "Pequeña y Mediana Empresa (PYME)": "PYME", "Hostelería y Restauración": "HOSTELERIA",
    "Autoempleo / Freelance": "AUTOEMPLEO", "Emprendimiento Social": "SOCIAL", "Intraemprendimiento": "INTRA"
}

def generate_id(): return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def init_session():
    if 'octagon' not in st.session_state:
        st.session_state.octagon = {k: 50 for k in LABELS_ES.keys()}
        st.session_state.flags = {k: 0 for k in ["excitable", "skeptical", "cautious", "reserved", "passive_aggressive", "arrogant", "mischievous", "melodramatic", "diligent", "dependent"]}
        st.session_state.current_step = 0
        st.session_state.finished = False
        st.session_state.started = False 
        st.session_state.data_verified = False
        st.session_state.data = []
        st.session_state.user_id = generate_id()
        st.session_state.user_data = {}

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
            if target in st.session_state.octagon:
                st.session_state.octagon[target] = max(0, min(100, st.session_state.octagon[target] + val))
            elif target in st.session_state.flags:
                st.session_state.flags[target] = max(0, st.session_state.flags[target] + val)

def calculate_results():
    o, f = st.session_state.octagon, st.session_state.flags
    avg = sum(o.values()) / 8
    friction = sum(f.values()) * 0.5
    triggers = []
    
    friction_reasons = []
    if f["cautious"] > 10 or f["diligent"] > 10: friction_reasons.append("Prudencia Administrativa: Prioriza seguridad jurídica sobre velocidad.")
    if f["dependent"] > 10 or f["skeptical"] > 10: friction_reasons.append("Exceso de Validación: Tendencia a buscar confirmación externa.")
    if f["arrogant"] > 20: friction_reasons.append("Rigidez Cognitiva: Dificultad para pivotar ante datos negativos.")
    
    if f["mischievous"] > 25: triggers.append("Riesgo de Desalineamiento Normativo")
    if f["arrogant"] > 25: triggers.append("Estilo Dominante / Rigidez Potencial")
    if f["passive_aggressive"] > 20: triggers.append("Fricción Relacional Latente")
    if o["achievement"] > 85 and o["emotional_stability"] < 40: triggers.append("Riesgo de Agotamiento Operativo (Burnout)")
    if o["risk_propensity"] > 85 and f["cautious"] < 10: triggers.append("Perfil de Riesgo Desmedido")
    
    ire = max(0, min(100, avg - (friction * 0.8) - (len(triggers) * 3)))
    
    # Cálculo del Delta (Diferencial)
    delta = round(avg - ire, 2)
    
    return round(ire, 2), round(avg, 2), round(friction, 2), triggers, friction_reasons, delta

# --- FUNCIÓN AUXILIAR PARA TEXTO QUE SE CORTA ---
def draw_wrapped_text(c, text, x, y, max_width, font_name, font_size, line_spacing=12):
    c.setFont(font_name, font_size)
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        width = c.stringWidth(" ".join(current_line), font_name, font_size)
        if width > max_width:
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [word]
    lines.append(" ".join(current_line))
    
    for line in lines:
        c.drawString(x, y, line)
        y -= line_spacing
    return y # Devolvemos la nueva posición Y

# --- PDF GENERATOR ---
def create_pdf_report(ire, avg, friction, triggers, friction_reasons, delta, user, stats):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    
    # --- 1. CABECERA AZUL COMPLETA (Sin diagonal) ---
    p.setFillColorRGB(0.02, 0.04, 0.12) # Navy Audeo
    p.rect(0, h-120, w, 120, fill=1, stroke=0)
    
    # LOGO EN RECUADRO BLANCO (Izquierda)
    if os.path.exists("logo_original.png"):
        # Caja blanca para el logo
        p.setFillColorRGB(1, 1, 1)
        p.rect(30, h-100, 150, 80, fill=1, stroke=0) # Caja
        try:
            img = ImageReader("logo_original.png")
            p.drawImage(img, 40, h-95, width=130, height=70, preserveAspectRatio=True, mask='auto')
        except: pass
    
    # TÍTULO (Derecha, texto blanco sobre azul)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 20)
    p.drawRightString(w-30, h-50, "INFORME TÉCNICO S.A.P.E.")
    p.setFont("Helvetica", 10)
    p.drawRightString(w-30, h-65, "Sistema de Análisis de la Personalidad Emprendedora")
    
    # --- 2. DATOS ---
    y_start = h - 160
    p.setFillColorRGB(0,0,0)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(40, y_start, f"ID Usuario: {st.session_state.user_id}")
    p.drawString(200, y_start, f"Fecha de Análisis: {datetime.now().strftime('%d/%m/%Y')}")
    p.drawString(400, y_start, f"Sector: {user.get('sector', 'N/A')}")
    
    # --- 3. MÉTRICAS ---
    y = y_start - 40
    p.setFont("Helvetica-Bold", 12)
    p.setFillColorRGB(0.02, 0.04, 0.12)
    p.drawString(40, y, "1. Métricas Principales")
    p.line(40, y-5, w-40, y-5)
    y -= 30
    
    # Helper para dibujar texto ajustado (Para que no se salga)
    def print_metric(label, val, desc_func, extra_desc=None):
        nonlocal y
        p.setFont("Helvetica-Bold", 10)
        p.drawString(50, y, f"{label} ({val} / 100):")
        p.setFont("Helvetica", 10)
        p.drawString(190, y, desc_func)
        y -= 15
        if extra_desc:
            p.setFont("Helvetica", 9)
            # Usamos el wrapper para el texto largo
            y = draw_wrapped_text(p, extra_desc, 50, y, 480, "Helvetica", 9)
        y -= 20

    print_metric("POTENCIAL", avg, get_potential_text(avg), 
                 "Recursos cognitivos y actitudinales basales para afrontar la complejidad operativa del sector.")
    
    print_metric("FRICCIÓN", friction, get_friction_text(friction), 
                 "Presencia de conductas de comprobación, validación externa o cautela que ralentizan la toma de decisiones.")
    
    # DELTA (DIFERENCIAL)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, y, f"DELTA (Diferencial) ({delta}):")
    p.setFont("Helvetica", 10)
    p.drawString(190, y, "Pérdida de eficiencia.")
    y -= 15
    p.setFont("Helvetica", 9)
    y = draw_wrapped_text(p, f"Discrepancia entre el Potencial ({avg}) y el IRE ({ire}). Representa el coste operativo autoimpuesto por mecanismos de control.", 50, y, 480, "Helvetica", 9)
    y -= 20

    print_metric("IRE FINAL", ire, get_ire_text(ire), 
                 "El índice ajustado confirma la viabilidad técnica y sostenibilidad a largo plazo.")

    # --- 4. ANÁLISIS DIMENSIONAL ---
    p.setFont("Helvetica-Bold", 12)
    p.drawString(40, y, "2. Análisis Dimensional (Perfil Competencial)")
    p.line(40, y-5, w-40, y-5)
    y -= 30
    
    # Barras
    sorted_stats = sorted(stats.items(), key=lambda item: item[1], reverse=True)
    top_3 = sorted_stats[:3]
    low_3 = sorted_stats[-3:]

    for k, v in stats.items():
        label = LABELS_ES.get(k, k)
        p.setFont("Helvetica-Bold", 9)
        p.setFillColorRGB(0,0,0)
        p.drawString(50, y, label)
        
        # Barra Fondo
        p.setFillColorRGB(0.9, 0.9, 0.9)
        p.rect(250, y, 200, 8, fill=1, stroke=0)
        
        bar_len = (v/100)*200
        if v <= 75:
            # Normal (Verde Audeo)
            p.setFillColorRGB(0.2, 0.6, 0.4)
            p.rect(250, y, bar_len, 8, fill=1, stroke=0)
        else:
            # Exceso (Verde -> Rojo)
            safe_len = (75/100)*200
            excess_len = bar_len - safe_len
            p.setFillColorRGB(0.2, 0.6, 0.4)
            p.rect(250, y, safe_len, 8, fill=1, stroke=0)
            p.setFillColorRGB(0.8, 0.2, 0.2) # Rojo Exceso
            p.rect(250 + safe_len, y, excess_len, 8, fill=1, stroke=0)
        
        p.setFillColorRGB(0,0,0)
        p.drawString(460, y, str(round(v, 1)))
        y -= 15
    
    y -= 10
    
    # Textos Dinámicos
    p.setFont("Helvetica-Bold", 10)
    p.drawString(40, y, "Fortalezas Consolidadas")
    y -= 15
    p.setFont("Helvetica", 9)
    for i, (k, v) in enumerate(top_3):
        title = LABELS_ES.get(k)
        raw_text = NARRATIVES_DB.get(k, {}).get("high", "Desempeño destacado.")
        text_line = f"{i+1}. {title} ({round(v)}/100): {raw_text}"
        y = draw_wrapped_text(p, text_line, 50, y, 480, "Helvetica", 9)
        y -= 5

    y -= 10
    p.setFont("Helvetica-Bold", 10)
    p.drawString(40, y, "Áreas de Desarrollo")
    y -= 15
    p.setFont("Helvetica", 9)
    for i, (k, v) in enumerate(low_3):
        title = LABELS_ES.get(k)
        mode = "low" if v < 60 else "high"
        raw_text = NARRATIVES_DB.get(k, {}).get(mode, "Requiere atención.")
        text_line = f"{i+1}. {title} ({round(v)}/100): {raw_text}"
        y = draw_wrapped_text(p, text_line, 50, y, 480, "Helvetica", 9)
        y -= 5

    if y < 100:
        p.showPage()
        y = h - 100

    # --- 5. FRICCIÓN ---
    y -= 20
    p.setFont("Helvetica-Bold", 12)
    p.drawString(40, y, "3. Análisis de la Fricción")
    p.line(40, y-5, w-40, y-5)
    y -= 30
    
    p.setFont("Helvetica", 9)
    p.setFillColorRGB(0,0,0)
    
    if friction_reasons:
        for reason in friction_reasons:
            p.drawString(50, y, f"• {reason}")
            y -= 15
    else:
        p.drawString(50, y, "• No se detectan patrones de fricción significativos.")
        y -= 15

    # --- 6. CONCLUSIÓN ---
    y -= 20
    p.setFont("Helvetica-Bold", 12)
    p.drawString(40, y, "4. Conclusión y Recomendación")
    p.line(40, y-5, w-40, y-5)
    y -= 30
    
    p.setFont("Helvetica", 9)
    concl = f"El perfil es técnicamente viable. La discrepancia entre Potencial ({avg}) e IRE ({ire}) marca el margen de mejora (Delta: {delta})."
    y = draw_wrapped_text(p, concl, 40, y, 480, "Helvetica", 9)
    y -= 10
    p.setFont("Helvetica-Bold", 9)
    p.drawString(40, y, "Recomendación:")
    y -= 12
    p.setFont("Helvetica", 9)
    rec_text = "Se debe trabajar en la reducción de los tiempos de deliberación. El objetivo es aumentar la velocidad de decisión, reduciendo las comprobaciones de seguridad redundantes."
    y = draw_wrapped_text(p, rec_text, 40, y, 480, "Helvetica", 9)

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

def get_ire_text(score):
    if score > 75: return "Nivel positivo. Rango de alta sostenibilidad."
    if score > 50: return "Nivel medio. Viable pero con coste operativo."
    return "Nivel comprometido. Riesgos de continuidad."

def get_potential_text(score):
    if score > 75: return "Nivel Notable."
    if score > 50: return "Nivel Medio."
    return "Nivel Bajo."

def get_friction_text(score):
    if score < 20: return "Nivel bajo-medio."
    if score < 40: return "Nivel medio."
    return "Nivel alto."

def get_risk_text(triggers):
    if not triggers: return "No se detectan indicadores críticos."
    return "Patrones detectados:"

def radar_chart():
    data = st.session_state.octagon
    cat = [LABELS_ES.get(k) for k in data.keys()]
    val = list(data.values())
    cat += [cat[0]]; val += [val[0]]
    fig = go.Figure(go.Scatterpolar(r=val, theta=cat, fill='toself', line=dict(color='#5D5FEF'), fillcolor='rgba(93, 95, 239, 0.2)'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, showticklabels=False), bgcolor='rgba(0,0,0,0)'), paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'), showlegend=False, margin=dict(l=40, r=40, t=20, b=20), dragmode=False)
    return fig

# --- HEADER CONSTANTE ---
def draw_header():
    # Header con columnas: Logo (Blanco) a la izquierda, Título derecha
    c1, c2 = st.columns([0.5, 4])
    with c1:
        if os.path.exists("logo_blanco.png"):
            st.image("logo_blanco.png", use_container_width=True)
    with c2:
        st.markdown('<p class="custom-header-title">Simulador S.A.P.E.</p>', unsafe_allow_html=True)
        st.markdown('<p class="custom-header-sub">Sistema de Análisis de la Personalidad Emprendedora</p>', unsafe_allow_html=True)
    st.markdown("---")

# --- 5. APP PRINCIPAL ---
init_session()

# LOGIN
if not st.session_state.get("auth", False):
    # Centrado vertical usando columnas vacías
    _, col_center, _ = st.columns([1, 2, 1])
    with col_center:
        st.markdown('<div class="login-container"><div class="login-card">', unsafe_allow_html=True)
        
        # 1. Logo Centrado
        if os.path.exists("logo_original.png"):
            # Usamos una columna interna de Streamlit para que st.image centre bien
            c_img1, c_img2, c_img3 = st.columns([1, 4, 1])
            with c_img2:
                st.image("logo_original.png", use_container_width=True)
        
        st.markdown("<h3>Audeo | Simulador S.A.P.E.</h3>", unsafe_allow_html=True)
        st.markdown("<p>Acceso Corporativo Seguro</p>", unsafe_allow_html=True)
        
        pwd = st.text_input("Clave de acceso", type="password")
        if st.button("ENTRAR AL SISTEMA", use_container_width=True):
            if pwd == st.secrets["general"]["password"]: st.session_state.auth = True; st.rerun()
            else: st.error("Acceso denegado")
            
        st.markdown('</div></div>', unsafe_allow_html=True)
    st.stop()

# CABECERA GLOBAL (Aparece en todas las páginas internas)
draw_header()

# FASE 1: DATOS
if not st.session_state.data_verified:
    st.markdown("#### 1. Identificación del/a Candidato/a")
    col1, col2 = st.columns(2)
    name = col1.text_input("Nombre Completo")
    age = col2.number_input("Edad", min_value=18, max_value=99, value=None, placeholder="--")
    
    col3, col4 = st.columns(2)
    gender = col3.selectbox("Género", ["Masculino", "Femenino", "Prefiero no decirlo"])
    country = col4.selectbox("País", ["España", "LATAM", "Europa", "Otros"])
    
    col5, col6 = st.columns(2)
    situation = col5.selectbox("Situación", ["Solo", "Con Socios", "Intraemprendimiento"])
    experience = col6.selectbox("Experiencia", ["Primer emprendimiento", "Con éxito previo", "Sin éxito previo"])
    
    st.markdown("<br>", unsafe_allow_html=True)
    consent = st.checkbox("He leído y acepto la Política de Privacidad.")
    st.markdown('<a href="https://www.audeo.es/privacidad" target="_blank" style="color:#5D5FEF;">📄 Ver Documento de Protección de Datos</a>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="validate-btn">', unsafe_allow_html=True)
    if st.button("🔐 VALIDAR DATOS Y CONTINUAR"):
        if name and age and consent:
            st.session_state.user_data = {"name": name, "age": age, "gender": gender, "sector": "", "experience": experience}
            st.session_state.data_verified = True
            st.rerun()
        else:
            st.error("Por favor, completa los campos obligatorios.")
    st.markdown('</div>', unsafe_allow_html=True)

# FASE 2: SECTOR
elif not st.session_state.started:
    st.markdown(f"#### 2. Selecciona el Sector del Proyecto:")
    
    def go_sector(sec):
        all_q = load_questions()
        code = SECTOR_MAP[sec]
        qs = [x for x in all_q if x['SECTOR'].strip().upper() == code]
        if not qs: qs = [x for x in all_q if x['SECTOR'].strip().upper() == "TECH"]
        st.session_state.data = qs
        st.session_state.user_data["sector"] = sec
        st.session_state.started = True
        st.rerun()

    # BOTONERA GIGANTE
    c1, c2, c3, c4 = st.columns(4)
    with c1: 
        st.markdown('<div class="sector-card">', unsafe_allow_html=True)
        if st.button("Startup Tecnológica\n(Scalable)"): go_sector("Startup Tecnológica (Scalable)")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="sector-card">', unsafe_allow_html=True) 
        if st.button("Consultoría /\nServicios Prof."): go_sector("Consultoría / Servicios Profesionales")
        st.markdown('</div>', unsafe_allow_html=True)
    with c3: 
        st.markdown('<div class="sector-card">', unsafe_allow_html=True)
        if st.button("Pequeña y Mediana\nEmpresa (PYME)"): go_sector("Pequeña y Mediana Empresa (PYME)")
        st.markdown('</div>', unsafe_allow_html=True)
    with c4: 
        st.markdown('<div class="sector-card">', unsafe_allow_html=True)
        if st.button("Hostelería y\nRestauración"): go_sector("Hostelería y Restauración")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    c5, c6, c7, c8 = st.columns(4)
    with c5:
        st.markdown('<div class="sector-card">', unsafe_allow_html=True)
        if st.button("Autoempleo /\nFreelance"): go_sector("Autoempleo / Freelance")
        st.markdown('</div>', unsafe_allow_html=True)
    with c6:
        st.markdown('<div class="sector-card">', unsafe_allow_html=True)
        if st.button("Emprendimiento\nSocial"): go_sector("Emprendimiento Social")
        st.markdown('</div>', unsafe_allow_html=True)
    with c7:
        st.markdown('<div class="sector-card">', unsafe_allow_html=True)
        if st.button("Intraemprendimiento"): go_sector("Intraemprendimiento")
        st.markdown('</div>', unsafe_allow_html=True)

# FASE 3: PREGUNTAS
elif not st.session_state.finished:
    row = st.session_state.data[st.session_state.current_step]
    st.progress((st.session_state.current_step + 1) / len(st.session_state.data))
    
    st.markdown(f"### {row['TITULO']}")
    
    c_text, c_opt = st.columns([1.5, 1])
    with c_text:
        st.markdown(f'<div class="diag-text" style="font-size:1.2rem;"><p>{row["NARRATIVA"]}</p></div>', unsafe_allow_html=True)
    with c_opt:
        st.markdown("#### Tu decisión:")
        step = st.session_state.current_step
        
        # Botones de respuesta
        if st.button(row.get('OPCION_A_TXT', 'A'), key=f"A_{step}", use_container_width=True):
            parse_logic(row.get('OPCION_A_LOGIC'))
            st.session_state.current_step += 1
            if st.session_state.current_step >= len(st.session_state.data): st.session_state.finished = True
            st.rerun()
            
        if st.button(row.get('OPCION_B_TXT', 'B'), key=f"B_{step}", use_container_width=True):
            parse_logic(row.get('OPCION_B_LOGIC'))
            st.session_state.current_step += 1
            if st.session_state.current_step >= len(st.session_state.data): st.session_state.finished = True
            st.rerun()
            
        if row.get('OPCION_C_TXT') and row.get('OPCION_C_TXT') != "None":
            if st.button(row.get('OPCION_C_TXT', 'C'), key=f"C_{step}", use_container_width=True):
                parse_logic(row.get('OPCION_C_LOGIC'))
                st.session_state.current_step += 1
                if st.session_state.current_step >= len(st.session_state.data): st.session_state.finished = True
                st.rerun()
        
        if row.get('OPCION_D_TXT') and row.get('OPCION_D_TXT') != "None" and row.get('OPCION_D_TXT') != "":
            if st.button(row.get('OPCION_D_TXT', 'D'), key=f"D_{step}", use_container_width=True):
                parse_logic(row.get('OPCION_D_LOGIC'))
                st.session_state.current_step += 1
                if st.session_state.current_step >= len(st.session_state.data): st.session_state.finished = True
                st.rerun()

# FASE 4: RESULTADOS
else:
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
    
    # Generación PDF
    pdf_bytes = create_pdf_report(ire, avg, friction, triggers, fric_reasons, delta, st.session_state.user_data, st.session_state.octagon)
    
    # Botón de descarga CSS forzado
    st.download_button(
        label="📥 DESCARGAR INFORME COMPLETO (PDF)",
        data=pdf_bytes,
        file_name=f"Informe_SAPE_{st.session_state.user_id}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
    
    if st.button("Reiniciar"):
        st.session_state.clear()
        st.rerun()