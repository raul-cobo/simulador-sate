import streamlit as st
import pandas as pd
import numpy as np
import csv
import os
import random
import string
import io
import plotly.graph_objects as go
import plotly.express as px

# --- GESTIÓN DE PDF ---
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Audeo | Oryon Edition", page_icon="🧬", layout="wide")

# --- 2. ESTILOS ---
def inject_style(mode):
    # CSS Base
    base_css = """
    <style>
        header, [data-testid="stHeader"] {display: none !important;}
        footer {display: none !important;}
        .block-container {padding-top: 1rem !important; padding-bottom: 2rem !important;}
        
        /* Estilos Oryon Dashboard */
        .metric-card {
            background-color: #1E1E1E;
            border: 1px solid #333;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
        }
        .stDataFrame { border-radius: 10px; overflow: hidden; }
    </style>
    """
    if mode == "login":
        theme_css = """<style>.stApp {background-color: #FFFFFF !important; color: #000000 !important;}</style>"""
    elif mode == "dashboard":
        theme_css = """<style>.stApp {background-color: #0E1117 !important; color: #FAFAFA !important;}</style>"""
    else:
        theme_css = """<style>.stApp {background-color: #0E1117 !important; color: #FAFAFA !important;}</style>"""
    
    st.markdown(base_css + theme_css, unsafe_allow_html=True)

# --- 3. LOGICA Y DICCIONARIOS (V58 BLINDADA) ---
SECTOR_MAP = {
    "Startup Tecnológica (Scalable)": "TECH", "Consultoría / Servicios Profesionales": "CONSULTORIA",
    "Pequeña y Mediana Empresa (PYME)": "PYME", "Hostelería y Restauración": "HOSTELERIA",
    "Autoempleo / Freelance": "AUTOEMPLEO", "Emprendimiento Social": "SOCIAL",
    "Intraemprendimiento": "INTRA", "Salud": "SALUD",
    "Psicología Sanitaria": "PSICOLOGIA_SANITARIA", "Psicología no sanitaria": "PSICOLOGÍA_NO_SANITARIA"
}

KEY_TRANSLATION = {
    "achievement": "achievement", "logro": "achievement", "ambition": "achievement", "success": "achievement", "profit": "achievement", "results": "achievement", "result": "achievement", "growth": "achievement", "scale": "achievement", "efficiency": "achievement", "business": "achievement", "valuation": "achievement", "cost_saving": "achievement", "financial_focus": "achievement", "money": "achievement", "wealth": "achievement", "pragmatism": "achievement", "effort": "achievement", "focus": "achievement", "discipline": "achievement", "tenacity": "achievement", "goal": "achievement", "impact": "achievement", "career": "achievement",
    "risk": "risk_propensity", "riesgo": "risk_propensity", "risk_propensity": "risk_propensity", "courage": "risk_propensity", "action": "risk_propensity", "speed": "risk_propensity", "audacity": "risk_propensity", "boldness": "risk_propensity", "investment": "risk_propensity", "debt": "risk_propensity", "financial_risk": "risk_propensity", "experimentation": "risk_propensity", "bet": "risk_propensity", "adventurous": "risk_propensity", "fast": "risk_propensity",
    "innovation": "innovativeness", "innovativeness": "innovativeness", "creativity": "innovativeness", "vision": "innovativeness", "change": "innovativeness", "strategy": "innovativeness", "future": "innovativeness", "adaptability": "innovativeness", "flexibility": "innovativeness", "curiosity": "innovativeness", "pivot": "innovativeness", "differentiation": "innovativeness", "new": "innovativeness", "smart": "innovativeness", "resourcefulness": "innovativeness", "technology": "innovativeness", "digital": "innovativeness",
    "locus": "locus_control", "locus_control": "locus_control", "control": "locus_control", "responsibility": "locus_control", "ownership": "locus_control", "realism": "locus_control", "accountability": "locus_control", "problem_solving": "locus_control", "proactivity": "locus_control", "no_excuses": "locus_control", "execution": "locus_control", "decision": "locus_control",
    "self_efficacy": "self_efficacy", "autoeficacia": "self_efficacy", "confidence": "self_efficacy", "leadership": "self_efficacy", "assertiveness": "self_efficacy", "influence": "self_efficacy", "sales": "self_efficacy", "communication": "self_efficacy", "negotiation": "self_efficacy", "management": "self_efficacy", "networking": "self_efficacy", "delegation": "self_efficacy",
    "autonomy": "autonomy", "autonomia": "autonomy", "independence": "autonomy", "freedom": "autonomy", "identity": "autonomy", "sovereignty": "autonomy", "refusal": "autonomy", "boundaries": "autonomy", "solo": "autonomy", "detached": "autonomy", "lifestyle": "autonomy",
    "ambiguity": "ambiguity_tolerance", "ambiguity_tolerance": "ambiguity_tolerance", "tolerance": "ambiguity_tolerance", "patience": "ambiguity_tolerance", "resilience": "ambiguity_tolerance", "calm": "ambiguity_tolerance", "stoicism": "ambiguity_tolerance", "hope": "ambiguity_tolerance", "trust": "ambiguity_tolerance", "uncertainty": "ambiguity_tolerance", "endurance": "ambiguity_tolerance",
    "stability": "emotional_stability", "emotional_stability": "emotional_stability", "emotional": "emotional_stability", "integrity": "emotional_stability", "ethics": "emotional_stability", "values": "emotional_stability", "justice": "emotional_stability", "honesty": "emotional_stability", "balance": "emotional_stability", "empathy": "emotional_stability", "humility": "emotional_stability", "humanity": "emotional_stability",
    "fear": "cautious", "anxiety": "cautious", "caution": "cautious", "paralysis": "cautious", "anger": "excitable", "aggression": "excitable", "conflict": "excitable", "reaction": "excitable", "doubt": "skeptical", "distrust": "skeptical", "cynicism": "skeptical", "ego": "arrogant", "pride": "arrogant", "arrogance": "arrogant", "vanity": "arrogant", "obsession": "diligent", "perfectionism": "diligent", "micromanagement": "diligent", "submission": "dependent", "dependency": "dependent", "obedience": "dependent", "manipulation": "mischievous", "lie": "mischievous", "greed": "mischievous", "victimism": "melodramatic", "drama": "melodramatic", "complaint": "melodramatic"
}

