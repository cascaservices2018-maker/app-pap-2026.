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
COLOR_FONDO_PRINCIPAL = "#A60000"  # Rojo Institucional
COLOR_BARRA_LATERAL = "#262730"    # Gris oscuro

estilos_css = f"""
<style>
    .stApp {{
        background-color: {COLOR_FONDO_PRINCIPAL};
    }}
    [data-testid="stSidebar"] {{
        background-color: {COLOR_BARRA_LATERAL};
    }}
    [data-testid="stMetricValue"], h1, h2, h3, p {{
        color: white !important;
    }}
    .vega-embed svg text {{
        fill: white !important;
    }}
</style>
"""
st.markdown(estilos_css, unsafe_allow_html=True)

# ==========================================
# 📖 DICCIONARIO INTELIGENTE (CORRECTOR DE ERRORES)
# ==========================================
# La clave (izquierda) es el error común o la raíz de la palabra.
# El valor (derecha) es la forma PERFECTA de escribirlo.
DICCIONARIO_CORRECTO = {
    # CATEGORÍAS PRINCIPALES
    "gestion": "Gestión",
    "gestión": "Gestión",
    
    "comunicacion": "Comunicación",
    "comunicasion": "Comunicación", # <--- Tu caso específico
    "comunica": "Comunicación",
    
    "infraestructura": "Infraestructura",
    "infra": "Infraestructura",
    
    "investigacion": "Investigación",
    "investigasion": "Investigación", # Error común s/c
    
    # SUBCATEGORÍAS
    "difusion": "Difusión",
    "difucion": "Difusión", # Error común s/c
    
    "vinculacion": "Vinculación",
    "vinc": "Vinculación",
    
    "financiamiento": "Financiamiento",
    "finanza": "Financiamiento",
    
    "diseno": "Diseño",
    "diseño": "Diseño",
    
    "arquitectonico": "Arquitectónico",
    "arquitectura": "Arquitectónico",
    
    "mantenimiento": "Mantenimiento",
    
    "teatrales": "Productos teatrales",
    "productos": "Productos teatrales",
    "producto": "Productos teatrales",
    
    "memoria": "Memoria/Archivo",
    "archivo": "Memoria/Archivo"
}

def normalizar_comparacion(texto):
    """Quita acentos y pone minúsculas para poder comparar 'comunicasion' con 'comunicación'"""
    if pd.isna(texto) or texto == "": return ""
    texto = str(texto).lower().strip()
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def limpiar_textos(texto_sucio):
    """
    Magia: Recibe 'comunicasion, difucion' y devuelve 'Comunicación, Difusión'
    """
    if pd.isna(texto_sucio) or str(texto_sucio).strip() == "": return ""
    
    # 1. Separar por comas (por si pusieron varias categorías)
    palabras = [p.strip() for p in str(texto_sucio).split(',')]
    palabras_corregidas = []
    
    for p in palabras:
        p_norm = normalizar_comparacion(p) # Convierte "Comunicasion" -> "comunicasion"
        encontrado = False
        
        # 2. Buscar en el diccionario
        for error_clave, correccion_perfecta in DICCIONARIO_CORRECTO.items():
            # Si el error conocido está dentro de lo que escribió el usuario
            if error_clave in p_norm: 
                palabras_corregidas.append(correccion_perfecta)
                encontrado = True
                break
        
        # 3. Si no es un error conocido, lo dejamos pero con Mayúscula inicial
        if not encontrado:
            palabras_corregidas.append(p.capitalize()) 
            
    # 4. Eliminar duplicados y ordenar (para que no salga "Diseño, Diseño")
    return ", ".join(sorted(list(dict.fromkeys(palabras_corregidas))))

# ==========================================
# 🔗 CONFIGURACIÓN DEL SISTEMA
# ==========================================

# --- TU LOGO AQUÍ ---
LOGO_URL = "https://github.com/cascaservices2018-maker/app-pap-2026./blob/main/cedramh3-removebg-preview.png?raw=true"

