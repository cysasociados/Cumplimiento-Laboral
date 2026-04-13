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
        df.columns = [str(c).strip() for c in df.columns] # Solo quitamos espacios, no forzamos mayúsculas
        return df.dropna(how='all')
    except:
        return pd.DataFrame()

# --- 2. LOGIN ---
if "authenticated" not in st.session_state:
    st.title("🔐 Acceso Auditoría CMSG")
    pwd = st.text_input("Contraseña:", type="password")
    if st.button("Entrar"):
        df_u = cargar_datos(ID_USUARIOS, "Usuarios")
        # Buscamos la columna de clave (sea cual sea el nombre)
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

# --- 3. CARGA Y DETECCIÓN AUTOMÁTICA ---
anio = st.sidebar.selectbox("Año", ["2026", "2025"])
df_av = cargar_datos(ID_AVANCE, anio)
df_id = cargar_datos(ID_EMPRESAS, "Hoja 1")

# Identificamos columnas de meses (buscamos cualquier cosa que tenga 3 letras de un mes)
meses_ref = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic']
cols_meses = [c for c in df_av.columns if any(m in c.lower() for m in meses_ref)]
col_empresa = [c for c in df_av.columns if 'EMP' in c.upper()][0]

# --- 4. LAS 4 PESTAÑAS ---
tabs = st.tabs(["📈 Avance Laboral", "🏢 Base IDs", "👥 Masa Laboral", "⚙️ Log"])

with tabs[0]:
    if not df_av.empty:
        # Filtro por usuario
        df_f = df_av[df_av[col_empresa] == st.session_state["u_emp"]] if st.session_state["u_rol"] == "USUARIO" else df_av
        
        # Resumen superior
        st.header(f"Tablero de Control - {anio}")
        
        # Calculamos cumplimiento sin nombres fijos
        df_num = df_f[cols_meses].apply(pd.to_numeric, errors='coerce')
        cumple = (df_num == 5).sum().sum()
        total = df_num.isin([1,2,3,4,5]).sum().sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Empresas", len(df_f))
        c2.metric("Certificados OK", int(cumple))
        c3.metric("% Avance", f"{(cumple/total*100 if total > 0 else 0):.1f}%")

        st.divider()

        # Detalle por Empresa
        emp_sel = st.selectbox("Seleccione Empresa:", sorted(df_f[col_empresa].unique()))
        row = df_f[df_f[col_empresa] == emp_sel].iloc[0]
        
        # Hallazgos y PDF
        col_inf, col_pdf = st.columns([2, 1])
        with col_inf:
            st.subheader("📝 Observaciones")
            col_obs = [c for c in df_av.columns if 'OBS' in c.upper()]
            st.warning(row[col_obs[0]] if col_obs and pd.notna(row[col_obs[0]]) else "Sin observaciones.")
            
        with col_pdf:
            st.subheader("📄 PDF")
            mes_pdf = st.selectbox("Mes para descargar:", cols_meses)
            if st.button("🔍 Buscar Certificado"):
                # Buscamos ID Carpeta
                c_id_folder = [c for c in df_id.columns if 'CARPETA' in c.upper() or 'ID' in c.upper()][0]
                c_id_emp = [c for c in df_id.columns if 'EMP' in c.upper()][0]
                match_id = df_id[df_id[c_id_emp].astype(str).str.contains(emp_sel, case=False, na=False)]
                
                if not match_id.empty:
                    id_f = match_id.iloc[0][c_id_folder]
                    # Formato: Certificado.042026
                    mm = str(cols_meses.index(mes_pdf) + 1).zfill(2)
                    nombre_f = f"Certificado.{mm}{anio}"
                    r = requests.get(f"{URL_MI_SCRIPT}?nombre={nombre_f}&carpeta={id_f}")
                    if r.text.startswith("http"):
                        st.success("Encontrado")
                        st.link_button("📥 Descargar", r.text.strip())
                    else: st.error("No disponible")
                else: st.error("ID no configurado")

        # GRÁFICO CIRCULAR (PIE CHART)
        st.divider()
        st.subheader("Distribución de Estados")
        mapa = {1:"Carga", 2:"Revisión", 3:"Obs", 4:"No Cumple", 5:"Cumple"}
        pie_data = pd.DataFrame([{'Estado': mapa.get(int(row[m]), "S/I") if pd.notna(row[m]) else "S/I"} for m in cols_meses])
        st.plotly_chart(px.pie(pie_data, names='Estado', hole=.4), use_container_width=True)

with tabs[1]:
    st.subheader("Base de Empresas e IDs")
    st.dataframe(df_id)

with tabs[3]:
    st.subheader("Log de Sistema")
    st.write("Conexión estable con Google Sheets.")


# Pie de página
st.markdown("---")
st.caption("Sistema de gestión de datos en tiempo real, desarrollado por C & S Asociados Ltda. para Control Laboral CMSG")