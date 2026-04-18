import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import base64
import re
import os
from datetime import datetime
import pytz

# ==============================================================================
# 1. CONFIGURACIÓN DE PÁGINA Y LIMPIEZA VISUAL (CSS)
# ==============================================================================
st.set_page_config(
    page_title="Control de Cumplimiento Laboral CMSG", 
    layout="wide", 
    page_icon="🛡️"
)
chile_tz = pytz.timezone('America/Santiago')

# Inyección de CSS para ocultar el mensaje de 200MB y mejorar la interfaz
st.markdown("""
    <style>
    /* Ocultar etiquetas de peso predeterminadas de Streamlit */
    [data-testid="stFileUploaderInstructions"] div { display: none !important; }
    .stFileUploader section div div { display: none !important; }
    .stFileUploader section div { padding-top: 5px !important; }
    /* Estética para cuadros de instrucciones */
    .caja-instrucciones {
        background-color: #fefefe; 
        padding: 20px; 
        border-radius: 12px; 
        border: 1px solid #ddd;
        margin-bottom: 15px;
    }
    .stButton > button { 
        width: 100%; 
        border-radius: 8px; 
        font-weight: bold; 
        height: 3.5em; 
        background-color: #f0f2f6;
    }
    </style>
    """, unsafe_allow_html=True)

# CONFIGURACIÓN DE CONEXIONES EXTERNAS
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbwt9t5vQBsijY4eI9yF-sI82ctU5HGuW8xE2WVPwUBjOvaqGSGh7bi1DZaazU7NQEavfA/exec"

ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"

# CONFIGURACIONES DE RRHH
CAUSALES_LEGALES = [
    "Art. 159 N°1: Mutuo acuerdo de las partes",
    "Art. 159 N°2: Renuncia voluntaria del trabajador",
    "Art. 159 N°4: Vencimiento del plazo convenido",
    "Art. 159 N°5: Conclusión del trabajo o servicio",
    "Art. 160: Conductas indebidas de carácter grave",
    "Art. 161: Necesidades de la empresa",
    "Traslado de Faena / Anexo de Contrato"
]

MAPA_ESTADOS = {1: "Carga Doc.", 2: "En Revision", 3: "Observado", 4: "No Cumple", 5: "Cumple", 8: "Sin Info", 9: "No Corresp."}
COLORES_ESTADOS = {"Cumple": "#00FF00", "No Cumple": "#FF0000", "Observado": "#FFFF00", "En Revision": "#1E90FF", "Carga Doc.": "#FF8C00", "Sin Info": "#555555", "No Corresp.": "#8B4513"}
MESES_LISTA = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC']
MAPA_MESES_NUM = {'ENE':'01','FEB':'02','MAR':'03','ABR':'04','MAY':'05','JUN':'06','JUL':'07','AGO':'08','SEP':'09','OCT':'10','NOV':'11','DIC':'12'}
MAPA_MESES_CARP = {'ENE':'01_ENE','FEB':'02_FEB','MAR':'03_MAR','ABR':'04_ABR','MAY':'05_MAY','JUN':'06_JUN','JUL':'07_JUL','AGO':'08_AGO','SEP':'09_SEP','OCT':'10_OCT','NOV':'11_NOV','DIC':'12_DIC'}

# ==============================================================================
# 2. FUNCIONES DE APOYO (LÓGICA EXPLÍCITA)
# ==============================================================================
def validar_rut(rut):
    """Verifica si el RUT chileno es matemáticamente correcto."""
    rut = str(rut).replace(".", "").replace("-", "").upper()
    if not re.match(r"^\d{7,8}[0-9K]$", rut): return False
    cuerpo, dv = rut[:-1], rut[-1]
    suma = 0; multiplo = 2
    for c in reversed(cuerpo):
        suma += int(c) * multiplo
        multiplo = 2 if multiplo == 7 else multiplo + 1
    dvr = 11 - (suma % 11)
    dvr = 'K' if dvr == 10 else '0' if dvr == 11 else str(dvr)
    return dv == dvr

