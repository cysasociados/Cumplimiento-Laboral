import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import re

# 1. CONFIGURACIÓN Y TU URL MAESTRA
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")

# ⚠️ PEGA AQUÍ TU URL DE APLICACIÓN WEB (LA QUE TERMINA EN /exec)
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbxbH7GCm95Eh0DMkBCNVD9Ce-lywoCqmUC_DraHw7DopQPeIOJ5XamcqHvf0dyBFtw/exec"

# IDs DE GOOGLE SHEETS
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"

# --- FUNCIONES DE LIMPIEZA ---
@st.cache_data(ttl=10)
def cargar_datos(sheet_id, nombre_pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
        df = pd.read_csv(url, encoding='utf-8-sig')
        # Limpieza de encabezados para evitar el KeyError
        df.columns = [re.sub(r'[^A-Z0-9]', '', str(c).upper()) for c in df.columns]
        return df.dropna(how='all')
    except:
        return pd.DataFrame()

# --- 2. LOGIN ---
if "authenticated" not in st.session_state:
    st.title("🔐 Portal Auditoría CMSG")
    pwd = st.text_input("Ingrese su Clave:", type="password")
    if st.button("Entrar"):
        df_u = cargar_datos(ID_USUARIOS, "Usuarios")
        if not df_u.empty:
            match = df_u[df_u['CLAVE'].astype(str) == pwd.strip().upper()]
            if not match.empty:
                st.session_state["authenticated"] = True
                st.session_state["u_nom"] = match.iloc[0].get('NOMBRE', 'USUARIO')
                st.session_state["u_emp"] = match.iloc[0].get('EMPRESA', '')
                st.session_state["u_rol"] = match.iloc[0].get('ROL', 'ADMIN')
                st.rerun()
            else: st.error("Clave incorrecta")
    st.stop()

# --- 3. BARRA LATERAL ---
with st.sidebar:
    st.image("https://cysasociados.cl/wp-content/uploads/2022/05/logo-cys.png", width=150)
    anio = st.selectbox("Año", ["2026", "2025"])
    if st.button("Cerrar Sesión"):
        del st.session_state["authenticated"]
        st.rerun()

df_av = cargar_datos(ID_AVANCE, anio)
df_id = cargar_datos(ID_EMPRESAS, "HOJA1")

# --- 4. LAS 4 PESTAÑAS ---
rol = st.session_state["u_rol"]
tabs = st.tabs(["📈 Avance Laboral", "🏢 KPIs Empresa", "👥 Masa Laboral", "⚙️ Log"])

# --- TAB 1: AVANCE LABORAL ---
with tabs[0]:
    if not df_av.empty:
        meses_ref = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC']
        cols_m = [c for c in df_av.columns if c in meses_ref]
        
        st.header(f"Gestión de Auditoría - {anio}")
        
        # KPIs
        df_num = df_av[cols_m].apply(pd.to_numeric, errors='coerce')
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas", len(df_av))
        k2.metric("Certificados OK", int((df_num == 5).sum().sum()))
        k3.metric("% Avance", f"{((df_num == 5).sum().sum() / df_num.isin([1,2,3,4,5]).sum().sum() * 100):.1f}%")

        st.divider()

        # Detalle Empresa
        emp_sel = st.selectbox("Seleccione Empresa:", sorted(df_av['EMPRESA'].unique()))
        row = df_av[df_av['EMPRESA'] == emp_sel].iloc[0]
        
        c_obs, c_pdf = st.columns([2, 1])
        with c_obs:
            st.subheader("📝 Observaciones")
            st.warning(row['OBSERVACIONES'] if 'OBSERVACIONES' in row and pd.notna(row['OBSERVACIONES']) else "Sin observaciones.")
            
        with c_pdf:
            st.subheader("📄 Certificado")
            mes_sel = st.selectbox("Mes:", cols_m)
            if st.button("🚀 Descargar PDF"):
                # Buscar ID Carpeta
                match_id = df_id[df_id['EMPRESA'].str.contains(emp_sel[:10], case=False, na=False)]
                if not match_id.empty:
                    id_folder = match_id.iloc[0]['IDCARPETA']
                    mm = str(meses_ref.index(mes_sel) + 1).zfill(2)
                    nombre_archivo = f"Certificado.{mm}{anio}.pdf"
                    
                    with st.spinner("Conectando con Drive..."):
                        r = requests.get(URL_APPS_SCRIPT, params={"nombre": nombre_archivo, "carpeta": id_folder})
                        if r.text.startswith("http"):
                            st.success("¡Encontrado!")
                            st.link_button("📥 Bajar Certificado", r.text.strip())
                        else: st.error("No disponible en Drive")
                else: st.error("ID no configurado")

        # Gráfico Circular
        st.subheader("Distribución de Estados")
        mapa_pie = {1:"Carga", 2:"Revisión", 3:"Obs", 4:"No Cumple", 5:"Cumple"}
        pie_data = pd.DataFrame([{'Estado': mapa_pie.get(int(float(row[m])), "S/I") if pd.notna(row[m]) else "S/I"} for m in cols_m])
        st.plotly_chart(px.pie(pie_data, names='Estado', hole=.4, color_discrete_map={"Cumple":"#00FF00","Obs":"#FFFF00","No Cumple":"#FF0000","Revisión":"#1E90FF","Carga":"#FF8C00"}), use_container_width=True)

with tabs[1]:
    st.subheader("Base de Datos IDs")
    st.dataframe(df_id)

with tabs[3]:
    st.subheader("Log de Sistema")
    st.write(f"Usuario: {st.session_state['u_nom']}")
    st.write(f"Conexión con Apps Script: Activa")