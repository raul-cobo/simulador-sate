import streamlit as st
import base64
import os

def load_css():
    st.markdown("""
        <style>
        /* =========================================
           1. FONDO Y TIPOGRAFÍA GLOBAL
           ========================================= */
        .stApp {
            background-color: #0E1117;
            color: #FFFFFF;
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        }
        
        h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, div, span {
            color: #FFFFFF !important;
        }

        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        /* =========================================
           2. INPUTS (Cajas de texto)
           ========================================= */
        .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
            color: #FFFFFF !important;
            background-color: #161B22 !important;
            border: 1px solid #83ABF1 !important;
            border-radius: 8px;
        }
        .stTextInput label, .stNumberInput label, .stSelectbox label {
            color: #E0E0E0 !important;
        }
        
        /* Regla Maestra: Aplica a TODOS los botones, incluidos los Primary (Login) */
        .stButton > button, div[data-testid="stFormSubmitButton"] > button {
            background-color: #0c2963 !important; /* AZUL OSCURO SIEMPRE */
            color: white !important;
            border: 2px solid #FFFFFF !important;
            border-radius: 15px !important;
            padding: 15px 24px !important;
            font-size: 16px !important;
            font-weight: 600 !important;
            width: 100%;
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3) !important;
        }

        /* Corrección específica para eliminar el ROJO de Streamlit */
        button[kind="primary"] {
            background-color: #0c2963 !important;
            border-color: #FFFFFF !important;
        }

        /* EFECTO HOVER (RATÓN ENCIMA) */
        .stButton > button:hover, div[data-testid="stFormSubmitButton"] > button:hover {
            transform: scale(1.15) !important;    /* Ampliación del 15% */
            background-color: #0D248D !important; /* Azul más brillante */
            border-color: #83ABF1 !important;
            box-shadow: 0 10px 20px rgba(13, 36, 141, 0.5) !important;
            z-index: 9999 !important;
        }
        
        .stButton > button:active, .stButton > button:focus {
            background-color: #1535C6 !important;
            border-color: white !important;
            box-shadow: none !important;
        }

        /* =========================================
           4. EXTRAS (Cajas Login, Logos, etc.)
           ========================================= */
        .login-logo-container {
            background-color: white;
            padding: 20px;
            border-radius: 20px;
            text-align: center;
            margin-bottom: 20px;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        .login-logo-container h1, .login-logo-container p {
            color: #0E1117 !important;
        }

        .stProgress > div > div > div > div {
            background-color: #0D248D;
        }
        
        hr { border-color: #83ABF1; }
        /* =========================================
           CORRECCIÓN QUIRÚRGICA: DESPLEGABLES (Selectbox)
           Estilo idéntico a los botones: #0c2963 y borde blanco
           ========================================= */
        
        /* 1. La caja del selector (cerrada) */
        div[data-baseweb="select"] > div {
            background-color: #0c2963 !important;
            color: white !important;
            border: 2px solid #FFFFFF !important; /* Mismo borde que los botones */
            border-radius: 15px !important;       /* Mismo redondeo que los botones */
        }

        /* 2. El texto de la opción seleccionada */
        div[data-baseweb="select"] span {
            color: white !important;
        }
        
        /* 3. La flechita del selector */
        div[data-baseweb="select"] svg {
            fill: white !important;
        }

        /* 4. El menú desplegable (la lista que se abre) */
        ul[data-baseweb="menu"], div[role="listbox"] {
            background-color: #0c2963 !important;
            border: 2px solid #FFFFFF !important;
            border-radius: 15px !important;
        }
        
        /* 5. Las opciones dentro de la lista */
        li[role="option"] {
            color: white !important;
        }
        
        /* 6. Efecto al pasar el ratón por las opciones (Hover) */
        li[role="option"]:hover, li[role="option"][aria-selected="true"] {
            background-color: #0D248D !important; /* Azul más claro, igual que hover botón */
            color: white !important;
            font-weight: bold;
        }    
        /* 1. El contenedor flotante externo (El que suele salir blanco) */
        div[data-baseweb="popover"], div[data-baseweb="popover"] > div {
            background-color: #0c2963 !important;
            border: 1px solid #FFFFFF !important;
            border-radius: 8px !important;
        }

        /* 2. La lista interna (Menú) */
        ul[data-baseweb="menu"] {
            background-color: #0c2963 !important;
        }

        /* 3. Las opciones individuales (Texto y Fondo) */
        li[role="option"] {
            background-color: #0c2963 !important; /* Forzamos fondo oscuro en cada renglón */
            color: white !important;               /* Letra blanca */
        }

        /* 4. Efecto Hover (Ratón encima) y Selección */
        li[role="option"]:hover, li[role="option"][aria-selected="true"] {
            background-color: #0D248D !important;  /* Azul más brillante */
            color: white !important;
        }
        /* =========================================
           CORRECCIÓN FINAL: CABECERA SIN FONDO BLANCO
           ========================================= */
        .header-transparent-fix {
            background-color: transparent !important;
            background: none !important;
            box-shadow: none !important;
        }
        
        /* Asegura que los hijos también sean transparentes */
        .header-transparent-fix > div, 
        .header-transparent-fix h3, 
        .header-transparent-fix p,
        .header-transparent-fix img {
            background-color: transparent !important;
            box-shadow: none !important;
        }
        </style>        
    """, unsafe_allow_html=True)

# --- UTILS ---
def get_img_as_base64(file_path):
    if not os.path.exists(file_path): return ""
    with open(file_path, "rb") as f: data = f.read()
    return base64.b64encode(data).decode()

def header_con_logo(titulo, sub_info=None):
    img_b64 = get_img_as_base64("logo_blanco.png")
    col_logo, col_txt = st.columns([1, 5])
    with col_logo:
        if img_b64: st.markdown(f'<img src="data:image/png;base64,{img_b64}" style="width:100%;">', unsafe_allow_html=True)
    with col_txt:
        if sub_info: st.markdown(f"<h4 style='text-align: center; margin:0; padding-top:5px; color:#83ABF1 !important;'>{sub_info}</h4>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align: center; margin:0;'>{titulo}</h3>", unsafe_allow_html=True)
    st.write("")