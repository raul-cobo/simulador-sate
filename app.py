import streamlit as st
import csv
import os
import random
import string
import json
import requests
import io
from datetime import datetime
import plotly.graph_objects as go
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Audeo | Simulador S.A.P.E.", page_icon="🧬", layout="wide")

# --- 2. INYECCIÓN CSS (DISEÑO NAVY & ELECTRIC) ---
def local_css():
    st.markdown("""
    <style>
        /* --- LIMPIEZA DE INTERFAZ (NUCLEAR) --- */
        header, [data-testid="stHeader"], .stAppHeader, [data-testid="stToolbar"] { display: none !important; }
        button[title="Manage app"], .stDeployButton, footer { display: none !important; }
        .main .block-container { padding-top: 1rem !important; margin-top: -2rem !important; }

        /* --- FONDO Y TIPOGRAFÍA --- */
        .stApp {
            background-color: #050A1F; /* Navy Profundo */
            color: #FFFFFF;
        }
        html, body, [class*="css"] {
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            font-weight: 300;
        }

        /* --- TARJETA LOGIN BLANCA --- */
        .login-card {
            background-color: white;
            padding: 3rem;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            margin-bottom: 20px;
            max-width: 500px;
            margin-left: auto;
            margin-right: auto;
        }
        
        /* --- INPUTS MODIFICADOS --- */
        .stTextInput > div > div > input, .stNumberInput > div > div > input, .stSelectbox > div > div > div {
            background-color: #0F1629;
            color: white;
            border: 1px solid #2D3748;
            border-radius: 6px;
        }
        .stSelectbox > label, .stTextInput > label, .stNumberInput > label, .stCheckbox > label {
            color: #A0AEC0 !important;
            font-size: 0.9rem;
        }
        .stCheckbox p { color: #E2E8F0 !important; font-size: 0.95rem !important; }

        /* --- BOTONES --- */
        .validate-btn > button {
            width: 100% !important;
            background-color: #5D5FEF !important;
            color: white !important;
            font-weight: bold !important;
            padding: 15px !important;
            border-radius: 8px !important;
            border: none !important;
            font-size: 1.1rem !important;
        }
        .validate-btn > button:hover { background-color: #4B4DCE !important; transform: scale(1.02); }

        .sector-btn > button {
            background-color: #0F1629 !important;
            border: 1px solid #5D5FEF !important;
            color: white !important;
            height: 100px !important;
            font-weight: 600 !important;
            border-radius: 12px !important;
        }
        .sector-btn > button:hover { background-color: #5D5FEF !important; transform: translateY(-5px); }

        .answer-btn > button {
            width: 100% !important;
            background-color: #1A202C !important;
            color: #E2E8F0 !important;
            border: 1px solid #4A5568 !important;
            padding: 20px !important;
            border-radius: 8px !important;
            text-align: left !important;
        }
        .answer-btn > button:hover { border-color: #5D5FEF !important; color: #5D5FEF !important; background-color: #0F1629 !important; }

        /* --- BARRA DE PROGRESO Y NARRATIVA --- */
        div[data-testid="stProgressBar"] > div > div > div > div { background-color: #5D5FEF !important; }
        .big-narrative {
            font-size: 1.25rem; line-height: 1.6; color: #E2E8F0;
            background-color: #0F1629; padding: 30px; border-radius: 12px;
            border-left: 5px solid #5D5FEF;
        }

        /* --- HEADER LOGO --- */
        .header-title {
            font-size: 2.5rem; font-weight: 700;
            background: -webkit-linear-gradient(left, #FFFFFF, #A0AEC0);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        .header-subtitle { font-size: 1.2rem; color: #5D5FEF; font-weight: 400; margin-bottom: 2rem; }
        .legal-link a { color: #5D5FEF !important; text-decoration: none; font-size: 0.85rem; }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- 3. LÓGICA DE NEGOCIO ---
SECTOR_MAPPING = {
    "Startup Tecnológica (Scalable)": "TECH", "Consultoría / Servicios Profesionales": "CONSULTORIA",
    "Pequeña y Mediana Empresa (PYME)": "PYME", "Hostelería y Restauración": "HOSTELERIA",
    "Autoempleo / Freelance": "AUTOEMPLEO", "Emprendimiento Social": "SOCIAL",
    "Intraemprendimiento": "INTRA"
}

VARIABLE_MAP = {
    "achievement": "achievement", "logro": "achievement", "risk_propensity": "risk_propensity", "riesgo": "risk_propensity",
    "innovativeness": "innovativeness", "innovacion": "innovativeness", "locus_control": "locus_control", "locus": "locus_control",
    "self_efficacy": "self_efficacy", "autoeficacia": "self_efficacy", "autonomy": "autonomy", "autonomia": "autonomy",
    "ambiguity_tolerance": "ambiguity_tolerance", "tolerancia": "ambiguity_tolerance", "emotional_stability": "emotional_stability", "estabilidad": "emotional_stability",
    "excitable": "excitable", "skeptical": "skeptical", "cautious": "cautious", "reserved": "reserved", "passive_aggressive": "passive_aggressive",
    "arrogant": "arrogant", "mischievous": "mischievous", "melodramatic": "melodramatic", "imaginative": "imaginative", "diligent": "diligent", "dependent": "dependent"
}

LABELS_ES = {
    "achievement": "Logro", "risk_propensity": "Riesgo", "innovativeness": "Innovación", "locus_control": "Locus Control",
    "self_efficacy": "Autoeficacia", "autonomy": "Autonomía", "ambiguity_tolerance": "Tol. Incertidumbre", "emotional_stability": "Estabilidad"
}

def generate_id(): return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def init_session():
    if 'octagon' not in st.session_state:
        st.session_state.octagon = {k: 50 for k in ["achievement", "risk_propensity", "innovativeness", "locus_control", "self_efficacy", "autonomy", "ambiguity_tolerance", "emotional_stability"]}
        st.session_state.flags = {k: 0 for k in ["excitable", "skeptical", "cautious", "reserved", "passive_aggressive", "arrogant", "mischievous", "melodramatic", "imaginative", "diligent", "dependent"]}
        st.session_state.current_step = 0
        st.session_state.finished = False
        st.session_state.started = False 
        st.session_state.data_verified = False
        st.session_state.data = []
        st.session_state.choices_log = [""] * 30 
        st.session_state.user_id = generate_id()
        st.session_state.user_data = {}

def load_questions():
    try:
        filename = 'SATE_v1.csv'
        if not os.path.exists(filename): return []
        with open(filename, encoding='utf-8-sig') as f: return list(csv.DictReader(f, delimiter=';'))
    except: return []

def parse_logic(logic_str, opt_idx, step):
    st.session_state.choices_log[step] = str(opt_idx)
    if not logic_str: return
    for action in logic_str.split('|'):
        parts = action.strip().split()
        if len(parts) < 2: continue
        var, val = VARIABLE_MAP.get(parts[0].lower()), int(parts[1])
        if var in st.session_state.flags: st.session_state.flags[var] = max(0, st.session_state.flags[var] + val)
        elif var in st.session_state.octagon: st.session_state.octagon[var] = max(0, min(100, st.session_state.octagon[var] + val))

# --- CÁLCULO PROFESIONAL ---
def calculate_results():
    o, f = st.session_state.octagon, st.session_state.flags
    avg = sum(o.values()) / 8
    
    # Penalizaciones suavizadas
    toxic_raw = sum([f[k] for k in ["mischievous", "arrogant", "passive_aggressive", "excitable", "melodramatic"]])
    toxic_penalty = toxic_raw * 0.4
    
    excess_raw = sum([max(0, f[k]-50) for k in ["diligent", "cautious", "dependent", "skeptical", "reserved", "imaginative"]])
    excess_penalty = excess_raw * 0.1
    
    triggers = []
    
    # Terminología profesional
    if f["mischievous"] > 25: triggers.append("RIESGO DE DESALINEAMIENTO NORMATIVO")
    if f["arrogant"] > 25: triggers.append("ESTILO DOMINANTE / POSIBLE RIGIDEZ")
    if f["passive_aggressive"] > 20: triggers.append("FRICCIÓN RELACIONAL LATENTE")
    if o["achievement"] > 85 and o["emotional_stability"] < 30: triggers.append("RIESGO DE AGOTAMIENTO OPERATIVO (BURNOUT)")
    if o["risk_propensity"] > 85 and f["cautious"] < 10: triggers.append("PERFIL DE RIESGO DESMEDIDO")
    if f["diligent"] > 60: triggers.append("BLOQUEO POR SOBRE-ANÁLISIS")
    if f["dependent"] > 55: triggers.append("NECESIDAD DE SUPERVISIÓN CONTINUA")

    ire = max(0, min(100, avg - toxic_penalty - excess_penalty - (len(triggers)*2.5)))
    return round(ire, 2), round(avg, 2), round(toxic_penalty, 2), triggers

# --- PDF ESTILO AUDITORÍA (HIGH TICKET) ---
def create_pdf_report(ire, avg, toxic, triggers, user, stats):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    
    # 1. CABECERA CORPORATIVA NAVY
    p.setFillColorRGB(0.02, 0.04, 0.12) # Navy Audeo
    p.rect(0, h-120, w, 120, fill=1, stroke=0)
    
    # Logo en Cabecera (Blanco simulado o carga archivo)
    try:
        # Intentamos cargar el logo original para ponerlo sobre una caja blanca pequeña o directo si es blanco
        # Para que quede profesional, pintamos el texto en blanco
        p.setFillColorRGB(1, 1, 1)
        p.setFont("Helvetica-Bold", 24)
        p.drawString(50, h-60, "AUDEO INTELLIGENCE")
        p.setFont("Helvetica", 12)
        p.drawString(50, h-80, "Due Diligence de Talento Emprendedor")
        
        # Si existe el logo original, lo ponemos en pequeñito a la derecha
        logo_path = "logo_original.png"
        if os.path.exists(logo_path):
             # Caja blanca para el logo
            p.setFillColorRGB(1, 1, 1)
            p.rect(w-120, h-100, 80, 80, fill=1, stroke=0)
            p.drawImage(logo_path, w-115, h-95, width=70, height=70, preserveAspectRatio=True, mask='auto')

    except:
        pass

    # 2. DATOS DEL CANDIDATO
    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, h-160, "DATOS DEL ANÁLISIS")
    p.line(50, h-165, w-50, h-165)
    
    p.setFont("Helvetica", 10)
    p.drawString(50, h-185, f"Candidato: {user.get('name')}")
    p.drawString(300, h-185, f"ID Referencia: {st.session_state.user_id}")
    p.drawString(50, h-205, f"Sector: {user.get('sector')}")
    p.drawString(300, h-205, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}")

    # 3. RESULTADOS MACRO (CAJAS DE COLOR)
    y_metrics = h-260
    
    # Caja IRE
    p.setFillColorRGB(0.95, 0.95, 0.95) # Gris muy claro
    p.roundRect(50, y_metrics-40, 200, 60, 5, fill=1, stroke=0)
    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica-Bold", 14)
    p.drawCentredString(150, y_metrics-10, "Índice IRE")
    p.setFont("Helvetica-Bold", 26)
    if ire > 70: p.setFillColorRGB(0, 0.6, 0) # Verde
    elif ire > 45: p.setFillColorRGB(0.8, 0.6, 0) # Naranja
    else: p.setFillColorRGB(0.8, 0, 0) # Rojo
    p.drawCentredString(150, y_metrics-35, f"{ire}/100")

    # Caja POTENCIAL
    p.setFillColorRGB(0.95, 0.95, 0.95)
    p.roundRect(300, y_metrics-40, 200, 60, 5, fill=1, stroke=0)
    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica-Bold", 14)
    p.drawCentredString(400, y_metrics-10, "Potencial Operativo")
    p.setFont("Helvetica-Bold", 26)
    p.drawCentredString(400, y_metrics-35, f"{avg}/100")

    # 4. ALERTAS Y RIESGOS
    y_pos = y_metrics - 100
    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y_pos, "DETECCIÓN DE RIESGOS Y ALERTAS")
    p.line(50, y_pos-5, w-50, y_pos-5)
    y_pos -= 30
    
    if triggers:
        for t in triggers:
            # Icono de alerta rojo
            p.setFillColorRGB(0.8, 0.1, 0.1)
            p.setFont("Helvetica-Bold", 14)
            p.drawString(50, y_pos, "!") 
            # Texto alerta
            p.setFillColorRGB(0.2, 0.2, 0.2)
            p.setFont("Helvetica", 10)
            p.drawString(70, y_pos, t)
            y_pos -= 20
    else:
        p.setFillColorRGB(0, 0.5, 0)
        p.setFont("Helvetica-Bold", 10)
        p.drawString(50, y_pos, "✓ No se han detectado indicadores críticos de riesgo en esta evaluación.")
        y_pos -= 20

    # 5. DESGLOSE COMPETENCIAL
    y_pos -= 30
    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y_pos, "PERFIL COMPETENCIAL (OCTÓGONO)")
    p.line(50, y_pos-5, w-50, y_pos-5)
    y_pos -= 30

    # Dibujar barritas simples
    p.setFont("Helvetica", 9)
    for k, v in stats.items():
        label = LABELS_ES.get(k, k)
        # Nombre
        p.setFillColorRGB(0,0,0)
        p.drawString(50, y_pos, label)
        # Barra fondo
        p.setFillColorRGB(0.9, 0.9, 0.9)
        p.rect(180, y_pos, 200, 8, fill=1, stroke=0)
        # Barra valor (Azul Audeo)
        p.setFillColorRGB(0.36, 0.37, 0.93) # #5D5FEF
        bar_width = (v / 100) * 200
        p.rect(180, y_pos, bar_width, 8, fill=1, stroke=0)
        # Valor numérico
        p.setFillColorRGB(0,0,0)
        p.drawString(390, y_pos, str(round(v, 1)))
        y_pos -= 20
        
        if y_pos < 50:
            p.showPage()
            y_pos = h - 50

    # FOOTER
    p.setFont("Helvetica-Oblique", 8)
    p.setFillColorRGB(0.5, 0.5, 0.5)
    p.drawCentredString(w/2, 30, "Documento confidencial generado por Audeo Intelligence Algorithms. Prohibida su distribución.")
    
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# --- GRÁFICA OPTIMIZADA ---
def radar_chart():
    data = st.session_state.octagon
    cat = [LABELS_ES.get(k) for k in data.keys()]
    val = list(data.values())
    cat += [cat[0]]; val += [val[0]]
    fig = go.Figure(go.Scatterpolar(r=val, theta=cat, fill='toself', line=dict(color='#5D5FEF', width=2), fillcolor='rgba(93, 95, 239, 0.2)'))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, linecolor='#2D3748'), bgcolor='rgba(0,0,0,0)'),
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white', size=11),
        showlegend=False,
        margin=dict(l=30, r=30, t=20, b=20),
        dragmode=False
    )
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig

# --- 4. SISTEMA DE LOGIN ---
def login_screen():
    if st.session_state.get("auth", False): return True
    
    # Centrado absoluto con columnas
    c1, c2, c3 = st.columns([1, 6, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        # TARJETA BLANCA DE LOGIN
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        
        # Intentamos cargar logo
        try:
            logo_login = Image.open("logo_original.png")
            st.image(logo_login, width=250) 
        except:
            st.warning("⚠️ Sube 'logo_original.png'")

        st.markdown("<h3 style='color:black; margin-top:20px;'>Acceso Corporativo</h3>", unsafe_allow_html=True)
        
        # Inputs dentro de la tarjeta blanca (truco: usar st.form o simplemente inputs)
        # Nota: Los inputs de streamlit por defecto son oscuros por mi CSS global.
        # Para que se vean bien en lo blanco, el CSS de inputs ya tiene borde y fondo oscuro que contrasta bien.
        
        pwd = st.text_input("Clave de acceso", type="password", key="pwd_in")
        
        if st.button("ENTRAR AL SISTEMA", use_container_width=True):
            if pwd == st.secrets["general"]["password"]: st.session_state.auth = True; st.rerun()
            else: st.error("⛔ Credenciales no válidas")
            
        st.markdown('</div>', unsafe_allow_html=True)
            
    return False

# --- 5. FLUJO PRINCIPAL ---
init_session()

if not login_screen(): st.stop()

# CARGAR LOGOS
try:
    logo_header = Image.open("logo_blanco.png") 
    logo_final = Image.open("logo_original.png") 
except:
    logo_header = None
    logo_final = None

if not st.session_state.started:
    # --- PANTALLA DE INICIO ---
    c_head_logo, c_head_txt = st.columns([0.8, 5])
    with c_head_logo:
        if logo_header: st.image(logo_header, use_container_width=True)
    with c_head_txt:
        st.markdown('<div class="header-title">AUDEO | S.A.P.E.</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="header-subtitle">Sistema de Análisis de la Personalidad Emprendedora</div>', unsafe_allow_html=True)
    st.markdown("---")

    # FASE 1: RECOGIDA DE DATOS
    if not st.session_state.data_verified:
        st.write("#### 1. Identificación del Candidato")
        
        c1, c2, c3 = st.columns(3)
        name = c1.text_input("Nombre Completo (Uso interno)")
        age = c2.number_input("Edad", min_value=18, max_value=99, value=None, placeholder="--")
        gender = c3.selectbox("Género", ["Masculino", "Femenino", "Prefiero no decirlo"])

        c4, c5, c6 = st.columns(3)
        country = c4.selectbox("País / Región", ["España", "LATAM", "Europa", "Otros"])
        situation = c5.selectbox("Situación", ["Solo", "Con Socios", "Intraemprendimiento"])
        experience = c6.selectbox("Experiencia previa", ["Primer emprendimiento", "Emprendimientos sin éxito", "Emprendimientos con éxito"])

        st.markdown("<br>", unsafe_allow_html=True)
        consent = st.checkbox("He leído y acepto la Política de Privacidad y autorizo el tratamiento de mis datos.")
        st.markdown('<div class="legal-link"><a href="#" target="_blank">📄 Ver Documento de Protección de Datos (RGPD)</a></div>', unsafe_allow_html=True)
        
        st.markdown('<div class="validate-btn">', unsafe_allow_html=True)
        if st.button("🔐 VALIDAR DATOS Y ACCEDER AL SIMULADOR"):
            if not name: st.error("⚠️ Falta el Nombre.")
            elif age is None: st.error("⚠️ Falta la Edad.")
            elif not consent: st.error("⚠️ Debes aceptar la política de datos.")
            else:
                st.session_state.user_data = {"name": name, "age": age, "gender": gender, "country": country, "situation": situation, "experience": experience}
                st.session_state.data_verified = True
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # FASE 2: SELECCIÓN DE SECTOR
    else:
        st.success(f"✅ Identidad verificada: {st.session_state.user_data['name']}")
        st.markdown("#### 2. Selecciona el Sector del Proyecto para iniciar:")
        
        def start_game(sector_name):
            all_q = load_questions()
            code = SECTOR_MAPPING[sector_name]
            qs = [q for q in all_q if q['SECTOR'].strip().upper() == code]
            if not qs: qs = [q for q in all_q if q['SECTOR'].strip().upper() == "TECH"]
            st.session_state.data = qs
            st.session_state.user_data["sector"] = sector_name
            st.session_state.started = True
            st.rerun()

        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            st.markdown('<div class="sector-btn">', unsafe_allow_html=True)
            if st.button("Startup Tecnológica\n(Scalable)", use_container_width=True): start_game("Startup Tecnológica (Scalable)")
            st.markdown('</div>', unsafe_allow_html=True)
        with col_b:
            st.markdown('<div class="sector-btn">', unsafe_allow_html=True)
            if st.button("Consultoría /\nServicios Prof.", use_container_width=True): start_game("Consultoría / Servicios Profesionales")
            st.markdown('</div>', unsafe_allow_html=True)
        with col_c:
            st.markdown('<div class="sector-btn">', unsafe_allow_html=True)
            if st.button("Pequeña y Mediana\nEmpresa (PYME)", use_container_width=True): start_game("Pequeña y Mediana Empresa (PYME)")
            st.markdown('</div>', unsafe_allow_html=True)
        with col_d:
            st.markdown('<div class="sector-btn">', unsafe_allow_html=True)
            if st.button("Hostelería y\nRestauración", use_container_width=True): start_game("Hostelería y Restauración")
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        _, col_e, col_f, col_g, _ = st.columns([0.5, 1, 1, 1, 0.5])
        with col_e:
            st.markdown('<div class="sector-btn">', unsafe_allow_html=True)
            if st.button("Autoempleo /\nFreelance", use_container_width=True): start_game("Autoempleo / Freelance")
            st.markdown('</div>', unsafe_allow_html=True)
        with col_f:
            st.markdown('<div class="sector-btn">', unsafe_allow_html=True)
            if st.button("Emprendimiento\nSocial", use_container_width=True): start_game("Emprendimiento Social")
            st.markdown('</div>', unsafe_allow_html=True)
        with col_g:
            st.markdown('<div class="sector-btn">', unsafe_allow_html=True)
            if st.button("Intraemprendimiento\nCorporativo", use_container_width=True): start_game("Intraemprendimiento")
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("⬅️ Corregir mis datos"): st.session_state.data_verified = False; st.rerun()

elif not st.session_state.finished:
    # --- PANTALLA PREGUNTAS ---
    c_q_logo, _ = st.columns([0.5, 5])
    with c_q_logo:
        if logo_header: st.image(logo_header, use_container_width=True)
    
    st.markdown("---")
    
    row = st.session_state.data[st.session_state.current_step]
    st.progress((st.session_state.current_step + 1) / len(st.session_state.data))
    st.markdown(f"### {row['TITULO']}")
    
    col_narrative, col_options = st.columns([1.2, 1]) 
    with col_narrative:
        st.markdown(f'<div class="big-narrative">{row["NARRATIVA"]}</div>', unsafe_allow_html=True)
    with col_options:
        st.markdown("#### ¿Qué harías tú?")
        st.markdown("<br>", unsafe_allow_html=True)
        step = st.session_state.current_step
        
        st.markdown('<div class="answer-btn">', unsafe_allow_html=True)
        if st.button(row.get('OPCION_A_TXT', 'A'), key=f"A_{step}"):
            parse_logic(row.get('OPCION_A_LOGIC'), 1, step)
            st.session_state.current_step += 1
            if st.session_state.current_step >= len(st.session_state.data): st.session_state.finished = True
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="answer-btn">', unsafe_allow_html=True)
        if st.button(row.get('OPCION_B_TXT', 'B'), key=f"B_{step}"):
            parse_logic(row.get('OPCION_B_LOGIC'), 2, step)
            st.session_state.current_step += 1
            if st.session_state.current_step >= len(st.session_state.data): st.session_state.finished = True
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        if row.get('OPCION_C_TXT') and row.get('OPCION_C_TXT') != "None":
            st.markdown('<div class="answer-btn">', unsafe_allow_html=True)
            if st.button(row.get('OPCION_C_TXT', 'C'), key=f"C_{step}"):
                parse_logic(row.get('OPCION_C_LOGIC'), 3, step)
                st.session_state.current_step += 1
                if st.session_state.current_step >= len(st.session_state.data): st.session_state.finished = True
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        if row.get('OPCION_D_TXT') and row.get('OPCION_D_TXT') != "None":
            st.markdown('<div class="answer-btn">', unsafe_allow_html=True)
            if st.button(row.get('OPCION_D_TXT', 'D'), key=f"D_{step}"):
                parse_logic(row.get('OPCION_D_LOGIC'), 4, step)
                st.session_state.current_step += 1
                if st.session_state.current_step >= len(st.session_state.data): st.session_state.finished = True
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

else:
    # --- PANTALLA RESULTADOS ---
    c_res_logo, c_res_title = st.columns([1, 5])
    with c_res_logo: 
        if logo_final: st.image(logo_final)
    with c_res_title:
        st.header(f"Informe Ejecutivo S.A.P.E. | {st.session_state.user_data['name']}")
        st.caption(f"ID Referencia: {st.session_state.user_id} | Sector: {st.session_state.user_data['sector']}")

    st.divider()
    
    ire, avg, toxic, triggers = calculate_results()
    
    k1, k2, k3 = st.columns(3)
    k1.metric("Índice IRE", f"{ire}/100", delta="Resiliencia"); k2.metric("Potencial", f"{avg}/100"); k3.metric("Nivel de Fricción", toxic, delta_color="inverse")

    c_chart, c_txt = st.columns([1, 1])
    with c_chart: 
        st.plotly_chart(radar_chart(), use_container_width=True, config={'displayModeBar': False})
    with c_txt:
        st.markdown("### Diagnóstico")
        if ire > 75: st.success("Perfil de Alta Resiliencia. Capacidad de gestión óptima.")
        elif ire > 45: st.warning("Perfil Equilibrado. Requiere seguimiento.")
        else: st.error("Perfil con Riesgos Operativos Detectados.")
        
        if triggers:
            st.markdown("#### ⚠️ Áreas de Atención Prioritaria")
            for t in triggers: st.markdown(f"- {t}")

    st.markdown("<br>", unsafe_allow_html=True)
    pdf_data = create_pdf_report(ire, avg, toxic, triggers, st.session_state.user_data, st.session_state.octagon)
    st.download_button("📥 DESCARGAR INFORME EJECUTIVO (PDF)", pdf_data, f"SAPE_{st.session_state.user_id}.pdf", "application/pdf", use_container_width=True)
    
    if st.button("Reiniciar Simulación"): st.session_state.clear(); st.rerun()