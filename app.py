import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import base64
import re
import os
from datetime import datetime
import pytz

# 1. CONFIGURACIÓN DE PANTALLA Y RELOJ CHILENO
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")
chile_tz = pytz.timezone('America/Santiago')

# --- CABECERA INSTITUCIONAL (LOGOS) ---
col_logo_l, col_espacio, col_logo_r = st.columns([2, 4, 1])
with col_logo_l:
    if os.path.exists("CMSG.png"):
        st.image("CMSG.png", width=250)
    else: st.subheader("🏢 Minera San Gerónimo")
with col_logo_r:
    if os.path.exists("cys.png"):
        st.image("cys.png", width=120)
    else: st.write("**C&S Asociados**")

# --- CONFIGURACIÓN DE CONEXIÓN ---
# Nota: Esta URL debe ser la que tiene permisos de Email habilitados (v8)
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbz0twB53lP3FXsKcYFeuiveudxWjHnJ8MBomDV1sGRl2SUqnPVeYay3BHKXhTg-hTe1hg/exec"

ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"

# MAPEOS
MAPA_ESTADOS = {1:"Carga Doc.", 2:"En Revision", 3:"Observado", 4:"No Cumple", 5:"Cumple", 8:"Sin Info", 9:"No Corresp."}
COLORES_ESTADOS = {"Cumple":"#00FF00", "No Cumple":"#FF0000", "Observado":"#FFFF00", "En Revision":"#1E90FF", "Carga Doc.":"#FF8C00", "Sin Info":"#555555", "No Corresp.":"#8B4513"}
MAPA_MESES_NUM = {'ENE':'01','FEB':'02','MAR':'03','ABR':'04','MAY':'05','JUN':'06','JUL':'07','AGO':'08','SEP':'09','OCT':'10','NOV':'11','DIC':'12'}
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

