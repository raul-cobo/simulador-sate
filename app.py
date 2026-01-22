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
st.set_page_config(page_title="Simulador S.A.P.E.", page_icon="🧬", layout="wide")

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

        /* --- INPUTS Y FORMULARIOS --- */
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
        /* Ajuste para que el texto del checkbox sea legible */
        .stCheckbox p {
            color: #E2E8F0 !important;
            font-size: 0.95rem !important;
        }

        /* --- TARJETAS DE SECTOR (BOTONES GRANDES) --- */
        .sector-btn > button {
            background-color: #0F1629 !important;
            border: 1px solid #5D5FEF !important;
            color: white !important;
            height: 100px !important;
            font-size: 16px !important;
            font-weight: 600 !important;
            border-radius: 12px !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }
        .sector-btn > button:hover {
            background-color: #5D5FEF !important;
            transform: translateY(-5px);
            box-shadow: 0 10px 15px rgba(93, 95, 239, 0.4);
        }

        /* --- BOTONES DE RESPUESTA --- */
        .answer-btn > button {
            width: 100% !important;
            background-color: #1A202C !important;
            color: #E2E8F0 !important;
            border: 1px solid #4A5568 !important;
            padding: 20px !important;
            border-radius: 8px !important;
            text-align: left !important;
            margin-bottom: 10px !important;
            transition: all 0.2s !important;
        }
        .answer-btn > button:hover {
            border-color: #5D5FEF !important;
            color: #5D5FEF !important;
            background-color: #0F1629 !important;
        }

        /* --- BARRA DE PROGRESO --- */
        div[data-testid="stProgressBar"] > div > div > div > div {
            background-color: #5D5FEF !important;
        }

        /* --- NARRATIVA --- */
        .big-narrative {
            font-size: 1.2rem;
            line-height: 1.6;
            color: #E2E8F0;
            background-color: #0F1629;
            padding: 30px;
            border-radius: 12px;
            border-left: 5px solid #5D5FEF;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
            height: 100%;
        }

        /* --- HEADER LOGO --- */
        .header-title {
            font-size: 2.5rem;
            font-weight: 700;
            background: -webkit-linear-gradient(left, #FFFFFF, #A0AEC0);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .header-subtitle {
            font-size: 1.2rem;
            color: #5D5FEF;
            font-weight: 400;
            margin-bottom: 2rem;
        }
        
        /* Enlace Legal */
        .legal-link a {
            color: #5D5FEF !important;
            text-decoration: none;
            font-size: 0.85rem;
        }
        .legal-link a:hover {
            text-decoration: underline;
        }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- 3. LÓGICA DE NEGOCIO ---

SECTOR_MAPPING = {
    "Startup Tecnológica (Scalable)": "TECH",
    "Consultoría / Servicios Profesionales": "CONSULTORIA",
    "Pequeña y Mediana Empresa (PYME)": "PYME",
    "Hostelería y Restauración": "HOSTELERIA",
    "Autoempleo / Freelance": "AUTOEMPLEO",
    "Emprendimiento Social": "SOCIAL",
    "Intraemprendimiento": "INTRA"
}

VARIABLE_MAP = {
    "achievement": "achievement", "logro": "achievement",
    "risk_propensity": "risk_propensity", "riesgo": "risk_propensity",
    "innovativeness": "innovativeness", "innovacion": "innovativeness",
    "locus_control": "locus_control", "locus": "locus_control",
    "self_efficacy": "self_efficacy", "autoeficacia": "self_efficacy",
    "autonomy": "autonomy", "autonomia": "autonomy",
    "ambiguity_tolerance": "ambiguity_tolerance", "tolerancia": "ambiguity_tolerance",
    "emotional_stability": "emotional_stability", "estabilidad": "emotional_stability",
    "excitable": "excitable", "skeptical": "skeptical", "cautious": "cautious",
    "reserved": "reserved", "passive_aggressive": "passive_aggressive",
    "arrogant": "arrogant", "mischievous": "mischievous",
    "melodramatic": "melodramatic", "imaginative": "imaginative",
    "diligent": "diligent", "dependent": "dependent"
}

LABELS_ES = {
    "achievement": "Logro", "risk_propensity": "Riesgo", "innovativeness": "Innovación",
    "locus_control": "Locus Control", "self_efficacy": "Autoeficacia", "autonomy": "Autonomía",
    "ambiguity_tolerance": "Tol. Incertidumbre", "emotional_stability": "Estabilidad"
}

def generate_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def init_session():
    if 'octagon' not in st.session_state:
        st.session_state.octagon = {k: 50 for k in ["achievement", "risk_propensity", "innovativeness", "locus_control", "self_efficacy", "autonomy", "ambiguity_tolerance", "emotional_stability"]}
        st.session_state.flags = {k: 0 for k in ["excitable", "skeptical", "cautious", "reserved", "passive_aggressive", "arrogant", "mischievous", "melodramatic", "imaginative", "diligent", "dependent"]}
        st.session_state.current_step = 0
        st.session_state.finished = False
        st.session_state.started = False 
        st.session_state.data = []
        st.session_state.choices_log = [""] * 30 
        st.session_state.user_id = generate_id()
        st.session_state.user_data = {}

def load_questions():
    try:
        filename = 'SATE_v1.csv'
        if not os.path.exists(filename): return []
        with open(filename, encoding='utf-8-sig') as f:
            return list(csv.DictReader(f, delimiter=';'))
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

def calculate_results():
    o, f = st.session_state.octagon, st.session_state.flags
    avg = sum(o.values()) / 8
    toxic = sum([f[k] for k in ["mischievous", "arrogant", "passive_aggressive", "excitable", "melodramatic"]])
    excess = sum([max(0, f[k]-50)*0.25 for k in ["diligent", "cautious", "dependent", "skeptical", "reserved", "imaginative"]])
    
    triggers = []
    if f["mischievous"] > 25: triggers.append("RIESGO ÉTICO ALTO")
    if f["arrogant"] > 25: triggers.append("NARCISISMO / ARROGANCIA")
    if f["passive_aggressive"] > 20: triggers.append("CONFLICTIVIDAD PASIVA")
    if o["achievement"] > 85 and o["emotional_stability"] < 30: triggers.append("RIESGO DE BURNOUT")
    if o["risk_propensity"] > 85 and f["cautious"] < 10: triggers.append("COMPORTAMIENTO TEMERARIO")
    
    ire = max(0, min(100, avg - toxic - excess - (len(triggers)*5)))
    return round(ire, 2), round(avg, 2), toxic, triggers

def create_pdf_report(ire, avg, toxic, triggers, user, stats):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    p.setFillColorRGB(0.02, 0.04, 0.12)
    p.rect(0, h-100, w, 100, fill=1)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 22)
    p.drawString(50, h-60, "Audeo Intelligence | Informe S.A.P.E.")
    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica", 10)
    p.drawString(50, h-130, f"Candidato: {user.get('name')} | ID: {st.session_state.user_id}")
    p.drawString(50, h-145, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}")
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, h-180, f"IRE (Índice de Resiliencia): {ire}/100")
    p.drawString(50, h-200, f"Potencial Promedio: {avg}/100")
    y = h-240
    if triggers:
        p.setFillColorRGB(0.8, 0, 0)
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y, "ALERTAS DETECTADAS:")
        y -= 20
        p.setFont("Helvetica", 10)
        for t in triggers: p.drawString(60, y, f"• {t}"); y -= 15
    else:
        p.setFillColorRGB(0, 0.5, 0)
        p.drawString(50, y, "Sin alertas críticas detectadas.")
    p.showPage(); p.save()
    buffer.seek(0)
    return buffer

