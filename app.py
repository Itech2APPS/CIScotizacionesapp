# app.py
import streamlit as st
import fitz  # PyMuPDF
import re
import os
import zipfile
import tempfile
from io import BytesIO

st.set_page_config(page_title="Divisor de Cotizaciones PDF", page_icon="📑")
st.title("📑 Divisor y Renombrador de Cotizaciones PDF (ZIP ordenado)")

def sanitize_filename(s: str) -> str:
    s = s.strip()
    s = re.sub(r'\s+', '_', s)                     # espacios -> guiones bajos
    s = re.sub(r'[<>:"/\\|?*]', '', s)             # quitar chars inválidos en Windows
    s = re.sub(r'_+', '_', s)                      # colapsar underscores repetidos
    return s

uploaded_file = st.file_uploader("Sube el archivo PDF", type=["pdf"])

if uploaded_file:
    with tempfile.TemporaryDirectory() as temp_dir:
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        st.write(f"📄 Total de páginas detectadas: {len(doc)}")

        archivos_generados = []  # lista de rutas a los PDFs (sin prefijos visibles)

        for i, page in enumerate(doc, start=1):
            text = page.get_text("text")

            # Extraer nombre (ajusta regex si tu formato es distinto)
            nombre_match = re.search(r"cotizaciones previsionales del Sr.\(a\)\s+([A-ZÁÉÍÓÚÑ&\s]+)[,\\n]", text, re.IGNORECASE)
            nombre_raw = nombre_match.group(1).strip() if nombre_match else f"DESCONOCIDO_{i}"
            nombre = sanitize_filename(nombre_raw)

            # Extraer RUT
            rut_match = re.search(r"Rut[:\s]*([\d\.]+-[0-9kK])", text, re.IGNORECASE)
            rut = rut_match.group(1).replace(".", "") if rut_match else f"SINRUT_{i}"

            # Extraer mes (solo el nombre del mes)
            mes_match = re.search(r"(Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto|Septiembre|Octubre|Noviembre|Diciembre)", text, re.IGNORECASE)
            mes = mes_match.group(1).capitalize() if mes_match else "SINMES"
            mes = sanitize_filename(mes)

            # Crear PDF por página
            new_doc = fitz.open()
            new_doc.insert_pdf(doc, from_page=i-1, to_page=i-1)
            filename = f"COTIZACIONES_{mes}_{rut}_{nombre}.pdf"   # sin numeración visible
            filepath = os.path.join(temp_dir, filename)
            new_doc.save(filepath)
            new_doc.close()

            archivos_generados.append(filepath)

        doc.close()

        # Crear ZIP: dentro del ZIP añadimos los archivos con prefijo numérico
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
            for idx, filepath in enumerate(archivos_generados, start=1):
                basename = os.path.basename(filepath)
                arcname = f"{idx:03d}_{basename}"   # prefijo para forzar orden al extraer
                zipf.write(filepath, arcname=arcname)

            # Agregar un .bat para Windows que remueve el prefijo "NNN_"
            win_bat = r"""@echo off
setlocal enabledelayedexpansion
echo Removiendo prefijos numericos (NNN_) de archivos...
for /f "delims=" %%f in ('dir /b /a-d *_COTIZACIONES_*.pdf ^| sort') do (
  set "fname=%%f"
  ren "%%f" "!fname:~4!"
)
endlocal
echo Hecho.
pause
"""
            zipf.writestr("REMOVE_PREFIXES_WINDOWS.bat", win_bat)

            # Agregar un .sh para macOS / Linux
            unix_sh = """#!/bin/bash
echo "Removiendo prefijos numericos (NNN_) de archivos..."
for f in [0-9][0-9][0-9]_*COTIZACIONES_*.pdf; do
  # mueve archivo removiendo los primeros 4 caracteres (NNN_)
  mv -- "$f" "${f:4}"
done
echo "Hecho."
"""
            zipf.writestr("remove_prefixes_unix.sh", unix_sh)

            # README con instrucciones
            readme = (
                "INSTRUCCIONES:\n\n"
                "1) Extrae el ZIP en una carpeta.\n"
                "2) Verás los archivos con prefijo numérico (p.ej. 001_COTIZACIONES_...).\n"
                "   Eso asegura que el Explorador de Windows los muestre en el orden original.\n"
                "3) Si quieres eliminar los prefijos y dejar sólo 'COTIZACIONES_MES_RUT_NOMBRE.pdf':\n"
                "   - En Windows: haz doble clic en REMOVE_PREFIXES_WINDOWS.bat\n"
                "   - En macOS/Linux: abre Terminal en esa carpeta y ejecuta:\n"
                "       bash remove_prefixes_unix.sh\n\n"
                "Nota: el script renombra los archivos REMOVIENDO el prefijo 'NNN_'.\n"
            )
            zipf.writestr("README.txt", readme)

        zip_buffer.seek(0)

        st.success("✅ Proceso completado. ZIP listo para descargar.")
        st.download_button(
            "⬇️ Descargar ZIP con todos los PDFs (ordenado)",
            zip_buffer,
            file_name="COTIZACIONES_PROCESADAS.zip",
            mime="application/zip"
        )
# 👣 Footer opcional - BY ISMAEL LEON
st.markdown("<hr style='margin-top:40px;'>", unsafe_allow_html=True)
st.markdown("Desarrollado por Ismael León – © 2025", unsafe_allow_html=True)
