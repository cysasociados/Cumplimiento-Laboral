import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import base64
import re
import os
from datetime import datetime
import pytz

# ==========================================
# 1. CONFIGURACIÓN Y CONEXIONES
# ==========================================
st.set_page_config(page_title="Control de Cumplimiento Laboral CMSG", layout="wide", page_icon="🛡️")
chile_tz = pytz.timezone('America/Santiago')

URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbwt9t5vQBsijY4eI9yF-sI82ctU5HGuW8xE2WVPwUBjOvaqGSGh7bi1DZaazU7NQEavfA/exec"

ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"

MAPA_ESTADOS = {1:"Carga Doc.", 2:"En Revision", 3:"Observado", 4:"No Cumple", 5:"Cumple", 8:"Sin Info", 9:"No Corresp."}
COLORES_ESTADOS = {"Cumple":"#00FF00", "No Cumple":"#FF0000", "Observado":"#FFFF00", "En Revision":"#1E90FF", "Carga Doc.":"#FF8C00", "Sin Info":"#555555", "No Corresp.":"#8B4513"}
MESES_LISTA = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC']
MAPA_MESES_NUM = {'ENE':'01','FEB':'02','MAR':'03','ABR':'04','MAY':'05','JUN':'06','JUL':'07','AGO':'08','SEP':'09','OCT':'10','NOV':'11','DIC':'12'}
MAPA_MESES_CARP = {'ENE':'01_ENE','FEB':'02_FEB','MAR':'03_MAR','ABR':'04_ABR','MAY':'05_MAY','JUN':'06_JUN','JUL':'07_JUL','AGO':'08_AGO','SEP':'09_SEP','OCT':'10_OCT','NOV':'11_NOV','DIC':'12_DIC'}

def validar_rut(rut):
    rut = rut.replace(".", "").replace("-", "").upper()
    if not re.match(r"^\d{7,8}[0-9K]$", rut): return False
    cuerpo, dv = rut[:-1], rut[-1]
    suma = 0
    multiplo = 2
    for c in reversed(cuerpo):
        suma += int(c) * multiplo
        multiplo = 2 if multiplo == 7 else multiplo + 1
    dvr = 11 - (suma % 11)
    dvr = 'K' if dvr == 10 else '0' if dvr == 11 else str(dvr)
    return dv == dvr

@st.cache_data(ttl=15)
def cargar_datos(sheet_id, p):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={p}"
        df = pd.read_csv(url, encoding='utf-8-sig')
        df.columns = [re.sub(r'[^A-Z0-9]', '', str(c).upper()) for c in df.columns]
        return df.dropna(how='all')
    except: return pd.DataFrame()

# 2. LOGIN
if "authenticated" not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if os.path.exists("CMSG.png"): st.image("CMSG.png", width=220)
        st.title("Control Laboral CMSG")
        pwd = st.text_input("Contraseña Corporativa:", type="password").strip()
        if st.button("Ingresar", use_container_width=True):
            df_u = cargar_datos(ID_USUARIOS, "Usuarios")
            if not df_u.empty:
                col_c = next((c for c in df_u.columns if 'CLAVE' in str(c).upper()), 'CLAVE')
                match = df_u[df_u[col_clave].astype(str).str.strip() == pwd]
                if not match.empty:
                    u = match.iloc[0]; n_u = u.get('NOMBRE','')
                    st.success(f"Bienvenido(a), {n_u}")
                    st.session_state.update({"authenticated": True, "u_nom": n_u, "u_rol": u.get('ROL',''), "u_emp": u.get('EMPRESA',''), "u_email": u.get('EMAIL','')})
                    st.rerun()
                else: st.error("Contraseña incorrecta.")
    st.stop()

# 3. SIDEBAR
with st.sidebar:
    if os.path.exists("CMSG.png"): st.image("CMSG.png", use_container_width=True)
    st.markdown(f"👤 **{st.session_state['u_nom']}**\n🏢 **{st.session_state['u_emp']}**")
    st.markdown("---")
    anio_global = st.selectbox("Año de Gestión", ["2026", "2025"])
    df_av = cargar_datos(ID_AVANCE, anio_global)
    cols_m = [c for c in df_av.columns if c in MESES_LISTA] if not df_av.empty else []
    mes_sidebar = st.selectbox("Mes de Análisis", ["AÑO COMPLETO"] + cols_m)
    if st.button("Cerrar Sesión", use_container_width=True):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# 4. TABS (RENOMBRADAS)
