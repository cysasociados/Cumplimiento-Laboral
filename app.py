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
            st.info("Bienvenido a Control Laboral CMSG. Por favor, identifíquese.")
            password = st.text_input("Introduzca la contraseña:", type="password")
            if st.button("Ingresar"):
                if password == "CMSG2026": # <--- TU CLAVE
                    st.session_state["password_correct"] = True
                    st.rerun()
                else:
                    st.error("❌ Contraseña incorrecta")
        return False
    return True

if not check_password():
    st.stop()

# Ocultar menús nativos
hide_st_style = """<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>"""
st.markdown(hide_st_style, unsafe_allow_html=True)

# IDs de Google Sheets
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1yZfnAfit8CPzPU-BnhZMEFIr6mNZs91q4SthH9TrAOo"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"

@st.cache_data(ttl=60)
def cargar_datos(sheet_id, nombre_pestana):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
    return pd.read_csv(url)

# --- MENÚ LATERAL GLOBAL ---
with st.sidebar:
    st.image("https://cysasociados.cl/wp-content/uploads/2022/05/logo-cys.png", width=150)
    st.header("Configuración Global")
    anio_global = st.selectbox("Seleccione Año de Análisis", ["2026", "2027"])
    if st.button("Cerrar Sesión"):
        del st.session_state["password_correct"]
        st.rerun()

tab1, tab2, tab3 = st.tabs(["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Colaboradores"])

# --- PESTAÑA 1: CUMPLIMIENTO ---
with tab1:
    try:
        df_av = cargar_datos(ID_AVANCE, anio_global)
        mapa_estados = {1:"Carga Doc.", 2:"En Revision", 3:"Observado", 4:"No Cumple", 5:"Cumple", 8:"Sin Info", 9:"No Corresp."}
        colores_mapa = {"Carga Doc.":"#FF8C00", "En Revision":"#1E90FF", "Observado":"#FFFF00", "No Cumple":"#FF0000", "Cumple":"#00FF00", "Sin Info":"#555555", "No Corresp.":"#8B4513"}
        
        meses_list = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
        cols_activos = [c for c in meses_list if c in df_av.columns]
        
        with st.sidebar:
            st.divider()
            st.subheader("Filtros Avance")
            mes_sel = st.selectbox("Mes de Análisis:", ["AÑO COMPLETO"] + cols_activos)

        cols_f = [mes_sel] if mes_sel != "AÑO COMPLETO" else cols_activos
        datos_periodo = df_av[cols_f]

        # KPIs Globales
        mask_evaluables = datos_periodo.isin([1, 2, 3, 4, 5])
        total_evaluables = mask_evaluables.sum().sum()
        total_cumple = (datos_periodo == 5).sum().sum()
        porc_cumplimiento = (total_cumple / total_evaluables * 100) if total_evaluables > 0 else 0

        st.header(f"Gestión de Cumplimiento - {anio_global}")
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas Totales", len(df_av))
        k2.metric("% Cumplimiento Real", f"{porc_cumplimiento:.1f}%")
        k3.metric("Casos 'No Cumple'", (datos_periodo == 4).sum().sum())
        
        st.divider()
        st.subheader("Evolución Mensual del Grupo")
        resumen_evo = []
        for m in cols_activos:
            counts = df_av[m].value_counts()
            for cod, cant in counts.items():
                resumen_evo.append({'Mes': m, 'Estado': mapa_estados.get(int(cod), "Otro"), 'Cant': cant})
        st.plotly_chart(px.bar(pd.DataFrame(resumen_evo), x='Mes', y='Cant', color='Estado', color_discrete_map=colores_mapa, barmode='stack'), use_container_width=True)

        st.divider()
        # --- AQUÍ ESTÁ LO QUE SE HABÍA PERDIDO: DETALLE POR EMPRESA ---
        st.subheader("🎯 Detalle Específico por Empresa")
        emp_sel = st.selectbox("Seleccione una empresa para ver su detalle:", ["SELECCIONAR..."] + sorted(list(df_av["Empresa"].unique())))

        if emp_sel != "SELECCIONAR...":
            row_emp = df_av[df_av["Empresa"] == emp_sel][cols_f].iloc[0]
            detalle_data = []
            for mes, cod in row_emp.items():
                detalle_data.append({'Mes': mes.upper(), 'Estado': mapa_estados.get(int(cod), "Otro")})
            df_det = pd.DataFrame(detalle_data)
            
            d1, d2 = st.columns([1, 2])
            with d1:
                fig_p = px.pie(df_det, names='Estado', hole=.4, color='Estado', color_discrete_map=colores_mapa, title=f"Distribución: {emp_sel}")
                fig_p.update_traces(textinfo='percent')
                st.plotly_chart(fig_p, use_container_width=True)
            with d2:
                st.markdown(f"**Estados mensuales para {emp_sel}:**")
                st.table(df_det.set_index('Mes').T)

    except Exception as e: st.error(f"Error en Pestaña 1: {e}")

