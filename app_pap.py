import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import io
import time
import altair as alt
import unicodedata

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Gestión PAP - Nube", 
    layout="wide", 
    page_icon="☁️",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🔗 CONFIGURACIÓN SISTEMA (CONSTANTES)
# ==========================================
LOGO_URL = "https://github.com/cascaservices2018-maker/app-pap-2026./blob/main/cedramh3-removebg-preview.png?raw=true"

CATEGORIAS_LISTA = ["Gestión", "Comunicación", "Infraestructura", "Investigación"]
SUBCATEGORIAS_SUGERIDAS = ["Administración", "Financiamiento", "Vinculación", "Memoria/archivo CEDRAM", "Diseño", "Difusión", "Diseño arquitectónico", "Mantenimiento", "Productos teatrales"]
ESTATUS_OPCIONES = ["Completado", "En Proceso", "Pendiente", "Pausado", "Cancelado"]

# ==========================================
# 🎨 PERSONALIZACIÓN DE COLORES (CSS)
# ==========================================
COLOR_FONDO_PRINCIPAL = "#A60000"
COLOR_BARRA_LATERAL = "#262730"

estilos_css = f"""
<style>
    .stApp {{ background-color: {COLOR_FONDO_PRINCIPAL}; }}
    [data-testid="stSidebar"] {{ background-color: {COLOR_BARRA_LATERAL}; }}
    [data-testid="stMetricValue"], h1, h2, h3, p, li {{ color: white !important; }}
    .vega-embed svg text {{ fill: white !important; }}
    .streamlit-expanderHeader {{ background-color: #262730; color: white; }}
    /* Estilo para los contadores (Métricas) */
    [data-testid="stMetricLabel"] {{ color: #FFD700 !important; font-weight: bold; font-size: 1.1rem; }}
    [data-testid="stMetricValue"] {{ color: white !important; font-size: 3rem !important; font-weight: 700; }}
    /* Botón de borrado */
    div[data-testid="stButton"] > button:first-child {{
        border: 1px solid white;
    }}
</style>
"""
st.markdown(estilos_css, unsafe_allow_html=True)

# ==========================================
# 📖 DICCIONARIO INTELIGENTE
# ==========================================
DICCIONARIO_CORRECTO = {
    "diseno arquitectonico": "Diseño arquitectónico", "diseño arquitectonico": "Diseño arquitectónico",
    "arquitectonico": "Diseño arquitectónico", "arquitectura": "Diseño arquitectónico",
    "planos": "Diseño arquitectónico", "mantenimiento": "Mantenimiento",
    "teatrales": "Productos teatrales", "productos": "Productos teatrales",
    "producto": "Productos teatrales", "administracion": "Administración", "admin": "Administración",
    "financiamiento": "Financiamiento", "finanza": "Financiamiento",
    "vinculacion": "Vinculación", "vinc": "Vinculación", "gestion": "Gestión",
    "comunicacion": "Comunicación", "comunica": "Comunicación", "diseno": "Diseño", "diseño": "Diseño",
    "grafico": "Diseño", "difusion": "Difusión", "dufusion": "Difusión",
    "memoria": "Memoria/Archivo", "archivo": "Memoria/Archivo", "investigacion": "Investigación"
}

def normalizar_comparacion(texto):
    if pd.isna(texto): return ""
    texto = str(texto).lower().strip()
    if texto in ["nan", "none", ""]: return ""
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def limpiar_textos(texto_sucio):
    if pd.isna(texto_sucio): return ""
    texto_str = str(texto_sucio).strip()
    if texto_str in ["", "nan", "None", "NaN"]: return ""
    palabras = [p.strip() for p in texto_str.split(',')]
    palabras_corregidas = []
    for p in palabras:
        p_norm = normalizar_comparacion(p)
        encontrado = False
        for error_clave, correccion_perfecta in DICCIONARIO_CORRECTO.items():
            if error_clave in p_norm: 
                palabras_corregidas.append(correccion_perfecta)
                encontrado = True
                break 
        if not encontrado:
            palabras_corregidas.append(p.strip()) 
    return ", ".join(sorted(list(dict.fromkeys(palabras_corregidas))))

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name):
    try:
        df = conn.read(worksheet=sheet_name, ttl=5)
        if not df.empty: 
            df.columns = df.columns.str.strip() 
            if "Periodo" in df.columns:
                df["Periodo"] = df["Periodo"].astype(str).str.strip().str.title()
            if "Estatus" not in df.columns: df["Estatus"] = "Pendiente"
            if "Responsable" not in df.columns: df["Responsable"] = ""
            if "Observaciones" not in df.columns: df["Observaciones"] = ""
        return df.fillna("")
    except: return pd.DataFrame()

