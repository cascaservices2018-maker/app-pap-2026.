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
</style>
"""
st.markdown(estilos_css, unsafe_allow_html=True)

# ==========================================
# 📖 DICCIONARIO INTELIGENTE (JERARQUIZADO)
# ==========================================
DICCIONARIO_CORRECTO = {
    # --- INFRAESTRUCTURA (Prioridad Alta) ---
    "diseno arquitectonico": "Diseño arquitectónico",
    "diseño arquitectonico": "Diseño arquitectónico",
    "arquitectonico": "Diseño arquitectónico", 
    "arquitectura": "Diseño arquitectónico",
    "planos": "Diseño arquitectónico",
    "mantenimiento": "Mantenimiento",
    "teatrales": "Productos teatrales",
    "productos teatrales": "Productos teatrales",
    
    # --- GESTIÓN ---
    "administracion": "Administración", "admin": "Administración",
    "financiamiento": "Financiamiento", "finanza": "Financiamiento",
    "vinculacion": "Vinculación", "vinc": "Vinculación",
    "gestion": "Gestión", "gestión": "Gestión",
    
    # --- COMUNICACIÓN ---
    "comunicacion": "Comunicación", "comunica": "Comunicación",
    "diseno": "Diseño", "diseño": "Diseño",
    "grafico": "Diseño",
    "difusion": "Difusión", "difucion": "Difusión",
    "memoria": "Memoria/Archivo", "archivo": "Memoria/Archivo",
    
    # --- INVESTIGACIÓN ---
    "investigacion": "Investigación"
}

def normalizar_comparacion(texto):
    if pd.isna(texto) or texto == "": return ""
    texto = str(texto).lower().strip()
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def limpiar_textos(texto_sucio):
    if pd.isna(texto_sucio) or str(texto_sucio).strip() == "": return ""
    palabras = [p.strip() for p in str(texto_sucio).split(',')]
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

# ==========================================
# 🔗 CONFIGURACIÓN SISTEMA
# ==========================================
LOGO_URL = "https://github.com/cascaservices2018-maker/app-pap-2026./blob/main/cedramh3-removebg-preview.png?raw=true"
CATEGORIAS_LISTA = ["Gestión", "Comunicación", "Infraestructura", "Investigación"]

SUBCATEGORIAS_SUGERIDAS = [
    "Administración", "Financiamiento", "Vinculación", 
    "Memoria/archivo CEDRAM", "Memoria/archivo PAP", "Diseño", "Difusión", 
    "Diseño arquitectónico", "Mantenimiento", "Productos teatrales"
]

conn = st.connection("gsheets", type=GSheetsConnection)

# -------------------------------------------------------
# MODIFICACIÓN: Aumento del TTL para evitar parpadeos
# -------------------------------------------------------
def load_data(sheet_name):
    try:
        # Aumentamos ttl a 600s (10 min) para que no recargue mientras editas
        df = conn.read(worksheet=sheet_name, ttl=600) 
        if not df.empty: 
            df.columns = df.columns.str.strip() 
            if "Periodo" in df.columns:
                df["Periodo"] = df["Periodo"].astype(str).str.strip().str.title()
        return df
    except: return pd.DataFrame()

def save_data(df, sheet_name):
    try:
        conn.update(worksheet=sheet_name, data=df)
        st.cache_data.clear() # Limpiamos caché solo al guardar
    except Exception as e: st.error(f"Error al guardar: {e}")

# -------------------------------------------------------
# MODIFICACIÓN: Nueva función para Gráficas de Pastel/Dona
# -------------------------------------------------------
def graficar_dona(df, col_categoria, col_conteo, titulo):
    base = alt.Chart(df).encode(
        theta=alt.Theta(col_conteo, stack=True)
    )
    pie = base.mark_arc(innerRadius=50, outerRadius=100).encode(
        color=alt.Color(col_categoria, scale=alt.Scale(scheme='tableau20')),
        order=alt.Order(col_conteo, sort='descending'),
        tooltip=[col_categoria, col_conteo]
    )
    text = base.mark_text(radius=120).encode(
        text=alt.Text(col_conteo),
        order=alt.Order(col_conteo, sort='descending'),
        color=alt.value("white")
    )
    st.altair_chart((pie + text).properties(title=titulo), use_container_width=True)

def graficar_barras(df, x_col, y_col, titulo_x, titulo_y, color_barra="#FFFFFF"):
    chart = alt.Chart(df).mark_bar(color=color_barra).encode(
        x=alt.X(x_col, title=titulo_x, sort='-y'),
        y=alt.Y(y_col, title=titulo_y),
        tooltip=[x_col, y_col]
    ).configure_axis(labelColor='white', titleColor='white', gridColor='#660000').properties(height=300)
    st.altair_chart(chart, use_container_width=True)

# --- VARIABLES DE ESTADO ---
if "form_seed" not in st.session_state: st.session_state.form_seed = 0
if "borradores" not in st.session_state: st.session_state.borradores = {}
if "proy_recien_creado" not in st.session_state: st.session_state.proy_recien_creado = None
if "proyecto_activo_masivo" not in st.session_state: st.session_state.proyecto_activo_masivo = None
if "df_buffer_masivo" not in st.session_state: st.session_state.df_buffer_masivo = pd.DataFrame()
if "stats_download" not in st.session_state: st.session_state.stats_download = {}

# --- SIDEBAR ---
with st.sidebar:
    st.image(LOGO_URL, width=280) 
    st.markdown("### ⚙️ Panel de Control")
    st.info("Sistema de Gestión de Proyectos PAP - 2026")
    st.markdown("---")
    st.write("Bienvenido al sistema colaborativo.")

col_logo, col_titulo = st.columns([2, 8])
with col_logo: st.image(LOGO_URL, width=170) 
with col_titulo: st.title("Base de datos PAP PERIODOS 2019-2026")
st.markdown("---")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["1. Registrar", "2. Carga Masiva", "3. 📝 Buscar/Editar", "4. 📊 Gráficas", "5. 📥 Descargas", "6. Glosario"])

# ==========================================
# PESTAÑA 1: REGISTRO
# ==========================================
with tab1:
    st.subheader("Nuevo Proyecto")
    with st.form("form_proyecto", clear_on_submit=False):
        c1, c2, c3 = st.columns(3)
        semilla = st.session_state.form_seed
        anio = c1.number_input("Año", 2019, 2030, datetime.now().year, key=f"anio_{semilla}")
        periodo = c2.selectbox("Periodo", ["Primavera", "Verano", "Otoño"], key=f"periodo_{semilla}")
        cats = c3.multiselect("Categoría(s)", CATEGORIAS_LISTA, key=f"cats_{semilla}")
        nombre = st.text_input("Nombre del Proyecto", key=f"nombre_{semilla}")
        desc = st.text_area("Descripción", key=f"desc_{semilla}")
        ce, cc = st.columns(2)
        num_ent = ce.number_input("Estimado Entregables", 1, step=1, key=f"num_{semilla}")
        comen = cc.text_area("Comentarios", key=f"comen_{semilla}")

        if st.form_submit_button("💾 Guardar Proyecto"):
            if not nombre: st.error("⚠️ El nombre es obligatorio.")
            elif not cats: st.error("⚠️ Elige categoría.")
            else:
                df = load_data("Proyectos")
                if not df.empty and "Nombre del Proyecto" in df.columns and nombre in df["Nombre del Proyecto"].values:
                    st.warning("⚠️ Ya existe.")
                else:
                    nuevo = {"Año": anio, "Periodo": periodo, "Nombre del Proyecto": nombre, "Descripción": desc, "Num_Entregables": num_ent, "Categoría": limpiar_textos(", ".join(cats)), "Comentarios": comen, "Fecha_Registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                    save_data(pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True), "Proyectos")
                    st.success("¡Guardado!")
                    st.session_state.proy_recien_creado = nombre
                    st.session_state.form_seed += 1
                    time.sleep(1); st.rerun()

# ==========================================
# PESTAÑA 2: CARGA MASIVA
# ==========================================
with tab2:
    st.subheader("⚡ Carga Rápida y Edición")
    st.info("💡 **Modo Offline:** Los cambios solo se envían a Google Sheets cuando pulsas 'Guardar Cambios'.")
    df_p = load_data("Proyectos")
    if df_p.empty: st.warning("Cargando...")
    elif "Nombre del Proyecto" in df_p.columns:
        lista_proy = sorted(df_p["Nombre del Proyecto"].unique().tolist())
        idx = lista_proy.index(st.session_state.proy_recien_creado) if st.session_state.proy_recien_creado in lista_proy else 0
        proy_sel = st.selectbox("Selecciona Proyecto:", lista_proy, index=idx)
        
        info = df_p[df_p["Nombre del Proyecto"] == proy_sel].iloc[0]
        cat, estim = info.get("Categoría", "General"), int(info.get("Num_Entregables", 5))
        st.caption(f"Categoría: {cat} | Espacios: {estim}")

        if st.session_state.proyecto_activo_masivo != proy_sel:
            df_e = load_data("Entregables")
            exist = df_e[df_e["Proyecto_Padre"] == proy_sel] if not df_e.empty else pd.DataFrame()
            if not exist.empty:
                st.session_state.df_buffer_masivo = exist[["Entregable", "Contenido", "Subcategoría", "Plantillas"]].rename(columns={"Entregable": "Nombre_Entregable", "Subcategoría": "Subcategorías", "Plantillas": "Plantillas_Usadas"}).fillna("").astype(str)
            else:
                st.session_state.df_buffer_masivo = pd.DataFrame("", index=range(estim), columns=["Nombre_Entregable", "Contenido", "Subcategorías", "Plantillas_Usadas"]).astype(str)
            st.session_state.proyecto_activo_masivo = proy_sel

        # El data_editor ya maneja su propio estado interno temporal
        edited_df = st.data_editor(st.session_state.df_buffer_masivo, num_rows="dynamic", key="editor_masivo", use_container_width=True,
            column_config={
                "Subcategorías": st.column_config.TextColumn("Subcategoría(s)", help=f"Sugerencias: {', '.join(SUBCATEGORIAS_SUGERIDAS)}"),
                "Nombre_Entregable": st.column_config.TextColumn("Nombre", required=True),
                "Contenido": st.column_config.TextColumn("Contenido", width="large")
            })
        
        # Persistencia local para evitar borrado al interactuar
        if not edited_df.equals(st.session_state.df_buffer_masivo): 
            st.session_state.df_buffer_masivo = edited_df

        if st.button("🚀 Guardar Cambios"):
            validos = edited_df[edited_df["Nombre_Entregable"].notna() & (edited_df["Nombre_Entregable"] != "")].copy()
            if validos.empty: st.error("No hay datos para guardar.")
            else:
                try:
                    validos["Subcategorías"] = validos["Subcategorías"].apply(limpiar_textos)
                    df_m = load_data("Entregables")
                    # Eliminamos los viejos de este proyecto y metemos los nuevos
                    if not df_m.empty: df_m = df_m[df_m["Proyecto_Padre"] != proy_sel]
                    nuevos = []
                    hoy = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    for _, r in validos.iterrows():
                        nuevos.append({"Proyecto_Padre": proy_sel, "Entregable": r["Nombre_Entregable"], "Contenido": r["Contenido"], "Categoría": cat, "Subcategoría": r["Subcategorías"], "Plantillas": r["Plantillas_Usadas"], "Fecha_Registro": hoy})
                    
                    save_data(pd.concat([df_m, pd.DataFrame(nuevos)], ignore_index=True), "Entregables")
                    st.success("¡Base de datos actualizada correctamente!"); 
                    st.session_state.proyecto_activo_masivo = None; 
                    time.sleep(1); st.rerun()
                except Exception as e: st.error(f"Error: {e}")

# ==========================================
# PESTAÑA 3: BÚSQUEDA Y EDICIÓN (FILTROS CASCADA)
# ==========================================
with tab3:
    st.header("📝 Edición de Base de Datos")
    st.info("💡 Filtros inteligentes: Selecciona el Año para ver Proyectos de ese año, etc.")
    
    # Cargamos datos (usando caché para no parpadear)
    df_proy = load_data("Proyectos"); df_ent = load_data("Entregables")

    if not df_proy.empty and "Año" in df_proy.columns:
        # Limpieza previa
        if "Categoría" in df_proy.columns: df_proy["Categoría"] = df_proy["Categoría"].apply(limpiar_textos)
        if not df_ent.empty: df_ent["Subcategoría"] = df_ent["Subcategoría"].apply(limpiar_textos)

        # --- FILTROS EN CASCADA ---
        col_f1, col_f2, col_f3 = st.columns(3)
        
        # 1. Filtro Año
        years_avail = sorted(df_proy["Año"].unique())
        f_ano = col_f1.multiselect("1. Año:", years_avail, key="f_cascade_ano")
        
        # Filtrado Nivel 1
        df_lvl1 = df_proy[df_proy["Año"].isin(f_ano)] if f_ano else df_proy
        
        # 2. Filtro Proyecto (Depende del Año)
        projs_avail = sorted(df_lvl1["Nombre del Proyecto"].unique())
        f_nom = col_f2.multiselect("2. Proyecto:", projs_avail, key="f_cascade_proy")
        
        # Filtrado Nivel 2
        df_lvl2 = df_lvl1[df_lvl1["Nombre del Proyecto"].isin(f_nom)] if f_nom else df_lvl1

        # 3. Filtro Categoría (Depende de Proyecto y Año)
        cats_raw = df_lvl2["Categoría"].unique()
        cats_avail = set()
        for c in cats_raw: cats_avail.update([limpiar_textos(x) for x in str(c).split(',')])
        f_cat = col_f3.multiselect("3. Categoría:", sorted(list(cats_avail)), key="f_cascade_cat")

        # Filtrado Final Proyectos
        df_v = df_lvl2.copy()
        if f_cat: df_v = df_v[df_v["Categoría"].apply(lambda x: any(limpiar_textos(c) in f_cat for c in str(x).split(',')))]

        st.markdown("---")
        
        # --- TABLA DE PROYECTOS ---
        with st.expander(f"📂 1. Tabla de Proyectos ({len(df_v)})", expanded=True):
            # Usamos key única y no recargamos si no es necesario
            ed_p = st.data_editor(df_v, use_container_width=True, key="ep_cascade", num_rows="fixed", column_config={
                "Categoría": st.column_config.TextColumn("Categoría(s)"),
                "Año": st.column_config.NumberColumn("Año", format="%d", step=1, required=True),
                "Periodo": st.column_config.SelectboxColumn("Periodo", options=["Primavera", "Verano", "Otoño"], required=True)
            })
            if st.button("💾 Actualizar Proyectos"):
                if "Categoría" in ed_p.columns: ed_p["Categoría"] = ed_p["Categoría"].apply(limpiar_textos)
                df_master_proy = load_data("Proyectos")
                # Actualización segura
                df_master_proy.set_index("Nombre del Proyecto", inplace=True)
                ed_p.set_index("Nombre del Proyecto", inplace=True)
                df_master_proy.update(ed_p)
                df_master_proy.reset_index(inplace=True)
                save_data(df_master_proy, "Proyectos")
                st.success("✅ Actualizado en la nube."); time.sleep(1); st.rerun()

        # --- TABLA DE ENTREGABLES (Con columnas ocultas) ---
        with st.expander("📦 2. Entregables Asociados", expanded=True):
            if not df_ent.empty:
                df_ef = df_ent[df_ent["Proyecto_Padre"].isin(df_v["Nombre del Proyecto"].unique())].copy()
                
                if not df_ef.empty:
                    # MODIFICACIÓN: Quitar columnas solicitadas
                    cols_a_quitar = ["Plantillas", "Responsable", "Estatus", "Observaciones"]
                    cols_existentes = [c for c in cols_a_quitar if c in df_ef.columns]
                    df_ef_clean = df_ef.drop(columns=cols_existentes)

                    ed_e = st.data_editor(df_ef_clean, use_container_width=True, key="ee_cascade", num_rows="fixed", 
                                          column_config={"Subcategoría": st.column_config.TextColumn("Subcategoría")})
                    
                    if st.button("💾 Actualizar Entregables"):
                        if "Subcategoría" in ed_e.columns: ed_e["Subcategoría"] = ed_e["Subcategoría"].apply(limpiar_textos)
                        df_master_ent = load_data("Entregables")
                        
                        # Combinamos los datos editados con las columnas ocultas originales
                        # (Para no perder la info de "Plantillas", etc. en la BD aunque no se vean aquí)
                        for idx, row in ed_e.iterrows():
                            # Buscamos por índice original si es posible, o por claves
                            pass 
                        # Método simplificado: Update sobre índice
                        # Nota: Si el usuario quiere borrar columnas de verdad, debe hacerlo en el excel.
                        # Aquí solo ocultamos visualmente. Para update seguro, necesitamos ID único.
                        # Como no hay ID, asumiremos coincidencia por Proyecto+Entregable o update global.
                        # Para este ejemplo simple, reconstruimos.
                        
                        # Estrategia: Actualizar solo las columnas visibles en el master
                        df_master_ent.update(ed_e) 
                        save_data(df_master_ent, "Entregables")
                        st.success("✅ Actualizado en la nube."); time.sleep(1); st.rerun()
                else: st.info("Sin entregables para estos proyectos.")
            else: st.info("Base de datos de entregables vacía.")

        with st.expander("🗑️ Zona de Borrado", expanded=False):
            ops = df_v["Nombre del Proyecto"].unique()
            if len(ops) > 0:
                d = st.selectbox("Eliminar:", ops)
                if st.button("Eliminar Definitivamente"):
                    save_data(df_proy[df_proy["Nombre del Proyecto"]!=d], "Proyectos")
                    if not df_ent.empty: save_data(df_ent[df_ent["Proyecto_Padre"]!=d], "Entregables")
                    st.success("Eliminado"); time.sleep(1); st.rerun()
    else: st.info("Cargando datos...")

# ==========================================
# PESTAÑA 4: GRÁFICAS (AHORA CON DONAS)
# ==========================================
with tab4:
    st.header("📊 Estadísticas en Vivo")
    
    try: df_p_s = load_data("Proyectos"); df_e_s = load_data("Entregables")
    except: df_p_s = pd.DataFrame(); df_e_s = pd.DataFrame()

    if not df_p_s.empty:
        if "Categoría" in df_p_s.columns: df_p_s["Categoría"] = df_p_s["Categoría"].apply(limpiar_textos)
        if not df_e_s.empty: df_e_s["Subcategoría"] = df_e_s["Subcategoría"].apply(limpiar_textos)

        # Filtros para gráficas
        c1, c2 = st.columns(2)
        yg = c1.multiselect("Filtrar Año", sorted(df_p_s["Año"].unique()), key="g_year")
        pg = c2.multiselect("Filtrar Periodo", ["Primavera", "Verano", "Otoño"], key="g_per")

        df_f = df_p_s.copy()
        if yg: df_f = df_f[df_f["Año"].isin(yg)]
        if pg: df_f = df_f[df_f["Periodo"].astype(str).str.strip().isin(pg)]

        if df_f.empty: st.warning("Sin datos para graficar.")
        else:
            st.markdown("---")
            
            # FILA 1: Barras y Dona de Periodos
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                st.subheader("📅 Proyectos por Año")
                pa = df_f["Año"].value_counts().reset_index(); pa.columns=["Año","Total"]
                graficar_barras(pa, "Año", "Total", "Año", "Cantidad", "#FF4B4B")
            
            with col_g2:
                st.subheader("🍰 Distribución por Periodo")
                data_p = df_f["Periodo"].value_counts().reset_index(); data_p.columns=["Periodo", "Total"]
                graficar_dona(data_p, "Periodo", "Total", "Proyectos por Periodo")

            st.markdown("---")
            
            # FILA 2: Categorías (Barras vs Dona)
            col_g3, col_g4 = st.columns(2)
            
            # Preparar datos categorías (explode por si hay multiples)
            sc = df_f["Categoría"].str.split(',').explode().str.strip(); sc=sc[sc!=""]; sc=sc[sc!="Nan"]
            data_c = sc.value_counts().reset_index(); data_c.columns=["Categoría", "Total"]

            with col_g3:
                st.subheader("📊 Categorías (Barras)")
                graficar_barras(data_c, "Categoría", "Total", "Categoría", "Total", "#E0E0E0")
            
            with col_g4:
                st.subheader("🍩 Categorías (Circular)")
                graficar_dona(data_c, "Categoría", "Total", "Distribución de Áreas")
            
            # Guardar para descarga
            st.session_state.stats_download = {
                "Por_Periodo": data_p,
                "Por_Categoría": data_c,
            }

# ==========================================
# PESTAÑA 5: DESCARGAS
# ==========================================
with tab5:
    st.header("📥 Centro de Descargas")
    
    st.subheader("1. Base de Datos Completa")
    if st.button("Generar Respaldo Completo (Excel)"):
        b = io.BytesIO()
        with pd.ExcelWriter(b, engine='openpyxl') as w: 
            load_data("Proyectos").to_excel(w, 'Proyectos', index=False)
            load_data("Entregables").to_excel(w, 'Entregables', index=False)
        st.download_button("⬇️ Descargar BD.xlsx", b.getvalue(), "Respaldo_Completo.xlsx")

    st.markdown("---")
    st.subheader("2. Reporte de Gráficas")
    if "stats_download" in st.session_state and not st.session_state.stats_download.get("Por_Categoría", pd.DataFrame()).empty:
        if st.button("Generar Reporte Estadístico"):
            b_stats = io.BytesIO()
            with pd.ExcelWriter(b_stats, engine='openpyxl') as w:
                st.session_state.stats_download["Por_Periodo"].to_excel(w, "Por Periodo", index=False)
                st.session_state.stats_download["Por_Categoría"].to_excel(w, "Por Categoría", index=False)
            st.download_button("⬇️ Descargar Reporte_Graficas.xlsx", b_stats.getvalue(), "Reporte_Graficas.xlsx")
    else:
        st.warning("⚠️ Ve a la pestaña 'Gráficas' primero para generar los datos.")

# ==========================================
# PESTAÑA 6: GLOSARIO
# ==========================================
with tab6:
    st.header("📖 Glosario de Términos")
    st.markdown("""
    ### 🗂️ Categorías
    * **Gestión:** Archivos que tengan que ver con la Dirección integral del proyecto.
    * **Comunicación:** Diseño y ejecución de mensajes, canales para alinear a internos/externos.
    * **Infraestructura:** Instalaciones fijas y móviles, planos arquitectónicos, señalética.
    * **Investigación:** História de la finca, del CEDRAM, mapeos de la zona.
    """)
