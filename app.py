import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import re

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")

# ⚠️ PEGA AQUÍ TU URL (La que termina en /exec)
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbxbH7GCm95Eh0DMkBCNVD9Ce-lywoCqmUC_DraHw7DopQPeIOJ5XamcqHvf0dyBFtw/exec" 

ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"

@st.cache_data(ttl=5)
def cargar_datos(sheet_id, nombre_pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
        df = pd.read_csv(url, encoding='utf-8-sig')
        # Limpiamos encabezados: quitamos espacios y dejamos en Mayúsculas
        df.columns = [re.sub(r'[^A-Z0-9]', '', str(c).upper()) for c in df.columns]
        return df.dropna(how='all')
    except: return pd.DataFrame()

# --- 2. LOGIN REFORZADO (Inmune a Mayúsculas) ---
if "authenticated" not in st.session_state:
    st.markdown("<h2 style='text-align: center;'>🔐 Acceso Auditoría CMSG</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pwd_input = st.text_input("Ingrese su Clave:", type="password").strip()
        if st.button("Ingresar", use_container_width=True):
            df_u = cargar_datos(ID_USUARIOS, "Usuarios")
            if not df_u.empty:
                # Buscamos la columna de clave (normalizada a CLAVE)
                col_c = next((c for c in df_u.columns if 'CLAVE' in c or 'PASS' in c), None)
                if col_c:
                    # Comparamos AMBOS en minúsculas para que no haya errores
                    df_u['CLAVE_COMP'] = df_u[col_c].astype(str).str.strip().str.lower()
                    if pwd_input.lower() in df_u['CLAVE_COMP'].values:
                        u = df_u[df_u['CLAVE_COMP'] == pwd_input.lower()].iloc[0]
                        st.session_state["authenticated"] = True
                        st.session_state["u_nom"] = u.get('NOMBRE', 'USUARIO')
                        st.session_state["u_emp"] = u.get('EMPRESA', '')
                        st.rerun()
                    else: st.error("❌ Clave no reconocida. Verifica tu Excel.")
                else: st.error("⚠️ No se encontró la columna 'CLAVE' en el Excel.")
    st.stop()

# --- 3. BARRA LATERAL ---
with st.sidebar:
    st.image("https://cysasociados.cl/wp-content/uploads/2022/05/logo-cys.png", width=150)
    st.write(f"👤 **{st.session_state['u_nom']}**")
    anio = st.selectbox("Año", ["2026", "2025"])
    if st.button("Cerrar Sesión"):
        del st.session_state["authenticated"]
        st.rerun()

# CARGA DE TABLAS PRINCIPALES
df_av = cargar_datos(ID_AVANCE, anio)
df_id = cargar_datos(ID_EMPRESAS, "HOJA1")

# --- 4. LAS 4 PESTAÑAS ---
tabs = st.tabs(["📈 Avance Laboral", "🏢 Base IDs", "👥 Masa Laboral", "⚙️ Log"])

with tabs[0]:
    if not df_av.empty:
        # Detectamos columnas de meses (Limpias)
        meses_std = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC']
        cols_m = [c for c in df_av.columns if c in meses_std]
        
        st.header(f"Gestión de Auditoría - {anio}")
        
        # 📊 INDICADORES
        df_num = df_av[cols_m].apply(pd.to_numeric, errors='coerce')
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas", len(df_av))
        k2.metric("Certificados OK", int((df_num == 5).sum().sum()))
        k3.metric("% Avance", f"{((df_num == 5).sum().sum() / df_num.isin([1,2,3,4,5]).sum().sum() * 100 if not df_num.empty else 0):.1f}%")

        st.divider()

        # SELECTOR Y PDF
        emp_sel = st.selectbox("Seleccione Empresa:", sorted(df_av['EMPRESA'].unique()))
        mes_sel = st.selectbox("Mes:", cols_m)
        row = df_av[df_av['EMPRESA'] == emp_sel].iloc[0]
        
        c_obs, c_btn = st.columns([2, 1])
        with c_obs:
            st.subheader("📝 Observaciones")
            # Buscamos la columna de observaciones (puede tener espacios)
            col_obs_act = next((c for c in df_av.columns if 'OBS' in c), None)
            st.warning(row[col_obs_act] if col_obs_act and pd.notna(row[col_obs_act]) else "Sin observaciones.")
            
        with c_btn:
            st.subheader("📄 Certificado")
            if st.button("🚀 Descargar PDF"):
                if "TU_URL" in URL_APPS_SCRIPT:
                    st.error("❌ Falta pegar la URL del Apps Script en la línea 12.")
                else:
                    # Match flexible de empresa
                    match_id = df_id[df_id['EMPRESA'].str.contains(emp_sel[:10], case=False, na=False)]
                    if not match_id.empty:
                        id_folder = str(match_id.iloc[0]['IDCARPETA']).strip()
                        mm = str(meses_std.index(mes_sel) + 1).zfill(2)
                        nombre_f = f"Certificado.{mm}{anio}.pdf"
                        
                        with st.spinner("Buscando en Drive..."):
                            try:
                                r = requests.get(URL_APPS_SCRIPT, params={"nombre": nombre_f, "carpeta": id_folder}, timeout=15)
                                if r.text.startswith("http"):
                                    st.success("¡Encontrado!")
                                    st.link_button("📥 Bajar Certificado", r.text.strip())
                                else: st.error("Archivo no encontrado en Drive.")
                            except: st.error("Error de conexión con el Script.")
                    else: st.error