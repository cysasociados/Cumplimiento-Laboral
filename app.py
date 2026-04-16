import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import base64
import re
import os
import pytz

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")
chile_tz = pytz.timezone('America/Santiago')

# --- CABECERA ---
col_logo_l, col_espacio, col_logo_r = st.columns([2, 4, 1])
with col_logo_l:
    if os.path.exists("CMSG.png"): st.image("CMSG.png", width=250)
    else: st.subheader("🏢 Minera San Gerónimo")
with col_logo_r:
    if os.path.exists("cys.png"): st.image("cys.png", width=120)
    else: st.write("**C&S Asociados**")

# --- CONEXIÓN ---
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbz0twB53lP3FXsKcYFeuiveudxWjHnJ8MBomDV1sGRl2SUqnPVeYay3BHKXhTg-hTe1hg/exec"

ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"

MAPA_ESTADOS = {1:"Carga Doc.", 2:"En Revision", 3:"Observado", 4:"No Cumple", 5:"Cumple", 8:"Sin Info", 9:"No Corresp."}
COLORES_ESTADOS = {"Carga Doc.":"#FF8C00", "En Revision":"#1E90FF", "Observado":"#FFFF00", "No Cumple":"#FF0000", "Cumple":"#00FF00", "Sin Info":"#555555", "No Corresp.":"#8B4513"}
MAPA_MESES = {'ENE':'01','FEB':'02','MAR':'03','ABR':'04','MAY':'05','JUN':'06','JUL':'07','AGO':'08','SEP':'09','OCT':'10','NOV':'11','DIC':'12'}
MAPA_MESES_CARPETAS = {'ENE':'01_ENE','FEB':'02_FEB','MAR':'03_MAR','ABR':'04_ABR','MAY':'05_MAY','JUN':'06_JUN','JUL':'07_JUL','AGO':'08_AGO','SEP':'09_SEP','OCT':'10_OCT','NOV':'11_NOV','DIC':'12_DIC'}

if "log_accesos" not in st.session_state:
    st.session_state["log_accesos"] = []

