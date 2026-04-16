import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import base64
import re
import os
from datetime import datetime
import pytz

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")
chile_tz = pytz.timezone('America/Santiago')

# --- CABECERA CON LOGOS ---
col_l, col_m, col_r = st.columns([2, 4, 1])
with col_l:
    if os.path.exists("CMSG.png"): st.image("CMSG.png", width=250)
    else: st.subheader("🏢 Minera San Gerónimo")
with col_r:
    if os.path.exists("cys.png"): st.image("cys.png", width=120)
    else: st.write("**C&S Asociados**")

# --- CONEXIÓN (IMPORTANTE: Verifica tu URL de Apps Script) ---
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbxbH7GCm95Eh0DMkBCNVD9Ce-lywoCqmUC_DraHw7DopQPeIOJ5XamcqHvf0dyBFtw/exec"

ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"

# MAPAS DE CONFIGURACIÓN
MAPA_ESTADOS = {1:"Carga Doc.", 2:"En Revision", 3:"Observado", 4:"No Cumple", 5:"Cumple", 8:"Sin Info", 9:"No Corresp."}
COLORES_ESTADOS = {"Cumple":"#00FF00", "No Cumple":"#FF0000", "Observado":"#FFFF00", "En Revision":"#1E90FF", "Carga Doc.":"#FF8C00", "Sin Info":"#555555", "No Corresp.":"#8B4513"}
MAPA_MESES_NUM = {'ENE':'01','FEB':'02','MAR':'03','ABR':'04','MAY':'05','JUN':'06','JUL':'07','AGO':'08','SEP':'09','OCT':'10','NOV':'11','DIC':'12'}
MAPA_MESES_CARPETAS = {'ENE':'01_ENE','FEB':'02_FEB','MAR':'03_MAR','ABR':'04_ABR','MAY':'05_MAY','JUN':'06_JUN','JUL':'07_JUL','AGO':'08_AGO','SEP':'09_SEP','OCT':'10_OCT','NOV':'11_NOV','DIC':'12_DIC'}

if "log_accesos" not in st.session_state:
    st.session_state["log_accesos"] = []

@st.cache_data(ttl=15)
def cargar_datos(sheet_id, p):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={p}"
        df = pd.read_csv(url, encoding='utf-8-sig')
        df.columns = [re.sub(r'[^A-Z0-9]', '', str(c).upper()) for c in df.columns]
        return df.dropna(how='all')
    except: return pd.DataFrame()

# --- 2. SISTEMA DE LOGIN ---
if "authenticated" not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.title("🔐 Acceso Control Laboral CMSG")
        pwd = st.text_input("Contraseña:", type="password").strip()
        if st.button("Ingresar", use_container_width=True):
            df_u = cargar_datos(ID_USUARIOS, "Usuarios")
            col_c = next((c for c in df_u.columns if 'CLAVE' in str(c).upper()), 'CLAVE')
            match = df_u[df_u[col_c].astype(str).str.strip() == pwd]
            if not match.empty:
                u = match.iloc[0]
                ahora = datetime.now(chile_tz)
                st.session_state["log_accesos"].append({
                    "Fecha": ahora.strftime("%d/%m/%Y"), "Hora": ahora.strftime("%H:%M:%S"),
                    "Usuario": u.get('NOMBRE',''), "Empresa": u.get('EMPRESA',''), "Rol": u.get('ROL','')
                })
                st.session_state.update({"authenticated": True, "u_nom": u.get('NOMBRE',''), "u_rol": u.get('ROL',''), "u_emp": u.get('EMPRESA',''), "u_email": u.get('EMAIL','')})
                st.rerun()
            else: st.error("❌ Clave no válida.")
    st.stop()

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuración")
    anio_global = st.selectbox("Año de Análisis", ["2026", "2025"])
    df_av = cargar_datos(ID_AVANCE, anio_global)
    cols_meses = [c for c in df_av.columns if c in MAPA_MESES_NUM.keys()] if not df_av.empty else []
    mes_sidebar = st.selectbox("Mes de Análisis", ["AÑO COMPLETO"] + cols_meses)
    st.divider()
    st.write(f"👤 **{st.session_state['u_nom']}**")
    if st.button("Cerrar Sesión"):
        del st.session_state["authenticated"]
        st.rerun()

