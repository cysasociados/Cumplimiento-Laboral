import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests

# 1. CONFIGURACIÓN DE PANTALLA Y ESTILO
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")

# Estilo para limpiar la interfaz (Ocultar menús de Streamlit)
st.markdown("<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>", unsafe_allow_html=True)

# URL de tu Apps Script (La llave que abre las carpetas de Drive)
URL_MI_SCRIPT = "https://script.google.com/a/macros/cysasociados.cl/s/AKfycbwi-UFcqZPZFmvA_80Naul4hHoJJAgUd8htMkJUmCpnGs_BAweZVOFFzclWQczMQXbq/exec"

# Inicializar log de ingresos en la memoria de la sesión
if "log_accesos" not in st.session_state:
    st.session_state["log_accesos"] = []

# IDs de tus bases de datos en Google Sheets
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1yZfnAfit8CPzPU-BnhZMEFIr6mNZs91q4SthH9TrAOo"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"

@st.cache_data(ttl=60)
def cargar_datos(sheet_id, nombre_pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        return df.dropna(how='all')
    except:
        return pd.DataFrame()

# --- 2. SISTEMA DE LOGIN POR ROLES ---
def check_password():
    if "authenticated" not in st.session_state:
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.title("🔐 Acceso Control Laboral CMSG")
            st.info("Ingrese su clave personal para continuar.")
            pwd_input = st.text_input("Contraseña:", type="password").strip()
            
            if st.button("Ingresar"):
                df_u = cargar_datos(ID_USUARIOS, "Usuarios")
                if not df_u.empty:
                    df_u['Clave'] = df_u['Clave'].astype(str).str.strip()
                    user_match = df_u[df_u['Clave'] == pwd_input]
                    
                    if not user_match.empty:
                        info_usr = user_match.iloc[0]
                        # Log detallado de ingreso
                        st.session_state["log_accesos"].append({
                            "Fecha": datetime.now().strftime("%d/%m/%Y"),
                            "Hora": datetime.now().strftime("%H:%M:%S"),
                            "Usuario": info_usr['Nombre'],
                            "Empresa": info_usr['Empresa'],
                            "Rol": info_usr['Rol']
                        })
                        
                        st.session_state["authenticated"] = True
                        st.session_state["user_nombre"] = info_usr['Nombre']
                        st.session_state["user_rol"] = info_usr['Rol']
                        st.session_state["user_empresa"] = info_usr['Empresa']
                        st.rerun()
                    else:
                        st.error("❌ Clave no válida.")
                else:
                    st.error("⚠️ Error de conexión con la base de usuarios.")
        return False
    return True

if not check_password():
    st.stop()

# --- 3. BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.image("https://cysasociados.cl/wp-content/uploads/2022/05/logo-cys.png", width=150)
    st.markdown(f"👤 **{st.session_state['user_nombre']}**")
    st.caption(f"Rol: {st.session_state['user_rol']}")
    if st.session_state["user_rol"] == "USUARIO":
        st.caption(f"Empresa: {st.session_state['user_empresa']}")
    
    st.divider()
    anio_global = st.selectbox("Año de Análisis", ["2025", "2026"])
    if st.button("Cerrar Sesión"):
        del st.session_state["authenticated"]
        st.rerun()

st.title(f"Bienvenido a Control Laboral CMSG 👋")

# --- 4. CONFIGURACIÓN DE PESTAÑAS POR ROL ---
rol = st.session_state["user_rol"]
if rol == "ADMIN":
    tabs = st.tabs(["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Colaboradores", "⚙️ Administración"])
elif rol == "REVISOR":
    tabs = st.tabs(["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Colaboradores"])
else: # USUARIO EECC
    tabs = st.tabs(["📈 Mi Avance", "👥 Masa Laboral"])

# --- PESTAÑA 1: CUMPLIMIENTO Y BUSCADOR DE CERTIFICADOS ---
with tabs[0]:
    df_av = cargar_datos(ID_AVANCE, anio_global)
    df_eecc = cargar_datos(ID_EMPRESAS, "Hoja 1")
    
    if not df_av.empty:
        df_display = df_av[df_av['Empresa'] == st.session_state["user_empresa"]] if rol == "USUARIO" else df_av

        try:
            mapa_estados = {1:"Carga Doc.", 2:"En Revision", 3:"Observado", 4:"No Cumple", 5:"Cumple", 8:"Sin Info", 9:"No Corresp."}
            colores_mapa = {"Carga Doc.":"#FF8C00", "En Revision":"#1E90FF", "Observado":"#FFFF00", "No Cumple":"#FF0000", "Cumple":"#00FF00", "Sin Info":"#555555", "No Corresp.":"#8B4513"}
            meses_list = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
            dic_mm = {m: str(i+1).zfill(2) for i, m in enumerate(meses_list)}
            
            cols_activos = [c for c in meses_list if c in df_display.columns]
            
            with st.sidebar:
                st.divider()
                mes_sel = st.selectbox("Mes de Análisis:", ["AÑO COMPLETO"] + cols_activos)

            cols_f = [mes_sel] if mes_sel != "AÑO COMPLETO" else cols_activos
            datos_periodo = df_display[cols_f]

            # KPIs Superiores
            mask_real = datos_periodo.isin([1, 2, 3, 4, 5])
            t_real = mask_real.sum().sum()
            t_cumple = (datos_periodo == 5).sum().sum()
            porc_c = (t_cumple / t_real * 100) if t_real > 0 else 0

            st.header(f"Gestión de Cumplimiento")
            k1, k2, k3 = st.columns(3)
            k1.metric("Unidades", len(df_display))
            k2.metric("% Cumplimiento Real", f"{porc_c:.1f}%")
            al_dia = ( (datos_periodo == 5).any(axis=1) & ~datos_periodo.isin([1, 2, 3, 4]).any(axis=1) ).sum()
            k3.metric("Empresas al Día", al_dia)

            st.divider()
            # SECCIÓN DE HALLAZGOS Y ROBOT BUSCADOR
            st.subheader("🎯 Detalle Específico y Certificados")
            emp_v = st.selectbox("Seleccione Empresa:", sorted(list(df_display["Empresa"].unique()))) if rol != "USUARIO" else st.session_state["user_empresa"]
            row_emp = df_display[df_display["Empresa"] == emp_v].iloc[0]

            col_hallazgos, col_descarga = st.columns([2, 1])
            
            with col_hallazgos:
                st.markdown(f"**Hallazgos Auditoría ({mes_sel}):**")
                # Busca en la columna 'Obs Auditoria'
                obs = row_emp["Obs Auditoria"] if "Obs Auditoria" in row_emp else ""
                if pd.notna(obs) and str(obs).strip() != "":
                    st.warning(obs)
                else:
                    st.success("✅ Sin observaciones pendientes para este periodo.")

            with col_descarga:
                st.markdown("**Buscador de Certificados:**")
                if mes_sel == "AÑO COMPLETO":
                    st.info("Seleccione un mes en el menú lateral.")
                else:
                    try:
                        # Buscamos el ID_Carpeta en la hoja de empresas
                        id_carpeta = df_eecc[df_eecc['Empresa'] == emp_v]['ID_Carpeta'].iloc[0]
                        mm_str = dic_mm.get(mes_sel.lower())
                        nombre_busqueda = f"Certificado.{mm_str}{anio_global}" # Ej: Certificado.082025
                        
                        if st.button(f"🔍 Buscar Certificado {mes_sel}"):
                            with st.spinner("Consultando en Drive..."):
                                response = requests.get(f"{URL_MI_SCRIPT}?nombre={nombre_busqueda}&carpeta={id_carpeta}")
                                if "http" in response.text:
                                    st.success("¡Documento encontrado!")
                                    st.link_button("📥 Descargar PDF", response.text)
                                else:
                                    st.error("Archivo no encontrado. Revise el nombre en Drive.")
                    except:
                        st.error("Error: Falta ID_Carpeta en la base de Empresas.")

            st.divider()
            # GRÁFICOS (

# Pie de página
st.markdown("---")
st.caption("Sistema de gestión de datos en tiempo real, desarrollado por C & S Asociados Ltda. para Control Laboral CMSG")