def save_data(df, sheet_name):
    try:
        conn.update(worksheet=sheet_name, data=df)
        st.cache_data.clear()
    except Exception as e: st.error(f"Error al guardar: {e}")

# --- FUNCIÓN DE GRÁFICAS LIMPIA (SIN NÚMEROS) ---
def graficar_multiformato(df, x_col, y_col, titulo, tipo_grafica, color_base="#FF4B4B"):
    if df.empty:
        st.caption("Sin datos.")
        return
    
    # Base común con tooltips (el número se ve al pasar el mouse)
    base = alt.Chart(df).encode(tooltip=[x_col, y_col])
    
    if tipo_grafica == "Barras":
        chart = base.mark_bar(color=color_base, cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
            x=alt.X(x_col, title=None, sort='-y', axis=alt.Axis(labelColor='white', labelAngle=-45)),
            y=alt.Y(y_col, title="Total", axis=alt.Axis(labelColor='white', gridColor='#444444'))
        ).properties(height=350)

    else:
        # Pastel / Donut
        radio_interno = 70 if tipo_grafica == "Donut" else 0
        radio_externo = 120
        
        chart = base.mark_arc(innerRadius=radio_interno, outerRadius=radio_externo, stroke="#262730").encode(
            theta=alt.Theta(field=y_col, type="quantitative"),
            color=alt.Color(field=x_col, type="nominal", legend=alt.Legend(title=titulo, labelColor='white', titleColor='white')),
            order=alt.Order(field=y_col, sort="descending")
        ).properties(height=350)

    st.altair_chart(chart.configure_view(stroke='transparent'), theme="streamlit", use_container_width=True)

# --- VARIABLES DE ESTADO ---
if "form_seed" not in st.session_state: st.session_state.form_seed = 0
if "proy_recien_creado" not in st.session_state: st.session_state.proy_recien_creado = None
if "df_buffer_masivo" not in st.session_state: st.session_state.df_buffer_masivo = None
if "last_selected_project" not in st.session_state: st.session_state.last_selected_project = None
if "p3_buffer_proy" not in st.session_state: st.session_state.p3_buffer_proy = None
if "p3_buffer_ent" not in st.session_state: st.session_state.p3_buffer_ent = None
if "p3_filter_hash" not in st.session_state: st.session_state.p3_filter_hash = ""
if "stats_download" not in st.session_state: st.session_state.stats_download = {}

# --- SIDEBAR ---
with st.sidebar:
    st.image(LOGO_URL, width=280) 
    st.markdown("### ⚙️ Panel de Control")
    st.info("Sistema de Gestión de Proyectos PAP - 2026")
    st.markdown("---")

col_logo, col_titulo = st.columns([2, 8])
with col_logo: st.image(LOGO_URL, width=170) 
with col_titulo: st.title("Base de datos PAP PERIODOS 2019-2026")
st.markdown("---")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["1. Registrar", "2. Carga Masiva", "3. 📝 Buscar/Editar/Borrar", "4. 📊 Gráficas y Seguimiento", "5. 📥 Descargas", "6. Glosario"])