# --- 2. LOGIN (CON BLINDAJE DE EMAIL 'nan') ---
if "authenticated" not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 Acceso Control Laboral CMSG")
        pwd = st.text_input("Contraseña:", type="password").strip()
        if st.button("Ingresar", use_container_width=True):
            df_u = cargar_datos(ID_USUARIOS, "Usuarios")
            col_c = next((c for c in df_u.columns if 'CLAVE' in c), 'CLAVE')
            match = df_u[df_u[col_c].astype(str).str.strip() == pwd]
            if not match.empty:
                u = match.iloc[0]
                ahora_ch = datetime.now(chile_tz)
                
                # Blindaje para el error 'nan'
                email_raw = u.get('EMAIL')
                email_limpio = str(email_raw).strip() if pd.notna(email_raw) else "cumplimiento@cysasociados.cl"
                
                st.session_state["log_accesos"].append({
                    "Fecha": ahora_ch.strftime("%d/%m/%Y"),
                    "Hora": ahora_ch.strftime("%H:%M:%S"),
                    "Usuario": u.get('NOMBRE',''),
                    "Empresa": u.get('EMPRESA',''),
                    "Rol": u.get('ROL','')
                })
                st.session_state.update({
                    "authenticated": True, 
                    "u_nom": u.get('NOMBRE',''), 
                    "u_rol": u.get('ROL',''), 
                    "u_emp": u.get('EMPRESA',''),
                    "u_email": email_limpio
                })
                st.rerun()
            else: st.error("❌ Clave no válida.")
    st.stop()

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuración")
    anio_global = st.selectbox("Año de Análisis", ["2026", "2025"])
    df_av = cargar_datos(ID_AVANCE, anio_global)
    cols_m_sidebar = [c for c in df_av.columns if c in MAPA_MESES_NUM.keys()] if not df_av.empty else []
    mes_sidebar = st.selectbox("Mes de Análisis", ["AÑO COMPLETO"] + cols_m_sidebar)
    
    st.divider()
    st.write(f"👤 **{st.session_state['u_nom']}**")
    st.caption(f"Empresa: {st.session_state['u_emp']}")
    if st.button("Cerrar Sesión"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# --- 4. TABS DINÁMICOS (NUEVA PESTAÑA DE CARGA) ---
rol = st.session_state["u_rol"]
if rol == "ADMIN":
    tabs = st.tabs(["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Colaboradores", "📤 Carga de Documentos", "⚙️ Administración"])
elif rol == "REVISOR":
    tabs = st.tabs(["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Colaboradores", "📤 Carga de Documentos"])
else: # USUARIO
    tabs = st.tabs(["📈 Mi Avance", "👥 Masa Laboral", "📤 Carga de Documentos"])

# --- TAB 1: AVANCE LABORAL (MATEMÁTICA ESTADO 9) ---
with tabs[0]:
    df_id = cargar_datos(ID_EMPRESAS, "HOJA1")
    if not df_av.empty:
        col_e = next((c for c in df_av.columns if 'EMP' in c), df_av.columns[0])
        df_f = df_av[df_av[col_e] == st.session_state["u_emp"]] if rol == "USUARIO" else df_av
        cols_filtro = [mes_sidebar] if mes_sidebar != "AÑO COMPLETO" else cols_m_sidebar
        df_num = df_f[cols_filtro].apply(pd.to_numeric, errors='coerce')

        # --- CÁLCULO CUMPLIMIENTO (EXCLUYENDO ESTADO 9) ---
        # Filtramos: Solo nos interesan los estados del 1 al 8. El 9 desaparece de la base.
        df_audit = df_num[df_num != 9]
        total_p = df_audit.count().sum() 
        total_5 = (df_audit == 5).sum().sum()
        
        st.header(f"Gestión de Control Laboral CMSG - {anio_global}")
        
        # KPIs
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas en Panel", len(df_f))
        k2.metric("% Cumplimiento Real", f"{(total_5/total_p*100 if total_p > 0 else 0):.1f}%", help="No considera el estado 'No Corresponde'")
        k3.metric("Empresas al Día (100%)", (df_audit == 5).all(axis=1).sum() if not df_audit.empty else 0)

        # Recuento por Estados
        st.write("### 📊 Cantidad por Estado")
        counts = df_num.stack().value_counts()
        m_cols = st.columns(len(MAPA_ESTADOS))
        for i, (code, name) in enumerate(MAPA_ESTADOS.items()):
            m_cols[i].metric(name, int(counts.get(code, 0)))

        if rol != "USUARIO" and mes_sidebar == "AÑO COMPLETO":
            st.divider()
            res_evo = []
            for m in cols_m_sidebar:
                c_m = df_f[m].value_counts()
                for cod, cant in c_m.items():
                    if pd.notna(cod):
                        res_evo.append({'Mes': m, 'Estado': MAPA_ESTADOS.get(int(cod), "S/I"), 'Cantidad': cant})
            if res_evo:
                st.plotly_chart(px.bar(pd.DataFrame(res_evo), x='Mes', y='Cantidad', color='Estado', 
                                       color_discrete_map=COLORES_ESTADOS, barmode='stack', title="Evolución Mensual"), use_container_width=True)

        st.divider()
        st.subheader("🎯 Análisis Detallado por Empresa")
        emp_sel = st.selectbox("Seleccione Empresa:", sorted(df_f[col_e].unique()))
        df_es = df_f[df_f[col_e] == emp_sel]
        
        col_pie, col_desc = st.columns([2, 1])
        with col_pie:
            pie_data = df_es[cols_m_sidebar].stack().value_counts().reset_index()
            pie_data.columns = ['Cod', 'Cant']; pie_data['Estado'] = pie_data['Cod'].map(MAPA_ESTADOS)
            st.plotly_chart(px.pie(pie_data, values='Cant', names='Estado', hole=.4, 
                                   color='Estado', color_discrete_map=COLORES_ESTADOS, title=f"Distribución: {emp_sel}"), use_container_width=True)
            
            # --- TABLA DE HISTORIAL (BAJO EL GRÁFICO) ---
            st.write("#### 📜 Historial Mensual")
            hist = df_es[cols_m_sidebar].T.reset_index()
            hist.columns = ['Mes', 'Cod']; hist['Estado'] = hist['Cod'].map(MAPA_ESTADOS)
            st.dataframe(hist[['Mes', 'Estado']], use_container_width=True)

        with col_desc:
            st.write("#### 📥 Certificados PDF")
            mes_pdf = st.selectbox("Mes para el PDF:", cols_m_sidebar)
            if st.button(f"🔍 Obtener Certificado"):
                match = df_id[df_id.iloc[:,1].str.contains(emp_sel[:10], case=False, na=False)]
                if not match.empty:
                    id_f = str(match.iloc[0][0]).strip()
                    nombre_f = f"Certificado.{MAPA_MESES_NUM[mes_pdf]}{anio_global}.pdf"
                    with st.spinner("Buscando en Drive..."):
                        r = requests.get(URL_APPS_SCRIPT, params={"nombre": nombre_f, "carpeta": id_f})
                        if r.text.startswith("http"):
                            st.success("✅ Encontrado")
                            st.link_button("📥 Descargar Archivo", r.text.strip())
                        else: st.error("No disponible.")

# --- TAB 2: KPIs EMPRESAS ---
if rol != "USUARIO":
    with tabs[1]:
        st.header("🏢 KPIs Nivel Empresa")
        st.dataframe(cargar_datos(ID_EMPRESAS, "HOJA1"), use_container_width=True)

# --- TAB 3: MASA COLABORADORES (ALERTAS V6) ---
idx_masa = 1 if rol == "USUARIO" else 2
with tabs[idx_masa]:
    st.header(f"Análisis de Dotación - {anio_global}")
    mes_m = st.selectbox("Mes Masa:", list(MAPA_MESES_NUM.keys()), key="m_masa")
    df_masa = cargar_datos(ID_COLABORADORES, f"{mes_m.capitalize()}{anio_global[-2:]}")
    if not df_masa.empty:
        col_rs = next((c for c in df_masa.columns if 'RAZON' in str(c).upper()), df_masa.columns[0])
        df_mf = df_masa[df_masa[col_rs] == st.session_state["u_emp"]] if rol == "USUARIO" else df_masa
        
        st.subheader("🚨 Alertas de Estabilidad")
        col_cont = next((c for c in df_mf.columns if 'CONTRATO' in str(c).upper()), None)
        if col_cont:
            pf = df_mf[df_mf[col_cont].str.contains("PLAZO FIJO", case=False, na=False)]
            if not pf.empty:
                st.warning(f"Se detectaron {len(pf)} trabajadores con contrato a Plazo Fijo.")
                st.dataframe(pf, use_container_width=True)
            else: st.success("✅ Todo el personal analizado tiene contrato Indefinido.")
        
        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("Dotación", len(df_mf))
        if 'NACIONALIDAD' in df_mf.columns:
            ext = len(df_mf[~df_mf['NACIONALIDAD'].str.contains('CHILE', na=False)])
            m2.metric("Extranjeros", ext)
        if 'TOTALHORASEXTRA' in df_mf.columns:
            m3.metric("HH.EE Mes", f"{pd.to_numeric(df_mf['TOTALHORASEXTRA'], errors='coerce').sum():,.0f}")
        st.dataframe(df_mf, use_container_width=True)

# --- TAB 4: CARGA DE DOCUMENTOS (PESTAÑA EXCLUSIVA) ---
idx_carga = 2 if rol == "USUARIO" else 3
with tabs[idx_carga]:
    st.header("📤 Pasarela de Carga de Documentos")
    if mes_sidebar == "AÑO COMPLETO":
        st.warning("⚠️ Seleccione un mes específico en el panel lateral para habilitar la carga.")
    else:
        empresa_up = st.session_state['u_emp'] if rol == "USUARIO" else st.selectbox("Empresa Destino:", sorted(df_av[col_e].unique()))
        docs = [("Liquidaciones", "LIQ"), ("Previred", "PREVIRED"), ("F30", "F30"), ("F30-1", "F30_1"), ("Pagos", "PAGOS")]
        
        for nombre, pref in docs:
            c1, c2 = st.columns([3, 1])
            archivo = c1.file_uploader(f"Subir {nombre}", type=["pdf"], key=f"up_{pref}")
            if c2.button(f"🚀 Cargar {pref}", key=f"btn_{pref}"):
                if archivo:
                    match_u = df_id[df_id.iloc[:,1].str.contains(empresa_up[:10], case=False, na=False)]
                    if not match_u.empty:
                        id_folder = str(match_u.iloc[0][0]).strip()
                        payload = {
                            "nombre_final": f"{pref}_{mes_sidebar}_{anio_global}_{empresa_up[:10]}.pdf",
                            "id_carpeta": id_folder, "anio": anio_global, 
                            "mes_nombre": MAPA_MESES_CARPETAS[mes_sidebar],
                            "mimetype": "application/pdf",
                            "archivo_base64": base64.b64encode(archivo.read()).decode('utf-8')
                        }
                        with st.spinner(f"Subiendo {pref}..."):
                            r = requests.post(URL_APPS_SCRIPT, data=payload)
                            if "✅" in r.text or "Exito" in r.text: st.success("¡Cargado!"); st.balloons()
                else: st.warning("Seleccione archivo.")

        st.divider()
        st.subheader("🏁 Finalizar Proceso")
        if st.button("✅ ENVIAR NOTIFICACIÓN DE CARGA FINALIZADA", use_container_width=True):
            p_email = {
                "accion": "enviar_email", "empresa": empresa_up, "usuario": st.session_state["u_nom"],
                "periodo": f"{mes_sidebar} {anio_global}", "email_usuario": st.session_state["u_email"]
            }
            with st.spinner("Enviando aviso..."):
                try:
                    res = requests.post(URL_APPS_SCRIPT, data=p_email)
                    if "✅" in res.text: st.success("¡Email enviado!"); st.balloons()
                    else: st.error(res.text)
                except: st.error("Error al notificar.")

# --- TAB ADMIN ---
if rol == "ADMIN":
    with tabs[-1]:
        st.header("⚙️ Administración")
        if st.session_state["log_accesos"]: st.table(pd.DataFrame(st.session_state["log_accesos"]))
        st.dataframe(cargar_datos(ID_USUARIOS, "Usuarios"), use_container_width=True)

st.markdown("---")
st.caption("C&S Asociados Ltda. para Control Laboral CMSG")