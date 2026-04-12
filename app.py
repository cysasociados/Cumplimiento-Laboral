imimport streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import re

# 1. CONFIGURACIÓN E INTERFAZ LIMPIA
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")
st.markdown("<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;}</style>", unsafe_allow_html=True)

# URL Puente a Drive
URL_MI_SCRIPT = "https://script.google.com/a/macros/cysasociados.cl/s/AKfycbwi-UFcqZPZFmvA_80Naul4hHoJJAgUd8htMkJUmCpnGs_BAweZVOFFzclWQczMQXbq/exec"

# IDs de Google Sheets
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"

# --- FUNCIONES DE SEGURIDAD ---
def limpiar_col(c):
    return re.sub(r'[^A-Z0-9]', '_', str(c).upper().strip())

def limpiar_val(v):
    if pd.isna(v): return ""
    return re.sub(r'[^A-Z0-9]', '', str(v).upper().strip())

@st.cache_data(ttl=30)
def cargar_datos(sheet_id, nombre_pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
        df = pd.read_csv(url)
        df.columns = [limpiar_col(c) for c in df.columns]
        return df.dropna(how='all')
    except Exception as e:
        return pd.DataFrame()

# --- 2. LOGIN SIN ERRORES ---
if "authenticated" not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 Acceso Control Laboral CMSG")
        pwd = st.text_input("Contraseña:", type="password")
        if st.button("Ingresar"):
            df_u = cargar_datos(ID_USUARIOS, "Usuarios")
            if not df_u.empty:
                # Buscador flexible de columna de clave
                col_c = next((c for c in df_u.columns if "CLAVE" in c or "PASS" in c), None)
                if col_c and pwd:
                    match = df_u[df_u[col_c].astype(str).str.strip() == pwd.strip()]
                    if not match.empty:
                        u = match.iloc[0]
                        st.session_state["authenticated"] = True
                        st.session_state["u_nom"] = u.get('NOMBRE', 'Usuario')
                        st.session_state["u_rol"] = u.get('ROL', 'USUARIO')
                        st.session_state["u_emp"] = u.get('EMPRESA', '')
                        st.rerun()
                    else: st.error("❌ Clave incorrecta")
            else: st.error("⚠️ No se pudo conectar con la base de usuarios")
    st.stop()

# --- 3. CARGA DE DATOS ---
with st.spinner("Sincronizando con Google Drive..."):
    anio = st.sidebar.selectbox("Seleccione Año", ["2025", "2026"])
    df_av = cargar_datos(ID_AVANCE, anio)
    df_id = cargar_datos(ID_EMPRESAS, "Hoja 1")

# Si no hay datos, mostrar aviso en lugar de crash
if df_av.empty:
    st.error(f"⚠️ No se encontraron datos en la pestaña '{anio}'. Revisa el nombre en Google Sheets.")
    st.stop()

# --- 4. INTERFAZ PRINCIPAL ---
st.sidebar.write(f"👤 **{st.session_state['u_nom']}**")
if st.sidebar.button("Cerrar Sesión"):
    del st.session_state["authenticated"]
    st.rerun()

# Filtro por rol
df_f = df_av[df_av['EMPRESA'] == st.session_state["u_emp"]] if st.session_state["u_rol"] == "USUARIO" else df_av

t1, t2 = st.tabs(["📈 Avance y Reportes", "⚙️ Configuración"])

with t1:
    meses = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC']
    cols_m = [c for c in meses if c in df_f.columns]
    mes_sel = st.sidebar.selectbox("Mes:", ["AÑO"] + cols_m)
    
    st.header(f"Gestión Laboral - {anio}")
    
    # KPIs
    datos_kpi = df_f[cols_m if mes_sel == "AÑO" else [mes_sel]]
    c1, c2, c3 = st.columns(3)
    c1.metric("Empresas", len(df_f))
    cumple = (datos_kpi == 5).sum().sum()
    c2.metric("Certificados OK", int(cumple))
    total_val = datos_kpi.isin([1,2,3,4,5]).sum().sum()
    c3.metric("% Cumplimiento", f"{(cumple/total_val*100 if total_val>0 else 0):.1f}%")

    st.divider()

    # DETALLE Y BUSCADOR
    emp_sel = st.selectbox("Seleccione Empresa:", sorted(df_f['EMPRESA'].unique())) if st.session_state["u_rol"] != "USUARIO" else st.session_state["u_emp"]
    
    if emp_sel in df_f['EMPRESA'].values:
        row = df_f[df_f['EMPRESA'] == emp_sel].iloc[0]
        col_obs, col_pdf = st.columns([2, 1])
        
        with col_obs:
            st.subheader("📝 Hallazgos")
            # Buscador flexible de columna de observaciones
            col_o = next((c for c in df_f.columns if "OBS" in c), None)
            st.warning(row[col_o] if col_o and pd.notna(row[col_o]) else "Sin observaciones.")
            
        with col_pdf:
            st.subheader("📄 Certificado")
            if mes_sel == "AÑO":
                st.info("Seleccione un mes.")
            else:
                # Búsqueda en ID_Empresas (Lógica flexible)
                df_id['KEY'] = df_id['EMPRESA'].apply(limpiar_val) if 'EMPRESA' in df_id.columns else ""
                match = df_id[df_id['KEY'] == limpiar_val(emp_sel)] if 'KEY' in df_id else pd.DataFrame()
                
                # Detectar columna de ID Carpeta aunque se llame distinto
                col_carpeta = next((c for c in df_id.columns if "CARPETA" in c or "ID" in c), None)
                
                if not match.empty and col_carpeta:
                    id_f = str(match[col_carpeta].iloc[0]).strip()
                    if id_f and id_f != "nan":
                        mm = str(meses.index(mes_sel)+1).zfill(2)
                        nombre_pdf = f"Certificado.{mm}{anio}"
                        if st.button(f"🔍 Buscar PDF {mes_sel}"):
                            try:
                                r = requests.get(f"{URL_MI_SCRIPT}?nombre={nombre_pdf}&carpeta={id_f}", timeout=10)
                                if r.text.startswith("http"):
                                    st.success("¡Encontrado!")
                                    st.link_button("📥 Descargar", r.text.strip())
                                else: st.warning("⚠️ Certificado No Disponible")
                            except: st.error("Error de conexión")
                    else: st.error("⚠️ Esta empresa no tiene ID de carpeta registrado.")
                else: st.error("⚠️ Empresa no vinculada en base de datos.")

    # Gráfico
    st.divider()
    mapa = {1:"Carga", 2:"Revisión", 3:"Observado", 4:"No Cumple", 5:"Cumple", 8:"S/I", 9:"N/A"}
    colores = {"Carga":"#FF8C00", "Revisión":"#1E90FF", "Observado":"#FFFF00", "No Cumple":"#FF0000", "Cumple":"#00FF00", "S/I":"#555555", "N/A":"#8B4513"}
    df_p = pd.DataFrame([{'Mes': m, 'Estado': mapa.get(int(row[m]), "S/I") if pd.notna(row

# Pie de página
st.markdown("---")
st.caption("Sistema de gestión de datos en tiempo real, desarrollado por C & S Asociados Ltda. para Control Laboral CMSG")