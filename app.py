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

# Librerías para PDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Audeo Intelligence", page_icon="🧬", layout="wide")

# --- 2. INYECCIÓN CSS (DISEÑO PROFESIONAL) ---
def local_css():
    st.markdown("""
    <style>
        /* Tipografía y márgenes */
        html, body, [class*="css"] {
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        }
        .block-container {
            padding-top: 2rem !important;
        }

        /* Botones de Respuesta Estilo 'Target' */
        .stButton > button {
            width: 100% !important;
            border-radius: 10px !important;
            padding: 18px 20px !important;
            font-size: 17px !important;
            font-weight: 500 !important;
            background-color: #1E1E1E !important;
            color: #FFFFFF !important;
            border: 1px solid #333333 !important;
            transition: all 0.3s ease !important;
            text-align: left !important;
        }

        .stButton > button:hover {
            background-color: #0047AB !important; /* Azul Cobalto Audeo */
            border-color: #0047AB !important;
            transform: translateY(-2px) !important;
        }

        /* Barra de progreso Dorada (Símbolo Au) */
        div[data-testid="stProgressBar"] > div > div > div > div {
            background-color: #D4AF37 !important;
        }

        /* Narrativa en caja destacada */
        .big-narrative {
            font-size: 1.15rem; 
            line-height: 1.6; 
            color: #E0E0E0;
            background-color: #262730; 
            padding: 25px; 
            border-radius: 10px;
            border-left: 6px solid #0047AB; 
            margin-bottom: 20px;
        }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- 3. SISTEMA DE LOGIN ---
def check_password():
    if st.session_state.get("password_correct", False):
        return True

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.write("### 🔒 Acceso Restringido")
        # El tipo 'password' permite usar el "ojo" para ver la clave sin que se dispare la entrada
        password_input = st.text_input("Introduce la clave de acceso:", type="password", key="login_pass")
        
        st.write(" ")
        # Solo se entra al pulsar este botón específicamente
        if st.button("Entrar al Sistema", use_container_width=True):
            if password_input == st.secrets["general"]["password"]:
                st.session_state.password_correct = True
                st.rerun()
            else:
                st.error("⛔ Clave incorrecta. Inténtalo de nuevo.")
                
        st.caption("Audeo Intelligence S.L. - Solo personal autorizado")
    return False

if not check_password():
    st.stop()

# Verificación de secretos de base de datos
if "supabase" not in st.secrets:
    st.error("⚠️ CRÍTICO: No existe configuración de base de datos.")
    st.stop()

# --- 4. MAPAS DE VARIABLES ---
VARIABLE_MAP = {
    "achievement": "achievement", "logro": "achievement",
    "risk_propensity": "risk_propensity", "riesgo": "risk_propensity",
    "innovativeness": "innovativeness", "innovacion": "innovativeness",
    "locus_control": "locus_control", "locus": "locus_control",
    "self_efficacy": "self_efficacy", "autoeficacia": "self_efficacy",
    "autonomy": "autonomy", "autonomia": "autonomy",
    "ambiguity_tolerance": "ambiguity_tolerance", "tolerancia": "ambiguity_tolerance",
    "emotional_stability": "emotional_stability", "estabilidad": "emotional_stability",
    "honesty": "emotional_stability", "integrity": "emotional_stability", "ethics": "emotional_stability",
    "collaboration": "self_efficacy",
    "excitable": "excitable", "explosivo": "excitable",
    "skeptical": "skeptical", "esceptico": "skeptical",
    "passive_aggressive": "passive_aggressive", "pasivo": "passive_aggressive",
    "arrogant": "arrogant", "arrogante": "arrogant", "narcissism": "arrogant", "ego": "arrogant",
    "mischievous": "mischievous", "astuto": "mischievous", "travieso": "mischievous", "corruption": "mischievous",
    "melodramatic": "melodramatic", "drama": "melodramatic", "victim": "melodramatic",
    "cautious": "cautious", "cauto": "cautious", "miedo": "cautious",
    "reserved": "reserved", "reservado": "reserved",
    "diligent": "diligent", "diligente": "diligent", "perfectionism": "diligent",
    "dependent": "dependent", "dependiente": "dependent", "obediente": "dependent",
    "imaginative": "imaginative", "imaginativo": "imaginative"
}

LABELS_ES = {
    "achievement": "Logro", "risk_propensity": "Riesgo", "innovativeness": "Innovación",
    "locus_control": "Locus Control", "self_efficacy": "Autoeficacia", "autonomy": "Autonomía",
    "ambiguity_tolerance": "Tol. Incertidumbre", "emotional_stability": "Estabilidad"
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

# --- 5. FUNCIONES DE APOYO ---
def generate_short_id():
    chars = string.ascii_uppercase + string.digits
    part1 = ''.join(random.choices(chars, k=2))
    part2 = ''.join(random.choices(chars, k=2))
    return f"{part1}-{part2}"

def init_session():
    if 'octagon' not in st.session_state:
        st.session_state.octagon = {k: 50 for k in ["achievement", "risk_propensity", "innovativeness", "locus_control", "self_efficacy", "autonomy", "ambiguity_tolerance", "emotional_stability"]}
        st.session_state.flags = {k: 0 for k in ["excitable", "skeptical", "cautious", "reserved", "passive_aggressive", "arrogant", "mischievous", "melodramatic", "imaginative", "diligent", "dependent"]}
        st.session_state.current_step = 0
        st.session_state.finished = False
        st.session_state.started = False 
        st.session_state.data = []
        st.session_state.choices_log = [""] * 30 
        st.session_state.saved = False 
        st.session_state.user_id = generate_short_id() 
        st.session_state.user_data = {"name": "", "age": 30, "venture_type": "TECH", "experience": "Primer emprendimiento", "partners": "Solo"}

def load_all_questions():
    try:
        filename = 'SATE_v1.csv'
        if not os.path.exists(filename):
            st.error("⚠️ No se encuentra el archivo de preguntas.")
            st.stop()
        with open(filename, encoding='utf-8-sig') as f:
            reader = list(csv.DictReader(f, delimiter=';'))
            if len(reader) > 0 and 'SECTOR' in reader[0]: return reader
        with open(filename, encoding='utf-8-sig') as f:
            reader = list(csv.DictReader(f, delimiter=','))
            if len(reader) > 0 and 'SECTOR' in reader[0]: return reader
        st.error("❌ Formato de CSV no reconocido.")
        st.stop()
    except Exception as e:
        st.error(f"❌ Error leyendo preguntas: {e}")
        st.stop()

def filter_questions_by_sector(all_rows, sector_code):
    filtered = [row for row in all_rows if row.get('SECTOR', '').strip().upper() == sector_code]
    if not filtered: filtered = [row for row in all_rows if row.get('SECTOR', '').strip().upper() == 'TECH']
    return filtered 

def parse_logic(logic_str, option_number, step_index):
    if step_index < 30:
        st.session_state.choices_log[step_index] = str(option_number)
    if not logic_str: return
    actions = str(logic_str).split('|')
    for action in actions:
        parts = action.strip().split()
        if len(parts) < 2: continue
        term = parts[0].lower().strip()
        try: val = int(parts[1])
        except ValueError: continue
        var_key = VARIABLE_MAP.get(term)
        if var_key:
            if var_key in st.session_state.flags:
                st.session_state.flags[var_key] = max(0, st.session_state.flags[var_key] + val)
            elif var_key in st.session_state.octagon:
                st.session_state.octagon[var_key] = max(0, min(100, st.session_state.octagon[var_key] + val))

def calculate_final_score():
    avg = sum(st.session_state.octagon.values()) / 8
    f = st.session_state.flags
    toxic_keys = ["mischievous", "arrogant", "passive_aggressive", "excitable", "melodramatic"]
    toxic_score = sum([f[k] for k in toxic_keys])
    toxic_penalty = toxic_score * 1.0 
    excess_keys = ["diligent", "cautious", "dependent", "skeptical", "reserved", "imaginative"]
    excess_penalty = 0
    threshold = 50 
    for k in excess_keys:
        if f[k] > threshold: excess_penalty += (f[k] - threshold) * 0.25
    total_penalty = toxic_penalty + excess_penalty
    
    triggers = []
    o = st.session_state.octagon
    if f["mischievous"] > 25: triggers.append("RIESGO ÉTICO ALTO")
    if f["arrogant"] > 25: triggers.append("NARCISISMO / ARROGANCIA")
    if f["passive_aggressive"] > 20: triggers.append("CONFLICTIVIDAD PASIVA")
    if o["achievement"] > 85 and o["emotional_stability"] < 30: triggers.append("RIESGO DE BURNOUT")
    if o["risk_propensity"] > 85 and f["cautious"] < 10: triggers.append("LUDÓPATA")
    if f["diligent"] > 60: triggers.append("PARÁLISIS POR ANÁLISIS")
    if f["dependent"] > 50: triggers.append("FALTA DE AUTONOMÍA")

    ire = avg - total_penalty - (len(triggers) * 5)
    ire = max(0, min(100, ire))
    return round(ire, 2), round(avg, 2), toxic_score, triggers

def generate_text_report(ire, avg, friction_points):
    report_text = ""
    if ire > 75: report_text += "Perfil: Alta Resiliencia. El usuario gestiona eficazmente la presión.\n"
    elif ire > 45: report_text += "Perfil: Equilibrado. Bases sólidas con margen de mejora.\n"
    else: report_text += "Perfil: Riesgo. Brecha crítica entre potencial y ejecución.\n"
    
    if friction_points < 15: report_text += "Nivel de Fricción: BAJO. Fluidez operativa."
    elif friction_points < 40: report_text += "Nivel de Fricción: MEDIO. Bloqueos defensivos presentes."
    else: report_text += "Nivel de Fricción: ALTO. Estilo de gestión conflictivo."
    return report_text

# --- FUNCIÓN GENERAR PDF ---
def create_pdf(ire, avg, toxic, triggers, user_data, octagon_data):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Diseño de Cabecera PDF
    p.setFont("Helvetica-Bold", 18)
    p.drawString(50, height - 50, "Audeo - Informe Estratégico de Talento")
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 70, f"Nombre: {user_data.get('name')} | ID: {st.session_state.user_id}")
    p.drawString(50, height - 85, f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    p.line(50, height - 95, width - 50, height - 95)
    
    y_pos = height - 130
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y_pos, f"Índice de Resiliencia (IRE): {ire}/100")
    p.drawString(300, y_pos, f"Promedio Potencial: {avg}")
    y_pos -= 40
    
    p.setFont("Helvetica", 12)
    for line in generate_text_report(ire, avg, toxic).split('\n'):
        p.drawString(50, y_pos, line)
        y_pos -= 20
    
    y_pos -= 20
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y_pos, "Puntuación por Competencia:")
    y_pos -= 25
    p.setFont("Helvetica", 10)
    
    for k, v in octagon_data.items():
        p.drawString(50, y_pos, f"{LABELS_ES.get(k, k)}: {round(v, 1)}")
        y_pos -= 15
        if y_pos < 50: p.showPage(); y_pos = height - 50
    
    if triggers:
        y_pos -= 20
        p.setFillColor(colors.red)
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y_pos, "ALERTAS DETECTADAS:")
        y_pos -= 20
        p.setFont("Helvetica", 10)
        for t in triggers:
            p.drawString(60, y_pos, f"• {t}")
            y_pos -= 15

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

def save_result_to_supabase(ire, avg, friction, triggers):
    try:
        url_base = st.secrets["supabase"]["url"]
        api_key = st.secrets["supabase"]["key"]
        headers = {"apikey": api_key, "Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "user_id_anonimo": st.session_state.user_id,
            "nombre_interno": st.session_state.user_data.get('name'),
            "sector": st.session_state.user_data.get('venture_type'),
            "respuestas": st.session_state.choices_log,
            "ire_final": float(ire), "potencial_final": float(avg),
            "alertas": " | ".join(triggers) if triggers else "Ninguna"
        }
        res = requests.post(f"{url_base}/rest/v1/resultados_sape", json=payload, headers=headers)
        if res.status_code in [200, 201]: st.session_state.saved = True
    except: pass

def draw_radar_chart():
    raw_data = st.session_state.octagon
    categories = [LABELS_ES.get(k, k) for k in raw_data.keys()]
    values = [*list(raw_data.values()), list(raw_data.values())[0]]
    categories = [*categories, categories[0]]
    fig = go.Figure(data=[go.Scatterpolar(r=values, theta=categories, fill='toself', line=dict(color='#0047AB'))])
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False, height=350)
    return fig

# --- 6. FLUJO PRINCIPAL ---
init_session()

if not st.session_state.started:
    # Pantalla de Bienvenida y Registro
    st.title("Audeo Intelligence")
    st.markdown("##### Auditoría de Personalidad y Capacidad Emprendedora")
    
    with st.form("registro_form"):
        c1, c2 = st.columns(2)
        name = c1.text_input("Nombre Completo")
        age = c1.number_input("Edad", 18, 99, 30)
        exp = c2.selectbox("Experiencia previa", ["Primer emprendimiento", "Socio fundador previo", "Inversor / Corporativo"])
        sector = c2.selectbox("Sector de Proyecto", list(SECTOR_MAP.keys()))
        
        if st.form_submit_button("🚀 INICIAR EVALUACIÓN", use_container_width=True):
            if name:
                st.session_state.data = filter_questions_by_sector(load_all_questions(), SECTOR_MAP[sector])
                st.session_state.user_data = {"name": name, "age": age, "venture_type": sector, "experience": exp}
                st.session_state.started = True
                st.rerun()
            else: st.error("Por favor, introduce tu nombre.")

elif st.session_state.finished:
    # Pantalla de Resultados
    ire, avg, flags, triggers = calculate_final_score()
    if not st.session_state.saved: save_result_to_supabase(ire, avg, flags, triggers)
    
    st.header(f"Resultados Audeo: {st.session_state.user_data['name']}")
    k1, k2, k3 = st.columns(3)
    k1.metric("IRE", f"{ire}/100")
    k2.metric("Potencial", avg)
    k3.metric("Fricción", flags)

    c_radar, c_info = st.columns([1, 1])
    with c_radar: st.plotly_chart(draw_radar_chart(), use_container_width=True)
    with c_info:
        st.markdown("### Diagnóstico")
        st.write(generate_text_report(ire, avg, flags))
        if triggers: st.error("⚠️ Alertas Críticas:\n" + "\n".join([f"- {t}" for t in triggers]))

    st.divider()
    pdf = create_pdf(ire, avg, flags, triggers, st.session_state.user_data, st.session_state.octagon)
    st.download_button("📄 DESCARGAR INFORME EJECUTIVO PDF", pdf, f"Audeo_{st.session_state.user_id}.pdf", "application/pdf", use_container_width=True)
    
    if st.button("🔄 Nueva Evaluación", use_container_width=True):
        st.session_state.clear(); st.rerun()

else:
    # Pantalla de Juego (Preguntas)
    q = st.session_state.data[st.session_state.current_step]
    st.progress(st.session_state.current_step / len(st.session_state.data))
    
    st.subheader(q['TITULO'])
    st.markdown(f'<div class="big-narrative">{q["NARRATIVA"]}</div>', unsafe_allow_html=True)
    
    st.write("##### Tu decisión estratégica:")
    for opt in ['A', 'B', 'C', 'D']:
        txt = q.get(f'OPCION_{opt}_TXT')
        if txt and txt != "None":
            if st.button(txt, key=f"{opt}_{st.session_state.current_step}", use_container_width=True):
                parse_logic(q.get(f'OPCION_{opt}_LOGIC'), ord(opt)-64, st.session_state.current_step)
                st.session_state.current_step += 1
                if st.session_state.current_step >= len(st.session_state.data): st.session_state.finished = True
                st.rerun()