# --- 4. TABS ---
rol = st.session_state["u_rol"]
tab_list = ["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Colaboradores", "⚙️ Admin"] if rol == "ADMIN" else ["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Colaboradores"]
if rol == "USUARIO": tab_list = ["📈 Mi Avance", "👥 Masa Laboral", "📤 Carga de Documentos"]
tabs = st.tabs(tab_list)

# --- TAB 0: AVANCE + CARGA + DESCARGA ---
with tabs[0]:
    df_id = cargar_datos(ID_EMPRESAS, "HOJA1")
    if not df_av.empty:
        col_e = next((c for c in df_av.columns if 'EMP' in str(c).upper()), 'EMPRESA')
        df_f = df_av[df_av[col_e] == st.session_state["u_emp"]] if rol == "USUARIO" else df_av
        cols_filtro = [mes_sidebar] if mes_sidebar != "AÑO COMPLETO" else cols_meses
        df_num = df_f[cols_filtro].apply(pd.to_numeric, errors='coerce')

        # --- KPIs (Excluyendo Estado 9) ---
        df_calc = df_num[df_num != 9]
        t_p = df_calc.count().sum()
        t_5 = (df_calc == 5).sum().sum()
        perc = (t_5 / t_p * 100) if t_p > 0 else 0

        st.header(f"Gestión Laboral CMSG - {mes_sidebar} {anio_global}")
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas", len(df_f))
        k2.metric("% Cumplimiento Real", f"{perc:.1f}%")
        k3.metric("Al Día (100%)", (df_calc == 5).all(axis=1).sum() if mes_sidebar == "AÑO COMPLETO" else "N/A")

        # Fila de contadores por estado
        st.write("### 📊 Periodos por Estado")
        counts = df_num.stack().value_counts()
        m_cols = st.columns(len(MAPA_ESTADOS))
        for i, (code, name) in enumerate(MAPA_ESTADOS.items()):
            m_cols[i].metric(name, int(counts.get(code, 0)))

        # Gráfico evolutivo (v.6)
        if rol != "USUARIO" and mes_sidebar == "AÑO COMPLETO":
            res_evo = []
            for m in cols_meses:
                for cod, cant in df_f[m].value_counts().items():
                    if pd.notna(cod): res_evo.append({'Mes': m, 'Estado': MAPA_ESTADOS.get(int(cod), "S/I"), 'Cantidad': cant})
            if res_evo: st.plotly_chart(px.bar(pd.DataFrame(res_evo), x='Mes', y='Cantidad', color='Estado', color_discrete_map=COLORES_ESTADOS, barmode='stack'), use_container_width=True)

        st.divider()
        # --- ANÁLISIS POR EMPRESA Y DESCARGA (v.6) ---
        st.subheader("🎯 Detalle por Empresa y Certificados")
        emp_sel = st.selectbox("Seleccione Empresa:", sorted(df_f[col_e].unique()))
        df_es = df_f[df_f[col_e] == emp_sel]
        
        c_pie, c_hist, c_btn = st.columns([1.5, 1.5, 1])
        with c_pie:
            pie_d = df_es[cols_meses].stack().value_counts().reset_index()
            pie_d.columns = ['Cod', 'Cant']; pie_d['Estado'] = pie_d['Cod'].map(MAPA_ESTADOS)
            st.plotly_chart(px.pie(pie_d, values='Cant', names='Estado', hole=.4, color='Estado', color_discrete_map=COLORES_ESTADOS), use_container_width=True)
        with c_hist:
            hist = df_es[cols_meses].T.reset_index()
            hist.columns = ['Mes', 'Cod']; hist['Estado'] = hist['Cod'].map(MAPA_ESTADOS)
            st.dataframe(hist[['Mes', 'Estado']], use_container_width=True, height=250)
        with c_btn:
            m_pdf = st.selectbox("Mes Certificado:", cols_meses)
            if st.button(f"🔍 Descargar PDF {m_pdf}"):
                match = df_id[df_id.iloc[:,1].str.contains(emp_sel[:10], case=False, na=False)]
                if not match.empty:
                    col_id_f = next((c for c in df_id.columns if 'ID' in str(c).upper() or 'CARPETA' in str(c).upper()), 'IDCARPETA')
                    id_f = str(match.iloc[0][col_id_f]).strip()
                    nombre_f = f"Certificado.{MAPA_MESES_NUM[m_pdf]}{anio_global}.pdf"
                    r = requests.get(URL_APPS_SCRIPT, params={"nombre": nombre_f, "carpeta": id_f})
                    if r.text.startswith("http"): st.link_button("📥 Descargar", r.text.strip())
                    else: st.error("No disponible.")

        # --- PASARELA DE CARGA (v.7) ---
        st.divider()
        with st.expander("📤 PASARELA DE CARGA DE DOCUMENTOS"):
            if mes_sidebar == "AÑO COMPLETO": st.warning("Seleccione un mes en el panel lateral.")
            else:
                emp_up = st.session_state['u_emp'] if rol == "USUARIO" else st.selectbox("Empresa para Carga:", sorted(df_f[col_e].unique()))
                docs = [("Liquidaciones", "LIQ"), ("Previred", "PREVIRED"), ("F30", "F30"), ("F30-1", "F30_1"), ("Pagos", "PAGOS")]
                for n, p in docs:
                    c_f, c_b = st.columns([3, 1])
                    arch = c_f.file_uploader(f"Subir {n}", type=["pdf"], key=f"u_{p}")
                    if c_b.button(f"🚀 Cargar {p}", key=f"b_{p}"):
                        if arch:
                            match_up = df_id[df_id.iloc[:,1].str.contains(emp_up[:10], case=False, na=False)]
                            if not match_up.empty:
                                id_f_up = str(match_up.iloc[0][0]).strip()
                                payload = {"nombre_final": f"{p}_{mes_sidebar}_{anio_global}_{emp_up[:10]}.pdf", "id_carpeta": id_f_up, "anio": anio_global, "mes_nombre": MAPA_MESES_CARPETAS[mes_sidebar], "mimetype": "application/pdf", "archivo_base64": base64.b64encode(arch.read()).decode('utf-8')}
                                with st.spinner("Subiendo..."):
                                    r = requests.post(URL_APPS_SCRIPT, data=payload)
                                    if "✅" in r.text or "Exito" in r.text: st.success("¡Cargado!"); st.balloons()
                st.divider()
                if st.button("🏁 FINALIZAR Y NOTIFICAR", use_container_width=True):
                    p_e = {"accion": "enviar_email", "empresa": emp_up, "usuario": st.session_state["u_nom"], "periodo": f"{mes_sidebar} {anio_global}", "email_usuario": st.session_state["u_email"]}
                    requests.post(URL_APPS_SCRIPT, data=p_e); st.success("Notificado!")