# --- LISTAS FIJAS ---
CATEGORIAS_LISTA = ["Gestión", "Comunicación", "Infraestructura", "Investigación"]
SUBCATEGORIAS_SUGERIDAS = [
    "Financiamiento", "Vinculación", "Memoria/archivo CEDRAM", 
    "Memoria/archivo PAP", "Diseño", "Difusión", 
    "Diseño arquitectónico", "Mantenimiento", "Productos teatrales"
]

# --- CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNCIONES ---
def load_data(sheet_name):
    try:
        df = conn.read(worksheet=sheet_name, ttl=5)
        if not df.empty:
            df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        try:
            time.sleep(2)
            df = conn.read(worksheet=sheet_name, ttl=5)
            if not df.empty:
                 df.columns = df.columns.str.strip()
            return df
        except:
            st.error(f"🚨 Error de conexión. Espera un poco y recarga la página.")
            return pd.DataFrame()

def save_data(df, sheet_name):
    try:
        conn.update(worksheet=sheet_name, data=df)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"No se pudo guardar: {e}")

def graficar_oscuro(df, x_col, y_col, titulo_x, titulo_y, color_barra="#FFFFFF"):
    chart = alt.Chart(df).mark_bar(color=color_barra).encode(
        x=alt.X(x_col, title=titulo_x, sort='-y'),
        y=alt.Y(y_col, title=titulo_y),
        tooltip=[x_col, y_col]
    ).configure_axis(
        labelColor='white', titleColor='white', gridColor='#660000'
    ).configure_view(
        strokeWidth=0
    ).properties(height=300)
    st.altair_chart(chart, use_container_width=True)

# --- INTERFAZ ---
with st.sidebar:
    st.image(LOGO_URL, width=280) 
    st.markdown("### ⚙️ Panel de Control")
    st.info("Sistema de Gestión de Proyectos PAP - 2026")
    st.markdown("---")
    st.write("Bienvenido al sistema colaborativo.")

col_logo, col_titulo = st.columns([2, 8])
with col_logo:
    st.image(LOGO_URL, width=170) 
with col_titulo:
    st.title("Base de datos PAP PERIODOS 2019-2026")

st.markdown("---")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "1. Registrar PROYECTO", 
    "2. Carga Masiva ENTREGABLES", 
    "3. 📝 Buscar y Editar", 
    "4. 📊 Gráficas",
    "5. 📥 Descargar Excel"
])

