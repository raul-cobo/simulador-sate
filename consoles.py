import streamlit as st
import pandas as pd
import json
from datetime import datetime

# ==============================================================================
# 🛡️ 1. CONSOLA ADMIN (TORRE DE CONTROL MAESTRA)
# ==============================================================================
def render_admin_dashboard(supabase):
    st.title("🛡️ Torre de Control Audeo (Admin)")
    
    # --- KPIs Globales ---
    try:
        total_orgs = supabase.table("organizations").select("*", count="exact").execute().count
        total_evals = supabase.table("evaluations").select("*", count="exact").execute().count
        c1, c2, c3 = st.columns(3)
        c1.metric("Organizaciones Activas", total_orgs)
        c2.metric("Evaluaciones Totales", total_evals)
        c3.metric("Estado del Sistema", "OPERATIVO", delta="🟢")
    except: pass

    st.divider()

    # Definición de pestañas (Corregida la coma faltante)
    tabs = st.tabs([
        "🏢 Orgs & Licencias", 
        "👥 Gestión Usuarios", 
        "📥 Carga Masiva Admin", 
        "📊 Analítica Maestra"
    ])

    # --- TAB 0: GESTIÓN DE ORGANIZACIONES ---
    with tabs[0]:
        col_izq, col_der = st.columns([1, 2])
        LISTA_SAPE = ["TECH", "CONSULTORIA", "PYME", "HOSTELERIA", "AUTOEMPLEO", "SOCIAL", "INTRA", "SALUD", "PSICOLOGIA_SANITARIA", "PSICOLOGÍA_NO_SANITARIA"]
        LISTA_SAPP = ["SANITARIA", "NO_SANITARIA"]

        with col_izq:
            try:
                all_orgs_res = supabase.table("organizations").select("*").order("id").execute()
                lista_orgs = ["➕ Crear Nueva"] + [o['id'] for o in all_orgs_res.data]
            except: lista_orgs = ["➕ Crear Nueva"]

            accion = st.selectbox("Seleccionar Organización", lista_orgs)
            
            # Valores por defecto para el formulario
            v_id, v_pass, v_lic, v_demo = "", "", 10, False
            v_sape_sect = LISTA_SAPE
            v_sapp_prof = LISTA_SAPP

            if accion != "➕ Crear Nueva":
                org_data = next((item for item in all_orgs_res.data if item["id"] == accion), None)
                if org_data:
                    v_id = org_data['id']
                    v_pass = org_data.get('password', '') 
                    v_lic = org_data.get('licenses', org_data.get('licencias', 0))
                    v_demo = org_data.get('is_demo', False)
                    raw_sectors = org_data.get('active_sectors')
                    if isinstance(raw_sectors, dict):
                        v_sape_sect = raw_sectors.get("SAPE", [])
                        v_sapp_prof = raw_sectors.get("SAPP", [])

            with st.form("admin_org_form"):
                f_id = st.text_input("ID Organización", value=v_id, disabled=(accion != "➕ Crear Nueva"))
                f_pass = st.text_input("Contraseña Manager", value=v_pass)
                f_lic = st.number_input("Licencias Totales", min_value=0, value=v_lic)
                f_demo = st.checkbox("Cuenta de demostración", value=v_demo)
                
                st.write("**Catálogo Habilitado:**")
                s_sape = st.multiselect("Sectores SAPE", LISTA_SAPE, default=v_sape_sect)
                s_sapp = st.multiselect("Perfiles SAPP", LISTA_SAPP, default=v_sapp_prof)
                
                if st.form_submit_button("💾 Guardar Configuración"):
                    try:
                        payload = {
                            "id": f_id, "name": f_id, "password": f_pass,
                            "licenses": f_lic, "is_demo": f_demo,
                            "active_sectors": {"SAPE": s_sape, "SAPP": s_sapp}
                        }
                        supabase.table("organizations").upsert(payload).execute()
                        st.success("Organización guardada.")
                        st.rerun()
                    except Exception as e: st.error(f"Error: {e}")

        with col_der:
            st.subheader("Directorio")
            if all_orgs_res.data:
                df_orgs = pd.DataFrame(all_orgs_res.data)
                # Normalizamos el nombre de la columna para la vista
                if 'licencias' in df_orgs.columns: df_orgs = df_orgs.rename(columns={'licencias': 'licenses'})
                st.dataframe(df_orgs[['id', 'licenses', 'password']], use_container_width=True, hide_index=True)

    # --- TAB 2: CARGA MASIVA (ADMIN) ---
    with tabs[2]:
        st.subheader("📥 Importación Masiva de Usuarios")
        try:
            orgs_list = [o['id'] for o in all_orgs_res.data]
            target_org = st.selectbox("Elegir Organización Destino", orgs_list)
        except: target_org = None
        
        file_admin = st.file_uploader("Subir Excel o CSV", type=["xlsx", "csv"], key="admin_uploader")
        if file_admin and target_org:
            df_admin = pd.read_csv(file_admin) if file_admin.name.endswith('.csv') else pd.read_excel(file_admin)
            st.dataframe(df_admin.head())
            if st.button("🚀 Procesar Carga"):
                if 'username' in df_admin.columns and 'password' in df_admin.columns:
                    preparados = [{"username": str(r['username']).strip(), "password": str(r['password']).strip(), "role": "STUDENT", "org_id": target_org} for _, r in df_admin.iterrows()]
                    supabase.table("users").upsert(preparados).execute()
                    st.success(f"Se han cargado/actualizado {len(preparados)} usuarios.")
                else: st.error("Faltan columnas 'username' o 'password'.")

