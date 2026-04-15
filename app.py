import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import base64
import re
import os
from datetime import datetime
import pytz

# 1. CONFIGURACIÓN Y ESTILO
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")
chile_tz = pytz.timezone('America/Santiago')

# --- CABECERA ---
col_l, col_m, col_r = st.columns([2, 4, 1])
with col_l:
    if os.path.exists("CMSG.png"): st.image("CMSG.png", width=250)
    else: st.subheader("🏢 Minera San Gerónimo")
with col_r:
    if os.path.exists("cys.png"): st.image("cys.png", width=120)
    else: st.write("**C&S Asociados**")

# --- CONEXIONES ---
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbz0twB53lP3FXsKcYFeuiveudxWjHnJ8MBomDV1sGRl2SUqnPVeYay3BHKXhTg-hTe1hg/exec"
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"

MAPA_ESTADOS = {1:"Carga Doc.", 2:"En Revision", 3:"Observado", 4:"No Cumple", 5:"Cumple", 8:"Sin Info", 9:"No Corresp."}
COLORES_ESTADOS = {"Cumple":"#00FF00", "No Cumple":"#FF0000", "Observado":"#FFFF00", "En Revision":"#1E90FF", "Carga Doc.":"#FF8C00", "Sin Info":"#555555", "No Corresp.":"#8B4513"}
MAPA_MESES_CARPETAS = {'ENE':'01_ENE','FEB':'02_FEB','MAR':'03_MAR','ABR':'04_ABR','MAY':'05_MAY','JUN':'06_JUN','JUL':'07_JUL','AGO':'08_AGO','SEP':'09_SEP','OCT':'10_OCT','NOV':'11_NOV','DIC':'12_DIC'}
MAPA_MES_NUM = {'ENE':'01','FEB':'02','MAR':'03','ABR':'04','MAY':'05','JUN':'06','JUL':'07','AGO':'08','SEP':'09','OCT':'10','NOV':'11','DIC':'12'}