@st.cache_data(ttl=15)
def cargar_datos(sheet_id, nombre_hoja):
    """Carga datos desde Google Sheets vía CSV de forma robusta."""
    try:
        url_csv = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nombre_hoja}"
        df = pd.read_csv(url_csv, encoding='utf-8-sig')
        df.columns = [re.sub(r'[^A-Z0-9]', '', str(c).upper()) for c in df.columns]
        return df.dropna(how='all')
    except Exception as e:
        st.error(f"Error cargando hoja {nombre_hoja}: {e}")
        return pd.DataFrame()

# ==============================================================================
# 3. SISTEMA DE LOGIN (SEGURO)
# ==============================================================================
if "authenticated" not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    c_l1, c_l2, c_l3 = st.columns([1, 2, 1])
    with c_l2:
        if os.path.exists("CMSG.png"): st.image("CMSG.png", width=220)
        st.title("Control de Cumplimiento CMSG")
        pwd_input = st.text_input("Contraseña Corporativa:", type="password").strip()
        if st.button("Ingresar al Portal", use_container_width=True):
            df_usuarios = cargar_datos(ID_USUARIOS, "Usuarios")
            if not df_usuarios.empty:
                # Buscamos la columna de clave sin importar variaciones de nombre
                col_c_login = next((c for c in df_usuarios.columns if 'CLAVE' in str(c).upper()), 'CLAVE')
                match = df_usuarios[df_usuarios[col_c_login].astype(str).str.strip() == pwd_input]
                if not match.empty:
                    u_data = match.iloc[0]
                    st.session_state.update({
                        "authenticated": True, 
                        "u_nom": u_data.get('NOMBRE',''), 
                        "u_rol": u_data.get('ROL',''), 
                        "u_emp": u_data.get('EMPRESA',''), 
                        "u_email": u_data.get('EMAIL','')
                    })
                    st.rerun()
                else: st.error("Contraseña incorrecta.")
    st.stop()

# ==============================================================================
# 4. SIDEBAR Y PERMISOS DE PESTAÑAS
# ==============================================================================
with st.sidebar:
    if os.path.exists("CMSG.png"): st.image("CMSG.png", use_container_width=True)
    st.markdown(f"👤 **{st.session_state['u_nom']}**")
    st.markdown(f"🏢 **{st.session_state['u_emp']}**")
    st.markdown("---")
    anio_sel = st.selectbox("Año de Gestión", ["2026", "2025"])
    df_avance_global = cargar_datos(ID_AVANCE, anio_sel)
    cols_meses_disp = [c for c in df_avance_global.columns if c in MESES_LISTA] if not df_avance_global.empty else []
    mes_filt_sidebar = st.selectbox("Mes de Análisis", ["AÑO COMPLETO"] + cols_meses_disp)
    st.write("")
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# LÓGICA DE PERMISOS DE SERGIO: EECC (Usuario) solo ve 1, 3 y 4.
u_rol_actual = st.session_state["u_rol"]
if u_rol_actual == "USUARIO":
    tab_list_final = ["📉 Dashboard", "📤 Carga Mensual", "👥 DOTACION"]
else:
    tab_list_final = ["📉 Dashboard", "📊 KPIS EMPRESAS", "📤 Carga Mensual", "👥 DOTACION", "⚙️ Admin"]

tabs_maestras = st.tabs(tab_list_final)

