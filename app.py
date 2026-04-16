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
    else: 
        st.subheader("🏢 Minera San Gerónimo")
with col_logo_r:
    if os.path.exists("cys.png"): 
        st.image("cys.png", width=120)
    else: 
        st.write("**C&S Asociados**")

# --- CONFIGURACIÓN DE CONEXIÓN (IMPORTANTE: Verifica tu URL de Apps Script) ---
# Esta URL debe ser la de tu última implementación con doGet y doPost
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbz0twB53lP3FXsKcYFeuiveudxWjHnJ8MBomDV1sGRl2SUqnPVeYay3BHKXhTg-hTe1hg/exec"

ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"

# MAPEOS Y DICCIONARIOS
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
        # Limpieza de cabeceras: Mayúsculas y sin caracteres raros
        df.columns = [re.sub(r'[^A-Z0-9]', '', str(c).upper()) for c in df.columns]
        return df.dropna(how='all')
    except Exception as e:
        st.error(f"Error al cargar {nombre_pestana}: {e}")
        return pd.DataFrame()

# --- 2. SISTEMA DE LOGIN (CAPTURA DE EMAIL PARA NOTIFICACIONES) ---
if "authenticated" not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 Acceso Control Laboral CMSG")
        pwd = st.text_input("Contraseña:", type="password").strip()
        if st.button("Ingresar al Portal", use_container_width=True):
            df_u = cargar_datos(ID_USUARIOS, "Usuarios")
            col_c = next((c for c in df_u.columns if 'CLAVE' in str(c).upper()), 'CLAVE')
            match = df_u[df_u[col_c].astype(str).str.strip() == pwd]
            if not match.empty:
                u = match.iloc[0]
                ahora_chile = datetime.now(chile_tz)
                # Guardamos datos en sesión
                st.session_state.update({
                    "authenticated": True,
                    "u_nom": u.get('NOMBRE','Sin Nombre'),
                    "u_rol": u.get('ROL','USUARIO'),
                    "u_emp": u.get('EMPRESA','CMSG'),
                    "u_email": u.get('EMAIL', 'cumplimiento@cysasociados.cl')
                })
                # Log de acceso
                st.session_state["log_accesos"].append({
                    "Fecha": ahora_chile.strftime("%d/%m/%Y"),
                    "Hora": ahora_chile.strftime("%H:%M:%S"),
                    "Usuario": u.get('NOMBRE',''),
                    "Empresa": u.get('EMPRESA',''),
                    "Rol": u.get('ROL','')
                })
                st.rerun()
            else:
                st.error("❌ Contraseña incorrecta. Por favor reintente.")
    st.stop()

