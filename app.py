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
# 1. CONFIGURACIÓN Y ESTILOS CORPORATIVOS (CSS)
# ==============================================================================
st.set_page_config(
    page_title="Control de Cumplimiento Laboral CMSG", 
    layout="wide", 
    page_icon="🛡️"
)
chile_tz = pytz.timezone('America/Santiago')

# Inyección de CSS para limpiar la UI y profesionalizar el Dashboard
st.markdown("""
    <style>
    /* Ocultar etiquetas de peso predeterminadas de Streamlit */
    [data-testid="stFileUploaderInstructions"] div { display: none !important; }
    .stFileUploader section div div { display: none !important; }
    .stFileUploader section div { padding-top: 5px !important; }
    
    /* Contenedores de información */
    .caja-instrucciones {
        background-color: #f8f9fa; 
        padding: 25px; 
        border-radius: 15px; 
        border: 1px solid #dee2e6;
        margin-bottom: 20px;
    }
    
    /* Estilo de Botones Maestros */
    .stButton > button { 
        width: 100%; 
        border-radius: 12px; 
        font-weight: 800; 
        height: 3.8em;
        text-transform: uppercase;
        transition: 0.3s ease;
    }
    
    /* Estilo para métricas KPI */
    [data-testid="stMetricValue"] { 
        font-size: 38px; 
        color: #1E90FF; 
        font-weight: 900; 
    }
    
    /* Estilo para los contadores por estado en Dashboard */
    .metric-card {
        text-align: center;
        padding: 10px;
        border-radius: 10px;
        color: white;
        font-weight: bold;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# URL DEL MOTOR DE CARGA
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbwt9t5vQBsijY4eI9yF-sI82ctU5HGuW8xE2WVPwUBjOvaqGSGh7bi1DZaazU7NQEavfA/exec"

# IDS DE BASES DE DATOS
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"

# CAUSALES RRHH
CAUSALES_FINIQUITO_LIST = [
    "Art. 159 N°1: Mutuo acuerdo", "Art. 159 N°2: Renuncia voluntaria",
    "Art. 159 N°4: Vencimiento de plazo", "Art. 159 N°5: Conclusión de servicio",
    "Art. 160: Conductas indebidas", "Art. 161: Necesidades de la empresa",
    "Traslado de Faena / Anexo Contrato"
]

# MAPEO DE 7 ESTADOS (INCLUYENDO ESTADO 9)
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
# 2. FUNCIONES DE APOYO
# ==============================================================================
def validar_rut(rut):
    """Módulo 11 para RUT chileno."""
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
    """Cargador CSV robusto."""
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={hoja}"
        df = pd.read_csv(url, encoding='utf-8-sig')
        df.columns = [re.sub(r'[^A-Z0-9]', '', str(c).upper()) for c in df.columns]
        return df.dropna(how='all')
    except: return pd.DataFrame()

# ==============================================================================
# 3. ACCESO (LOGIN)
# ==============================================================================
if "authenticated" not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    c_l1, c_l2, c_l3 = st.columns([1, 2, 1])
    with c_l2:
        if os.path.exists("CMSG.png"): st.image("CMSG.png", width=220)
        st.title("Portal de Cumplimiento CMSG")
        pwd_inp = st.text_input("Contraseña Corporativa:", type="password").strip()
        if st.button("Ingresar al Sistema", use_container_width=True):
            df_u = cargar_datos(ID_USUARIOS, "Usuarios")
            if not df_u.empty:
                col_c = next((c for c in df_u.columns if 'CLAVE' in str(c).upper()), 'CLAVE')
                match = df_u[df_u[col_c].astype(str).str.strip() == pwd_inp]
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
# 4. SIDEBAR Y PERMISOS
# ==============================================================================
with st.sidebar:
    if os.path.exists("CMSG.png"): st.image("CMSG.png", use_container_width=True)
    st.markdown(f"👤 **{st.session_state['u_nom']}**\n🏢 **{st.session_state['u_emp']}**")
    st.markdown("---")
    anio_sel = st.selectbox("Año de Gestión", ["2026", "2025"])
    df_av_global = cargar_datos(ID_AVANCE, anio_sel)
    cols_m_disp = [c for c in df_av_global.columns if c in MESES_LISTA] if not df_av_global.empty else []
    mes_sidebar = st.selectbox("Mes de Análisis", ["AÑO COMPLETO"] + cols_m_disp)
    if st.button("🚪 Cerrar Sesión"):
        for k_s in list(st.session_state.keys()): del st.session_state[k_s]
        st.rerun()

rol_u = st.session_state["u_rol"]
if rol_u == "USUARIO":
    t_list = ["📉 Dashboard", "📤 Carga Mensual", "👥 DOTACION"]
else:
    t_list = ["📉 Dashboard", "📊 KPIS EMPRESAS", "📤 Carga Mensual", "👥 DOTACION", "⚙️ Admin"]

tabs = st.tabs(t_list)

# ==============================================================================
# 5. TAB 1: DASHBOARD (INTELIGENCIA Y CONTEO POR ESTADO)
# ==============================================================================
with tabs[t_list.index("📉 Dashboard")]:
    df_id_db_all = cargar_datos(ID_EMPRESAS, "HOJA1")
    if not df_av_global.empty:
        col_e_ch = next((c for c in df_av_global.columns if 'EMP' in str(c).upper()), 'EMPRESA')
        df_f_dash = df_av_global[df_av_global[col_e_ch] == st.session_state["u_emp"]] if rol_u == "USUARIO" else df_av_global
        c_cols_dash = [mes_sidebar] if mes_sidebar != "AÑO COMPLETO" else cols_m_disp
        
        # --- CÁLCULO ESTADÍSTICO (ESTADO 9 EXCLUIDO DE LA MEDIA) ---
        df_num_dash = df_f_dash[c_cols_dash].apply(pd.to_numeric, errors='coerce')
        df_audit_dash = df_num_dash.copy()
        df_audit_dash[df_audit_dash == 9] = pd.NA # Exclusión del 9 para el promedio
        
        tp_total = df_audit_dash.count().sum()
        tp_cumple = (df_audit_dash == 5).sum().sum()
        perc_promedio = (tp_cumple / tp_total * 100) if tp_total > 0 else 0
        
        # --- CONTEO EXPLÍCITO POR ESTADO ---
        # Stackeamos todos los datos evaluados para contar frecuencias
        conteo_serie = df_num_dash.stack().value_counts()
        
        st.header(f"Seguimiento General - {mes_sidebar} {anio_sel}")
        
        # FILA 1: KPIs PRINCIPALES
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas Evaluadas", len(df_f_dash))
        k2.metric("% Cumplimiento Promedio", f"{perc_promedio:.1f}%")
        k3.metric("Documentos 'Cumple'", int(tp_cumple))

        st.divider()
        st.subheader("📊 Cantidad de Documentos por Estado")
        
        # FILA 2: CONTADORES POR ESTADO (LOS 7 ESTADOS)
        # Creamos 7 columnas para mostrar la cantidad de cada uno
        c_est = st.columns(7)
        for idx, (cod, nom) in enumerate(MAPA_ESTADOS.items()):
            cantidad = int(conteo_serie.get(cod, 0))
            color_b = COLORES_ESTADOS.get(nom, "#555555")
            c_est[idx].markdown(f"""
                <div class='metric-card' style='background-color:{color_b};'>
                    <div style='font-size:12px;'>{nom.upper()}</div>
                    <div style='font-size:24px;'>{cantidad}</div>
                </div>
            """, unsafe_allow_html=True)

        # --- GRÁFICO EVOLUTIVO (BARRAS) ---
        if mes_sidebar == "AÑO COMPLETO":
            st.write("### 📈 Evolución Histórica (Excluyendo N/C)")
            r_evo_dash = []
            for m_i in cols_m_disp:
                counts_m = df_f_dash[m_i].value_counts()
                for cod_m, cant_m in counts_m.items():
                    if pd.notna(cod_m) and int(cod_m) != 9:
                        r_evo_dash.append({'Mes': m_i, 'Estado': MAPA_ESTADOS.get(int(cod_m), "S/I"), 'Cantidad': cant_m})
            if r_evo_dash:
                st.plotly_chart(px.bar(pd.DataFrame(r_evo_dash), x='Mes', y='Cantidad', color='Estado', color_discrete_map=COLORES_ESTADOS, barmode='stack'), use_container_width=True)

        st.divider()
        emp_sel_dash = st.selectbox("Detalle por Empresa:", sorted(df_f_dash[col_e_ch].unique()))
        df_es_dash = df_f_dash[df_f_dash[col_e_ch] == emp_sel_dash]
        col_iz, col_de = st.columns([3, 1.2])
        
        with col_iz:
            # Pie Chart detallado
            p_pie = df_es_dash[cols_m_disp].stack().value_counts().reset_index(); p_pie.columns = ['Cod', 'Cant']
            p_pie = p_pie[p_pie['Cod'] != 9] # Filtro de gráfico
            p_pie['Estado'] = p_pie['Cod'].map(MAPA_ESTADOS)
            st.plotly_chart(px.pie(p_pie, values='Cant', names='Estado', hole=.4, color='Estado', color_discrete_map=COLORES_ESTADOS, title=f"Estatus: {emp_sel_dash}"), use_container_width=True)
            
            # Semáforo de 12 Meses
            st.write("#### 📜 Semáforo Mensual")
            sm1, sm2 = cols_m_disp[:6], cols_m_disp[6:]
            def render_sem(lista):
                cs_s = st.columns(6)
                for i_s, m_s in enumerate(lista):
                    v_s = int(df_es_dash[m_s].values[0]) if pd.notna(df_es_dash[m_s].values[0]) else 8
                    t_s = MAPA_ESTADOS.get(v_s, "S/I"); bg_s = COLORES_ESTADOS.get(t_s, "#555555"); tc_s = "#000000" if t_s in ["Observado", "Cumple", "En Revision"] else "#FFFFFF"
                    cs_s[i_s].markdown(f"<div style='text-align:center; border:1px solid #ddd; padding:8px; border-radius:8px; background-color:{bg_s}; color:{tc_s}; min-height:65px; display:flex; flex-direction:column; justify-content:center;'><b style='font-size:11px;'>{m_s}</b><br><span style='font-size:8px; font-weight:bold;'>{t_s.upper()}</span></div>", unsafe_allow_html=True)
            render_sem(sm1); st.write(""); render_sem(sm2)

        with col_de:
            st.subheader("📄 Certificado")
            m_pdf_sel = st.selectbox("Mes Certificado:", cols_m_disp, key="s_pdf_dash_v45")
            if st.button("Consultar Certificado", use_container_width=True):
                mt_c = df_id_db_all[df_id_db_all['EMPRESA'].str.contains(emp_sel_dash[:10], case=False, na=False)]
                if not mt_c.empty:
                    id_fc = str(mt_c.iloc[0]['IDCARPETA']).strip()
                    n_fc = f"Certificado.{MAPA_MESES_NUM[m_pdf_sel]}{anio_sel}.pdf"
                    r_c = requests.get(URL_APPS_SCRIPT, params={"nombre": n_fc, "carpeta": id_fc})
                    if r_c.text.startswith("http"): st.session_state["link_v45"] = r_c.text.strip()
            if "link_v45" in st.session_state: st.link_button("📥 DESCARGAR PDF", st.session_state["link_v45"], use_container_width=True)

# ==============================================================================
# 6. TAB: KPIS EMPRESAS (SÓLO ADMIN)
# ==============================================================================
if rol_u != "USUARIO":
    with tabs[t_list.index("📊 KPIS EMPRESAS")]:
        st.header(f"📊 Dotación Vigente - {anio_sel}")
        mes_k_v = st.selectbox("Mes Visualización:", MESES_LISTA, key="m_kpi_v45")
        df_kpi_v = cargar_datos(ID_COLABORADORES, f"{mes_k_v.capitalize()}{anio_sel[-2:]}")
        if not df_kpi_v.empty: st.dataframe(df_kpi_v, use_container_width=True)

# ==============================================================================
# 7. TAB: CARGA MENSUAL (EXPLÍCITA - 8 CARGADORES)
# ==============================================================================
with tabs[t_list.index("📤 Carga Mensual")]:
    st.header("📤 Portal de Carga Documental Mensual")
    if mes_sidebar == "AÑO COMPLETO": st.warning("Seleccione un Mes en el sidebar para cargar.")
    else:
        col_m_i, col_m_t = st.columns([1.7, 1.3])
        with col_m_t:
            st.markdown("""<div class='caja-instrucciones' style='border-left: 8px solid #FF8C00;'>
            <h4>📖 Instrucciones de Carga</h4><p style='font-size:14px; color:#d9534f;'><b>⚠️ REGLA: MÁXIMO 20MB POR ARCHIVO.</b></p>
            <ul style='font-size:13px; line-height:1.7;'>
                <li>Liquidaciones Sueldo (PDF único).</li><li>Pagos de Anticipos/Sueldos (PDF único).</li>
                <li>Cotizaciones Previred.</li><li>Libro Remuneraciones CSV.</li>
                <li>Comp. Envío LRE DT.</li><li>F30 / F30-1 Vigentes.</li>
                <li>Planilla Control Mensual (.XLS).</li>
            </ul></div>""", unsafe_allow_html=True)
        with col_m_i:
            e_u_m = st.session_state['u_emp'] if rol_u == "USUARIO" else st.selectbox("Empresa Evaluada:", sorted(df_av_global[col_e_ch].unique()), key="sel_m_v45")
            st.divider()
            
            def pro_upload(file, pref, emp_nombre):
                if file and file.size <= 20*1024*1024:
                    mt = df_id_db_all[df_id_db_all['EMPRESA'].str.contains(emp_nombre[:10], case=False, na=False)]
                    if not mt.empty:
                        idf = str(mt.iloc[0]['IDCARPETA']).strip(); ex = file.name.split('.')[-1]
                        py = {"tipo":"mensual","id_carpeta":idf,"anio":anio_sel,"nombre_final":f"{pref}_{mes_sidebar}.{ex}","mes_nombre":MAPA_MESES_CARP[mes_sidebar],"archivo_base64":base64.b64encode(file.read()).decode('utf-8')}
                        if requests.post(URL_APPS_SCRIPT, data=py).status_code == 200: st.success(f"{pref} cargado con éxito.")
                elif file: st.error("⚠️ El archivo supera los 20MB permitidos.")

            # CARGADORES UNO POR UNO
            u1=st.file_uploader("1. Liquidaciones", type=["pdf"], key="u1"); b1=st.button("Subir Liquidaciones", key="b1")
            if b1: pro_upload(u1, "LIQ", e_u_m)
            u2=st.file_uploader("2. Comprobantes Pago", type=["pdf"], key="u2"); b2=st.button("Subir Comprobantes", key="b2")
            if b2: pro_upload(u2, "PAGOS", e_u_m)
            u3=st.file_uploader("3. Cotizaciones Previred", type=["pdf"], key="u3"); b3=st.button("Subir Cotizaciones", key="b3")
            if b3: pro_upload(u3, "PREVIRED", e_u_m)
            u4=st.file_uploader("4. Libro Remun. CSV", type=["csv"], key="u4"); b4=st.button("Subir Libro", key="b4")
            if b4: pro_upload(u4, "LIBRO", e_u_m)
            u5=st.file_uploader("5. Comp. Envío DT", type=["pdf"], key="u5"); b5=st.button("Subir DT", key="b5")
            if b5: pro_upload(u5, "DT", e_u_m)
            u6=st.file_uploader("6. Certificado F30", type=["pdf"], key="u6"); b6=st.button("Subir F30", key="b6")
            if b6: pro_upload(u6, "F30", e_u_m)
            u7=st.file_uploader("7. Certificado F30-1", type=["pdf"], key="u7"); b7=st.button("Subir F30-1", key="b7")
            if b7: pro_upload(u7, "F301", e_u_m)
            u8=st.file_uploader("8. Planilla Control", type=["xlsx","xls"], key="u8"); b8=st.button("Subir Planilla", key="b8")
            if b8: pro_upload(u8, "CTRL", e_u_m)

            st.divider()
            if st.button("🏁 FINALIZAR Y NOTIFICAR CIERRE", key="btn_not_m_v45", use_container_width=True):
                requests.post(URL_APPS_SCRIPT, data={"accion":"enviar_email","empresa":e_u_m,"usuario":st.session_state["u_nom"],"periodo":f"CARGA MENSUAL: {mes_sidebar} {anio_sel}"})
                st.success("Notificación enviada al equipo C&S.")

# ==============================================================================
# 8. TAB: DOTACION (DINÁMICA ALTA/BAJA - EXPLÍCITA)
# ==============================================================================
with tabs[t_list.index("👥 DOTACION")]:
    st.header("👥 Gestión de Movimientos de Personal")
    tipo_m = st.radio("Acción a Informar:", ["🟢 Alta (Nuevo Ingreso)", "🔴 Baja (Egreso/Traslado)"], horizontal=True)
    st.divider()
    
    col_dx1, col_dx2 = st.columns([1.7, 1.3])
    with col_dx2:
        if "Alta" in tipo_m:
            color_dx = "#1E90FF"; tit_dx = "Requisitos de Alta"
            req_dx = """<li>Contrato de Trabajo</li><li>Anexo de Traslado</li><li>Cédula Identidad</li>
                        <li>Certificado Afiliacion AFP</li><li>Certificado Afiliacion Salud</li>
                        <li>Registro Contrato en DT</li><li>Entrega de RIOHS</li>"""
        else:
            color_dx = "#d9534f"; tit_dx = "Requisitos de Baja"
            req_dx = """<li>Finiquito Legalizado + Comprobante Pago</li><li>Anexo Traslado de Faena</li>"""
            
        st.markdown(f"""<div class='caja-instrucciones' style='border-left: 8px solid {color_dx};'>
        <h4>📌 {tit_dx}</h4><p style='font-size:14px; color:#d9534f;'><b>⚠️ REGLA: MÁXIMO 20MB POR ARCHIVO.</b></p>
        <ul style='font-size:14px; line-height:1.7;'>{req_dx}</ul></div>""", unsafe_allow_html=True)
    
    with col_dx1:
        e_c_dx = st.session_state['u_emp'] if rol_u == "USUARIO" else st.selectbox("Empresa Contratista:", sorted(df_av_global[col_e_ch].unique()), key="sel_d_v45")
        dx_c1, dx_c2 = st.columns(2)
        with dx_c1: t_nom = st.text_input("Nombre Trabajador:", placeholder="JUAN PEREZ")
        with dx_c2: 
            t_rut = st.text_input("RUT Trabajador:", placeholder="12.345.678-9")
            r_ok = validar_rut(t_rut) if t_rut else False
            if t_rut: st.caption("✅ RUT Válido" if r_ok else "❌ RUT Inválido")
        
        dx_c3, dx_c4 = st.columns(2)
        with dx_c3: t_fecha = st.date_input("Fecha Efectiva:", datetime.now())
        with dx_c4: t_cau = st.selectbox("Causal Legal:", CAUSALES_FINIQUITO_LIST) if "Baja" in tipo_m else "Nuevo Ingreso"

        st.divider()
        ar_dot = st.file_uploader("Subir Documentos (PDF):", type=["pdf"], accept_multiple_files=True, key="bulk_dot_v45")
        
        if st.button("🚀 PROCESAR Y NOTIFICAR MOVIMIENTO", key="btn_not_d_v45", use_container_width=True):
            if t_nom and r_ok and ar_dot:
                if any(az.size > 20*1024*1024 for az in ar_dot): st.error("⚠️ Uno o más archivos exceden los 20MB.")
                else:
                    mt_dx = df_id_db_all[df_id_db_all['EMPRESA'].str.contains(e_c_dx[:10], case=False, na=False)]
                    if not mt_dx.empty:
                        idf_dx = str(mt_dx.iloc[0]['IDCARPETA']).strip()
                        for fi_s in ar_dot:
                            requests.post(URL_APPS_SCRIPT, data={"tipo":"colaborador","id_carpeta":idf_dx,"nombre_persona":t_nom.upper(),"rut":t_rut,"nombre_final":fi_s.name,"archivo_base64":base64.b64encode(fi_s.read()).decode('utf-8')})
                        
                        # Notificación Estructurada
                        body_rrhh = f"Acción: {tipo_m}\nTrabajador: {t_nom.upper()}\nFecha: {t_fecha.strftime('%d/%m/%Y')}\nCausal: {t_cau}"
                        requests.post(URL_APPS_SCRIPT, data={"accion":"enviar_email", "empresa":e_c_dx, "usuario":st.session_state["u_nom"], "periodo": body_rrhh})
                        st.success(f"✅ Notificación enviada para {t_nom.upper()}.")
            else: st.warning("Complete todos los campos.")

# --- TAB: ADMIN ---
if rol_u != "USUARIO":
    with tabs[t_list.index("⚙️ Admin")]:
        st.header("⚙️ Gestión Administrativa"); st.dataframe(cargar_datos(ID_USUARIOS, "Usuarios"), use_container_width=True)

st.markdown("---")
st.caption("Control Laboral CMSG | Gestión Contratistas | C & S Asociados Ltda.")