# ==========================================
# PESTAÑA 1
# ==========================================
with tab1:
    st.subheader("Nuevo Proyecto")
    with st.form("form_proyecto", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1: anio = st.number_input("Año", min_value=2019, max_value=2030, value=datetime.now().year)
        with col2: periodo = st.selectbox("Periodo", ["Primavera", "Verano", "Otoño"])
        with col3: cats_seleccionadas = st.multiselect("Categoría(s)", CATEGORIAS_LISTA)

        nombre_proyecto = st.text_input("Nombre del Proyecto")
        descripcion = st.text_area("Descripción")
        c_ent, c_com = st.columns(2)
        with c_ent: num_entregables = st.number_input("Estimado de Entregables", min_value=1, step=1, value=1)
        with c_com: comentarios = st.text_area("Comentarios")

        if st.form_submit_button("💾 Guardar Proyecto"):
            if not nombre_proyecto: st.error("El nombre es obligatorio")
            elif not cats_seleccionadas: st.error("Debes elegir al menos una categoría")
            else:
                df_proy = load_data("Proyectos")
                if not df_proy.empty and "Nombre del Proyecto" in df_proy.columns and nombre_proyecto in df_proy["Nombre del Proyecto"].values:
                     st.warning("⚠️ Ya existe un proyecto con ese nombre.")
                else:
                    # Limpiamos antes de guardar (Aquí entra la corrección automática)
                    categoria_str = limpiar_textos(", ".join(cats_seleccionadas))
                    
                    nuevo = {
                        "Año": anio, "Periodo": periodo, "Nombre del Proyecto": nombre_proyecto,
                        "Descripción": descripcion, "Num_Entregables": num_entregables,
                        "Categoría": categoria_str,
                        "Comentarios": comentarios,
                        "Fecha_Registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    df_updated = pd.concat([df_proy, pd.DataFrame([nuevo])], ignore_index=True)
                    save_data(df_updated, "Proyectos")
                    st.success("¡Proyecto guardado! (Ortografía corregida automáticamente)")

# ==========================================
# PESTAÑA 2
# ==========================================
with tab2:
    st.subheader("⚡ Carga Rápida de Entregables")
    st.info("💡 **Tip:** Escribe subcategorías como quieras (ej: 'difucion'). El sistema lo corregirá a 'Difusión' al guardar.")
    df_p = load_data("Proyectos")
    
    if df_p.empty: st.warning("Cargando proyectos...")
    elif "Nombre del Proyecto" in df_p.columns:
        lista_proyectos = sorted(df_p["Nombre del Proyecto"].unique().tolist())
        proyecto_sel = st.selectbox("Selecciona el Proyecto:", lista_proyectos)
        
        info_proyecto = df_p[df_p["Nombre del Proyecto"] == proyecto_sel].iloc[0]
        cat_auto = info_proyecto.get("Categoría", "General")
        num_estimado = int(info_proyecto.get("Num_Entregables", 5))
        st.caption(f"Categoría(s): **{cat_auto}** | Espacios generados: **{num_estimado}**")

        session_key = f"data_editor_{proyecto_sel}"
        if session_key not in st.session_state:
            st.session_state[session_key] = pd.DataFrame(index=range(num_estimado), columns=["Nombre_Entregable", "Contenido", "Subcategorías", "Plantillas_Usadas"])

        st.write("👇 **Llena la tabla:**")
        edited_df = st.data_editor(
            st.session_state[session_key], num_rows="dynamic", key=f"editor_widget_{proyecto_sel}", use_container_width=True, 
            column_config={
                "Subcategorías": st.column_config.TextColumn("Subcategoría(s)", default="General", help=f"Opciones: {', '.join(SUBCATEGORIAS_SUGERIDAS)}"),
                "Nombre_Entregable": st.column_config.TextColumn("Nombre Entregable", required=True),
                "Contenido": st.column_config.TextColumn("Contenido", width="large"),
                "Plantillas_Usadas": st.column_config.TextColumn("Link/Plantilla")
            }
        )

        if st.button("🚀 Guardar Todos los Entregables"):
            datos_validos = edited_df[edited_df["Nombre_Entregable"].notna() & (edited_df["Nombre_Entregable"] != "")].copy()
            if datos_validos.empty: st.error("La tabla está vacía.")
            else:
                try:
                    # Limpieza automática antes de guardar (CORRIGE ERRORES AQUÍ)
                    datos_validos["Subcategorías"] = datos_validos["Subcategorías"].apply(limpiar_textos)
                    
                    df_ent_cloud = load_data("Entregables")
                    nuevas_filas = []
                    fecha_hoy = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    for index, row in datos_validos.iterrows():
                        nuevas_filas.append({
                            "Proyecto_Padre": proyecto_sel, "Entregable": row["Nombre_Entregable"],
                            "Contenido": row["Contenido"], "Categoría": cat_auto,
                            "Subcategoría": row["Subcategorías"], "Plantillas": row["Plantillas_Usadas"],
                            "Fecha_Registro": fecha_hoy
                        })
                    df_final = pd.concat([df_ent_cloud, pd.DataFrame(nuevas_filas)], ignore_index=True)
                    save_data(df_final, "Entregables")
                    st.success(f"¡Éxito! Guardados {len(nuevas_filas)} entregables (Corregidos).")
                    del st.session_state[session_key]
                    st.balloons(); time.sleep(1); st.rerun()
                except Exception as e: st.error(f"Error al guardar: {e}")

# ==========================================
# PESTAÑA 3
# ==========================================
with tab3:
    st.header("📝 Edición de Base de Datos")
    st.info("💡 **Magia:** Si ves 'comunicasion', solo dale al botón 'Actualizar' y se convertirá en 'Comunicación'.")
    
    df_proy = load_data("Proyectos")
    df_ent = load_data("Entregables")

    if not df_proy.empty and "Año" in df_proy.columns:
        # Preparación de filtros usando la limpieza visual (limpia los filtros aunque la DB esté sucia)
        todas_cats = set()
        if "Categoría" in df_proy.columns:
            for c in df_proy["Categoría"].dropna(): 
                todas_cats.update([limpiar_textos(x) for x in str(c).split(',')])
        
        todas_subs = set()
        if not df_ent.empty and "Subcategoría" in df_ent.columns:
            for s in df_ent["Subcategoría"].dropna(): 
                todas_subs.update([limpiar_textos(x) for x in str(s).split(',')])

        c_nom, c1, c2, c3, c4 = st.columns(5)
        with c_nom: 
            lista_nombres = sorted(df_proy["Nombre del Proyecto"].unique().tolist())
            f_nombre = st.multiselect("🔍 Filtrar Proyecto:", lista_nombres)
        with c1: f_year = st.multiselect("Filtrar Año:", sorted(df_proy["Año"].unique()))
        with c2: f_period = st.multiselect("Filtrar Periodo:", ["Primavera", "Verano", "Otoño"])
        with c3: f_cat = st.multiselect("Filtrar Categoría:", sorted(list(todas_cats)))
        with c4: f_sub = st.multiselect("Filtrar Subcategoría:", sorted(list(todas_subs)))

        df_view = df_proy.copy()
        df_ent_view = df_ent.copy() if not df_ent.empty else pd.DataFrame()

        if f_nombre: df_view = df_view[df_view["Nombre del Proyecto"].isin(f_nombre)]
        if f_year: df_view = df_view[df_view["Año"].isin(f_year)]
        if f_period: df_view = df_view[df_view["Periodo"].isin(f_period)]
        
        if f_cat:
            mask_cat = df_view["Categoría"].apply(lambda x: any(limpiar_textos(c) in f_cat for c in str(x).split(',')))
            df_view = df_view[mask_cat]
        
        if f_sub and not df_ent_view.empty:
            mask_sub = df_ent_view["Subcategoría"].apply(lambda x: any(limpiar_textos(s) in f_sub for s in str(x).split(',')))
            df_ent_view = df_ent_view[mask_sub]
            df_view = df_view[df_view["Nombre del Proyecto"].isin(df_ent_view["Proyecto_Padre"].unique())]
        
        st.subheader(f"1. Proyectos ({len(df_view)})")
        edited_proy = st.data_editor(df_view, use_container_width=True, key="editor_proyectos_main", num_rows="fixed", column_config={"Categoría": st.column_config.TextColumn("Categoría(s)")})
        
        if st.button("💾 Actualizar y Corregir Proyectos"):
            try:
                # Limpieza AL GUARDAR
                if "Categoría" in edited_proy.columns: edited_proy["Categoría"] = edited_proy["Categoría"].apply(limpiar_textos)
                df_master_proy = load_data("Proyectos")
                df_master_proy.update(edited_proy)
                save_data(df_master_proy, "Proyectos")
                st.success("✅ Proyectos actualizados y ortografía corregida.")
            except Exception as e: st.error(f"Error: {e}")

        st.markdown("---")

        st.subheader("2. Entregables Asociados")
        if not df_ent.empty:
            if f_sub: 
                df_ent_final = df_ent_view[df_ent_view["Proyecto_Padre"].isin(df_view["Nombre del Proyecto"].unique())]
            else: 
                df_ent_final = df_ent[df_ent["Proyecto_Padre"].isin(df_view["Nombre del Proyecto"].unique())]
            
            if not df_ent_final.empty:
                edited_ent = st.data_editor(df_ent_final, use_container_width=True, key="editor_entregables_main", num_rows="fixed", column_config={"Subcategoría": st.column_config.TextColumn("Subcategoría")})
                if st.button("💾 Actualizar y Corregir Entregables"):
                    try:
                        # Limpieza AL GUARDAR
                        if "Subcategoría" in edited_ent.columns: edited_ent["Subcategoría"] = edited_ent["Subcategoría"].apply(limpiar_textos)
                        df_master_ent = load_data("Entregables")
                        df_master_ent.update(edited_ent)
                        save_data(df_master_ent, "Entregables")
                        st.success("✅ Entregables actualizados y ortografía corregida.")
                    except Exception as e: st.error(f"Error: {e}")
            else: st.info("No hay entregables con estos filtros.")
        else: st.info("Vacío.")

        st.markdown("---")
        with st.expander("🗑️ Zona de Borrado"):
            opciones_borrar = df_view["Nombre del Proyecto"].unique()
            if len(opciones_borrar) > 0:
                to_del = st.selectbox("Proyecto a eliminar:", opciones_borrar)
                if st.button("Eliminar Definitivamente"):
                    df_proy_new = df_proy[df_proy["Nombre del Proyecto"] != to_del]
                    if not df_ent.empty: save_data(df_ent[df_ent["Proyecto_Padre"] != to_del], "Entregables")
                    save_data(df_proy_new, "Proyectos")
                    st.success(f"Eliminado."); time.sleep(1); st.rerun()
    else: st.info("Cargando...")

# ==========================================
# PESTAÑA 4 (GRÁFICAS - AHORA LIMPIAS VISUALMENTE)
# ==========================================
with tab4:
    st.header("📊 Estadísticas en Vivo")
    try: df_p_s = load_data("Proyectos"); df_e_s = load_data("Entregables")
    except: df_p_s = pd.DataFrame(); df_e_s = pd.DataFrame()

    if not df_p_s.empty and "Año" in df_p_s.columns:
        # APLICAMOS LIMPIEZA EN VIVO PARA LAS GRÁFICAS
        # (Esto hace que "comunicasion" y "Comunicación" se sumen juntos en la barra)
        if "Categoría" in df_p_s.columns:
            df_p_s["Categoría"] = df_p_s["Categoría"].apply(limpiar_textos)
        if not df_e_s.empty and "Subcategoría" in df_e_s.columns:
            df_e_s["Subcategoría"] = df_e_s["Subcategoría"].apply(limpiar_textos)

        # Preparación de filtros
        cats_graph = set()
        for c in df_p_s["Categoría"].dropna(): 
            cats_graph.update([x.strip() for x in str(c).split(',') if x.strip()])
        
        subs_graph = set()
        if not df_e_s.empty:
            for s in df_e_s["Subcategoría"].dropna(): 
                subs_graph.update([x.strip() for x in str(s).split(',') if x.strip()])

        c1, c2, c3, c4 = st.columns(4)
        with c1: years_g = st.multiselect("Año", sorted(df_p_s["Año"].unique()), default=sorted(df_p_s["Año"].unique()))
        with c2: periods_g = st.multiselect("Periodo", ["Primavera", "Verano", "Otoño"], default=["Primavera", "Verano", "Otoño"])
        with c3: cat_g = st.multiselect("Categoría", sorted(list(cats_graph)))
        with c4: sub_g = st.multiselect("Subcategoría", sorted(list(subs_graph)))

        df_f = df_p_s[df_p_s["Año"].isin(years_g) & df_p_s["Periodo"].isin(periods_g)]
        df_e_f = df_e_s.copy() if not df_e_s.empty else pd.DataFrame()

        if cat_g:
            mask_cat = df_f["Categoría"].apply(lambda x: any(item in cat_g for item in str(x).split(', ')))
            df_f = df_f[mask_cat]

        if sub_g and not df_e_f.empty:
            mask_sub = df_e_f["Subcategoría"].apply(lambda x: any(item in sub_g for item in str(x).split(', ')))
            df_e_f = df_e_f[mask_sub]
            df_f = df_f[df_f["Nombre del Proyecto"].isin(df_e_f["Proyecto_Padre"].unique())]

        if df_f.empty: st.warning("No hay datos con esos filtros.")
        else:
            st.markdown("---")
            # --- EVOLUCIÓN ANUAL ---
            st.subheader("📅 Evolución Anual (Proyectos vs Entregables)")
            
            p_anios = df_f["Año"].value_counts().reset_index(); p_anios.columns=["Año", "Total"]; p_anios["Tipo"]="Proyectos"
            visibles = df_f["Nombre del Proyecto"].unique()
            
            if not df_e_s.empty:
                if sub_g: e_validos = df_e_f[df_e_f["Proyecto_Padre"].isin(visibles)]
                else: e_validos = df_e_s[df_e_s["Proyecto_Padre"].isin(visibles)]
                
                mapa_anios = df_f.set_index("Nombre del Proyecto")["Año"].to_dict()
                e_validos["Año_Real"] = e_validos["Proyecto_Padre"].map(mapa_anios)
                e_validos = e_validos.dropna(subset=["Año_Real"])
                e_anios = e_validos["Año_Real"].value_counts().reset_index(); e_anios.columns=["Año", "Total"]; e_anios["Tipo"]="Entregables"
            else: e_anios = pd.DataFrame()

            df_chart_anual = pd.concat([p_anios, e_anios], ignore_index=True)
            
            if not df_chart_anual.empty:
                base = alt.Chart(df_chart_anual).encode(
                    x=alt.X('Tipo:N', title=None, axis=None),
                    color=alt.Color('Tipo:N', scale=alt.Scale(domain=['Proyectos', 'Entregables'], range=['#FFFFFF', '#FFD700']), legend=alt.Legend(title="Tipo", labelColor="white", titleColor="white"))
                )
                bars = base.mark_bar(size=35, cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(y=alt.Y('Total:Q', title='Total'))
                text = base.mark_text(dy=-10, color='white').encode(y=alt.Y('Total:Q'), text=alt.Text('Total:Q'))
                
                # FACET para separar por años
                chart_anual = alt.layer(bars, text).properties(height=250).facet(
                    column=alt.Column('Año:O', header=alt.Header(labelColor="white", titleColor="white", titleOrient="bottom", labelOrient="bottom"))
                ).configure_view(stroke='transparent')
                
                st.altair_chart(chart_anual, use_container_width=True)
            
            st.markdown("---")
            # --- KPIs Y OTRAS GRÁFICAS ---
            k1, k2 = st.columns(2)
            k1.metric("Proyectos Filtrados", len(df_f))
            
            visibles = df_f["Nombre del Proyecto"].unique()
            if not df_e_s.empty:
                if sub_g: df_e_final_graph = df_e_s[df_e_s["Proyecto_Padre"].isin(visibles)]
                else: df_e_final_graph = df_e_f[df_e_f["Proyecto_Padre"].isin(visibles)]
            else: df_e_final_graph = pd.DataFrame()

            k2.metric("Entregables Asociados", len(df_e_final_graph))

            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Por Periodo")
                dp = df_f["Periodo"].value_counts().reset_index(); dp.columns=["Periodo","Cantidad"]
                graficar_oscuro(dp, "Periodo", "Cantidad", "Periodo", "Total", "#FFFFFF")
            with c2:
                st.subheader("Por Categoría")
                if "Categoría" in df_f.columns:
                    sc = df_f["Categoría"].astype(str).str.split(',').explode().str.strip() # Ya viene limpio arriba
                    sc = sc[sc != "Nan"]; sc = sc[sc != ""]
                    dc = sc.value_counts().reset_index(); dc.columns=["Categoría","Cantidad"]
                    graficar_oscuro(dc, "Categoría", "Cantidad", "Categoría", "Total", "#E0E0E0")
            st.markdown("---")
            st.subheader("📦 Subcategorías")
            if not df_e_final_graph.empty and "Subcategoría" in df_e_final_graph.columns:
                 ss = df_e_final_graph["Subcategoría"].astype(str).str.split(',').explode().str.strip() # Ya viene limpio
                 ss = ss[ss != "Nan"]; ss = ss[ss != ""]
                 ds = ss.value_counts().reset_index(); ds.columns=["Subcategoría","Cantidad"]
                 graficar_oscuro(ds, "Subcategoría", "Cantidad", "Subcategoría", "Total", "#CCCCCC")
    else: st.info("Cargando...")

# ==========================================
# PESTAÑA 5
# ==========================================
with tab5:
    st.header("📥 Exportar")
    if st.button("Generar Excel"):
        with st.spinner("Descargando..."):
            b = io.BytesIO()
            with pd.ExcelWriter(b, engine='openpyxl') as w:
                load_data("Proyectos").to_excel(w, 'Proyectos', index=False)
                load_data("Entregables").to_excel(w, 'Entregables', index=False)
            st.download_button("⬇️ Descargar .xlsx", b.getvalue(), f"Reporte_{datetime.now().strftime('%Y-%m-%d')}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
