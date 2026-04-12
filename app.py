import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")

# Estilo para ocultar menús de sistema
st.markdown("<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>", unsafe_allow_html=True)

# URL DE TU APPS SCRIPT
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

# --- 2. SISTEMA DE LOGIN ---
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

# --- 3. DISEÑO DE INTERFAZ ---
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

# --- TAB 1: CUMPLIMIENTO TOTAL ---
with tabs[0]:
    df_av = cargar_datos(ID_AVANCE, anio_global)
    df_eecc = cargar_datos(ID_EMPRESAS, "Hoja 1")
    
    if not df_av.empty:
        df_f = df_av[df_av['Empresa'] == st.session_state["user_empresa"]] if rol == "USUARIO" else df_av
        
        meses_list = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic']
        dic_mm = {m: str(i+1).zfill(2) for i, m in enumerate(meses_list)}
        cols_activos = [c for c in meses_list if c in df_f.columns]
        
        with st.sidebar:
            st.divider()
            mes_sel = st.selectbox("Mes de Análisis:", ["AÑO COMPLETO"] + cols_activos)

        # --- INDICADORES SUPERIORES (KPIs) ---
        st.header(f"Gestión de Cumplimiento - {anio_global}")
        
        cols_kpi = [mes_sel] if mes_sel != "AÑO COMPLETO" else cols_activos
        datos_kpi = df_f[cols_kpi]
        
        # Matemática de cumplimiento (Ignora estado 9)
        mask_real = datos_kpi.isin([1, 2, 3, 4, 5])
        total_real = mask_real.sum().sum()
        total_cumple = (datos_kpi == 5).sum().sum()
        porc_cumple = (total_cumple / total_real * 100) if total_real > 0 else 0
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Unidades Auditadas", len(df_f))
        k2.metric("% Cumplimiento Real", f"{porc_cumple:.1f}%")
        # Empresas al día: Tienen al menos un 5 y NO tienen ningún 1,2,3,4 en el periodo
        al_dia = ( (datos_kpi == 5).any(axis=1) & ~datos_kpi.isin([1, 2, 3, 4]).any(axis=1) ).sum()
        k3.metric("Empresas al Día", al_dia)

        st.divider()

        # --- GRÁFICO DE BARRAS (EVOLUCIÓN GRUPAL) ---
        mapa_e = {1:"Carga Doc.", 2:"En Revision", 3:"Observado", 4:"No Cumple", 5:"Cumple", 8:"Sin Info", 9:"No Corresp."}
        colores = {"Carga Doc.":"#FF8C00", "En Revision":"#1E90FF", "Observado":"#FFFF00", "No Cumple":"#FF0000", "Cumple":"#00FF00", "Sin Info":"#555555", "No Corresp.":"#8B4513"}

        if rol != "USUARIO":
            st.subheader("📈 Evolución Mensual del Grupo")
            resumen_evo = []
            for m in cols_activos:
                counts = df_f[m].value_counts()
                for cod, cant in counts.items():
                    resumen_evo.append({'Mes': m.upper(), 'Estado': mapa_e.get(int(cod), "Otro"), 'Cant': cant})
            if resumen_evo:
                fig_bar = px.bar(pd.DataFrame(resumen_evo), x='Mes', y='Cant', color='Estado', 
                                 color_discrete_map=colores, barmode='stack', height=400)
                st.plotly_chart(fig_bar, use_container_width=True)

        st.divider()

        # --- SECCIÓN HALLAZGOS Y BUSCADOR ---
        st.subheader("🎯 Detalle Específico y Certificados")
        emp_v = st.selectbox("Seleccione Empresa:", sorted(df_f["Empresa"].unique())) if rol != "USUARIO" else st.session_state["user_empresa"]
        row_emp = df_f[df_f["Empresa"] == emp_v].iloc[0]

        c_obs, c_cert = st.columns([2, 1])
        with c_obs:
            st.markdown(f"**Hallazgos de Auditoría ({mes_sel}):**")
            obs = row_emp["Obs Auditoria"] if "Obs Auditoria" in row_emp else ""
            if pd.notna(obs) and str(obs).strip() != "": st.warning(obs)
            else: st.success("✅ Sin observaciones pendientes.")

        with c_cert:
            st.markdown("**Buscador de Certificados:**")
            if mes_sel != "AÑO COMPLETO":
                if not df_eecc.empty and "ID_Carpeta" in df_eecc.columns:
                    match_emp = df_eecc[df_eecc['Empresa'] == emp_v]
                    if not match_emp.empty:
                        id_carpeta = match_emp['ID_Carpeta'].iloc[0]
                        mm = dic_mm.get(mes_sel.lower())
                        nombre_pdf = f"Certificado.{mm}{anio_global}"
                        if st.button(f"🔍 Buscar PDF {mes_sel}"):
                            with st.spinner("Consultando Drive..."):
                                try:
                                    res = requests.get(f"{URL_MI_SCRIPT}?nombre={nombre_pdf}&carpeta={id_carpeta}")
                                    if "http" in res.text:
                                        st.success("¡Encontrado!")
                                        st.link_button("📥 Descargar PDF", res.text)
                                    else: st.error("No encontrado. Revise nombre.")
                                except: st.error("Error de conexión.")
                else: st.error("Falta columna 'ID_Carpeta' en Empresas.")
            else: st.info("Elija un mes para descargar.")

        st.divider()
        
        # GRÁFICO INDIVIDUAL PIE Y TABLA
        st.subheader(f"Distribución de Estados: {emp_v}")
        cols_g = [mes_sel] if mes_sel != "AÑO COMPLETO" else cols_activos
        df_p = pd.DataFrame([{'Mes': m.upper(), 'Estado': mapa_e.get(int(row_emp[m]), "Sin Datos") if pd.notna(row_emp[m]) else "Sin Datos"} for m in cols_g])
        st.plotly_chart(px.pie(df_p, names='Estado', hole=.4, color='Estado', color_discrete_map=colores), use_container_width=True)
        st.table(df_p.set_index('Mes').T)

