import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import re

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")

# Estilo para ocultar menús
st.markdown("<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>", unsafe_allow_html=True)

# URL DE TU APPS SCRIPT
URL_MI_SCRIPT = "https://script.google.com/a/macros/cysasociados.cl/s/AKfycbwi-UFcqZPZFmvA_80Naul4hHoJJAgUd8htMkJUmCpnGs_BAweZVOFFzclWQczMQXbq/exec"

# IDs de tus Google Sheets
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"

def limpiar_nombre_columna(col):
    """Limpia encabezados: elimina espacios, puntos y pasa a MAYÚSCULAS"""
    return re.sub(r'[^A-Z0-9]', '_', str(col).upper().strip()).replace('__', '_')

def limpiar_llave_empresa(texto):
    """Limpia nombres de empresa para comparar sin errores"""
    if pd.isna(texto): return ""
    return re.sub(r'[^A-Z0-9]', '', str(texto).upper())

@st.cache_data(ttl=60)
def cargar_datos(sheet_id, nombre_pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
        df = pd.read_csv(url)
        # LIMPIEZA AGRESIVA DE ENCABEZADOS
        df.columns = [limpiar_nombre_columna(c) for c in df.columns]
        return df.dropna(how='all')
    except:
        return pd.DataFrame()

# --- 2. LOGIN ---
if "authenticated" not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 Acceso Control Laboral CMSG")
        pwd_input = st.text_input("Contraseña:", type="password").strip()
        if st.button("Ingresar"):
            df_u = cargar_datos(ID_USUARIOS, "Usuarios")
            if not df_u.empty:
                # Buscamos en columna CLAVE (ya limpiada por cargar_datos)
                user_match = df_u[df_u['CLAVE'].astype(str).str.strip() == pwd_input]
                if not user_match.empty:
                    info = user_match.iloc[0]
                    st.session_state["authenticated"] = True
                    st.session_state["user_nombre"] = info['NOMBRE']
                    st.session_state["user_rol"] = info['ROL']
                    st.session_state["user_empresa"] = info['EMPRESA']
                    st.rerun()
                else: st.error("❌ Clave no válida.")
    st.stop()

# --- 3. DISEÑO ---
with st.sidebar:
    st.image("https://cysasociados.cl/wp-content/uploads/2022/05/logo-cys.png", width=150)
    st.markdown(f"👤 **{st.session_state['user_nombre']}**")
    st.caption(f"Rol: {st.session_state['user_rol']}")
    anio_global = st.selectbox("Año", ["2025", "2026"])
    if st.button("Cerrar Sesión"):
        del st.session_state["authenticated"]
        st.rerun()

rol = st.session_state["user_rol"]
tabs = st.tabs(["📈 Avance Laboral", "🏢 Base Empresas", "👥 Masa Colaboradores", "⚙️ Administración"]) if rol == "ADMIN" else st.tabs(["📈 Avance", "👥 Masa"])

# --- TAB 1: CUMPLIMIENTO ---
with tabs[0]:
    df_av = cargar_datos(ID_AVANCE, anio_global)
    df_eecc = cargar_datos(ID_EMPRESAS, "Hoja 1")
    
    if not df_av.empty:
        # Usamos nombres en mayúsculas por la limpieza automática
        df_f = df_av[df_av['EMPRESA'] == st.session_state["user_empresa"]] if rol == "USUARIO" else df_av
        
        meses_list = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC']
        cols_activos = [c for c in meses_list if c in df_f.columns]
        
        with st.sidebar:
            st.divider()
            mes_sel = st.selectbox("Mes de Análisis:", ["AÑO COMPLETO"] + cols_activos)

        st.header(f"Control de Cumplimiento - {anio_global}")
        
        # KPIs
        cols_kpi = [mes_sel] if mes_sel != "AÑO COMPLETO" else cols_activos
        datos_kpi = df_f[cols_kpi]
        
        mask_real = datos_kpi.isin([1, 2, 3, 4, 5])
        total_real = mask_real.sum().sum()
        total_cumple = (datos_kpi == 5).sum().sum()
        porc_c = (total_cumple / total_real * 100) if total_real > 0 else 0
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas", len(df_f))
        k2.metric("% Cumplimiento", f"{porc_c:.1f}%")
        k3.metric("Certificados OK", int(total_cumple))

        # INDICADORES POR ESTADO
        st.subheader("📊 Resumen por Estados")
        ind1, ind2, ind3, ind4, ind5 = st.columns(5)
        ind1.metric("✅ Cumple", (datos_kpi == 5).sum().sum())
        ind2.metric("🔵 Revisión", (datos_kpi == 2).sum().sum())
        ind3.metric("🟠 Carga", (datos_kpi == 1).sum().sum())
        ind4.metric("🟡 Observado", (datos_kpi == 3).sum().sum())
        ind5.metric("🔴 No Cumple", (datos_kpi == 4).sum().sum())

        st.divider()

        # DETALLE Y BUSCADOR
        emp_v = st.selectbox("Seleccione Empresa:", sorted(df_f["EMPRESA"].unique())) if rol != "USUARIO" else st.session_state["user_empresa"]
        row_emp = df_f[df_f["EMPRESA"] == emp_v].iloc[0]

        c_obs, c_cert = st.columns([2, 1])
        with c_obs:
            st.markdown("**Hallazgos de Auditoría:**")
            obs = row_emp["OBS_AUDITORIA"] if "OBS_AUDITORIA" in row_emp else "Sin observaciones."
            if pd.notna(obs) and str(obs).strip() != "": st.warning(obs)
            else: st.success("✅ Todo al día.")

        with c_cert:
            st.markdown("**Buscador de Certificados:**")
            if mes_sel != "AÑO COMPLETO":
                if not df_eecc.empty:
                    # Comparamos empresas limpiando todo
                    df_eecc['KEY'] = df_eecc['EMPRESA'].apply(limpiar_llave_empresa)
                    key_v = limpiar_llave_empresa(emp_v)
                    match = df_eecc[df_eecc['KEY'] == key_v]
                    
                    if not match.empty:
                        # Buscamos la columna ID_CARPETA (limpiada)
                        col_id = 'ID_CARPETA'
                        if col_id in match.columns:
                            id_carpeta = str(match[col_id].iloc[0]).strip()
                            mm = str(meses_list.index(mes_sel) + 1).zfill(2)
                            nombre_pdf = f"Certificado.{mm}{anio_global}"
                            if st.button(f"🔍 Buscar PDF {mes_sel}"):
                                with st.spinner("Buscando..."):
                                    try:
                                        res = requests.get(f"{URL_MI_SCRIPT}?nombre={nombre_pdf}&carpeta={id_carpeta}", timeout=10)
                                        if res.text.startswith("http"):
                                            st.success("¡Encontrado!")
                                            st.link_button("📥 Descargar", res.text.strip())
                                        else: st.warning("⚠️ Certificado No Disponible")
                                    except: st.error("Error al conectar con Drive.")
                        else: st.error(f"Falta columna ID_CARPETA en {ID_EMPRESAS}")
                    else: st.error("Empresa no mapeada en ID_Empresas.")
            else: st.info("Elija un mes para buscar PDF.")

        st.divider()
        # Gráficos
        mapa_e = {1:"Carga Doc.", 2:"En Revision", 3:"Observado", 4:"No Cumple", 5:"Cumple", 8:"Sin Info", 9:"No Corresp."}
        colores = {"Carga Doc.":"#FF8C00", "En Revision":"#1E90FF", "Observado":"#FFFF00", "No Cumple":"#FF0000", "Cumple":"#00FF00", "Sin Info":"#555555", "No Corresp.":"#8B4513"}
        
        df_p = pd.DataFrame([{'Mes': m, 'Estado': mapa_e.get(int(row_emp[m]), "Sin Datos") if pd.notna(row_emp[m]) else "Sin Datos"} for m in cols_kpi])
        st.plotly_chart(px.pie(df_p, names='Estado', hole=.4, color='Estado', color_discrete_map=colores), use_container_width=True)

# --- TAB ADMIN ---
if rol == "ADMIN":
    with tabs[1]:
        st.subheader("Verificación de Columnas")
        st.write("Columnas detectadas en Empresas:", df_eecc.columns.tolist())
        st.dataframe(df_eecc)


# Pie de página
st.markdown("---")
st.caption("Sistema de gestión de datos en tiempo real, desarrollado por C & S Asociados Ltda. para Control Laboral CMSG")