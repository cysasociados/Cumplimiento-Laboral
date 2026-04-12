import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. CONFIGURACIÓN DE PANTALLA
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")

# Inicializar bitácora de ingresos en memoria
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

# --- SISTEMA DE LOGIN POR ROLES ---
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
                        info_usr = user_match.iloc[0]
                        # REGISTRO DE ACCESO CON DÍA Y HORA
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

st.title(f"Bienvenido al Portal de Gestión 👋")

# --- DEFINICIÓN DINÁMICA DE PESTAÑAS ---
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
    if not df_av.empty:
        df_display = df_av[df_av['Empresa'] == st.session_state["user_empresa"]] if rol == "USUARIO" else df_av

        try:
            mapa_estados = {1:"Carga Doc.", 2:"En Revision", 3:"Observado", 4:"No Cumple", 5:"Cumple", 8:"Sin Info", 9:"No Corresp."}
            colores_mapa = {"Carga Doc.":"#FF8C00", "En Revision":"#1E90FF", "Observado":"#FFFF00", "No Cumple":"#FF0000", "Cumple":"#00FF00", "Sin Info":"#555555", "No Corresp.":"#8B4513"}
            meses_list = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
            cols_activos = [c for c in meses_list if c in df_display.columns]
            
            with st.sidebar:
                st.divider()
                mes_sel = st.selectbox("Mes de Análisis:", ["AÑO COMPLETO"] + cols_activos)

            cols_f = [mes_sel] if mes_sel != "AÑO COMPLETO" else cols_activos
            datos_periodo = df_display[cols_f]

            # KPIs
            mask_real = datos_periodo.isin([1, 2, 3, 4, 5])
            total_r = mask_real.sum().sum()
            total_c = (datos_periodo == 5).sum().sum()
            porc_c = (total_c / total_r * 100) if total_r > 0 else 0

            st.header(f"Gestión de Cumplimiento")
            k1, k2, k3 = st.columns(3)
            k1.metric("Empresas", len(df_display))
            k2.metric("% Cumplimiento Real", f"{porc_c:.1f}%")
            
            tiene_f = datos_periodo.isin([1, 2, 3, 4]).any(axis=1)
            tiene_e = (datos_periodo == 5).any(axis=1)
            al_d = (tiene_e & ~tiene_f).sum()
            k3.metric("Empresas al Día", al_d)

            st.divider()
            st.subheader("📊 Conteo de Estados")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("✅ Cumple", (datos_periodo == 5).sum().sum())
            c2.metric("🔵 En Revisión", (datos_periodo == 2).sum().sum())
            c3.metric("🟠 Carga Doc.", (datos_periodo == 1).sum().sum())
            c4.metric("🟡 Observado", (datos_periodo == 3).sum().sum())
            
            c5, c6, c7, _ = st.columns(4)
            c5.metric("🔴 No Cumple", (datos_periodo == 4).sum().sum())
            c6.metric("⚪ Sin Info", (datos_periodo == 8).sum().sum())
            c7.metric("🟤 No Corresp.", (datos_periodo == 9).sum().sum())

            # --- RECUPERADO: GRÁFICO DE BARRAS (EVOLUCIÓN) ---
            if rol != "USUARIO":
                st.divider()
                st.subheader("📈 Evolución Mensual del Grupo")
                resumen_evo = []
                for m in cols_activos:
                    counts = df_display[m].value_counts()
                    for cod, cant in counts.items():
                        resumen_evo.append({'Mes': m, 'Estado': mapa_estados.get(int(cod), "Otro"), 'Cant': cant})
                if resumen_evo:
                    st.plotly_chart(px.bar(pd.DataFrame(resumen_evo), x='Mes', y='Cant', color='Estado', color_discrete_map=colores_mapa, barmode='stack'), use_container_width=True)

            st.divider()
            st.subheader("🎯 Detalle Individual")
            emp_v = st.selectbox("Seleccione Empresa:", sorted(list(df_display["Empresa"].unique()))) if rol != "USUARIO" else st.session_state["user_empresa"]
            row_emp = df_display[df_display["Empresa"] == emp_v][cols_f].iloc[0]
            df_det = pd.DataFrame([{'Mes': m.upper(), 'Estado': mapa_estados.get(int(c), "Otro")} for m, c in row_emp.items()])
            st.plotly_chart(px.pie(df_det, names='Estado', hole=.4, color='Estado', color_discrete_map=colores_mapa, title=f"Distribución: {emp_v}"), use_container_width=True)
            st.table(df_det.set_index('Mes').T)

        except Exception as e: st.error(f"Error en Pestaña 1: {e}")

