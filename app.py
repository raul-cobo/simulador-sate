import streamlit as st
import csv
import os
import random
import string
import io

# --- CONFIGURACIÓN BÁSICA ---
st.set_page_config(page_title="Modo Diagnóstico", layout="wide")

# --- FUNCIONES DE ESTILO MÍNIMAS ---
def inject_style():
    st.markdown("""<style>
        .stApp {background-color: #050A1F; color: white;} 
        .debug-box {background-color: #222; padding: 10px; border: 1px solid yellow; margin-bottom: 20px;}
    </style>""", unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
if 'octagon' not in st.session_state:
    st.session_state.octagon = {"achievement":0, "risk_propensity":0, "innovativeness":0, "locus_control":0, "self_efficacy":0, "autonomy":0, "ambiguity_tolerance":0, "emotional_stability":0}
    st.session_state.flags = {"excitable":0, "skeptical":0, "cautious":0, "reserved":0, "passive_aggressive":0, "arrogant":0, "mischievous":0, "melodramatic":0, "diligent":0, "dependent":0}
    st.session_state.current_step = 0
    st.session_state.data = []
    st.session_state.user_id = "TEST"
    st.session_state.auth = False
    st.session_state.data_verified = False
    st.session_state.started = False

# --- LOGICA SIMPLE ---
def parse_logic(logic_str):
    if not isinstance(logic_str, str): return
    # Mapeo simple para asegurar que sumamos
    mapping = {"logro":"achievement", "riesgo":"risk_propensity", "innovacion":"innovativeness", "locus":"locus_control", "autoeficacia":"self_efficacy", "autonomia":"autonomy", "tolerancia":"ambiguity_tolerance", "estabilidad":"emotional_stability"}
    
    for part in logic_str.split('|'):
        try:
            p = part.strip().split()
            if len(p)<2: continue
            k = p[0].lower(); val = int(p[1])
            real_k = mapping.get(k, k)
            
            if real_k in st.session_state.octagon:
                st.session_state.octagon[real_k] += val
            elif real_k in st.session_state.flags:
                st.session_state.flags[real_k] += val
        except: pass

# --- APP ---
inject_style()

# 1. LOGIN
if not st.session_state.auth:
    st.title("Paso 1: Login")
    pwd = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        st.session_state.auth = True
        st.rerun()
    st.stop()

# 2. DATOS
if not st.session_state.data_verified:
    st.title("Paso 2: Datos")
    name = st.text_input("Nombre")
    if st.button("Validar"):
        st.session_state.user_data = {"name": name}
        st.session_state.data_verified = True
        st.rerun()
    st.stop()

# 3. SELECCIÓN DE SECTOR (AQUÍ ESTÁ EL DIAGNÓSTICO)
if not st.session_state.started:
    st.title("Paso 3: Selección de Sector (DIAGNÓSTICO)")
    
    # --- ZONA DE DIAGNÓSTICO DEL CSV ---
    st.markdown('<div class="debug-box">', unsafe_allow_html=True)
    st.subheader("🕵️‍♂️ Analizando archivo SATE_v1.csv...")
    
    if not os.path.exists("SATE_v1.csv"):
        st.error("❌ EL ARCHIVO NO EXISTE. Sube el CSV a GitHub.")
    else:
        st.success("✅ Archivo encontrado.")
        
        # Intento de lectura 1: Separador punto y coma
        try:
            with open("SATE_v1.csv", encoding='utf-8-sig') as f:
                content = f.read()
                lines = content.splitlines()
                st.write(f"📊 Total líneas en el archivo: **{len(lines)}**")
                st.write(f"📝 Primera línea (Cabecera): `{lines[0]}`")
                
                if ";" in lines[0]:
                    st.success("✅ Detectado separador: PUNTO Y COMA (;)")
                elif "," in lines[0]:
                    st.warning("⚠️ Detectado separador: COMA (,). El código espera punto y coma.")
                else:
                    st.error("❌ No detecto separadores válidos en la cabecera.")
        except Exception as e:
            st.error(f"Error leyendo archivo: {e}")
            
    st.markdown('</div>', unsafe_allow_html=True)
    # ------------------------------------

    def load_sector(s):
        try:
            # Forzamos lectura robusta
            with open("SATE_v1.csv", encoding='utf-8-sig') as f:
                # Detectar delimitador automáticamente
                first_line = f.readline()
                delimiter = ';' if ';' in first_line else ','
                f.seek(0) # Volver al principio
                
                reader = csv.DictReader(f, delimiter=delimiter)
                rows = list(reader)
                
            # Filtrar
            data = [r for r in rows if r['SECTOR'].strip().upper() == s]
            
            if len(data) == 0:
                st.error(f"❌ ERROR: He leído el archivo, pero he encontrado 0 preguntas para el sector {s}.")
                st.write("Sectores encontrados en el archivo:", set([r['SECTOR'] for r in rows]))
                return
            
            st.session_state.data = data
            st.session_state.started = True
            st.rerun()
            
        except Exception as e:
            st.error(f"Error fatal: {e}")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("TECH"): load_sector("TECH")
        if st.button("CONSULTORIA"): load_sector("CONSULTORIA")
    with c2:
        if st.button("HOSTELERIA"): load_sector("HOSTELERIA")
        if st.button("PYME"): load_sector("PYME")

# 4. PREGUNTAS
elif not st.session_state.get('finished'):
    if st.session_state.current_step >= len(st.session_state.data):
        st.session_state.finished = True
        st.rerun()
        
    row = st.session_state.data[st.session_state.current_step]
    
    st.progress((st.session_state.current_step + 1) / len(st.session_state.data))
    st.write(f"Pregunta {st.session_state.current_step + 1} de {len(st.session_state.data)}")
    st.markdown(f"### {row['TITULO']}")
    st.info(row['NARRATIVA'])
    
    if st.button(f"A: {row.get('OPCION_A_TXT')}"):
        parse_logic(row.get('OPCION_A_LOGIC'))
        st.session_state.current_step += 1
        st.rerun()
        
    if st.button(f"B: {row.get('OPCION_B_TXT')}"):
        parse_logic(row.get('OPCION_B_LOGIC'))
        st.session_state.current_step += 1
        st.rerun()

# 5. RESULTADOS (SIMPLE PARA VER SI LLEGA)
else:
    st.title("✅ HE LLEGADO AL FINAL CON DATOS")
    st.write("Puntuaciones acumuladas:")
    st.json(st.session_state.octagon)
    if st.button("Reiniciar"):
        st.session_state.clear()
        st.rerun()