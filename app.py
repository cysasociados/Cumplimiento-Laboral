import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import base64
import re
import os
from datetime import datetime
import pytz

# 1. CONFIGURACION
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="S")
chile_tz = pytz.timezone('America/Santiago')

# CONEXION (USA TU URL)
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycby3NSTypKAzcpJpdAsZyWYWYiDq4uZ9jbGwJc5GwcM1SeyMIIrTlnDnrZEfpaXIevzzdw/exec"
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"

MAPA_ESTADOS = {1:"Carga Doc.", 2:"En Revision", 3:"Observado", 4:"No Cumple", 5:"Cumple", 8:"Sin Info", 9:"No Corresp."}
COLORES_ESTADOS = {"Cumple":"#00FF00", "No Cumple":"#FF0000", "Observado":"#FFFF00", "En Revision":"#1E90FF", "Carga Doc.":"#FF8C00", "Sin Info":"#555555", "No Corresp.":"#8B4513"}
MESES_STD = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC']

@st.cache_data(ttl=15)
def cargar_datos(sheet_id, p):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={p}"
        df = pd.read_csv(url, encoding='utf-8-sig')
        df.columns = [re.sub(r'[^A-Z0-9]', '', str(c).upper()) for c in df.columns]
        return df.dropna(how='all')
    except: return pd.DataFrame()

# LOGIN
if "authenticated" not in st.session_state:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.title("Acceso CMSG")
        pwd = st.text_input("Contrasena:", type="password").strip()
        if st.button("Ingresar", use_container_width=True):
            df_u = cargar_datos(ID_USUARIOS, "Usuarios")
            if not df_u.empty:
                col_c = next((c for c in df_u.columns if 'CLAVE' in str(c).upper()), 'CLAVE')
                match = df_u[df_u[col_c].astype(str).str.strip() == pwd]
                if not match.empty:
                    u = match.iloc[0]
                    email_u = str(u.get('EMAIL')).strip() if pd.notna(u.get('EMAIL')) else 'cumplimiento@cysasociados.cl'
                    st.session_state.update({"authenticated": True, "u_nom": u.get('NOMBRE',''), "u_rol": u.get('ROL',''), "u_emp": u.get('EMPRESA',''), "u_email": email_u})
                    st.rerun()
                else: st.error("Clave incorrecta")
    st.stop()

# SIDEBAR
with st.sidebar:
    anio_global = st.selectbox("Anio", ["2026", "2025"])
    df_av = cargar_datos(ID_AVANCE, anio_global)
    cols_m = [c for c in df_av.columns if c in MESES_STD] if not df_av.empty else []
    mes_sidebar = st.selectbox("Mes", ["AÑO COMPLETO"] + cols_m)
    st.write(f"Usuario: {st.session_state['u_nom']}")
    if st.button("Cerrar Sesion"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# TABS
rol = st.session_state["u_rol"]
if rol == "USUARIO": t_list = ["Dashboard", "Dotacion", "Carga"]
else: t_list = ["Dashboard", "Empresas", "Dotacion", "Carga", "Admin"]
tabs = st.tabs(t_list)

# TAB 1
with tabs[0]:
    df_id_f = cargar_datos(ID_EMPRESAS, "HOJA1")
    if not df_av.empty:
        col_e = next((c for c in df_av.columns if 'EMP' in str(c).upper()), 'EMPRESA')
        df_f = df_av[df_av[col_e] == st.session_state["u_emp"]] if rol == "USUARIO" else df_av
        c_filt = [mes_sidebar] if mes_sidebar != "AÑO COMPLETO" else cols_m
        df_num = df_f[c_filt].apply(pd.to_numeric, errors='coerce')

        # CALCULO SIN ESTADO 9
        df_audit = df_num.copy()
        df_audit[df_audit == 9] = pd.NA
        perc = (df_audit == 5).sum().sum() / df_audit.count().sum() * 100 if df_audit.count().sum() > 0 else 0
        
        st.header(f"Control Laboral {mes_sidebar}")
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas", len(df_f))
        k2.metric("% Cumplimiento", f"{perc:.1f}%")
        
        al_dia = df_audit.apply(lambda x: x.dropna().eq(5).all() if x.dropna().size > 0 else False, axis=1).sum()
        k3.metric("Empresas al Dia", int(al_dia))

        # CONTADORES
        st.write("### Estados")
        st_c = df_num.stack().value_counts()
        m_c = st.columns(len(MAPA_ESTADOS))
        for i, (cod, nom) in enumerate(MAPA_ESTADOS.items()):
            m_c[i].metric(nom, int(st_c.get(cod, 0)))

        # GRAFICO BARRAS
        if mes_sidebar