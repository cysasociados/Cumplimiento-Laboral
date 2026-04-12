import streamlit as st
import pandas as pd
import plotly.express as px

# 1. CONFIGURACIÓN DE PANTALLA
st.set_page_config(page_title="Portal de Gestión CyS", layout="wide", page_icon="🛡️")

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
        # Limpiamos nombres de columnas y quitamos filas vacías
        df.columns = df.columns.str.strip()
        return df.dropna(how='all')
    except Exception as e:
        return pd.DataFrame()

# --- SISTEMA DE LOGIN POR ROLES (ADMIN, REVISOR, USUARIO) ---
def check_password():
    if "authenticated" not in st.session_state:
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.title("🔐 Acceso a Control Laboral CMSG")
            st.info("Ingrese su clave personal para continuar.")
            pwd_input = st.text_input("Contraseña:", type="password").strip()
            
            if st.button("Ingresar"):
                df_u = cargar_datos(ID_USUARIOS, "Usuarios")
                
                if not df_u.empty:
                    # Buscamos la clave ignorando espacios
                    df_u['Clave'] = df_u['Clave'].astype(str).str.strip()
                    user_match = df_u[df_u['Clave'] == pwd_input]
                    
                    if not user_match.empty:
                        st.session_state["authenticated"] = True
                        st.session_state["user_nombre"] = user_match.iloc[0]['Nombre']
                        st.session_state["user_rol"] = user_match.iloc[0]['Rol']
                        st.session_state["user_empresa"] = user_match.iloc[0]['Empresa']
                        st.rerun()
                    else:
                        st.error("❌ Clave no válida. Intente nuevamente.")
                else:
                    st.error("⚠️ No se pudo cargar la base de usuarios. Verifique los permisos del archivo.")
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
    if st.session_state["user_rol"] == "USUARIO":
        st.caption(f"Empresa: {st.session_state['user_empresa']}")
    
    st.divider()
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
        # FILTRO DE SEGURIDAD POR ROL
        if st.session_state["user_rol"] == "USUARIO":
            df_display = df_av[df_av['Empresa'] == st.session_state["user_empresa"]]
        else:
            df_display = df_av

        if df_display.empty:
            st.warning(f"No hay registros para la empresa {st.session_state['user_empresa']}.")
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

                # KPIs (Excluyendo el 9 y el 8 del cumplimiento real)
                mask_real = datos_periodo.isin([1, 2, 3, 4, 5])
                total_r = mask_real.sum().sum()
                total_c = (datos_periodo == 5).sum().sum()
                porc_c = (total_c / total_r * 100) if total_r > 0 else 0

                st.header(f"Gestión de Cumplimiento")
                k1, k2, k3 = st.columns(3)
                k1.metric("Empresas en Vista", len(df_display))
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

                # Gráfico Evolución (No disponible para Rol USUARIO para evitar comparaciones)
                if st.session_state["user_rol"] != "USUARIO":
                    st.divider()
                    st.subheader("📈 Evolución Mensual del Grupo")
                    resumen_evo = []
                    for m in cols_activos:
                        counts = df_display[m].value_counts()
                        for cod, cant in counts.items():
                            resumen_evo.append({'Mes': m, 'Estado': mapa_estados.get(int(cod), "Otro"), 'Cant': cant})
                    st.plotly_chart(px.bar(pd.DataFrame(resumen_evo), x='Mes', y='Cant', color='Estado', color_discrete_map=colores_mapa, barmode='stack'), use_container_width=True)

                st.divider()
                # --- DETALLE INDIVIDUAL (TABLA DEBAJO DE GRÁFICO) ---
                st.subheader("🎯 Zoom Específico")
                if st.session_state["user_rol"] != "USUARIO":
                    emp_v = st.selectbox("Seleccione Empresa:", sorted(list(df_display["Empresa"].unique())))
                else:
                    emp_v = st.session_state["user_empresa"]
                
                row_emp = df_display[df_display["Empresa"] == emp_v][cols_f].iloc[0]
                df_det = pd.DataFrame([{'Mes': m.upper(), 'Estado': mapa_estados.get(int(c), "Otro")} for m, c in row_emp.items()])
                
                st.plotly_chart(px.pie(df_det, names='Estado', hole=.4, color='Estado', color_discrete_map=colores_mapa, title=f"Distribución: {emp_v}"), use_container_width=True)
                st.table(df_det.set_index('Mes').T)

            except Exception as e: st.error(f"Error en cálculos: {e}")

