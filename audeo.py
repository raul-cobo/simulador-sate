import streamlit as st
from supabase import create_client
import styles  # Importamos el nuevo estilo
import consoles # <--- IMPORTANTE PARA PODER LLAMAR A LAS CONSOLAS

# ==========================================
# ⚙️ CONFIGURACIÓN Y ESTADOS
# ==========================================
st.set_page_config(page_title="AUDEO Platform", layout="wide")
styles.load_css()

# Inicialización de estados
if 'fase' not in st.session_state: st.session_state.fase = "LOGIN"
if 'user_data' not in st.session_state: st.session_state.user_data = {}
if 'sistema_elegido' not in st.session_state: st.session_state.sistema_elegido = None 
if 'sub_prueba_elegida' not in st.session_state: st.session_state.sub_prueba_elegida = None
if 'datos_demo' not in st.session_state: st.session_state.datos_demo = {}

# --- CONEXIÓN ---
@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except:
        return None

supabase = init_connection()

def obtener_permisos_org(org_id):
    """Devuelve qué sistemas y sectores tiene permitidos la organización."""
    try:
        # 1. Consultar configuración
        resp = supabase.table("organizations").select("active_sectors").eq("id", org_id).single().execute()
        raw_config = resp.data.get('active_sectors')
        
        # 2. Normalizar "ALL" o Nulo
        if not raw_config or raw_config == "ALL":
            return {
                "SAPE": ["TECH", "CONSULTORIA", "PYME", "HOSTELERIA", "AUTOEMPLEO", "SOCIAL", "INTRA", "SALUD", "PSICOLOGIA_SANITARIA", "PSICOLOGÍA_NO_SANITARIA"],
                "SAPP": ["SANITARIA", "NO_SANITARIA"]
            }
            
        # 3. Parsear si viene como texto
        if isinstance(raw_config, str):
            import json
            try:
                config = json.loads(raw_config)
            except:
                return {"SAPE": [], "SAPP": []} # Error de formato
        else:
            config = raw_config

        return config # Devuelve el diccionario {"SAPE": [...], "SAPP": [...]}
        
    except Exception as e:
        print(f"Error permisos: {e}")
        return {"SAPE": [], "SAPP": []} # Cerrado por seguridad si falla

# --- COLOCA ESTO DEBAJO DE obtener_permisos_org ---

def fase_perfilado():
    styles.header_con_logo("Configuración de Perfil")
    
    st.markdown("""
    <div style="background-color: #1E2329; padding: 20px; border-radius: 10px; border-left: 5px solid #83ABF1;">
        <p style="margin: 0; font-size: 16px;">
        👋 Hola. Para ajustar correctamente el algoritmo de Audeo, necesitamos conocer tu trayectoria.
        Esta información es confidencial y se utiliza para calibrar los baremos de tu evaluación.
        </p>
    </div>
    <br>
    """, unsafe_allow_html=True)

    with st.form("form_perfilado"):
        c1, c2 = st.columns(2)
        
        # 1. Datos Demográficos
        edad = c1.number_input("Tu Edad", min_value=16, max_value=90, value=30)
        genero = c2.selectbox("Género (Opcional)", ["Prefiero no decirlo", "Hombre", "Mujer", "No binario"])
        
        st.divider()
        
        # 2. Historial Emprendedor (Según tu esquema de Word)
        st.subheader("Trayectoria Emprendedora")
        experiencia = st.radio(
            "Selecciona tu situación actual:",
            [
                "Nunca he emprendido (Primera vez)",
                "He emprendido anteriormente sin éxito",
                "He emprendido anteriormente con éxito",
                "Soy intra-emprendedor (Emprendo dentro de una organización)"
            ]
        )
        
        detalles = st.text_area("Comentarios adicionales sobre tu experiencia (Opcional):")

        submitted = st.form_submit_button("💾 Guardar Perfil y Continuar", type="primary", use_container_width=True)

        if submitted:
            try:
                # Preparamos el paquete de datos
                perfil_data = {
                    "edad": edad,
                    "genero": genero,
                    "experiencia_tipo": experiencia,
                    "experiencia_detalle": detalles
                }
                
                # Guardamos en la columna 'profile_data' de la tabla 'users'
                usuario_id = st.session_state.username
                supabase.table("users").update({"profile_data": perfil_data}).eq("username", usuario_id).execute()
                
                # Actualizamos la sesión para que el main() vea que ya NO es None
                st.session_state.user_data['profile_data'] = perfil_data
                
                st.success("✅ Perfil actualizado correctamente.")
                st.session_state.fase = "SELECTOR_SISTEMA"
                st.rerun()
                
            except Exception as e:
                st.error(f"Error al guardar el perfil: {e}")