# --- 3. SIDEBAR DE CONTROL ---
with st.sidebar:
    st.header("⚙️ Filtros de Análisis")
    anio_global = st.selectbox("Seleccione Año", ["2026", "2025"])
    df_av = cargar_datos(ID_AVANCE, anio_global)
    cols_m = [c for c in df_av.columns if c in MAPA_MESES_NUM.keys()] if not df_av.empty else []
    mes_sidebar = st.selectbox("Mes de Análisis", ["AÑO COMPLETO"] + cols_m)
    st.divider()
    st.write(f"👤 **Usuario:** {st.session_state['u_nom']}")
    st.caption(f"Empresa: {st.session_state['u_emp']}")
    if st.button("Cerrar Sesión"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# --- 4. DEFINICIÓN DE PESTAÑAS (TABS) POR ROL ---
rol = st.session_state["u_rol"]
if rol == "ADMIN":
    tab_list = ["📈 Avance Global", "🏢 KPIs Empresas", "👥 Masa Colaboradores", "📤 Carga de Documentos", "⚙️ Admin"]
elif rol == "REVISOR":
    tab_list = ["📈 Avance Global", "🏢 KPIs Empresas", "👥 Masa Colaboradores", "📤 Carga de Documentos"]
else: # Rol USUARIO (Empresa Contratista)
    tab_list = ["📈 Mi Avance", "👥 Masa Laboral", "📤 Carga de Documentos"]

tabs = st.tabs(tab_list)

# --- TAB 1: DASHBOARD (CÁLCULO EXCLUYENDO ESTADO 9) ---
with tabs[0]:
    df_id_emp = cargar_datos(ID_EMPRESAS, "HOJA1")
    if not df_av.empty:
        col_e = next((c for c in df_av.columns if 'EMP' in str(c).upper()), 'EMPRESA')
        df_f = df_av[df_av[col_e] == st.session_state["u_emp"]] if rol == "USUARIO" else df_av
        
        # Selección de columnas para cálculo
        cols_filtro = [mes_sidebar] if mes_sidebar != "AÑO COMPLETO" else cols_m
        df_num = df_f[cols_filtro].apply(pd.to_numeric, errors='coerce')

        # --- LÓGICA DE AUDITORÍA: FILTRAR ESTADO 9 ---
        # El 9 ("No Corresponde") no debe ser parte del universo para el porcentaje
        df_audit = df_num[df_num != 9] 
        total_p = df_audit.count().sum() # Cuenta celdas con valores 1-8, ignora 9 y vacíos
        total_5 = (df_audit == 5).sum().sum()
        perc_real = (total_5 / total_p * 100) if total_p > 0 else 0

        st.header(f"Dashboard de Cumplimiento - {mes_sidebar} {anio_global}")
        
        # KPIs Superiores
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas en Panel", len(df_f))
        k2.metric("% Cumplimiento Auditado", f"{perc_real:.1f}%", help="Este cálculo excluye los periodos marcados como 'No Corresponde Informar'.")
        k3.metric("Empresas 100% Al Día", (df_audit == 5).all(axis=1).sum() if mes_sidebar == "AÑO COMPLETO" else "N/A")

        # Fila de contadores por estado (Detalle numérico)
        st.write("### 📊 Periodos por Estado de Auditoría")
        counts = df_num.stack().value_counts()
        m_cols = st.columns(len(MAPA_ESTADOS))
        for i, (code, name) in enumerate(MAPA_ESTADOS.items()):
            m_cols[i].metric(name, int(counts.get(code, 0)))

        # Gráfico evolutivo (Solo Admin/Revisor)
        if rol != "USUARIO" and mes_sidebar == "AÑO COMPLETO":
            res_evo = []
            for m in cols_m:
                counts_m = df_f[m].value_counts()
                for cod, cant in counts_m.items():
                    if pd.notna(cod):
                        res_evo.append({'Mes': m, 'Estado': MAPA_ESTADOS.get(int(cod), "S/I"), 'Cantidad': cant})
            if res_evo:
                st.plotly_chart(px.bar(pd.DataFrame(res_evo), x='Mes', y='Cantidad', color='Estado', 
                                       color_discrete_map=COLORES_ESTADOS, barmode='stack', title="Evolución Mensual de Estados"), use_container_width=True)

        st.divider()
        # --- DETALLE POR EMPRESA Y DESCARGA (Lógica v.6) ---
        st.subheader("🎯 Análisis Detallado y Certificados")
        emp_sel = st.selectbox("Seleccione Empresa para visualizar:", sorted(df_f[col_e].unique()))
        df_es = df_f[df_f[col_e] == emp_sel]
        
        c_pie, c_hist, c_desc = st.columns([1.5, 1.5, 1])
        with c_pie:
            st.write("**Estatus Anual (Distribución)**")
            pie_data = df_es[cols_m].stack().value_counts().reset_index()
            pie_data.columns = ['Cod', 'Cant']; pie_data['Estado'] = pie_data['Cod'].map(MAPA_ESTADOS)
            st.plotly_chart(px.pie(pie_data, values='Cant', names='Estado', hole=.4, color='Estado', color_discrete_map=COLORES_ESTADOS), use_container_width=True)
        
        with c_hist:
            st.write("**Historial Mes a Mes**")
            hist_view = df_es[cols_m].T.reset_index()
            hist_view.columns = ['Mes', 'Cod']; hist_view['Estado'] = hist_view['Cod'].map(MAPA_ESTADOS)
            st.dataframe(hist_view[['Mes', 'Estado']], use_container_width=True, height=250)
            
        with c_desc:
            st.write("**Descarga de Certificados**")
            mes_pdf = st.selectbox("Mes del Certificado:", cols_m)
            if st.button(f"🔍 Obtener PDF {mes_pdf}"):
                # Buscamos ID de carpeta en la base de empresas
                match_ids = df_id_emp[df_id_emp.iloc[:,1].str.contains(emp_sel[:12], case=False, na=False)]
                if not match_ids.empty:
                    col_id_folder = next((c for c in df_id_emp.columns if 'ID' in str(c).upper() or 'CARPETA' in str(c).upper()), df_id_emp.columns[0])
                    id_f = str(match_ids.iloc[0][col_id_folder]).strip()
                    nombre_f = f"Certificado.{MAPA_MESES_NUM[mes_pdf]}{anio_global}.pdf"
                    with st.spinner("Consultando Drive..."):
                        try:
                            r = requests.get(URL_APPS_SCRIPT, params={"nombre": nombre_f, "carpeta": id_f}, timeout=15)
                            if r.text.startswith("http"):
                                st.success("✅ Certificado encontrado")
                                st.link_button("📥 DESCARGAR ARCHIVO", r.text.strip())
                            else: st.error("⚠️ El certificado aún no ha sido emitido.")
                        except: st.error("❌ Error de comunicación con el servidor.")

# --- TAB 2: MASA LABORAL (ALERTAS DE ESTABILIDAD v.6) ---
with tabs[1]:
    st.header(f"Gestión de Nómina y Dotación - {anio_global}")
    mes_masa = st.selectbox("Seleccione Mes de la Nómina:", list(MAPA_MESES_NUM.keys()), key="m_masa")
    df_m = cargar_datos(ID_COLABORADORES, f"{mes_masa.capitalize()}{anio_global[-2:]}")
    
    if not df_m.empty:
        col_rs = next((c for c in df_m.columns if 'RAZON' in str(c).upper()), df_m.columns[0])
        df_mf = df_m[df_m[col_rs] == st.session_state["u_emp"]] if rol == "USUARIO" else df_m
        
        # --- ALERTAS DE ESTABILIDAD ---
        st.subheader("🚨 Alertas de Estabilidad Laboral")
        col_contrato = next((c for c in df_mf.columns if 'CONTRATO' in str(c).upper()), None)
        if col_contrato:
            pf = df_mf[df_mf[col_contrato].str.contains("PLAZO FIJO", case=False, na=False)]
            if not pf.empty:
                st.warning(f"Se han detectado **{len(pf)}** trabajadores con contrato a **Plazo Fijo**. Revisar vencimientos.")
                with st.expander("Ver lista de contratos a plazo fijo"):
                    st.dataframe(pf, use_container_width=True)
            else: st.success("✅ Todo el personal analizado cuenta con contrato **Indefinido**.")
        
        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("Dotación Total", len(df_mf))
        if 'NACIONALIDAD' in df_mf.columns:
            ext = len(df_mf[~df_mf['NACIONALIDAD'].str.contains('CHILE', na=False)])
            m2.metric("Personal Extranjero", f"{ext} ({(ext/len(df_mf)*100 if len(df_mf)>0 else 0):.1f}%)")
        if 'TOTALHORASEXTRA' in df_mf.columns:
            hhex = pd.to_numeric(df_mf['TOTALHORASEXTRA'], errors='coerce').sum()
            m3.metric("Horas Extra del Mes", f"{hhex:,.0f}")
        
        st.dataframe(df_mf, use_container_width=True)

# --- TAB 3: CARGA DE DOCUMENTOS (PESTAÑA EXCLUSIVA v.7/v.8) ---
with tabs[tab_list.index("📤 Carga de Documentos")]:
    st.header("📤 Pasarela de Carga de Documentación Técnica")
    if mes_sidebar == "AÑO COMPLETO":
        st.warning("⚠️ Para habilitar la carga, debe seleccionar un **Mes Específico** en el panel lateral.")
    else:
        emp_up = st.session_state['u_emp'] if rol == "USUARIO" else st.selectbox("Empresa Destino de Carga:", sorted(df_av[col_e].unique()))
        st.info(f"Subiendo archivos para: **{emp_up}** | Periodo: **{mes_sidebar} {anio_global}**")
        
        docs = [("Liquidaciones de Sueldo", "LIQ"), ("Planilla Previred", "PREVIRED"), ("Certificado F30", "F30"), ("Certificado F30-1", "F30_1"), ("Comprobantes de Pago", "PAGOS")]
        
        for nombre_doc, prefijo in docs:
            c_file, c_btn = st.columns([3, 1])
            arch = c_file.file_uploader(f"Cargar {nombre_doc}", type=["pdf"], key=f"up_{prefijo}")
            if c_btn.button(f"🚀 Subir {prefijo}", key=f"btn_{prefijo}"):
                if arch:
                    # Buscamos ID de carpeta
                    match_up = df_id_emp[df_id_emp.iloc[:,1].str.contains(emp_up[:12], case=False, na=False)]
                    if not match_up.empty:
                        id_folder_up = str(match_up.iloc[0][0]).strip()
                        # Preparamos Payload
                        payload = {
                            "nombre_final": f"{prefijo}_{mes_sidebar}_{anio_global}_{emp_up[:10]}.pdf",
                            "id_carpeta": id_folder_up, "anio": anio_global, 
                            "mes_nombre": MAPA_MESES_CARPETAS[mes_sidebar],
                            "mimetype": "application/pdf",
                            "archivo_base64": base64.b64encode(arch.read()).decode('utf-8')
                        }
                        with st.spinner(f"Subiendo {prefijo}..."):
                            try:
                                res = requests.post(URL_APPS_SCRIPT, data=payload, timeout=40)
                                if "✅" in res.text or "Exito" in res.text:
                                    st.success(f"¡{nombre_doc} subido correctamente!")
                                    st.balloons()
                                else: st.error(f"Error de Google: {res.text}")
                            except: st.error("Se agotó el tiempo de espera. El archivo puede ser muy pesado.")
                else: st.warning("Por favor, seleccione un archivo PDF antes de subir.")

        # --- BOTÓN DE FINALIZACIÓN Y CORREO ---
        st.divider()
        st.subheader("🏁 Finalizar Proceso del Mes")
        st.caption("Al presionar este botón, se enviará un correo de confirmación a C&S Asociados y un comprobante a su casilla.")
        if st.button("✅ ENVIAR NOTIFICACIÓN DE CARGA FINALIZADA", use_container_width=True):
            p_email = {
                "accion": "enviar_email", "empresa": emp_up, "usuario": st.session_state["u_nom"],
                "periodo": f"{mes_sidebar} {anio_global}", "email_usuario": st.session_state["u_email"]
            }
            with st.spinner("Enviando aviso por correo electrónico..."):
                try:
                    res_mail = requests.post(URL_APPS_SCRIPT, data=p_email, timeout=25)
                    if "✅" in res_mail.text:
                        st.success("¡Notificación enviada con éxito! Su proceso ha quedado registrado."); st.balloons()
                    else: st.error(f"Error al enviar: {res_mail.text}")
                except: st.error("No se pudo conectar con el servidor de correos.")

# --- TAB: ADMINISTRACIÓN ---
if rol == "ADMIN":
    with tabs[-1]:
        st.header("⚙️ Centro de Administración")
        st.subheader("📅 Log de Accesos Recientes")
        if st.session_state["log_accesos"]:
            st.table(pd.DataFrame(st.session_state["log_accesos"]))
        st.divider()
        st.subheader("👥 Base de Usuarios Registrados")
        st.dataframe(cargar_datos(ID_USUARIOS, "Usuarios"), use_container_width=True)

st.markdown("---")
st.caption("Portal de Control Laboral CMSG - Desarrollado por C&S Asociados Ltda.")