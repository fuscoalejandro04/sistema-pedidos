import streamlit as st
import pandas as pd
from fpdf import FPDF
import tempfile
import os

st.set_page_config(page_title="Gestión de Pedidos", layout="wide", initial_sidebar_state="expanded")

st.title("📦 Sistema de Carga de Pedidos")
st.markdown("---")

# Inicializar el carrito en la memoria de la sesión
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# 1. CARGAR DATOS
@st.cache_data
def load_databases():
    df_cli = pd.read_excel("DB_Clientes_Limpia.xlsx")
    df_prod = pd.read_excel("DB_Productos_Unificada.xlsx")
    return df_cli, df_prod

try:
    df_clientes, df_productos = load_databases()
except Exception as e:
    st.error(f"Error al cargar archivos: {e}")
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
    st.warning("No se encontró la base de clientes.")

st.markdown("---")

# 3. CATÁLOGO Y AGREGADO AL CARRITO
st.subheader("2. Catálogo de Productos")

col_f1, col_f2 = st.columns(2)
marcas_disponibles = sorted(df_productos['Marca'].dropna().unique())
marca_filtro = col_f1.selectbox("Filtrar por Línea / Marca:", options=["Todas"] + marcas_disponibles)
busqueda = col_f2.text_input("🔍 Buscar por Código, Modelo o Descripción:")

df_filtrado = df_productos.copy()
if marca_filtro != "Todas":
    df_filtrado = df_filtrado[df_filtrado['Marca'] == marca_filtro]

if busqueda:
    b_up = busqueda.upper()
    df_filtrado = df_filtrado[
        df_filtrado['Codigo'].astype(str).str.upper().str.contains(b_up) |
        df_filtrado['Modelo'].astype(str).str.upper().str.contains(b_up) |
        df_filtrado['Descripcion'].astype(str).str.upper().str.contains(b_up)
    ]

# Selector para agregar al pedido
st.markdown("##### Agregar al Pedido")
if not df_filtrado.empty:
    df_filtrado['Display'] = df_filtrado['Codigo'].astype(str) + " | " + df_filtrado['Descripcion'].astype(str) + " | $" + df_filtrado['Precio_Lista'].round(2).astype(str)
    
    col_sel, col_qty, col_btn = st.columns([3, 1, 1])
    prod_seleccionado = col_sel.selectbox("Seleccione el producto:", options=df_filtrado['Display'].tolist())
    cantidad = col_qty.number_input("Cantidad:", min_value=1, value=1, step=1)
    
    if col_btn.button("➕ Agregar al Carrito", use_container_width=True):
        prod_idx = df_filtrado[df_filtrado['Display'] == prod_seleccionado].index[0]
        prod_data = df_filtrado.loc[prod_idx]
        
        st.session_state.carrito.append({
            "Marca": prod_data['Marca'],
            "Codigo": prod_data['Codigo'],
            "Descripcion": prod_data['Descripcion'],
            "Precio_Lista": prod_data['Precio_Lista'],
            "IVA": prod_data['IVA'],
            "Cantidad": cantidad,
            "Subtotal": prod_data['Precio_Lista'] * cantidad
        })
        st.success(f"¡Agregado: {cantidad}x {prod_data['Codigo']}!")
else:
    st.info("No se encontraron productos con esa búsqueda.")

st.markdown("---")

# 4. RESUMEN DEL PEDIDO Y DESCUENTOS
st.subheader("3. Resumen del Pedido")