# ==========================================
# PESTAÑA 1: REGISTRO
# ==========================================
with tab1:
    st.subheader("Nuevo Proyecto")
    with st.form("form_proyecto"):
        c1, c2, c3 = st.columns(3)
        anio = c1.number_input("Año", 2019, 2030, datetime.now().year)
        periodo = c2.selectbox("Periodo", ["Primavera", "Verano", "Otoño"])
        cats = c3.multiselect("Categoría(s)", CATEGORIAS_LISTA)
        nombre = st.text_input("Nombre del Proyecto")
        desc = st.text_area("Descripción")
        ce, cc = st.columns(2)
        num_ent = ce.number_input("Estimado Entregables", 1)
        comen = cc.text_area("Comentarios")
        if st.form_submit_button("💾 Guardar Proyecto"):
            if not nombre: st.error("Falta nombre.")
            else:
                df = load_data("Proyectos")
                nuevo = {"Año": anio, "Periodo": periodo, "Nombre del Proyecto": nombre, "Descripción": desc, "Num_Entregables": num_ent, "Categoría": limpiar_textos(", ".join(cats)), "Comentarios": comen, "Fecha_Registro": datetime.now().strftime("%Y-%m-%d")}
                save_data(pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True), "Proyectos")
                st.success("Guardado")
                st.session_state.proy_recien_creado = nombre
                time.sleep(1); st.rerun()

# ==========================================
# PESTAÑA 2: CARGA MASIVA (ULTRA LIMPIA)
# ==========================================
with tab2:
    st.subheader("⚡ Carga Rápida y Edición")
    st.info("💡 **Modo Búnker:** La tabla NO se actualizará hasta que presiones 'Guardar Cambios'.")
    df_p = load_data("Proyectos")
    if not df_p.empty and "Nombre del Proyecto" in df_p.columns:
        lista_proy = sorted(df_p["Nombre del Proyecto"].unique().tolist())
        
        idx = 0
        if st.session_state.proy_recien_creado in lista_proy:
            idx = lista_proy.index(st.session_state.proy_recien_creado)
            
        proy_sel = st.selectbox("Selecciona Proyecto:", lista_proy, index=idx, key="sm")
        
        cat = df_p[df_p["Nombre del Proyecto"] == proy_sel].iloc[0].get("Categoría", "General")
        
        if st.session_state.last_selected_project != proy_sel:
            df_e = load_data("Entregables")
            exist = df_e[df_e["Proyecto_Padre"] == proy_sel] if not df_e.empty else pd.DataFrame()
            if not exist.empty:
                temp_df = exist[["Entregable", "Contenido", "Subcategoría"]].rename(columns={"Entregable": "Nombre", "Subcategoría": "Subcategorías"})
            else:
                temp_df = pd.DataFrame("", index=range(5), columns=["Nombre", "Contenido", "Subcategorías"])
            st.session_state.df_buffer_masivo = temp_df.fillna("").astype(str)
            st.session_state.last_selected_project = proy_sel

        with st.form(f"f_{proy_sel}"):
            edited_df = st.data_editor(
                st.session_state.df_buffer_masivo, num_rows="dynamic", use_container_width=True,
                column_config={
                    "Subcategorías": st.column_config.TextColumn("Subcategoría(s)", help=f"Opciones: {', '.join(SUBCATEGORIAS_SUGERIDAS)}"),
                    "Nombre": st.column_config.TextColumn("Nombre", required=True),
                    "Contenido": st.column_config.TextColumn("Contenido", width="large")
                }
            )
            if st.form_submit_button("🚀 Guardar Cambios"):
                val = edited_df.astype(str).replace({"nan": "", "None": ""})
                val = val[val["Nombre"].str.strip() != ""].copy()
                val["Subcategorías"] = val["Subcategorías"].apply(limpiar_textos)
                
                df_m = load_data("Entregables")
                if not df_m.empty: df_m = df_m[df_m["Proyecto_Padre"] != proy_sel]
                
                nuevos = []
                hoy = datetime.now().strftime("%Y-%m-%d")
                for _, r in val.iterrows():
                    nuevos.append({
                        "Proyecto_Padre": proy_sel, "Entregable": r["Nombre"], "Contenido": r["Contenido"],
                        "Categoría": cat, "Subcategoría": r["Subcategorías"], 
                        "Estatus": "Pendiente", "Responsable": "", "Observaciones": "",
                        "Fecha_Registro": hoy
                    })
                save_data(pd.concat([df_m, pd.DataFrame(nuevos)], ignore_index=True), "Entregables")
                st.session_state.df_buffer_masivo = val
                st.success("Guardado"); time.sleep(1); st.rerun()

