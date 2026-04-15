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

# DICCIONARIOS DE APOYO
MAPA_ESTADOS = {1:"Carga Doc.", 2:"En Revision", 3:"Observado", 4:"No Cumple", 5:"Cumple", 8:"Sin Info", 9:"No Corresp."}
COLORES_ESTADOS = {"Cumple":"#00FF00", "No Cumple":"#FF0000", "Observado":"#FFFF00", "En Revision":"#1E90FF", "Carga Doc.":"#FF8C00", "Sin Info":"#555555", "No Corresp.":"#8B4513"}
MAPA_MESES_CARPETAS = {'ENE':'01_ENE','FEB':'02_FEB','MAR':'03_MAR','ABR':'04_ABR','MAY':'05_MAY','JUN':'06_JUN','JUL':'07_JUL','AGO':'08_AGO','SEP':'09_SEP','OCT':'10_OCT','NOV':'11_NOV','DIC':'12_DIC'}
MAPA_MES_NUM = {'ENE':'01','FEB':'02','MAR':'03','ABR':'04','MAY':'05','JUN':'06','JUL':'07','AGO':'08','SEP':'09','OCT':'10','NOV':'11','DIC':'12'}

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

# --- 2. LOGIN COMPLETO ---
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
                ahora_ch = datetime.now(chile_tz)
                st.session_state.update({
                    "authenticated": True, "u_nom": u.get('NOMBRE',''), "u_rol": u.get('ROL',''), 
                    "u_emp": u.get('EMPRESA',''), "u_email": u.get('EMAIL', 'cumplimiento@cysasociados.cl')
                })
                st.session_state["log_accesos"].append({
                    "Fecha": ahora_ch.strftime("%d/%m/%Y"), "Usuario": u.get('NOMBRE',''), "Acción": "Login"
                })
                st.rerun()
            else: st.error("❌ Clave no válida.")
    st.stop()

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Filtros")
    anio_global = st.selectbox("Año", ["2026", "2025"])
    df_av = cargar_datos(ID_AVANCE, anio_global)
    cols_meses = [c for c in df_av.columns if c in MAPA_MESES_CARPETAS.keys()] if not df_av.empty else []
    mes_sidebar = st.selectbox("Mes de Análisis", ["AÑO COMPLETO"] + cols_meses)
    st.divider()
    st.write(f"👤 **{st.session_state['u_nom']}**")
    if st.button("Cerrar Sesión"):
        del st.session_state["authenticated"]
        st.rerun()

# --- 4. TABS ---
rol = st.session_state["u_rol"]
tab_list = ["📈 Avance Laboral", "👥 Masa Colaboradores", "📤 Carga de Documentos"]
if rol == "ADMIN": tab_list.append("⚙️ Admin")
tabs = st.tabs(tab_list)