# ==============================================================================
# 5. PESTAÑA 1: DASHBOARD (RESTAURADA COMPLETA)
# ==============================================================================
with tabs_maestras[tab_list_final.index("📉 Dashboard")]:
    df_id_empresas_db = cargar_datos(ID_EMPRESAS, "HOJA1")
    if not df_avance_global.empty:
        col_emp_check = next((c for c in df_avance_global.columns if 'EMP' in str(c).upper()), 'EMPRESA')
        # Filtro de seguridad por empresa
        df_f_dash = df_avance_global[df_avance_global[col_emp_check] == st.session_state["u_emp"]] if u_rol_actual == "USUARIO" else df_avance_global
        c_filt_dash = [mes_filt_sidebar] if mes_filt_sidebar != "AÑO COMPLETO" else cols_meses_disp
        
        df_num_dash = df_f_dash[c_filt_dash].apply(pd.to_numeric, errors='coerce')
        df_audit_dash = df_num_dash.copy(); df_audit_dash[df_audit_dash == 9] = pd.NA
        total_puntos = df_audit_dash.count().sum()
        total_cumple = (df_audit_dash == 5).sum().sum()
        perc_dash = (total_cumple / total_puntos * 100) if total_puntos > 0 else 0
        
        st.header(f"Seguimiento Laboral - {mes_filt_sidebar} {anio_sel}")
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas", len(df_f_dash))
        k2.metric("% Cumplimiento Real", f"{perc_dash:.1f}%")
        k3.metric("Al Día (Cumple)", int(total_cumple))

        if mes_filt_sidebar == "AÑO COMPLETO":
            st.divider(); st.write("### 📈 Evolución Mensual de Estados")
            res_evo_dash = []
            for m_item in cols_meses_disp:
                counts_item = df_f_dash[m_item].value_counts()
                for cod_item, cant_item in counts_item.items():
                    if pd.notna(cod_item):
                        res_evo_dash.append({'Mes': m_item, 'Estado': MAPA_ESTADOS.get(int(cod_item), "S/I"), 'Cantidad': cant_item})
            if res_evo_dash:
                st.plotly_chart(px.bar(pd.DataFrame(res_evo_dash), x='Mes', y='Cantidad', color='Estado', color_discrete_map=COLORES_ESTADOS, barmode='stack'), use_container_width=True)

        st.divider(); emp_sel_dash = st.selectbox("Empresa para Detalle:", sorted(df_f_dash[col_emp_check].unique()))
        df_es_dash = df_f_dash[df_f_dash[col_emp_check] == emp_sel_dash]
        c_iz_dash, c_de_dash = st.columns([3, 1.2])
        with c_iz_dash:
            p_d_dash = df_es_dash[cols_meses_disp].stack().value_counts().reset_index(); p_d_dash.columns = ['Cod', 'Cant']
            p_d_dash['Estado'] = p_d_dash['Cod'].map(MAPA_ESTADOS)
            st.plotly_chart(px.pie(p_d_dash[p_d_dash['Cod'] != 9], values='Cant', names='Estado', hole=.4, color='Estado', color_discrete_map=COLORES_ESTADOS, title=f"Estatus: {emp_sel_dash}"), use_container_width=True)
            st.write("#### 📜 Historial de Estados (12 Meses)"); m1_h, m2_h = cols_meses_disp[:6], cols_meses_disp[6:]
            def draw_grid_dash(lista_meses):
                cs_dash = st.columns(6)
                for i_h, m_h in enumerate(lista_meses):
                    val_h = int(df_es_dash[m_h].values[0]) if pd.notna(df_es_dash[m_h].values[0]) else 8
                    txt_h = MAPA_ESTADOS.get(val_h, "S/I"); bg_h = COLORES_ESTADOS.get(txt_h, "#555555"); tc_h = "#000000" if txt_h in ["Observado", "Cumple", "En Revision"] else "#FFFFFF"
                    cs_dash[i_h].markdown(f"<div style='text-align:center; border:1px solid #ddd; padding:8px; border-radius:8px; background-color:{bg_h}; color:{tc_h}; min-height:65px; display:flex; flex-direction:column; justify-content:center;'><b style='font-size:11px;'>{m_h}</b><br><span style='font-size:8px; font-weight:bold;'>{txt_h.upper()}</span></div>", unsafe_allow_html=True)
            draw_grid_dash(m1_h); st.write(""); draw_grid_dash(m2_h)
        with c_de_dash:
            st.subheader("📄 Certificado")
            mes_pdf_sel = st.selectbox("Mes Certificado:", cols_meses_disp, key="s_pdf_maestro")
            if st.button("Generar Enlace Descarga", use_container_width=True):
                match_id_cert = df_id_empresas_db[df_id_empresas_db['EMPRESA'].str.contains(emp_sel_dash[:10], case=False, na=False)]
                if not match_id_cert.empty:
                    id_f_cert = str(match_id_cert.iloc[0]['IDCARPETA']).strip()
                    n_f_cert = f"Certificado.{MAPA_MESES_NUM[mes_pdf_sel]}{anio_sel}.pdf"
                    r_cert = requests.get(URL_APPS_SCRIPT, params={"nombre": n_f_cert, "carpeta": id_f_cert})
                    if r_cert.text.startswith("http"): st.session_state["link_final"] = r_cert.text.strip()
                    else: st.error("No disponible en Drive.")
            if "link_final" in st.session_state: st.link_button("📥 DESCARGAR PDF", st.session_state["link_final"], use_container_width=True)

