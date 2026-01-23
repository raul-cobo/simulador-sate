import streamlit as st
import csv
import os
import random
import string
import io
from datetime import datetime
import plotly.graph_objects as go
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Audeo | Simulador S.A.P.E.", page_icon="🧬", layout="wide")

# --- 2. INYECCIÓN CSS (CORRECCIONES VISUALES) ---
def local_css():
    st.markdown("""
    <style>
        /* Ocultar elementos nativos */
        header, [data-testid="stHeader"], .stAppHeader, [data-testid="stToolbar"] { display: none !important; }
        footer, .stDeployButton { display: none !important; }
        .main .block-container { padding-top: 2rem !important; }

        /* FONDO GLOBAL */
        .stApp { background-color: #050A1F; color: #FFFFFF; }
        
        /* FUERZA TEXTO BLANCO GENERAL (Menos en login) */
        h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, div[data-testid="stMarkdownContainer"] p { 
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
        
        /* BOTONES DE SECTOR (IGUALAR TAMAÑOS) */
        .sector-card button {
            height: 140px !important; /* Altura fija para todos */
            min-height: 140px !important;
            width: 100% !important;
            white-space: normal !important; /* Permitir salto de línea */
            font-size: 1.1rem !important;
            background-color: #0F1629 !important;
            color: white !important;
            border: 2px solid #2D3748 !important;
            display: flex;
            align-items: center;
            justify_content: center;
        }
        .sector-card button:hover {
            border-color: #5D5FEF !important;
            background-color: #1A202C !important;
            transform: translateY(-2px);
        }

        /* CAJA DE LOGIN (Blanca con texto negro forzado) */
        .login-card { 
            background-color: white; 
            padding: 3rem; 
            border-radius: 15px; 
            text-align: center; 
            margin-top: 50px;
        }
        /* Forzamos negro SOLO dentro de la login-card */
        .login-card h1, .login-card h2, .login-card h3, .login-card p, .login-card div {
            color: #000000 !important;
        }
        .login-card input { 
            background-color: #f0f2f6 !important; 
            color: #000000 !important; 
            border: 1px solid #ccc !important; 
        }
        
        /* HEADER EN APP (No Login) */
        .custom-header { font-size: 2rem; font-weight: bold; color: white !important; margin-bottom: 0px; }
        .custom-sub { font-size: 1.1rem; color: #5D5FEF !important; margin-bottom: 2rem; }

        /* TEXTO RESULTADOS */
        .diag-text { background-color: #0F1629; padding: 15px; border-radius: 8px; border-left: 4px solid #5D5FEF; margin-bottom: 10px; }
        .diag-text p { color: #E2E8F0 !important; margin: 0; }
        
        /* VALIDAR BTN */
        .validate-btn button { background-color: #5D5FEF !important; font-size: 1.2rem !important; border: none !important; }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- 3. VARIABLES Y LÓGICA ---
LABELS_ES = {
    "achievement": "Necesidad de Logro", "risk_propensity": "Propensión al Riesgo",
    "innovativeness": "Innovatividad", "locus_control": "Locus de Control Interno",
    "self_efficacy": "Autoeficacia", "autonomy": "Autonomía",
    "ambiguity_tolerance": "Optimismo / Tolerancia a la Incertidumbre",
    "emotional_stability": "Tolerancia al Estrés / Estabilidad Emocional"
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
    if f["mischievous"] > 25: triggers.append("Riesgo de Desalineamiento Normativo")
    if f["arrogant"] > 25: triggers.append("Estilo Dominante / Rigidez Potencial")
    if f["passive_aggressive"] > 20: triggers.append("Fricción Relacional Latente")
    if o["achievement"] > 85 and o["emotional_stability"] < 40: triggers.append("Riesgo de Agotamiento Operativo (Burnout)")
    if o["risk_propensity"] > 85 and f["cautious"] < 10: triggers.append("Perfil de Riesgo Desmedido")
    if f["diligent"] > 60: triggers.append("Bloqueo por Sobre-Análisis")
    if f["dependent"] > 55: triggers.append("Alta Necesidad de Supervisión")
    ire = max(0, min(100, avg - (friction * 0.8) - (len(triggers) * 3)))
    return round(ire, 2), round(avg, 2), round(friction, 2), triggers

# --- PDF GENERATOR (CORREGIDO) ---
def create_pdf_report(ire, avg, friction, triggers, user, stats):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    
    # 1. CABECERA DIAGONAL (Método drawPath para evitar crash)
    p.setFillColorRGB(0.02, 0.04, 0.12) # Navy
    # Dibujamos un rectángulo base
    p.rect(0, h-140, w, 140, fill=1, stroke=0)
    
    # Dibujamos triángulo blanco superior izquierdo
    p.setFillColorRGB(1, 1, 1)
    path = p.beginPath()
    path.moveTo(0, h)      # Top Left
    path.lineTo(w, h)      # Top Right
    path.lineTo(0, h-140)  # Bottom Left
    path.close()
    p.drawPath(path, fill=1, stroke=0) # CORRECCIÓN AQUÍ: drawPath en vez de fillPath
    
    # 2. LOGO
    logo_path = "logo_original.png"
    if os.path.exists(logo_path):
        try:
            img = ImageReader(logo_path)
            # Logo más grande, a la izquierda, sobre lo blanco
            p.drawImage(img, 30, h-110, width=160, height=80, preserveAspectRatio=True, mask='auto')
        except: pass
    
    # 3. TÍTULO
    p.setFillColorRGB(1, 1, 1) # Blanco sobre azul
    p.setFont("Helvetica-Bold", 18)
    p.drawRightString(w-30, h-50, "INFORME TÉCNICO S.A.P.E.")
    p.setFont("Helvetica", 10)
    p.drawRightString(w-30, h-65, "Sistema de Análisis de la Personalidad Emprendedora")
    
    # 4. DATOS
    y_start = h - 170
    p.setFillColorRGB(0,0,0)
    p.setFont("Helvetica-Bold", 11)
    p.drawString(40, y_start, f"ID Usuario: {st.session_state.user_id}")
    p.drawString(40, y_start-15, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}")
    p.drawString(40, y_start-30, f"Sector: {user.get('sector', 'N/A')}")
    
    # 5. RESULTADOS
    y = y_start - 70
    p.setFont("Helvetica-Bold", 14)
    p.setFillColorRGB(0.02, 0.04, 0.12)
    p.drawString(40, y, "1. Métricas Principales")
    p.line(40, y-5, w-40, y-5)
    y -= 30
    
    # Potencial
    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, y, f"POTENCIAL ({avg}/100):")
    p.setFont("Helvetica", 10)
    p.drawString(50, y-15, get_potential_text(avg))
    y -= 45
    
    # Fricción
    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, y, f"FRICCIÓN ({friction}/100):")
    p.setFont("Helvetica", 10)
    if friction < 20: txt = "Nivel bajo. Resistencia operativa mínima."
    elif friction < 45: txt = "Nivel medio. Presencia moderada de bloqueos."
    else: txt = "Nivel alto. Importante coste operativo."
    p.drawString(50, y-15, txt)
    y -= 45
    
    # IRE
    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, y, f"IRE FINAL ({ire}/100):")
    p.setFont("Helvetica", 10)
    p.drawString(50, y-15, get_ire_text(ire))
    y -= 50
    
    # 6. GRÁFICO BARRAS
    p.setFont("Helvetica-Bold", 14)
    p.drawString(40, y, "2. Análisis Dimensional")
    p.line(40, y-5, w-40, y-5)
    y -= 30
    
    for k, v in stats.items():
        label = LABELS_ES.get(k, k)
        p.setFont("Helvetica-Bold", 9)
        p.drawString(50, y, label)
        # Barra fondo
        p.setFillColorRGB(0.9, 0.9, 0.9)
        p.rect(280, y, 200, 8, fill=1, stroke=0)
        # Barra valor
        if v > 75: p.setFillColorRGB(0.2, 0.6, 0.2)
        elif v > 45: p.setFillColorRGB(0.2, 0.3, 0.7)
        else: p.setFillColorRGB(0.8, 0.3, 0.3)
        p.rect(280, y, (v/100)*200, 8, fill=1, stroke=0)
        p.setFillColorRGB(0,0,0)
        p.drawString(490, y, str(round(v, 1)))
        y -= 20
        
    # 7. ALERTAS
    y -= 20
    p.setFont("Helvetica-Bold", 14)
    p.drawString(40, y, "3. Alertas Detectadas")
    p.line(40, y-5, w-40, y-5)
    y -= 30
    p.setFont("Helvetica", 10)
    p.drawString(50, y, get_risk_text(triggers))
    y -= 20
    if triggers:
        for t in triggers:
            p.setFillColorRGB(0.7, 0, 0)
            p.drawString(60, y, f"• {t}")
            y -= 15
            
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

def get_ire_text(score):
    if score > 75: return "Nivel positivo. El perfil opera en un rango de alta sostenibilidad."
    if score > 50: return "Nivel medio. Funcional, pero requiere monitorizar costes operativos."
    return "Nivel comprometido. Riesgos de continuidad por discrepancia potencial/ejecución."

def get_potential_text(score):
    if score > 75: return "Nivel Alto. Recursos cognitivos y actitudinales superiores."
    if score > 50: return "Nivel Medio. Recursos suficientes para la operativa estándar."
    return "Nivel Bajo. Requiere plan de desarrollo intensivo."

def get_risk_text(triggers):
    if not triggers: return "No se detectan indicadores críticos."
    return "Se detectan patrones conductuales que pueden generar ineficiencias:"

def radar_chart():
    data = st.session_state.octagon
    cat = [LABELS_ES.get(k) for k in data.keys()]
    val = list(data.values())
    cat += [cat[0]]; val += [val[0]]
    fig = go.Figure(go.Scatterpolar(r=val, theta=cat, fill='toself', line=dict(color='#5D5FEF'), fillcolor='rgba(93, 95, 239, 0.2)'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, showticklabels=False), bgcolor='rgba(0,0,0,0)'), paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'), showlegend=False, margin=dict(l=40, r=40, t=20, b=20), dragmode=False)
    return fig

# --- 5. APP PRINCIPAL ---
init_session()

# LOGIN
if not st.session_state.get("auth", False):
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        # Logo grande (300px)
        if os.path.exists("logo_original.png"):
            st.image("logo_original.png", width=300)
        
        # TÍTULO NEGRO FORZADO EN HTML
        st.markdown("<h1 style='color:black !important; font-size: 2rem; margin-top:10px;'>Audeo | Simulador S.A.P.E.</h1>", unsafe_allow_html=True)
        st.markdown("<p style='color:#555 !important;'>Acceso Corporativo Seguro</p>", unsafe_allow_html=True)
        
        pwd = st.text_input("Clave de acceso", type="password")
        if st.button("ENTRAR AL SISTEMA", use_container_width=True):
            if pwd == st.secrets["general"]["password"]: st.session_state.auth = True; st.rerun()
            else: st.error("Acceso denegado")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# HEADER INTERNO
c1, c2 = st.columns([0.5, 4])
with c1:
    if os.path.exists("logo_blanco.png"): st.image("logo_blanco.png")
with c2:
    st.markdown('<div class="custom-header">Simulador S.A.P.E.</div>', unsafe_allow_html=True)
    st.markdown('<div class="custom-sub">Sistema de Análisis de la Personalidad Emprendedora</div>', unsafe_allow_html=True)
st.markdown("---")

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
        
        # Opciones A, B, C
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
        
        # OPCIÓN D (ACTIVADA)
        if row.get('OPCION_D_TXT') and row.get('OPCION_D_TXT') != "None" and row.get('OPCION_D_TXT') != "":
            if st.button(row.get('OPCION_D_TXT', 'D'), key=f"D_{step}", use_container_width=True):
                parse_logic(row.get('OPCION_D_LOGIC'))
                st.session_state.current_step += 1
                if st.session_state.current_step >= len(st.session_state.data): st.session_state.finished = True
                st.rerun()

# FASE 4: RESULTADOS
else:
    ire, avg, friction, triggers = calculate_results()
    
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
    pdf_bytes = create_pdf_report(ire, avg, friction, triggers, st.session_state.user_data, st.session_state.octagon)
    
    st.download_button(
        "📥 DESCARGAR INFORME COMPLETO (PDF)",
        pdf_bytes,
        file_name=f"Informe_SAPE_{st.session_state.user_id}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
    
    if st.button("Reiniciar"):
        st.session_state.clear()
        st.rerun()