def radar_chart():
    data = st.session_state.octagon
    cat = [LABELS_ES.get(k) for k in data.keys()]
    val = list(data.values())
    cat += [cat[0]]; val += [val[0]]
    fig = go.Figure(go.Scatterpolar(r=val, theta=cat, fill='toself', line=dict(color='#5D5FEF'), fillcolor='rgba(93, 95, 239, 0.2)'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, linecolor='#2D3748'), bgcolor='rgba(0,0,0,0)'), paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'), showlegend=False, margin=dict(l=40, r=40, t=20, b=20))
    return fig

# --- 4. SISTEMA DE LOGIN ---
def login_screen():
    if st.session_state.get("auth", False): return True
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("### 🔒 Acceso Audeo S.A.P.E.")
        pwd = st.text_input("Clave de acceso", type="password", key="pwd_in")
        if st.button("Entrar", use_container_width=True):
            if pwd == st.secrets["general"]["password"]: st.session_state.auth = True; st.rerun()
            else: st.error("Clave incorrecta")
    return False

# --- 5. FLUJO PRINCIPAL ---
init_session()

if not login_screen(): st.stop()

# CARGAR LOGO (Nombre Corregido)
try:
    logo = Image.open("logo_Audeo.png")
except:
    logo = None # Si falla, no rompe la app, solo no muestra logo