rol = st.session_state["u_rol"]
tab_list = ["📉 Dashboard", "📊 KPIS EMPRESAS", "📤 Carga Mensual", "👥 DOTACION"]
if rol != "USUARIO": tab_list.append("⚙️ Admin")
tabs = st.tabs(tab_list)

# --- TAB 1: DASHBOARD ---
with tabs[0]:
    df_id_empresas = cargar_datos(ID_EMPRESAS, "HOJA1")
    if not df_av.empty:
        col_e = next((c for c in df_av.columns if 'EMP' in str(c).upper()), 'EMPRESA')
        df_f = df_av[df_av[col_e] == st.session_state["u_emp"]] if rol == "USUARIO" else df_av
        c_filt = [mes_sidebar] if mes_sidebar != "AÑO COMPLETO" else cols_m
        df_num = df_f[c_filt].apply(pd.to_numeric, errors='coerce')
        df_audit = df_num.copy(); df_audit[df_audit == 9] = pd.NA
        t_p = df_audit.count().sum(); t_5 = (df_audit == 5).sum().sum()
        perc = (t_5 / t_p * 100) if t_p > 0 else 0
        st.header(f"Seguimiento Laboral - {mes_sidebar} {anio_global}")
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas", len(df_f)); k2.metric("% Cumplimiento", f"{perc:.1f}%"); k3.metric("Al Día", int(df_audit.apply(lambda x: x.dropna().eq(5).all() if x.dropna().size > 0 else False, axis=1).sum() if mes_sidebar == "AÑO COMPLETO" else (df_audit == 5).sum().sum()))
        if mes_sidebar == "AÑO COMPLETO":
            st.divider(); st.write("### 📈 Evolución Mensual")
            res_evo = []
            for m in cols_m:
                counts_m = df_f[m].value_counts()
                for cod, cant in counts_m.items():
                    if pd.notna(cod): res_evo.append({'Mes': m, 'Estado': MAPA_ESTADOS.get(int(cod), "S/I"), 'Cantidad': cant})
            if res_evo: st.plotly_chart(px.bar(pd.DataFrame(res_evo), x='Mes', y='Cantidad', color='Estado', color_discrete_map=COLORES_ESTADOS, barmode='stack'), use_container_width=True)
        st.divider(); emp_sel = st.selectbox("Empresa para Detalle:", sorted(df_f[col_e].unique())); df_es = df_f[df_f[col_e] == emp_sel]
        c_iz, c_de = st.columns([3, 1.2])
        with c_iz:
            p_d = df_es[cols_m].stack().value_counts().reset_index(); p_d.columns = ['Cod', 'Cant']; p_d['Estado'] = p_d['Cod'].map(MAPA_ESTADOS)
            st.plotly_chart(px.pie(p_d[p_d['Cod'] != 9], values='Cant', names='Estado', hole=.4, color='Estado', color_discrete_map=COLORES_ESTADOS, title=f"Estatus: {emp_sel}"), use_container_width=True)
            st.write("#### 📜 Historial Mensual"); m1, m2 = cols_m[:6], cols_m[6:]
            def draw_grid_c(l):
                cs = st.columns(6)
                for i, m in enumerate(l):
                    v = int(df_es[m].values[0]) if pd.notna(df_es[m].values[0]) else 8
                    t = MAPA_ESTADOS.get(v, "S/I"); b = COLORES_ESTADOS.get(t, "#555555"); tc = "#000000" if t in ["Observado", "Cumple", "En Revision"] else "#FFFFFF"
                    cs[i].markdown(f"<div style='text-align:center; border:1px solid #ddd; padding:8px; border-radius:8px; background-color:{b}; color:{tc}; min-height:65px; display:flex; flex-direction:column; justify-content:center;'><b style='font-size:11px;'>{m}</b><br><span style='font-size:8px; font-weight:bold;'>{t.upper()}</span></div>", unsafe_allow_html=True)
            draw_grid_c(m1); st.write(""); draw_grid_c(m2)
        with c_de:
            st.subheader("📄 Certificado")
            m_pdf = st.selectbox("Mes PDF:", cols_m, key="s_pdf_dash")
            if st.button("Obtener PDF", use_container_width=True):
                match_id = df_id_empresas[df_id_empresas['EMPRESA'].str.contains(emp_sel[:10], case=False, na=False)]
                if not match_id.empty:
                    id_f = str(match_id.iloc[0]['IDCARPETA']).strip(); n_f = f"Certificado.{MAPA_MESES_NUM[m_pdf]}{anio_global}.pdf"
                    r = requests.get(URL_APPS_SCRIPT, params={"nombre": n_f, "carpeta": id_f})
                    if r.text.startswith("http"): st.session_state["link_descarga"] = r.text.strip()
                    else: st.error("No disponible.")
            if "link_descarga" in st.session_state: st.link_button("📥 Descargar", st.session_state["link_descarga"], use_container_width=True)

