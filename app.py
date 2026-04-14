import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import re

# 1. CONFIGURACIÓN DE PANTALLA
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")

# --- CONEXIÓN DRIVE (Tu llave maestra verificada) ---
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbxbH7GCm95Eh0DMkBCNVD9Ce-lywoCqmUC_DraHw7DopQPeIOJ5XamcqHvf0dyBFTw/exec"

# IDs de Google Sheets
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"

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
                    col_clave = next((c for c in df_u.columns if 'Clave' in c or 'CLAVE' in c), 'Clave')
                    user_match = df_u[df_u[col_clave].astype(str).str.strip() == pwd_input]
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

# --- DISEÑO ---
with st.sidebar:
    st.image("https://cysasociados.cl/wp-content/uploads/2022/05/logo-cys.png", width=150)
    st.markdown(f"👤 **{st.session_state['user_nombre']}**")
    anio_global = st.selectbox("Año", ["2026", "2025"])
    if st.button("Cerrar Sesión"):
        del st.session_state["authenticated"]
        st.rerun()

rol = st.session_state["user_rol"]
if rol == "ADMIN":
    tabs = st.tabs(["📈 Avance", "🏢 KPIs", "👥 Masa Laboral", "⚙️ Admin"])
elif rol == "REVISOR":
    tabs = st.tabs(["📈 Avance", "🏢 KPIs", "👥 Masa Laboral"])
else:
    tabs = st.tabs(["📈 Mi Avance", "👥 Masa Laboral"])

# --- PESTAÑA 1: CUMPLIMIENTO ---
with tabs[0]:
    df_av = cargar_datos(ID_AVANCE, anio_global)
    df_id_empresas = cargar_datos(ID_EMPRESAS, "Hoja 1")
    
    if not df_av.empty:
        col_emp = next((c for c in df_av.columns if 'Empresa' in c or 'EMPRESA' in c), 'Empresa')
        df_display = df_av[df_av[col_emp] == st.session_state["user_empresa"]] if rol == "USUARIO" else df_av

        mapa_estados = {1:"Carga Doc.", 2:"En Revision", 3:"Observado", 4:"No Cumple", 5:"Cumple", 8:"Sin Info", 9:"No Corresp."}
        colores_mapa = {"Cumple":"#00FF00", "Observado":"#FFFF00", "No Cumple":"#FF0000", "En Revision":"#1E90FF", "Carga Doc.":"#FF8C00"}
        
        meses_posibles = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic', 
                          'ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC']
        cols_activos = [c for c in df_display.columns if c in meses_posibles]

        st.header(f"Gestión de Cumplimiento {anio_global}")
        
        # KPIs
        df_num = df_display[cols_activos].apply(pd.to_numeric, errors='coerce')
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas", len(df_display))
        if not df_num.empty:
            ok = (df_num == 5).sum().sum()
            k2.metric("Certificados OK", int(ok))
            total = df_num.isin([1, 2, 3, 4, 5]).sum().sum()
            k3.metric("% Avance", f"{(ok/total*100 if total > 0 else 0):.1f}%")

        st.divider()

        st.subheader("🎯 Detalle y Descargas")
        emp_v = st.selectbox("Seleccione Empresa:", sorted(list(df_display[col_emp].unique()))) if rol != "USUARIO" else st.session_state["user_empresa"]
        row_emp = df_display[df_display[col_emp] == emp_v].iloc[0]
        
        c1, c2 = st.columns([1, 1])
        with c1:
            st.info(f"Empresa: **{emp_v}**")
            if cols_activos:
                mes_cert = st.selectbox("Mes para Descarga:", cols_activos)
                if st.button(f"🔍 Descargar {mes_cert.upper()}"):
                    col_id_folder = next((c for c in df_id_empresas.columns if 'IDCarpeta' in c or 'ID' in c), 'IDCarpeta')
                    match_id = df_id_empresas[df_id_empresas[col_emp].str.strip().str.upper() == emp_v.strip().upper()]
                    
                    if not match_id.empty:
                        id_f = str(match_id.iloc[0][col_id_folder]).strip()
                        mes_num = (meses_posibles.index(mes_cert) % 12) + 1
                        nombre_pdf = f"Certificado.{str(mes_num).zfill(2)}{anio_global}.pdf"
                        
                        r = requests.get(URL_APPS_SCRIPT, params={"nombre": nombre_pdf, "carpeta": id_f})
                        if r.text.startswith("http"):
                            st.success("✅ Encontrado")
                            st.link_button("📥 Descargar", r.text.strip())
                        else: st.error("No disponible")
            else: st.warning("Sin meses detectados.")

        with c2:
            pie_list = [{'Estado': mapa_estados.get(int(row_emp[m]), "S/I")} for m in cols_activos if pd.notna(row_emp[m])]
            if pie_list:
                st.plotly_chart(px.pie(pd.DataFrame(pie_list), names='Estado', hole=.4, color='Estado', color_discrete_map=colores_mapa, height=300), use_container_width=True)

# --- PESTAÑA 2: KPIs ---
if rol != "USUARIO":
    with tabs[1]:
        st.dataframe(cargar_datos(ID_EMPRESAS, "Hoja 1"), use_container_width=True)

# --- PESTAÑA 3: MASA LABORAL ---
idx_masa = 1 if rol == "USUARIO" else 2
with tabs[idx_masa]:
    if anio_global == "2025": st.warning("No disponible para 2025.")
    else:
        mes_m = st.selectbox("Mes Masa:", ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"])
        df_m = cargar_datos(ID_COLABORADORES, f"{mes_m}{anio_global[-2:]}")
        if not df_m.empty:
            df_m_f = df_m[df_m['Razón Social'] == st.session_state["user_empresa"]] if rol == "USUARIO" else df_m
            m1, m2, m3 = st.columns(3)
            # AQUÍ ESTABA EL ERROR: Líneas corregidas y completas
            m1.metric("Dotación", len(df_m_f))
            if 'Nacionalidad' in df_m_f.columns:
                ext = len(df_m_f[~df_m_f['Nacionalidad'].str.contains('Chile', na=False)])
                m2.metric("Extranjeros", ext)
            if 'Total Horas Extra' in df_m_f.columns:
                hhex = pd.to_numeric(df_m_f['Total Horas Extra'], errors='coerce').sum()
                m3.metric("HH.EE Mes", f"{hhex:,.0f}")
            st.dataframe(df_m_f, use_container_width=True)

# --- PESTAÑA 4: ADMIN ---
if rol == "ADMIN":
    with tabs[3]:
        if st.session_state["log_accesos"]: st.table(pd.DataFrame(st.session_state["log_accesos"]))
        st.dataframe(cargar_datos(ID_USUARIOS, "Usuarios"), use_container_width=True)

st.caption("C & S Asociados Ltda. - Control Laboral CMSG")