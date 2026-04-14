import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import re

# 1. CONFIGURACIÓN DE PANTALLA Y CONSTANTES
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")

# --- CONEXIÓN DRIVE (Tu llave maestra) ---
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbxbH7GCm95Eh0DMkBCNVD9Ce-lywoCqmUC_DraHw7DopQPeIOJ5XamcqHvf0dyBFtw/exec"

# IDs DE GOOGLE SHEETS
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"

# MAPAS DE CONFIGURACIÓN
MAPA_ESTADOS = {1:"Carga Doc.", 2:"En Revision", 3:"Observado", 4:"No Cumple", 5:"Cumple", 8:"Sin Info", 9:"No Corresp."}
COLORES_ESTADOS = {"Carga Doc.":"#FF8C00", "En Revision":"#1E90FF", "Observado":"#FFFF00", "No Cumple":"#FF0000", "Cumple":"#00FF00", "Sin Info":"#555555", "No Corresp.":"#8B4513"}
MAPA_MESES = {'ENE':'01','FEB':'02','MAR':'03','ABR':'04','MAY':'05','JUN':'06','JUL':'07','AGO':'08','SEP':'09','OCT':'10','NOV':'11','DIC':'12'}

if "log_accesos" not in st.session_state:
    st.session_state["log_accesos"] = []