VARIABLE_TYPE = {
    "achievement": "TRAIT", "risk_propensity": "TRAIT", "innovativeness": "TRAIT", "locus_control": "TRAIT", "self_efficacy": "TRAIT", "autonomy": "TRAIT", "ambiguity_tolerance": "TRAIT", "emotional_stability": "TRAIT",
    "excitable": "FLAG", "skeptical": "FLAG", "cautious": "FLAG", "reserved": "FLAG", "passive_aggressive": "FLAG", "arrogant": "FLAG", "mischievous": "FLAG", "melodramatic": "FLAG", "diligent": "FLAG", "dependent": "FLAG"
}

TRAIT_TEXTS = {
    "achievement": { "low": "ÁREA DE MEJORA: Dificultad para mantener el foco en resultados tangibles.", "med": "FORTALEZA: Orientación sana a objetivos y capacidad de esfuerzo.", "high": "ALERTA DE BURNOUT: Obsesión por resultados sacrificando sostenibilidad." },
    "risk_propensity": { "low": "ÁREA DE MEJORA: Exceso de conservadurismo y miedo al error.", "med": "FORTALEZA: Valentía para actuar con información incompleta.", "high": "ALERTA DE IMPRUDENCIA: Tendencia a asumir riesgos desmedidos." },
    "innovativeness": { "low": "ÁREA DE MEJORA: Tendencia a replicar lo existente sin diferenciar.", "med": "FORTALEZA: Capacidad para encontrar soluciones nuevas.", "high": "ALERTA DE DISPERSIÓN: Síndrome del objeto brillante." },
    "locus_control": { "low": "RIESGO DE VICTIMISMO: Sensación de falta de control sobre el destino.", "med": "FORTALEZA: Responsabilidad proactiva sobre lo que se puede cambiar.", "high": "ALERTA DE CULPA: Asunción excesiva de responsabilidad por fallos ajenos." },
    "self_efficacy": { "low": "ÁREA DE MEJORA: Dudas sobre la propia capacidad.", "med": "FORTALEZA: Confianza sólida para vender y liderar.", "high": "ALERTA DE ARROGANCIA: Exceso de confianza que ciega ante errores." },
    "autonomy": { "low": "ÁREA DE MEJORA: Dependencia excesiva de validación externa.", "med": "FORTALEZA: Independencia operativa sana.", "high": "ALERTA DE AISLAMIENTO: Rechazo sistemático a la ayuda externa." },
    "ambiguity_tolerance": { "low": "ÁREA DE MEJORA: El estrés bloquea ante la falta de claridad.", "med": "FORTALEZA: Capacidad de operar en la niebla con calma.", "high": "ALERTA DE CAOS: Comodidad excesiva en la desorganización." },
    "emotional_stability": { "low": "ÁREA DE MEJORA: Vulnerabilidad ante la presión y contratiempos.", "med": "FORTALEZA: Gestión emocional madura en crisis.", "high": "ALERTA DE RIGIDEZ: Frialdad excesiva o falta de empatía." }
}

