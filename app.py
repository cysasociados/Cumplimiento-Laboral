Entiendo perfectamente, Sergio. A veces es mejor dar un paso atrás, pisar tierra firme sobre un código que ya conoces y, desde ahí, construir con cuidado. Vamos a trabajar sobre la base que me pasaste para solucionar los dos puntos críticos: el cálculo real de cumplimiento y la descarga de archivos, asegurando que el diseño sea el que pediste.

Aquí tienes el código actualizado con estas correcciones específicas:

🚀 app.py: Versión Corregida (Base Sólida + Mejoras de Visualización)
Python
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import re
import os

# 1. CONFIGURACIÓN DE PANTALLA
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")

# --- CABECERA INSTITUCIONAL (LOGOS) ---
col_logo_l, col_espacio, col_logo_r = st.columns([2, 4, 1])
with col_logo_l:
    if os.path.exists("CMSG.png"): st.image("CMSG.png", width=250)
    else: st.subheader("🏢 Minera San Gerónimo")
with col_logo_r:
    if os.path.exists("cys.png"): st.image("cys.png", width=120)
    else: st.write("**C&S Asociados**")

# --- CONFIGURACIÓN DE CONEXIÓN ---
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbxbH7GCm95Eh0DMkBCNVD9Ce-lywoCqmUC_DraHw7DopQPeIOJ5XamcqHvf0dyBFtw/exec"

ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"

MAPA_ESTADOS = {1:"Carga Doc.", 2:"En Revision", 3:"Observado", 4:"No Cumple", 5:"Cumple", 8:"Sin Info", 9:"No Corresp."}
COLORES_ESTADOS = {"Carga Doc.":"#FF8C00", "En Revision":"#1E90FF", "Observado":"#FFFF00", "No Cumple":"#FF0000", "Cumple":"#00FF00", "Sin Info":"#555555", "No Corresp.":"#8B4513"}
MAPA_MESES = {'ENE':'01','FEB':'02','MAR':'03','ABR':'04','MAY':'05','JUN':'06','JUL':'07','AGO':'08','SEP':'09','OCT':'10','NOV':'11','DIC':'12'}

if "log_accesos" not in st.session_state:
    st.session_state["log_accesos"] = []