# --- PESTAÑA 2: KPIs EMPRESAS ---
if rol != "USUARIO":
    with tabs[1]:
        st.header("🏢 KPIs Nivel Empresa")
        st.info("Espacio para métricas de gestión administrativa.")
        st.dataframe(cargar_datos(ID_EMPRESAS, "Hoja 1"), use_container_width=True)

# --- PESTAÑA 3: COLABORADORES ---
idx_masa = 1 if rol == "USUARIO" else 2
with tabs[idx_masa]:
    if anio_global == "2025":
        st.warning("⚠️ Masa Laboral no disponible para 2025.")
    else:
        st.header(f"Análisis de Dotación - {anio_global}")
        meses_abrev = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        with st.sidebar:
            st.divider()
            mes_c = st.selectbox("Mes Masa:", ["AÑO COMPLETO"] + meses_abrev)
        
        df_s = cargar_datos(ID_COLABORADORES, f"{mes_c}{anio_global[-2:]}" if mes_c != "AÑO COMPLETO" else "Ene26")
        
        if not df_s.empty:
            df_s.columns = df_s.columns.str.strip()
            df_f = df_s[df_s['Razón Social'] == st.session_state["user_empresa"]] if rol == "USUARIO" else df_s

            st.subheader("🚨 Alertas de Estabilidad")
            plazo_f = df_f[df_f['Tipo Contrato'].str.contains("Plazo Fijo", na=False)]
            if not plazo_f.empty:
                st.warning(f"Se detectaron {len(plazo_f)} contratos a Plazo Fijo.")
                st.dataframe(plazo_f[['Razón Social', 'Rut Trabajador', 'Nombres', 'Tipo Contrato']], use_container_width=True)
            else: st.success("✅ Todo el personal analizado tiene contrato Indefinido.")

            st.divider()
            m1, m2, m3 = st.columns(3)
            m1.metric("Dotación", len(df_f))
            m2.metric("Extranjeros", len(df_f[~df_f['Nacionalidad'].str.contains('Chile', na=False)]))
            m3.metric("HH.EE Acumuladas", f"{pd.to_numeric(df_f['Total Horas Extra'], errors='coerce').sum():,.0f}")
            
            st.plotly_chart(px.pie(df_f, names='Genero', hole=0.4, title="Género"), use_container_width=True)

# --- PESTAÑA 4: ADMINISTRACIÓN (SÓLO SERGIO / ADMIN) ---
if rol == "ADMIN":
    with tabs[3]:
        st.header("⚙️ Centro de Administración y Control")
        st.subheader("📅 Log de Accesos (Registro Detallado)")
        if st.session_state["log_accesos"]:
            # Mostramos el log con las nuevas columnas de Fecha y Hora
            st.table(pd.DataFrame(st.session_state["log_accesos"]))
        else: st.info("Sin ingresos registrados en esta sesión.")
        
        st.divider()
        st.subheader("👥 Usuarios del Sistema")
        st.dataframe(cargar_datos(ID_USUARIOS, "Usuarios"), use_container_width=True)

# Pie de página
st.markdown("---")
st.caption("Sistema desarrollado por C & S Asociados Ltda. para Control Laboral CMSG")