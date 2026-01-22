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

# --- 1. CONFIGURACIÓN INICIAL (Debe ir primero) ---
st.set_page_config(page_title="Audeo Intelligence", page_icon="🧬", layout="wide")

# --- 2. INYECCIÓN CSS (DISEÑO PREMIUM) ---
def local_css():
    st.markdown("""
    <style>
        /* --- ELIMINACIÓN RADICAL DE ELEMENTOS --- */
        
        /* 1. Elimina la barra superior negra completa (Escalera, Perfil, etc.) */
        header, [data-testid="stHeader"] {
            display: none !important;
        }

        /* 2. Elimina el menú de hamburguesa y el botón de Deploy (Corona) */
        #MainMenu, .stDeployButton, [data-testid="stToolbar"] {
            display: none !important;
        }

        /* 3. Elimina el pie de página (Made with Streamlit) */
        footer {
            display: none !important;
        }

        /* 4. Elimina cualquier botón de "Manage App" que Streamlit intente forzar */
        .stAppDeployButton, .st-emotion-cache-1h9usn1, .st-emotion-cache-zq5wth {
            display: none !important;
        }

        /* --- AJUSTES DE DISEÑO --- */
        
        /* Subir el contenido para que no quede un hueco blanco arriba */
        .main .block-container {
            padding-top: 0rem !important;
            margin-top: -2rem !important;
        }

        /* Botones de respuesta estilo Audeo */
        .stButton > button {
            width: 100% !important;
            background-color: #1E1E1E !important;
            color: white !important;
            border: 1px solid #333333 !important;
            padding: 15px !important;
            border-radius: 8px !important;
            text-align: left !important;
        }

        .stButton > button:hover {
            background-color: #0047AB !important;
            border-color: #0047AB !important;
        }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- 3. SISTEMA DE LOGIN (CORREGIDO) ---
def check_password():
    """Retorna True si el usuario tiene la contraseña correcta."""
    if st.session_state.get("password_correct", False):
        return True

    # Interfaz de Login
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.write("### 🔒 Acceso Restringido")
        st.write(" ")
        
        # Input de contraseña SIN on_change para evitar recargas automáticas
        password_input = st.text_input("Introduce la clave de acceso:", type="password", key="login_pass")
        
        st.write(" ")
        # Botón manual para validar
        if st.button("Entrar al Sistema", use_container_width=True):
            if password_input == st.secrets["general"]["password"]:
                st.session_state.password_correct = True
                st.rerun()
            else:
                st.error("⛔ Clave incorrecta. Inténtalo de nuevo.")
                
        st.caption("Audeo Intelligence S.L. - Solo personal autorizado")
    return False

if not check_password():
    st.stop()  # 🛑 AQUÍ SE DETIENE TODO SI NO HAY CLAVE

# Verificación de secretos
if "supabase" not in st.secrets:
    st.error("⚠️ CRÍTICO: No existe el archivo .streamlit/secrets.toml con las claves.")
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

# --- 5. FUNCIONES ---
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
            st.error("⚠️ CRÍTICO: No encuentro 'SATE_v1.csv'.")
            st.stop()
        with open(filename, encoding='utf-8-sig') as f:
            reader = list(csv.DictReader(f, delimiter=';'))
            if len(reader) > 0 and 'SECTOR' in reader[0]: return reader
        with open(filename, encoding='utf-8-sig') as f:
            reader = list(csv.DictReader(f, delimiter=','))
            if len(reader) > 0 and 'SECTOR' in reader[0]: return reader
        st.error("❌ ERROR CSV: No encuentro la columna 'SECTOR'.")
        st.stop()
    except Exception as e:
        st.error(f"❌ Error leyendo archivo: {e}")
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
        var_key = VARIABLE_MAP.get(term, None)
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
    if ire > 75: report_text += "Perfil: Alta Resiliencia. El usuario gestiona eficazmente la presión y los recursos.\n"
    elif ire > 45: report_text += "Perfil: Equilibrado. Bases sólidas, aunque con áreas de mejora en la gestión del estrés.\n"
    else: report_text += "Perfil: Riesgo. La brecha entre Potencial y Ejecución es peligrosa.\n"
    
    if friction_points < 15: report_text += "Nivel de Fricción: BAJO. Toma de decisiones fluida."
    elif friction_points < 40: report_text += "Nivel de Fricción: MEDIO. Existen bloqueos defensivos."
    else: report_text += "Nivel de Fricción: ALTO. El estilo de gestión genera conflictos."
    return report_text

# --- FUNCIÓN GENERAR PDF ---
def create_pdf(ire, avg, toxic, triggers, user_data, octagon_data):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Encabezado
    p.setFont("Helvetica-Bold", 18)
    p.drawString(50, height - 50, "Audeo - Informe Ejecutivo")
    
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 70, f"Usuario: {user_data.get('name', 'Anon')} | ID: {st.session_state.user_id}")
    p.drawString(50, height - 85, f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    p.line(50, height - 95, width - 50, height - 95)
    
    # Métricas Principales
    y_pos = height - 130
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y_pos, f"IRE (Índice Resiliencia): {ire}/100")
    p.drawString(300, y_pos, f"Potencial Promedio: {avg}")
    y_pos -= 30
    
    # Interpretación
    p.setFont("Helvetica", 12)
    report_lines = generate_text_report(ire, avg, toxic).split('\n')
    for line in report_lines:
        p.drawString(50, y_pos, line)
    y_pos -= 20
    y_pos -= 20
    
    # Desglose Octógono
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y_pos, "Desglose de Competencias:")
    y_pos -= 20
    p.setFont("Helvetica", 10)
    
    col = 0
    start_y = y_pos
    for k, v in octagon_data.items():
        label = LABELS_ES.get(k, k)
        if col == 0:
            p.drawString(50, y_pos, f"{label}: {round(v, 1)}")
        else:
            p.drawString(300, y_pos, f"{label}: {round(v, 1)}")
            y_pos -= 15
        col = 1 - col
        if col == 0: pass 
    
    # Alertas
    y_pos = start_y - 100
    if triggers:
        p.setFillColor(colors.red)
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y_pos, "⚠️ ALERTAS DETECTADAS:")
        y_pos -= 20
        p.setFont("Helvetica", 10)
        for t in triggers:
            p.drawString(50, y_pos, f"- {t}")
            y_pos -= 15
    else:
        p.setFillColor(colors.green)
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y_pos, "✅ Sin alertas críticas detectadas.")
    
    # Pie de página
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Oblique", 8)
    p.drawString(50, 30, "Documento confidencial. Generado por Audeo Intelligence Algorithms.")
    
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

def save_result_to_supabase(ire, avg, friction, triggers):
    try:
        url_base = st.secrets["supabase"]["url"]
        api_key = st.secrets["supabase"]["key"]
        endpoint = f"{url_base}/rest/v1/resultados_sape"
        headers = {
            "apikey": api_key, "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json", "Prefer": "return=minimal"
        }
        data_payload = {
            "user_id_anonimo": st.session_state.user_id,
            "nombre_interno": st.session_state.user_data.get('name', 'Anon'),
            "sector": st.session_state.user_data.get('venture_type', 'Unknown'),
            "experiencia": st.session_state.user_data.get('experience', ''),
            "respuestas": st.session_state.choices_log,
            "score_logro": st.session_state.octagon['achievement'],
            "score_riesgo": st.session_state.octagon['risk_propensity'],
            "score_innovacion": st.session_state.octagon['innovativeness'],
            "score_locus": st.session_state.octagon['locus_control'],
            "score_autoeficacia": st.session_state.octagon['self_efficacy'],
            "score_autonomia": st.session_state.octagon['autonomy'],
            "score_ambiguedad": st.session_state.octagon['ambiguity_tolerance'],
            "score_estabilidad": st.session_state.octagon['emotional_stability'],
            "ire_final": float(ire), "potencial_final": float(avg),
            "friccion_final": float(friction), "alertas": " | ".join(triggers) if triggers else "Ninguna"
        }
        response = requests.post(endpoint, json=data_payload, headers=headers)
        if response.status_code in [200, 201]:
            st.session_state.saved = True
            st.success("✅ Resultados guardados en la nube correctamente.")
        else:
            st.error(f"❌ Error al guardar: {response.status_code} - {response.text}")
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")

def draw_radar_chart():
    raw_data = st.session_state.octagon
    categories = [LABELS_ES.get(k, k) for k in raw_data.keys()]
    values = list(raw_data.values())
    categories = [*categories, categories[0]]
    values = [*values, values[0]]
    fig = go.Figure(data=[go.Scatterpolar(
        r=values, theta=categories, fill='toself', name='Perfil',
        line=dict(color='#00CC96'), fillcolor='rgba(0, 204, 150, 0.3)'
    )])
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=False, height=300, margin=dict(t=20, b=20, l=40, r=40)
    )
    return fig

def cargar_logo():
    nombres = ["logo.png", "logo.jpg", "logo.jpeg"]
    for n in nombres:
        if os.path.exists(n): return Image.open(n)
    return None

# --- 6. FLUJO PRINCIPAL ---
init_session()
logo_img = cargar_logo()

if not st.session_state.started:
    c_spacer_L, c_main, c_spacer_R = st.columns([1, 4, 1])
    with c_main:
        col_logo, col_text = st.columns([1.5, 4]) 
        with col_logo:
            if logo_img: st.image(logo_img, use_container_width=True)
        with col_text:
            st.title("Audeo Intelligence")
            st.markdown("**Due Diligence de Talento Emprendedor**")
    
    with st.form("registro_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Nombre Completo (Uso interno)")
            age = st.number_input("Edad", min_value=18, max_value=99, value=30)
            experience = st.selectbox("Experiencia", ["Primer emprendimiento", "Con emprendimientos sin éxito", "Con emprendimientos con éxito"])
        with col2:
            partners = st.selectbox("Situación", ["Solo", "Con Socios", "Intraemprendimiento"])
            venture_selection = st.selectbox("Sector", list(SECTOR_MAP.keys()))
        st.markdown("---")
        consent = st.checkbox("Autorizo el tratamiento de datos para el análisis.")
        if st.form_submit_button("🚀 INICIAR SIMULACIÓN", use_container_width=True):
            if not consent or len(name) < 2:
                st.error("⚠️ Por favor, introduce tu nombre y acepta el tratamiento de datos.")
            else:
                all_csv_data = load_all_questions()
                sector_code = SECTOR_MAP[venture_selection]
                game_questions = filter_questions_by_sector(all_csv_data, sector_code)
                if not game_questions: st.error(f"⚠️ ERROR: No hay preguntas para {sector_code}.")
                else:
                    st.session_state.data = game_questions
                    st.session_state.user_data = {"name": name, "age": age, "venture_type": venture_selection, "experience": experience, "partners": partners}
                    st.session_state.started = True
                    st.rerun()

elif st.session_state.finished:
    ire, avg, flags, cocktails = calculate_final_score()
    
    if not st.session_state.saved: 
        save_result_to_supabase(ire, avg, flags, cocktails) 
    
    col_logo_rep, col_text_rep = st.columns([1.5, 6]) 
    with col_logo_rep:
         if logo_img: st.image(logo_img, use_container_width=True)
    with col_text_rep:
        st.subheader("Informe Audeo") 
        st.markdown(f"**ID Usuario:** {st.session_state.user_id} | **Perfil:** {st.session_state.user_data['experience']}")
    
    st.divider()
    k1, k2, k3 = st.columns(3)
    k1.metric("IRE (Resiliencia)", f"{ire}/100")
    k2.metric("Potencial", avg)
    k3.metric("Fricción", flags, delta_color="inverse")

    c_izq, c_der = st.columns([1, 1])
    with c_izq:
        st.plotly_chart(draw_radar_chart(), use_container_width=True)
    with c_der:
        st.markdown("### Resultados")
        st.markdown(generate_text_report(ire, avg, flags))
        if cocktails: st.error("⚠️ Alertas:\n" + "\n".join([f"- {c}" for c in cocktails]))
        else: st.success("✅ Sin alertas graves.")
    
    st.divider()
    
    # --- BOTÓN DE DESCARGA PDF ---
    pdf_file = create_pdf(ire, avg, flags, cocktails, st.session_state.user_data, st.session_state.octagon)
    st.download_button(
        label="📄 DESCARGAR INFORME PDF",
        data=pdf_file,
        file_name=f"Informe_Audeo_{st.session_state.user_id}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
    
    if st.button("🔄 Reiniciar", use_container_width=True):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

else:
    if len(st.session_state.data) > 0: st.progress(st.session_state.current_step / len(st.session_state.data))
    if st.session_state.current_step < len(st.session_state.data):
        row = st.session_state.data[st.session_state.current_step]
        st.markdown(f"### {row['TITULO']}")
        st.divider()
        c_text, c_actions = st.columns([55, 45])
        with c_text: st.markdown(f"""<div class="big-narrative">{row['NARRATIVA']}</div>""", unsafe_allow_html=True)
        with c_actions:
            st.markdown("##### Tu decisión:")
            step = st.session_state.current_step
            
            # BOTONES DE RESPUESTA (Estilizados por CSS arriba)
            if st.button(f"{row.get('OPCION_A_TXT')}", key=f"a_{step}", use_container_width=True): 
                parse_logic(row.get('OPCION_A_LOGIC', ''), 1, step)
                st.session_state.current_step += 1; st.rerun()
            
            if st.button(f"{row.get('OPCION_B_TXT')}", key=f"b_{step}", use_container_width=True): 
                parse_logic(row.get('OPCION_B_LOGIC', ''), 2, step)
                st.session_state.current_step += 1; st.rerun()
            
            if row.get('OPCION_C_TXT') and row.get('OPCION_C_TXT') != "None":
                if st.button(f"{row.get('OPCION_C_TXT')}", key=f"c_{step}", use_container_width=True): 
                    parse_logic(row.get('OPCION_C_LOGIC', ''), 3, step)
                    st.session_state.current_step += 1; st.rerun()
            
            if row.get('OPCION_D_TXT') and row.get('OPCION_D_TXT') != "None":
                if st.button(f"{row.get('OPCION_D_TXT')}", key=f"d_{step}", use_container_width=True): 
                    parse_logic(row.get('OPCION_D_LOGIC', ''), 4, step)
                    st.session_state.current_step += 1; st.rerun()
    else:
        st.session_state.finished = True
        st.rerun()