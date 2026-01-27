import streamlit as st
import csv
import os
import random
import string
import io
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from PIL import Image

# --- GESTIÓN DE PDF (Opcional, no rompe si falla) ---
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# --- 1. CONFIGURACIÓN INICIAL (OBLIGATORIO PRIMERA LÍNEA) ---
st.set_page_config(page_title="Audeo | Oryon Edition", page_icon="🧬", layout="wide")

# --- 2. ESTILOS (TU DISEÑO DE CONFIANZA V50.8) ---
def inject_style(mode):
    # CSS Base para limpiar la interfaz
    base_css = """
    <style>
        header, [data-testid="stHeader"] {display: none !important;}
        footer {display: none !important;}
        .block-container {padding-top: 1rem !important; padding-bottom: 2rem !important;}
        
        /* Estilo para el Logo de Oryon en el Dashboard */
        .oryon-logo-container {
            display: flex;
            justify-content: center;
            margin-bottom: 20px;
        }
        .oryon-logo-container img {
            max-height: 80px; /* Ajusta altura del logo */
            width: auto;
        }
    </style>
    """
    
    # CSS Específico
    if mode == "login":
        theme_css = """<style>.stApp {background-color: #FFFFFF !important; color: #000000 !important;}</style>"""
    elif mode == "dashboard":
        # Fondo oscuro profesional para el cuadro de mando
        theme_css = """<style>.stApp {background-color: #0E1117 !important; color: #FAFAFA !important;}</style>"""
    else: # Modo Dark (Test)
        theme_css = """<style>.stApp {background-color: #0E1117 !important; color: #FAFAFA !important;}</style>"""
    
    st.markdown(base_css + theme_css, unsafe_allow_html=True)

# --- 3. DATOS Y LÓGICA (V50.8 BASE) ---

SECTOR_MAP = {
    "Startup Tecnológica (Scalable)": "TECH", "Consultoría / Servicios Profesionales": "CONSULTORIA",
    "Pequeña y Mediana Empresa (PYME)": "PYME", "Hostelería y Restauración": "HOSTELERIA",
    "Autoempleo / Freelance": "AUTOEMPLEO", "Emprendimiento Social": "SOCIAL",
    "Intraemprendimiento": "INTRA", "Salud": "SALUD",
    "Psicología Sanitaria": "PSICOLOGIA_SANITARIA", "Psicología no sanitaria": "PSICOLOGÍA_NO_SANITARIA"
}

# --- 4. FUNCIONES DE LÓGICA DEL TEST (V50.8) ---
# (Nota: Usamos la lógica de cálculo v50.8 para no romper nada visualmente hoy)

def safe_rerun():
    try: st.rerun()
    except: st.experimental_rerun()

@st.cache_data
def load_questions():
    filename = 'SATE_v1.csv'
    if not os.path.exists(filename): return []
    for enc in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
        try:
            with open(filename, encoding=enc, errors='strict') as f:
                data = list(csv.DictReader(f, delimiter=';'))
                if data and 'SECTOR' in data[0]: return data
        except: continue
    return []

# Parser simple de v50.8 (Sin la lógica matemática nueva para no romper la demo visual)
def parse_logic(logic_str):
    if not logic_str or not isinstance(logic_str, str): return
    # Diccionario simple de mapeo para evitar errores básicos
    KEY_MAP = {"risk": "risk_propensity", "innovation": "innovativeness", "locus": "locus_control", 
               "ambiguity": "ambiguity_tolerance", "stability": "emotional_stability"}
    
    parts = logic_str.split('|')
    for part in parts:
        try:
            tokens = part.strip().split()
            if len(tokens) < 2: continue
            key = tokens[0].lower().strip()
            val = int(tokens[1])
            final_key = KEY_MAP.get(key, key) # Mapeo básico
            
            # Sumar directamente (Lógica v50.8 original)
            if final_key in st.session_state.traits: st.session_state.traits[final_key] += val
            elif final_key in st.session_state.flags: st.session_state.flags[final_key] += val
        except: continue