# --- PESTAÑA 2: EMPRESAS ---
with tab2:
    st.header("Detalle de Empresas y Contratos")
    try:
        st.dataframe(cargar_datos(ID_EMPRESAS, "Hoja 1"), use_container_width=True)
    except: st.warning("Hoja de empresas no encontrada.")

# --- PESTAÑA 3: COLABORADORES ---
with tab3:
    st.header(f"Análisis de Dotación - {anio_global}")
    meses_abrev = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    
    with st.sidebar:
        st.divider()
        st.subheader("Filtros Masa Colaboradores")
        mes_colab = st.selectbox("Seleccione Mes Masa:", ["AÑO COMPLETO"] + meses_abrev)
        anio_corto = anio_global[-2:]

    try:
        if mes_colab == "AÑO COMPLETO":
            list_df = []
            for m in meses_abrev:
                try: list_df.append(cargar_datos(ID_COLABORADORES, f"{m}{anio_corto}"))
                except: continue
            df_staff = pd.concat(list_df, ignore_index=True).drop_duplicates(subset=['Rut Trabajador'])
        else:
            df_staff = cargar_datos(ID_COLABORADORES, f"{mes_colab}{anio_corto}")

        df_staff.columns = df_staff.columns.str.strip()
        empresas_list = sorted(df_staff['Razón Social'].unique())
        emp_sel_tab3 = st.multiselect("Filtrar por Empresa (Masa):", empresas_list, default=empresas_list)
        df_final = df_staff[df_staff['Razón Social'].isin(emp_sel_tab3)]

        if not df_final.empty:
            c1, c2, c3, c4 = st.columns(4)
            tot = len(df_final)
            fem = len(df_final[df_final['Genero'].str.contains('Femenino', case=False, na=False)])
            ext = len(df_final[~df_final['Nacionalidad'].str.contains('Chile', case=False, na=False)])
            hhe = pd.to_numeric(df_final['Total Horas Extra'], errors='coerce').sum() if 'Total Horas Extra' in df_final.columns else 0

            c1.metric("Dotación", tot)
            c2.metric("% Femenino", f"{(fem/tot*100):.1f}%")
            c3.metric("Extranjeros", ext)
            c4.metric("Total HH.EE", f"{hhe:,.0f}")

            st.divider()
            g1, g2 = st.columns(2)
            with g1: st.plotly_chart(px.pie(df_final, names='Genero', hole=0.4, title="Género"), use_container_width=True)
            with g2: st.plotly_chart(px.bar(df_final['Tipo Contrato'].value_counts().reset_index(), x='Tipo Contrato', y='count', title="Contratos"), use_container_width=True)
        else:
            st.info("Seleccione empresas para ver KPIs.")
    except: st.info(f"No hay datos de colaboradores para {mes_colab}{anio_corto}.")

# Pie de página
st.markdown("---")
st.caption("Sistema de gestión de datos en tiempo real, desarrollado por C & S Asociados Ltda. para Control Laboral CMSG")