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

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Audeo | Simulador S.A.P.E.", page_icon="🧬", layout="wide")

# --- 2. ESTILOS ---
def inject_style(mode):
    base_css = """
        header, [data-testid="stHeader"] {display:none!important}
        footer {display:none!important}
        .main .block-container {padding-top:1rem!important; max-width:95%!important}
    """
    if mode == "login":
        theme = ".stApp{background-color:white;color:black} input{background:#F8F9FA;color:black;border:1px solid #E0E0E0} button{background:#050A1F;color:white;width:100%}"
    else:
        theme = ".stApp{background-color:#050A1F;color:white} input{background:#0F1629;color:white;border:1px solid #5D5FEF} button{background:#1A202C;color:white;border:1px solid #5D5FEF;border-radius:8px} div[data-testid='column'] button{height:180px;font-size:26px;font-weight:bold;background:#0F1629;border:2px solid #2D3748;margin-bottom:1rem}"
    st.markdown(f"<style>{base_css}\n{theme}</style>", unsafe_allow_html=True)

# --- 3. LÓGICA ---
LABELS = { "achievement": "Necesidad de Logro", "risk_propensity": "Propensión al Riesgo", "innovativeness": "Innovatividad", "locus_control": "Locus de Control Interno", "self_efficacy": "Autoeficacia", "autonomy": "Autonomía", "ambiguity_tolerance": "Tol. Ambigüedad", "emotional_stability": "Estabilidad Emocional" }
FLAGS = ["excitable", "skeptical", "cautious", "reserved", "passive_aggressive", "arrogant", "mischievous", "melodramatic", "diligent", "dependent"]
ARCHETYPES = {
    "tyrant": {"t":"Patrón de Liderazgo Coercitivo", "d":"Alta exigencia + Baja estabilidad + Bajo locus."},
    "false_prophet": {"t":"Patrón Visionario sin Ejecución", "d":"Alta creatividad + Baja orientación a resultados."},
    "micromanager": {"t":"Patrón de Bloqueo por Perfeccionismo", "d":"Alto logro + Aversión al riesgo + Baja autonomía."},
    "gambler": {"t":"Patrón de Riesgo Desmedido", "d":"Riesgo alto + Autoeficacia desbordada + Bajo locus."},
    "soldier": {"t":"Patrón Ejecutor Dependiente", "d":"Alta estabilidad + Baja autonomía e innovatividad."}
}
VAR_MAP = {"logro":"achievement", "riesgo":"risk_propensity", "innovacion":"innovativeness", "locus":"locus_control", "autoeficacia":"self_efficacy", "autonomia":"autonomy", "tolerancia":"ambiguity_tolerance", "estabilidad":"emotional_stability"}

def init_session():
    if 'octagon' not in st.session_state:
        # BASE 0: Confiamos en el CSV rebalanceado
        st.session_state.octagon = {k: 0 for k in LABELS.keys()}
        st.session_state.flags = {k: 0 for k in FLAGS}
        st.session_state.current_step = 0
        st.session_state.data = []
        st.session_state.user_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def parse_logic(logic_str):
    if not isinstance(logic_str, str): return
    for part in logic_str.split('|'):
        try:
            p = part.strip().split()
            if len(p)<2: continue
            k = p[0].lower(); val = int(p[1])
            k = VAR_MAP.get(k, k) 
            if k in st.session_state.octagon:
                # Topes 0-100
                st.session_state.octagon[k] = max(0, min(100, st.session_state.octagon[k] + val))
            elif k in st.session_state.flags:
                st.session_state.flags[k] += val
        except: pass

def calculate_results():
    o = st.session_state.octagon
    f = st.session_state.flags
    avg = sum(o.values()) / 8
    
    # Fricción: Dividimos por 3 (con ~30 puntos de flag es suficiente para alertar)
    friction = min(100, sum(f.values()) / 3)
    
    triggers = []
    # Arquetipos
    if o['achievement']>75 and o['emotional_stability']<40 and o['locus_control']<40: triggers.append(ARCHETYPES['tyrant']['t'])
    if o['innovativeness']>75 and o['self_efficacy']>75 and o['achievement']<40: triggers.append(ARCHETYPES['false_prophet']['t'])
    if o['achievement']>75 and o['risk_propensity']<40 and o['autonomy']<40: triggers.append(ARCHETYPES['micromanager']['t'])
    if o['risk_propensity']>75 and o['self_efficacy']>75 and o['locus_control']<40: triggers.append(ARCHETYPES['gambler']['t'])
    if o['innovativeness']<40 and o['autonomy']<40 and o['emotional_stability']>75: triggers.append(ARCHETYPES['soldier']['t'])
    
    # IRE
    ire = avg - (friction * 0.5)
    if avg < 40: ire -= 15 # Penalización por perfil insuficiente
    if triggers: ire -= 5
    
    return max(0, min(100, ire)), round(avg,2), round(friction,2), triggers