def calculate_results():
    # Lógica Visual v50.8
    # Normalización simple para que el gráfico no explote
    total = sum(st.session_state.traits.values())
    factor = 500/total if total > 500 else 1
    
    traits_norm = {k: v*factor for k,v in st.session_state.traits.items()}
    avg = sum(traits_norm.values())/8
    
    # Fricción
    fric = sum(st.session_state.flags.values())
    friction = min(100, (fric/50)*100) # Escalado visual
    
    ire = avg * (1 - friction/200)
    
    triggers = [k for k,v in st.session_state.flags.items() if v > 10]
    return round(ire, 2), round(avg, 2), round(friction, 2), triggers, [], 0

def get_ire_text(score):
    if score >= 75: return "Nivel ÉLITE: Alta viabilidad."
    if score >= 60: return "Nivel SÓLIDO: Buen potencial."
    if score >= 40: return "Nivel MEDIO: Riesgos operativos."
    return "Nivel CRÍTICO: Alta probabilidad de bloqueo."

# --- 5. CUADRO DE MANDO ORYON (DASHBOARD) ---
def render_oryon_dashboard():
    inject_style("dashboard")
    
    # LOGO UPLOADER (EN SIDEBAR)
    st.sidebar.divider()
    st.sidebar.markdown("### ⚙️ Configuración Visual")
    uploaded_logo = st.sidebar.file_uploader("Subir Logo Corporativo", type=['png', 'jpg', 'jpeg'])
    
    # HEADER DEL DASHBOARD
    c_logo, c_title = st.columns([1, 5])
    with c_logo:
        if uploaded_logo:
            st.image(uploaded_logo, width=100)
        else:
            # Placeholder si no hay logo
            st.markdown("## 🏢") 
    with c_title:
        st.title("Talent Command Center")
        st.caption("Monitorización de Cohorte en Tiempo Real")

    st.divider()

    # GENERACIÓN DE DATOS SIMULADOS (Para que siempre se vea bonito)
    # Generamos 25 candidatos aleatorios
    np.random.seed(42) # Semilla para que los datos "aleatorios" sean estables en la demo
    n_candidatos = 25
    data = {
        'ID': [f'CND-{i:03d}' for i in range(1, n_candidatos + 1)],
        'Sector': np.random.choice(['TECH', 'SOCIAL', 'SALUD', 'CONSULTORIA'], n_candidatos),
        'IRE': np.random.randint(35, 98, n_candidatos),
        'Potencial': np.random.randint(45, 95, n_candidatos),
        'Friccion': np.random.randint(5, 75, n_candidatos)
    }
    df = pd.DataFrame(data)

    # KPIS PRINCIPALES
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Candidatos Analizados", f"{n_candidatos}", "+3 esta semana")
    k2.metric("IRE Promedio", f"{int(df['IRE'].mean())}/100", delta_color="normal")
    riesgo_alto = len(df[df['IRE'] < 50])
    k3.metric("Riesgo Latente", f"{riesgo_alto} Equipos", delta_color="inverse")
    k4.metric("Inversión Recomendada", "450k €", "Basado en IRE > 75")
    
    st.divider()

    # GRÁFICOS POTENTES
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader("Matriz de Decisión (Potencial vs Riesgo)")
        fig = px.scatter(df, x="Potencial", y="Friccion", color="Sector", size="IRE", hover_data=["ID"],
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        # Zonas de fondo para dar contexto
        fig.add_hrect(y0=60, y1=100, line_width=0, fillcolor="red", opacity=0.1, annotation_text="Zona de Peligro")
        fig.add_hrect(y0=0, y1=40, line_width=0, fillcolor="green", opacity=0.1, annotation_text="Zona de Inversión")
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white'), height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with c2:
        st.subheader("ADN de la Cohorte")
        # Datos simulados del radar promedio
        categories = ['Logro', 'Riesgo', 'Innov.', 'Locus', 'Autoef.', 'Auton.', 'Ambig.', 'Estab.']
        values = [75, 60, 85, 50, 70, 65, 55, 60]
        fig_r = go.Figure(data=go.Scatterpolar(r=values, theta=categories, fill='toself', name='Media'))
        fig_r.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False, 
                            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white'),
                            margin=dict(t=20, b=20, l=20, r=20), height=400)
        st.plotly_chart(fig_r, use_container_width=True)

    # TABLA DE GESTIÓN
    st.subheader("Expedientes Individuales")
    
    def highlight_ire(val):
        color = '#2ECC71' if val > 75 else '#F1C40F' if val > 50 else '#E74C3C'
        return f'color: {color}; font-weight: bold;'

    st.dataframe(df.style.applymap(highlight_ire, subset=['IRE']), use_container_width=True)


