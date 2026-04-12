import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. CONFIGURACIÓN DE PANTALLA
st.set_page_config(page_title="Portal de Gestión CyS", layout="wide", page_icon="🛡️")

# Inicializar el log de accesos en la memoria del sistema
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
        return df
    except:
        return pd.DataFrame()

# --- LOGIN CON REGISTRO DE ACCESO ---
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
                        # NUEVO: Guardar el acceso en el Log
                        nombre = user_match.iloc[0]['Nombre']
                        hora = datetime.now().strftime("%H:%M:%S")
                        st.session_state["log_accesos"].append({"Usuario": nombre, "Hora": hora, "Rol": user_match.iloc[0]['Rol']})
                        
                        st.session_state["authenticated"] = True
                        st.session_state["user_nombre"] = nombre
                        st.session_state["user_rol"] = user_match.iloc[0]['Rol']
                        st.session_state["user_empresa"] = user_match.iloc[0]['Empresa']
                        st.rerun()
                    else:
                        st.error("❌ Clave no válida.")
        return False
    return True

if not check_password():
    st.stop()

# --- DISEÑO POST-LOGIN ---
st.markdown("<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>", unsafe_allow_html=True)

with st.sidebar:
    st.image("https://cysasociados.cl/wp-content/uploads/2022/05/logo-cys.png", width=150)
    st.markdown(f"👤 **{st.session_state['user_nombre']}**")
    st.caption(f"Rol: {st.session_state['user_rol']}")
    st.divider()
    anio_global = st.selectbox("Año de Análisis", ["2025", "2026"])
    if st.button("Cerrar Sesión"):
        del st.session_state["authenticated"]
        st.rerun()

tab1, tab2, tab3 = st.tabs(["📈 Avance Laboral", "🏢 Gestión Admin", "👥 Masa Laboral"])

# --- PESTAÑA 1: CUMPLIMIENTO ---
with tab1:
    df_av = cargar_datos(ID_AVANCE, anio_global)
    if not df_av.empty:
        df_f = df_av[df_av['Empresa'] == st.session_state["user_empresa"]] if st.session_state["user_rol"] == "USUARIO" else df_av
        
        # (Aquí va tu código de KPIs que ya funciona...)
        st.header(f"Resumen de Gestión {anio_global}")
        st.info(f"Bienvenido al panel de control, {st.session_state['user_nombre']}.")

# --- PESTAÑA 2: GESTIÓN ADMIN (LOGS) ---
with tab2:
    if st.session_state["user_rol"] == "USUARIO":
        st.warning("Acceso restringido.")
    else:
        col_a, col_b = st.columns([1, 2])
        with col_a:
            st.subheader("📝 Registro de Entradas")
            if st.session_state["log_accesos"]:
                st.table(pd.DataFrame(st.session_state["log_accesos"]))
            else:
                st.write("No hay ingresos recientes.")
        
        with col_b:
            st.subheader("🏢 Base de Empresas")
            st.dataframe(cargar_datos(ID_EMPRESAS, "Hoja 1"), use_container_width=True)

# --- PESTAÑA 3: MASA LABORAL CON ALERTAS ---
with tab3:
    if anio_global == "2025":
        st.warning("Sin datos para 2025.")
    else:
        st.header("👥 Masa de Colaboradores y Alertas")
        mes_c = st.sidebar.selectbox("Mes Masa:", ["Ene", "Feb", "Mar", "Abr"]) # Simplificado para el ejemplo
        anio_c = anio_global[-2:]
        
        df_staff = cargar_datos(ID_COLABORADORES, f"{mes_c}{anio_c}")
        
        if not df_staff.empty:
            # Filtro por empresa
            df_f = df_staff[df_staff['Razón Social'] == st.session_state["user_empresa"]] if st.session_state["user_rol"] == "USUARIO" else df_staff
            
            # --- LÓGICA DE ALERTAS (Contratos a Plazo Fijo) ---
            st.subheader("🚨 Alertas de Contratación")
            
            # Supongamos que buscamos contratos Plazo Fijo que suelen durar poco
            plazo_fijo = df_f[df_f['Tipo Contrato'].str.contains("Plazo Fijo", na=False)]
            
            if not plazo_fijo.empty:
                st.warning(f"Se detectaron {len(plazo_fijo)} trabajadores con contrato a Plazo Fijo. Revisar fechas de vencimiento.")
                # Aquí podrías aplicar un estilo de color si tuvieras una columna "Fecha Término"
                st.dataframe(plazo_fijo[['Razón Social', 'Rut Trabajador', 'Nombres', 'Apellido Paterno', 'Tipo Contrato']], use_container_width=True)
            else:
                st.success("✅ No hay alertas críticas de vencimiento para este mes.")
            
            st.divider()
            # Gráficos de siempre
            st.plotly_chart(px.pie(df_f, names='Genero', title="Distribución por Género"), use_container_width=True)

# Pie de página
st.markdown("---")
st.caption("Sistema de gestión de datos en tiempo real, desarrollado por C & S Asociados Ltda. para Control Laboral CMSG")