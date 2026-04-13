import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import re

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")
st.markdown("<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;}</style>", unsafe_allow_html=True)

URL_MI_SCRIPT = "https://script.google.com/a/macros/cysasociados.cl/s/AKfycbwi-UFcqZPZFmvA_80Naul4hHoJJAgUd8htMkJUmCpnGs_BAweZVOFFzclWQczMQXbq/exec"

# IDs DE TUS ARCHIVOS
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"

@st.cache_data(ttl=10)
def cargar_datos(sheet_id, nombre_pestana):
    try:
        # Usamos utf-8-sig para eliminar automáticamente el carácter invisible BOM
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
        df = pd.read_csv(url, encoding='utf-8-sig')
        
        # --- LIMPIEZA AGRESIVA DE COLUMNAS ---
        # Borra todo lo que no sea letra o número y pasa a MAYÚSCULAS
        df.columns = [re.sub(r'[^A-Z0-9]', '', str(c).upper()) for c in df.columns]
        
        # Limpiar espacios en los datos de texto
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip().str.upper()
        return df.dropna(how='all')
    except Exception as e:
        return pd.DataFrame()

# --- 2. LOGIN ---
if "authenticated" not in st.session_state:
    st.title("🔐 Acceso Auditoría CMSG")
    pwd = st.text_input("Contraseña:", type="password")
    if st.button("Entrar"):
        df_u = cargar_datos(ID_USUARIOS, "Usuarios")
        if not df_u.empty:
            # Buscamos la columna de clave (normalizada a CLAVE)
            col_c = next((c for c in df_u.columns if 'CLAVE' in c or 'PASS' in c), None)
            if col_c:
                match = df_u[df_u[col_c].astype(str) == pwd.strip().upper()]
                if not match.empty:
                    st.session_state["authenticated"] = True
                    st.session_state["u_nom"] = match.iloc[0].get('NOMBRE', 'USUARIO')
                    st.session_state["u_emp"] = match.iloc[0].get('EMPRESA', '')
                    st.session_state["u_rol"] = match.iloc[0].get('ROL', 'ADMIN')
                    st.rerun()
                else: st.error("Clave incorrecta")
    st.stop()

# --- 3. PROCESAMIENTO ---
anio = st.sidebar.selectbox("Año", ["2026", "2025"])
df_av = cargar_datos(ID_AVANCE, anio)
df_id = cargar_datos(ID_EMPRESAS, "HOJA1") # Sin espacios

# Definimos meses esperados (ya normalizados)
meses_reales = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC']
cols_meses = [c for c in df_av.columns if c in meses_reales]

# --- 4. LAS 4 PESTAÑAS ---
rol = st.session_state["u_rol"]
if rol == "ADMIN":
    tabs = st.tabs(["📈 Avance Laboral", "🏢 Base IDs", "👥 Masa Laboral", "⚙️ Log"])
elif rol == "REVISOR":
    tabs = st.tabs(["📈 Avance Laboral", "🏢 Base IDs", "👥 Masa Laboral"])
else:
    tabs = st.tabs(["📈 Mi Avance", "👥 Masa Laboral"])

# --- TAB 1: AVANCE ---
with tabs[0]:
    if not df_av.empty:
        col_empresa = next((c for c in df_av.columns if 'EMP' in c), df_av.columns[0])
        df_f = df_av[df_av[col_empresa] == st.session_state["u_emp"]] if rol == "USUARIO" else df_av
        
        st.header(f"Gestión de Auditoría - {anio}")
        
        # KPIs
        df_num = df_f[cols_meses].apply(pd.to_numeric, errors='coerce')
        cumple = (df_num == 5).sum().sum()
        total = df_num.isin([1,2,3,4,5]).sum().sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Unidades", len(df_f))
        c2.metric("Certificados OK", int(cumple))
        c3.metric("% Avance", f"{(cumple/total*100 if total > 0 else 0):.1f}%")

        st.divider()

        # Detalle Empresa
        emp_sel = st.selectbox("Seleccione Empresa:", sorted(df_f[col_empresa].unique()))
        row = df_f[df_f[col_empresa] == emp_sel].iloc[0]
        
        col_left, col_right = st.columns([2, 1])
        with col_left:
            st.subheader("📝 Observaciones")
            c_obs = next((c for c in df_av.columns if 'OBS' in c), None)
            st.warning(row[c_obs] if c_obs and pd.notna(row[c_obs]) else "Sin observaciones.")
            
        with col_right:
            st.subheader("📄 Certificado")
            mes_pdf = st.selectbox("Elegir Mes:", cols_meses)
            if st.button("🔍 Obtener PDF"):
                c_id_f = next((c for c in df_id.columns if 'CARPETA' in c or 'ID' in c), None)
                c_id_e = next((c for c in df_id.columns if 'EMP' in c), None)
                match_id = df_id[df_id[c_id_e].str.contains(emp_sel, case=False, na=False)]
                
                if not match_id.empty and c_id_f:
                    id_folder = match_id.iloc[0][c_id_f]
                    mm = str(meses_reales.index(mes_pdf) + 1).zfill(2)
                    nombre_archivo = f"Certificado.{mm}{anio}"
                    r = requests.get(f"{URL_MI_SCRIPT}?nombre={nombre_archivo}&carpeta={id_folder}")
                    if r.text.startswith("http"):
                        st.success("¡Encontrado!")
                        st.link_button("📥 Descargar", r.text.strip())
                    else: st.error("No disponible")
                else: st.error("ID no configurado")

        # GRÁFICO CIRCULAR
        st.divider()
        st.subheader(f"Distribución de Estados: {emp_sel}")
        mapa_pie = {1:"Carga", 2:"Revisión", 3:"Obs", 4:"No Cumple", 5:"Cumple"}
        datos_pie = []
        for m in cols_meses:
            try:
                val = int(float(row[m]))
                if val in mapa_pie: datos_pie.append({'Estado': mapa_pie[val]})
            except: pass
        
        if datos_pie:
            st.plotly_chart(px.pie(pd.DataFrame(datos_pie), names='Estado', hole=.4, 
                                 color_discrete_map={"Cumple":"#00FF00","Obs":"#FFFF00","No Cumple":"#FF0000","Revisión":"#1E90FF","Carga":"#FF8C00"}), 
                                 use_container_width=True)

with tabs[1]:
    st.subheader("Base de Empresas e IDs")
    st.dataframe(df_id, use_container_width=True)

if rol == "ADMIN":
    with tabs[3]:
        st.subheader("⚙️ Log de Sistema")
        st.write("Columnas detectadas en Avance (Limpias):")
        st.write(list(df_av.columns))

# Pie de página
st.markdown("---")
st.caption("Sistema de gestión de datos en tiempo real, desarrollado por C & S Asociados Ltda. para Control Laboral CMSG")