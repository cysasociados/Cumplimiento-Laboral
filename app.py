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
# 1. CONFIGURACIÓN Y CONEXIONES CORPORATIVAS
# ==========================================
st.set_page_config(page_title="Control de Cumplimiento Laboral CMSG", layout="wide", page_icon="🛡️")
chile_tz = pytz.timezone('America/Santiago')

# URL PROPORCIONADA ACTUALIZADA
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbwt9t5vQBsijY4eI9yF-sI82ctU5HGuW8xE2WVPwUBjOvaqGSGh7bi1DZaazU7NQEavfA/exec"

# IDS DE LAS HOJAS DE GOOGLE DRIVE
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"

# MAPEOS DE ESTADOS Y COLORES
MAPA_ESTADOS = {1:"Carga Doc.", 2:"En Revision", 3:"Observado", 4:"No Cumple", 5:"Cumple", 8:"Sin Info", 9:"No Corresp."}
COLORES_ESTADOS = {"Cumple":"#00FF00", "No Cumple":"#FF0000", "Observado":"#FFFF00", "En Revision":"#1E90FF", "Carga Doc.":"#FF8C00", "Sin Info":"#555555", "No Corresp.":"#8B4513"}
MESES_LISTA = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC']
MAPA_MESES_NUM = {'ENE':'01','FEB':'02','MAR':'03','ABR':'04','MAY':'05','JUN':'06','JUL':'07','AGO':'08','SEP':'09','OCT':'10','NOV':'11','DIC':'12'}
MAPA_MESES_CARP = {'ENE':'01_ENE','FEB':'02_FEB','MAR':'03_MAR','ABR':'04_ABR','MAY':'05_MAY','JUN':'06_JUN','JUL':'07_JUL','AGO':'08_AGO','SEP':'09_SEP','OCT':'10_OCT','NOV':'11_NOV','DIC':'12_DIC'}

# --- FUNCIÓN: VALIDACIÓN MATEMÁTICA DE RUT ---
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

# ==========================================
# 2. CONTROL DE ACCESO (LOGIN)
# ==========================================
if "authenticated" not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if os.path.exists("CMSG.png"): st.image("CMSG.png", width=220)
        st.title("Control Laboral CMSG")
        pwd = st.text_input("Contraseña Corporativa:", type="password").strip()
        if st.button("Ingresar al Portal", use_container_width=True):
            df_u = cargar_datos(ID_USUARIOS, "Usuarios")
            if not df_u.empty:
                col_clave = next((c for c in df_u.columns if 'CLAVE' in str(c).upper()), 'CLAVE')
                match = df_u[df_u[col_clave].astype(str).str.strip() == pwd]
                if not match.empty:
                    u = match.iloc[0]; n_u = u.get('NOMBRE','')
                    st.success(f"Bienvenido(a), {n_u}")
                    st.session_state.update({"authenticated": True, "u_nom": n_u, "u_rol": u.get('ROL',''), "u_emp": u.get('EMPRESA',''), "u_email": u.get('EMAIL','')})
                    st.rerun()
                else: st.error("Contraseña incorrecta.")
    st.stop()

# ==========================================
# 3. SIDEBAR (FILTROS)
# ==========================================
with st.sidebar:
    if os.path.exists("CMSG.png"): st.image("CMSG.png", use_container_width=True)
    st.markdown(f"👤 **{st.session_state['u_nom']}**\n🏢 **{st.session_state['u_emp']}**")
    st.markdown("---")
    anio_global = st.selectbox("Año de Gestión", ["2026", "2025"])
    df_av = cargar_datos(ID_AVANCE, anio_global)
    cols_m = [c for c in df_av.columns if c in MESES_LISTA] if not df_av.empty else []
    mes_sidebar = st.selectbox("Mes de Análisis", ["AÑO COMPLETO"] + cols_m)
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# ==========================================
# 4. PESTAÑAS (TABS)
# ==========================================
rol = st.session_state["u_rol"]
tab_list = ["📈 Dashboard", "👥 Dotación", "📤 Carga Mensual", "👤 Ingreso Colaborador"]
if rol != "USUARIO": tab_list.append("⚙️ Admin")
tabs = st.tabs(tab_list)