# --- 4. FUNCIONES CORE ---
if 'traits' not in st.session_state: st.session_state.traits = {k: 10 for k in ['achievement', 'risk_propensity', 'innovativeness', 'locus_control', 'self_efficacy', 'autonomy', 'ambiguity_tolerance', 'emotional_stability']}
if 'flags' not in st.session_state: st.session_state.flags = {k: 0 for k in ['excitable', 'skeptical', 'cautious', 'reserved', 'passive_aggressive', 'arrogant', 'mischievous', 'melodramatic', 'diligent', 'dependent']}
if 'current_step' not in st.session_state: st.session_state.current_step = 0
if 'user_data' not in st.session_state: st.session_state.user_data = {}
if 'sector_data' not in st.session_state: st.session_state.sector_data = []
if 'history' not in st.session_state: st.session_state.history = []

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

def parse_logic(logic_str):
    if not logic_str or not isinstance(logic_str, str): return
    parts = logic_str.split('|')
    for part in parts:
        try:
            tokens = part.strip().split()
            if len(tokens) < 2: continue
            raw_key = tokens[0].lower().strip()
            val = int(tokens[1])
            clean_key = KEY_TRANSLATION.get(raw_key, raw_key)
            balanced_val = int(round(val / 5.0))
            if balanced_val == 0 and val > 0: balanced_val = 1
            var_type = VARIABLE_TYPE.get(clean_key)
            if var_type == "TRAIT": st.session_state.traits[clean_key] += balanced_val
            elif var_type == "FLAG": st.session_state.flags[clean_key] += balanced_val
        except: continue

def calculate_results():
    raw_traits = st.session_state.traits.copy()
    total_raw = sum(raw_traits.values())
    final_traits = {}
    if total_raw > 500:
        factor = 500.0 / total_raw
        for k, v in raw_traits.items(): final_traits[k] = min(100, v * factor)
    else:
        for k, v in raw_traits.items(): final_traits[k] = min(100, v)
    avg = sum(final_traits.values()) / 8.0
    raw_friction = sum(st.session_state.flags.values())
    friction = min(100, (raw_friction / 40.0) * 100)
    penalty = friction / 200.0
    ire = avg * (1 - penalty)
    trait_details = []
    for k, v in final_traits.items():
        if v < 40: txt = TRAIT_TEXTS[k]["low"]
        elif v < 80: txt = TRAIT_TEXTS[k]["med"]
        else: txt = TRAIT_TEXTS[k]["high"]
        trait_details.append((k, v, txt))
    triggers = [k for k, v in st.session_state.flags.items() if v > 8]
    return round(ire, 2), round(avg, 2), round(friction, 2), triggers, trait_details

def get_ire_text(score):
    if score >= 75: return "Nivel ÉLITE: Alta viabilidad."
    if score >= 60: return "Nivel SÓLIDO: Buen potencial."
    if score >= 40: return "Nivel MEDIO: Riesgos operativos."
    return "Nivel CRÍTICO: Alta probabilidad de bloqueo."