# ==========================================
# 🖼️ PANTALLAS DEL FLUJO
# ==========================================

def fase_login():
    # Usamos columnas para centrar el formulario y que se vea profesional
    col_izq, col_centro, col_der = st.columns([1, 2, 1])

    with col_centro:
        st.markdown("### 🔐 Acceso a AUDEO")
        st.write("Introduce tus credenciales corporativas.")
        
        # Formulario de entrada
        user_input = st.text_input("Usuario o Email")
        pass_input = st.text_input("Contraseña", type="password")

        if st.button("Iniciar Sesión", type="primary", use_container_width=True):
            if not user_input or not pass_input:
                st.warning("⚠️ Por favor, rellena todos los campos.")
                return

            try:
                # 1. Buscamos al usuario en Supabase
                response = supabase.table("users").select("*").eq("username", user_input).execute()
                
                # 2. Verificamos si existe y si la contraseña coincide
                if response.data:
                    user_db = response.data[0]
                    
                    # NOTA: En producción idealmente usaríamos hashes, aquí comparamos directo
                    if user_db['password'] == pass_input:
                        
                        # --- 3. ACTUALIZACIÓN CRÍTICA DE ESTADOS ---
                        st.session_state.logged_in = True
                        st.session_state.username = user_db['username']
                        st.session_state.user_role = user_db['role']     # <--- ESTO ES LO QUE LEE EL ROUTER (ADMIN/MANAGER)
                        st.session_state.user_data = user_db             # Guardamos todo el objeto por si acaso
                        st.session_state.fase = "SELECTOR_SISTEMA"       # Estado inicial para alumnos
                        
                        st.success(f"✅ Acceso concedido. Bienvenido/a {user_db['username']}")
                        
                        # --- 4. RECARGA OBLIGATORIA ---
                        # Esto fuerza a python a volver a leer 'def main()' con los nuevos datos
                        st.rerun()
                        
                    else:
                        st.error("❌ Contraseña incorrecta.")
                else:
                    st.error("❌ El usuario no existe.")
            
            except Exception as e:
                st.error(f"Error de conexión con el servidor: {e}")

def fase_selector_sistema():
    styles.header_con_logo("Panel de Selección")
    st.write("")
    
    col1, col2 = st.columns(2, gap="large")
    
    auth_id = st.session_state.user_data.get('auth_id')
    permitidos = {"SAPE", "SAPP"} # Fallback por defecto para pruebas
    
    if supabase and auth_id:
        try:
            res = supabase.table("evaluations").select("test_type").eq("user_id", auth_id).execute()
            if res.data:
                permitidos = {r['test_type'] for r in res.data}
        except: pass

    with col1:
        st.markdown("#### Opción Emprendedora")
        if st.button("Prueba S.A.P.E.\nSistema de Análisis de la Personalidad Emprendedora", 
                     type="secondary", use_container_width=True, disabled="SAPE" not in permitidos):
            st.session_state.sistema_elegido = "SAPE"
            st.session_state.fase = "DEMOGRAFICOS"
            st.rerun()

    with col2:
        st.markdown("#### Opción Profesional")
        if st.button("Prueba S.A.P.P.\nSistema de Análisis del Perfil Profesional", 
                     type="secondary", use_container_width=True, disabled="SAPP" not in permitidos):
            st.session_state.sistema_elegido = "SAPP"
            st.session_state.fase = "DEMOGRAFICOS"
            st.rerun()

def fase_demograficos():
    styles.header_con_logo(f"Registro: {st.session_state.sistema_elegido}")
    
    col_form, _ = st.columns([2, 1])
    with col_form:
        with st.form("demo"):
            st.markdown("##### Datos Básicos")
            edad = st.number_input("Edad", 18, 99, 25)
            formacion = st.selectbox("Formación", ["Grado", "Máster", "Doctorado", "Formación Profesional", "Otros"])
            genero = st.radio("Género", ["Masculino", "Femenino", "Otro"], horizontal=True)
            
            st.write("")
            if st.form_submit_button("SIGUIENTE", type="primary", use_container_width=True):
                st.session_state.datos_demo = {"edad": edad, "form": formacion, "gen": genero}
                st.session_state.fase = "SELECTOR_SUBPRUEBA"
                st.rerun()

