import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import re

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")

# ⚠️ PEGA AQUÍ TU URL ACTUALIZADA (La que termina en /exec)
URL_APPS_SCRIPT = "TU_URL_AQUÍ"

ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"

@st.cache_data(ttl=10)
def cargar_datos(sheet_id, nombre_pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
        df = pd.read_csv(url, encoding='utf-8-sig')
        df.columns = [re.sub(r'[^A-Z0-9]', '', str(c).upper()) for c in df.columns]
        return df.dropna(how='all')
    except: return pd.DataFrame()

# --- LOGIN (Simplificado para que entres rápido) ---
if "authenticated" not in st.session_state:
    st.title("🔐 Acceso Auditoría CMSG")
    pwd = st.text_input("Clave:", type="password")
    if st.button("Entrar"):
        df_u = cargar_datos(ID_USUARIOS, "Usuarios")
        if not df_u.empty:
            match = df_u[df_u['CLAVE'].astype(str).str.strip().str.upper() == pwd.strip().upper()]
            if not match.empty:
                st.session_state["authenticated"] = True
                st.session_state["u_nom"] = match.iloc[0].get('NOMBRE', 'USUARIO')
                st.session_state["u_emp"] = match.iloc[0].get('EMPRESA', '')
                st.rerun()
    st.stop()

# --- DATOS ---
anio = st.sidebar.selectbox("Año", ["2026", "2025"])
df_av = cargar_datos(ID_AVANCE, anio)
df_id = cargar_datos(ID_EMPRESAS, "HOJA1")

# --- PANEL DE DESCARGA ---
st.header(f"Portal de Descargas {anio}")

if not df_av.empty:
    meses_std = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC']
    cols_m = [c for c in df_av.columns if c in meses_std]
    
    emp_sel = st.selectbox("Seleccione Empresa:", sorted(df_av['EMPRESA'].unique()))
    mes_sel = st.selectbox("Seleccione Mes:", cols_m)
    
    if st.button("🚀 Iniciar Descarga"):
        # Buscar Carpeta
        match_id = df_id[df_id['EMPRESA'].str.contains(emp_sel[:10], case=False, na=False)]
        
        if not match_id.empty:
            id_folder = str(match_id.iloc[0]['IDCARPETA']).strip()
            mm = str(meses_std.index(mes_sel) + 1).zfill(2)
            nombre_f = f"Certificado.{mm}{anio}.pdf"
            
            with st.status("Conectando con servidores de Google...", expanded=True) as status:
                try:
                    params = {"nombre": nombre_f, "carpeta": id_folder}
                    st.write(f"🔍 Buscando: `{nombre_f}`")
                    
                    r = requests.get(URL_APPS_SCRIPT, params=params, timeout=15)
                    
                    if r.status_code == 200:
                        if r.text.startswith("http"):
                            status.update(label="✅ ¡Archivo encontrado!", state="complete")
                            st.success("Enlace generado con éxito.")
                            st.link_button("📥 Bajar Certificado", r.text.strip())
                        else:
                            status.update(label="❌ Google respondió pero no halló el archivo.", state="error")
                            st.error(f"Respuesta de Drive: {r.text}")
                    else:
                        status.update(label=f"❌ Error de Servidor (Código {r.status_code})", state="error")
                        st.warning("Google rechazó la conexión. Revisa que el Script esté como 'Cualquier persona'.")
                
                except Exception as e:
                    status.update(label="💥 Fallo Crítico de Red", state="error")
                    st.error(f"Detalle técnico: {e}")
        else:
            st.error("No se encontró el ID de carpeta para esta empresa en Base IDs.")