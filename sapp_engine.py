import streamlit as st
import pandas as pd

TRADUCCION_COMPETENCIAS = {
    "therapeutic_alliance": "Alianza terapéutica",
    "reflective_practice": "Práctica reflexiva",
    "ethical_integrity": "Integridad ética",
    "professionalism": "Profesionalidad",
    "case_formulation": "Formulación de caso",
    "differential_diagnosis": "Diagnóstico diferencial",
    "evidence_based_treatment": "Tratamiento basado en evidencia",
    "risk_management": "Gestión de riesgos",
    "clinical_psychometrics": "Psicometría clínica",
    "diagnostic_manuals": "Manuales diagnósticos",
    "health_records": "Registros de salud",
    "telepractice": "Telepráctica"
}

def calcular_resultados_sapp(respuestas_usuario, df_preguntas):
    resultados = {}
    df_preguntas = df_preguntas.copy()
    df_preguntas['ID'] = df_preguntas['ID'].astype(str)

    for q_id, letra in respuestas_usuario.items():
        fila = df_preguntas[df_preguntas['ID'] == str(q_id)]
        if fila.empty: continue
        logica = fila.iloc[0].get(f'OPCION_{letra}_LOGIC')
        if logica and str(logica).strip() not in ['0', 'nan', '']:
            partes = str(logica).split()
            comp_id, puntos = partes[0], int(partes[1])
            resultados[comp_id] = resultados.get(comp_id, 0) + puntos

    informe_final = {}
    for comp_id, suma in resultados.items():
        porcentaje = max(0, min(100, (suma + 10) * 5))
        
        # 🚦 Lógica de colores SAPP solicitada
        if porcentaje <= 30: color, hex, est = "🔴 Rojo", "#FF4B4B", "Competencia no adquirida"
        elif porcentaje <= 50: color, hex, est = "🟠 Naranja", "#FFA500", "Competencia no apta"
        elif porcentaje <= 70: color, hex, est = "🟡 Amarillo", "#F4D03F", "Competencia en desarrollo"
        else: color, hex, est = "🟢 Verde", "#27AE60", "Competencia adquirida"
            
        informe_final[comp_id] = {
            "nombre": TRADUCCION_COMPETENCIAS.get(comp_id, comp_id.title()),
            "porcentaje": porcentaje,
            "color_label": color,
            "hex": hex,
            "estatus": est
        }
    return informe_final

# ==========================================
# ⚙️ CONFIGURACIÓN
# ==========================================
CSV_FILE = 'SATE_perfil_profesional_FINAL_100.csv'
SEPARATOR = ';' 
COLUMNA_GRUPO = 'GRUPO'
COLUMNA_SECTOR = 'SECTOR'

# Mapeo: Lo que tienes en la Base de Datos -> Lo que busca en el CSV
SECTOR_MAP = {
    "Psicología sanitaria": "SANITARY_PSYCH",
    "Psícología educativa": "EDU_PSYCH",
    "Psicología social": "SOCIAL_PSYCH",
    "Psicología organizacional": "ORG_PSYCH"
}

def load_questions():
    """Carga CSV y repara texto dañado (cp1252)"""
    try:
        # 1. Leer como UTF-8
        df = pd.read_csv(CSV_FILE, sep=SEPARATOR, encoding='utf-8')
        
        # 2. Reparar Mojibake (Símbolos raros)
        def reparar_texto(texto):
            if isinstance(texto, str):
                try:
                    return texto.encode('cp1252').decode('utf-8')
                except:
                    return texto
            return texto

        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].apply(reparar_texto)

        # 3. Limpieza de nombres
        df.columns = df.columns.str.strip()
        if COLUMNA_GRUPO in df.columns:
            df[COLUMNA_GRUPO] = df[COLUMNA_GRUPO].astype(str).str.strip()
        if COLUMNA_SECTOR in df.columns:
            df[COLUMNA_SECTOR] = df[COLUMNA_SECTOR].astype(str).str.strip()
            
        return df

    except Exception as e:
        st.error(f"❌ Error leyendo CSV: {e}")
        return None