def fase_selector_subprueba():
    sistema = st.session_state.get('sistema_elegido')
    org_id = st.session_state.user_data.get('org_id')
    
    # 1. Recuperamos permisos
    permisos = obtener_permisos_org(org_id)
    sectores_permitidos = permisos.get(sistema, [])

    # 2. Definimos las OPCIONES_BASE según el sistema
    if sistema == "SAPP":
        titulo = "Ámbito de la Evaluación SAPP"
        opciones_base = ["SANITARIA", "NO_SANITARIA"]
        col_count = 2 
    else:
        titulo = "Sector de Análisis Emprendedor SAPE"
        opciones_base = [
            "TECH", "CONSULTORIA", "PYME", "HOSTELERIA", 
            "AUTOEMPLEO", "SOCIAL", "INTRA", "SALUD",
            "PSICOLOGIA_SANITARIA", "PSICOLOGÍA_NO_SANITARIA"
        ]
        col_count = 3

    styles.header_con_logo(titulo)
    st.write("Selecciona la opción habilitada para tu perfil:") 
    
    # 3. EL FILTRO (Aquí ya no dará error porque opciones_base existe arriba)
    opciones_finales = [opt for opt in opciones_base if opt in sectores_permitidos]
    
    # Fallback de seguridad por si la org está vacía
    if not opciones_finales and (not sectores_permitidos or sectores_permitidos == "ALL"):
        opciones_finales = opciones_base

    if not opciones_finales:
        st.error(f"⛔ No tienes sectores habilitados para {sistema}.")
        if st.button("Volver"):
            st.session_state.fase = "SELECTOR_SISTEMA"
            st.rerun()
        return

    # 4. RENDERIZADO DE BOTONES
    cols = st.columns(col_count, gap="medium")
    
    for i, opt in enumerate(opciones_finales):
        if cols[i % col_count].button(opt, use_container_width=True):
            # Guardamos la elección
            st.session_state.sub_prueba_elegida = opt
            
            try:
                # Registramos el inicio en la DB
                usuario = st.session_state.get('username')
                datos_inicio = {
                    "user_id": usuario,
                    "test_type": sistema,
                    "sector": opt,
                    "status": "pending",
                    "org_id": org_id,
                    "created_at": "now()"
                }
                
                res_db = supabase.table("evaluations").insert(datos_inicio).execute()
                
                if res_db.data:
                    # Guardamos el ID de la evaluación y avanzamos
                    st.session_state.current_eval_id = res_db.data[0]['id']
                    st.session_state.fase = "INSTRUCCIONES"
                    st.rerun()
                else:
                    st.error("Error al registrar la prueba en la base de datos.")
            except Exception as e:
                st.error(f"Error técnico: {e}")

