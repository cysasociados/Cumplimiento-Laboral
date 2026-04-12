import streamlit as st
import pandas as pd
import plotly.express as px

# 1. CONFIGURACIÓN DE PANTALLA
st.set_page_config(page_title="Control Cumplimiento CMSG", layout="wide", page_icon="📊")

# Ocultar menús nativos de Streamlit para mayor profesionalismo
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- IDs DE LOS ARCHIVOS (Google Sheets) ---
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1yZfnAfit8CPzPU-BnhZMEFIr6mNZs91q4SthH9TrAOo"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"

# --- FUNCIÓN DE CARGA (TTL de 60 segundos para actualizaciones rápidas) ---
@st.cache_data(ttl=60)
def cargar_datos(sheet_id, nombre_pestana):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
    return pd.read_csv(url)

# --- MENÚ LATERAL ---
with st.sidebar:
    st.header("Configuración de Filtros")
    anio_global = st.selectbox("Seleccione Año de Análisis", ["2025", "2026"])
    st.divider()

# --- CREACIÓN DE PESTAÑAS ---
tab1, tab2, tab3 = st.tabs([
    "📈 Resumen Cumplimiento Laboral", 
    "🏢 KPIs Mensuales Empresas", 
    "👥 Masa Trabajadores EECC"
])

