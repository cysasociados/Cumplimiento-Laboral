import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import re

# 1. CONFIGURACIÓN E INTERFAZ
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")

# ⚠️ PASO 1: PEGA AQUÍ TU URL DE APLICACIÓN WEB (LA QUE TERMINA EN /exec)
URL_APPS_SCRIPT = "TU_URL_AQUÍ"

# IDs DE TUS HOJAS DE CÁLCULO
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"

# --- FUNCIONES DE CARGA CON LIMPIEZA QUIRÚRGICA ---
@st.cache_data(ttl=10)
def cargar_datos(sheet_id, nombre_pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
        df = pd.read_csv(url, encoding='utf-8-sig')
        # Limpiamos encabezados: quitamos todo lo que no sea letra o número
        df.columns = [re.sub(r'[^A-Z0-9]', '', str(c).upper()) for c in df.columns]
        return df.dropna(how='all')
    except:
        return pd.DataFrame()

# --- 2. LOGIN ULTRA-FLEXIBLE ---
if "authenticated" not in st.session_state:
    st.markdown("<h2 style='text-align: center;'>🔐 Portal Auditoría CMSG</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pwd_input = st.text_input("Ingrese su Clave:", type="password").strip()
        if st.button("Entrar", use_container_width=True):
            df_u = cargar_datos(ID_USUARIOS, "Usuarios")
            if not df_u.empty:
                # Buscamos la columna CLAVE (ya normalizada)
                col_c = next((c for c in df_u.columns if 'CLAVE' in c or 'PASS' in c), None)
                if col_c:
                    # Comparamos ignorando mayúsculas/minúsculas
                    df_u['KEY_TEMP'] = df_u[col_c].astype(str).str.strip().str.lower()
                    match = df_u[df_u['KEY_TEMP'] == pwd_input.lower()]
                    if not match.empty:
                        u = match.iloc[0]
                        st.session_state["authenticated"] = True
                        st.session_state["u_nom"] = u.get('NOMBRE', 'USUARIO')
                        st.session_state["u_emp"] = u.get('EMPRESA', '')
                        st.session_state["u_rol"] = u.get('ROL', 'ADMIN')
                        st.rerun()
                    else: st.error("❌ Clave incorrecta.")
                else: st.error("⚠️ No se halló columna 'CLAVE' en el Excel.")
            else: st.error("❌ Error al conectar con Base de Usuarios.")
    st.stop()

# --- 3. PROCESAMIENTO DE DATOS ---
with st.sidebar:
    st.image("https://cysasociados.cl/wp-content/uploads/2022/05/logo-cys.png", width=150)
    st.write(f"👤 **{st.session_state['u_nom']}**")
    anio = st.selectbox("Año de Análisis", ["2026", "2025"])
    if st.button("Cerrar Sesión"):
        del st.session_state["authenticated"]
        st.rerun()

df_av = cargar_datos(ID_AVANCE, anio)
df_id = cargar_datos(ID_EMPRESAS, "HOJA1")

# --- 4. LAS 4 PESTAÑAS ---
tabs = st.tabs(["📈 Avance Laboral", "🏢 Base IDs", "👥 Masa Laboral", "⚙️ Log"])

with tabs[0]:
    if not df_av.empty:
        # Detectamos meses presentes
        meses_std = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC']
        cols_m = [c for c in df_av.columns if c in meses_std]
        
        st.header(f"Gestión de Auditoría - {anio}")
        
        # KPIs Superiores
        df_num = df_av[cols_m].apply(pd.to_numeric, errors='coerce')
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas Auditadas", len(df_av))
        k2.metric("Certificados OK", int((df_num == 5).sum().sum()))
        k3.metric("% Cumplimiento", f"{((df_num == 5).sum().sum() / df_num.isin([1,2,3,4,5]).sum().sum() * 100 if not df_num.empty else 0):.1f}%")

        st.divider()

        # Selector de Empresa y PDF
        col_e = next((c for c in df_av.columns if 'EMP' in c), df_av.columns[0])
        emp_sel = st.selectbox("Seleccione Empresa:", sorted(df_av[col_e].unique()))
        row = df_av[df_av[col_e] == emp_sel].iloc[0]
        
        c_obs, c_pdf = st.columns([2, 1])
        with c_obs:
            st.subheader("📝 Hallazgos")
            col_o = next((c for c in df_av.columns if 'OBS' in c), 'OBSERVACIONES')
            st.warning(row[col_o] if col_o in row and pd.notna(row[col_o]) else "Sin observaciones.")
            
        with c_pdf:
            st.subheader("📄 Certificado Digital")
            mes_sel = st.selectbox("Mes:", cols_m)
            if st.button("🚀 Descargar PDF"):
                # Buscar Carpeta
                col_id_e = next((c for c in df_id.columns if 'EMP' in c), df_id.columns[0])
                col_id_f = next((c for c in df_id.columns if 'CARPETA' in c or 'ID' in c), None)
                
                match_id = df_id[df_id[col_id_e].str.contains(emp_sel[:10], case=False, na=False)]
                if not match_id.empty and col_id_f:
                    id_folder = match_id.iloc[0][col_id_f]
                    mm = str(meses_std.index(mes_sel) + 1).zfill(2)
                    nombre_f = f"Certificado.{mm}{anio}.pdf"
                    
                    try:
                        r = requests.get(URL_APPS_SCRIPT, params={"nombre": nombre_f, "carpeta": id_folder}, timeout=15)
                        if r.text.startswith("http"):
                            st.success("¡Documento encontrado!")
                            st.link_button("📥 Bajar Certificado", r.text.strip())
                        else: st.error(f"No disponible: {r.text}")
                    except: st.error("Error de conexión con Google.")
                else: st.error("ID de carpeta no configurado para esta empresa.")

        # Gráfico Circular
        st.subheader("Visualización de Estados")
        mapa = {1:"Carga", 2:"Revisión", 3:"Obs", 4:"No Cumple", 5:"Cumple"}
        pie_list = []
        for m in cols_m:
            try:
                val = int(float(row[m]))
                pie_list.append({'Estado': mapa.get(val, "S/I")})
            except: pass
        if pie_list:
            st.plotly_chart(px.pie(pd.DataFrame(pie_list), names='Estado', hole=.4, color_discrete_map={"Cumple":"#00FF00","Obs":"#FFFF00","No Cumple":"#FF0000","Revisión":"#1E90FF","Carga":"#FF8C00"}), use_container_width=True)

with tabs[1]:
    st.subheader("Base de Datos de Conexión (IDs)")
    st.dataframe(df_id, use_container_width=True)

with tabs[3]:
    st.subheader("⚙️ Log de Sistema")
    st.write(f"Conectado como: {st.session_state.get('u_nom')}")
    st.write("Detección de columnas activa.")