def draw_pdf(ire, avg, fric, triggers, user, stats):
    b = io.BytesIO(); c = canvas.Canvas(b, pagesize=A4); w,h = A4
    c.setFillColorRGB(0.02,0.04,0.12); c.rect(0,h-100,w,100,fill=1)
    c.setFillColorRGB(1,1,1); c.setFont("Helvetica-Bold",16); c.drawRightString(w-30,h-50,"INFORME TÉCNICO S.A.P.E.")
    
    y = h-130; c.setFillColorRGB(0,0,0); c.setFont("Helvetica",10)
    c.drawString(40,y,f"Candidato: {user.get('name')}"); c.drawString(300,y,f"ID: {st.session_state.user_id}"); y-=40
    
    c.setFont("Helvetica-Bold",12); c.drawString(40,y,"1. MÉTRICAS"); y-=25
    c.setFont("Helvetica",10)
    c.drawString(50,y,f"IRE: {ire}/100"); c.drawString(200,y,f"POTENCIAL: {avg}/100"); c.drawString(350,y,f"FRICCIÓN: {fric}"); y-=40
    
    c.setFont("Helvetica-Bold",12); c.drawString(40,y,"2. PERFIL COMPETENCIAL"); y-=25
    for k,v in stats.items():
        c.setFont("Helvetica",9); c.drawString(50,y,LABELS.get(k,k))
        # Barra semáforo
        c.setFillColorRGB(0.9,0.9,0.9); c.rect(200,y,150,8,fill=1,stroke=0)
        
        # Color Semáforo (Rojo <25, Amarillo <60, Verde <75, Rojo >75)
        col = (0.8,0.2,0.2) 
        if v >= 25 and v < 60: col = (0.9,0.7,0)
        if v >= 60 and v <= 75: col = (0.2,0.6,0.2)
        if v > 75: col = (0.8,0.2,0.2)
        
        c.setFillColorRGB(*col); c.rect(200,y,v*1.5,8,fill=1,stroke=0)
        c.setFillColorRGB(0,0,0); c.drawString(360,y,str(round(v,1))); y-=15
    
    c.showPage(); c.save(); b.seek(0); return b

# --- 4. INTERFAZ ---
init_session()

# Login
if not st.session_state.get("auth"):
    inject_style("login"); c1,c2,c3 = st.columns([1,2,1])
    with c2:
        st.markdown("### Simulador S.A.P.E.")
        pwd = st.text_input("Clave", type="password")
        if st.button("Entrar"):
            if pwd == st.secrets["general"]["password"]: st.session_state.auth=True; st.rerun()
            else: st.error("Error")
    st.stop()

inject_style("app")

# Datos
if not st.session_state.data_verified:
    st.markdown("#### Datos del Candidato")
    name = st.text_input("Nombre"); age = st.number_input("Edad",18,99)
    if st.button("Continuar") and name:
        st.session_state.user_data={"name":name}; st.session_state.data_verified=True; st.rerun()

# Sector
elif not st.session_state.started:
    st.markdown("#### Selecciona Sector")
    def go(s):
        try:
            # Asegúrate de subir SATE_v2_balanced.csv renombrado a SATE_v1.csv
            rows = list(csv.DictReader(open("SATE_v1.csv"), delimiter=";"))
            st.session_state.data = [r for r in rows if r['SECTOR']==s or r['SECTOR']=="TECH"]
            st.session_state.user_data['sector']=s; st.session_state.started=True; st.rerun()
        except: st.error("Falta el archivo de preguntas.")
    
    c1,c2 = st.columns(2)
    with c1:
        if st.button("Startup Tech"): go("TECH")
        if st.button("PYME"): go("PYME")
    with c2:
        if st.button("Consultoría"): go("CONSULTORIA")
        if st.button("Hostelería"): go("HOSTELERIA")

# Preguntas
elif not st.session_state.finished:
    if st.session_state.current_step >= len(st.session_state.data): st.session_state.finished=True; st.rerun()
    row = st.session_state.data[st.session_state.current_step]
    st.progress((st.session_state.current_step+1)/len(st.session_state.data))
    st.markdown(f"### {row['TITULO']}")
    c1,c2 = st.columns([2,1])
    with c1: st.info(row['NARRATIVA'])
    with c2:
        if st.button("A: "+row.get('OPCION_A_TXT','')): parse_logic(row.get('OPCION_A_LOGIC')); st.session_state.current_step+=1; st.rerun()
        if st.button("B: "+row.get('OPCION_B_TXT','')): parse_logic(row.get('OPCION_B_LOGIC')); st.session_state.current_step+=1; st.rerun()
        if row.get('OPCION_C_TXT'): 
            if st.button("C: "+row.get('OPCION_C_TXT','')): parse_logic(row.get('OPCION_C_LOGIC')); st.session_state.current_step+=1; st.rerun()
        if row.get('OPCION_D_TXT'): 
            if st.button("D: "+row.get('OPCION_D_TXT','')): parse_logic(row.get('OPCION_D_LOGIC')); st.session_state.current_step+=1; st.rerun()

# Resultados
else:
    ire, avg, fric, triggers = calculate_results()
    st.title(f"Informe {st.session_state.user_data['name']}")
    c1,c2,c3 = st.columns(3)
    c1.metric("IRE", f"{ire}/100"); c2.metric("Potencial", f"{avg}/100"); c3.metric("Fricción", fric)
    
    pdf = draw_pdf(ire, avg, fric, triggers, st.session_state.user_data, st.session_state.octagon)
    st.download_button("Descargar PDF", pdf, "informe.pdf", "application/pdf")
    if st.button("Reiniciar"): st.session_state.clear(); st.rerun()