if st.session_state.carrito:
    df_carrito = pd.DataFrame(st.session_state.carrito)
    st.dataframe(df_carrito[['Codigo', 'Descripcion', 'Cantidad', 'Precio_Lista', 'Subtotal']], use_container_width=True)
    
    if st.button("🗑️ Vaciar Carrito"):
        st.session_state.carrito = []
        st.rerun()

    st.markdown("#### Bonificaciones y Cierre")
    
    # Configuramos las columnas para los descuentos individuales
    col_desc1, col_desc2, col_desc3, col_totales = st.columns([1, 1, 1, 2])
    
    desc_gen = col_desc1.number_input("Desc. General (%)", min_value=0.0, max_value=100.0, value=30.0, step=1.0)
    desc_ad1 = col_desc2.number_input("Desc. Adicional 1 (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0)
    desc_ad2 = col_desc3.number_input("Desc. Adicional 2 (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0)
    
    # Calcular cascada de multiplicadores
    multiplicador_desc = (1 - (desc_gen / 100)) * (1 - (desc_ad1 / 100)) * (1 - (desc_ad2 / 100))
    
    # Armar un texto limpio para el PDF solo con los descuentos que se usaron
    descuentos_usados = [f"-{d}%" for d in [desc_gen, desc_ad1, desc_ad2] if d > 0]
    texto_descuentos = " ".join(descuentos_usados) if descuentos_usados else "Sin bonificación"

    # Calcular totales
    subtotal_bruto = df_carrito['Subtotal'].sum()
    subtotal_neto = subtotal_bruto * multiplicador_desc
    
    df_carrito['Neto_Unitario'] = df_carrito['Precio_Lista'] * multiplicador_desc
    df_carrito['Subtotal_Neto'] = df_carrito['Neto_Unitario'] * df_carrito['Cantidad']
    df_carrito['Monto_IVA'] = df_carrito['Subtotal_Neto'] * df_carrito['IVA']
    
    total_iva = df_carrito['Monto_IVA'].sum()
    total_final = subtotal_neto + total_iva

    col_totales.metric("Subtotal Bruto", f"${subtotal_bruto:,.2f}")
    col_totales.metric(f"Neto ({texto_descuentos})", f"${subtotal_neto:,.2f}")
    col_totales.metric("Total Final (Inc. IVA)", f"${total_final:,.2f}")

    # 5. EXPORTACIÓN A PDF
    st.markdown("---")
    if st.button("📄 Generar PDF del Pedido", type="primary"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "PROFORMA DE PEDIDO", ln=True, align='C')
        pdf.ln(5)
        
        # Datos del Cliente
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 6, f"Cliente: {cliente_seleccionado}", ln=True)
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 6, f"CUIT: {cli_info.get('C.U.I.T.', '-')} | Condicion: {cli_info.get('FORMA DE PAGO', '-')}", ln=True)
        pdf.cell(0, 6, f"Vendedor: {cli_info.get('NOMB.VENDEDOR', '-')}", ln=True)
        pdf.ln(10)
        
        # Encabezados de Tabla
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(30, 8, "Codigo", border=1)
        pdf.cell(90, 8, "Descripcion", border=1)
        pdf.cell(15, 8, "Cant", border=1, align='C')
        pdf.cell(30, 8, "P. Unitario", border=1, align='R')
        pdf.cell(30, 8, "Subtotal", border=1, align='R')
        pdf.ln()
        
        # Filas de Productos
        pdf.set_font("Arial", '', 8)
        for _, row in df_carrito.iterrows():
            desc_corta = str(row['Descripcion'])[:50]
            pdf.cell(30, 6, str(row['Codigo']), border=1)
            pdf.cell(90, 6, desc_corta, border=1)
            pdf.cell(15, 6, str(row['Cantidad']), border=1, align='C')
            pdf.cell(30, 6, f"${row['Precio_Lista']:,.2f}", border=1, align='R')
            pdf.cell(30, 6, f"${row['Subtotal']:,.2f}", border=1, align='R')
            pdf.ln()
            
        # Totales
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(165, 6, "Subtotal Bruto:", align='R')
        pdf.cell(30, 6, f"${subtotal_bruto:,.2f}", align='R')
        pdf.ln()
        pdf.cell(165, 6, f"Bonificaciones ({texto_descuentos}):", align='R')
        pdf.cell(30, 6, f"${subtotal_neto:,.2f}", align='R')
        pdf.ln()
        pdf.cell(165, 6, "IVA Total:", align='R')
        pdf.cell(30, 6, f"${total_iva:,.2f}", align='R')
        pdf.ln()
        pdf.cell(165, 8, "TOTAL FINAL:", align='R')
        pdf.cell(30, 8, f"${total_final:,.2f}", align='R')
        
        # Guardar temporalmente y permitir descarga
        fd, path = tempfile.mkstemp(suffix=".pdf")
        try:
            pdf.output(path)
            with open(path, "rb") as f:
                pdf_bytes = f.read()
            st.download_button(
                label="⬇️ Descargar PDF",
                data=pdf_bytes,
                file_name="Pedido_Proforma.pdf",
                mime="application/pdf"
            )
            st.success("PDF generado exitosamente. ¡Haz clic en el botón de arriba para descargarlo!")
        finally:
            os.close(fd)
else:
    st.info("El carrito está vacío. Buscá un producto y agregalo al pedido.")
