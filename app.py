import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import re

# 1. CONFIGURACIÓN DE PANTALLA
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")

# --- CONFIGURACIÓN DE CONEXIÓN (IMPORTANTE) ---
# ⚠️ Reemplaza esta URL con la que obtuviste de tu Google Apps Script (Nueva Implementación -> Aplicación Web)
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbxbH7GCm95Eh0DMkBCNVD9Ce-lywoCqmUC_DraHw7DopQPeIOJ5XamcqHvf0dyBFTw/exec"

# IDs de Google Sheets
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"

@st.cache_data(ttl=60)
def cargar_datos(sheet_id, nombre_pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
        df = pd.read_csv(url, encoding='utf-8-sig')
        # Limpieza ácida de encabezados para evitar errores de espacios o caracteres raros
        df.columns = [re.sub(r'[^A-Za-z0-9]', '', str(c).strip()) for c in df.columns]
        return df.dropna(how='all')
    except:
        return pd.DataFrame()

# --- SISTEMA DE LOGIN ---
if "authenticated" not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 Control Laboral CMSG")
        pwd_input = st.text_input("Contraseña:", type="password").strip()
        if st.button("Ingresar"):
            df_u = cargar_datos(ID_USUARIOS, "Usuarios")
            if not df_u.empty:
                # Normalizar búsqueda de claves
                df_u['Clave'] = df_u['Clave'].astype(str).str.strip()
                user_match = df_u[df_u['Clave'] == pwd_input]
                if not user_match.empty:
                    info_usr = user_match.iloc[0]
                    st.session_state["authenticated"] = True
                    st.session_state["user_nombre"] = info_usr['Nombre']
                    st.session_state["user_rol"] = info_usr['Rol']
                    st.session_state["user_empresa"] = info_usr.get('Empresa', '')
                    st.rerun()
                else: st.error("❌ Clave no válida.")
    st.stop()

# --- DISEÑO POST-LOGIN ---
st.markdown("<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;}</style>", unsafe_allow_html=True)

with st.sidebar:
    st.image("https://cysasociados.cl/wp-content/uploads/2022/05/logo-cys.png", width=150)
    st.markdown(f"👤 **{st.session_state['user_nombre']}**")
    st.caption(f"Rol: {st.session_state['user_rol']}")
    anio_global = st.selectbox("Año de Análisis", ["2025", "2026"])
    if st.button("Cerrar Sesión"):
        del st.session_state["authenticated"]
        st.rerun()

# --- DEFINICIÓN DE PESTAÑAS ---
rol = st.session_state["user_rol"]
if rol == "ADMIN":
    tabs = st.tabs(["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Colaboradores", "⚙️ Administración"])
elif rol == "REVISOR":
    tabs = st.tabs(["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Colaboradores"])
else: # USUARIO
    tabs = st.tabs(["📈 Mi Avance", "👥 Masa Laboral"])

# --- PESTAÑA 1: CUMPLIMIENTO ---
with tabs[0]:
    df_av = cargar_datos(ID_AVANCE, anio_global)
    df_id_empresas = cargar_datos(ID_EMPRESAS, "Hoja 1")
    
    if not df_av.empty:
        df_display = df_av[df_av['Empresa'] == st.session_state["user_empresa"]] if rol == "USUARIO" else df_av

        try:
            mapa_estados = {1:"Carga Doc.", 2:"En Revision", 3:"Observado", 4:"No Cumple", 5:"Cumple", 8:"Sin Info", 9:"No Corresp."}
            colores_mapa = {"Carga Doc.":"#FF8C00", "En Revision":"#1E90FF", "Observado":"#FFFF00", "No Cumple":"#FF0000", "Cumple":"#00FF00", "Sin Info":"#555555", "No Corresp.":"#8B4513"}
            meses_list = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
            # Filtrar columnas que existen en el dataframe (meses)
            cols_activos = [c for c in meses_list if c in df_display.columns]
            
            with st.sidebar:
                st.divider()
                mes_sel = st.selectbox("Mes de Análisis:", ["AÑO COMPLETO"] + cols_activos)

            cols_f = [mes_sel] if mes_sel != "AÑO COMPLETO" else cols_activos
            datos_periodo = df_display[cols_f]

            # KPIs
            df_num = datos_periodo.apply(pd.to_numeric, errors='coerce')
            total_r = df_num.isin([1, 2, 3, 4, 5]).sum().sum()
            total_c = (df_num == 5).sum().sum()
            porc_c = (total_c / total_r * 100) if total_r > 0 else 0

            st.header(f"Gestión de Cumplimiento")
            k1, k2, k3 = st.columns(3)
            k1.metric("Empresas", len(df_display))
            k2.metric("% Cumplimiento Real", f"{porc_c:.1f}%")
            k3.metric("Certificados OK", int(total_c))

            st.divider()
            
            # --- DETALLE INDIVIDUAL Y DESCARGAS ---
            st.subheader("🎯 Detalle Individual y Descarga de Certificados")
            emp_v = st.selectbox("Seleccione Empresa:", sorted(list(df_display["Empresa"].unique()))) if rol != "USUARIO" else st.session_state["user_empresa"]
            
            # Obtener fila de la empresa
            row_emp = df_display[df_display["Empresa"] == emp_v].iloc[0]
            
            c_inf, c_graf = st.columns([1, 1])
            
            with c_inf:
                st.info(f"Visualizando: **{emp_v}**")
                mes_cert = st.selectbox("Seleccionar Mes para Descarga:", cols_activos)
                
                if st.button(f"🔍 Obtener Certificado {mes_cert.upper()}"):
                    # 1. Buscar el ID de Carpeta de la empresa
                    # Normalizamos nombres para el match
                    df_id_empresas['EmpresaNorm'] = df_id_empresas['Empresa'].str.strip().str.upper()
                    match_id = df_id_empresas[df_id_empresas['EmpresaNorm'] == emp_v.strip().upper()]
                    
                    if not match_id.empty:
                        id_carpeta = str(match_id.iloc[0]['IDCarpeta']).strip()
                        # 2. Construir nombre del archivo (Certificado.012025.pdf)
                        num_mes = str(meses_list.index(mes_cert) + 1).zfill(2)
                        nombre_pdf = f"Certificado.{num_mes}{anio_global}.pdf"
                        
                        with st.spinner("Buscando en Drive..."):
                            try:
                                r = requests.get(URL_APPS_SCRIPT, params={"nombre": nombre_pdf, "carpeta": id_carpeta}, timeout=15)
                                if r.text.startswith("http"):
                                    st.success("✅ ¡Archivo encontrado!")
                                    st.link_button("📥 Descargar Certificado", r.text.strip())
                                else:
                                    st.error("❌ El certificado no se encuentra disponible en Drive.")
                            except:
                                st.error("💥 Error de conexión con el servidor de archivos.")
                    else:
                        st.error("⚠️ Esta empresa no tiene un ID de carpeta configurado.")

            with c_graf:
                # Gráfico circular de la empresa seleccionada
                est_data = []
                for m in cols_activos:
                    val = row_emp[m]
                    est_data.append({'Estado': mapa_estados.get(int(val), "S/I") if pd.notna(val) else "S/I"})
                st.plotly_chart(px.pie(pd.DataFrame(est_data), names='Estado', hole=.4, color='Estado', color_discrete_map=colores_mapa, height=300), use_container_width=True)

        except Exception as e: st.error(f"Error en Pestaña 1: {e}")

# --- PESTAÑAS 2, 3 y 4 SE MANTIENEN IGUAL QUE TU CÓDIGO ---
# (Se omite repetición de Masa Laboral y Administración para brevedad, pero se mantienen en tu archivo)
