import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import re

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")

# --- LLAVE MAESTRA ---
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbxbH7GCm95Eh0DMkBCNVD9Ce-lywoCqmUC_DraHw7DopQPeIOJ5XamcqHvf0dyBFTw/exec"

# IDs DE GOOGLE SHEETS
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kzt?WBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"

if "log_accesos" not in st.session_state:
    st.session_state["log_accesos"] = []

@st.cache_data(ttl=30)
def cargar_datos(sheet_id, nombre_pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
        df = pd.read_csv(url, encoding='utf-8-sig')
        df.columns = [str(c).strip() for c in df.columns]
        return df.dropna(how='all')
    except: return pd.DataFrame()

# --- LOGIN ---
if "authenticated" not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 Acceso CMSG")
        pwd_input = st.text_input("Contraseña:", type="password").strip()
        if st.button("Ingresar", use_container_width=True):
            df_u = cargar_datos(ID_USUARIOS, "Usuarios")
            col_c = next((c for c in df_u.columns if 'Clave' in c or 'CLAVE' in c), 'Clave')
            user_match = df_u[df_u[col_c].astype(str).str.strip() == pwd_input]
            if not user_match.empty:
                u = user_match.iloc[0]
                st.session_state["log_accesos"].append({"Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"), "Usuario": u['Nombre']})
                st.session_state.update({"authenticated": True, "user_nombre": u['Nombre'], "user_rol": u['Rol'], "user_empresa": u['Empresa']})
                st.rerun()
            else: st.error("❌ Clave no reconocida.")
    st.stop()

# --- INTERFAZ ---
with st.sidebar:
    st.image("https://cysasociados.cl/wp-content/uploads/2022/05/logo-cys.png", width=150)
    st.write(f"👤 **{st.session_state['user_nombre']}**")
    anio_global = st.selectbox("Año", ["2026", "2025"])
    if st.button("Cerrar Sesión"):
        del st.session_state["authenticated"]
        st.rerun()

rol = st.session_state["user_rol"]
tabs = st.tabs(["📈 Avance", "🏢 KPIs", "👥 Masa Laboral", "⚙️ Admin"]) if rol == "ADMIN" else st.tabs(["📈 Avance", "👥 Masa Laboral"])

# --- PESTAÑA 1: AVANCE Y DESCARGAS ---
with tabs[0]:
    df_av = cargar_datos(ID_AVANCE, anio_global)
    df_id = cargar_datos(ID_EMPRESAS, "HOJA1")
    
    if not df_av.empty:
        col_e = next((c for c in df_av.columns if 'Empresa' in c or 'EMPRESA' in c), 'Empresa')
        df_f = df_av[df_av[col_e] == st.session_state["user_empresa"]] if rol == "USUARIO" else df_av

        # Mapeo de Meses para construir el nombre del archivo
        mapa_meses = {
            'ENE': '01', 'FEB': '02', 'MAR': '03', 'ABR': '04', 'MAY': '05', 'JUN': '06',
            'JUL': '07', 'AGO': '08', 'SEP': '09', 'OCT': '10', 'NOV': '11', 'DIC': '12'
        }
        cols_m = [c for c in df_f.columns if c.upper() in mapa_meses]

        st.subheader("🎯 Detalle Individual y Certificados")
        emp_v = st.selectbox("Seleccione Empresa:", sorted(df_f[col_e].unique()))
        row = df_f[df_f[col_e] == emp_v].iloc[0]

        c_d, c_g = st.columns(2)
        with c_d:
            st.info(f"Empresa: **{emp_v}**")
            mes_sel = st.selectbox("Mes para Descarga:", cols_m)
            
            if st.button(f"🚀 Obtener Certificado {mes_sel}"):
                # Buscar ID de carpeta
                col_id_e = next((c for c in df_id.columns if 'Empresa' in c or 'EMPRESA' in c), 'EMPRESA')
                col_id_f = next((c for c in df_id.columns if 'ID' in c or 'CARPETA' in c), 'IDCARPETA')
                match = df_id[df_id[col_id_e].astype(str).str.contains(emp_v[:15], case=False, na=False)]
                
                if not match.empty:
                    id_folder = str(match.iloc[0][col_id_f]).strip()
                    num_mes = mapa_meses.get(mes_sel.upper(), '01')
                    nombre_archivo = f"Certificado.{num_mes}{anio_global}.pdf"
                    
                    with st.spinner("Buscando..."):
                        try:
                            r = requests.get(URL_APPS_SCRIPT, params={"nombre": nombre_archivo, "carpeta": id_folder}, timeout=10)
                            if r.text.startswith("http"):
                                st.success("✅ ¡Encontrado!")
                                st.link_button("📥 Bajar Certificado", r.text.strip())
                            else: 
                                st.error("No disponible.")
                                st.caption(f"Buscado como: `{nombre_archivo}` en carpeta `{id_folder}`")
                        except: st.error("Error de conexión.")
                else: st.error("Empresa no vinculada en Base de IDs.")

        with c_g:
            # Gráfico Circular
            mapa_est = {1:"Carga", 2:"Revisión", 3:"Obs", 4:"No Cumple", 5:"Cumple"}
            pie_list = [{'Estado': mapa_est.get(int(row[m]), "S/I")} for m in cols_m if pd.notna(row[m])]
            if pie_list:
                st.plotly_chart(px.pie(pd.DataFrame(pie_list), names='Estado', hole=.4, 
                                      color_discrete_map={"Cumple":"#00FF00","Obs":"#FFFF00","No Cumple":"#FF0000","Revisión":"#1E90FF","Carga":"#FF8C00"}), use_container_width=True)

# --- PESTAÑA MASA LABORAL ---
idx_masa = 1 if rol == "USUARIO" else 2
with tabs[idx_masa]:
    mes_m = st.selectbox("Mes Masa:", list(mapa_meses.keys()))
    df_m = cargar_datos(ID_COLABORADORES, f"{mes_m.capitalize()}26")
    if not df_m.empty:
        df_m_f = df_m[df_m['Razón Social'] == st.session_state["user_empresa"]] if rol == "USUARIO" else df_m
        st.metric("Dotación", len(df_m_f))
        st.dataframe(df_m_f, use_container_width=True)