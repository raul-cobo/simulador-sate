import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import random
from datetime import datetime

# --- CONFIGURACIÓN DE DIMENSIONES ---
TRADUCCION_SAPE = {
    "risk_propensity": "Propensión al Riesgo",
    "innovativeness": "Innovación",
    "locus_control": "Locus de Control",
    "ambiguity_tolerance": "Tolerancia a la Ambigüedad",
    "self_efficacy": "Autoeficacia",
    "achievement": "Necesidad de Logro",
    "autonomy": "Autonomía",
    "resilience": "Resiliencia",
    "leadership": "Liderazgo",
    "emotional_stability": "Estabilidad Emocional"
}

# --- 1. LÓGICA DE CÁLCULO Y LÍMITES ---

def obtener_limites_sector(df_sector):
    limites = {}
    for _, row in df_sector.iterrows():
        q_data = {}
        for letra in ['A', 'B', 'C', 'D']:
            logic = str(row.get(f'OPCION_{letra}_LOGIC', ''))
            if logic and logic != 'nan':
                for regla in logic.split('|'):
                    partes = regla.strip().split()
                    if len(partes) >= 2:
                        dim, val = partes[0], int(partes[1])
                        if dim not in q_data: q_data[dim] = []
                        q_data[dim].append(val)
        for dim, valores in q_data.items():
            if dim not in limites: limites[dim] = {'max': 0, 'min': 0}
            limites[dim]['max'] += max(valores + [0])
            limites[dim]['min'] += min(valores + [0])
    return limites

def calcular_resultados_sape(respuestas, df_sector, limites):
    sumas_brutas = {}
    for q_id, letra in respuestas.items():
        # Usamos loc para buscar por el índice original del CSV
        fila = df_sector.loc[int(q_id)]
        logic = str(fila.get(f'OPCION_{letra}_LOGIC', ''))
        if logic and logic != 'nan':
            for regla in logic.split('|'):
                partes = regla.strip().split()
                if len(partes) >= 2:
                    dim, val = partes[0], int(partes[1])
                    sumas_brutas[dim] = sumas_brutas.get(dim, 0) + val
    
    scores_finales = {}
    for dim, suma in sumas_brutas.items():
        if dim in limites:
            l_max, l_min = limites[dim]['max'], limites[dim]['min']
            rango = l_max - l_min
            if rango != 0:
                p = ((suma - l_min) / rango) * 100
                scores_finales[dim] = round(max(0, min(100, p)), 1)
            else:
                scores_finales[dim] = 50.0
    return scores_finales

# --- 2. GRÁFICO ---

def generar_radar_chart(scores):
    if not scores: return None
    labels = [TRADUCCION_SAPE.get(k, k) for k in scores.keys()]
    values = list(scores.values())
    labels.append(labels[0]); values.append(values[0])
    
    fig = go.Figure(data=go.Scatterpolar(
        r=values, theta=labels, fill='toself',
        line_color='#83ABF1', fillcolor='rgba(131, 171, 241, 0.3)'
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100], color='white'),
                   angularaxis=dict(color='white')),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'), margin=dict(l=60, r=60, t=20, b=20)
    )
    return fig

# --- 3. INTERFAZ ---