# --- TAB 1: DASHBOARD (VERSION FINAL EXPANDIDA) ---
with tabs[0]:
    if not df_av.empty:
        col_e = next((c for c in df_av.columns if 'EMP' in str(c).upper()), 'EMPRESA')
        df_f = df_av[df_av[col_e] == st.session_state["u_emp"]] if rol == "USUARIO" else df_av
        cols_filtro = [mes_sidebar] if mes_sidebar != "AÑO COMPLETO" else cols_meses
        df_num = df_f[cols_filtro].apply(pd.to_numeric, errors='coerce')

        st.header(f"Dashboard de Cumplimiento - {mes_sidebar} {anio_global}")
        
        # FILA 1: KPIs Principales
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas", len(df_f))
        t_p = df_num.isin([1,2,3,4,5]).sum().sum()
        t_5 = (df_num == 5).sum().sum()
        k2.metric("% Cumplimiento", f"{(t_5/t_p*100 if t_p > 0 else 0):.1f}%")
        al_dia = ((df_num == 5).all(axis=1)).sum() if mes_sidebar == "AÑO COMPLETO" else "N/A"
        k3.metric("Empresas 100% Al Día", al_dia)

        # FILA 2: Recuento por Estados (NUEVO)
        st.write("### 📊 Periodos por Estado")
        status_counts = df_num.stack().value_counts()
        m_cols = st.columns(len(MAPA_ESTADOS))
        for i, (code, name) in enumerate(MAPA_ESTADOS.items()):
            cant = int(status_counts.get(code, 0))
            m_cols[i].metric(name, cant)

        st.divider()

        # Gráfico de Barras Evolutivo / Mensual
        st.write(f"### 📈 Distribución de Estados en el Tiempo")
        res_evo = []
        # Siempre mostramos todos los meses para ver evolución, o solo el mes filtrado
        for m in (cols_meses if mes_sidebar == "AÑO COMPLETO" else [mes_sidebar]):
            counts = df_f[m].value_counts()
            for cod, cant in counts.items():
                if pd.notna(cod) and int(cod) in MAPA_ESTADOS:
                    res_evo.append({'Mes': m, 'Estado': MAPA_ESTADOS[int(cod)], 'Cantidad': cant})
        
        if res_evo:
            st.plotly_chart(px.bar(pd.DataFrame(res_evo), x='Mes', y='Cantidad', color='Estado', 
                                   color_discrete_map=COLORES_ESTADOS, barmode='stack'), use_container_width=True)

        st.divider()

        # ANALISIS POR EMPRESA
        st.write("### 🎯 Detalle por Empresa y Descarga de Certificados")
        emp_sel = st.selectbox("Seleccione Empresa:", sorted(df_f[col_e].unique()))
        df_emp_sel = df_f[df_f[col_e] == emp_sel]
        
        c_pie, c_tab, c_cert = st.columns([1.5, 1.5, 1])
        
        with c_pie:
            st.write("**Resumen Anual**")
            emp_pie_data = df_emp_sel[cols_meses].stack().value_counts().reset_index()
            emp_pie_data.columns = ['Cod', 'Cant']
            emp_pie_data['Estado'] = emp_pie_data['Cod'].map(MAPA_ESTADOS)
            st.plotly_chart(px.pie(emp_pie_data, values='Cant', names='Estado', color='Estado', 
                                   color_discrete_map=COLORES_ESTADOS, hole=0.4), use_container_width=True)

        with c_tab:
            st.write("**Historial Mensual**")
            detalle_emp = df_emp_sel[cols_meses].T.reset_index()
            detalle_emp.columns = ['Mes', 'Cod']
            detalle_emp['Estado'] = detalle_emp['Cod'].map(MAPA_ESTADOS)
            st.dataframe(detalle_emp[['Mes', 'Estado']], use_container_width=True, height=250)

        with c_cert:
            st.write("**Certificados**")
            m_cert = st.selectbox("Mes Certificado:", cols_meses)
            if st.button(f"🔍 Obtener PDF {m_cert}"):
                df_id = cargar_datos(ID_EMPRESAS, "HOJA1")
                match_id = df_id[df_id.iloc[:,1].str.contains(emp_sel[:12], case=False, na=False)]
                if not match_id.empty:
                    id_f = str(match_id.iloc[0][0]).strip()
                    nombre_f = f"Certificado.{MAPA_MES_NUM[m_cert]}{anio_global}.pdf"
                    with st.spinner("Buscando..."):
                        r = requests.get(URL_APPS_SCRIPT, params={"nombre": nombre_f, "carpeta": id_f})
                        if r.text.startswith("http"): st.link_button("📥 Descargar", r.text.strip())
                        else: st.error("No disponible.")

