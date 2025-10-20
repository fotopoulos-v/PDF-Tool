import streamlit as st
import subprocess
import os
import tempfile
from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter
import fitz  # PyMuPDF
# Import for new feature
import json
import io

st.set_page_config(page_title="PDF Tool", layout="wide")
st.markdown("""
    <div style="display: flex; align-items: center; gap: 10px;">
        <img src="https://i.imgur.com/Sz8WC8L.png" width="40">
        <h1 style="margin: 0;">PDF Tool</h1>
    </div>
""", unsafe_allow_html=True)

# Sidebar for action selection
action = st.sidebar.radio(
    "Select Action",
    ["Compress", "Extract Text", "Extract Pages", "Merge", "Split", "Rotate", "Convert to PDF"],
    index=0
)

# Function to run subprocess command and handle errors
def run_subprocess(cmd, input_path, output_path):
    """Encapsulates subprocess call and error checking."""
    # Timeout set to 5 minutes to prevent long-running processes on large files
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300) 
        
        # Check if output file was created (essential for Ghostscript and pandoc)
        if result.returncode == 0 and os.path.exists(output_path):
            return True, None
        else:
            # Check for common dependency errors
            if "wkhtmltopdf" in cmd[0] and "cannot execute binary file" in result.stderr:
                return False, "❌ wkhtmltopdf is installed but may require the correct architecture or dependencies (like `libcairo2-dev`)."
            if "pandoc" in cmd[0] and result.returncode != 0:
                 return False, f"Pandoc failed with error: {result.stderr or result.stdout}"
            return False, result.stderr
    except FileNotFoundError:
        return False, f"Required external tool not found: {cmd[0]}. Check if dependencies are installed in `packages.txt`."
    except subprocess.TimeoutExpired:
        return False, "Process timed out after 5 minutes."
    except Exception as e:
        return False, str(e)