# --- TAB 2: BASE MAESTRA ---
if rol != "USUARIO":
    with tabs[1]:
        st.header("🏢 Base de Datos Empresas")
        st.info("Utilice esta tabla para verificar los IDs de carpeta cargados.")
        st.dataframe(df_eecc, use_container_width=True)

# --- TAB 3: MASA LABORAL ---
idx_m = 1 if rol == "USUARIO" else 2
with tabs[idx_m]:
    if anio_global == "2025": st.warning("⚠️ Datos de Masa no disponibles para 2025.")
    else:
        st.header("👥 Dotación de Personal")
        mes_m = st.sidebar.selectbox("Mes Masa:", ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"])
        df_s = cargar_datos(ID_COLABORADORES, f"{mes_m}{anio_global[-2:]}")
        if not df_s.empty:
            df_f_m = df_s[df_s['Razón Social'] == st.session_state["user_empresa"]] if rol == "USUARIO" else df_s
            st.metric("Dotación Total", len(df_f_m))
            st.plotly_chart(px.pie(df_f_m, names='Genero', hole=0.4, title="Género"), use_container_width=True)

# --- TAB 4: ADMINISTRACIÓN ---
if rol == "ADMIN":
    with tabs[3]:
        st.header("⚙️ Administración")
        st.subheader("📅 Log de Accesos")
        if st.session_state["log_accesos"]: st.table(pd.DataFrame(st.session_state["log_accesos"]))
        st.subheader("👥 Usuarios del Sistema")
        st.dataframe(cargar_datos(ID_USUARIOS, "Usuarios"), use_container_width=True)

# Pie de página
st.markdown("---")
st.caption("Sistema de gestión de datos en tiempo real, desarrollado por C & S Asociados Ltda. para Control Laboral CMSG")