# ==========================================
# 🧠 MOTOR PRINCIPAL
# ==========================================
def run_sapp_interface(supabase):
    
    st.markdown("## 🧬 Evaluación de Perfil Profesional (SAPP)")

    # 1. Cargar TODAS las preguntas
    raw_df = load_questions()
    if raw_df is None: return

    # 2. IDENTIFICAR EL SECTOR DEL USUARIO
    # Necesitamos saber si eres 'Sanitario', 'Educativo', etc.
    if 'sapp_user_sector_code' not in st.session_state:
        try:
            eval_id = st.session_state.get('sapp_eval_id')
            if eval_id:
                # Consultamos a Supabase qué sector tiene esta evaluación
                response = supabase.table('evaluations').select('sector').eq('id', eval_id).single().execute()
                sector_db = response.data.get('sector') # Ej: "Sanitario"
                
                # Traducimos "Sanitario" -> "SANITARY_PSYCH"
                codigo_sector = SECTOR_MAP.get(sector_db)
                
                if codigo_sector:
                    st.session_state.sapp_user_sector_code = codigo_sector
                else:
                    st.error(f"Error: El sector '{sector_db}' no está en mi mapa de códigos.")
                    return
            else:
                st.error("Error: No hay ID de evaluación.")
                return
        except Exception as e:
            st.error(f"Error obteniendo sector: {e}")
            return

    # 3. FILTRADO MAESTRO POR SECTOR
    # Aquí nos quedamos SOLO con las preguntas de TU sector (ej: 120 preguntas)
    user_sector = st.session_state.sapp_user_sector_code
    full_df = raw_df[raw_df[COLUMNA_SECTOR] == user_sector].reset_index(drop=True)
    
    if len(full_df) == 0:
        st.warning(f"⚠️ No he encontrado preguntas para el sector: {user_sector}")
        return

    # ---------------------------------------------------------
    # 🏛️ FASE 0: EL LOBBY (Selección de Competencia)
    # ---------------------------------------------------------
    
    # Inicializar sesión
    if 'sapp_selected_group' not in st.session_state:
        st.session_state.sapp_selected_group = None
    if 'sapp_current_q' not in st.session_state:
        st.session_state.sapp_current_q = 0
    if 'sapp_answers' not in st.session_state:
        st.session_state.sapp_answers = {}

    if st.session_state.sapp_selected_group is None:
        st.info(f"👋 Perfil detectado: **{user_sector}**. Selecciona bloque:")
        
        # Contamos preguntas (Ahora sí darán 40 aprox)
        counts = full_df[COLUMNA_GRUPO].value_counts()

        c1, c2, c3 = st.columns(3)
        
        if c1.button(f"🧠 Personales\n({counts.get('PERSONALES', 0)})", use_container_width=True):
            st.session_state.sapp_selected_group = "PERSONALES"
            st.session_state.sapp_current_q = 0
            st.rerun()
            
        if c2.button(f"💼 Profesionales\n({counts.get('PROFESIONALES', 0)})", use_container_width=True):
            st.session_state.sapp_selected_group = "PROFESIONALES"
            st.session_state.sapp_current_q = 0
            st.rerun()
            
        if c3.button(f"🛠️ Técnicas\n({counts.get('TECNICAS', 0)})", use_container_width=True):
            st.session_state.sapp_selected_group = "TECNICAS"
            st.session_state.sapp_current_q = 0
            st.rerun()

        st.divider()
        if st.button("⬅️ Salir"):
            st.session_state.clear()
            st.rerun()
        return

    # ---------------------------------------------------------
    # 🚀 FASE 1: LOGICA DEL EXAMEN
    # ---------------------------------------------------------
    grupo_actual = st.session_state.sapp_selected_group
    
    # Filtramos por GRUPO (Ahora de 120 pasamos a 40)
    df_bloque = full_df[full_df[COLUMNA_GRUPO] == grupo_actual].reset_index(drop=True)
    
    total_questions = len(df_bloque)
    current_q_index = st.session_state.sapp_current_q
    
    # Barra de Progreso
    if total_questions > 0:
        st.progress(current_q_index / total_questions, text=f"{grupo_actual}: {current_q_index + 1}/{total_questions}")

    # --- FINAL DEL BLOQUE ---
    if current_q_index >= total_questions and total_questions > 0:
        st.success(f"✅ ¡Bloque {grupo_actual} completado!")
        
        if st.button("📊 Ver Informe de Resultados", use_container_width=True, type="primary"):
            try:
                # 1. Calculamos el informe con los datos actuales
                informe = calcular_resultados_sapp(st.session_state.sapp_answers, df_bloque)
                
                # 2. Guardamos en la sesión para que audeo.py lo pinte
                st.session_state.sapp_final_results = informe
                
                # 3. Intentamos guardar en Supabase SOLO si tenemos el ID
                eval_id = st.session_state.get('sapp_eval_id')
                
                if eval_id: # <--- EVITA EL ERROR BIGINT: NONE
                    supabase.table("evaluations").update({
                        "final_scores": informe,
                        "status": "completed"
                    }).eq("id", eval_id).execute()
                else:
                    st.warning("⚠️ No se encontró ID de evaluación en base de datos, pero verás el informe en pantalla.")
                
                # 4. Saltamos a la fase de resultados
                st.session_state.fase = "RESULTADOS"
                st.rerun()
                
            except Exception as e:
                st.error(f"Error al procesar resultados: {e}")
        return
    # ---------------------------------------------------------
    # 🎨 FASE 2: TU DISEÑO (55% / 45%)
    # ---------------------------------------------------------
    q_data = df_bloque.iloc[current_q_index]
    
    col_narrativa, col_opciones = st.columns([0.55, 0.45], gap="large")
    
    # Izquierda
    with col_narrativa:
        st.markdown(f"### {q_data.get('TITULO', 'Pregunta')}")
        st.info(q_data.get('NARRATIVA', '...'), icon="👁️")

    # Derecha
    with col_opciones:
        st.write("Selecciona tu respuesta:")
        opciones = [
            q_data.get('OPCION_A_TXT'), q_data.get('OPCION_B_TXT'),
            q_data.get('OPCION_C_TXT'), q_data.get('OPCION_D_TXT')
        ]
        
        # Definimos las letras para saber cuál es cuál
        letras = ['A', 'B', 'C', 'D']
        
        for i, txt in enumerate(opciones):
            if pd.notna(txt) and str(txt).strip() != "":
                if st.button(f"{txt}", key=f"btn_{grupo_actual}_{current_q_index}_{i}", use_container_width=True):
                    # BIEN: Guardamos el ID real del CSV y la LETRA de la opción
                    id_real = str(q_data['ID'])
                    letra_elegida = letras[i]
                    
                    st.session_state.sapp_answers[id_real] = letra_elegida
                    st.session_state.sapp_current_q += 1
                    st.rerun()

    st.divider()
    if st.button("🔙 Cancelar Bloque", type="secondary"):
        st.session_state.sapp_selected_group = None
        st.session_state.sapp_current_q = 0
        st.rerun()