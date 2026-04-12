import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. CONFIGURACIÓN DE PANTALLA
st.set_page_config(page_title="Portal de Gestión CyS - CMSG", layout="wide", page_icon="🛡️")

# Log de accesos en memoria
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

# --- SISTEMA DE LOGIN ---
def check_password():
    if "authenticated" not in st.session_state:
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.title("🔐 Acceso a Control Laboral CMSG")
            pwd_input = st.text_input("Contraseña:", type="password").strip()
            if st.button("Ingresar"):
                df_u = cargar_datos(ID_USUARIOS, "Usuarios")
                if not df_u.empty:
                    df_u['Clave'] = df_u['Clave'].astype(str).str.strip()
                    user_match = df_u[df_u['Clave'] == pwd_input]
                    if not user_match.empty:
                        info = user_match.iloc[0]
                        # Log de entrada
                        st.session_state["log_accesos"].append({
                            "Usuario": info['Nombre'],
                            "Hora": datetime.now().strftime("%H:%M:%S"),
                            "Empresa": info['Empresa']
                        })
                        st.session_state["authenticated"] = True
                        st.session_state["user_nombre"] = info['Nombre']
                        st.session_state["user_rol"] = info['Rol']
                        st.session_state["user_empresa"] = info['Empresa']
                        st.rerun()
                    else:
                        st.error("❌ Clave no válida.")
        return False
    return True

if not check_password():
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cysasociados.cl/wp-content/uploads/2022/05/logo-cys.png", width=150)
    st.markdown(f"👤 **{st.session_state['user_nombre']}**")
    st.caption(f"Acceso: {st.session_state['user_rol']}")
    st.divider()
    anio_global = st.selectbox("Año de Análisis", ["2025", "2026", "2027"])
    if st.button("Cerrar Sesión"):
        del st.session_state["authenticated"]
        st.rerun()

# --- LÓGICA DE PESTAÑAS EXCLUSIVAS ---
rol = st.session_state["user_rol"]
nombre = st.session_state["user_nombre"]

if rol == "USUARIO":
    tabs = st.tabs(["📈 Mi Cumplimiento", "👥 Masa Laboral"])
elif rol == "REVISOR":
    tabs = st.tabs(["📈 Avance Laboral", "🏢 KPIs Empresa", "👥 Masa Laboral"])
else: # ADMIN (Sergio)
    tabs = st.tabs(["📈 Avance Laboral", "🏢 KPIs Empresa", "👥 Masa Laboral", "⚙️ Administración"])

# --- TAB 1: CUMPLIMIENTO (Para todos) ---
with tabs[0]:
    df_av = cargar_datos(ID_AVANCE, anio_global)
    if not df_av.empty:
        df_f = df_av[df_av['Empresa'] == st.session_state["user_empresa"]] if rol == "USUARIO" else df_av
        
        # Matemática de Cumplimiento (Excluyendo 9)
        cols_m = [c for c in ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'] if c in df_f.columns]
        with st.sidebar:
            mes_sel = st.selectbox("Mes Filtro:", ["AÑO COMPLETO"] + cols_m)
        
        cols_f = [mes_sel] if mes_sel != "AÑO COMPLETO" else cols_m
        datos = df_f[cols_f]
        
        # KPIs
        t_real = datos.isin([1,2,3,4,5]).sum().sum()
        t_cumple = (datos == 5).sum().sum()
        porc = (t_cumple/t_real*100) if t_real > 0 else 0
        
        st.header(f"Gestión Laboral - {anio_global}")
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas", len(df_f))
        k2.metric("% Cumplimiento", f"{porc:.1f}%")
        k3.metric("Al Día", ( ( (datos==5).any(axis=1) ) & ~(datos.isin([1,2,3,4]).any(axis=1)) ).sum() )
        
        st.divider()
        emp_v = st.selectbox("Detalle Empresa:", sorted(df_f["Empresa"].unique())) if rol != "USUARIO" else st.session_state["user_empresa"]
        row = df_f[df_f["Empresa"] == emp_v][cols_f].iloc[0]
        df_p = pd.DataFrame([{'Mes': m.upper(), 'Estado': str(c)} for m, c in row.items()])
        st.plotly_chart(px.pie(df_p, names='Estado', hole=.4, title=f"Estado: {emp_v}"), use_container_width=True)
        st.table(df_p.set_index('Mes').T)

# --- TAB 2: KPIs EMPRESA (Revisor y Admin) ---
if rol != "USUARIO":
    with tabs[1]:
        st.header("🏢 KPIs Nivel Empresa")
        st.dataframe(cargar_datos(ID_EMPRESAS, "Hoja 1"), use_container_width=True)

# --- TAB 3: MASA LABORAL (Para todos, pero con orden distinto) ---
t_masa = tabs[1] if rol == "USUARIO" else tabs[2]
with t_masa:
    if anio_global == "2025":
        st.warning("⚠️ Datos no disponibles para 2025.")
    else:
        st.header("👥 Análisis de Colaboradores")
        df_staff = cargar_datos(ID_COLABORADORES, "Ene26") # Ejemplo carga
        if not df_staff.empty:
            df_f = df_staff[df_staff['Razón Social'] == st.session_state["user_empresa"]] if rol == "USUARIO" else df_staff
            
            # Alerta Plazo Fijo
            pf = df_f[df_f['Tipo Contrato'].str.contains("Plazo Fijo", na=False)]
            if not pf.empty:
                st.warning(f"🚨 Se detectaron {len(pf)} contratos a Plazo Fijo.")
                st.dataframe(pf[['Razón Social', 'Rut Trabajador', 'Nombres', 'Tipo Contrato']], use_container_width=True)
            
            st.plotly_chart(px.pie(df_f, names='Genero', title="Género"), use_container_width=True)

# --- TAB 4: ADMINISTRACIÓN (SOLO SERGIO / ADMIN) ---
if rol == "ADMIN":
    with tabs[3]:
        st.header("⚙️ Panel Privado de Administración")
        st.subheader("📅 Log de Accesos del Día")
        if st.session_state["log_accesos"]:
            st.table(pd.DataFrame(st.session_state["log_accesos"]))
        
        st.divider()
        st.subheader("👥 Gestión de Usuarios Autorizados")
        st.dataframe(cargar_datos(ID_USUARIOS, "Usuarios"), use_container_width=True)

# Pie de página
st.markdown("---")
st.caption("Sistema de gestión de datos en tiempo real, desarrollado por C & S Asociados Ltda. para Control Laboral CMSG")