import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import re

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")

# URL de tu Apps Script (Puente a Google Drive)
URL_MI_SCRIPT = "https://script.google.com/a/macros/cysasociados.cl/s/AKfycbwi-UFcqZPZFmvA_80Naul4hHoJJAgUd8htMkJUmCpnGs_BAweZVOFFzclWQczMQXbq/exec"

# IDs de tus Google Sheets (IDs Reales de tu Drive)
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"

# --- FUNCIONES DE LIMPIEZA PARA EVITAR ERRORES ---
def limpiar_col(c):
    return re.sub(r'[^A-Z0-9]', '_', str(c).upper().strip())

def limpiar_val(v):
    if pd.isna(v): return ""
    return re.sub(r'[^A-Z0-9]', '', str(v).upper().strip())

@st.cache_data(ttl=60)
def cargar_datos(sheet_id, nombre_pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
        df = pd.read_csv(url)
        df.columns = [limpiar_col(c) for c in df.columns]
        return df.dropna(how='all')
    except Exception as e:
        st.error(f"Error cargando {nombre_pestana}: {e}")
        return pd.DataFrame()

# --- 2. SISTEMA DE LOGIN SEGURO ---
if "authenticated" not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 Acceso Control Laboral CMSG")
        pwd = st.text_input("Contraseña:", type="password")
        if st.button("Ingresar"):
            df_u = cargar_datos(ID_USUARIOS, "Usuarios")
            if not df_u.empty:
                # Buscador flexible de la columna de contraseña
                col_c = next((c for c in df_u.columns if "CLAVE" in c or "PASS" in c), None)
                if col_c:
                    match = df_u[df_u[col_c].astype(str).str.strip() == pwd.strip()]
                    if not match.empty:
                        u = match.iloc[0]
                        st.session_state["authenticated"] = True
                        st.session_state["u_nom"] = u.get('NOMBRE', 'Usuario')
                        st.session_state["u_rol"] = u.get('ROL', 'USUARIO')
                        st.session_state["u_emp"] = u.get('EMPRESA', '')
                        st.rerun()
                    else: st.error("❌ Clave incorrecta")
                else: st.error("No se encontró columna 'CLAVE' en el Excel de Usuarios")
    st.stop()

# --- 3. INTERFAZ PRINCIPAL ---
with st.sidebar:
    st.image("https://cysasociados.cl/wp-content/uploads/2022/05/logo-cys.png", width=150)
    st.write(f"👤 **{st.session_state['u_nom']}**")
    anio = st.selectbox("Seleccione Año", ["2025", "2026"])
    if st.button("Cerrar Sesión"):
        del st.session_state["authenticated"]
        st.rerun()

# Carga de datos de la nube
df_av = cargar_datos(ID_AVANCE, anio)
df_id = cargar_datos(ID_EMPRESAS, "Hoja 1")

if df_av.empty or df_id.empty:
    st.warning("⚠️ Conectando con bases de datos en la nube...")
    st.stop()

# Filtro de seguridad por Empresa
rol = st.session_state["u_rol"]
df_f = df_av[df_av['EMPRESA'] == st.session_state["u_emp"]] if rol == "USUARIO" else df_av

t1, t2, t3 = st.tabs(["📈 Avance y Reportes", "👥 Masa Laboral", "⚙️ Administración"])

with t1:
    meses = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC']
    cols_m = [c for c in meses if c in df_f.columns]
    mes_sel = st.sidebar.selectbox("Mes de Análisis:", ["AÑO COMPLETO"] + cols_m)
    
    st.header(f"Gestión Laboral CMSG - {anio}")
    
    # --- KPIs DE ESTADO ---
    datos_kpi = df_f[cols_m if mes_sel == "AÑO COMPLETO" else [mes_sel]]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("✅ Cumple", (datos_kpi == 5).sum().sum())
    c2.metric("🔵 Revisión", (datos_kpi == 2).sum().sum())
    c3.metric("🟡 Observado", (datos_kpi == 3).sum().sum())
    c4.metric("🟠 Carga", (datos_kpi == 1).sum().sum())
    c5.metric("🔴 No Cumple", (datos_kpi == 4).sum().sum())

    st.divider()
    
    # --- SECCIÓN BUSCADOR Y HALLAZGOS ---
    emp_sel = st.selectbox("Empresa:", sorted(df_f['EMPRESA'].unique())) if rol != "USUARIO" else st.session_state["u_emp"]
    row = df_f[df_f['EMPRESA'] == emp_sel].iloc[0]
    
    col_obs, col_pdf = st.columns([2, 1])
    
    with col_obs:
        st.subheader("📝 Hallazgos de Auditoría")
        col_o = next((c for c in df_f.columns if "OBS" in c), None)
        obs_texto = row[col_o] if col_o and pd.notna(row[col_o]) else "Sin observaciones registradas."
        st.warning(obs_texto)
        
    with col_pdf:
        st.subheader("📄 Certificado PDF")
        if mes_sel == "AÑO COMPLETO":
            st.info("Elija un mes para descargar.")
        else:
            # Match con ID_Empresas (Limpiando nombres)
            df_id['KEY_ID'] = df_id['EMPRESA'].apply(limpiar_val)
            match = df_id[df_id['KEY_ID'] == limpiar_val(emp_sel)]
            
            if not match.empty:
                id_carpeta = str(match['ID_CARPETA'].iloc[0]).strip()
                mm = str(meses.index(mes_sel)+1).zfill(2)
                nombre_pdf = f"Certificado.{mm}{anio}"
                
                if st.button(f"🔍 Buscar Certificado {mes_sel}"):
                    try:
                        r = requests.get(f"{URL_MI_SCRIPT}?nombre={nombre_pdf}&carpeta={id_carpeta}", timeout=10)
                        if r.text.startswith("http"):
                            st.success("¡Documento Encontrado!")
                            st.link_button("📥 Descargar Certificado", r.text.strip())
                        else:
                            st.error("⚠️ Certificado No Disponible")
                    except:
                        st.error("Error de conexión con Drive")
            else:
                st.error("Empresa no vinculada en el archivo de IDs")

    # --- GRÁFICO DE EVOLUCIÓN (SÓLO ADMIN) ---
    st.divider()
    if rol != "USUARIO":
        st.subheader("📈 Evolución Mensual del Grupo")
        mapa = {1:"Carga", 2:"Revisión", 3:"Observado", 4:"No Cumple", 5:"Cumple", 8:"S/I", 9:"N/A"}
        colores = {"Carga":"#FF8C00", "Revisión":"#1E90FF", "Observado":"#FFFF00", "No Cumple":"#FF0000", "Cumple":"#00FF00", "S/I":"#555555", "N/A":"#8B4513"}
        resumen = []
        for m in cols_m:
            counts = df_f[m].value_counts()
            for cod, cant in counts.items():
                resumen.append({'Mes': m, 'Estado': mapa.get(int(cod), "S/I"), 'Cantidad': cant})
        if resumen:
            st.plotly_chart(px.bar(pd.DataFrame(resumen), x='Mes', y='Cantidad', color='Estado', color_discrete_map=colores, barmode='stack'), use_container_width=True)

with t2:
    st.header("Análisis de Masa Laboral")
    st.info("Cargue el mes correspondiente en el panel lateral.")

with t3:
    if rol == "ADMIN":
        st.subheader("🛠️ Diagnóstico de Estructura")
        st.write("Columnas detectadas en ID_Empresas:", df_id.columns.tolist())
        st.dataframe(df_id[['EMPRESA', 'ID_CARPETA']])

# Pie de página
st.markdown("---")
st.caption("Sistema de gestión de datos en tiempo real, desarrollado por C & S Asociados Ltda. para Control Laboral CMSG")