@st.cache_data(ttl=15)
def cargar_datos(sheet_id, nombre_pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
        df = pd.read_csv(url, encoding='utf-8-sig')
        df.columns = [re.sub(r'[^A-Z0-9]', '', str(c).upper()) for c in df.columns]
        return df.dropna(how='all')
    except: return pd.DataFrame()

# --- 2. LOGIN ---
if "authenticated" not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 Acceso Control Laboral CMSG")
        pwd = st.text_input("Contraseña:", type="password").strip()
        if st.button("Ingresar", use_container_width=True):
            df_u = cargar_datos(ID_USUARIOS, "Usuarios")
            col_c = next((c for c in df_u.columns if 'CLAVE' in c), 'CLAVE')
            match = df_u[df_u[col_c].astype(str).str.strip() == pwd]
            if not match.empty:
                u = match.iloc[0]
                st.session_state.update({"authenticated": True, "u_nom": u.get('NOMBRE',''), "u_rol": u.get('ROL',''), "u_emp": u.get('EMPRESA','')})
                st.rerun()
            else: st.error("❌ Clave no válida.")
    st.stop()

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuración")
    anio_global = st.selectbox("Año de Análisis", ["2026", "2025"])
    df_av = cargar_datos(ID_AVANCE, anio_global)
    cols_m_sidebar = [c for c in df_av.columns if c in MAPA_MESES.keys()] if not df_av.empty else []
    mes_sidebar = st.selectbox("Mes de Análisis", ["AÑO COMPLETO"] + cols_m_sidebar)
    st.divider()
    st.write(f"👤 **{st.session_state['u_nom']}**")
    if st.button("Cerrar Sesión"):
        del st.session_state["authenticated"]
        st.rerun()

# --- 4. TABS ---
rol = st.session_state["u_rol"]
if rol == "ADMIN": tabs = st.tabs(["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Colaboradores", "⚙️ Administración"])
elif rol == "REVISOR": tabs = st.tabs(["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Colaboradores"])
else: tabs = st.tabs(["📈 Mi Avance", "👥 Masa Laboral"])

# --- TAB 1: AVANCE LABORAL ---
with tabs[0]:
    df_id = cargar_datos(ID_EMPRESAS, "HOJA1")
    if not df_av.empty:
        col_e = next((c for c in df_av.columns if 'EMP' in c), df_av.columns[0])
        df_f = df_av[df_av[col_e] == st.session_state["u_emp"]] if rol == "USUARIO" else df_av
        cols_filtro = [mes_sidebar] if mes_sidebar != "AÑO COMPLETO" else cols_m_sidebar
        df_num = df_f[cols_filtro].apply(pd.to_numeric, errors='coerce')

        # --- CÁLCULO DE CUMPLIMIENTO REAL (EXCLUYENDO ESTADO 9) ---
        # Definimos el universo de meses que SI deben informar (1, 2, 3, 4, 5, 8)
        df_auditables = df_num[df_num.isin([1, 2, 3, 4, 5, 8])]
        total_periodos = df_auditables.count().sum() # .count() ignora NaNs (meses con 9)
        total_cumple = (df_auditables == 5).sum().sum()
        cumplimiento_final = (total_cumple / total_periodos * 100) if total_periodos > 0 else 0

        st.header(f"Gestión de Control Laboral CMSG - {mes_sidebar} {anio_global}")
        
        # KPIs
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas en Panel", len(df_f))
        k2.metric("% Cumplimiento Global", f"{cumplimiento_final:.1f}%", help="No considera los estados 'No Corresponde Informar'")
        al_dia = ((df_auditables == 5).all(axis=1) if mes_sidebar == "AÑO COMPLETO" else (df_auditables == 5).sum(axis=1) > 0).sum()
        k3.metric("Empresas al Día (100%)", int(al_dia))

        # Recuento de Estados
        st.write("### 📊 Resumen de Estados por Periodo")
        st_cols = st.columns(len(MAPA_ESTADOS))
        for i, (code, name) in enumerate(MAPA_ESTADOS.items()):
            cant = int((df_num == code).sum().sum())
            st_cols[i].metric(name, cant)

        st.divider()
        st.subheader("🎯 Detalle por Empresa y Certificados")
        emp_sel = st.selectbox("Seleccione Empresa para visualizar:", sorted(df_f[col_e].unique()))
        row_sel = df_f[df_f[col_e] == emp_sel].iloc[0]
        
        col_desc, col_grafico = st.columns([1, 2])
        
        with col_desc:
            st.info(f"Empresa: **{emp_sel}**")
            mes_pdf = st.selectbox("Mes para el PDF:", cols_m_sidebar)
            if st.button(f"🔍 Buscar Certificado {mes_pdf}"):
                col_id_e = next((c for c in df_id.columns if 'EMP' in c), 'EMPRESA')
                col_id_f = next((c for c in df_id.columns if 'ID' in c or 'CARPETA' in c), 'IDCARPETA')
                match = df_id[df_id[col_id_e].str.contains(emp_sel[:10], case=False, na=False)]
                if not match.empty:
                    id_f = str(match.iloc[0][col_id_f]).strip()
                    nombre_f = f"Certificado.{MAPA_MESES[mes_pdf]}{anio_global}.pdf"
                    with st.spinner("Conectando con Drive..."):
                        r = requests.get(URL_APPS_SCRIPT, params={"nombre": nombre_f, "carpeta": id_f})
                        if r.text.startswith("http"):
                            st.success("✅ Encontrado")
                            st.link_button("📥 Descargar Certificado", r.text.strip())
                        else: st.error("No disponible en Drive.")
                else: st.error("ID de carpeta no configurado para esta empresa.")

        with col_grafico:
            # Gráfico de Torta
            pie_data = [{'Estado': MAPA_ESTADOS.get(int(row_sel[m]), "S/I")} for m in cols_m_sidebar if pd.notna(row_sel[m])]
            st.plotly_chart(px.pie(pd.DataFrame(pie_data), names='Estado', hole=.4, 
                                  color_discrete_map=COLORES_ESTADOS, title=f"Distribución Anual: {emp_sel}"), use_container_width=True)
            
            # TABLA DE HISTORIAL BAJO EL GRÁFICO (Lo solicitado)
            st.write("#### 📜 Historial Mensual")
            hist_view = df_f[df_f[col_e] == emp_sel][cols_m_sidebar].T.reset_index()
            hist_view.columns = ['Mes', 'Cod_Estado']
            hist_view['Estado'] = hist_view['Cod_Estado'].map(MAPA_ESTADOS)
            st.dataframe(hist_view[['Mes', 'Estado']], use_container_width=True)

# --- TAB: MASA COLABORADORES (CON ALERTAS) ---
idx_masa = 1 if rol == "USUARIO" else 2
with tabs[idx_masa]:
    st.header(f"Análisis de Dotación - {anio_global}")
    mes_m = st.selectbox("Filtrar Mes Masa:", list(MAPA_MESES.keys()))
    df_masa = cargar_datos(ID_COLABORADORES, f"{mes_m.capitalize()}{anio_global[-2:]}")
    if not df_masa.empty:
        col_rs = next((c for c in df_masa.columns if 'RAZON' in c), df_masa.columns[0])
        df_mf = df_masa[df_masa[col_rs] == st.session_state["u_emp"]] if rol == "USUARIO" else df_masa
        
        st.subheader("🚨 Alertas de Estabilidad")
        col_contrato = next((c for c in df_mf.columns if 'CONTRATO' in c), None)
        if col_contrato:
            plazo_f = df_mf[df_mf[col_contrato].str.contains("PLAZO FIJO", case=False, na=False)]
            if not plazo_f.empty:
                st.warning(f"Se detectaron {len(pf)} contratos a Plazo Fijo.")
                st.dataframe(pf, use_container_width=True)
            else: st.success("✅ Todo el personal analizado tiene contrato Indefinido.")

        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("Dotación Total", len(df_mf))
        if 'NACIONALIDAD' in df_mf.columns:
            ext = len(df_mf[~df_mf['NACIONALIDAD'].str.contains('CHILE', na=False)])
            m2.metric("Extranjeros", ext)
        if 'TOTALHORASEXTRA' in df_mf.columns:
            hhex = pd.to_numeric(df_mf['TOTALHORASEXTRA'], errors='coerce').sum()
            m3.metric("HH.EE Mes", f"{hhex:,.0f}")
        st.dataframe(df_mf, use_container_width=True)

st.markdown("---")
st.caption("CMSG | C&S Asociados Ltda.")