# --- 6. CONTROL DE FLUJO PRINCIPAL ---

# Inicialización de Estado
if 'traits' not in st.session_state: st.session_state.traits = {k: 10 for k in ['achievement', 'risk', 'innovation', 'locus', 'self_efficacy', 'autonomy', 'ambiguity', 'stability']}
if 'flags' not in st.session_state: st.session_state.flags = {k: 0 for k in ['excitable', 'skeptical', 'cautious', 'reserved', 'passive_aggressive', 'arrogant', 'mischievous', 'melodramatic', 'diligent', 'dependent']}
if 'current_step' not in st.session_state: st.session_state.current_step = 0
if 'user_data' not in st.session_state: st.session_state.user_data = {}
if 'sector_data' not in st.session_state: st.session_state.sector_data = []
if 'history' not in st.session_state: st.session_state.history = []

# SIDEBAR DE NAVEGACIÓN
st.sidebar.image("logo.png", width=50) if os.path.exists("logo.png") else st.sidebar.markdown("# 🧬")
modo = st.sidebar.radio("Navegación", ["Evaluación (Candidato)", "Acceso Corporativo (Oryon)"])

if modo == "Acceso Corporativo (Oryon)":
    render_oryon_dashboard()

else:
    # === AQUÍ PEGAMOS LA LÓGICA V50.8 TAL CUAL ===
    
    if st.session_state.current_step == 0:
        inject_style("login")
        st.markdown("<div style='text-align: center; margin-top: 50px;'><h1>Audeo</h1><p>Sistema de Inteligencia Emprendedora</p></div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            name = st.text_input("Nombre / ID de Candidato", placeholder="Ej: Juan Pérez")
            if st.button("INICIAR EVALUACIÓN"):
                if name:
                    st.session_state.user_data = {'name': name, 'id': ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}
                    st.session_state.current_step = 1
                    safe_rerun()

    elif st.session_state.current_step == 1:
        inject_style("dark")
        # Header simple
        c1, c2 = st.columns([1, 6])
        with c1: st.markdown("### 🧬")
        with c2: st.markdown("**Simulador S.A.P.E.** | Sistema de Análisis")
        st.divider()
        
        st.markdown("### Selecciona el Sector del Proyecto")
        def go_sector(sec_name):
            code = SECTOR_MAP.get(sec_name)
            raw = load_questions()
            st.session_state.sector_data = [r for r in raw if r['SECTOR'] == code]
            try: st.session_state.sector_data.sort(key=lambda x: int(x['MES']))
            except: pass
            if st.session_state.sector_data:
                st.session_state.current_step = 2
                safe_rerun()
            else: st.error("No hay preguntas para este sector.")

        c1, c2 = st.columns(2)
        with c1: 
            if st.button("Startup Tecnológica (Scalable)", use_container_width=True): go_sector("Startup Tecnológica (Scalable)")
            if st.button("Pequeña y Mediana Empresa (PYME)", use_container_width=True): go_sector("Pequeña y Mediana Empresa (PYME)")
            if st.button("Autoempleo / Freelance", use_container_width=True): go_sector("Autoempleo / Freelance")
            if st.button("Intraemprendimiento", use_container_width=True): go_sector("Intraemprendimiento")
            if st.button("Psicología Sanitaria", use_container_width=True): go_sector("Psicología Sanitaria")
        with c2:
            if st.button("Consultoría / Servicios Profesionales", use_container_width=True): go_sector("Consultoría / Servicios Profesionales")
            if st.button("Hostelería y Restauración", use_container_width=True): go_sector("Hostelería y Restauración")
            if st.button("Emprendimiento Social", use_container_width=True): go_sector("Emprendimiento Social")
            if st.button("Emprendimiento en Salud", use_container_width=True): go_sector("Salud")
            if st.button("Psicología no sanitaria", use_container_width=True): go_sector("Psicología no sanitaria")

    elif st.session_state.current_step == 2:
        inject_style("dark")
        # Header simple
        c1, c2 = st.columns([1, 6])
        with c1: st.markdown("### 🧬")
        with c2: st.markdown("**Simulador S.A.P.E.** | Sistema de Análisis")
        st.divider()
        
        q_idx = len(st.session_state.history)
        if q_idx >= len(st.session_state.sector_data):
            st.session_state.current_step = 3
            safe_rerun()
        
        row = st.session_state.sector_data[q_idx]
        st.progress((q_idx + 1) / len(st.session_state.sector_data))
        st.caption(f"Mes {row['MES']} | {row['TITULO']}")
        st.markdown(f"#### {row['NARRATIVA']}")
        
        def next_q(opt, logic):
            parse_logic(logic)
            st.session_state.history.append({'opcion': opt})
            safe_rerun()

        if row.get('OPCION_A_TXT'): 
            if st.button(f"A) {row['OPCION_A_TXT']}", key=f"A_{q_idx}", use_container_width=True): next_q('A', row.get('OPCION_A_LOGIC'))
        if row.get('OPCION_B_TXT'):
            if st.button(f"B) {row['OPCION_B_TXT']}", key=f"B_{q_idx}", use_container_width=True): next_q('B', row.get('OPCION_B_LOGIC'))
        if row.get('OPCION_C_TXT'):
            if st.button(f"C) {row['OPCION_C_TXT']}", key=f"C_{q_idx}", use_container_width=True): next_q('C', row.get('OPCION_C_LOGIC'))
        if row.get('OPCION_D_TXT'):
            if st.button(f"D) {row['OPCION_D_TXT']}", key=f"D_{q_idx}", use_container_width=True): next_q('D', row.get('OPCION_D_LOGIC'))

    elif st.session_state.current_step == 3:
        inject_style("dark")
        # Header simple
        c1, c2 = st.columns([1, 6])
        with c1: st.markdown("### 🧬")
        with c2: st.markdown("**Simulador S.A.P.E.** | Sistema de Análisis")
        st.divider()
        
        ire, avg, friction, triggers, _, _ = calculate_results()
        
        st.header(f"Informe S.A.P.E. | {st.session_state.user_data['name']}")
        k1, k2, k3 = st.columns(3)
        k1.metric("IRE", f"{int(ire)}/100")
        k2.metric("Potencial", f"{int(avg)}/100")
        k3.metric("Fricción", f"{int(friction)}/100", delta_color="inverse")
        
        vals = [v for v in st.session_state.traits.values()]
        # Normalizar para visualización si es necesario
        vals_plot = [min(10, v/10) for v in vals] if max(vals) > 20 else vals
        
        labels = [k.replace('_', ' ').title() for k in st.session_state.traits.keys()]
        fig = go.Figure(data=go.Scatterpolar(r=vals_plot, theta=labels, fill='toself', name='Perfil'))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])), showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
        
        c_chart, c_desc = st.columns([1, 1])
        with c_chart: st.plotly_chart(fig, use_container_width=True)
        with c_desc:
            st.markdown("### Diagnóstico")
            st.info(get_ire_text(ire))
            if triggers: st.warning(f"**Alertas:** {', '.join([t.title() for t in triggers])}")
        
        if PDF_AVAILABLE:
            def create_pdf_file():
                b = io.BytesIO()
                c = canvas.Canvas(b, pagesize=A4)
                c.drawString(50, 800, "Audeo - Informe S.A.P.E.")
                c.drawString(50, 780, f"Candidato: {st.session_state.user_data['name']}")
                c.drawString(50, 760, f"IRE: {int(ire)} | Potencial: {int(avg)} | Fricción: {int(friction)}")
                c.save()
                b.seek(0)
                return b
            st.download_button("Descargar Informe PDF", data=create_pdf_file(), file_name="Informe_SAPE.pdf", mime="application/pdf")
            
        if st.button("Reiniciar"):
            st.session_state.clear()
            safe_rerun()