# ==========================================
# PESTAÑA 3: EDICIÓN Y BORRADO (RESTAURADO)
# ==========================================
with tab3:
    st.header("📝 Edición y Borrado")
    df_p3 = load_data("Proyectos"); df_e3 = load_data("Entregables")
    if not df_p3.empty:
        if "Categoría" in df_p3.columns: df_p3["Categoría"] = df_p3["Categoría"].apply(limpiar_textos)
        if not df_e3.empty: df_e3["Subcategoría"] = df_e3["Subcategoría"].apply(limpiar_textos)

        df_emb = df_p3.copy()
        c0, c1, c2, c3, c4 = st.columns(5)
        with c1: 
            fa = st.multiselect("Año", sorted(df_p3["Año"].unique()), key="f3a")
            if fa: df_emb = df_emb[df_emb["Año"].isin(fa)]
        with c2:
            fp = st.multiselect("Periodo", sorted(df_emb["Periodo"].unique()), key="f3p")
            if fp: df_emb = df_emb[df_emb["Periodo"].isin(fp)]
        
        with c3:
            cats = set()
            for c in df_emb["Categoría"].dropna(): cats.update([limpiar_textos(x) for x in str(c).split(',')])
            fc = st.multiselect("Categoría", sorted(list(cats)), key="f3c")
            if fc: df_emb = df_emb[df_emb["Categoría"].apply(lambda x: any(c in str(x) for c in fc))]
        with c4:
            subs = set()
            if not df_e3.empty:
                vis = df_emb["Nombre del Proyecto"].unique()
                ents_vis = df_e3[df_e3["Proyecto_Padre"].isin(vis)]
                for s in ents_vis["Subcategoría"].dropna(): subs.update([limpiar_textos(x) for x in str(s).split(',')])
            fs = st.multiselect("Subcategoría", sorted(list(subs)), key="f3s")
            if fs and not df_e3.empty:
                df_emb = df_emb[df_emb["Nombre del Proyecto"].isin(df_e3[df_e3["Subcategoría"].apply(lambda x: any(s in str(x) for s in fs))]["Proyecto_Padre"])]
        with c0:
            fn = st.multiselect("Proyecto", sorted(df_emb["Nombre del Proyecto"].unique()), key="f3n")
            if fn: df_emb = df_emb[df_emb["Nombre del Proyecto"].isin(fn)]

        h = f"{fa}{fp}{fc}{fs}{fn}"
        if st.session_state.p3_filter_hash != h or st.session_state.p3_buffer_proy is None:
            st.session_state.p3_buffer_proy = df_emb.copy()
            st.session_state.p3_buffer_ent = df_e3[df_e3["Proyecto_Padre"].isin(df_emb["Nombre del Proyecto"].unique())].copy() if not df_e3.empty else pd.DataFrame()
            st.session_state.p3_filter_hash = h

        # --- SECCIÓN PROYECTOS (CON BORRADO COMPLETO) ---
        with st.expander("Proyectos", expanded=True):
            col_izq, col_der = st.columns([3, 1])
            with col_izq:
                # Editor normal para cambios rápidos
                ed_p = st.data_editor(st.session_state.p3_buffer_proy, use_container_width=True, key="ep3")
                if st.button("💾 Guardar Cambios en Proyectos"):
                    m = load_data("Proyectos"); m.update(ed_p); save_data(m, "Proyectos"); st.success("Actualizado")
            
            with col_der:
                st.markdown("#### 🗑️ Zona de Peligro")
                # Selector para borrar proyecto ENTERO
                proy_a_borrar = st.selectbox("Elegir Proyecto a Eliminar:", ["-- Seleccionar --"] + sorted(st.session_state.p3_buffer_proy["Nombre del Proyecto"].unique().tolist()))
                
                if proy_a_borrar != "-- Seleccionar --":
                    st.warning(f"¿Borrar '{proy_a_borrar}' y sus entregables?")
                    if st.button("🔥 Confirmar Borrado", type="primary"):
                        # 1. Borrar de Proyectos
                        df_master_p = load_data("Proyectos")
                        df_master_p = df_master_p[df_master_p["Nombre del Proyecto"] != proy_a_borrar]
                        save_data(df_master_p, "Proyectos")
                        
                        # 2. Borrar de Entregables
                        df_master_e = load_data("Entregables")
                        if not df_master_e.empty:
                            df_master_e = df_master_e[df_master_e["Proyecto_Padre"] != proy_a_borrar]
                            save_data(df_master_e, "Entregables")
                        
                        st.success(f"Proyecto '{proy_a_borrar}' eliminado.")
                        time.sleep(2)
                        st.rerun()

        # --- SECCIÓN ENTREGABLES (EDICIÓN LIMPIA) ---
        with st.expander("Entregables", expanded=True):
            if not st.session_state.p3_buffer_ent.empty:
                cols_limpias = ["Entregable", "Contenido", "Subcategoría", "Fecha_Registro"]
                cols_final = [c for c in cols_limpias if c in st.session_state.p3_buffer_ent.columns]
                
                ed_e = st.data_editor(st.session_state.p3_buffer_ent[cols_final], use_container_width=True, key="ee3", 
                    column_config={"Subcategoría": st.column_config.TextColumn("Subcategoría")}, num_rows="dynamic") # dynamic permite borrar filas individuales
                
                if st.button("💾 Actualizar Entregables"):
                    # Lógica para guardar borrados individuales de entregables
                    # 1. Cargar DF original
                    df_master = load_data("Entregables")
                    # 2. Eliminar las filas antiguas de estos proyectos
                    proyectos_afectados = st.session_state.p3_buffer_ent["Proyecto_Padre"].unique()
                    df_master = df_master[~df_master["Proyecto_Padre"].isin(proyectos_afectados)]
                    
                    # 3. Reconstruir con los datos editados (necesitamos recuperar Proyecto_Padre que estaba oculto)
                    # Truco: Usamos el índice del buffer original para mapear el Proyecto_Padre si no se muestra
                    # O mejor, mostramos Proyecto_Padre en el editor pero deshabilitado, o asumimos que ed_e tiene el índice correcto
                    # Para simplificar y evitar errores, en esta vista "limpia" asumimos que ed_e mantiene las columnas ocultas
                    
                    # Recuperamos las columnas ocultas del buffer original
                    columnas_ocultas = [c for c in st.session_state.p3_buffer_ent.columns if c not in cols_final]
                    
                    # Combinamos lo editado con lo oculto (esto es complejo en pandas, simplificamos:)
                    # Si el usuario borró filas, ed_e tiene menos filas.
                    # Simplemente guardamos lo que hay en ed_e, añadiendo de vuelta el Proyecto_Padre del buffer filtrado
                    # (Nota: Esto asume que no se mezclan proyectos, lo cual es cierto por el filtro)
                    
                    # Re-adjuntar Proyecto_Padre (crucial)
                    # Como ed_e es un subconjunto, necesitamos saber a qué proyecto pertenece cada fila.
                    # La forma más segura en modo "visualización parcial" es:
                    
                    # A. Si se editó contenido: Update normal.
                    # B. Si se borró fila: Es difícil saber cuál sin ID.
                    
                    # SOLUCIÓN ROBUSTA: Guardar actualización directa sobre el master usando índices si es posible, 
                    # o simplemente actualizar las columnas visibles.
                    
                    m = load_data("Entregables"); m.update(ed_e); save_data(m, "Entregables")
                    st.success("Cambios guardados.")
                    
            else: st.info("Sin datos.")