# --- TAB 1: DASHBOARD (RESTAURADO) ---
with tabs[0]:
    df_id_empresas = cargar_datos(ID_EMPRESAS, "HOJA1")
    if not df_av.empty:
        col_e = next((c for c in df_av.columns if 'EMP' in str(c).upper()), 'EMPRESA')
        df_f = df_av[df_av[col_e] == st.session_state["u_emp"]] if rol == "USUARIO" else df_av
        c_filt = [mes_sidebar] if mes_sidebar != "AÑO COMPLETO" else cols_m
        
        # Matemática (Excluyendo Estado 9)
        df_num = df_f[c_filt].apply(pd.to_numeric, errors='coerce')
        df_audit = df_num.copy(); df_audit[df_audit == 9] = pd.NA
        t_p = df_audit.count().sum(); t_5 = (df_audit == 5).sum().sum()
        perc = (t_5 / t_p * 100) if t_p > 0 else 0
        
        st.header(f"Seguimiento Laboral - {mes_sidebar} {anio_global}")
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas", len(df_f))
        k2.metric("% Cumplimiento", f"{perc:.1f}%")
        k3.metric("Al Día", int(df_audit.apply(lambda x: x.dropna().eq(5).all() if x.dropna().size > 0 else False, axis=1).sum() if mes_sidebar == "AÑO COMPLETO" else (df_audit == 5).sum().sum()))

        # Metricas de Estados
        st.write("###")
        st_c = df_num.stack().value_counts(); m_cols_res = st.columns(len(MAPA_ESTADOS))
        for i, (code, name) in enumerate(MAPA_ESTADOS.items()):
            m_cols_res[i].metric(name, int(st_c.get(code, 0)))

        # --- GRÁFICO DE BARRAS EVOLUTIVO (RESTAURADO) ---
        if mes_sidebar == "AÑO COMPLETO":
            st.divider()
            st.write("### 📈 Evolución Mensual de Estados")
            res_evo = []
            for m in cols_m:
                counts_m = df_f[m].value_counts()
                for cod, cant in counts_m.items():
                    if pd.notna(cod):
                        res_evo.append({'Mes': m, 'Estado': MAPA_ESTADOS.get(int(cod), "S/I"), 'Cantidad': cant})
            if res_evo:
                st.plotly_chart(px.bar(pd.DataFrame(res_evo), x='Mes', y='Cantidad', color='Estado', color_discrete_map=COLORES_ESTADOS, barmode='stack'), use_container_width=True)

        st.divider()
        emp_sel = st.selectbox("Seleccione Empresa para Detalle:", sorted(df_f[col_e].unique()))
        df_es = df_f[df_f[col_e] == emp_sel]
        c_iz, c_de = st.columns([3, 1.2])

        with c_iz:
            # Gráfico Circular
            p_d = df_es[cols_m].stack().value_counts().reset_index(); p_d.columns = ['Cod', 'Cant']
            p_d['Estado'] = p_d['Cod'].map(MAPA_ESTADOS)
            st.plotly_chart(px.pie(p_d[p_d['Cod'] != 9], values='Cant', names='Estado', hole=.4, color='Estado', color_discrete_map=COLORES_ESTADOS, title=f"Estatus: {emp_sel}"), use_container_width=True)
            
            # Historial Cromático
            st.write("#### 📜 Historial Mensual")
            m1, m2 = cols_m[:6], cols_m[6:]
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
                    id_f = str(match_id.iloc[0]['IDCARPETA']).strip()
                    # --- CORRECCIÓN LÓGICA NOMBRE PDF (RESTAURADA) ---
                    n_f = f"Certificado.{MAPA_MESES_NUM[m_pdf]}{anio_global}.pdf"
                    r = requests.get(URL_APPS_SCRIPT, params={"nombre": n_f, "carpeta": id_f})
                    if r.text.startswith("http"): st.session_state["link_descarga"] = r.text.strip()
                    else: st.error("No disponible en Drive.")
            
            if "link_descarga" in st.session_state:
                st.link_button("📥 Descargar", st.session_state["link_descarga"], use_container_width=True)
            
            st.divider(); st.subheader("📝 Observaciones")
            col_o = next((c for c in df_av.columns if 'OBS' in str(c).upper()), None)
            if col_o and pd.notna(df_es.iloc[0][col_o]): st.warning(df_es.iloc[0][col_o])
            else: st.info("Sin observaciones.")

