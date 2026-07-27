import streamlit as st
import pandas as pd

st.set_page_config(page_title="Gestión de Pedidos", layout="wide", initial_sidebar_state="expanded")

st.title("📦 Sistema de Carga de Pedidos")
st.markdown("---")

# 1. CARGAR DATOS DESDE LAS BASES UNIFICADAS
@st.cache_data
def load_databases():
    df_cli = pd.read_excel("DB_Clientes_Limpia.xlsx")
    df_prod = pd.read_excel("DB_Productos_Unificada.xlsx")
    return df_cli, df_prod

try:
    df_clientes, df_productos = load_databases()
    st.sidebar.success("✅ Base de datos conectada correctamente.")
except Exception as e:
    st.sidebar.error(f"Error al cargar archivos en la nube: {e}")
    st.stop()

# 2. SELECCIÓN DE CLIENTE
st.subheader("1. Selección de Cliente")
if 'DENOMINACÍON LEGAL' in df_clientes.columns:
    lista_clientes = sorted(df_clientes['DENOMINACÍON LEGAL'].dropna().unique())
    cliente_seleccionado = st.selectbox("Buscar / Seleccionar Cliente:", options=lista_clientes)
    
    cli_info = df_clientes[df_clientes['DENOMINACÍON LEGAL'] == cliente_seleccionado].iloc[0]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("CUIT", str(cli_info.get('C.U.I.T.', '-')))
    col2.metric("Localidad", str(cli_info.get('LOCALIDAD', '-')))
    col3.metric("Condición de Pago", str(cli_info.get('FORMA DE PAGO', '-')))
    col4.metric("Vendedor", str(cli_info.get('NOMB.VENDEDOR', '-')))
else:
    st.warning("No se encontró la columna de denominación legal.")

st.markdown("---")

# 3. FILTRADO Y BÚSQUEDA DE PRODUCTOS
st.subheader("2. Catálogo de Productos y Armado de Pedido")

# Filtros laterales o superiores
col_f1, col_f2 = st.columns(2)
marcas_disponibles = sorted(df_productos['Marca'].dropna().unique())
marca_filtro = col_f1.selectbox("Filtrar por Línea / Marca:", options=["Todas"] + marcas_disponibles)
busqueda = col_f2.text_input("🔍 Buscar por Código, Modelo o Descripción:")

# Aplicar filtros
df_filtrado = df_productos.copy()
if marca_filtro != "Todas":
    df_filtrado = df_filtrado[df_filtrado['Marca'] == marca_filtro]

if busqueda:
    busqueda_upper = busqueda.upper()
    df_filtrado = df_filtrado[
        df_filtrado['Codigo'].astype(str).str.upper().str.contains(busqueda_upper) |
        df_filtrado['Modelo'].astype(str).str.upper().str.contains(busqueda_upper) |
        df_filtrado['Descripcion'].astype(str).str.upper().str.contains(busqueda_upper) |
        df_filtrado['Titulo'].astype(str).str.upper().str.contains(busqueda_upper)
    ]

# Mostrar tabla interactiva de productos
st.dataframe(
    df_filtrado[['Marca', 'Codigo', 'Titulo', 'Modelo', 'Descripcion', 'Precio_Lista', 'IVA']],
    use_container_width=True,
    hide_index=True
)

st.markdown("---")
st.subheader("3. Resumen y Exportación")
if st.button("Generar Resumen de Pedido", type="primary"):
    st.success("¡Estructura de pedido lista para procesar!")