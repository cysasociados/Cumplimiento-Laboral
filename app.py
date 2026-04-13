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

# IDs DE ARCHIVOS
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"

@st.cache_data(ttl=10)
def cargar_datos(sheet_id, nombre_pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
        df = pd.read_csv(url, encoding='utf-8-sig')
        # Limpieza ácida de encabezados
        df.columns = [re.sub(r'[^A-Z0-9]', '', str(c).upper()) for c in df.columns]
        return df.dropna(how='all')
    except:
        return pd.DataFrame()

# --- 2. LOGIN ---
if "authenticated" not in st.session_state:
    st.title("🔐 Acceso Auditoría CMSG")
    pwd = st.text_input("Contraseña:", type="password")
    if st.button("Entrar"):
        df_u = cargar_datos(ID_USUARIOS, "Usuarios")
        if not df_u.empty:
            col_c = next((c for c in df_u.columns if 'CLAVE' in c or 'PASS' in c), None)
            if col_c:
                # Comparamos clave limpia
                match = df_u[df_u[col_c].astype(str).str.strip().str.upper() == pwd.strip().upper()]
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
df_id = cargar_datos(ID_EMPRESAS, "HOJA1")

meses_reales = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC']
cols_meses = [c for c in df_av.columns if c in meses_reales]

# --- 4. INTERFAZ ---
st.header(f"Gestión de Auditoría - {anio}")

# KPIs
df_f = df_av[df_av.iloc[:,0] == st.session_state["u_emp"]] if st.session_state["u_rol"] == "USUARIO" else df_av
df_num = df_f[cols_meses].apply(pd.to_numeric, errors='coerce')
cumple = (df_num == 5).sum().sum()
total = df_num.isin([1,2,3,4,5]).sum().sum()

c1, c2, c3 = st.columns(3)
c1.metric("Unidades", len(df_f))
c2.metric("Certificados OK", int(cumple))
c3.metric("% Avance", f"{(cumple/total*100 if total > 0 else 0):.1f}%")

st.divider()

# Búsqueda
col_empresa = next((c for c in df_av.columns if 'EMP' in c), df_av.columns[0])
emp_sel = st.selectbox("Seleccione Empresa:", sorted(df_f[col_empresa].unique()))
row = df_f[df_f[col_empresa] == emp_sel].iloc[0]

ca, cb = st.columns([2, 1])
with ca:
    st.subheader("📝 Observaciones")
    c_obs = next((c for c in df_av.columns if 'OBS' in c), None)
    st.warning(row[c_obs] if c_obs and pd.notna(row[c_obs]) else "Sin observaciones.")

with cb:
    st.subheader("📄 Certificado")
    mes_pdf = st.selectbox("Elegir Mes:", cols_meses)
    
    # Lógica de construcción de nombre
    mm = str(meses_reales.index(mes_pdf) + 1).zfill(2)
    nombre_archivo = f"Certificado.{mm}{anio}"
    
    if st.button("Obtener PDF"):
        # Buscar ID Carpeta
        c_id_f = next((c for c in df_id.columns if 'CARPETA' in c or 'ID' in c), None)
        c_id_e = next((c for c in df_id.columns if 'EMP' in c), None)
        
        # Match flexible de nombre de empresa
        match_id = df_id[df_id[c_id_e].astype(str).str.contains(re.escape(emp_sel[:10]), case=False, na=False)]
        
        if not match_id.empty and c_id_f:
            id_folder = str(match_id.iloc[0][c_id_f]).strip()
            
            # --- DEPUREACIÓN (Solo para Sergio) ---
            st.caption(f"🔍 Buscando: `{nombre_archivo}` en Carpeta: `{id_folder}`")
            
            try:
                r = requests.get(f"{URL_MI_SCRIPT}?nombre={nombre_archivo}&carpeta={id_folder}", timeout=10)
                if r.text.startswith("http"):
                    st.success("¡Encontrado!")
                    st.link_button("📥 Descargar", r.text.strip())
                else:
                    st.error(f"No disponible")
                    st.info("💡 Consejo: Revisa que el archivo en Drive se llame EXACTAMENTE igual (ej: Certificado.122025.pdf o Certificado.122025)")
            except:
                st.error("Error de conexión con el servidor de archivos.")
        else:
            st.error("Empresa no vinculada en base de IDs.")

# Pie de página
st.markdown("---")
st.caption("Sistema de gestión de datos en tiempo real, desarrollado por C & S Asociados Ltda. para Control Laboral CMSG")