@st.cache_data(ttl=30)
def cargar_datos(sheet_id, nombre_pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
        df = pd.read_csv(url, encoding='utf-8-sig')
        # Normalización de columnas para evitar KeyErrors
        df.columns = [re.sub(r'[^A-Z0-9]', '', str(c).upper()) for c in df.columns]
        return df.dropna(how='all')
    except: return pd.DataFrame()

# --- 2. SISTEMA DE LOGIN ---
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
                st.session_state["log_accesos"].append({
                    "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Usuario": u.get('NOMBRE',''),
                    "Empresa": u.get('EMPRESA','')
                })
                st.session_state.update({
                    "authenticated": True, 
                    "u_nom": u.get('NOMBRE',''), 
                    "u_rol": u.get('ROL',''), 
                    "u_emp": u.get('EMPRESA','')
                })
                st.rerun()
            else: st.error("❌ Clave no válida.")
    st.stop()

# --- 3. BARRA LATERAL ---
with st.sidebar:
    st.image("https://cysasociados.cl/wp-content/uploads/2022/05/logo-cys.png", width=150)
    st.write(f"👤 **{st.session_state['u_nom']}**")
    st.caption(f"Rol: {st.session_state['u_rol']}")
    anio_global = st.selectbox("Año de Análisis", ["2026", "2025"])
    if st.button("Cerrar Sesión"):
        del st.session_state["authenticated"]
        st.rerun()

# --- PESTAÑAS SEGÚN ROL ---
rol = st.session_state["u_rol"]
if rol == "ADMIN":
    tabs = st.tabs(["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Colaboradores", "⚙️ Administración"])
elif rol == "REVISOR":
    tabs = st.tabs(["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Colaboradores"])
else: # USUARIO
    tabs = st.tabs(["📈 Mi Avance", "👥 Masa Laboral"])

# --- TAB 1: CUMPLIMIENTO ---
with tabs[0]:
    df_av = cargar_datos(ID_AVANCE, anio_global)
    df_id = cargar_datos(ID_EMPRESAS, "HOJA1")
    
    if not df_av.empty:
        col_e = next((c for c in df_av.columns if 'EMP' in c), df_av.columns[0])
        df_f = df_av[df_av[col_e] == st.session_state["u_emp"]] if rol == "USUARIO" else df_av
        cols_m = [c for c in df_f.columns if c in MAPA_MESES.keys()]
        df_num = df_f[cols_m].apply(pd.to_numeric, errors='coerce')

        st.header(f"Gestión de Auditoría - {anio_global}")
        
        # --- LÍNEA 1: KPIs MAESTROS ---
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas en Panel", len(df_f))
        
        total_p = df_num.isin([1,2,3,4,5]).sum().sum()
        total_5 = (df_num == 5).sum().sum()
        k2.metric("% Cumplimiento Global", f"{(total_5/total_p*100 if total_p > 0 else 0):.1f}%")
        
        al_dia = ((df_num == 5).any(axis=1) & ~(df_num.isin([1,2,3,4]).any(axis=1))).sum()
        k3.metric("Empresas al Día (100%)", al_dia)

        # --- LÍNEA 2: CONTEO POR ESTADOS ---
        st.write("### 📊 Resumen de Periodos por Estado")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("✅ Cumple", int((df_num == 5).sum().sum()))
        c2.metric("🔵 En Revisión", int((df_num == 2).sum().sum()))
        c3.metric("🟠 Carga Doc.", int((df_num == 1).sum().sum()))
        c4.metric("🟡 Observado", int((df_num == 3).sum().sum()))
        
        c5, c6, c7, _ = st.columns(4)
        c5.metric("🔴 No Cumple", int((df_num == 4).sum().sum()))
        c6.metric("⚪ Sin Info", int((df_num == 8).sum().sum()))
        c7.metric("🟤 No Corresp.", int((df_num == 9).sum().sum()))

        # --- GRÁFICO DE BARRAS DE EVOLUCIÓN ---
        st.divider()
        st.subheader("📈 Evolución Mensual del Cumplimiento")
        res_evo = []
        for m in cols_m:
            counts = df_f[m].value_counts()
            for cod, cant in counts.items():
                if pd.notna(cod):
                    res_evo.append({'Mes': m, 'Estado': MAPA_ESTADOS.get(int(cod), "S/I"), 'Cantidad': cant})
        if res_evo:
            st.plotly_chart(px.bar(pd.DataFrame(res_evo), x='Mes', y='Cantidad', color='Estado', 
                                   color_discrete_map=COLORES_ESTADOS, barmode='stack'), use_container_width=True)

        # --- DETALLE INDIVIDUAL Y DESCARGAS ---
        st.divider()
        st.subheader("🎯 Detalle por Empresa y Descarga de Certificados")
        emp_sel = st.selectbox("Seleccione Empresa para visualizar:", sorted(df_f[col_e].unique()))
        row = df_f[df_f[col_e] == emp_sel].iloc[0]
        
        col_d, col_p = st.columns(2)
        with col_d:
            st.info(f"Empresa: **{emp_sel}**")
            mes_sel = st.selectbox("Seleccione Mes para el PDF:", cols_m)
            if st.button(f"🚀 Obtener Certificado {mes_sel}"):
                col_id_e = next((c for c in df_id.columns if 'EMP' in c), 'EMPRESA')
                col_id_f = next((c for c in df_id.columns if 'ID' in c or 'CARPETA' in c), 'IDCARPETA')
                match = df_id[df_id[col_id_e].str.contains(emp_sel[:15], case=False, na=False)]
                if not match.empty:
                    id_f = str(match.iloc[0][col_id_f]).strip()
                    nombre_f = f"Certificado.{MAPA_MESES[mes_sel]}{anio_global}.pdf"
                    r = requests.get(URL_APPS_SCRIPT, params={"nombre": nombre_f, "carpeta": id_f})
                    if r.text.startswith("http"):
                        st.success("✅ Documento Localizado")
                        st.link_button("📥 Descargar Certificado", r.text.strip())
                    else: st.error("No disponible en Drive.")
                else: st.error("Empresa sin ID de carpeta configurado.")

        with col_p:
            pie_list = [{'Estado': MAPA_ESTADOS.get(int(row[m]), "S/I")} for m in cols_m if pd.notna(row[m])]
            st.plotly_chart(px.pie(pd.DataFrame(pie_list), names='Estado', hole=.4, 
                                  color_discrete_map=COLORES_ESTADOS, title=f"Estado Anual: {emp_sel}"), use_container_width=True)

# --- OTRAS PESTAÑAS (KPIs, MASA, ADMIN) ---
if rol != "USUARIO" and "KPIs Empresas" in str(tabs):
    with tabs[1]:
        st.header("🏢 KPIs Nivel Empresa")
        st.dataframe(cargar_datos(ID_EMPRESAS, "HOJA1"), use_container_width=True)

idx_masa = 1 if rol == "USUARIO" else 2
with tabs[idx_masa]:
    st.header(f"Análisis de Dotación - {anio_global}")
    mes_m = st.selectbox("Mes Masa:", list(MAPA_MESES.keys()))
    df_m = cargar_datos(ID_COLABORADORES, f"{mes_m.capitalize()}{anio_global[-2:]}")
    if not df_m.empty:
        col_rs = next((c for c in df_m.columns if 'RAZON' in c), df_m.columns[0])
        df_mf = df_m[df_m[col_rs] == st.session_state["u_emp"]] if rol == "USUARIO" else df_m
        m1, m2, m3 = st.columns(3)
        m1.metric("Dotación", len(df_mf))
        if 'NACIONALIDAD' in df_mf.columns:
            ext = len(df_mf[~df_mf['NACIONALIDAD'].str.contains('CHILE', na=False)])
            m2.metric("Extranjeros", ext)
        if 'TOTALHORASEXTRA' in df_mf.columns:
            m3.metric("HH.EE Mes", f"{pd.to_numeric(df_mf['TOTALHORASEXTRA'], errors='coerce').sum():,.0f}")
        st.dataframe(df_mf, use_container_width=True)

if rol == "ADMIN":
    with tabs[3]:
        st.subheader("📅 Log de Accesos")
        st.table(pd.DataFrame(st.session_state["log_accesos"]))
        st.subheader("👥 Usuarios del Sistema")
        st.dataframe(cargar_datos(ID_USUARIOS, "Usuarios"))

# --- PIE DE PÁGINA ---
st.markdown("---")
st.caption("Sistema de gestión de datos, desarrollado por C & S Asociados Ltda. para Control Laboral CMSG")