# --- 5. CUADRO DE MANDO (ORYON DASHBOARD) ---
def render_oryon_dashboard():
    inject_style("dashboard")
    st.title("Oryon Foundation | Talent Command Center")
    st.markdown("Monitorización en tiempo real de la cohorte de emprendimiento.")
    
    # Simulación de Datos o Carga Real
    if os.path.exists("resultados_anonimos.csv"):
        try:
            df = pd.read_csv("resultados_anonimos.csv", sep=';', decimal=',')
            # Limpieza básica
            df['IRE'] = pd.to_numeric(df['IRE'], errors='coerce')
            df['Potencial'] = pd.to_numeric(df['Potencial'], errors='coerce')
            df['Banderas'] = pd.to_numeric(df['Banderas'], errors='coerce')
        except:
            st.error("Error al leer datos históricos. Mostrando datos simulados.")
            df = None
    else:
        df = None

    if df is None:
        # Generar datos simulados para la DEMO
        data = {
            'ID': [f'CAN-{i:03d}' for i in range(1, 21)],
            'Sector': [random.choice(['TECH', 'SOCIAL', 'SALUD', 'PYME']) for _ in range(20)],
            'IRE': [random.randint(30, 95) for _ in range(20)],
            'Potencial': [random.randint(40, 90) for _ in range(20)],
            'Friccion': [random.randint(0, 80) for _ in range(20)]
        }
        df = pd.DataFrame(data)

    # KPIS PRINCIPALES
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Talento Analizado", f"{len(df)}", "+5 hoy")
    k2.metric("IRE Promedio Cohorte", f"{int(df['IRE'].mean())}/100", delta_color="normal")
    riesgo_alto = len(df[df['IRE'] < 40])
    k3.metric("Riesgo Alto", f"{riesgo_alto}", delta_color="inverse")
    k4.metric("Talento Recuperable", f"{len(df) - riesgo_alto}", "Ready to Invest")
    
    st.divider()

    # GRÁFICOS
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader("Matriz de Viabilidad (Potencial vs Fricción)")
        fig = px.scatter(df, x="Potencial", y="Friccion", color="Sector", size="IRE", hover_data=["ID"],
                         color_discrete_sequence=px.colors.qualitative.Bold)
        fig.add_hrect(y0=50, y1=100, line_width=0, fillcolor="red", opacity=0.1, annotation_text="Zona de Riesgo")
        fig.add_hrect(y0=0, y1=50, line_width=0, fillcolor="green", opacity=0.1, annotation_text="Zona Viable")
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
        st.plotly_chart(fig, use_container_width=True)
    
    with c2:
        st.subheader("Radar Promedio")
        # Datos simulados para el radar promedio
        categories = ['Logro', 'Riesgo', 'Innov.', 'Locus', 'Autoef.', 'Auton.', 'Ambig.', 'Estab.']
        values = [7, 6, 8, 5, 7, 6, 5, 6] # Simulado promedio
        fig_r = go.Figure(data=go.Scatterpolar(r=values, theta=categories, fill='toself', name='Media Cohorte'))
        fig_r.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])), showlegend=False, 
                            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white'),
                            margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig_r, use_container_width=True)
        st.info("💡 El Locus de Control promedio es bajo (5/10), indicando necesidad de mentoría en 'Accountability'.")

    # TABLA DE DETALLE
    st.subheader("Expedientes Candidatos")
    
    def color_ire(val):
        color = '#2ECC71' if val > 60 else '#F1C40F' if val > 40 else '#E74C3C'
        return f'color: {color}; font-weight: bold;'
    
    st.dataframe(df.style.applymap(color_ire, subset=['IRE']), use_container_width=True)


# --- 6. NAVEGACIÓN PRINCIPAL ---

# Sidebar oculto o visible según preferencia
modo = st.sidebar.selectbox("Modo de Visualización", ["Evaluación (Candidato)", "Acceso Corporativo (Oryon)"])

if modo == "Acceso Corporativo (Oryon)":
    render_oryon_dashboard()

else:
    # MODO CANDIDATO (JUEGO)
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
            else: st.error("No hay preguntas.")

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
        c1, c2 = st.columns([1, 6])
        with c1: st.markdown("### 🧬")
        with c2: st.markdown("**Simulador S.A.P.E.** | Sistema de Análisis")
        st.divider()
        ire, avg, friction, triggers, trait_details = calculate_results()
        
        st.header(f"Informe S.A.P.E. | {st.session_state.user_data['name']}")
        k1, k2, k3 = st.columns(3)
        k1.metric("IRE", f"{ire}/100")
        k2.metric("Potencial", f"{avg}/100")
        k3.metric("Fricción", f"{friction}/100", delta_color="inverse")
        
        vals = [min(10, v/10) for v in st.session_state.traits.values()]
        labels = [k.replace('_', ' ').title() for k in st.session_state.traits.keys()]
        fig = go.Figure(data=go.Scatterpolar(r=vals, theta=labels, fill='toself', name='Perfil'))
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
                c.drawString(50, 760, f"IRE: {ire} | Potencial: {avg} | Fricción: {friction}")
                y = 720
                c.setFont("Helvetica-Bold", 12)
                c.drawString(50, y, "2. PERFIL COMPETENCIAL (DETALLE)")
                y -= 25
                c.setFont("Helvetica", 9)
                for k, score, txt in trait_details:
                    label = k.replace('_', ' ').title()
                    c.setFont("Helvetica-Bold", 10)
                    c.drawString(50, y, f"{label}: {int(score)}")
                    c.setFont("Helvetica", 9)
                    c.drawString(200, y, txt)
                    y -= 20
                    if y < 100: c.showPage(); y = 800
                c.save()
                b.seek(0)
                return b
            st.download_button("Descargar Informe PDF", data=create_pdf_file(), file_name="Informe_SAPE.pdf", mime="application/pdf")
            
        if st.button("Reiniciar"):
            st.session_state.clear()
            safe_rerun()