# ==============================================================================
# 🏢 2. CONSOLA MANAGER (CLIENTE B2B)
# ==============================================================================
def render_manager_dashboard(supabase):
    org_id = st.session_state.user_data.get('org_id')
    
    # 1. Carga de datos de la organización
    try:
        res = supabase.table("organizations").select("*").eq("id", org_id).single().execute()
        org_config = res.data
    except:
        st.error("Error al conectar con la base de datos.")
        return

    # Detectar nombre de columna de licencias
    lic_col = 'licenses' if 'licenses' in org_config else 'licencias'
    licenses_avail = org_config.get(lic_col, 0)
    privs = org_config.get('privileges', {})

    st.title(f"🏢 Panel Manager: {org_id}")
    st.metric("Licencias Disponibles", licenses_avail)
    
    tabs = st.tabs(["👥 Mi Equipo", "📥 Carga Masiva", "🎯 Asignar Pruebas", "📊 Resultados"])

    # --- TAB 0: GESTIÓN MANUAL ---
    with tabs[0]:
        st.subheader("Crear Usuario Individual")
        with st.form("manual_user_form"):
            new_u = st.text_input("Email/Usuario").strip()
            new_p = st.text_input("Contraseña").strip()
            if st.form_submit_button("Registrar Alumno (-1 Licencia)"):
                if licenses_avail > 0 and new_u and new_p:
                    # Comprobar si ya existe
                    exist = supabase.table("users").select("username").eq("username", new_u).execute()
                    if exist.data:
                        st.error(f"El usuario '{new_u}' ya existe.")
                    else:
                        try:
                            supabase.table("users").insert({"username": new_u, "password": new_p, "role": "STUDENT", "org_id": org_id}).execute()
                            supabase.table("organizations").update({lic_col: licenses_avail - 1}).eq("id", org_id).execute()
                            st.success(f"Usuario {new_u} creado."); st.rerun()
                        except Exception as e: st.error(f"Error: {e}")
                else: st.error("No hay licencias o faltan datos.")

    # --- TAB 1: CARGA MASIVA MANAGER ---
    with tabs[1]:
        st.subheader("Importación Masiva")
        st.info(f"Puedes cargar hasta {licenses_avail} alumnos.")
        file_mgr = st.file_uploader("Seleccionar archivo", type=["xlsx", "csv"], key="mgr_uploader")
        if file_mgr:
            df_mgr = pd.read_csv(file_mgr) if file_mgr.name.endswith('.csv') else pd.read_excel(file_mgr)
            num_req = len(df_mgr)
            st.dataframe(df_mgr.head())
            if st.button(f"🚀 Cargar {num_req} alumnos"):
                if num_req > licenses_avail:
                    st.error("Licencias insuficientes.")
                elif 'username' not in df_mgr.columns or 'password' not in df_mgr.columns:
                    st.error("Columnas requeridas: username, password")
                else:
                    try:
                        preparados = [{"username": str(r['username']).strip(), "password": str(r['password']).strip(), "role": "STUDENT", "org_id": org_id} for _, r in df_mgr.iterrows()]
                        supabase.table("users").upsert(preparados).execute()
                        supabase.table("organizations").update({lic_col: licenses_avail - num_req}).eq("id", org_id).execute()
                        st.success("Importación exitosa."); st.rerun()
                    except Exception as e: st.error(f"Fallo en carga: {e}")

    # --- TAB 2: ASIGNAR PRUEBAS (Lógica de filtrado JSON) ---
    with tabs[2]:
        st.subheader("Asignar Evaluación")
        
        # Procesar catálogo de la org
        catalog = org_config.get('active_sectors')
        if isinstance(catalog, str) and catalog != "ALL":
            try: catalog = json.loads(catalog)
            except: catalog = {}
        
        valid_types = []
        sape_opts, sapp_opts = [], []
        
        if catalog == "ALL" or not catalog:
            valid_types = ["SAPE", "SAPP"]
            sape_opts = ["TECH", "CONSULTORIA", "PYME", "HOSTELERIA", "AUTOEMPLEO", "SOCIAL", "INTRA", "SALUD", "PSICOLOGIA_SANITARIA", "PSICOLOGÍA_NO_SANITARIA"]
            sapp_opts = ["SANITARIA", "NO_SANITARIA"]
        elif isinstance(catalog, dict):
            if catalog.get("SAPE"): 
                valid_types.append("SAPE"); sape_opts = catalog["SAPE"]
            if catalog.get("SAPP"): 
                valid_types.append("SAPP"); sapp_opts = catalog["SAPP"]

        if not valid_types:
            st.warning("No tienes sectores habilitados.")
        else:
            try:
                users_res = supabase.table("users").select("username").eq("org_id", org_id).eq("role", "STUDENT").execute()
                lista_est = [u['username'] for u in users_res.data]
            except: lista_est = []

            if lista_est:
                with st.form("assign_test_form"):
                    c1, c2, c3 = st.columns(3)
                    u_sel = c1.selectbox("Alumno", lista_est)
                    t_sel = c2.selectbox("Sistema", valid_types)
                    s_sel = c3.selectbox("Sector/Perfil", sape_opts if t_sel == "SAPE" else sapp_opts)
                    is_demo = st.checkbox("Modo Demo (Prueba corta)")
                    
                    if st.form_submit_button("Habilitar"):
                        try:
                            supabase.table("evaluations").insert({
                                "user_id": u_sel, "test_type": t_sel, "sector": s_sel,
                                "org_id": org_id, "status": "pending", "is_demo_test": is_demo
                            }).execute()
                            st.success(f"Test asignado a {u_sel}")
                        except Exception as e: st.error(f"Error: {e}")
            else:
                st.info("No hay alumnos registrados.")

    # --- TAB 3: RESULTADOS (Con botón de descarga) ---
    with tabs[3]:
        st.subheader("📊 Seguimiento y Notas")
        try:
            # Traemos todos los datos para extraer el IRE
            res_evals = supabase.table("evaluations").select("*").eq("org_id", org_id).execute()
            if res_evals.data:
                df_res = pd.DataFrame(res_evals.data)
                
                # Extraer puntuación si existe
                def get_score(row):
                    try:
                        if isinstance(row, dict): return row['metricas_globales'].get('ire', 'N/A')
                        return 'N/A'
                    except: return 'Pndte'

                if 'results' in df_res.columns:
                    df_res['IRE_Score'] = df_res['results'].apply(get_score)
                
                # Mostrar tabla limpia
                cols = ['user_id', 'test_type', 'sector', 'status', 'created_at']
                if 'IRE_Score' in df_res.columns: cols.append('IRE_Score')
                st.dataframe(df_res[cols], use_container_width=True, hide_index=True)
                
                # Botón de descarga CSV (Optimizado para Excel)
                csv = df_res.drop(columns=['results'], errors='ignore').to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 Descargar Reporte Completo (CSV)",
                    data=csv,
                    file_name=f"audeo_{org_id}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("Aún no hay pruebas realizadas.")
        except Exception as e: st.error(f"Error al cargar: {e}")