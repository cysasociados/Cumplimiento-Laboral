import streamlit as st
import pandas as pd
import plotly.express as px

# 1. CONFIGURACIÓN DE PANTALLA
st.set_page_config(page_title="Portal de Gestión CyS", layout="wide", page_icon="🛡️")

# IDs de Google Sheets
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1yZfnAfit8CPzPU-BnhZMEFIr6mNZs91q4SthH9TrAOo"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY" # Tu nuevo archivo de usuarios

@st.cache_data(ttl=60)
def cargar_datos(sheet_id, nombre_pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
        df = pd.read_csv(url)
        return df if not df.empty else pd.DataFrame()
    except:
        return pd.DataFrame()

# --- SISTEMA DE LOGIN POR NIVELES ---
def check_password():
    if "authenticated" not in st.session_state:
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.title("🔐 Acceso a Control Laboral CMSG")
            st.info("Por favor, ingrese su clave personal para continuar.")
            pwd_input = st.text_input("Contraseña:", type="password")
            if st.button("Ingresar"):
                # Cargamos la base de usuarios (Hoja 1)
                df_u = cargar_datos(ID_USUARIOS, "Hoja 1")
                if not df_u.empty:
                    # Buscamos la clave ingresada
                    user_match = df_u[df_u['Clave'].astype(str) == pwd_input]
                    if not user_match.empty:
                        st.session_state["authenticated"] = True
                        st.session_state["user_nombre"] = user_match.iloc[0]['Nombre']
                        st.session_state["user_rol"] = user_match.iloc[0]['Rol']
                        st.session_state["user_empresa"] = user_match.iloc[0]['Empresa']
                        st.rerun()
                    else:
                        st.error("❌ Clave no válida. Contacte a soporte@cysasociados.cl")
                else:
                    st.error("⚠️ Error de conexión con la base de datos.")
        return False
    return True

if not check_password():
    st.stop()

# --- INTERFAZ POST-LOGIN ---
st.markdown("<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>", unsafe_allow_html=True)

with st.sidebar:
    st.image("https://cysasociados.cl/wp-content/uploads/2022/05/logo-cys.png", width=150)
    st.markdown(f"👤 **{st.session_state['user_nombre']}**")
    st.caption(f"Rol: {st.session_state['user_rol']}")
    if st.session_state["user_rol"] == "USUARIO":
        st.caption(f"Empresa: {st.session_state['user_empresa']}")
    
    st.divider()
    st.header("Configuración")
    anio_global = st.selectbox("Año de Análisis", ["2025", "2026", "2027"])
    
    if st.button("Cerrar Sesión"):
        del st.session_state["authenticated"]
        st.rerun()

st.title(f"Bienvenido, {st.session_state['user_nombre']} 👋")

tab1, tab2, tab3 = st.tabs(["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Colaboradores"])

# --- PESTAÑA 1: CUMPLIMIENTO ---
with tab1:
    df_av = cargar_datos(ID_AVANCE, anio_global)
    if not df_av.empty:
        # APLICAR FILTRO POR ROL
        if st.session_state["user_rol"] == "USUARIO":
            df_display = df_av[df_av['Empresa'] == st.session_state["user_empresa"]]
        else:
            df_display = df_av # ADMIN y REVISOR ven todo

        if df_display.empty:
            st.info(f"No hay datos de cumplimiento registrados para {st.session_state['user_empresa']}.")
        else:
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
                mask_gestion_real = datos_periodo.isin([1, 2, 3, 4, 5])
                total_reales = mask_gestion_real.sum().sum()
                total_cumple = (datos_periodo == 5).sum().sum()
                porc_cumplimiento = (total_cumple / total_reales * 100) if total_reales > 0 else 0

                st.header(f"Gestión de Cumplimiento")
                k1, k2, k3 = st.columns(3)
                k1.metric("Unidades en Control", len(df_display))
                k2.metric("% Cumplimiento Real", f"{porc_cumplimiento:.1f}%")
                
                tiene_fallo = datos_periodo.isin([1, 2, 3, 4]).any(axis=1)
                tiene_exito = (datos_periodo == 5).any(axis=1)
                al_dia = (tiene_exito & ~tiene_fallo).sum()
                k3.metric("Empresas al Día", al_dia)

                st.divider()
                st.subheader("📊 Conteo de Estados")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("✅ Cumple", (datos_periodo == 5).sum().sum())
                c2.metric("🔵 En Revisión", (datos_periodo == 2).sum().sum())
                c3.metric("🟠 Carga Doc.", (datos_periodo == 1).sum().sum())
                c4.metric("🟡 Observado", (datos_periodo == 3).sum().sum())

                # Detalle Individual (Solo para ADMIN/REVISOR o si es su propia empresa)
                if st.session_state["user_rol"] != "USUARIO":
                    st.divider()
                    st.subheader("🎯 Zoom por Empresa")
                    emp_sel = st.selectbox("Seleccione Empresa:", sorted(list(df_display["Empresa"].unique())))
                    row_emp = df_display[df_display["Empresa"] == emp_sel][cols_f].iloc[0]
                    df_det = pd.DataFrame([{'Mes': m.upper(), 'Estado': mapa_estados.get(int(c), "Otro")} for m, c in row_emp.items()])
                    st.plotly_chart(px.pie(df_det, names='Estado', hole=.4, color='Estado', color_discrete_map=colores_mapa), use_container_width=True)
                    st.table(df_det.set_index('Mes').T)
                else:
                    # El USUARIO ve su propio gráfico directamente
                    st.divider()
                    st.subheader(f"🎯 Mi Estado de Cumplimiento")
                    row_emp = df_display.iloc[0][cols_f]
                    df_det = pd.DataFrame([{'Mes': m.upper(), 'Estado': mapa_estados.get(int(c), "Otro")} for m, c in row_emp.items()])
                    st.plotly_chart(px.pie(df_det, names='Estado', hole

# Pie de página
st.markdown("---")
st.caption("Sistema de gestión de datos en tiempo real, desarrollado por C & S Asociados Ltda. para Control Laboral CMSG")