# --- TAB 2: MASA LABORAL (CON ALERTAS PLAZO FIJO) ---
with tabs[1]:
    st.header(f"Nómina de Colaboradores - {anio_global}")
    mes_m = st.selectbox("Mes Nómina:", list(MAPA_MES_NUM.keys()))
    df_masa = cargar_datos(ID_COLABORADORES, f"{mes_m.capitalize()}{anio_global[-2:]}")
    if not df_masa.empty:
        col_rs = next((c for c in df_masa.columns if 'RAZON' in str(c).upper()), df_masa.columns[0])
        df_mf = df_masa[df_masa[col_rs] == st.session_state["u_emp"]] if rol == "USUARIO" else df_masa
        
        # Alerta Plazo Fijo (Recuperada de v.6)
        col_c = next((c for c in df_mf.columns if 'CONTRATO' in str(c).upper()), None)
        if col_c:
            plazo_f = df_mf[df_mf[col_c].str.contains("PLAZO FIJO", case=False, na=False)]
            if not plazo_f.empty:
                st.warning(f"🚨 Alerta: Se detectaron {len(plazo_f)} contratos a Plazo Fijo.")
                with st.expander("Ver detalle de contratos a plazo"):
                    st.dataframe(plazo_f)
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Dotación", len(df_mf))
        if 'NACIONALIDAD' in df_mf.columns:
            ext = len(df_mf[~df_mf['NACIONALIDAD'].str.contains('CHILE', na=False)])
            m2.metric("Extranjeros", ext)
        if 'TOTALHORASEXTRA' in df_mf.columns:
            m3.metric("HH.EE Mes", f"{pd.to_numeric(df_mf['TOTALHORASEXTRA'], errors='coerce').sum():,.0f}")
            
        st.dataframe(df_mf, use_container_width=True)

# --- TAB 3: CARGA DE DOCUMENTOS (CON NOTIFICACIÓN EMAIL) ---
with tabs[2]:
    st.header("📤 Pasarela de Carga")
    if mes_sidebar == "AÑO COMPLETO": st.warning("⚠️ Seleccione un mes en el sidebar.")
    else:
        empresa_up = st.session_state['u_emp'] if rol == "USUARIO" else st.selectbox("Empresa Destino:", sorted(df_av[col_e].unique()))
        docs = [("Liquidaciones", "LIQ"), ("Previred", "PREVIRED"), ("F30", "F30"), ("F30-1", "F30_1"), ("Pagos", "PAGOS")]
        
        for n, pref in docs:
            c1, c2 = st.columns([3, 1])
            archivo = c1.file_uploader(f"Subir {n}", type=["pdf"], key=f"u_{pref}")
            if c2.button(f"🚀 Cargar {pref}", key=f"b_{pref}"):
                if archivo:
                    df_id_up = cargar_datos(ID_EMPRESAS, "HOJA1")
                    match_up = df_id_up[df_id_up.iloc[:,1].str.contains(empresa_up[:12], case=False, na=False)]
                    if not match_up.empty:
                        id_f_up = str(match_up.iloc[0][0]).strip()
                        payload = {
                            "nombre_final": f"{pref}_{mes_sidebar}_{anio_global}_{empresa_up[:10]}.pdf",
                            "id_carpeta": id_f_up, "anio": anio_global, "mes_nombre": MAPA_MESES_CARPETAS[mes_sidebar],
                            "mimetype": "application/pdf", "archivo_base64": base64.b64encode(archivo.read()).decode('utf-8')
                        }
                        with st.spinner("Subiendo..."):
                            r = requests.post(URL_APPS_SCRIPT, data=payload)
                            if "✅" in r.text or "Exito" in r.text: 
                                st.success(f"¡{n} cargado!"); st.balloons()
                else: st.warning("Falta archivo.")

        st.divider()
        if st.button("🏁 FINALIZAR Y NOTIFICAR POR CORREO", use_container_width=True):
            p_email = {"accion": "enviar_email", "empresa": empresa_up, "usuario": st.session_state["u_nom"], "periodo": f"{mes_sidebar} {anio_global}", "email_usuario": st.session_state["u_email"]}
            with st.spinner("Enviando aviso..."):
                r = requests.post(URL_APPS_SCRIPT, data=p_email)
                if "✅" in r.text: st.success("¡Email enviado!"); st.balloons()

st.markdown("---")
st.caption("CMSG | C&S Asociados Ltda.")