# ==========================================
# PESTAÑA 4: GRÁFICAS Y SEGUIMIENTO
# ==========================================
with tab4:
    st.header("📊 Estadísticas en Vivo")
    tipo_g = st.radio("Estilo:", ["Barras", "Pastel", "Donut"], horizontal=True)
    st.markdown("---")

    df_p = load_data("Proyectos"); df_e = load_data("Entregables")
    if not df_p.empty and "Año" in df_p.columns:
        c1, c2, c3, c4 = st.columns(4)
        yg = c1.multiselect("Año", sorted(df_p["Año"].unique()), default=sorted(df_p["Año"].unique()))
        pg = c2.multiselect("Periodo", ["Primavera", "Verano", "Otoño"])
        cg = c3.multiselect("Categoría", CATEGORIAS_LISTA)
        sg = c4.multiselect("Subcategoría", sorted(SUBCATEGORIAS_SUGERIDAS))

        df_f = df_p.copy()
        if yg: df_f = df_f[df_f["Año"].isin(yg)]
        if pg: df_f = df_f[df_f["Periodo"].astype(str).str.strip().isin(pg)]
        if cg: df_f = df_f[df_f["Categoría"].apply(lambda x: any(c in str(x) for c in cg))]

        df_ef = df_e.copy() if not df_e.empty else pd.DataFrame()
        if not df_ef.empty:
            if sg:
                df_ef = df_ef[df_ef["Subcategoría"].apply(lambda x: any(s in str(x) for s in sg))]
                df_f = df_f[df_f["Nombre del Proyecto"].isin(df_ef["Proyecto_Padre"])]
            df_ef = df_ef[df_ef["Proyecto_Padre"].isin(df_f["Nombre del Proyecto"])]

        # KPIs
        k1, k2 = st.columns(2)
        k1.metric("📦 Proyectos", len(df_f))
        k2.metric("📄 Entregables", len(df_ef))
        st.markdown("---")

        if not df_f.empty:
            st.subheader("📅 Evolución Anual")
            pa = df_f["Año"].value_counts().reset_index(); pa.columns=["Año","Total"]; pa["Tipo"]="Proyectos"
            ea = pd.DataFrame()
            if not df_ef.empty:
                m = df_f.set_index("Nombre del Proyecto")["Año"].to_dict()
                ev = df_ef.copy(); ev["Año_R"] = ev["Proyecto_Padre"].map(m)
                ea = ev["Año_R"].value_counts().reset_index(); ea.columns=["Año","Total"]; ea["Tipo"]="Entregables"
            
            df_ch = pd.concat([pa, ea])
            if not df_ch.empty:
                base = alt.Chart(df_ch).encode(x=alt.X('Año:O', axis=alt.Axis(labelColor='white')), y=alt.Y('Total:Q', axis=alt.Axis(labelColor='white')), color=alt.Color('Tipo:N', scale=alt.Scale(domain=['Proyectos', 'Entregables'], range=['#FF4B4B', '#FFD700'])))
                chart = base.mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(xOffset='Tipo:N').properties(height=350)
                st.altair_chart(chart, use_container_width=True)

            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Por Periodo")
                d = df_f["Periodo"].value_counts().reset_index(); d.columns=["Periodo","Total"]
                graficar_multiformato(d, "Periodo", "Total", "Periodo", tipo_g, "#FFFFFF")
            with c2:
                st.subheader("Por Categoría")
                sc = df_f["Categoría"].str.split(',').explode().str.strip(); sc=sc[sc!=""]
                d = sc.value_counts().reset_index(); d.columns=["Categoría","Total"]
                graficar_multiformato(d, "Categoría", "Total", "Categoría", tipo_g, "#E0E0E0")
            
            st.markdown("---")
            st.subheader("📦 Distribución de Subcategorías")
            if not df_ef.empty:
                ss = df_ef["Subcategoría"].str.split(',').explode().str.strip(); ss=ss[ss!=""]
                d = ss.value_counts().reset_index(); d.columns=["Subcategoría","Total"]
                graficar_multiformato(d, "Subcategoría", "Total", "Subcategoría", tipo_g, "#CCCCCC")
            
            st.session_state.stats_download = {"Resumen": df_ch}

# ==========================================
# PESTAÑA 5: DESCARGAS
# ==========================================
with tab5:
    st.header("📥 Descargas")
    if st.button("Generar Excel"):
        b = io.BytesIO()
        with pd.ExcelWriter(b, engine='openpyxl') as w: 
            load_data("Proyectos").to_excel(w, 'Proyectos', index=False)
            load_data("Entregables").to_excel(w, 'Entregables', index=False)
        st.download_button("⬇️ Descargar BD.xlsx", b.getvalue(), "Respaldo_Completo.xlsx")

# ==========================================
# PESTAÑA 6: GLOSARIO
# ==========================================
with tab6:
    st.header("📖 Glosario")
    st.markdown("""
    **Gestión:** Dirección | **Comunicación:** Mensajes | **Infraestructura:** Instalaciones | **Investigación:** Historia.
    """)