# --- Compress Section ---
if action == "Compress":
    st.header("Compress PDF")
    st.write("Reduce your PDF file size using Ghostscript compression.")
    
    uploaded_file = st.file_uploader("Upload PDF", type="pdf", key="compress_file")
    
    compression_map = {
        1: (72, "Maximum (smallest file)"),
        2: (100, "High"),
        3: (150, "Medium"),
        4: (250, "Low"),
        5: (300, "Minimum (best quality)")
    }
    
    compression_level = st.slider(
        "Compression Level",
        min_value=1,
        max_value=5,
        value=3,
        help="1 = Maximum compression (smaller file), 5 = Minimum compression (best quality)")
    
    dpi_value = compression_map[compression_level][0]
    description = compression_map[compression_level][1]
    st.caption(f"Selected: {description}")
    
    if uploaded_file and st.button("Compress PDF"):
        file_size_mb = uploaded_file.size / (1024 * 1024)
        if file_size_mb > 80:
            st.warning(f"⚠️ Large file ({file_size_mb:.1f} MB) - this may take a while.")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = os.path.join(temp_dir, "input.pdf")
            output_path = os.path.join(temp_dir, "compressed.pdf")
            
            with open(input_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            try:
                
                # Loader
                status_container = st.empty()
                
                # --- Conditional Message Logic ---
                if file_size_mb > 80:
                    loader_text = "Compressing PDF... Please wait."
                else:
                    loader_text = "Compressing PDF... Please wait. Image-heavy PDFs may take a while."
                    
                status_container.markdown(f"""
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <img src="https://cdn.pixabay.com/animation/2023/08/11/21/18/21-18-05-265_256.gif" width="30">
                        <h3 style="margin: 0;">{loader_text}</h3>
                    </div>
                """, unsafe_allow_html=True)
                # --- End Conditional Message Logic ---
                
                pdf_setting = "/ebook" if compression_level >= 4 else "/screen"
                
                cmd = [
                    "gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
                    f"-dPDFSETTINGS={pdf_setting}", "-dNOPAUSE", "-dQUIET", "-dBATCH",
                    "-dDetectDuplicateImages", "-dCompressFonts=true",
                    f"-r{dpi_value}x{dpi_value}",
                    f"-sOutputFile={output_path}", input_path
                ]
                
                success, error = run_subprocess(cmd, input_path, output_path)
                status_container.empty()
                
                if success:
                    original_size = os.path.getsize(input_path) / (1024 * 1024)
                    compressed_size = os.path.getsize(output_path) / (1024 * 1024)
                    
                    if compressed_size > original_size:
                        st.warning("⚠️ Output file is larger than input. Please choose a lower compression level.")
                    else:
                        reduction = ((original_size - compressed_size) / original_size) * 100
                        st.success("✅ Compression complete!")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Original Size", f"{original_size:.2f} MB")
                        with col2:
                            st.metric("Compressed Size", f"{compressed_size:.2f} MB")
                        with col3:
                            st.metric("Reduction", f"{reduction:.1f}%")
                        
                        output_filename = uploaded_file.name.replace(".pdf", "_compressed.pdf")
                        with open(output_path, "rb") as f:
                            st.download_button(
                                label="📥 Download Compressed PDF",
                                data=f.read(),
                                file_name=output_filename,
                                mime="application/pdf"
                            )
                else:
                    st.error(f"❌ Compression failed: {error}")
            except Exception as e:
                st.error(f"❌ Error: {e}")


# --- Extract Text Section ---
elif action == "Extract Text":
    st.header("Extract Text from PDF")
    uploaded_file = st.file_uploader("Upload PDF", type="pdf", key="extract_text_file")
    
    if uploaded_file and st.button("Extract Text"):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = os.path.join(temp_dir, "input.pdf")
            with open(input_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            try:
                status_container = st.empty()
                status_container.markdown("""
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <img src="https://cdn.pixabay.com/animation/2023/08/11/21/18/21-18-05-265_256.gif" width="30">
                        <h3 style="margin: 0;">Extracting text... Please wait</h3>
                    </div>
                """, unsafe_allow_html=True)
                
                reader = PdfReader(input_path)
                text = ""
                for page_num, page in enumerate(reader.pages, 1):
                    extracted = page.extract_text()
                    if extracted:
                        text += f"--- Page {page_num} ---\n{extracted}\n\n"
                
                status_container.empty()
                st.success("✅ Text extracted successfully!")
                
                # Use reportlab to create a PDF of the extracted text for cleaner download
                from reportlab.pdfgen import canvas
                from reportlab.lib.pagesizes import letter
                
                pdf_path = os.path.join(temp_dir, "extracted_text.pdf")
                c = canvas.Canvas(pdf_path, pagesize=letter)
                width, height = letter
                y = height - 50
                
                for line in text.split("\n"):
                    if y < 50:
                        c.showPage()
                        y = height - 50
                    safe_line = line[:1000]
                    if safe_line.strip():
                        c.drawString(40, y, safe_line)
                    y -= 12
                c.save()
                
                original_name = Path(uploaded_file.name).stem
                pdf_filename = f"{original_name}_text.pdf"
                txt_filename = f"{original_name}_text.txt"
                
                col1, col2 = st.columns(2)
                with col1:
                    with open(pdf_path, "rb") as f:
                        st.download_button("📥 Download as PDF", f.read(), pdf_filename, "application/pdf")
                with col2:
                    st.download_button("📥 Download as Text", text, txt_filename, "text/plain")
                
                with st.expander("Preview (first 500 characters)"):
                    st.text(text[:500])
            except Exception as e:
                st.error(f"❌ Error: {e}")


# --- Extract Pages Section ---
elif action == "Extract Pages":
    st.header("Extract Pages from PDF")
    uploaded_file = st.file_uploader("Upload PDF", type="pdf", key="extract_pages_file")
    
    if uploaded_file:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = os.path.join(temp_dir, "input.pdf")
            with open(input_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            try:
                reader = PdfReader(input_path)
                total_pages = len(reader.pages)
                st.info(f"Total pages in PDF: {total_pages}")
                
                col1, col2 = st.columns(2)
                with col1:
                    from_page = st.number_input("From Page", 1, total_pages, 1)
                with col2:
                    to_page = st.number_input("To Page", 1, total_pages, total_pages)
                
                if st.button("Extract Pages"):
                    if from_page <= to_page:
                        status_container = st.empty()
                        status_container.markdown("""
                            <div style="display: flex; align-items: center; gap: 15px;">
                                <img src="https://cdn.pixabay.com/animation/2023/08/11/21/18/21-18-05-265_256.gif" width="30">
                                <h3 style="margin: 0;">Extracting pages... Please wait</h3>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        writer = PdfWriter()
                        for page_num in range(from_page - 1, to_page):
                            writer.add_page(reader.pages[page_num])
                        
                        output_path = os.path.join(temp_dir, "extracted.pdf")
                        with open(output_path, "wb") as f:
                            writer.write(f)
                        
                        status_container.empty()
                        st.success("✅ Pages extracted successfully!")
                        output_filename = uploaded_file.name.replace(".pdf", f"_pages_{from_page}_to_{to_page}.pdf")
                        with open(output_path, "rb") as f:
                            st.download_button("Download Extracted PDF", f.read(), output_filename, "application/pdf")
                    else:
                        st.error("❌ 'From Page' must be less than or equal to 'To Page'")
            except Exception as e:
                st.error(f"❌ Error: {e}")

# --- Merge PDFs Section ---
elif action == "Merge":
    st.header("Merge PDFs")
    uploaded_files = st.file_uploader("Upload PDFs", type="pdf", accept_multiple_files=True, key="merge_files")
    
    if uploaded_files and len(uploaded_files) > 1:
        st.info(f"Ready to merge {len(uploaded_files)} PDFs")
        if st.button("Merge PDFs"):
            with tempfile.TemporaryDirectory() as temp_dir:
                writer = PdfWriter()
                try:
                    status_container = st.empty()
                    status_container.markdown("""
                        <div style="display: flex; align-items: center; gap: 15px;">
                            <img src="https://cdn.pixabay.com/animation/2023/08/11/21/18/21-18-05-265_256.gif" width="30">
                            <h3 style="margin: 0;">Merging PDFs... Please wait</h3>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    for i, uploaded_file in enumerate(uploaded_files):
                        input_path = os.path.join(temp_dir, f"input_{i}.pdf")
                        with open(input_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        reader = PdfReader(input_path)
                        for page in reader.pages:
                            writer.add_page(page)
                    
                    output_path = os.path.join(temp_dir, "merged.pdf")
                    with open(output_path, "wb") as f:
                        writer.write(f)
                    
                    status_container.empty()
                    st.success("✅ PDFs merged successfully!")
                    with open(output_path, "rb") as f:
                        st.download_button("Download Merged PDF", f.read(), "merged.pdf", "application/pdf")
                except Exception as e:
                    st.error(f"❌ Error: {e}")
    elif uploaded_files and len(uploaded_files) == 1:
        st.warning("⚠️ Please upload at least 2 PDFs.")

# --- Split PDF Section ---
elif action == "Split":
    st.header("Split PDF")
    uploaded_file = st.file_uploader("Upload PDF", type="pdf", key="split_file")
    
    if uploaded_file and st.button("Split PDF"):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = os.path.join(temp_dir, "input.pdf")
            with open(input_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            try:
                status_container = st.empty()
                status_container.markdown("""
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <img src="https://cdn.pixabay.com/animation/2023/08/11/21/18/21-18-05-265_256.gif" width="30">
                        <h3 style="margin: 0;">Splitting PDF... Please wait</h3>
                    </div>
                """, unsafe_allow_html=True)
                
                reader = PdfReader(input_path)
                total_pages = len(reader.pages)
                st.success(f"✅ PDF split into {total_pages} pages!")
                
                import zipfile
                zip_buffer = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
                with zipfile.ZipFile(zip_buffer.name, 'w') as zf:
                    for page_num, page in enumerate(reader.pages, 1):
                        writer = PdfWriter()
                        writer.add_page(page)
                        page_path = os.path.join(temp_dir, f"page_{page_num}.pdf")
                        with open(page_path, "wb") as f:
                            writer.write(f)
                        zf.write(page_path, arcname=f"page_{page_num}.pdf")
                
                status_container.empty()
                original_name = Path(uploaded_file.name).stem
                zip_filename = f"{original_name}.zip"
                with open(zip_buffer.name, "rb") as f:
                    st.download_button("Download All Pages (ZIP)", f.read(), zip_filename, "application/zip")
            except Exception as e:
                st.error(f"❌ Error: {e}")


# --- Rotate Section ---
elif action == "Rotate":
    st.header("Rotate PDF Pages")
    uploaded_file = st.file_uploader("Upload PDF", type="pdf", key="rotate_file")
    rotation = st.selectbox("Rotation", ["90°", "180°", "270°"], index=0)
    
    if uploaded_file and st.button("Rotate PDF"):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = os.path.join(temp_dir, "input.pdf")
            with open(input_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            try:
                status_container = st.empty()
                status_container.markdown("""
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <img src="https://cdn.pixabay.com/animation/2023/08/11/21/18/21-18-05-265_256.gif" width="30">
                        <h3 style="margin: 0;">Rotating PDF... Please wait</h3>
                    </div>
                """, unsafe_allow_html=True)
                
                rotation_map = {"90°": 90, "180°": 180, "270°": 270}
                rotation_degrees = rotation_map[rotation]
                
                reader = PdfReader(input_path)
                writer = PdfWriter()
                for page in reader.pages:
                    page.rotate(rotation_degrees)
                    writer.add_page(page)
                
                output_path = os.path.join(temp_dir, "rotated.pdf")
                with open(output_path, "wb") as f:
                    writer.write(f)
                
                status_container.empty()
                st.success("✅ PDF rotated successfully!")
                
                original_name = Path(uploaded_file.name).stem
                rotated_filename = f"{original_name}_rotated.pdf"
                with open(output_path, "rb") as f:
                    st.download_button("Download Rotated PDF", f.read(), rotated_filename, "application/pdf")
            except Exception as e:
                st.error(f"❌ Error: {e}")

# --- Convert to PDF Section ---
elif action == "Convert to PDF":
    st.header("Convert Files to PDF")
    st.write("Convert text and document files (txt, docx, html, py, ipynb) into a PDF document.")

    uploaded_file = st.file_uploader(
        "Upload File", 
        type=["txt", "doc", "docx", "odt", "ipynb", "py", "html"], 
        key="convert_file"
    )

    if uploaded_file and st.button("Convert to PDF"):
        file_extension = Path(uploaded_file.name).suffix.lower()
        original_name = Path(uploaded_file.name).stem
        
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = os.path.join(temp_dir, f"input{file_extension}")
            output_path = os.path.join(temp_dir, "output.pdf")
            
            # Save uploaded file
            with open(input_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            status_container = st.empty()
            status_container.markdown("""
                <div style="display: flex; align-items: center; gap: 15px;">
                    <img src="https://cdn.pixabay.com/animation/2023/08/11/21/18/21-18-05-265_256.gif" width="30">
                    <h3 style="margin: 0;">Converting file... Please wait</h3>
                </div>
            """, unsafe_allow_html=True)
            
            try:
                conversion_success = False
                error_message = ""

                # --- TXT Conversion ---
                if file_extension == ".txt":
                    from reportlab.pdfgen import canvas
                    from reportlab.lib.pagesizes import letter
                    from reportlab.lib.units import inch

                    with open(input_path, "r", encoding="utf-8") as f:
                        text = f.read()
                    
                    c = canvas.Canvas(output_path, pagesize=letter)
                    width, height = letter
                    margin = 0.75 * inch  # 0.75 inch margins all around
                    y = height - margin
                    c.setFont("Courier", 10)
                    
                    for line in text.split("\n"):
                        # wrap lines if too long
                        while len(line) > 0:
                            c.drawString(margin, y, line[:95])
                            line = line[95:]
                            y -= 12
                            if y < margin:
                                c.showPage()
                                y = height - margin
                                c.setFont("Courier", 10)
                    c.save()
                    conversion_success = True

                # --- PY Conversion (with syntax highlighting, fixed) ---
                elif file_extension == ".py":
                    py_content = uploaded_file.getvalue().decode("utf-8")
                    # Escape underscores and special LaTeX chars in filename
                    escaped_name = original_name.replace("_", r"\_").replace("&", r"\&").replace("%", r"\%")
                    
                    latex_template = fr"""
\documentclass[12pt,a4paper]{{article}}
\usepackage[margin=2cm]{{geometry}}
\usepackage{{minted}}
\usepackage{{xcolor}}
\usepackage{{fancyhdr}}
\usepackage{{titlesec}}

% --- Header/footer removed for filename only on first page ---
\pagestyle{{plain}}

% Optional: reduce spacing before code
\titlespacing*{{\section}}{{0pt}}{{0pt}}{{0pt}}

\begin{{document}}

% Filename as first page heading only
\begin{{center}}
    \Large \textbf{{{escaped_name}}}
\end{{center}}
\vspace{{0.5cm}}

% Python code with syntax highlighting, no line numbers, wrapped lines
\begin{{minted}}[
    breaklines,
    breakanywhere,
    fontsize=\small
]{{python}}
{py_content}
\end{{minted}}

\end{{document}}
"""

                    tex_path = os.path.join(temp_dir, "py_file.tex")
                    with open(tex_path, "w", encoding="utf-8") as f:
                        f.write(latex_template)
                    
                    # Compile LaTeX with xelatex and minted
                    try:
                        cmd_xelatex = ["xelatex", "-shell-escape", "-interaction=batchmode", tex_path]
                        subprocess.run(cmd_xelatex, cwd=temp_dir, capture_output=True, text=True, timeout=120, check=True)
                        subprocess.run(cmd_xelatex, cwd=temp_dir, capture_output=True, text=True, timeout=120, check=True)
                        pdf_file = os.path.join(temp_dir, "py_file.pdf")
                        if os.path.exists(pdf_file):
                            os.rename(pdf_file, output_path)
                            conversion_success = True
                        else:
                            conversion_success = False
                            error_message = "LaTeX compilation failed."
                    except subprocess.CalledProcessError as e:
                        conversion_success = False
                        error_message = e.stderr or e.stdout

                # --- IPYNB Conversion ---
                elif file_extension == ".ipynb":
                    latex_output_name = "notebook_output.tex"
                    latex_output_path = os.path.join(temp_dir, latex_output_name)
                    cmd_nbconvert = [
                        "jupyter-nbconvert", "--to", "latex", 
                        input_path, 
                        "--output", latex_output_name, 
                        "--output-dir", temp_dir 
                    ]
                    result_nb = subprocess.run(cmd_nbconvert, capture_output=True, text=True, timeout=120)
                    if result_nb.returncode == 0 and os.path.exists(latex_output_path):
                        # Compile LaTeX to PDF
                        xelatex_cmd = ["xelatex", "--interaction=batchmode", latex_output_name]
                        subprocess.run(xelatex_cmd, cwd=temp_dir, capture_output=True, text=True, timeout=120)
                        subprocess.run(xelatex_cmd, cwd=temp_dir, capture_output=True, text=True, timeout=120)
                        final_pdf_name = Path(latex_output_name).stem + ".pdf"
                        final_pdf_path_temp = os.path.join(temp_dir, final_pdf_name)
                        if os.path.exists(final_pdf_path_temp):
                            os.rename(final_pdf_path_temp, output_path)
                            conversion_success = True
                        else:
                            conversion_success = False
                            error_message = "IPYNB LaTeX compilation failed."
                    else:
                        error_message = "IPYNB to LaTeX conversion failed."

                # --- DOC/DOCX/ODT Conversion ---
                elif file_extension in [".doc", ".docx", ".odt"]:
                    html_path = os.path.join(temp_dir, "temp.html")
                    cmd_pandoc = ["pandoc", input_path, "-o", html_path, "--standalone"]
                    result_html = subprocess.run(cmd_pandoc, capture_output=True, text=True, timeout=60)
                    if result_html.returncode == 0:
                        cmd_pdf = ["wkhtmltopdf", "--quiet", html_path, output_path]
                        result_pdf = subprocess.run(cmd_pdf, capture_output=True, text=True, timeout=60)
                        if result_pdf.returncode == 0 and os.path.exists(output_path):
                            conversion_success = True
                        else:
                            conversion_success = False
                            error_message = "DOCX -> PDF conversion failed."
                    else:
                        conversion_success = False
                        error_message = "Pandoc conversion to HTML failed."

                # --- HTML Conversion ---
                elif file_extension == ".html":
                    cmd_pdf = ["wkhtmltopdf", "--quiet", input_path, output_path]
                    result_pdf = subprocess.run(cmd_pdf, capture_output=True, text=True, timeout=60)
                    if result_pdf.returncode == 0 and os.path.exists(output_path):
                        conversion_success = True
                    else:
                        conversion_success = False
                        error_message = "HTML -> PDF conversion failed."

                # --- Final Result ---
                status_container.empty()
                if conversion_success and os.path.exists(output_path):
                    st.success(f"✅ {file_extension[1:].upper()} converted to PDF successfully!")
                    converted_size = os.path.getsize(output_path) / (1024 * 1024)
                    st.metric("Output Size", f"{converted_size:.2f} MB")
                    with open(output_path, "rb") as f:
                        st.download_button(
                            label="📥 Download PDF",
                            data=f.read(),
                            file_name=f"{original_name}.pdf",
                            mime="application/pdf"
                        )
                else:
                    st.error(f"❌ Conversion failed: {error_message}")

            except Exception as e:
                status_container.empty()
                st.error(f"❌ Critical Error: {e}")