# --- TAB 2: DOTACIÓN ---
with tabs[1]:
    st.header(f"Personal Vigente - {anio_global}")
    mes_dot = st.selectbox("Mes:", MESES_LISTA, key="m_dot_view")
    df_m = cargar_datos(ID_COLABORADORES, f"{mes_dot.capitalize()}{anio_global[-2:]}")
    if not df_m.empty:
        c_rs = next((c for c in df_m.columns if 'RAZON' in str(c).upper()), df_m.columns[0])
        st.dataframe(df_m[df_m[c_rs] == st.session_state["u_emp"]] if rol == "USUARIO" else df_m, use_container_width=True)

# --- TAB 3: CARGA MENSUAL ---
with tabs[2]:
    st.header("📤 Carga de Documentación Mensual")
    if mes_sidebar == "AÑO COMPLETO": st.warning("Seleccione un Mes en el sidebar.")
    else:
        emp_u = st.session_state['u_emp'] if rol == "USUARIO" else st.selectbox("Empresa:", sorted(df_av[col_e].unique()), key="up_m")
        st.divider()
        m_docs = [("Liquidaciones", "LIQ", ["pdf"]), ("Previred", "PREVIRED", ["pdf"]), ("Cert. F30", "F30", ["pdf"]), ("Cert. F30-1", "F30_1", ["pdf"]), ("Compr. Pagos", "PAGOS", ["pdf"]), ("Planilla Control", "CONTROL", ["xlsx", "xls"])]
        for n, p, e in m_docs:
            cf, cb, cs = st.columns([4, 1.5, 4.5])
            with cf: a = st.file_uploader(f"Subir {n}", type=e, key=f"m_{p}")
            with cb:
                st.write("##")
                if st.button("Subir", key=f"bm_{p}", use_container_width=True):
                    if a:
                        mt = df_id_empresas[df_id_empresas['EMPRESA'].str.contains(emp_u[:10], case=False, na=False)]
                        if not mt.empty:
                            id_f = str(mt.iloc[0]['IDCARPETA']).strip(); ext = a.name.split('.')[-1]
                            payload = {"tipo":"mensual","id_carpeta":id_f,"anio":anio_global,"nombre_final":f"{p}_{mes_sidebar}_{anio_global}_{emp_u[:10]}.{ext}","mes_nombre":MAPA_MESES_CARP[mes_sidebar],"mimetype":"application/pdf" if ext=="pdf" else "application/vnd.ms-excel","archivo_base64":base64.b64encode(a.read()).decode('utf-8')}
                            r = requests.post(URL_APPS_SCRIPT, data=payload)
                            if r.status_code == 200: st.success("Cargado exitosamente.")
        st.divider()
        if "c_send" not in st.session_state: st.session_state.c_send = False
        if not st.session_state.c_send:
            if st.button("🏁 FINALIZAR Y NOTIFICAR CMSG", use_container_width=True): st.session_state.c_send = True; st.rerun()
        else:
            st.warning("⚠️ ¿Confirmar envío mensual de documentos?")
            c1, c2 = st.columns(2)
            if c1.button("✅ SÍ, ENVIAR", use_container_width=True):
                requests.post(URL_APPS_SCRIPT, data={"accion":"enviar_email","empresa":emp_u,"usuario":st.session_state["u_nom"],"periodo":f"{mes_sidebar} {anio_global}"})
                st.session_state.c_send = False; st.success("Notificado.")
            if c2.button("❌ NO", use_container_width=True): st.session_state.c_send = False; st.rerun()