# --- PESTAÑA 1: SEGUIMIENTO DE AVANCE ---
with tab1:
    try:
        df_av = cargar_datos(ID_AVANCE, anio_global)
        
        mapa_estados = {
            1: "Carga Documentos", 2: "En Revision", 3: "Observado", 
            4: "No Cumple", 5: "Cumple", 8: "Sin Informacion", 9: "No Corresponde"
        }
        colores_mapa = {
            "Carga Documentos": "#FF8C00", "En Revision": "#1E90FF", "Observado": "#FFFF00",
            "No Cumple": "#FF0000", "Cumple": "#00FF00", "Sin Informacion": "#555555",
            "No Corresponde": "#8B4513"
        }

        meses_list = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
        cols_activos = [c for c in meses_list if c in df_av.columns]
        
        with st.sidebar:
            mes_sel = st.selectbox("📅 Mes de Análisis:", ["AÑO COMPLETO"] + cols_activos)

        periodo_txt = f"{anio_global}" if mes_sel == "AÑO COMPLETO" else f"{mes_sel.upper()} {anio_global}"
        st.header(f"Control de Cumplimiento Laboral CMSG - {periodo_txt}")

        cols_f = [mes_sel] if mes_sel != "AÑO COMPLETO" else cols_activos
        datos_periodo = df_av[cols_f]

        # --- CÁLCULOS DE CUMPLIMIENTO REAL (Excluyendo 'No Corresponde' 9 y 'Sin Info' 8) ---
        
        # 1. Porcentaje de Cumplimiento Real
        # Solo evaluamos celdas que tengan estados de gestión (1, 2, 3, 4, 5)
        mask_evaluables = datos_periodo.isin([1, 2, 3, 4, 5])
        total_evaluables = mask_evaluables.sum().sum()
        total_cumple = (datos_periodo == 5).sum().sum()
        
        porc_cumplimiento = (total_cumple / total_evaluables) * 100 if total_evaluables > 0 else 0

        # 2. Empresas al Día
        # Una empresa está al día si en el periodo NO tiene estados negativos (1,2,3,4) 
        # y tiene al menos un estado de 'Cumple' (5).
        tiene_incumplimiento = datos_periodo.isin([1, 2, 3, 4]).any(axis=1)
        tiene_cumplimiento = (datos_periodo == 5).any(axis=1)
        empresas_cumplen_total = (tiene_cumplimiento & ~tiene_incumplimiento).sum()

        # --- FILA 1 DE KPIs ---
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total Empresas", len(df_av))
        m2.metric("% Cumplimiento Real", f"{porc_cumplimiento:.1f}%", help="Ignora meses 'No Corresponde' y 'Sin Info'")
        m3.metric("Empresas al Día", empresas_cumplen_total, help="Empresas con gestión perfecta en meses activos")
        m4.metric("Observado", (datos_periodo == 3).sum().sum())
        m5.metric("No Cumple", (datos_periodo == 4).sum().sum())
        
        # --- FILA 2 DE KPIs ---
        m6, m7, m8, m9 = st.columns(4)
        m6.metric("En Revision", (datos_periodo == 2).sum().sum())
        m7.metric("Carga Documentos", (datos_periodo == 1).sum().sum())
        m8.metric("Sin Info", (datos_periodo == 8).sum().sum())
        m9.metric("No Corresponde", (datos_periodo == 9).sum().sum())

        st.divider()

        # Gráfico de Evolución
        st.subheader("📈 Evolución de Estados por Mes")
        resumen_evo = []
        for m in cols_activos:
            counts = df_av[m].value_counts()
            for cod, cant in counts.items():
                resumen_evo.append({'Mes': m, 'Estado': mapa_estados.get(int(cod), "Otro"), 'Cant': cant})
        
        fig_evo = px.bar(pd.DataFrame(resumen_evo), x='Mes', y='Cant', color='Estado',
                         color_discrete_map=colores_mapa, barmode='stack', height=400)
        st.plotly_chart(fig_evo, use_container_width=True)

        # Rankings
        st.subheader(f"🏆 Rankings de Desempeño - {periodo_txt}")
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            st.markdown("### ✅ Top 5: Más Cumplidores")
            df_av['p_cumple'] = (df_av[cols_f] == 5).sum(axis=1)
            top_pos = df_av.nlargest(5, 'p_cumple')[['Empresa', 'p_cumple']]
            for i, row in enumerate(top_pos.itertuples(), 1):
                st.write(f"{i}. **{row.Empresa}** ({row.p_cumple} meses)")

        with col_r2:
            st.markdown("### ❌ Top 5: Críticos (No Cumple)")
            df_av['p_ncumple'] = (df_av[cols_f] == 4).sum(axis=1)
            top_neg = df_av.nlargest(5, 'p_ncumple')[['Empresa', 'p_ncumple']]
            for i, row in enumerate(top_neg.itertuples(), 1):
                st.write(f"{i}. **{row.Empresa}** ({row.p_ncumple} meses)")

        st.divider()

        # Detalle por empresa
        st.subheader("🎯 Detalle Específico por Empresa")
        emp_sel = st.selectbox("Seleccione empresa:", ["SELECCIONAR..."] + list(df_av["Empresa"].unique()))

        if emp_sel != "SELECCIONAR...":
            row_emp = df_av[df_av["Empresa"] == emp_sel][cols_f].iloc[0]
            detalle_data = []
            for mes, cod in row_emp.items():
                detalle_data.append({'Mes': mes, 'Estado': mapa_estados.get(int(cod), "Otro")})
            df_det = pd.DataFrame(detalle_data)
            
            fig_p = px.pie(df_det, names='Estado', hole=.4, color='Estado', color_discrete_map=colores_mapa,
                           title=f"Distribución de Estados: {emp_sel}")
            fig_p.update_traces(textinfo='percent+label')
            st.plotly_chart(fig_p, use_container_width=True)
            st.table(df_det.set_index('Mes').T)

    except Exception as e:
        st.error(f"Error en Pestaña 1: {e}")

# --- PESTAÑAS RESTANTES ---
with tab2:
    st.header("🏢 Información Mensual y KPIs")
    try:
        df_kpi = cargar_datos(ID_EMPRESAS, "Hoja 1") 
        st.dataframe(df_kpi, use_container_width=True)
    except Exception as e:
        st.error(f"Error en Pestaña 2: {e}")

with tab3:
    st.header("👥 Masa Trabajadores EECC")
    try:
        df_staff = cargar_datos(ID_COLABORADORES, "Hoja 1")
        st.dataframe(df_staff, use_container_width=True)
    except Exception as e:
        st.error(f"Error en Pestaña 3: {e}")

# Pie de página
st.markdown("---")
st.caption("Sistema de gestión de datos en tiempo real, desarrollado por C & S Asociados Ltda. para Control Laboral CMSG")