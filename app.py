import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests

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
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
        df = pd.read_csv(url)
        # Limpieza de espacios en los nombres de columnas
        df.columns = [str(c).strip() for c in df.columns]
        return df.dropna(how='all')
    except:
        return pd.DataFrame()

# --- 2. LOGIN INTELIGENTE ---
if "authenticated" not in st.session_state:
    st.title("🔐 Acceso Auditoría CMSG")
    pwd = st.text_input("Contraseña:", type="password")
    if st.button("Entrar"):
        df_u = cargar_datos(ID_USUARIOS, "Usuarios")
        # Buscamos columna de clave (sin importar si es mayúscula o minúscula)
        col_c = [c for c in df_u.columns if 'CLAVE' in c.upper() or 'PASS' in c.upper()][0]
        match = df_u[df_u[col_c].astype(str) == pwd.strip()]
        if not match.empty:
            st.session_state["authenticated"] = True
            st.session_state["u_nom"] = match.iloc[0].get('Nombre', 'Usuario')
            st.session_state["u_emp"] = match.iloc[0].get('Empresa', '')
            st.session_state["u_rol"] = match.iloc[0].get('Rol', 'ADMIN')
            st.rerun()
        else: st.error("Clave incorrecta")
    st.stop()

# --- 3. CARGA Y DETECCIÓN AUTOMÁTICA (EL RADAR) ---
anio = st.sidebar.selectbox("Seleccione Año", ["2026", "2025"])
df_av = cargar_datos(ID_AVANCE, anio)
df_id = cargar_datos(ID_EMPRESAS, "Hoja 1")

# RADAR: Buscamos automáticamente las columnas que parecen meses
meses_ref = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic']
cols_meses = [c for c in df_av.columns if any(m in c.lower() for m in meses_ref)]
# Buscamos la columna de empresa y observaciones por "parecido"
col_empresa = [c for c in df_av.columns if 'EMP' in c.upper()][0]
col_obs = [c for c in df_av.columns if 'OBS' in c.upper()]

# --- 4. LAS 4 PESTAÑAS ---
tabs = st.tabs(["📈 Avance Laboral", "🏢 Base IDs", "👥 Masa Laboral", "⚙️ Log"])

with tabs[0]:
    if not df_av.empty:
        # Filtro por empresa según el usuario
        df_f = df_av[df_av[col_empresa] == st.session_state["u_emp"]] if st.session_state["u_rol"] == "USUARIO" else df_av
        
        st.header(f"Gestión de Auditoría - {anio}")
        
        # KPIs DINÁMICOS (No usan nombres fijos)
        df_num = df_f[cols_meses].apply(pd.to_numeric, errors='coerce')
        cumple = (df_num == 5).sum().sum()
        total = df_num.isin([1,2,3,4,5]).sum().sum()
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Unidades", len(df_f))
        k2.metric("Cumplimiento OK", int(cumple))
        k3.metric("% Avance", f"{(cumple/total*100 if total > 0 else 0):.1f}%")

        st.divider()

        # Detalle y PDF
        emp_sel = st.selectbox("Empresa Seleccionada:", sorted(df_f[col_empresa].unique()))
        row = df_f[df_f[col_empresa] == emp_sel].iloc[0]
        
        c_info, c_pdf = st.columns([2, 1])
        with c_info:
            st.subheader("📝 Observaciones Actuales")
            st.warning(row[col_obs[0]] if col_obs and pd.notna(row[col_obs[0]]) else "Sin observaciones pendientes.")
            
        with c_pdf:
            st.subheader("📄 Descarga PDF")
            mes_descarga = st.selectbox("Elegir Mes:", cols_meses)
            if st.button("🔍 Obtener Archivo"):
                # Buscamos el ID de carpeta en el otro archivo
                c_id_folder = [c for c in df_id.columns if 'CARPETA' in c.upper() or 'ID' in c.upper()][0]
                c_id_emp = [c for c in df_id.columns if 'EMP' in c.upper()][0]
                match_id = df_id[df_id[c_id_emp].astype(str).str.contains(emp_sel, case=False, na=False)]
                
                if not match_id.empty:
                    id_f = match_id.iloc[0][c_id_folder]
                    # Calculamos el número del mes según su posición en la lista detectada
                    num_m = str(cols_meses.index(mes_descarga) + 1).zfill(2)
                    nombre_f = f"Certificado.{num_m}{anio}"
                    r = requests.get(f"{URL_MI_SCRIPT}?nombre={nombre_f}&carpeta={id_f}")
                    if r.text.startswith("http"):
                        st.success("¡Encontrado!")
                        st.link_button("📥 Descargar PDF", r.text.strip())
                    else: st.error("No se encontró el archivo en Drive")
                else: st.error("Esta empresa no tiene ID de carpeta configurado")

        # GRÁFICO CIRCULAR (RESUMEN INDIVIDUAL)
        st.divider()
        st.subheader(f"Resumen Visual: {emp_sel}")
        mapa_pie = {1:"Carga", 2:"Revisión", 3:"Obs", 4:"No Cumple", 5:"Cumple"}
        pie_data = pd.DataFrame([{'Estado': mapa_pie.get(int(row[m]), "S/I") if pd.notna(row[m]) else "S/I"} for m in cols_meses])
        st.plotly_chart(px.pie(pie_data, names='Estado', hole=.4, 
                             color_discrete_map={"Cumple":"#00FF00","Obs":"#FFFF00","No Cumple":"#FF0000","Revisión":"#1E90FF","Carga":"#FF8C00","S/I":"#555555"}), 
                             use_container_width=True)

with tabs[1]:
    st.subheader("Base de Datos de Conexión")
    st.dataframe(df_id)

with tabs[3]:
    st.subheader("Registro de Actividad")
    st.write("Sistema conectado y operando con detección dinámica de columnas.")

# Pie de página
st.markdown("---")
st.caption("Sistema de gestión de datos en tiempo real, desarrollado por C & S Asociados Ltda. para Control Laboral CMSG")