def run_sape_interface(supabase):
    try:
        df = pd.read_csv('SATE_personalidad_emprendeora v4.csv', sep=';')
    except:
        st.error("Error cargando CSV.")
        return

    sector = st.session_state.get('sub_prueba_elegida')
    # Definimos df_sector aquí para que esté disponible en todo el ámbito de la función
    df_sector = df[df['SECTOR'] == sector].copy()
    
    if 'sape_answers' not in st.session_state: st.session_state.sape_answers = {}
    if 'sape_idx' not in st.session_state: st.session_state.sape_idx = 0
    
    idx = st.session_state.sape_idx
    total = len(df_sector)

    # --- FINALIZACIÓN: CÁLCULOS, REGISTRO Y RESULTADOS ---
    if idx >= total:
        st.success("🏁 Auditoría SAPE Finalizada")
        
        # 1. CÁLCULOS DE AUDITORÍA
        # Obtenemos los techos y suelos del sector para normalizar
        limites = obtener_limites_sector(df_sector)
        # res contiene los rasgos del 0 al 100
        res = calcular_resultados_sape(st.session_state.sape_answers, df_sector, limites)
        
        # Algoritmo de Robustez
        potencial = sum(res.values()) / len(res) if res else 0
        friccion = 100 - potencial
        ire = potencial - friccion

        # 2. PERSISTENCIA EN SUPABASE (DATOS COMPLETOS)
        # Recuperamos el ID que se creó al inicio en audeo.py
        eval_id = st.session_state.get('current_eval_id')
        
        if eval_id:
            # Evitamos duplicar el guardado si se refresca la página
            if not st.session_state.get('sape_saved', False):
                try:
                    # Construimos el paquete completo de datos
                    datos_auditoria = {
                        "tipo_test": "SAPE",
                        "sector": sector,
                        "metricas_globales": {
                            "potencial": round(potencial, 2),
                            "friccion": round(friccion, 2),
                            "ire": round(ire, 2)
                        },
                        "puntuaciones_rasgos": res,  # El mapa de los 10 rasgos
                        "respuestas_detalle": st.session_state.sape_answers, # ID_Pregunta: Letra
                        "metadata": {
                            "total_preguntas": total,
                            "fecha_finalizacion": datetime.now().isoformat()
                        }
                    }

                    # Actualización en la base de datos
                    supabase.table("evaluations").update({
                        "results": datos_auditoria,
                        "status": "completed",
                        "completed_at": datetime.now().isoformat()
                    }).eq("id", eval_id).execute()
                    
                    st.session_state.sape_saved = True
                    st.toast("✅ Datos sincronizados con Audeo Cloud", icon="☁️")
                except Exception as e:
                    st.error(f"Error al guardar en Supabase: {e}")
        else:
            # Si llegas aquí sin ID, los datos se ven pero no se guardan
            st.error("No se detectó ID de evaluación. Verifica el inicio de la prueba.")

        # 3. INTERFAZ VISUAL DEL INFORME
        st.markdown(f"## Informe de Auditoría: {sector}")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("POTENCIAL", f"{potencial:.1f}%")
        c2.metric("FRICCIÓN", f"{friccion:.1f}%", delta_color="inverse")
        c3.metric("I.R.E.", f"{ire:.1f}", delta="ROBUSTEZ" if ire > 0 else "VULNERABILIDAD", 
                  delta_color="normal" if ire > 0 else "inverse")

        st.divider()

        col_left, col_right = st.columns([1.3, 1], gap="large")
        
        with col_left:
            st.markdown("#### 🕸️ Mapa Competencial")
            fig = generar_radar_chart(res)
            if fig: st.plotly_chart(fig, use_container_width=True)

        with col_right:
            st.markdown("#### 🚨 Descarriladores (20/90)")
            # Lógica para mostrar alertas de riesgo
            alertas = False
            for k, v in res.items():
                nombre = TRADUCCION_SAPE.get(k, k)
                if v > 90:
                    st.warning(f"**Exceso:** {nombre} ({v}%)")
                    alertas = True
                elif v < 20:
                    st.error(f"**Brecha:** {nombre} ({v}%)")
                    alertas = True
            
            if not alertas:
                st.success("Perfil dentro de rangos operativos.")

            st.write("")
            st.markdown("#### 📊 Desglose")
            for k, v in sorted(res.items(), key=lambda x: x[1], reverse=True):
                nombre = TRADUCCION_SAPE.get(k, k)
                bar_color = "#E67E22" if v < 20 or v > 90 else "#83ABF1"
                st.markdown(f"""
                    <div style='margin-bottom:8px;'>
                        <div style='display:flex; justify-content:space-between; font-size:13px;'>
                            <span>{nombre}</span><span style='color:{bar_color}; font-weight:bold;'>{v}%</span>
                        </div>
                        <div style='background-color:#1e2329; border-radius:4px; height:4px;'>
                            <div style='background-color:{bar_color}; width:{v}%; height:4px; border-radius:4px;'></div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

        if st.button("FINALIZAR Y SALIR", type="primary", use_container_width=True):
            st.session_state.clear()
            st.rerun()
            
        return # Finalizamos la ejecución de la interfaz

    # FLUJO DE PREGUNTAS CON ALEATORIZACIÓN
    q = df_sector.iloc[idx]
    
    # Preparamos y mezclamos opciones
    if f"shuffle_{idx}" not in st.session_state:
        opciones = []
        for l in ['A', 'B', 'C', 'D']:
            t = q.get(f'OPCION_{l}_TXT')
            if pd.notna(t) and str(t).strip():
                opciones.append((t, l))
        random.shuffle(opciones)
        st.session_state[f"shuffle_{idx}"] = opciones

    col_n, col_o = st.columns([0.55, 0.45], gap="large")
    with col_n:
        st.markdown(f"#### {q.get('TITULO')}")
        st.info(q.get('NARRATIVA'))
        st.progress(idx / total)

    with col_o:
        st.write("Selecciona tu respuesta:")
        for txt, letra_orig in st.session_state[f"shuffle_{idx}"]:
            if st.button(txt, key=f"btn_{idx}_{letra_orig}", type="secondary", use_container_width=True):
                st.session_state.sape_answers[str(q.name)] = letra_orig
                st.session_state.sape_idx += 1
                st.rerun()