def fase_instrucciones():
    styles.header_con_logo("Instrucciones")
    
    st.markdown("""
    <div style='background-color: rgba(255,255,255,0.05); padding: 20px; border-radius: 10px; border: 1px solid #83ABF1;'>
        <p style='font-size: 18px;'>
        Bienvenido a la prueba. A continuación se te presentarán una serie de situaciones narrativas.<br><br>
        1. Lee atentamente cada situación.<br>
        2. Selecciona la opción que mejor describa tu comportamiento habitual.<br>
        3. No hay respuestas correctas o incorrectas, sé sincero.<br>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("")
    if st.button("🚀 COMENZAR PRUEBA", type="primary", use_container_width=True):
        st.session_state.fase = "EJECUCION"  # <--- Asegúrate de que ponga EJECUCION
        st.rerun()

def fase_resultados():
    # Cabecera
    usuario = st.session_state.user_data.get('username', 'Candidato')
    edad = st.session_state.datos_demo.get('edad', 'N/A')
    formacion = st.session_state.datos_demo.get('form', 'N/A')
    sector = st.session_state.get('sapp_user_sector_code', 'Psicología sanitaria')
    bloque = st.session_state.get('sub_prueba_elegida', 'N/A')

    info_header = f"{usuario} | {edad} años | {formacion}"
    styles.header_con_logo("Informe Final", sub_info=info_header)

    st.markdown(f"<p style='text-align:center; color:#83ABF1 !important; margin-bottom:20px;'>{sector} / {bloque}</p>", unsafe_allow_html=True)
    st.divider()

    resultados = st.session_state.get('sapp_final_results', {})
    
    if not resultados:
        st.warning("No se encontraron resultados.")
    
    for comp_id, info in resultados.items():
        col_txt, col_bar = st.columns([1, 2])
        with col_txt:
            st.markdown(f"**{info['nombre']}**")
            st.caption(f"{info['color_label']} {info['estatus']}")
        with col_bar:
            st.markdown(f"""
                <div style="background-color: #333; border-radius: 12px; width: 100%; height: 24px; margin-top: 10px;">
                    <div style="background-color: {info['hex']}; width: {info['porcentaje']}%; 
                    height: 24px; border-radius: 12px; text-align: center; color: white; font-weight: bold; line-height: 24px;">
                        {info['porcentaje']}%
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
    st.write("")
    if st.button("Finalizar y Salir", type="primary", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ==========================================
# 🚦 RUTEADOR
# ==========================================
def main():
    # ---------------------------------------------------------
    # 0. INICIALIZACIÓN DE VARIABLES CRÍTICAS
    # ---------------------------------------------------------
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if 'user_role' not in st.session_state: st.session_state.user_role = 'STUDENT'
    if 'fase' not in st.session_state: st.session_state.fase = "LOGIN"

    # ---------------------------------------------------------
    # 1. PANTALLA DE LOGIN (Bloqueante)
    # ---------------------------------------------------------
    if not st.session_state.logged_in:
        fase_login()
        return # DETENEMOS aquí. No cargamos nada más hasta que haga login.

    # ---------------------------------------------------------
    # 2. ROUTER DE ROLES (El "Policía de Tráfico")
    # ---------------------------------------------------------
    # Solo llegamos aquí si logged_in es True
    rol = st.session_state.user_role

    if rol == "ADMIN":
        import consoles
        consoles.render_admin_dashboard(supabase)
        return

    elif rol == "MANAGER":
        import consoles
        consoles.render_manager_dashboard(supabase)
        return

   # ---------------------------------------------------------
    # 3. ZONA DE ESTUDIANTE (Flujo Normal SAPP/SAPE)
    # ---------------------------------------------------------
    else:
        # A. COMPROBACIÓN DE PERFIL
        profile = st.session_state.user_data.get('profile_data')
        if not profile and st.session_state.fase not in ["PERFILADO", "LOGIN"]:
             st.session_state.fase = "PERFILADO"

        # --- MÁQUINA DE ESTADOS (ZONA CRÍTICA) ---

        if st.session_state.fase == "PERFILADO":
            fase_perfilado()

      # --- SELECTOR DE SISTEMA FILTRADO ---
        elif st.session_state.fase == "SELECTOR_SISTEMA" or st.session_state.sistema_elegido is None:
            st.title("Panel de Evaluación")
            
            # Consultamos qué tiene permitido su empresa
            permisos = obtener_permisos_org(st.session_state.user_data.get('org_id'))
            
            tiene_sape = len(permisos.get("SAPE", [])) > 0
            tiene_sapp = len(permisos.get("SAPP", [])) > 0
            
            if not tiene_sape and not tiene_sapp:
                st.error("⛔ Tu organización no tiene pruebas habilitadas.")
            else:
                st.write("Selecciona tu itinerario:")
                c1, c2 = st.columns(2)
                
                if tiene_sapp:
                    if c1.button("🧠 SAPP (Perfil Competencial)", use_container_width=True):
                        st.session_state.sistema_elegido = "SAPP"
                        st.session_state.fase = "SELECTOR_SUBPRUEBA"
                        st.rerun()
                
                if tiene_sape:
                    if c2.button("🚀 SAPE (Perfil Emprendedor)", use_container_width=True):
                        st.session_state.sistema_elegido = "SAPE"
                        st.session_state.fase = "SELECTOR_SUBPRUEBA"
                        st.rerun()

        elif st.session_state.fase == "SELECTOR_SUBPRUEBA":
            fase_selector_subprueba()

        elif st.session_state.fase == "INSTRUCCIONES":
            # ASEGÚRATE DE QUE ESTA FUNCIÓN EXISTE Y TIENE UN BOTÓN
            fase_instrucciones()

        elif st.session_state.fase == "EJECUCION":
            # --- ESTA ES LA ZONA QUE SE QUEDA EN BLANCO ---
            sistema = st.session_state.get('sistema_elegido')
            eval_id = st.session_state.get('current_eval_id')
            
            if sistema == "SAPE":
                try:
                    import sape_engine
                    # Forzamos la ejecución pasando supabase
                    sape_engine.run_sape_interface(supabase)
                except Exception as e:
                    st.error(f"❌ Error al cargar el motor SAPE: {e}")
                    st.info("Revisa si el archivo sape_engine.py tiene errores de sintaxis.")
            
            elif sistema == "SAPP":
                st.info("Módulo SAPP en desarrollo.")
            
            else:
                # Si llega aquí, es que 'sistema_elegido' se ha borrado de la memoria
                st.warning("⚠️ No se detecta sistema elegido.")
                st.write(f"Estado: {st.session_state.fase} | Sistema: {sistema}")
                if st.button("Volver al inicio"):
                    st.session_state.fase = "SELECTOR_SISTEMA"
                    st.rerun()
        
        else:
            # SI LA PANTALLA ESTÁ EN BLANCO, ES QUE ESTÁ ENTRANDO AQUÍ
            st.error(f"Fase desconocida: {st.session_state.fase}")
            if st.button("Resetear a Selector"):
                st.session_state.fase = "SELECTOR_SISTEMA"
                st.rerun()

if __name__ == "__main__":
    main()