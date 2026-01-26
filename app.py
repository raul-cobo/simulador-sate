import streamlit as st
import csv
import os

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Modo Diagnóstico V47", layout="wide")

# --- ESTILOS ---
st.markdown("""<style>
    .stApp {background-color: #050A1F; color: white;} 
    .success-box {background-color: #155724; color: #d4edda; padding: 15px; border-radius: 5px; border: 1px solid #c3e6cb;}
    .error-box {background-color: #721c24; color: #f8d7da; padding: 15px; border-radius: 5px; border: 1px solid #f5c6cb;}
    .info-box {background-color: #0c5460; color: #d1ecf1; padding: 15px; border-radius: 5px; border: 1px solid #bee5eb;}
</style>""", unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
if 'octagon' not in st.session_state:
    st.session_state.octagon = {"achievement":0, "risk_propensity":0, "innovativeness":0, "locus_control":0, "self_efficacy":0, "autonomy":0, "ambiguity_tolerance":0, "emotional_stability":0}
    st.session_state.flags = {"excitable":0, "skeptical":0, "cautious":0, "reserved":0, "passive_aggressive":0, "arrogant":0, "mischievous":0, "melodramatic":0, "diligent":0, "dependent":0}
    st.session_state.current_step = 0
    st.session_state.data = []
    st.session_state.auth = False
    st.session_state.encoding_detected = 'utf-8-sig' # Por defecto

# --- LÓGICA DE PUNTOS ---
def parse_logic(logic_str):
    if not isinstance(logic_str, str): return
    mapping = {"logro":"achievement", "riesgo":"risk_propensity", "innovacion":"innovativeness", "locus":"locus_control", "autoeficacia":"self_efficacy", "autonomia":"autonomy", "tolerancia":"ambiguity_tolerance", "estabilidad":"emotional_stability"}
    for part in logic_str.split('|'):
        try:
            p = part.strip().split()
            if len(p)<2: continue
            k = p[0].lower(); val = int(p[1])
            real_k = mapping.get(k, k)
            if real_k in st.session_state.octagon: st.session_state.octagon[real_k] += val
            elif real_k in st.session_state.flags: st.session_state.flags[real_k] += val
        except: pass

# --- PANTALLA 1: DIAGNÓSTICO AUTOMÁTICO ---
st.title("🕵️‍♂️ Diagnóstico de Archivo SATE")

if not os.path.exists("SATE_v1.csv"):
    st.markdown('<div class="error-box">❌ EL ARCHIVO NO EXISTE. Súbelo a GitHub.</div>', unsafe_allow_html=True)
    st.stop()

# INTENTO DE LECTURA INTELIGENTE
try:
    # Intento 1: UTF-8 (Moderno)
    with open("SATE_v1.csv", encoding='utf-8-sig') as f:
        content = f.read()
        st.session_state.encoding_detected = 'utf-8-sig'
except UnicodeDecodeError:
    # Intento 2: Latin-1 (Excel antiguo/Español)
    try:
        with open("SATE_v1.csv", encoding='latin-1') as f:
            content = f.read()
            st.session_state.encoding_detected = 'latin-1'
    except Exception as e:
        st.error(f"❌ Error fatal leyendo el archivo: {e}")
        st.stop()

lines = content.splitlines()
count = len(lines)
preview = lines[0] if lines else "VACÍO"

# REPORTE DE ESTADO
if count > 300:
    st.markdown(f'<div class="success-box">✅ <b>ESTADO: PERFECTO</b><br>Se han detectado <b>{count} líneas</b> (Objetivo: ~320).<br>Codificación usada: {st.session_state.encoding_detected}</div>', unsafe_allow_html=True)
elif count > 150:
    st.markdown(f'<div class="info-box">⚠️ <b>ESTADO: INCOMPLETO</b><br>Se han detectado <b>{count} líneas</b>. Faltan preguntas.<br>Codificación usada: {st.session_state.encoding_detected}</div>', unsafe_allow_html=True)
else:
    st.markdown(f'<div class="error-box">❌ <b>ESTADO: CRÍTICO</b><br>Solo hay <b>{count} líneas</b>. El archivo está vacío o roto.</div>', unsafe_allow_html=True)

st.write("---")

# --- PANTALLA 2: SIMULADOR ---
if count > 1: # Solo si hay datos
    
    # Selector de Sector
    if not st.session_state.get('started'):
        st.subheader("Prueba de Carga por Sector")
        
        def load_sector(s):
            # Usamos la codificación que ya sabemos que funciona
            with open("SATE_v1.csv", encoding=st.session_state.encoding_detected) as f:
                # Detectar separador
                first = f.readline()
                sep = ';' if ';' in first else ','
                f.seek(0)
                reader = csv.DictReader(f, delimiter=sep)
                rows = list(reader)
            
            data = [r for r in rows if r['SECTOR'].strip().upper() == s]
            
            if not data:
                st.error(f"❌ Error: 0 preguntas encontradas para {s}.")
            else:
                st.session_state.data = data
                st.session_state.started = True
                st.rerun()

        c1, c2, c3, c4 = st.columns(4)
        if c1.button("CONSULTORIA"): load_sector("CONSULTORIA")
        if c2.button("TECH"): load_sector("TECH")
        if c3.button("PYME"): load_sector("PYME")
        if c4.button("HOSTELERIA"): load_sector("HOSTELERIA")

    # Preguntas
    elif not st.session_state.get('finished'):
        if st.session_state.current_step >= len(st.session_state.data):
            st.session_state.finished = True
            st.rerun()
            
        row = st.session_state.data[st.session_state.current_step]
        st.progress((st.session_state.current_step + 1) / len(st.session_state.data))
        st.write(f"Pregunta {st.session_state.current_step + 1} de {len(st.session_state.data)}")
        
        st.markdown(f"### {row['TITULO']}")
        st.info(row['NARRATIVA'])
        
        c1, c2 = st.columns(2)
        if c1.button("A: " + str(row.get('OPCION_A_TXT'))): 
            parse_logic(row.get('OPCION_A_LOGIC')); st.session_state.current_step += 1; st.rerun()
        if c2.button("B: " + str(row.get('OPCION_B_TXT'))): 
            parse_logic(row.get('OPCION_B_LOGIC')); st.session_state.current_step += 1; st.rerun()

    # Final
    else:
        st.success("✅ ¡TEST COMPLETADO! El flujo funciona.")
        st.json(st.session_state.octagon)
        if st.button("Reiniciar"): st.session_state.clear(); st.rerun()