@st.cache_data(ttl=15)
def cargar_datos(sheet_id, nombre_pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
        df = pd.read_csv(url, encoding='utf-8-sig')
        df.columns = [re.sub(r'[^A-Z0-9]', '', str(c).upper()) for c in df.columns]
        return df.dropna(how='all')
    except: return pd.DataFrame()

# --- 2. LOGIN ---
if "authenticated" not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 Acceso Control Laboral CMSG")
        pwd = st.text_input("Contraseña:", type="password").strip()
        if st.button("Ingresar", use_container_width=True):
            df_u = cargar_datos(ID_USUARIOS, "Usuarios")
            col_c = next((c for c in df_u.columns if 'CLAVE' in str(c).upper()), 'CLAVE')
            match = df_u[df_u[col_c].astype(str).str.strip() == pwd]
            if not match.empty:
                u = match.iloc[0]
                ahora_ch = datetime.now(chile_tz)
                email_user = str(u.get('EMAIL')).strip() if pd.notna(u.get('EMAIL')) else 'cumplimiento@cysasociados.cl'
                st.session_state.update({
                    "authenticated": True, "u_nom": u.get('NOMBRE',''), "u_rol": u.get('ROL',''), 
                    "u_emp": u.get('EMPRESA',''), "u_email": email_user
                })
                st.rerun()
            else: st.error("❌ Clave no válida.")
    st.stop()

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuración")
    anio_global = st.selectbox("Año de Análisis", ["2026", "2025"])
    df_av = cargar_datos(ID_AVANCE, anio_global)
    cols_m_sidebar = [c for c in df_av.columns if c in MAPA_MESES.keys()] if not df_av.empty else []
    mes_sidebar = st.selectbox("Mes de Análisis", ["AÑO COMPLETO"] + cols_m_sidebar)
    st.divider()
    st.write(f"👤 **{st.session_state['u_nom']}**")
    st.caption(f"Rol: {st.session_state['u_rol']}")
    if st.button("Cerrar Sesión"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# --- 4. TABS ---
rol = st.session_state["u_rol"]
if rol == "ADMIN": tab_list = ["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Colaboradores", "📤 Carga", "⚙️ Administración"]
elif rol == "REVISOR": tab_list = ["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Colaboradores", "📤 Carga"]
else: tab_list = ["📈 Mi Avance", "👥 Masa Laboral", "📤 Carga de Documentos"]
tabs = st.tabs(tab_list)

# --- TAB 1: AVANCE ---
with tabs[0]:
    df_id = cargar_datos(ID_EMPRESAS, "HOJA1")
    if not df_av.empty:
        col_e = next((c for c in df_av.columns if 'EMP' in str(c).upper()), 'EMPRESA')
        df_f = df_av[df_av[col_e] == st.session_state["u_emp"]] if rol == "USUARIO" else df_av
        cols_filtro = [mes_sidebar] if mes_sidebar != "AÑO COMPLETO" else cols_m_sidebar
        df_num = df_f[cols_filtro].apply(pd.to_numeric, errors='coerce')

        # --- CÁLCULO CUMPLIMIENTO (IGNORANDO ESTADO 9) ---
        df_auditables = df_num[df_num != 9] # Filtramos los No Corresp.
        total_p = df_auditables.count().sum() # .count() cuenta todo lo que NO es NaN/9
        total_5 = (df_auditables == 5).sum().sum()
        cumplimiento = (total_5 / total_p * 100) if total_p > 0 else 0

        st.header(f"Gestión Laboral CMSG - {anio_global}")
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas", len(df_f))
        k2.metric("% Cumplimiento Real", f"{cumplimiento:.1f}%", help="No incluye estados 'No Corresp.'")
        k3.metric("Empresas al Día", (df_auditables == 5).all(axis=1).sum() if mes_sidebar == "AÑO COMPLETO" else "N/A")

        st.write("### 📊 Resumen por Estados")
        recuento = df_num.stack().value_counts()
        m_cols = st.columns(len(MAPA_ESTADOS))
        for i, (cod, nom) in enumerate(MAPA_ESTADOS.items()):
            m_cols[i].metric(nom, int(recuento.get(cod, 0)))

        st.divider()
        st.subheader("🎯 Análisis Detallado por Empresa")
        emp_sel = st.selectbox("Seleccione Empresa:", sorted(df_f[col_e].unique()))
        df_es = df_f[df_f[col_e] == emp_sel]
        
        col_d, col_p = st.columns([1, 2])
        with col_d:
            st.info(f"Empresa: **{emp_sel}**")
            mes_pdf = st.selectbox("Mes para Certificado:", cols_m_sidebar)
            if st.button(f"🔍 Obtener PDF {mes_pdf}"):
                match = df_id[df_id.iloc[:,1].str.contains(emp_sel[:10], case=False, na=False)]
                if not match.empty:
                    id_f = str(match.iloc[0][0]).strip()
                    nombre_f = f"Certificado.{MAPA_MESES[mes_pdf]}{anio_global}.pdf"
                    r = requests.get(URL_APPS_SCRIPT, params={"nombre": nombre_f, "carpeta": id_f})
                    if r.text.startswith("http"):
                        st.success("✅ Certificado Encontrado")
                        st.link_button("📥 Descargar Archivo", r.text.strip())
                    else: st.error("No disponible en Drive.")

        with col_p:
            pie_data = df_es[cols_m_sidebar].stack().value_counts().reset_index()
            pie_data.columns = ['Cod', 'Cant']; pie_data['Estado'] = pie_data['Cod'].map(MAPA_ESTADOS)
            st.plotly_chart(px.pie(pie_data, values='Cant', names='Estado', hole=.4, 
                                  color='Estado', color_discrete_map=COLORES_ESTADOS, title=f"Estatus Anual: {emp_sel}"), use_container_width=True)
            
            st.write("#### 📜 Historial Mensual")
            hist = df_es[cols_m_sidebar].T.reset_index()
            hist.columns = ['Mes', 'Cod']; hist['Estado'] = hist['Cod'].map(MAPA_ESTADOS)
            st.dataframe(hist[['Mes', 'Estado']], use_container_width=True)

# --- TAB: MASA LABORAL ---
idx_masa = tab_list.index("👥 Masa Laboral") if "👥 Masa Laboral" in tab_list else tab_list.index("👥 Masa Colaboradores")
with tabs[idx_masa]:
    st.header(f"Dotación de Personal - {anio_global}")
    mes_m = st.selectbox("Mes Masa:", list(MAPA_MESES.keys()), key="m_masa")
    df_m = cargar_datos(ID_COLABORADORES, f"{mes_m.capitalize()}{anio_global[-2:]}")
    if not df_m.empty:
        col_rs = next((c for c in df_m.columns if 'RAZON' in c), df_m.columns[0])
        df_mf = df_m[df_m[col_rs] == st.session_state["u_emp"]] if rol == "USUARIO" else df_m
        col_c = next((c for c in df_mf.columns if 'CONTRATO' in c), None)
        if col_c:
            pf = df_mf[df_mf[col_c].str.contains("PLAZO FIJO", case=False, na=False)]
            if not pf.empty: st.warning(f"🚨 Alerta: Se detectaron {len(pf)} contratos a Plazo Fijo.")
        st.dataframe(df_mf, use_container_width=True)

# --- TAB: CARGA ---
idx_carga = tab_list.index("📤 Carga") if "📤 Carga" in tab_list else tab_list.index("📤 Carga de Documentos")
with tabs[idx_carga]:
    st.header("📤 Pasarela de Carga")
    if mes_sidebar == "AÑO COMPLETO": st.warning("Seleccione un mes en el panel lateral.")
    else:
        empresa_up = st.session_state['u_emp'] if rol == "USUARIO" else st.selectbox("Empresa Destino:", sorted(df_av[col_e].unique()), key="emp_up")
        docs = [("Liquidaciones", "LIQ"), ("Previred", "PREVIRED"), ("F30", "F30"), ("F30-1", "F30_1"), ("Pagos", "PAGOS")]
        for n, p in docs:
            c1, c2 = st.columns([3, 1])
            arch = c1.file_uploader(f"Subir {n}", type=["pdf"], key=f"f_{p}")
            if c2.button(f"🚀 Cargar {p}", key=f"b_{p}"):
                if arch:
                    match_u = df_id[df_id.iloc[:,1].str.contains(empresa_up[:10], case=False, na=False)]
                    if not match_u.empty:
                        id_f_up = str(match_u.iloc[0][0]).strip()
                        payload = {
                            "nombre_final": f"{p}_{mes_sidebar}_{anio_global}_{empresa_up[:10]}.pdf",
                            "id_carpeta": id_f_up, "anio": anio_global, "mes_nombre": MAPA_MESES_CARPETAS[mes_sidebar],
                            "mimetype": "application/pdf", "archivo_base64": base64.b64encode(arch.read()).decode('utf-8')
                        }
                        with st.spinner("Subiendo..."):
                            r = requests.post(URL_APPS_SCRIPT, data=payload)
                            if "✅" in r.text or "Exito" in r.text: st.success("¡Cargado!"); st.balloons()
                else: st.warning("Seleccione archivo.")
        
        st.divider()
        if st.button("🏁 FINALIZAR Y NOTIFICAR", use_container_width=True):
            p_e = {"accion": "enviar_email", "empresa": empresa_up, "usuario": st.session_state["u_nom"], "periodo": f"{mes_sidebar} {anio_global}", "email_usuario": st.session_state["u_email"]}
            with st.spinner("Enviando aviso..."):
                r = requests.post(URL_APPS_SCRIPT, data=p_e)
                if "✅" in r.text: st.success("¡Notificación enviada!"); st.balloons()

st.markdown("---")
st.caption("CMSG | C&S Asociados Ltda.")