# --- TAB 2: MASA LABORAL (ALERTAS v.6) ---
idx_masa = 1 if rol == "USUARIO" else 2
with tabs[idx_masa]:
    st.header(f"Análisis de Dotación - {anio_global}")
    mes_m = st.selectbox("Mes Masa:", list(MAPA_MESES_NUM.keys()))
    df_masa = cargar_datos(ID_COLABORADORES, f"{mes_m.capitalize()}{anio_global[-2:]}")
    if not df_masa.empty:
        col_rs = next((c for c in df_masa.columns if 'RAZON' in str(c).upper()), df_masa.columns[0])
        df_mf = df_masa[df_masa[col_rs] == st.session_state["u_emp"]] if rol == "USUARIO" else df_masa
        
        st.subheader("🚨 Alertas de Estabilidad")
        col_c = next((c for c in df_mf.columns if 'CONTRATO' in str(c).upper()), None)
        if col_c:
            pf = df_mf[df_mf[col_c].str.contains("PLAZO FIJO", case=False, na=False)]
            if not pf.empty:
                st.warning(f"Se detectaron {len(pf)} contratos a Plazo Fijo.")
                st.dataframe(pf, use_container_width=True)
            else: st.success("✅ Todo el personal tiene contrato Indefinido.")
        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("Dotación Total", len(df_mf))
        if 'NACIONALIDAD' in df_mf.columns:
            ext = len(df_mf[~df_mf['NACIONALIDAD'].str.contains('CHILE', na=False)])
            m2.metric("Extranjeros", ext)
        if 'TOTALHORASEXTRA' in df_mf.columns:
            m3.metric("HH.EE Mes", f"{pd.to_numeric(df_mf['TOTALHORASEXTRA'], errors='coerce').sum():,.0f}")
        st.dataframe(df_mf, use_container_width=True)

# --- TAB ADMIN ---
if rol == "ADMIN":
    with tabs[-1]:
        st.header("⚙️ Administración")
        if st.session_state["log_accesos"]: st.table(pd.DataFrame(st.session_state["log_accesos"]))
        st.divider()
        st.dataframe(cargar_datos(ID_USUARIOS, "Usuarios"), use_container_width=True)

st.markdown("---")
st.caption("CMSG | C&S Asociados Ltda.")