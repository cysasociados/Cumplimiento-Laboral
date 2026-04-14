import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import re

# 1. CONFIGURACIÓN DE PANTALLA
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")

# --- CONEXIÓN DRIVE (Tu llave maestra) ---
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbxbH7GCm95Eh0DMkBCNVD9Ce-lywoCqmUC_DraHw7DopQPeIOJ5XamcqHvf0dyBFTw/exec"

# IDs de Google Sheets
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"

# Inicializar bitácora
if "log_accesos" not in st.session_state:
    st.session_state["log_accesos"] = []

@st.cache_data(ttl=60)
def cargar_datos(sheet_id, nombre_pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
        df = pd.read_csv(url, encoding='utf-8-sig')
        df.columns = [str(c).strip() for c in df.columns]
        return df.dropna(how='all')
    except:
        return pd.DataFrame()

# --- SISTEMA DE LOGIN ---
def check_password():
    if "authenticated" not in st.session_state:
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.title("🔐 Acceso Control Laboral CMSG")
            pwd_input = st.text_input("Contraseña:", type="password").strip()
            if st.button("Ingresar"):
                df_u = cargar_datos(ID_USUARIOS, "Usuarios")
                if not df_u.empty:
                    user_match = df_u[df_u['Clave'].astype(str).str.strip() == pwd_input]
                    if not user_match.empty:
                        info_usr = user_match.iloc[0]
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
                    else: st.error("❌ Clave no válida.")
        return False
    return True

if not check_password():
    st.stop()

# --- DISEÑO POST-LOGIN ---
st.markdown("<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;}</style>", unsafe_allow_html=True)

with st.sidebar:
    st.image("https://cysasociados.cl/wp-content/uploads/2022/05/logo-cys.png", width=150)
    st.markdown(f"👤 **{st.session_state['user_nombre']}**")
    anio_global = st.selectbox("Año de Análisis", ["2026", "2025"])
    if st.button("Cerrar Sesión"):
        del st.session_state["authenticated"]
        st.rerun()

# --- TABS ---
rol = st.session_state["user_rol"]
if rol == "ADMIN":
    tabs = st.tabs(["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Colaboradores", "⚙️ Administración"])
elif rol == "REVISOR":
    tabs = st.tabs(["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Colaboradores"])
else:
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
            
            # NORMALIZACIÓN DE MESES: El código busca tanto mayúsculas como minúsculas
            meses_posibles = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic', 
                              'ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC']
            cols_activos = [c for c in df_display.columns if c in meses_posibles]

            st.header(f"Gestión de Cumplimiento")
            
            # KPIs
            df_num = df_display[cols_activos].apply(pd.to_numeric, errors='coerce')
            k1, k2, k3 = st.columns(3)
            k1.metric("Empresas", len(df_display))
            if not df_num.empty:
                total_c = (df_num == 5).sum().sum()
                k2.metric("Certificados OK", int(total_c))
                total_r = df_num.isin([1, 2, 3, 4, 5]).sum().sum()
                porc = (total_c / total_r * 100) if total_r > 0 else 0
                k3.metric("% Avance Real", f"{porc:.1f}%")

            st.divider()

            # --- DETALLE INDIVIDUAL Y DESCARGA ---
            st.subheader("🎯 Detalle Individual y Descarga de Certificados")
            emp_v = st.selectbox("Seleccione Empresa:", sorted(list(df_display["Empresa"].unique()))) if rol != "USUARIO" else st.session_state["user_empresa"]
            
            row_emp = df_display[df_display["Empresa"] == emp_v].iloc[0]
            
            col_l, col_r = st.columns([1, 1])
            with col_l:
                st.info(f"Empresa: **{emp_v}**")
                # Escudo contra el error NoneType
                if cols_activos:
                    mes_cert = st.selectbox("Seleccionar Mes para Descarga:", cols_activos)
                    if st.button(f"🔍 Obtener Certificado {mes_cert.upper() if mes_cert else ''}"):
                        match_id = df_id_empresas[df_id_empresas['Empresa'].str.strip().str.upper() == emp_v.strip().upper()]
                        if not match_id.empty:
                            id_carpeta = str(match_id.iloc[0]['IDCarpeta']).strip()
                            # Convertimos el nombre del mes a número (ene -> 01)
                            mes_idx = meses_posibles.index(mes_cert) % 12 + 1
                            nombre_pdf = f"Certificado.{str(mes_idx).zfill(2)}{anio_global}.pdf"
                            
                            with st.spinner("Buscando en Drive..."):
                                try:
                                    r = requests.get(URL_APPS_SCRIPT, params={"nombre": nombre_pdf, "carpeta": id_carpeta}, timeout=15)
                                    if r.text.startswith("http"):
                                        st.success("✅ ¡Archivo encontrado!")
                                        st.link_button("📥 Descargar Certificado", r.text.strip())
                                    else: st.error("❌ No disponible en Drive.")
                                except: st.error("Fallo de conexión.")
                        else: st.error("ID de carpeta no configurado.")
                else:
                    st.warning("No se detectaron columnas de meses en el archivo.")

            with col_r:
                # Gráfico circular individual
                pie_data = []
                for m in cols_activos:
                    val = row_emp[m]
                    if pd.notna(val):
                        pie_data.append({'Estado': mapa_estados.get(int(val), "S/I")})
                if pie_data:
                    st.plotly_chart(px.pie(pd.DataFrame(pie_data), names='Estado', hole=.4, color='Estado', color_discrete_map=colores_mapa, height=300), use_container_width=True)

        except Exception as e: st.error(f"Error en Pestaña 1: {e}")

# --- PESTAÑA 2: KPIs ---
if rol != "USUARIO":
    with tabs[1]:
        st.header("🏢 KPIs Nivel Empresa")
        st.dataframe(cargar_datos(ID_EMPRESAS, "Hoja 1"), use_container_width=True)

# --- PESTAÑA 3: MASA LABORAL ---
idx_masa = 1 if rol == "USUARIO" else 2
with tabs[idx_masa]:
    if anio_global == "2025": st.warning("⚠️ No disponible para 2025.")
    else:
        st.header(f"Análisis de Dotación - {anio_global}")
        mes_masa = st.selectbox("Mes Masa:", ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"])
        df_masa = cargar_datos(ID_COLABORADORES, f"{mes_masa}{anio_global[-2:]}")
        if not df_masa.empty:
            df_masa_f = df_masa[df_masa['Razón Social'] == st.session_state["user_empresa"]] if rol == "USUARIO" else df_masa
            m1, m2, m3 = st.columns(3)
            m1.metric("Dotación Total", len(df_masa_f))
            m2.metric("Extranjeros", len(df_masa_f[df_masa_f['Nacionalidad'] != 'Chilena']) if 'Nacionalidad' in df_masa_f.columns else 0)
            st.dataframe(df_masa_f, use_container_width=True)

# --- PESTAÑA 4: ADMIN ---
if rol == "ADMIN":
    with tabs[3]:
        st.header("⚙️ Administración")
        st.subheader("📅 Log de Accesos")
        if st.session_state["log_accesos"]: st.table(pd.DataFrame(st.session_state["log_accesos"]))
        st.divider()
        st.subheader("👥 Usuarios")
        st.dataframe(cargar_datos(ID_USUARIOS, "Usuarios"), use_container_width=True)

# Pie de página
st.markdown("---")
st.caption("Sistema de gestión de datos, desarrollado por C & S Asociados Ltda. para Control Laboral CMSG")