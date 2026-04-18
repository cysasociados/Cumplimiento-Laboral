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
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS CORPORATIVOS (CSS)
# ==============================================================================
st.set_page_config(
    page_title="Control de Cumplimiento Laboral CMSG", 
    layout="wide", 
    page_icon="🛡️"
)
chile_tz = pytz.timezone('America/Santiago')

# Inyección de CSS: Ocultar 200MB nativo y profesionalizar la interfaz
st.markdown("""
    <style>
    /* Ocultar etiquetas de peso predeterminadas de Streamlit */
    [data-testid="stFileUploaderInstructions"] div { display: none !important; }
    .stFileUploader section div div { display: none !important; }
    .stFileUploader section div { padding-top: 5px !important; }
    
    /* Contenedores de información y tarjetas */
    .caja-instrucciones {
        background-color: #f8f9fa; 
        padding: 25px; 
        border-radius: 15px; 
        border: 1px solid #dee2e6;
        margin-bottom: 20px;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.05);
    }
    
    /* Estética de Botones Maestros */
    .stButton > button { 
        width: 100%; 
        border-radius: 12px; 
        font-weight: 800; 
        height: 3.8em;
        text-transform: uppercase;
        transition: 0.3s ease all;
    }
    
    /* Indicadores KPI en Dashboard */
    [data-testid="stMetricValue"] { 
        font-size: 38px; 
        color: #1E90FF; 
        font-weight: 900; 
    }

    /* Tarjetas de conteo por estado */
    .metric-card {
        text-align: center;
        padding: 12px;
        border-radius: 10px;
        color: white;
        font-weight: bold;
        margin-bottom: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# CONFIGURACIÓN DE CONEXIONES (GOOGLE DRIVE / SHEETS)
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbwt9t5vQBsijY4eI9yF-sI82ctU5HGuW8xE2WVPwUBjOvaqGSGh7bi1DZaazU7NQEavfA/exec"

ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"

# CONFIGURACIÓN DE RECURSOS HUMANOS
CAUSALES_LEGALES_CHILE = [
    "Art. 159 N°1: Mutuo acuerdo de las partes",
    "Art. 159 N°2: Renuncia voluntaria del trabajador",
    "Art. 159 N°4: Vencimiento del plazo convenido",
    "Art. 159 N°5: Conclusión del trabajo o servicio",
    "Art. 160: Conductas indebidas de carácter grave",
    "Art. 161: Necesidades de la empresa",
    "Traslado de Faena / Anexo de Contrato"
]

# MAPEOS DE ESTADO (7 ESTADOS OFICIALES)
MAPA_ESTADOS = {
    1: "Carga Doc.", 2: "En Revision", 3: "Observado", 
    4: "No Cumple", 5: "Cumple", 8: "Sin Info", 9: "No Corresp."
}

COLORES_ESTADOS = {
    "Cumple": "#00FF00", "No Cumple": "#FF0000", "Observado": "#FFFF00", 
    "En Revision": "#1E90FF", "Carga Doc.": "#FF8C00", "Sin Info": "#555555", 
    "No Corresp.": "#8B4513"
}

MESES_LISTA = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC']
MAPA_MESES_NUM = {'ENE':'01','FEB':'02','MAR':'03','ABR':'04','MAY':'05','JUN':'06','JUL':'07','AGO':'08','SEP':'09','OCT':'10','NOV':'11','DIC':'12'}
MAPA_MESES_CARP = {'ENE':'01_ENE','FEB':'02_FEB','MAR':'03_MAR','ABR':'04_ABR','MAY':'05_MAY','JUN':'06_JUN','JUL':'07_JUL','AGO':'08_AGO','SEP':'09_SEP','OCT':'10_OCT','NOV':'11_NOV','DIC':'12_DIC'}

# ==============================================================================
# 2. FUNCIONES DE APOYO (LÓGICA EXPLÍCITA)
# ==============================================================================
def validar_rut(rut):
    """Algoritmo Módulo 11 para validación de RUT chileno."""
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

@st.cache_data(ttl=10)
def cargar_datos(sheet_id, hoja):
    """Cargador de datos CSV robusto y explícito."""
    try:
        url_csv = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={hoja}"
        df = pd.read_csv(url_csv, encoding='utf-8-sig')
        df.columns = [re.sub(r'[^A-Z0-9]', '', str(c).upper()) for c in df.columns]
        return df.dropna(how='all')
    except: return pd.DataFrame()

# ==============================================================================
# 3. SISTEMA DE SEGURIDAD (LOGIN)
# ==============================================================================
if "authenticated" not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    c_log1, c_log2, c_log3 = st.columns([1, 2, 1])
    with c_log2:
        if os.path.exists("CMSG.png"): st.image("CMSG.png", width=220)
        st.title("Acceso Control Laboral")
        p_login = st.text_input("Contraseña Corporativa:", type="password").strip()
        if st.button("INGRESAR AL PORTAL", use_container_width=True):
            df_usuarios = cargar_datos(ID_USUARIOS, "Usuarios")
            if not df_usuarios.empty:
                col_clave_check = next((c for c in df_usuarios.columns if 'CLAVE' in str(c).upper()), 'CLAVE')
                match = df_usuarios[df_usuarios[col_clave_check].astype(str).str.strip() == p_login]
                if not match.empty:
                    u_inf = match.iloc[0]
                    st.session_state.update({
                        "authenticated": True, "u_nom": u_inf.get('NOMBRE',''), 
                        "u_rol": u_inf.get('ROL',''), "u_emp": u_inf.get('EMPRESA',''), 
                        "u_email": u_inf.get('EMAIL','')
                    })
                    st.rerun()
                else: st.error("Contraseña incorrecta.")
    st.stop()

# ==============================================================================
# 4. SIDEBAR Y PERMISOS DE PESTAÑAS (FILTRO EECC)
# ==============================================================================
with st.sidebar:
    if os.path.exists("CMSG.png"): st.image("CMSG.png", use_container_width=True)
    st.markdown(f"👤 **{st.session_state['u_nom']}**")
    st.markdown(f"🏢 **{st.session_state['u_emp']}**")
    st.markdown("---")
    anio_gestion = st.selectbox("Año de Gestión", ["2026", "2025"])
    df_av_maestro = cargar_datos(ID_AVANCE, anio_gestion)
    cols_m_ready = [c for c in df_av_maestro.columns if c in MESES_LISTA] if not df_av_maestro.empty else []
    mes_sidebar_sel = st.selectbox("Periodo de Análisis", ["AÑO COMPLETO"] + cols_m_ready)
    if st.button("🚪 CERRAR SESIÓN"):
        for k_s in list(st.session_state.keys()): del st.session_state[k_s]
        st.rerun()

rol_sergio = st.session_state["u_rol"]
if rol_sergio == "USUARIO":
    t_list_final = ["📉 Dashboard", "📤 Carga Mensual", "👥 DOTACION"]
else:
    t_list_final = ["📉 Dashboard", "📊 KPIS EMPRESAS", "📤 Carga Mensual", "👥 DOTACION", "⚙️ Admin"]

tabs = st.tabs(t_list_final)

# ==============================================================================
# 5. TAB 1: DASHBOARD (INDICADORES + CONTEO + GRÁFICOS)
# ==============================================================================
with tabs[t_list_final.index("📉 Dashboard")]:
    df_id_empresas_db = cargar_datos(ID_EMPRESAS, "HOJA1")
    if not df_av_maestro.empty:
        col_emp_check = next((c for c in df_av_maestro.columns if 'EMP' in str(c).upper()), 'EMPRESA')
        df_f_dash = df_av_maestro[df_av_maestro[col_emp_check] == st.session_state["u_emp"]] if rol_sergio == "USUARIO" else df_av_maestro
        c_cols_filt = [mes_sidebar_sel] if mes_sidebar_sel != "AÑO COMPLETO" else cols_m_ready
        
        # --- LÓGICA DE CUMPLIMIENTO (ESTADO 9 EXCLUIDO) ---
        df_num_dash = df_f_dash[c_cols_filt].apply(pd.to_numeric, errors='coerce')
        df_audit_dash = df_num_dash.copy()
        df_audit_dash[df_audit_dash == 9] = pd.NA # Excluir No Corresponde de la media
        
        total_evaluados = df_audit_dash.count().sum()
        total_cumple = (df_audit_dash == 5).sum().sum()
        perc_final = (total_cumple / total_evaluados * 100) if total_evaluados > 0 else 0
        
        # --- CONTEO CUANTITATIVO POR ESTADO ---
        conteo_data = df_num_dash.stack().value_counts()
        
        st.header(f"Gestión de Cumplimiento - {mes_sidebar_sel} {anio_gestion}")
        
        # FILA 1: KPIs MAESTROS
        km1, km2, km3 = st.columns(3)
        km1.metric("EECC en el Sistema", len(df_f_dash))
        km2.metric("% Cumplimiento Real", f"{perc_final:.1f}%")
        km3.metric("Documentos Aprobados", int(total_cumple))

        st.divider()
        st.subheader("📊 Cantidad de Documentos por Estado")
        
        # FILA 2: CONTADORES POR ESTADO (LOS 7 ESTADOS)
        c_est = st.columns(7)
        for idx, (cod, nom) in enumerate(MAPA_ESTADOS.items()):
            cant_est = int(conteo_data.get(cod, 0))
            color_est = COLORES_ESTADOS.get(nom, "#555555")
            c_est[idx].markdown(f"""
                <div class='metric-card' style='background-color:{color_est};'>
                    <div style='font-size:11px;'>{nom.upper()}</div>
                    <div style='font-size:24px;'>{cant_est}</div>
                </div>
            """, unsafe_allow_html=True)

        # --- GRÁFICO DE BARRAS EVOLUTIVO (EXCLUYE 9) ---
        if mes_sidebar_sel == "AÑO COMPLETO":
            st.divider(); st.write("### 📈 Evolución Mensual de Cumplimiento (Sin N/C)")
            r_evo_dash = []
            for m_loop in cols_m_ready:
                counts_loop = df_f_dash[m_loop].value_counts()
                for cod_loop, cant_loop in counts_loop.items():
                    if pd.notna(cod_loop) and int(cod_loop) != 9:
                        r_evo_dash.append({'Mes': m_loop, 'Estado': MAPA_ESTADOS.get(int(cod_loop), "S/I"), 'Cantidad': cant_loop})
            if r_evo_dash:
                st.plotly_chart(px.bar(pd.DataFrame(r_evo_dash), x='Mes', y='Cantidad', color='Estado', color_discrete_map=COLORES_ESTADOS, barmode='stack'), use_container_width=True)

        st.divider()
        emp_sel_dash = st.selectbox("Analizar Detalle de Empresa:", sorted(df_f_dash[col_emp_check].unique()))
        df_es_dash = df_f_dash[df_f_dash[col_emp_check] == emp_sel_dash]
        col_izq, col_der = st.columns([3, 1.2])
        
        with col_izq:
            # Gráfico de Pie (Excluye el 9)
            p_pie_data = df_es_dash[cols_m_ready].stack().value_counts().reset_index(); p_pie_data.columns = ['Cod', 'Cant']
            p_pie_data = p_pie_data[p_pie_data['Cod'] != 9]
            p_pie_data['Estado'] = p_pie_data['Cod'].map(MAPA_ESTADOS)
            st.plotly_chart(px.pie(p_pie_data, values='Cant', names='Estado', hole=.4, color='Estado', color_discrete_map=COLORES_ESTADOS, title=f"Estatus: {emp_sel_dash}"), use_container_width=True)
            
            # GRILLA DE SEMÁFORO (12 MESES)
            st.write("#### 📜 Semáforo Histórico 12 Meses")
            gm1, gm2 = cols_m_ready[:6], cols_m_ready[6:]
            def render_semaforo(lista_meses):
                cs_sem = st.columns(6)
                for ix_s, m_s in enumerate(lista_meses):
                    val_s = int(df_es_dash[m_s].values[0]) if pd.notna(df_es_dash[m_s].values[0]) else 8
                    txt_s = MAPA_ESTADOS.get(val_s, "S/I"); bg_s = COLORES_ESTADOS.get(txt_s, "#555555"); tc_s = "#000000" if txt_s in ["Observado", "Cumple", "En Revision"] else "#FFFFFF"
                    cs_sem[ix_s].markdown(f"<div style='text-align:center; border:1px solid #ddd; padding:8px; border-radius:8px; background-color:{bg_s}; color:{tc_s}; min-height:65px; display:flex; flex-direction:column; justify-content:center;'><b style='font-size:11px;'>{m_s}</b><br><span style='font-size:8px; font-weight:bold;'>{txt_s.upper()}</span></div>", unsafe_allow_html=True)
            render_semaforo(gm1); st.write(""); render_semaforo(gm2)

        with col_der:
            st.subheader("📄 Certificado")
            mes_pdf_sel = st.selectbox("Mes Certificado:", cols_m_ready, key="s_pdf_dash_v47")
            if st.button("Consultar PDF en Drive", use_container_width=True):
                mt_cert = df_id_empresas_db[df_id_empresas_db['EMPRESA'].str.contains(emp_sel_dash[:10], case=False, na=False)]
                if not mt_cert.empty:
                    id_fc = str(mt_cert.iloc[0]['IDCARPETA']).strip()
                    n_fc = f"Certificado.{MAPA_MESES_NUM[mes_pdf_sel]}{anio_gestion}.pdf"
                    r_fc = requests.get(URL_APPS_SCRIPT, params={"nombre": n_fc, "carpeta": id_fc})
                    if r_fc.text.startswith("http"): st.session_state["link_v47"] = r_fc.text.strip()
            if "link_v47" in st.session_state: st.link_button("📥 DESCARGAR PDF", st.session_state["link_v47"], use_container_width=True)

# ==============================================================================
# 6. TAB: KPIS EMPRESAS (REPORTE DE LOG_DOTACION)
# ==============================================================================
if rol_sergio != "USUARIO":
    with tabs[t_list_final.index("📊 KPIS EMPRESAS")]:
        st.header("📊 Inteligencia de Movimientos de Personal")
        df_log_dot = cargar_datos(ID_COLABORADORES, "Log_Dotacion")
        if not df_log_dot.empty:
            st.write("### Historial Reciente de Altas y Bajas")
            st.dataframe(df_log_dot.sort_values(by=df_log_dot.columns[0], ascending=False), use_container_width=True)
            
            c_graf1, c_graf2 = st.columns(2)
            with c_graf1:
                st.write("#### Movimientos por Empresa")
                st.plotly_chart(px.bar(df_log_dot, x=df_log_dot.columns[1], color=df_log_dot.columns[2], barmode='group'), use_container_width=True)
            with c_graf2:
                st.write("#### Análisis de Causales")
                st.plotly_chart(px.pie(df_log_dot, names=df_log_dot.columns[6]), use_container_width=True)
        else:
            st.info("Aún no se registran movimientos en la base de datos Log_Dotacion.")

# ==============================================================================
# 7. TAB: CARGA MENSUAL (EXPLÍCITA - 8 CARGADORES)
# ==============================================================================
with tabs[t_list_final.index("📤 Carga Mensual")]:
    st.header("📤 Portal de Carga de Información Mensual")
    if mes_sidebar_sel == "AÑO COMPLETO": st.warning("Seleccione un Mes en el sidebar para habilitar la carga.")
    else:
        cm1, cm2 = st.columns([1.7, 1.3])
        with cm2:
            st.markdown("""<div class='caja-instrucciones' style='border-left: 8px solid #FF8C00;'>
            <h4>📖 Instrucciones de Carga</h4><p style='font-size:14px; color:#d9534f;'><b>⚠️ REGLA: MÁXIMO 20MB POR ARCHIVO.</b></p>
            <ul style='font-size:13px; line-height:1.7;'>
                <li><b>1. Liquidaciones:</b> PDF único con todas las del mes.</li>
                <li><b>2. Pagos:</b> PDF con comprobantes de pago/anticipos.</li>
                <li><b>3. Cotizaciones:</b> Planillas de pago Previred.</li>
                <li><b>4. Libro:</b> Archivo CSV de remuneraciones (LRE).</li>
                <li><b>5. Comp. DT:</b> Comprobante de registro LRE en DT.</li>
                <li><b>6. F30:</b> Certificado de Antecedentes actualizado.</li>
                <li><b>7. F30-1:</b> Certificado de Cumplimiento actualizado.</li>
                <li><b>8. Planilla Control:</b> Archivo Excel (.XLS) de seguimiento.</li>
            </ul></div>""", unsafe_allow_html=True)
        with cm1:
            e_u_m = st.session_state['u_emp'] if rol_sergio == "USUARIO" else st.selectbox("EECC a Cargar:", sorted(df_av_maestro[col_emp_check].unique()), key="sel_m_v47")
            st.divider()
            
            def procesar_subida(f, pref, empresa):
                if f and f.size <= 20*1024*1024:
                    mt = df_id_empresas_db[df_id_empresas_db['EMPRESA'].str.contains(empresa[:10], case=False, na=False)]
                    if not mt.empty:
                        idf = str(mt.iloc[0]['IDCARPETA']).strip(); ex = f.name.split('.')[-1]
                        py = {"tipo":"mensual","id_carpeta":idf,"anio":anio_gestion,"nombre_final":f"{pref}_{mes_sidebar_sel}.{ex}","mes_nombre":MAPA_MESES_CARP[mes_sidebar_sel],"archivo_base64":base64.b64encode(f.read()).decode('utf-8')}
                        if requests.post(URL_APPS_SCRIPT, data=py).status_code == 200: st.success(f"Archivo {pref} enviado.")
                elif f: st.error("⚠️ El archivo supera los 20MB permitidos.")

            # CARGADORES UNO POR UNO (PARA MÁXIMA ESTABILIDAD)
            u1 = st.file_uploader("1. Liquidaciones de Sueldo", type=["pdf"], key="u1")
            if st.button("Subir Liquidaciones", key="bu1"): procesar_subida(u1, "LIQ", e_u_m)
            
            u2 = st.file_uploader("2. Comprobantes de Pago", type=["pdf"], key="u2")
            if st.button("Subir Comprobantes", key="bu2"): procesar_subida(u2, "PAGOS", e_u_m)
            
            u3 = st.file_uploader("3. Cotizaciones Previred", type=["pdf"], key="u3")
            if st.button("Subir Cotizaciones", key="bu3"): procesar_subida(u3, "PREVIRED", e_u_m)
            
            u4 = st.file_uploader("4. Libro Remuneraciones (CSV)", type=["csv"], key="u4")
            if st.button("Subir Libro CSV", key="bu4"): procesar_subida(u4, "LIBRO", e_u_m)
            
            u5 = st.file_uploader("5. Comprobante Envío DT", type=["pdf"], key="u5")
            if st.button("Subir Comprobante DT", key="bu5"): procesar_subida(u5, "DT", e_u_m)
            
            u6 = st.file_uploader("6. Certificado F30", type=["pdf"], key="u6")
            if st.button("Subir F30", key="bu6"): procesar_subida(u6, "F30", e_u_m)
            
            u7 = st.file_uploader("7. Certificado F30-1", type=["pdf"], key="u7")
            if st.button("Subir F30-1", key="bu7"): procesar_subida(u7, "F301", e_u_m)
            
            u8 = st.file_uploader("8. Planilla de Control Mensual", type=["xlsx","xls"], key="u8")
            if st.button("Subir Planilla Control", key="bu8"): procesar_subida(u8, "CTRL", e_u_m)

            st.divider()
            if st.button("🏁 FINALIZAR CARGA Y NOTIFICAR", key="btn_not_m_v47", use_container_width=True):
                requests.post(URL_APPS_SCRIPT, data={"accion":"enviar_email","empresa":e_u_m,"usuario":st.session_state["u_nom"],"periodo":f"CARGA MENSUAL: {mes_sidebar_sel} {anio_gestion}"})
                st.success("Notificación enviada al equipo de auditoría.")

# ==============================================================================
# 8. TAB: DOTACION (DINÁMICA ALTA/BAJA - EXPLÍCITA)
# ==============================================================================
with tabs[t_list_final.index("👥 DOTACION")]:
    st.header("👥 Gestión de Movimientos de Personal")
    tipo_m_s = st.radio("Acción a Registrar:", ["🟢 Alta (Nuevo Ingreso)", "🔴 Baja (Egreso/Traslado)"], horizontal=True)
    st.divider()
    
    col_dx1, col_dx2 = st.columns([1.7, 1.3])
    with col_dx2:
        if "Alta" in tipo_m_s:
            color_dx = "#1E90FF"; tit_dx = "Requisitos de Alta (Ingreso)"
            req_dx = """<li>Contrato de Trabajo</li><li>Anexo de Traslado</li><li>Cédula Identidad</li>
                        <li>Certificado Afiliacion AFP</li><li>Certificado Afiliacion Salud</li>
                        <li>Registro Contrato en DT</li><li>Entrega de RIOHS</li>"""
        else:
            color_dx = "#d9534f"; tit_dx = "Requisitos de Baja (Egreso)"
            req_dx = """<li>Finiquito Legalizado + Comprobante Pago</li><li>Anexo Traslado de Faena</li>"""
            
        st.markdown(f"""<div class='caja-instrucciones' style='border-left: 8px solid {color_dx};'>
        <h4>📌 {tit_dx}</h4><p style='font-size:14px; color:#d9534f;'><b>REGLA: MÁXIMO 20MB POR ARCHIVO.</b></p>
        <ul style='font-size:14px; line-height:1.7;'>{req_dx}</ul></div>""", unsafe_allow_html=True)
    
    with col_dx1:
        e_c_dx = st.session_state['u_emp'] if rol_sergio == "USUARIO" else st.selectbox("EECC Responsable:", sorted(df_av_maestro[col_emp_check].unique()), key="sel_d_v47")
        dx_c1, dx_c2 = st.columns(2)
        with dx_c1: t_nom_s = st.text_input("Nombre Trabajador:", placeholder="JUAN PEREZ")
        with dx_c2: 
            t_rut_s = st.text_input("RUT (ej: 12345678-9):", placeholder="12.345.678-9")
            r_ok_s = validar_rut(t_rut_s) if t_rut_s else False
            if t_rut_s: st.caption("✅ RUT Válido" if r_ok_s else "❌ RUT Inválido")
        
        dx_c3, dx_c4 = st.columns(2)
        with dx_c3: t_fec_s = st.date_input("Fecha Efectiva:", datetime.now())
        with dx_c4: t_cau_s = st.selectbox("Causal de Movimiento:", CAUSALES_LEGALES_CHILE) if "Baja" in tipo_m_s else "Nuevo Ingreso"

        st.divider()
        ar_dot_s = st.file_uploader("Cargar Documentación (PDF):", type=["pdf"], accept_multiple_files=True, key="bulk_dot_v47")
        
        # BOTÓN DE REGISTRO EN BASE DE DATOS LOG_DOTACION
        if st.button("🚀 PROCESAR Y REGISTRAR MOVIMIENTO", key="btn_not_d_v47", use_container_width=True):
            if t_nom_s and r_ok_s and ar_dot_s:
                if any(az.size > 20*1024*1024 for az in ar_dot_s): st.error("⚠️ Un archivo excede los 20MB.")
                else:
                    mt_dx = df_id_empresas_db[df_id_empresas_db['EMPRESA'].str.contains(e_c_dx[:10], case=False, na=False)]
                    if not mt_dx.empty:
                        idf_dx = str(mt_dx.iloc[0]['IDCARPETA']).strip()
                        for fi_s in ar_dot_s:
                            requests.post(URL_APPS_SCRIPT, data={"tipo":"colaborador","id_carpeta":idf_dx,"nombre_persona":t_nom_s.upper(),"rut":t_rut_s,"nombre_final":fi_s.name,"archivo_base64":base64.b64encode(fi_s.read()).decode('utf-8')})
                        
                        # Notificación Estructurada y Grabado en Hoja Log_Dotacion
                        body_rrhh = f"Acción: {tipo_m_s}\nTrabajador: {t_nom_s.upper()}\nFecha: {t_fec_s.strftime('%d/%m/%Y')}\nCausal: {t_cau_s}"
                        
                        requests.post(URL_APPS_SCRIPT, data={
                            "accion": "enviar_email", 
                            "tipo": "colaborador", 
                            "empresa": e_c_dx,
                            "usuario": st.session_state["u_nom"],
                            "movimiento": tipo_m_s,
                            "nombre_persona": t_nom_s.upper(),
                            "rut": t_rut_s,
                            "fecha_evento": t_fec_s.strftime('%d/%m/%Y'),
                            "causal": t_cau_s,
                            "periodo": body_rrhh
                        })
                        st.success(f"✅ Movimiento de {t_nom_s.upper()} registrado exitosamente.")
            else: st.warning("Por favor complete todos los datos y cargue los archivos requeridos.")

# --- TAB: ADMIN ---
if rol_sergio != "USUARIO":
    with tabs[4]:
        st.header("⚙️ Gestión Administrativa"); st.dataframe(cargar_datos(ID_USUARIOS, "Usuarios"), use_container_width=True)

st.markdown("---")
st.caption("Control Laboral CMSG | Gestión de Contratistas | Desarrollado por C & S Asociados.")