@st.cache_data(ttl=15)
def cargar_datos(sheet_id, nombre_pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
        df = pd.read_csv(url, encoding='utf-8-sig')
        df.columns = [re.sub(r'[^A-Z0-9]', '', str(c).upper()) for c in df.columns]
        return df.dropna(how='all')
    except: return pd.DataFrame()

# --- LOGIN ---
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
                st.session_state.update({"authenticated": True, "u_nom": u.get('NOMBRE',''), "u_rol": u.get('ROL',''), "u_emp": u.get('EMPRESA',''), "u_email": u.get('EMAIL', 'cumplimiento@cysasociados.cl')})
                st.rerun()
            else: st.error("❌ Clave no válida.")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    anio_global = st.selectbox("Año", ["2026", "2025"])
    df_av = cargar_datos(ID_AVANCE, anio_global)
    cols_meses_data = [c for c in df_av.columns if c in MAPA_MESES_CARPETAS.keys()] if not df_av.empty else []
    mes_sidebar = st.selectbox("Mes de Análisis", ["AÑO COMPLETO"] + cols_meses_data)
    st.divider()
    st.write(f"👤 **{st.session_state['u_nom']}**")
    if st.button("Cerrar Sesión"):
        del st.session_state["authenticated"]; st.rerun()

# --- TABS ---
rol = st.session_state["u_rol"]
tab_list = ["📈 Avance Laboral", "👥 Masa Colaboradores", "📤 Carga de Documentos"]
if rol == "ADMIN": tab_list.append("⚙️ Admin")
tabs = st.tabs(tab_list)

# --- TAB 1: DASHBOARD ---
with tabs[0]:
    if not df_av.empty:
        col_e_name = next((c for c in df_av.columns if 'EMP' in str(c).upper()), 'EMPRESA')
        df_f = df_av[df_av[col_e_name] == st.session_state["u_emp"]] if rol == "USUARIO" else df_av
        
        # Seleccionamos meses y convertimos a número
        cols_filtro = [mes_sidebar] if mes_sidebar != "AÑO COMPLETO" else cols_meses_data
        df_num = df_f[cols_filtro].apply(pd.to_numeric, errors='coerce')

        # --- EXCLUSIÓN CRÍTICA DEL ESTADO 9 ---
        # Creamos una copia que reemplaza el 9 por vacíos (NaN) para que no cuente en los porcentajes
        df_calculo = df_num.replace(9, pd.NA)
        
        total_periodos_validos = df_calculo.count().sum() # .count() ignora NaNs (incluyendo los que eran 9)
        total_cumple = (df_calculo == 5).sum().sum()
        perc_cumplimiento = (total_cumple / total_periodos_validos * 100) if total_periodos_validos > 0 else 0

        st.header(f"Dashboard - {mes_sidebar} {anio_global}")
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas", len(df_f))
        k2.metric("% Cumplimiento (Auditado)", f"{perc_cumplimiento:.1f}%", help="No considera los estados 'No Corresponde'")
        al_dia = ((df_calculo == 5).all(axis=1)).sum() if mes_sidebar == "AÑO COMPLETO" else "N/A"
        k3.metric("Empresas 100% Al Día", al_dia)

        # Recuento por Estados (Aquí sí mostramos el 9 solo para información visual)
        st.write("### 📊 Cantidad de Periodos por Estado")
        counts = df_num.stack().value_counts()
        m_cols = st.columns(len(MAPA_ESTADOS))
        for i, (code, name) in enumerate(MAPA_ESTADOS.items()):
            cant = int(counts.get(code, 0))
            m_cols[i].metric(name, cant)

        st.divider()

        # Gráfico de Barras Evolutivo
        res_bar = []
        for m in (cols_meses_data if mes_sidebar == "AÑO COMPLETO" else [mes_sidebar]):
            c_m = df_f[m].value_counts()
            for cod, cant in c_m.items():
                if pd.notna(cod) and int(cod) in MAPA_ESTADOS:
                    res_bar.append({'Mes': m, 'Estado': MAPA_ESTADOS[int(cod)], 'Cantidad': cant})
        if res_bar:
            st.plotly_chart(px.bar(pd.DataFrame(res_bar), x='Mes', y='Cantidad', color='Estado', 
                                   color_discrete_map=COLORES_ESTADOS, barmode='stack'), use_container_width=True)

        st.divider()

        # ANÁLISIS POR EMPRESA Y CERTIFICADOS
        st.write("### 🎯 Detalle por Empresa y Descarga de Certificados")
        emp_sel = st.selectbox("Seleccione Empresa:", sorted(df_f[col_e_name].unique()))
        df_e_sel = df_f[df_f[col_e_name] == emp_sel]
        
        c_p, c_t, c_c = st.columns([1.5, 1.5, 1])
        with c_p:
            st.write("**Estatus Anual**")
            pie_data = df_e_sel[cols_meses_data].stack().value_counts().reset_index()
            pie_data.columns = ['Cod', 'Cant']; pie_data['Estado'] = pie_data['Cod'].map(MAPA_ESTADOS)
            st.plotly_chart(px.pie(pie_data, values='Cant', names='Estado', color='Estado', 
                                   color_discrete_map=COLORES_ESTADOS, hole=0.4), use_container_width=True)
        with c_t:
            st.write("**Historial**")
            hist = df_e_sel[cols_meses_data].T.reset_index()
            hist.columns = ['Mes', 'Cod']; hist['Estado'] = hist['Cod'].map(MAPA_ESTADOS)
            st.dataframe(hist[['Mes', 'Estado']], use_container_width=True, height=250)
        
        with c_c:
            st.write("**Descarga PDF**")
            m_pdf = st.selectbox("Mes Certificado:", cols_meses_data)
            if st.button(f"🔍 Obtener PDF {m_pdf}"):
                df_ent = cargar_datos(ID_EMPRESAS, "HOJA1")
                # Buscador flexible: quitamos espacios y pasamos a mayúsculas
                match_ent = df_ent[df_ent.iloc[:,1].str.replace(' ','').str.upper().str.contains(emp_sel[:10].replace(' ','').upper(), na=False)]
                if not match_ent.empty:
                    col_id = next((c for c in df_ent.columns if 'ID' in str(c).upper()), df_ent.columns[0])
                    id_folder = str(match_ent.iloc[0][col_id]).strip()
                    nombre_archivo = f"Certificado.{MAPA_MES_NUM[m_pdf]}{anio_global}.pdf"
                    
                    with st.spinner("Buscando en servidor..."):
                        try:
                            # Forzamos la consulta al Apps Script
                            res_script = requests.get(URL_APPS_SCRIPT, params={"nombre": nombre_archivo, "carpeta": id_folder}, timeout=15)
                            if res_script.text.startswith("http"): 
                                st.success("✅ Certificado Listo")
                                st.link_button("📥 Descargar Archivo", res_script.text.strip())
                            else: st.warning("⚠️ No se encontró el archivo. Verifique que esté emitido en Drive.")
                        except: st.error("❌ Error de comunicación con Google Drive.")
                else: st.error("No se encontró el ID de carpeta para esta empresa.")

# --- TAB 2: MASA LABORAL ---
with tabs[1]:
    st.header(f"Nómina de Colaboradores - {anio_global}")
    mes_nom = st.selectbox("Mes Nómina:", list(MAPA_MES_NUM.keys()))
    df_m = cargar_datos(ID_COLABORADORES, f"{mes_nom.capitalize()}{anio_global[-2:]}")
    if not df_m.empty:
        col_r_social = next((c for c in df_m.columns if 'RAZON' in str(c).upper()), df_m.columns[0])
        df_m_f = df_m[df_m[col_r_social] == st.session_state["u_emp"]] if rol == "USUARIO" else df_m
        
        col_cont = next((c for c in df_m_f.columns if 'CONTRATO' in str(c).upper()), None)
        if col_cont:
            pf = df_m_f[df_m_f[col_cont].str.contains("PLAZO FIJO", case=False, na=False)]
            if not pf.empty: st.warning(f"🚨 Alerta: Hay {len(pf)} contratos a Plazo Fijo.")
        st.dataframe(df_m_f, use_container_width=True)

# --- TAB 3: CARGA ---
with tabs[2]:
    st.header("📤 Carga de Documentos")
    if mes_sidebar == "AÑO COMPLETO": st.warning("⚠️ Elija un mes específico.")
    else:
        emp_up = st.session_state['u_emp'] if rol == "USUARIO" else st.selectbox("Empresa:", sorted(df_av[col_e_name].unique()))
        for n, p in [("Liquidaciones", "LIQ"), ("Previred", "PREVIRED"), ("F30", "F30"), ("F30-1", "F30_1"), ("Pagos", "PAGOS")]:
            c1, c2 = st.columns([3, 1])
            arch = c1.file_uploader(f"Subir {n}", type=["pdf"], key=f"f_{p}")
            if c2.button(f"🚀 Cargar {p}", key=f"b_{p}"):
                if arch:
                    df_ent_up = cargar_datos(ID_EMPRESAS, "HOJA1")
                    match_up = df_ent_up[df_ent_up.iloc[:,1].str.replace(' ','').str.upper().str.contains(emp_up[:10].replace(' ','').upper(), na=False)]
                    if not match_up.empty:
                        col_id_up = next((c for c in df_ent_up.columns if 'ID' in str(c).upper()), df_ent_up.columns[0])
                        id_f_up = str(match_up.iloc[0][col_id_up]).strip()
                        payload = {"nombre_final": f"{p}_{mes_sidebar}_{anio_global}_{emp_up[:10]}.pdf", "id_carpeta": id_f_up, "anio": anio_global, "mes_nombre": MAPA_MESES_CARPETAS[mes_sidebar], "mimetype": "application/pdf", "archivo_base64": base64.b64encode(arch.read()).decode('utf-8')}
                        with st.spinner("Subiendo..."):
                            r = requests.post(URL_APPS_SCRIPT, data=payload)
                            if "✅" in r.text or "Exito" in r.text: st.success("¡Cargado!"); st.balloons()
                else: st.warning("Seleccione archivo.")
        st.divider()
        if st.button("🏁 FINALIZAR Y NOTIFICAR", use_container_width=True):
            p_e = {"accion": "enviar_email", "empresa": emp_up, "usuario": st.session_state["u_nom"], "periodo": f"{mes_sidebar} {anio_global}", "email_usuario": st.session_state["u_email"]}
            with st.spinner("Notificando..."):
                r = requests.post(URL_APPS_SCRIPT, data=p_e)
                if "✅" in r.text: st.success("¡Notificado!"); st.balloons()

st.caption("CMSG | C&S Asociados Ltda.")