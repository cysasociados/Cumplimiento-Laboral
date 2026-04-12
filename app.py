import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests

# 1. CONFIGURACIÓN Y LLAVE MAESTRA
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")

# URL DE TU CAPTURA DE PANTALLA
URL_MI_SCRIPT = "https://script.google.com/a/macros/cysasociados.cl/s/AKfycbwi-UFcqZPZFmvA_80Naul4hHoJJAgUd8htMkJUmCpnGs_BAweZVOFFzclWQczMQXbq/exec"

if "log_accesos" not in st.session_state:
    st.session_state["log_accesos"] = []

# IDs de Google Sheets
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

# --- 2. LOGIN ---
def check_password():
    if "authenticated" not in st.session_state:
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.title("🔐 Acceso Control Laboral")
            pwd_input = st.text_input("Contraseña:", type="password").strip()
            if st.button("Ingresar"):
                df_u = cargar_datos(ID_USUARIOS, "Usuarios")
                if not df_u.empty:
                    df_u['Clave'] = df_u['Clave'].astype(str).str.strip()
                    user_match = df_u[df_u['Clave'] == pwd_input]
                    if not user_match.empty:
                        info = user_match.iloc[0]
                        st.session_state["log_accesos"].append({
                            "Fecha": datetime.now().strftime("%d/%m/%Y"),
                            "Hora": datetime.now().strftime("%H:%M:%S"),
                            "Usuario": info['Nombre'], "Empresa": info['Empresa']
                        })
                        st.session_state["authenticated"] = True
                        st.session_state["user_nombre"] = info['Nombre']
                        st.session_state["user_rol"] = info['Rol']
                        st.session_state["user_empresa"] = info['Empresa']
                        st.rerun()
                    else: st.error("❌ Clave no válida.")
        return False
    return True

if not check_password():
    st.stop()

# --- 3. DISEÑO ---
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

rol = st.session_state["user_rol"]
if rol == "ADMIN":
    tabs = st.tabs(["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Colaboradores", "⚙️ Administración"])
elif rol == "REVISOR":
    tabs = st.tabs(["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Colaboradores"])
else:
    tabs = st.tabs(["📈 Mi Avance", "👥 Masa Laboral"])

# --- TAB 1: CUMPLIMIENTO ---
with tabs[0]:
    df_av = cargar_datos(ID_AVANCE, anio_global)
    df_eecc = cargar_datos(ID_EMPRESAS, "Hoja 1")
    
    if not df_av.empty:
        df_f = df_av[df_av['Empresa'] == st.session_state["user_empresa"]] if rol == "USUARIO" else df_av
        
        meses_abrev = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic']
        dic_mm = {m: str(i+1).zfill(2) for i, m in enumerate(meses_abrev)}
        cols_activos = [c for c in meses_abrev if c in df_f.columns]
        
        with st.sidebar:
            st.divider()
            mes_sel = st.selectbox("Mes Filtro:", ["AÑO COMPLETO"] + cols_activos)

        st.header(f"Gestión de Cumplimiento")
        emp_v = st.selectbox("Seleccione Empresa:", sorted(df_f["Empresa"].unique())) if rol != "USUARIO" else st.session_state["user_empresa"]
        row_emp = df_f[df_f["Empresa"] == emp_v].iloc[0]

        # HALLAZGOS Y BUSCADOR
        st.divider()
        c_obs, c_cert = st.columns([2, 1])
        with c_obs:
            st.subheader(f"📝 Hallazgos ({mes_sel})")
            obs = row_emp["Obs Auditoria"] if "Obs Auditoria" in row_emp else ""
            if pd.notna(obs) and str(obs).strip() != "": st.warning(obs)
            else: st.success("✅ Sin observaciones pendientes.")

        with c_cert:
            st.subheader("📄 Certificado")
            if mes_sel != "AÑO COMPLETO":
                try:
                    id_carpeta = df_eecc[df_eecc['Empresa'] == emp_v]['ID_Carpeta'].iloc[0]
                    mm = dic_mm.get(mes_sel.lower())
                    nombre_pdf = f"Certificado.{mm}{anio_global}"
                    if st.button(f"🔍 Buscar PDF {mes_sel}"):
                        with st.spinner("Buscando..."):
                            res = requests.get(f"{URL_MI_SCRIPT}?nombre={nombre_pdf}&carpeta={id_carpeta}")
                            if "http" in res.text: st.link_button("📥 Descargar", res.text)
                            else: st.error("No encontrado. Revise nombre en Drive.")
                except: st.error("Falta ID_Carpeta en Base Empresas.")
            else: st.info("Elija un mes para descargar.")

        st.divider()
        # GRÁFICOS (Escudo anti-NaN)
        mapa_e = {1:"Carga Doc.", 2:"En Revision", 3:"Observado", 4:"No Cumple", 5:"Cumple", 8:"Sin Info", 9:"No Corresp."}
        colores = {"Carga Doc.":"#FF8C00", "En Revision":"#1E90FF", "Observado":"#FFFF00", "No Cumple":"#FF0000", "Cumple":"#00FF00", "Sin Info":"#555555", "No Corresp.":"#8B4513"}
        
        cols_g = [mes_sel] if mes_sel != "AÑO COMPLETO" else cols_activos
        df_p = pd.DataFrame([{'Mes': m.upper(), 'Estado': mapa_e.get(int(row_emp[m]), "Sin Datos") if pd.notna(row_emp[m]) else "Sin Datos"} for m in cols_g])
        st.plotly_chart(px.pie(df_p, names='Estado', hole=.4, color='Estado', color_discrete_map=colores), use_container_width=True)
        st.table(df_p.set_index('Mes').T)

# --- TAB 2: BASE EMPRESAS ---
if rol != "USUARIO":
    with tabs[1]:
        st.header("🏢 Base Maestra")
        st.dataframe(df_eecc, use_container_width=True)

# --- TAB 3: MASA LABORAL ---
idx_m = 1 if rol == "USUARIO" else 2
with tabs[idx_m]:
    if anio_global == "2025": st.warning("Sin datos 2025.")
    else:
        st.header("👥 Masa Colaboradores")
        mes_m = st.sidebar.selectbox("Mes Masa:", ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"])
        df_s = cargar_datos(ID_COLABORADORES, f"{mes_m}{anio_global[-2:]}")
        if not df_s.empty:
            df_f_m = df_s[df_s['Razón Social'] == st.session_state["user_empresa"]] if rol == "USUARIO" else df_s
            st.metric("Dotación", len(df_f_m))
            st.plotly_chart(px.pie(df_f_m, names='Genero', title="Género"), use_container_width=True)

# --- TAB 4: ADMIN ---
if rol == "ADMIN":
    with tabs[3]:
        st.header("⚙️ Administración")
        st.subheader("📅 Log de Accesos")
        if st.session_state["log_accesos"]: st.table(pd.DataFrame(st.session_state["log_accesos"]))
        st.subheader("👥 Usuarios")
        st.dataframe(cargar_datos(ID_USUARIOS, "Usuarios"), use_container_width=True)

# Pie de página
st.markdown("---")
st.caption("Sistema de gestión de datos en tiempo real, desarrollado por C & S Asociados Ltda. para Control Laboral CMSG")