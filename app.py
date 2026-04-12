import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import re

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")

# URL DE TU APPS SCRIPT (No la cambies)
URL_MI_SCRIPT = "https://script.google.com/a/macros/cysasociados.cl/s/AKfycbwi-UFcqZPZFmvA_80Naul4hHoJJAgUd8htMkJUmCpnGs_BAweZVOFFzclWQczMQXbq/exec"

# IDs de tus Google Sheets
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"

# --- FUNCIONES DE LIMPIEZA ---
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
        st.error(f"❌ Error cargando pestaña '{nombre_pestana}': {e}")
        return pd.DataFrame()

# --- 2. SISTEMA DE LOGIN ---
if "authenticated" not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 Acceso Control Laboral CMSG")
        pwd = st.text_input("Contraseña:", type="password")
        if st.button("Ingresar"):
            df_u = cargar_datos(ID_USUARIOS, "Usuarios")
            if not df_u.empty:
                # Buscamos la clave en la columna CLAVE
                match = df_u[df_u['CLAVE'].astype(str).str.strip() == pwd.strip()]
                if not match.empty:
                    u = match.iloc[0]
                    st.session_state["authenticated"] = True
                    st.session_state["u_nom"] = u['NOMBRE']
                    st.session_state["u_rol"] = u['ROL']
                    st.session_state["u_emp"] = u['EMPRESA']
                    st.rerun()
                else: st.error("Clave incorrecta")
    st.stop()

# --- 3. INTERFAZ PRINCIPAL ---
with st.sidebar:
    st.image("https://cysasociados.cl/wp-content/uploads/2022/05/logo-cys.png", width=150)
    st.write(f"👤 **{st.session_state['u_nom']}**")
    st.caption(f"Rol: {st.session_state['u_rol']}")
    anio = st.selectbox("Año", ["2025", "2026"])
    if st.button("Salir"):
        del st.session_state["authenticated"]
        st.rerun()

# Carga de datos maestros
df_av = cargar_datos(ID_AVANCE, anio)
df_id = cargar_datos(ID_EMPRESAS, "Hoja 1")

if df_av.empty or df_id.empty:
    st.warning("⚠️ Esperando conexión con Google Sheets...")
    st.stop()

# Filtro por rol
rol = st.session_state["u_rol"]
df_f = df_av[df_av['EMPRESA'] == st.session_state["u_emp"]] if rol == "USUARIO" else df_av

# Pestañas
t1, t2, t3 = st.tabs(["📈 Avance", "👥 Masa", "⚙️ Admin"])

with t1:
    meses = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC']
    cols_m = [c for c in meses if c in df_f.columns]
    mes_sel = st.sidebar.selectbox("Mes:", ["AÑO"] + cols_m)
    
    st.header(f"Gestión de Cumplimiento {anio}")
    
    # KPIs Rápidos
    datos_kpi = df_f[cols_m if mes_sel == "AÑO" else [mes_sel]]
    cumple = (datos_kpi == 5).sum().sum()
    total = datos_kpi.isin([1,2,3,4,5]).sum().sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Empresas", len(df_f))
    c2.metric("% Cumple", f"{(cumple/total*100 if total>0 else 0):.1f}%")
    c3.metric("Certificados OK", int(cumple))

    st.divider()
    
    # Selector de Empresa y Buscador
    emp_sel = st.selectbox("Empresa:", sorted(df_f['EMPRESA'].unique())) if rol != "USUARIO" else st.session_state["u_emp"]
    row = df_f[df_f['EMPRESA'] == emp_sel].iloc[0]
    
    col_a, col_b = st.columns([2, 1])
    with col_a:
        st.subheader("📝 Hallazgos")
        obs_col = "OBS_AUDITORIA" if "OBS_AUDITORIA" in row else "OBS_AUDITORIA" # Ajuste manual
        st.info(row[obs_col] if obs_col in row and pd.notna(row[obs_col]) else "Sin observaciones.")
        
    with col_b:
        st.subheader("📄 Certificado")
        if mes_sel != "AÑO":
            # MATCH DE EMPRESA LIMPIO
            df_id['KEY'] = df_id['EMPRESA'].apply(limpiar_val)
            emp_key = limpiar_val(emp_sel)
            match_folder = df_id[df_id['KEY'] == emp_key]
            
            if not match_folder.empty and "ID_CARPETA" in df_id.columns:
                id_folder = str(match_folder['ID_CARPETA'].iloc[0]).strip()
                mm = str(meses.index(mes_sel)+1).zfill(2)
                nombre_pdf = f"Certificado.{mm}{anio}"
                
                if st.button(f"🔍 Buscar PDF {mes_sel}"):
                    try:
                        r = requests.get(f"{URL_MI_SCRIPT}?nombre={nombre_pdf}&carpeta={id_folder}", timeout=10)
                        if r.text.startswith("http"):
                            st.success("¡Encontrado!")
                            st.link_button("📥 Descargar", r.text.strip())
                        else: st.warning("Certificado No Disponible")
                    except: st.error("Error de conexión con Drive")
            else: st.error("Empresa no vinculada en ID_Empresas")

    # Gráficos
    st.divider()
    mapa = {1:"Carga", 2:"Revisión", 3:"Observado", 4:"No Cumple", 5:"Cumple", 8:"S/I", 9:"N/A"}
    colores = {"Carga":"#FF8C00", "Revisión":"#1E90FF", "Observado":"#FFFF00", "No Cumple":"#FF0000", "Cumple":"#00FF00", "S/I":"#555555", "N/A":"#8B4513"}
    
    df_plot = pd.DataFrame([{'Mes': m, 'Estado': mapa.get(int(row[m]), "S/I") if pd.notna(row[m]) else "S/I"} for m in (cols_m if mes_sel=="AÑO" else [mes_sel])])
    st.plotly_chart(px.pie(df_plot, names='Estado', hole=.4, color='Estado', color_discrete_map=colores), use_container_width=True)

with t3:
    if rol == "ADMIN":
        st.subheader("Diagnóstico de Columnas")
        st.write("Columnas en Avance:", df_av.columns.tolist())
        st.write("Columnas en Empresas:", df_id.columns.tolist())
        st.dataframe(df_id)

# Pie de página
st.markdown("---")
st.caption("Sistema de gestión de datos en tiempo real, desarrollado por C & S Asociados Ltda. para Control Laboral CMSG")