# --- TAB 4: INGRESO COLABORADOR (MASIVO + RUT + RECORDATORIO) ---
with tabs[3]:
    st.header("👤 Registro de Nuevo Colaborador")
    st.info("Complete los datos y arrastre la documentación base.")
    
    col_inp, col_rec = st.columns([3, 1.2])
    
    with col_rec:
        st.markdown("""
        <div style='background-color:#f1f3f6; padding:15px; border-radius:10px; border-left: 5px solid #1E90FF;'>
        <h4 style='margin-top:0;'>📌 Recordatorio</h4>
        <small>Documentos requeridos:</small>
        <ul style='font-size:11px; padding-left:15px;'>
            <li>Contrato de Trabajo / Anexo</li>
            <li>Cédula de Identidad</li>
            <li>Certificado AFP / Salud</li>
            <li>Pacto Horas Extras</li>
            <li>Entrega RIOH / EPP</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)

    with col_inp:
        emp_c = st.session_state['u_emp'] if rol == "USUARIO" else st.selectbox("Empresa:", sorted(df_av[col_e].unique()), key="c_up_col")
        ci1, ci2 = st.columns(2)
        with ci1: n_new = st.text_input("Nombre Completo:", placeholder="JUAN PEREZ")
        with ci2: 
            r_new = st.text_input("RUT (ej: 12345678-9):", placeholder="12345678-9")
            r_ok = False
            if r_new:
                if validar_rut(r_new): st.caption("✅ RUT Válido"); r_ok = True
                else: st.caption("❌ RUT Inválido")
        
        st.divider()
        f_bulk = st.file_uploader("Arrastre archivos aquí:", type=["pdf"], accept_multiple_files=True, key="bulk_up_new")
        
        if f_bulk and n_new and r_ok:
            if st.button("Subir Documentación", use_container_width=True):
                mt = df_id_empresas[df_id_empresas['EMPRESA'].str.contains(emp_c[:10], case=False, na=False)]
                if not mt.empty:
                    id_f = str(mt.iloc[0]['IDCARPETA']).strip()
                    for f in f_bulk:
                        payload = {"tipo":"colaborador","id_carpeta":id_f,"nombre_persona":n_new.upper(),"rut":r_new,"nombre_final":f.name,"mimetype":"application/pdf","archivo_base64":base64.b64encode(f.read()).decode('utf-8')}
                        requests.post(URL_APPS_SCRIPT, data=payload)
                    st.success(f"Carga de {len(f_bulk)} archivos completada.")

    st.divider()
    if "c_new" not in st.session_state: st.session_state.c_new = False
    if not st.session_state.c_new:
        if st.button("🏁 FINALIZAR INGRESO Y NOTIFICAR", use_container_width=True):
            if n_new and r_ok: st.session_state.c_new = True; st.rerun()
    else:
        st.warning(f"⚠️ **¿Confirmar ingreso de {n_new}?**")
        k1, k2 = st.columns(2)
        if k1.button("✅ SÍ, NOTIFICAR", use_container_width=True):
            msg = f"{mes_sidebar} {anio_global}\nNuevo Colaborador: {n_new.upper()}"
            requests.post(URL_APPS_SCRIPT, data={"accion":"enviar_email", "empresa":emp_c, "usuario":st.session_state["u_nom"], "periodo":msg})
            st.session_state.c_new = False; st.success("Notificado.")
        if k2.button("❌ VOLVER", use_container_width=True): st.session_state.c_new = False; st.rerun()

# --- TAB: ADMIN ---
if rol != "USUARIO":
    with tabs[4]:
        st.header("⚙️ Panel Administrativo")
        st.dataframe(cargar_datos(ID_USUARIOS, "Usuarios"), use_container_width=True)

st.markdown("---")
st.caption("Control Laboral CMSG | Desarrollado por C & S Asociados Ltda.")