if not st.session_state.started:
    # --- PANTALLA DE INICIO (HOME) ---
    c_logo, c_title = st.columns([1, 5])
    with c_logo:
        if logo: st.image(logo, use_container_width=True)
    with c_title:
        st.markdown('<div class="header-title">Simulador S.A.P.E.</div>', unsafe_allow_html=True)
        st.markdown('<div class="header-subtitle">Sistema de Análisis de la Personalidad Emprendedora</div>', unsafe_allow_html=True)

    st.markdown("---")

    # Formulario
    c1, c2, c3 = st.columns(3)
    name = c1.text_input("Nombre Completo (Uso interno)")
    # EDAD CORREGIDA: value=None para que salga vacío
    age = c2.number_input("Edad", min_value=18, max_value=99, value=None, placeholder="--")
    gender = c3.selectbox("Género", ["Masculino", "Femenino", "Prefiero no decirlo"])

    c4, c5, c6 = st.columns(3)
    country = c4.selectbox("País / Región", ["España", "LATAM", "Europa", "Otros"])
    situation = c5.selectbox("Situación", ["Solo", "Con Socios", "Intraemprendimiento"])
    experience = c6.selectbox("Experiencia previa", ["Primer emprendimiento", "Emprendimientos sin éxito", "Emprendimientos con éxito"])

    st.markdown("<br>", unsafe_allow_html=True)
    
    # CHECKBOX LEGAL Y ENLACE RGPD
    consent = st.checkbox("He leído y acepto la Política de Privacidad y autorizo el tratamiento de mis datos para fines de investigación académica y estadística.")
    st.markdown('<div class="legal-link"><a href="#" target="_blank">📄 Ver Documento de Protección de Datos (RGPD)</a></div>', unsafe_allow_html=True)

    st.markdown("<br><h5>Selecciona el Sector del Proyecto para iniciar:</h5>", unsafe_allow_html=True)

    def start_game(sector_name):
        if not name:
            st.error("⚠️ Por favor, introduce tu nombre antes de empezar.")
        elif age is None:
            st.error("⚠️ Por favor, introduce tu edad.")
        elif not consent:
            st.error("⚠️ Debes aceptar el tratamiento de datos para continuar.")
        else:
            all_q = load_questions()
            code = SECTOR_MAPPING[sector_name]
            qs = [q for q in all_q if q['SECTOR'].strip().upper() == code]
            if not qs: qs = [q for q in all_q if q['SECTOR'].strip().upper() == "TECH"]
            
            st.session_state.data = qs
            st.session_state.user_data = {
                "name": name, "age": age, "gender": gender, 
                "country": country, "situation": situation, 
                "experience": experience, "sector": sector_name
            }
            st.session_state.started = True
            st.rerun()

    # GRID SECTORES
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

elif not st.session_state.finished:
    # --- PANTALLA PREGUNTAS ---
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
    ire, avg, toxic, triggers = calculate_results()
    c_res_logo, c_res_title = st.columns([1, 5])
    with c_res_logo: 
        if logo: st.image(logo)
    with c_res_title:
        st.header(f"Informe S.A.P.E. | {st.session_state.user_data['name']}")
        st.caption(f"ID: {st.session_state.user_id} | Sector: {st.session_state.user_data['sector']}")

    st.divider()
    k1, k2, k3 = st.columns(3)
    k1.metric("Índice IRE", f"{ire}/100"); k2.metric("Potencial", f"{avg}/100"); k3.metric("Fricción", toxic, delta_color="inverse")

    c_chart, c_txt = st.columns([1, 1])
    with c_chart: st.plotly_chart(radar_chart(), use_container_width=True)
    with c_txt:
        st.markdown("### Diagnóstico Ejecutivo")
        if ire > 75: st.success("Perfil de Alta Resiliencia.")
        elif ire > 45: st.warning("Perfil Equilibrado.")
        else: st.error("Perfil de Riesgo.")
        if triggers:
            st.markdown("#### ⚠️ Alertas Críticas")
            for t in triggers: st.markdown(f"- {t}")

    st.markdown("<br>", unsafe_allow_html=True)
    pdf_data = create_pdf_report(ire, avg, toxic, triggers, st.session_state.user_data, st.session_state.octagon)
    st.download_button("📥 Descargar Informe Completo (PDF)", pdf_data, f"SAPE_{st.session_state.user_id}.pdf", "application/pdf", use_container_width=True)
    
    if st.button("Reiniciar Simulación"): st.session_state.clear(); st.rerun()