# --- TAB 2: KPIS EMPRESAS ---
with tabs[1]:
    st.header(f"📊 Reporte de Dotación por Empresa - {anio_global}")
    mes_kpi = st.selectbox("Mes Visualización:", MESES_LISTA, key="m_kpi_v")
    df_k = cargar_datos(ID_COLABORADORES, f"{mes_kpi.capitalize()}{anio_global[-2:]}")
    if not df_k.empty:
        c_rs = next((c for c in df_k.columns if 'RAZON' in str(c).upper()), df_k.columns[0])
        st.dataframe(df_k[df_k[c_rs] == st.session_state["u_emp"]] if rol == "USUARIO" else df_k, use_container_width=True)

# --- TAB 3: CARGA MENSUAL (CON LIMITE 20MB) ---
with tabs[2]:
    st.header("📤 Carga de Documentación Mensual")
    if mes_sidebar == "AÑO COMPLETO": st.warning("Seleccione un Mes en el sidebar.")
    else:
        col_m_inp, col_m_inst = st.columns([1.7, 1.3])
        with col_m_inst:
            st.markdown(f"""
            <div style='background-color:#fefefe; padding:18px; border-radius:12px; border: 1px solid #ddd; border-left: 8px solid #FF8C00;'>
            <h4 style='margin-top:0; color:#222;'>📖 Instrucciones de Carga</h4>
            <p style='font-size:14px; color:#d9534f;'><b>⚠️ MAXIMO 20MB POR ARCHIVO.</b></p>
            <ul style='font-size:14px; padding-left:18px; line-height:1.6; color:#222;'>
                <li><b>Liquidaciones:</b> PDF único con todos los trabajadores.</li>
                <li><b>Pagos/Anticipos:</b> PDF único con todos los comprobantes.</li>
                <li><b>Cotizaciones:</b> Planillas de pago (Previred).</li>
                <li><b>Libro Auxiliar:</b> Archivo CSV (el enviado a la DT).</li>
                <li><b>Comprobante DT:</b> Certificado envío libro remuneraciones.</li>
                <li><b>F30:</b> Certificado actualizado (máx. 30 días).</li>
                <li><b>F30-1:</b> Solo personal asignado a CMSG.</li>
                <li><b>Planilla Control:</b> Archivo .XLS del mes en curso.</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)
        with col_m_inp:
            emp_u = st.session_state['u_emp'] if rol == "USUARIO" else st.selectbox("Empresa:", sorted(df_av[col_e].unique()), key="up_m_sel")
            st.divider()
            m_docs = [("Liquidaciones Sueldo", "LIQ", ["pdf"]),("Comprobantes Pago", "PAGOS", ["pdf"]),("Cotizaciones", "PREVIRED", ["pdf"]),("Libro Remuneraciones (CSV)", "LIBRO", ["csv"]),("Comprobante DT", "DT_COMP", ["pdf"]),("Certificado F30", "F30", ["pdf"]),("Certificado F30-1", "F30_1", ["pdf"]),("Planilla Control (.XLS)", "CONTROL", ["xlsx", "xls"])]
            for n, p, e in m_docs:
                cf, cb, cs = st.columns([4, 2, 0.5])
                with cf: a = st.file_uploader(f"Subir {n} (Máx 20MB)", type=e, key=f"m_{p}")
                with cb:
                    st.write("##")
                    if st.button("Subir", key=f"bm_{p}", use_container_width=True):
                        if a:
                            if a.size > 20 * 1024 * 1024: st.error("⚠️ Archivo excede los 20MB.")
                            else:
                                mt = df_id_empresas[df_id_empresas['EMPRESA'].str.contains(emp_u[:10], case=False, na=False)]
                                if not mt.empty:
                                    id_f = str(mt.iloc[0]['IDCARPETA']).strip(); ext = a.name.split('.')[-1]
                                    payload = {"tipo":"mensual","id_carpeta":id_f,"anio":anio_global,"nombre_final":f"{p}_{mes_sidebar}_{anio_global}_{emp_u[:10]}.{ext}","mes_nombre":MAPA_MESES_CARP[mes_sidebar],"mimetype":"application/pdf" if ext=="pdf" else "text/csv" if ext=="csv" else "application/vnd.ms-excel","archivo_base64":base64.b64encode(a.read()).decode('utf-8')}
                                    r = requests.post(URL_APPS_SCRIPT, data=payload)
                                    if r.status_code == 200: st.success("Cargado correctamente.")
                        else: st.warning("Falta archivo.")

# --- TAB 4: DOTACION (ALTAS/BAJAS Y LIMITE 20MB) ---
with tabs[3]:
    st.header("👥 Gestión de Dotación (Altas y Bajas)")
    acc_dot = st.radio("Acción:", ["🟢 Alta (Ingreso)", "🔴 Baja (Egreso)"], horizontal=True)
    st.divider()
    col_d_inp, col_d_inst = st.columns([1.7, 1.3])
    with col_d_inst:
        color_b = "#1E90FF" if "Alta" in acc_dot else "#d9534f"
        txt_d = "<li>Contrato / Anexo</li><li>Cédula Identidad</li><li>Cert. AFP/Salud</li>" if "Alta" in acc_dot else "<li>Finiquito Firmado</li><li>Anexo Traslado</li>"
        st.markdown(f"""
        <div style='background-color:#fefefe; padding:18px; border-radius:12px; border: 1px solid #ddd; border-left: 8px solid {color_b};'>
        <h4 style='margin-top:0;'>📌 Requisitos</h4>
        <p style='font-size:14px; color:#d9534f;'><b>⚠️ MAXIMO 20MB POR ARCHIVO.</b></p>
        <ul style='font-size:14px; padding-left:20px; line-height:1.6; color:#222;'>{txt_d}</ul>
        </div>
        """, unsafe_allow_html=True)
    with col_d_inp:
        emp_c = st.session_state['u_emp'] if rol == "USUARIO" else st.selectbox("Empresa:", sorted(df_av[col_e].unique()), key="c_up_dot")
        ci1, ci2 = st.columns(2)
        with ci1: n_nom = st.text_input("Nombre Trabajador:", placeholder="JUAN PEREZ")
        with ci2: 
            r_rut = st.text_input("RUT (ej: 12345678-9):", placeholder="12345678-9")
            r_ok = False
            if r_rut:
                if validar_rut(r_rut): st.caption("✅ RUT Válido"); r_ok = True
                else: st.caption("❌ RUT Inválido")
        st.divider()
        if "Alta" in acc_dot:
            f_in = st.file_uploader("Documentos de Ingreso (Máx 20MB):", type=["pdf"], accept_multiple_files=True, key="bulk_in")
            if f_in and n_nom and r_ok:
                if st.button("Subir Alta", use_container_width=True):
                    if any(f.size > 20*1024*1024 for f in f_in): st.error("⚠️ Uno o más archivos exceden 20MB.")
                    else:
                        mt = df_id_empresas[df_id_empresas['EMPRESA'].str.contains(emp_c[:10], case=False, na=False)]
                        if not mt.empty:
                            id_f = str(mt.iloc[0]['IDCARPETA']).strip()
                            for f in f_in:
                                payload = {"tipo":"colaborador","id_carpeta":id_f,"nombre_persona":n_nom.upper(),"rut":r_rut,"nombre_final":f.name,"mimetype":"application/pdf","archivo_base64":base64.b64encode(f.read()).decode('utf-8')}
                                requests.post(URL_APPS_SCRIPT, data=payload)
                            st.success("Alta procesada.")
        else:
            t_baja = st.selectbox("Tipo Documento:", ["FINIQUITO", "ANEXO_TRASLADO"])
            f_out = st.file_uploader(f"Subir {t_baja} (Máx 20MB):", type=["pdf"], key="f_baja")
            if f_out and n_nom and r_ok:
                if st.button("Subir Baja", use_container_width=True):
                    if f_out.size > 20*1024*1024: st.error("⚠️ Archivo excede los 20MB.")
                    else:
                        mt = df_id_empresas[df_id_empresas['EMPRESA'].str.contains(emp_c[:10], case=False, na=False)]
                        if not mt.empty:
                            id_f = str(mt.iloc[0]['IDCARPETA']).strip()
                            payload = {"tipo":"colaborador","id_carpeta":id_f,"nombre_persona":n_nom.upper(),"rut":r_rut,"nombre_final":f"{t_baja}_{r_rut}.pdf","mimetype":"application/pdf","archivo_base64":base64.b64encode(f_out.read()).decode('utf-8')}
                            requests.post(URL_APPS_SCRIPT, data=payload)
                            st.success("Baja procesada.")

st.markdown("---")
st.caption("Control Laboral CMSG | Desarrollado por C & S Asociados Ltda.")