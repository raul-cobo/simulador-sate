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

# --- 2. INYECCIÓN CSS (CORRECCIÓN DE COLORES Y DISEÑO) ---
def local_css():
    st.markdown("""
    <style>
        /* Ocultar elementos nativos */
        header, [data-testid="stHeader"], .stAppHeader, [data-testid="stToolbar"] { display: none !important; }
        footer, .stDeployButton { display: none !important; }
        .main .block-container { padding-top: 2rem !important; }

        /* FONDO GLOBAL */
        .stApp {
            background-color: #050A1F; /* Navy Profundo */
            color: #FFFFFF;
        }

        /* TEXTOS GENERALES (Forzar blanco para que se lea) */
        h1, h2, h3, h4, h5, h6, p, label, .stMarkdown {
            color: #FFFFFF !important;
        }

        /* INPUTS Y CAJAS DE TEXTO (Arreglo del fondo blanco) */
        .stTextInput > div > div > input, 
        .stNumberInput > div > div > input, 
        .stSelectbox > div > div > div {
            background-color: #0F1629 !important; /* Fondo oscuro */
            color: white !important;
            border: 1px solid #5D5FEF !important;
        }
        /* Color del texto dentro de los selectbox */
        div[data-testid="stSelectbox"] div[role="listbox"] ul {
            background-color: #0F1629 !important;
        }
        
        /* BOTONES (Arreglo del blanco sobre blanco) */
        .stButton > button {
            background-color: #1A202C !important; /* Fondo oscuro */
            color: #FFFFFF !important; /* Texto blanco */
            border: 1px solid #5D5FEF !important;
            border-radius: 8px !important;
            font-weight: 500 !important;
        }
        .stButton > button:hover {
            background-color: #5D5FEF !important;
            border-color: #FFFFFF !important;
            color: #FFFFFF !important;
        }
        
        /* BOTÓN DE VALIDAR (VERDE/AZUL DESTACADO) */
        .validate-btn button {
            background-color: #5D5FEF !important;
            color: white !important;
            font-size: 1.2rem !important;
            padding: 1rem !important;
            border: none !important;
        }

        /* TARJETAS DE SECTOR */
        .sector-card button {
            height: 120px !important;
            font-size: 1.1rem !important;
            background-color: #0F1629 !important;
            color: white !important;
            border: 2px solid #2D3748 !important;
        }
        .sector-card button:hover {
            border-color: #5D5FEF !important;
            background-color: #1A202C !important;
        }

        /* CAJA DE LOGIN (Blanca) */
        .login-card {
            background-color: white;
            padding: 2rem;
            border-radius: 15px;
            text-align: center;
        }
        /* Ajuste específico para inputs dentro del login (para que se vean oscuros sobre blanco) */
        .login-card input {
            color: white !important;
        }
        
        /* HEADER PERSONALIZADO */
        .custom-header {
            font-size: 2rem;
            font-weight: bold;
            color: white;
            margin-bottom: 0.5rem;
        }
        .custom-sub {
            font-size: 1.1rem;
            color: #5D5FEF;
            margin-bottom: 2rem;
        }

        /* TEXTO DEL DIAGNÓSTICO (Resultados) */
        .diag-text {
            background-color: #0F1629;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #5D5FEF;
            color: #E2E8F0 !important;
        }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- 3. LÓGICA DE VARIABLES Y ETIQUETAS ---

# Nombres exactos solicitados para el informe (8 Dimensiones)
LABELS_ES = {
    "achievement": "Necesidad de Logro",
    "risk_propensity": "Propensión al Riesgo",
    "innovativeness": "Innovatividad",
    "locus_control": "Locus de Control Interno",
    "self_efficacy": "Autoeficacia",
    "autonomy": "Autonomía",
    "ambiguity_tolerance": "Optimismo / Tolerancia a la Incertidumbre",
    "emotional_stability": "Tolerancia al Estrés / Estabilidad Emocional"
}

# Mapeo de variables internas a las 8 dimensiones
VARIABLE_MAP = {
    # Achievement
    "achievement": "achievement", "logro": "achievement",
    # Risk
    "risk_propensity": "risk_propensity", "riesgo": "risk_propensity",
    # Innovativeness
    "innovativeness": "innovativeness", "innovacion": "innovativeness",
    # Locus
    "locus_control": "locus_control", "locus": "locus_control",
    # Self Efficacy
    "self_efficacy": "self_efficacy", "autoeficacia": "self_efficacy", "collaboration": "self_efficacy",
    # Autonomy
    "autonomy": "autonomy", "autonomia": "autonomy",
    # Ambiguity / Optimism
    "ambiguity_tolerance": "ambiguity_tolerance", "tolerancia": "ambiguity_tolerance", "imaginative": "ambiguity_tolerance",
    # Stability
    "emotional_stability": "emotional_stability", "estabilidad": "emotional_stability",
    
    # Flags (Fricción)
    "excitable": "excitable", "skeptical": "skeptical", "cautious": "cautious", 
    "reserved": "reserved", "passive_aggressive": "passive_aggressive",
    "arrogant": "arrogant", "mischievous": "mischievous", 
    "melodramatic": "melodramatic", "diligent": "diligent", "dependent": "dependent"
}

SECTOR_MAP = {
    "Startup Tecnológica (Scalable)": "TECH",
    "Consultoría / Servicios Profesionales": "CONSULTORIA",
    "Pequeña y Mediana Empresa (PYME)": "PYME",
    "Hostelería y Restauración": "HOSTELERIA",
    "Autoempleo / Freelance": "AUTOEMPLEO",
    "Emprendimiento Social": "SOCIAL",
    "Intraemprendimiento": "INTRA"
}

# --- 4. FUNCIONES DE LÓGICA ---
def generate_id(): return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def init_session():
    if 'octagon' not in st.session_state:
        # Inicializamos las 8 dimensiones base en 50
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
    o = st.session_state.octagon
    f = st.session_state.flags
    
    # Promedio Potencial
    avg = sum(o.values()) / 8
    
    # Cálculo de Fricción
    friction_sum = sum(f.values())
    friction_final = friction_sum * 0.5 # Factor de ajuste
    
    # Triggers (Texto profesional)
    triggers = []
    if f["mischievous"] > 25: triggers.append("Riesgo de Desalineamiento Normativo")
    if f["arrogant"] > 25: triggers.append("Estilo Dominante / Rigidez Potencial")
    if f["passive_aggressive"] > 20: triggers.append("Fricción Relacional Latente")
    if o["achievement"] > 85 and o["emotional_stability"] < 40: triggers.append("Riesgo de Agotamiento Operativo (Burnout)")
    if o["risk_propensity"] > 85 and f["cautious"] < 10: triggers.append("Perfil de Riesgo Desmedido")
    if f["diligent"] > 60: triggers.append("Bloqueo por Sobre-Análisis")
    if f["dependent"] > 55: triggers.append("Alta Necesidad de Supervisión")

    # IRE
    ire = avg - (friction_final * 0.8) - (len(triggers) * 3)
    ire = max(0, min(100, ire))
    
    return round(ire, 2), round(avg, 2), round(friction_final, 2), triggers

# --- GENERADOR DE TEXTOS EXPLICATIVOS (BASE CONOCIMIENTO) ---
def get_ire_text(score):
    if score > 75: return "Nivel de viabilidad positivo. El índice confirma que el perfil opera en un rango de alta sostenibilidad."
    if score > 50: return "Nivel de viabilidad medio. El perfil es funcional pero requiere monitorizar los costes operativos derivados de la fricción."
    return "Nivel de viabilidad comprometido. La discrepancia entre potencial y ejecución sugiere riesgos de continuidad."

def get_potential_text(score):
    if score > 75: return "Nivel Alto. El sujeto dispone de recursos cognitivos y actitudinales superiores para afrontar la complejidad del sector."
    if score > 50: return "Nivel Medio. Recursos suficientes para la operativa estándar, con áreas específicas de desarrollo."
    return "Nivel Bajo. Se requiere un plan de desarrollo intensivo en competencias basales."

def get_risk_text(triggers):
    if not triggers: return "No se detectan indicadores críticos que comprometan la operativa inmediata."
    return "Se detectan patrones conductuales que pueden generar ineficiencias o conflictos si no se gestionan (ver detalle abajo)."

# --- PDF ESTILO "ANÁLISIS PROFESIONAL" (DIAGONAL) ---
def create_pdf_report(ire, avg, friction, triggers, user, stats):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    
    # 1. DISEÑO DE CABECERA (DIAGONAL)
    # Parte Azul (Abajo izquierda)
    p.setFillColorRGB(0.02, 0.04, 0.12) # Navy
    path = p.beginPath()
    path.moveTo(0, h)      # Top Left (fuera)
    path.lineTo(0, h-120)  # Bajamos 120
    path.lineTo(w, h-40)   # Subimos a la derecha
    path.lineTo(w, h)      # Top Right
    path.close()
    p.fillPath(path)
    
    # 2. LOGO (Izquierda, sobre zona limpia o recuadro si es necesario)
    # En este diseño diagonal, la esquina superior izquierda es Navy.
    # Pondremos el Logo en BLANCO si existe 'logo_blanco.png', si no un recuadro blanco y el original.
    logo_file = "logo_blanco.png" if os.path.exists("logo_blanco.png") else None
    
    if logo_file:
        try:
            p.drawImage(logo_file, 40, h-90, width=120, height=60, preserveAspectRatio=True, mask='auto')
        except: pass
    else:
        # Plan B: Recuadro blanco
        if os.path.exists("logo_original.png"):
            p.setFillColorRGB(1,1,1)
            p.rect(40, h-100, 130, 70, fill=1, stroke=0)
            try:
                p.drawImage("logo_original.png", 50, h-90, width=110, height=50, preserveAspectRatio=True, mask='auto')
            except: pass

    # TÍTULO DEL INFORME (Alineado a la derecha en la zona blanca/azul)
    p.setFillColorRGB(0.02, 0.04, 0.12) # Texto oscuro para la zona blanca (derecha abajo)
    p.setFont("Helvetica-Bold", 18)
    p.drawRightString(w-40, h-70, "INFORME TÉCNICO S.A.P.E.")
    p.setFont("Helvetica", 10)
    p.setFillColorRGB(0.4, 0.4, 0.4)
    p.drawRightString(w-40, h-85, "Sistema de Análisis de la Personalidad Emprendedora")

    # 3. DATOS DE IDENTIFICACIÓN
    y_start = h - 150
    p.setFillColorRGB(0,0,0)
    p.setFont("Helvetica-Bold", 11)
    p.drawString(40, y_start, f"ID Usuario: {st.session_state.user_id}")
    p.drawString(40, y_start-15, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}")
    p.drawString(40, y_start-30, f"Sector: {user.get('sector', 'N/A')}")
    
    # 4. MÉTRICAS PRINCIPALES (Texto explicado)
    y = y_start - 70
    p.setFont("Helvetica-Bold", 14)
    p.setFillColorRGB(0.02, 0.04, 0.12)
    p.drawString(40, y, "1. Métricas Principales")
    p.line(40, y-5, w-40, y-5)
    y -= 30
    
    # Bloque Potencial
    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, y, f"POTENCIAL ({avg}/100):")
    p.setFont("Helvetica", 10)
    text_pot = get_potential_text(avg)
    p.drawString(200, y, text_pot)
    y -= 20
    
    # Bloque Fricción
    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, y, f"FRICCIÓN ({friction}/100):")
    p.setFont("Helvetica", 10)
    if friction < 20: txt_fric = "Nivel bajo. Resistencia operativa mínima."
    elif friction < 45: txt_fric = "Nivel medio. Presencia moderada de bloqueos conductuales."
    else: txt_fric = "Nivel alto. Importante coste operativo por conductas defensivas."
    p.drawString(200, y, txt_fric)
    y -= 20
    
    # Bloque IRE
    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, y, f"IRE FINAL ({ire}/100):")
    p.setFont("Helvetica", 10)
    text_ire = get_ire_text(ire)
    p.drawString(200, y, text_ire)
    y -= 40
    
    # 5. ANÁLISIS DIMENSIONAL (Perfil Competencial)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(40, y, "2. Análisis Dimensional (Perfil Competencial)")
    p.line(40, y-5, w-40, y-5)
    y -= 30
    
    p.setFont("Helvetica", 10)
    p.drawString(40, y, "Desglose de las 8 dimensiones evaluadas:")
    y -= 25
    
    # Tabla de barras
    for k, v in stats.items():
        label = LABELS_ES.get(k, k)
        p.setFont("Helvetica-Bold", 9)
        p.drawString(50, y, label)
        
        # Barra gris
        p.setFillColorRGB(0.9, 0.9, 0.9)
        p.rect(250, y, 200, 8, fill=1, stroke=0)
        
        # Barra valor
        if v > 75: p.setFillColorRGB(0.2, 0.6, 0.2) # Verde
        elif v > 45: p.setFillColorRGB(0.2, 0.3, 0.7) # Azul
        else: p.setFillColorRGB(0.8, 0.3, 0.3) # Rojo
        
        bar_w = (v/100)*200
        p.rect(250, y, bar_w, 8, fill=1, stroke=0)
        
        p.setFillColorRGB(0,0,0)
        p.drawString(460, y, str(round(v, 1)))
        y -= 20
        
    y -= 20
    
    # 6. ALERTAS
    p.setFont("Helvetica-Bold", 14)
    p.drawString(40, y, "3. Detección de Riesgos y Alertas")
    p.line(40, y-5, w-40, y-5)
    y -= 30
    
    p.setFont("Helvetica", 10)
    text_risk = get_risk_text(triggers)
    p.drawString(50, y, text_risk)
    y -= 20
    
    if triggers:
        for t in triggers:
            p.setFillColorRGB(0.7, 0, 0)
            p.setFont("Helvetica-Bold", 10)
            p.drawString(60, y, f"• {t}")
            # Explicación genérica de impacto (se podría personalizar más)
            p.setFillColorRGB(0.3, 0.3, 0.3)
            p.setFont("Helvetica", 9)
            p.drawString(80, y-12, "Impacto: Posible reducción de la eficiencia en toma de decisiones.")
            y -= 30

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

def radar_chart():
    data = st.session_state.octagon
    cat = [LABELS_ES.get(k) for k in data.keys()]
    val = list(data.values())
    cat += [cat[0]]; val += [val[0]]
    fig = go.Figure(go.Scatterpolar(
        r=val, theta=cat, fill='toself', 
        line=dict(color='#5D5FEF', width=2),
        fillcolor='rgba(93, 95, 239, 0.2)'
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, linecolor='#4A5568'), bgcolor='rgba(0,0,0,0)'),
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white', size=12),
        showlegend=False,
        margin=dict(l=40, r=40, t=20, b=20),
        dragmode=False
    )
    return fig

# --- 5. LOGO HELPER ---
def get_logo_image():
    # Prioridad: 1. Blanco, 2. Original. Para la web fondo oscuro, mejor blanco.
    if os.path.exists("logo_blanco.png"): return Image.open("logo_blanco.png")
    if os.path.exists("logo_original.png"): return Image.open("logo_original.png")
    return None

# --- 6. FLUJO DE PANTALLAS ---
init_session()
logo_main = get_logo_image()

# LOGIN
if not st.session_state.get("auth", False):
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.container():
            st.markdown('<div class="login-card">', unsafe_allow_html=True)
            if os.path.exists("logo_original.png"):
                st.image("logo_original.png", width=250)
            else:
                st.header("AUDEO")
            
            st.markdown("<h3 style='color:black !important;'>Acceso Corporativo</h3>", unsafe_allow_html=True)
            
            password = st.text_input("Clave de acceso", type="password")
            if st.button("ENTRAR AL SISTEMA", use_container_width=True):
                if password == st.secrets["general"]["password"]:
                    st.session_state.auth = True
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")
            st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# CABECERA COMÚN (En todas las páginas tras login)
c_h1, c_h2 = st.columns([0.5, 4])
with c_h1:
    if logo_main: st.image(logo_main, use_container_width=True)
with c_h2:
    st.markdown('<div class="custom-header">Simulador S.A.P.E.</div>', unsafe_allow_html=True)
    st.markdown('<div class="custom-sub">Sistema de Análisis de la Personalidad Emprendedora</div>', unsafe_allow_html=True)

st.markdown("---")

# PANTALLA 1: DATOS
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
    # Enlace simulado que no recarga (javascript void) o a una web externa real
    st.markdown('<a href="https://www.audeo.es/privacidad" target="_blank" style="color:#5D5FEF;">📄 Ver Documento de Protección de Datos</a>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="validate-btn">', unsafe_allow_html=True)
    if st.button("🔐 VALIDAR DATOS Y CONTINUAR"):
        if name and age and consent:
            st.session_state.user_data = {"name": name, "age": age, "gender": gender, "sector": "", "experience": experience}
            st.session_state.data_verified = True
            st.rerun()
        else:
            st.error("Por favor, completa nombre, edad y acepta la privacidad.")
    st.markdown('</div>', unsafe_allow_html=True)

# PANTALLA 2: SECTOR
elif not st.session_state.started:
    st.success(f"Bienvenido/a, {st.session_state.user_data['name']}")
    st.markdown("#### 2. Selecciona el Sector del Proyecto:")
    
    def go_sector(sec):
        all_q = load_questions()
        code = SECTOR_MAP[sec]
        # Filtrado simple por si falla el CSV
        qs = [x for x in all_q if x['SECTOR'].strip().upper() == code]
        if not qs: qs = [x for x in all_q if x['SECTOR'].strip().upper() == "TECH"]
        st.session_state.data = qs
        st.session_state.user_data["sector"] = sec
        st.session_state.started = True
        st.rerun()

    c1, c2, c3, c4 = st.columns(4)
    # Usamos clases CSS para hacer botones grandes
    with c1: 
        st.markdown('<div class="sector-card">', unsafe_allow_html=True)
        if st.button("Tecnología / Startup"): go_sector("Startup Tecnológica (Scalable)")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="sector-card">', unsafe_allow_html=True) 
        if st.button("Consultoría"): go_sector("Consultoría / Servicios Profesionales")
        st.markdown('</div>', unsafe_allow_html=True)
    with c3: 
        st.markdown('<div class="sector-card">', unsafe_allow_html=True)
        if st.button("Comercio / PYME"): go_sector("Pequeña y Mediana Empresa (PYME)")
        st.markdown('</div>', unsafe_allow_html=True)
    with c4: 
        st.markdown('<div class="sector-card">', unsafe_allow_html=True)
        if st.button("Hostelería"): go_sector("Hostelería y Restauración")
        st.markdown('</div>', unsafe_allow_html=True)

# PANTALLA 3: JUEGO
elif not st.session_state.finished:
    row = st.session_state.data[st.session_state.current_step]
    st.progress((st.session_state.current_step + 1) / len(st.session_state.data))
    
    st.markdown(f"### {row['TITULO']}")
    
    c_text, c_opt = st.columns([1.5, 1])
    with c_text:
        st.markdown(f'<div class="diag-text" style="font-size:1.2rem;">{row["NARRATIVA"]}</div>', unsafe_allow_html=True)
    with c_opt:
        st.markdown("#### Tu decisión:")
        step = st.session_state.current_step
        
        # Opciones
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

# PANTALLA 4: RESULTADOS
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
        # Textos claros sobre fondo oscuro
        st.markdown(f'<div class="diag-text">{get_ire_text(ire)}</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if triggers:
             st.error("Alertas: " + ", ".join(triggers))
        else:
             st.success("Perfil sin alertas críticas.")

    st.markdown("<br>", unsafe_allow_html=True)
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