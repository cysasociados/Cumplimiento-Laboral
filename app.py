import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import re

# 1. CONFIGURACIÓN Y CONSTANTES GLOBALES
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")

# --- LLAVE MAESTRA DE DRIVE ---
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbxbH7GCm95Eh0DMkBCNVD9Ce-lywoCqmUC_DraHw7DopQPeIOJ5XamcqHvf0dyBFtw/exec"

# IDs DE GOOGLE SHEETS
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"

# --- MAPA DE MESES (Global para evitar el NameError) ---
# Usamos mayúsculas para que coincida con el Excel estandarizado
MAPA_MESES = {
    'ENE': '01', 'FEB': '02', 'MAR': '03', 'ABR': '04', 'MAY': '05', 'JUN': '06',
    'JUL': '07', 'AGO': '08', 'SEP': '09', 'OCT': '10', 'NOV': '11', 'DIC': '12'
}

if "log_accesos" not in st.session_state:
    st.session_state["log_accesos"] = []

@st.cache_data(ttl=30)
def cargar_datos(sheet_id, nombre_pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
        df = pd.read_csv(url, encoding='utf-8-sig')
        # Limpieza ácida de encabezados: todo a MAYÚSCULAS y sin espacios
        df.columns = [re.sub(r'[^A-Z0-9]', '', str(c).upper()) for c in df.columns]
        return df.dropna(how='all')
    except:
        return pd.DataFrame()

# --- 2. SISTEMA DE LOGIN (DE v.4) ---
if "authenticated" not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 Acceso Control Laboral CMSG")
        pwd_input = st.text_input("Contraseña:", type="password").strip()
        if st.button("Ingresar", use_container_width=True):
            df_u = cargar_datos(ID_USUARIOS, "Usuarios")
            if not df_u.empty:
                col_c = next((c for c in df_u.columns if 'CLAVE' in c), 'CLAVE')
                match = df_u[df_u[col_c].astype(str).str.strip() == pwd_input]
                if not match.empty:
                    u = match.iloc[0]
                    st.session_state["log_accesos"].append({
                        "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Usuario": u.get('NOMBRE', 'USUARIO'),
                        "Empresa": u.get('EMPRESA', 'N/A')
                    })
                    st.session_state.update({
                        "authenticated": True,
                        "u_nom": u.get('NOMBRE', 'USUARIO'),
                        "u_rol": u.get('ROL', 'USUARIO'),
                        "u_emp": u.get('EMPRESA', '')
                    })
                    st.rerun()
                else: st.error("❌ Clave no válida.")
    st.stop()

# --- 3. DISEÑO INTERFAZ ---
with st.sidebar:
    st.image("https://cysasociados.cl/wp-content/uploads/2022/05/logo-cys.png", width=150)
    st.write(f"👤 **{st.session_state['u_nom']}**")
    st.caption(f"Rol: {st.session_state['u_rol']}")
    anio_global = st.selectbox("Año de Análisis", ["2026", "2025"])
    if st.button("Cerrar Sesión"):
        del st.session_state["authenticated"]
        st.rerun()

# --- PESTAÑAS SEGÚN ROL ---
rol = st.session_state["u_rol"]
if rol == "ADMIN":
    tabs = st.tabs(["📈 Avance", "🏢 KPIs", "👥 Masa Laboral", "⚙️ Admin"])
elif rol == "REVISOR":
    tabs = st.tabs(["📈 Avance", "🏢 KPIs", "👥 Masa Laboral"])
else: # USUARIO
    tabs = st.tabs(["📈 Mi Avance", "👥 Masa Laboral"])

# --- TAB 1: AVANCE Y DESCARGAS (LOGICA v.5) ---
with tabs[0]:
    df_av = cargar_datos(ID_AVANCE, anio_global)
    df_id = cargar_datos(ID_EMPRESAS, "HOJA1")
    
    if not df_av.empty:
        col_e = next((c for c in df_av.columns if 'EMP' in c), df_av.columns[0])
        df_f = df_av[df_av[col_e] == st.session_state["u_emp"]] if rol == "USUARIO" else df_av
        cols_m = [c for c in df_f.columns if c in MAPA_MESES.keys()]

        st.header(f"Gestión de Auditoría - {anio_global}")
        
        # KPIs
        df_num = df_f[cols_m].apply(pd.to_numeric, errors='coerce')
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas", len(df_f))
        if not df_num.empty:
            ok = (df_num == 5).sum().sum()
            k2.metric("Certificados OK", int(ok))
            total = df_num.isin([1,2,3,4,5]).sum().sum()
            k3.metric("% Avance", f"{(ok/total*100 if total > 0 else 0):.1f}%")

        st.divider()

        # Detalle y Descarga
        emp_sel = st.selectbox("Seleccione Empresa:", sorted(df_f[col_e].unique()))
        row = df_f[df_f[col_e] == emp_sel].iloc[0]
        
        c_desc, c_pie = st.columns(2)
        with c_desc:
            st.info(f"Visualizando: **{emp_sel}**")
            mes_sel = st.selectbox("Mes para Certificado:", cols_m)
            
            if st.button(f"🚀 Descargar {mes_sel}"):
                col_id_e = next((c for c in df_id.columns if 'EMP' in c), 'EMPRESA')
                col_id_f = next((c for c in df_id.columns if 'ID' in c or 'CARPETA' in c), 'IDCARPETA')
                
                # Match flexible (Toledo Gianzo vs Toledo Gianzo y Cía)
                match = df_id[df_id[col_id_e].str.contains(emp_sel[:15], case=False, na=False)]
                
                if not match.empty:
                    id_folder = str(match.iloc[0][col_id_f]).strip()
                    nombre_archivo = f"Certificado.{MAPA_MESES[mes_sel]}{anio_global}.pdf"
                    
                    with st.spinner("Buscando en Drive..."):
                        try:
                            r = requests.get(URL_APPS_SCRIPT, params={"nombre": nombre_archivo, "carpeta": id_folder}, timeout=15)
                            if r.text.startswith("http"):
                                st.success("✅ ¡Encontrado!")
                                st.link_button("📥 Bajar Certificado", r.text.strip())
                            else: 
                                st.error("No disponible en Drive.")
                                st.caption(f"Buscado como: `{nombre_archivo}`")
                        except: st.error("Error de conexión.")
                else: st.error("Empresa no vinculada en Base IDs.")

        with c_pie:
            est_map = {1:"Carga", 2:"Revisión", 3:"Obs", 4:"No Cumple", 5:"Cumple"}
            pie_list = [{'Estado': est_map.get(int(row[m]), "S/I")} for m in cols_m if pd.notna(row[m])]
            if pie_list:
                st.plotly_chart(px.pie(pd.DataFrame(pie_list), names='Estado', hole=.4, 
                                      color_discrete_map={"Cumple":"#00FF00","Obs":"#FFFF00","No Cumple":"#FF0000","Revisión":"#1E90FF","Carga":"#FF8C00"}), use_container_width=True)

# --- TAB 3: MASA LABORAL (FIX NameError) ---
idx_masa = 1 if rol == "USUARIO" else 2
with tabs[idx_masa]:
    st.header(f"Análisis de Dotación - {anio_global}")
    # Ahora MAPA_MESES es global y el selectbox no fallará
    mes_m = st.selectbox("Mes Masa:", list(MAPA_MESES.keys()))
    
    df_m = cargar_datos(ID_COLABORADORES, f"{mes_m.capitalize()}{anio_global[-2:]}")
    if not df_m.empty:
        col_rs = next((c for c in df_m.columns if 'RAZON' in c), df_m.columns[0])
        df_m_f = df_m[df_m[col_rs] == st.session_state["u_emp"]] if rol == "USUARIO" else df_m
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Dotación", len(df_m_f))
        if 'NACIONALIDAD' in df_m_f.columns:
            ext = len(df_m_f[~df_m_f['NACIONALIDAD'].str.contains('CHILE', na=False)])
            m2.metric("Extranjeros", ext)
        st.dataframe(df_m_f, use_container_width=True)

# --- TAB 4: ADMIN (DE v.4) ---
if rol == "ADMIN":
    with tabs[3]:
        st.subheader("📅 Log de Accesos")
        if st.session_state["log_accesos"]: st.table(pd.DataFrame(st.session_state["log_accesos"]))
        st.divider()
        st.subheader("👥 Usuarios")
        st.dataframe(cargar_datos(ID_USUARIOS, "Usuarios"), use_container_width=True)