# --- PESTAÑA 2: EMPRESAS (BLOQUEADA PARA USUARIOS EECC) ---
with tab2:
    if st.session_state["user_rol"] == "USUARIO":
        st.warning("Acceso restringido. Esta pestaña es solo para Administradores y Revisores.")
    else:
        st.header("Base de Datos Empresas")
        st.dataframe(cargar_datos(ID_EMPRESAS, "Hoja 1"), use_container_width=True)

# --- PESTAÑA 3: COLABORADORES (BLOQUEO 2025) ---
with tab3:
    if anio_global == "2025":
        st.warning("⚠️ Sin datos de Masa Laboral para el periodo 2025.")
    else:
        st.header(f"Análisis de Dotación")
        meses_abrev = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        with st.sidebar:
            st.divider()
            mes_c = st.selectbox("Mes Masa:", ["AÑO COMPLETO"] + meses_abrev)
            anio_c = anio_global[-2:]

        try:
            if mes_c == "AÑO COMPLETO":
                list_df = []
                for m in meses_abrev:
                    tmp = cargar_datos(ID_COLABORADORES, f"{m}{anio_c}")
                    if not tmp.empty: list_df.append(tmp)
                df_s = pd.concat(list_df, ignore_index=True).drop_duplicates(subset=['Rut Trabajador']) if list_df else pd.DataFrame()
            else:
                df_s = cargar_datos(ID_COLABORADORES, f"{mes_c}{anio_c}")

            if not df_s.empty:
                df_s.columns = df_s.columns.str.strip()
                if st.session_state["user_rol"] == "USUARIO":
                    df_f = df_s[df_s['Razón Social'] == st.session_state["user_empresa"]]
                else:
                    e_list = sorted(df_s['Razón Social'].unique())
                    e_sel = st.multiselect("Filtrar EECC:", e_list, default=e_list)
                    df_f = df_s[df_s['Razón Social'].isin(e_sel)]

                if not df_f.empty:
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Dotación", len(df_f))
                    fem = len(df_f[df_f['Genero'].str.contains('Femenino', case=False, na=False)])
                    m2.metric("% Fem", f"{(fem/len(df_f)*100):.1f}%")
                    ext = len(df_f[~df_f['Nacionalidad'].str.contains('Chile', case=False, na=False)])
                    m3.metric("Extranjeros", ext)
                    hhe = pd.to_numeric(df_f['Total Horas Extra'], errors='coerce').sum() if 'Total Horas Extra' in df_f.columns else 0
                    m4.metric("HH.EE", f"{hhe:,.0f}")
                    
                    g1, g2 = st.columns(2)
                    with g1: st.plotly_chart(px.pie(df_f, names='Genero', hole=0.4, title="Distribución Género"), use_container_width=True)
                    with g2: st.plotly_chart(px.bar(df_f['Tipo Contrato'].value_counts().reset_index(), x='Tipo Contrato', y='count', title="Tipos de Contrato"), use_container_width=True)
                else:
                    st.info("No hay datos de colaboradores para mostrar.")
        except Exception as e: st.info(f"Seleccione un periodo con datos cargados. ({e})")

# Pie de página
st.markdown("---")
st.caption("Sistema de gestión de datos en tiempo real, desarrollado por C & S Asociados Ltda. para Control Laboral CMSG")