# ==============================================================================
# 6. PESTAÑA 2: KPIS EMPRESAS (OCULTO PARA EECC)
# ==============================================================================
if u_rol_actual != "USUARIO":
    with tabs_maestras[tab_list_final.index("📊 KPIS EMPRESAS")]:
        st.header(f"📊 Dotación por Empresa - {anio_sel}")
        mes_kpi_v = st.selectbox("Seleccione Mes:", MESES_LISTA, key="m_kpi_view_final")
        df_kpi_data = cargar_datos(ID_COLABORADORES, f"{mes_kpi_v.capitalize()}{anio_sel[-2:]}")
        if not df_kpi_data.empty: st.dataframe(df_kpi_data, use_container_width=True)

# ==============================================================================
# 7. PESTAÑA 3: CARGA MENSUAL (EXPLÍCITA - 8 DOCUMENTOS)
# ==============================================================================
with tabs_maestras[tab_list_final.index("📤 Carga Mensual")]:
    st.header("📤 Carga de Documentación Mensual")
    if mes_filt_sidebar == "AÑO COMPLETO": st.warning("Seleccione un Mes en el sidebar para cargar.")
    else:
        col_m1, col_m2 = st.columns([1.7, 1.3])
        with col_m2:
            st.markdown("""<div class='caja-instrucciones' style='border-left: 8px solid #FF8C00;'>
            <h4>📖 Instrucciones de Carga</h4><p style='font-size:14px; color:#d9534f;'><b>⚠️ MÁXIMO 20MB POR ARCHIVO.</b></p>
            <ul style='font-size:14px; line-height:1.6;'>
                <li>Liquidaciones de Sueldos.</li><li>Comprobantes de Pago/Anticipo.</li><li>Cotizaciones Previred.</li>
                <li>Libro Remuneración DT (CSV).</li><li>Comprobante LRE en DT.</li><li>Certificado F30 Vigente.</li>
                <li>Certificado F30-1 Vigente.</li><li>Planilla Control Mensual.</li>
            </ul></div>""", unsafe_allow_html=True)
        with col_m1:
            emp_u_m = st.session_state['u_emp'] if u_rol_actual == "USUARIO" else st.selectbox("Empresa:", sorted(df_avance_global[col_emp_check].unique()), key="sel_emp_m")
            st.divider()
            
            # FUNCION DE SUBIDA INDIVIDUAL PARA EVITAR NAMEERROR
            def subir_mensual(archivo, prefijo, empresa):
                if archivo and archivo.size <= 20*1024*1024:
                    mt_m = df_id_empresas_db[df_id_empresas_db['EMPRESA'].str.contains(empresa[:10], case=False, na=False)]
                    if not mt_m.empty:
                        id_f_m = str(mt_m.iloc[0]['IDCARPETA']).strip(); ext_m = archivo.name.split('.')[-1]
                        payload_m = {"tipo":"mensual","id_carpeta":id_f_m,"anio":anio_sel,"nombre_final":f"{prefijo}_{mes_filt_sidebar}.{ext_m}","mes_nombre":MAPA_MESES_CARP[mes_filt_sidebar],"archivo_base64":base64.b64encode(archivo.read()).decode('utf-8')}
                        if requests.post(URL_APPS_SCRIPT, data=payload_m).status_code == 200: st.success(f"{prefijo} subido.")
                elif archivo: st.error("⚠️ El archivo supera los 20MB.")

            # CARGADORES EXPLÍCITOS (8 LÍNEAS)
            f1 = st.file_uploader("1. Liquidaciones Sueldo", type=["pdf"], key="f1")
            if st.button("Subir Liquidaciones", key="b1"): subir_mensual(f1, "LIQ", emp_u_m)
            
            f2 = st.file_uploader("2. Comprobantes Pago", type=["pdf"], key="f2")
            if st.button("Subir Comprobantes", key="b2"): subir_mensual(f2, "PAGOS", emp_u_m)
            
            f3 = st.file_uploader("3. Cotizaciones", type=["pdf"], key="f3")
            if st.button("Subir Cotizaciones", key="b3"): subir_mensual(f3, "PREVIRED", emp_u_m)
            
            f4 = st.file_uploader("4. Libro Remuneraciones (CSV)", type=["csv"], key="f4")
            if st.button("Subir Libro", key="b4"): subir_mensual(f4, "LIBRO", emp_u_m)
            
            f5 = st.file_uploader("5. Comprobante Envío DT", type=["pdf"], key="f5")
            if st.button("Subir Comprobante DT", key="b5"): subir_mensual(f5, "DT", emp_u_m)
            
            f6 = st.file_uploader("6. Certificado F30", type=["pdf"], key="f6")
            if st.button("Subir F30", key="b6"): subir_mensual(f6, "F30", emp_u_m)
            
            f7 = st.file_uploader("7. Certificado F30-1", type=["pdf"], key="f7")
            if st.button("Subir F30-1", key="b7"): subir_mensual(f7, "F301", emp_u_m)
            
            f8 = st.file_uploader("8. Planilla Control (.XLS)", type=["xlsx","xls"], key="f8")
            if st.button("Subir Planilla", key="b8"): subir_mensual(f8, "CTRL", emp_u_m)

            st.divider()
            if st.button("🏁 FINALIZAR Y NOTIFICAR CARGA MENSUAL", key="btn_notif_m_final", use_container_width=True):
                requests.post(URL_APPS_SCRIPT, data={"accion":"enviar_email","empresa":emp_u_m,"usuario":st.session_state["u_nom"],"periodo":f"Carga Mensual: {mes_filt_sidebar} {anio_sel}"})
                st.success("Notificación enviada con éxito.")

