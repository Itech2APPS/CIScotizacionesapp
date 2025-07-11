
import streamlit as st
import fitz
import os
import tempfile
import re
import zipfile
from unidecode import unidecode

def limpiar_texto(texto):
    return unidecode(texto).replace("'", "").strip().upper()

# Buscar el mes que aparece después del bloque "N° Folio\nPlanilla"
def extraer_mes(texto):
    patron = re.compile(
        r"N° Folio\s*Planilla\s*.*?\n(?:.*?)\n((Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto|Septiembre|Octubre|Noviembre|Diciembre))",
        re.IGNORECASE | re.DOTALL
    )
    match = patron.search(texto)
    return match.group(1).capitalize() if match else None

def procesar_pdf(uploaded_file):
    output_dir = tempfile.mkdtemp()
    zip_output_path = os.path.join(output_dir, "cotizaciones_separadas.zip")
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    pdf_paths = []

    for i, page in enumerate(doc):
        text = page.get_text()

        nombre_match = re.search(r"del Sr\.\(a\)\s+([A-ZÑÁÉÍÓÚ ]+),", text)
        rut_match = re.search(r"Rut:?\s*([\d\.]+-[\dkK])", text)
        mes = extraer_mes(text)

        if rut_match and nombre_match and mes:
            rut = rut_match.group(1).replace(".", "")
            nombre_completo = limpiar_texto(nombre_match.group(1))
            primer_nombre = nombre_completo.split()[0]
            apellidos = " ".join(nombre_completo.split()[1:])
            nombre_archivo = f"COTIZACIONES_{mes}_{rut}_{primer_nombre}_{apellidos}.pdf".replace(" ", "_")

            nuevo_pdf_path = os.path.join(output_dir, nombre_archivo)
            nuevo_pdf = fitz.open()
            nuevo_pdf.insert_pdf(doc, from_page=i, to_page=i)
            nuevo_pdf.save(nuevo_pdf_path)
            nuevo_pdf.close()

            pdf_paths.append(nuevo_pdf_path)
        else:
            st.warning(f"No se pudo procesar la página {i+1}. Revisa si contiene RUT, nombre y el mes después del bloque N° Folio / Planilla.")

    doc.close()

    if pdf_paths:
        with zipfile.ZipFile(zip_output_path, 'w') as zipf:
            for path in pdf_paths:
                zipf.write(path, arcname=os.path.basename(path))

        with open(zip_output_path, "rb") as f:
            st.download_button(
                label="📦 Descargar todos los PDFs en ZIP",
                data=f,
                file_name="cotizaciones_separadas.zip",
                mime="application/zip"
            )
    else:
        st.error("No se generaron archivos. Verifica el formato del PDF.")

st.set_page_config(page_title="Divisor de Cotizaciones", layout="centered")
st.title("🔍 Divisor de Cotizaciones Previsionales")
st.write("Sube un archivo PDF de cotizaciones y descarga automáticamente todos los archivos en un ZIP.")

uploaded_file = st.file_uploader("📁 Sube tu archivo PDF", type=["pdf"])
if uploaded_file:
    procesar_pdf(uploaded_file)