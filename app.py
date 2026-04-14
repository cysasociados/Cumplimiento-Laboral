import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import re

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")

# ⚠️ PASO VITAL: Pega aquí tu URL de Aplicación Web de Google
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbxbH7GCm95Eh0DMkBCNVD9Ce-lywoCqmUC_DraHw7DopQPeIOJ5XamcqHvf0dyBFtw/exec" 

# IDs de tus archivos
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"

@st.cache_data(ttl=15)
def cargar_datos(sheet_id, nombre_pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
        df = pd.read_csv(url, encoding='utf-8-sig')
        # Limpieza ácida: borra caracteres raros invisibles de los títulos
        df.columns = [re.sub(r'[^A-Z0-9]', '', str(c).upper()) for c in df.columns]
        return df.dropna(how='all')
    except: return pd.DataFrame()

# --- 2. LOGIN ---
if "authenticated" not in st.session_state:
    st.markdown("<h2 style='text-align: center;'>🔐 Acceso Auditoría CMSG</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pwd = st.text_input("Ingrese Clave:", type="password").strip().upper()
        if st.button("Entrar", use_container_width=True):
            df_u = cargar_datos(ID_USUARIOS, "Usuarios")
            if not df_u.empty and pwd in df_u['CLAVE'].astype(str).values:
                u = df_u[df_u['CLAVE'].astype(str) == pwd].iloc[0]
                st.session_state["authenticated"] = True
                st.session_state["u_nom"] = u.get('NOMBRE', 'USUARIO')
                st.session_state["u_emp"] = u.get('EMPRESA', '')
                st.rerun()
            else: st.error("❌ Clave no reconocida.")
    st.stop()

# --- 3. BARRA LATERAL ---
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
        meses_std = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC']
        cols_m = [c for c in df_av.columns if c in meses_std]
        
        st.header(f"Gestión de Auditoría - {anio}")
        
        # 📊 INDICADORES SUPERIORES
        df_num = df_av[cols_m].apply(pd.to_numeric, errors='coerce')
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas", len(df_av))
        k2.metric("Certificados OK", int((df_num == 5).sum().sum()))
        k3.metric("% Avance", f"{((df_num == 5).sum().sum() / df_num.isin([1,2,3,4,5]).sum().sum() * 100 if not df_num.empty else 0):.1f}%")

        st.divider()

        # 🎯 SELECTOR Y PDF
        emp_sel = st.selectbox("Seleccione Empresa:", sorted(df_av['EMPRESA'].unique()))
        mes_sel = st.selectbox("Mes para Certificado:", cols_m)
        row = df_av[df_av['EMPRESA'] == emp_sel].iloc[0]
        
        c_obs, c_btn = st.columns([2, 1])
        with c_obs:
            st.subheader("📝 Observaciones")
            st.warning(row.get('OBSERVACIONES', "Sin observaciones registradas."))
            
        with c_btn:
            st.subheader("📄 Certificado")
            if st.button("🚀 Descargar PDF"):
                if "TU_URL" in URL_APPS_SCRIPT:
                    st.error("❌ Sergio, ¡te olvidaste de pegar tu URL en el código!")
                else:
                    # Buscar Carpeta
                    match_id = df_id[df_id['EMPRESA'].str.contains(emp_sel[:10], case=False, na=False)]
                    if not match_id.empty:
                        id_folder = str(match_id.iloc[0]['IDCARPETA']).strip()
                        mm = str(meses_std.index(mes_sel) + 1).zfill(2)
                        nombre_f = f"Certificado.{mm}{anio}.pdf"
                        
                        try:
                            r = requests.get(URL_APPS_SCRIPT, params={"nombre": nombre_f, "carpeta": id_folder}, timeout=15)
                            if r.text.startswith("http"):
                                st.success("¡Encontrado!")
                                st.link_button("📥 Bajar Certificado", r.text.strip())
                            else: st.error("No disponible en Drive.")
                        except: st.error("Fallo de red. Revisa tu URL de Apps Script.")
                    else: st.error("ID de carpeta no configurado.")

        # 🔵 GRÁFICO CIRCULAR
        st.divider()
        st.subheader("Estado de Auditoría Anual")
        mapa = {1:"Carga", 2:"Revisión", 3:"Obs", 4:"No Cumple", 5:"Cumple"}
        pie_data = pd.DataFrame([{'Estado': mapa.get(int(float(row[m])), "S/I") if pd.notna(row[m]) else "S/I"} for m in cols_m])
        st.plotly_chart(px.pie(pie_data, names='Estado', hole=.4, color_discrete_map={"Cumple":"#00FF00","Obs":"#FFFF00","No Cumple":"#FF0000","Revisión":"#1E90FF","Carga":"#FF8C00"}), use_container_width=True)

with tabs[1]:
    st.subheader("Base Maestra de IDs")
    st.dataframe(df_id, use_container_width=True)

with tabs[3]:
    st.write("Columnas detectadas:", list(df_av.columns))