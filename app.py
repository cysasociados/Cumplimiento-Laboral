import streamlit as st
import pandas as pd
import plotly.express as px

# 1. CONFIGURACIÓN DE PANTALLA
st.set_page_config(page_title="Control Cumplimiento CMSG", layout="wide", page_icon="🔐")

# --- CONTROL DE ACCESO (LOGUEO) ---
def check_password():
    if "password_correct" not in st.session_state:
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.title("🔐 Acceso Restringido")
            st.info("Bienvenido a Control Laboral CMSG. Por favor, ingrese su clave.")
            password = st.text_input("Contraseña:", type="password")
            if st.button("Ingresar"):
                if password == "CMSG2026":
                    st.session_state["password_correct"] = True
                    st.rerun()
                else:
                    st.error("❌ Contraseña incorrecta")
        return False
    return True

if not check_password():
    st.stop()

# Ocultar menús
st.markdown("<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>", unsafe_allow_html=True)

# IDs de Google Sheets
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1yZfnAfit8CPzPU-BnhZMEFIr6mNZs91q4SthH9TrAOo"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"

@st.cache_data(ttl=60)
def cargar_datos(sheet_id, nombre_pestana):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
    return pd.read_csv(url)

# --- MENÚ LATERAL ---
with st.sidebar:
    st.image("https://cysasociados.cl/wp-content/uploads/2022/05/logo-cys.png", width=150)
    st.header("Configuración")
    anio_global = st.selectbox("Año de Análisis", ["2025", "2026", "2027"])
    if st.button("Cerrar Sesión"):
        del st.session_state["password_correct"]
        st.rerun()

tab1, tab2, tab3 = st.tabs(["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Colaboradores"])

# --- PESTAÑA 1: CUMPLIMIENTO (LÓGICA FILTRADA) ---
with tab1:
    try:
        df_av = cargar_datos(ID_AVANCE, anio_global)
        mapa_estados = {1:"Carga Doc.", 2:"En Revision", 3:"Observado", 4:"No Cumple", 5:"Cumple", 8:"Sin Info", 9:"No Corresp."}
        colores_mapa = {"Carga Doc.":"#FF8C00", "En Revision":"#1E90FF", "Observado":"#FFFF00", "No Cumple":"#FF0000", "Cumple":"#00FF00", "Sin Info":"#555555", "No Corresp.":"#8B4513"}
        
        meses_list = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
        cols_activos = [c for c in meses_list if c in df_av.columns]
        
        with st.sidebar:
            st.divider()
            mes_sel = st.selectbox("Mes de Análisis:", ["AÑO COMPLETO"] + cols_activos)

        periodo_txt = f"{anio_global}" if mes_sel == "AÑO COMPLETO" else f"{mes_sel.upper()} {anio_global}"
        cols_f = [mes_sel] if mes_sel != "AÑO COMPLETO" else cols_activos
        datos_periodo = df_av[cols_f]

        # --- CÁLCULO DE % EXCLUYENDO 8 Y 9 ---
        # Solo consideramos celdas con valores del 1 al 5 (estados de gestión real)
        mask_gestion_real = datos_periodo.isin([1, 2, 3, 4, 5])
        total_casos_reales = mask_gestion_real.sum().sum()
        total_cumple = (datos_periodo == 5).sum().sum()
        
        porc_cumplimiento = (total_cumple / total_casos_reales * 100) if total_casos_reales > 0 else 0

        # Empresas al día (No tiene 1,2,3,4 y tiene al menos un 5 en el periodo)
        tiene_fallo = datos_periodo.isin([1, 2, 3, 4]).any(axis=1)
        tiene_exito = (datos_periodo == 5).any(axis=1)
        al_dia = (tiene_exito & ~tiene_fallo).sum()

        st.header(f"Gestión de Cumplimiento - {periodo_txt}")
        
        # KPIs Principales
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas Totales", len(df_av))
        k2.metric("% Cumplimiento Real", f"{porc_cumplimiento:.1f}%", help="Calculado solo sobre meses con gestión activa (Excluye 'No Corresponde' y 'Sin Info')")
        k3.metric("Empresas al Día", al_dia)

        st.divider()
        
        # Conteo por Estados
        st.subheader("📊 Conteo de Estados en el Periodo")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("✅ Cumple", (datos_periodo == 5).sum().sum())
        c2.metric("🔵 En Revisión", (datos_periodo == 2).sum().sum())
        c3.metric("🟠 Carga Doc.", (datos_periodo == 1).sum().sum())
        c4.metric("🟡 Observado", (datos_periodo == 3).sum().sum())
        
        c5, c6, c7, _ = st.columns(4)
        c5.metric("🔴 No Cumple", (datos_periodo == 4).sum().sum())
        c6.metric("⚪ Sin Info", (datos_periodo == 8).sum().sum())
        c7.metric("🟤 No Corresp.", (datos_periodo == 9).sum().sum())

        st.divider()
        
        # Evolución
        st.subheader("📈 Evolución Mensual")
        resumen_evo = []
        for m in cols_activos:
            counts = df_av[m].value_counts()
            for cod, cant in counts.items():
                resumen_evo.append({'Mes': m, 'Estado': mapa_estados.get(int(cod), "Otro"), 'Cant': cant})
        st.plotly_chart(px.bar(pd.DataFrame(resumen_evo), x='Mes', y='Cant', color='Estado', color_discrete_map=colores_mapa, barmode='stack'), use_container_width=True)

        st.divider()
        # Zoom por Empresa
        st.subheader("🎯 Detalle Individual")
        emp_sel = st.selectbox("Seleccione Empresa:", ["SELECCIONAR..."] + sorted(list(df_av["Empresa"].unique())))

        if emp_sel != "SELECCIONAR...":
            row_emp = df_av[df_av["Empresa"] == emp_sel][cols_f].iloc[0]
            df_det = pd.DataFrame([{'Mes': m.upper(), 'Estado': mapa_estados.get(int(c), "Otro")} for m, c in row_emp.items()])
            d1, d2 = st.columns([1, 2])
            with d1:
                st.plotly_chart(px.pie(df_det, names='Estado', hole=.4, color='Estado', color_discrete_map=colores_mapa), use_container_width=True)
            with d2:
                st.table(df_det.set_index('Mes').T)

    except Exception as e: st.error(f"Error: {e}")

# --- PESTAÑA 2: EMPRESAS ---
with tab2:
    st.header("Base de Datos Empresas")
    try: st.dataframe(cargar_datos(ID_EMPRESAS, "Hoja 1"), use_container_width=True)
    except: st.warning("No se encontró la hoja de empresas.")

# --- PESTAÑA 3: COLABORADORES (BLOQUEO 2025) ---
with tab3:
    if anio_global == "2025":
        st.warning("⚠️ Sin datos de Masa Laboral para 2025.")
    else:
        st.header(f"Análisis de Dotación - {anio_global}")
        meses_abrev = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        with st.sidebar:
            st.divider()
            mes_colab = st.selectbox("Mes Masa:", ["AÑO COMPLETO"] + meses_abrev)
            anio_corto = anio_global[-2:]

        try:
            if mes_colab == "

# Pie de página
st.markdown("---")
st.caption("Sistema de gestión de datos en tiempo real, desarrollado por C & S Asociados Ltda. para Control Laboral CMSG")