# ==============================================================================
# 8. PESTAÑA 4: DOTACION (ALTAS Y BAJAS DINÁMICAS - EXPLÍCITA)
# ==============================================================================
with tabs_maestras[tab_list_final.index("👥 DOTACION")]:
    st.header("👥 Gestión de Movimientos de Personal")
    tipo_mov = st.radio("Acción a Realizar:", ["🟢 Alta (Ingreso de Trabajador)", "🔴 Baja (Egreso/Traslado)"], horizontal=True)
    st.divider()
    
    col_d1, col_d2 = st.columns([1.7, 1.3])
    with col_d2:
        # Lógica de requisitos dinámica según clic de Sergio
        if "Alta" in tipo_mov:
            color_d = "#1E90FF"; tit_d = "Requisitos de Ingreso"
            txt_req = """<li>Contrato de Trabajo</li><li>Anexo de Traslado</li><li>Cédula Identidad</li>
                         <li>Cert. AFP</li><li>Cert. Salud</li><li>Registro DT</li><li>Entrega RIOHS</li>"""
        else:
            color_d = "#d9534f"; tit_d = "Requisitos de Baja"
            txt_req = """<li>Finiquito Legalizado</li><li>Comprobante de Pago</li><li>Anexo Traslado de Faena</li>"""
            
        st.markdown(f"""<div class='caja-instrucciones' style='border-left: 8px solid {color_d};'>
        <h4>📌 {tit_d}</h4><p style='font-size:14px; color:#d9534f;'><b>⚠️ MÁXIMO 20MB POR ARCHIVO.</b></p>
        <ul style='font-size:14px; line-height:1.6;'>{txt_req}</ul></div>""", unsafe_allow_html=True)
    
    with col_d1:
        emp_c_d = st.session_state['u_emp'] if u_rol_actual == "USUARIO" else st.selectbox("EECC:", sorted(df_avance_global[col_emp_check].unique()), key="sel_emp_d")
        ci1, ci2 = st.columns(2)
        with ci1: t_nombre = st.text_input("Nombre Completo Trabajador:", placeholder="JUAN PEREZ SOTO")
        with ci2: 
            t_rut = st.text_input("RUT Trabajador:", placeholder="12.345.678-9")
            r_ok_d = validar_rut(t_rut) if t_rut else False
            if t_rut: st.caption("✅ RUT Válido" if r_ok_d else "❌ RUT Inválido")
        
        ci3, ci4 = st.columns(2)
        with ci3: t_fecha = st.date_input("Fecha Efectiva del Movimiento:", datetime.now())
        with ci4:
            if "Baja" in tipo_mov: t_causal = st.selectbox("Causal de Egreso:", CAUSALES_LEGALES)
            else: t_causal = "Nuevo Ingreso"

        st.divider()
        archivos_d = st.file_uploader("Arrastre toda la documentación requerida (PDF):", type=["pdf"], accept_multiple_files=True, key="bulk_dot_maestro")
        
        # BOTÓN DE CARGA DE PERSONAL (RESTAURADO)
        if st.button("🚀 FINALIZAR Y NOTIFICAR MOVIMIENTO", key="btn_notif_d_final", use_container_width=True):
            if t_nombre and r_ok_d and archivos_d:
                if any(ar.size > 20*1024*1024 for ar in archivos_d): st.error("⚠️ Uno o más archivos exceden los 20MB.")
                else:
                    mt_d = df_id_empresas_db[df_id_empresas_db['EMPRESA'].str.contains(emp_c_d[:10], case=False, na=False)]
                    if not mt_d.empty:
                        id_f_d = str(mt_d.iloc[0]['IDCARPETA']).strip()
                        for ar_item in archivos_d:
                            requests.post(URL_APPS_SCRIPT, data={"tipo":"colaborador","id_carpeta":id_f_d,"nombre_persona":t_nombre.upper(),"rut":t_rut,"nombre_final":ar_item.name,"archivo_base64":base64.b64encode(ar_item.read()).decode('utf-8')})
                        
                        # Notificación Limpia (Sin contaminar con 'Periodo')
                        detalle_email = f"Movimiento: {tipo_mov}\nTrabajador: {t_nombre.upper()}\nFecha Evento: {t_fecha.strftime('%d/%m/%Y')}\nCausal: {t_causal}"
                        requests.post(URL_APPS_SCRIPT, data={"accion":"enviar_email", "empresa":emp_c_d, "usuario":st.session_state["u_nom"], "periodo": detalle_email})
                        st.success(f"✅ Notificado: {tipo_mov} de {t_nombre.upper()}")
            else: st.warning("Complete Nombre, RUT válido y cargue los archivos necesarios.")

# --- TAB 5: ADMIN ---
if u_rol_actual != "USUARIO":
    with tabs_maestras[tab_list_final.index("⚙️ Admin")]:
        st.header("⚙️ Configuración Administrativa"); st.dataframe(cargar_datos(ID_USUARIOS, "Usuarios"), use_container_width=True)

st.markdown("---")
st.caption("Control Laboral CMSG | Desarrollado por C & S Asociados Ltda.")