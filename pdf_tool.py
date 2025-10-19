import streamlit as st
import subprocess
import os
import tempfile
from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter
import fitz  # PyMuPDF

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
    ["Compress", "Extract Text", "Extract Pages", "Merge", "Split", "Rotate"],
    index=0
)

# Compress
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
        help="1 = Maximum compression (smaller file), 5 = Minimum compression (best quality)"
    )
    
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
                import time
                
                # Loader
                status_container = st.empty()
                status_container.markdown("""
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <img src="https://cdn.pixabay.com/animation/2023/08/11/21/18/21-18-05-265_256.gif" width="30">
                        <h3 style="margin: 0;">Compressing PDF... Please wait</h3>
                    </div>
                """, unsafe_allow_html=True)
                
                pdf_setting = "/ebook" if compression_level >= 4 else "/screen"
                
                cmd = [
                    "gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
                    f"-dPDFSETTINGS={pdf_setting}", "-dNOPAUSE", "-dQUIET", "-dBATCH",
                    "-dDetectDuplicateImages", "-dCompressFonts=true",
                    f"-r{dpi_value}x{dpi_value}",
                    f"-sOutputFile={output_path}", input_path
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                status_container.empty()
                
                if result.returncode == 0 and os.path.exists(output_path):
                    original_size = os.path.getsize(input_path) / (1024 * 1024)
                    compressed_size = os.path.getsize(output_path) / (1024 * 1024)
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
                    st.error(f"❌ Compression failed: {result.stderr}")
            except FileNotFoundError:
                st.error("❌ Ghostscript not found. Install with: sudo apt install ghostscript")
            except Exception as e:
                st.error(f"❌ Error: {e}")

# Extract Text
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


# Extract Pages
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

# Merge PDFs
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

# Split PDF
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


# Rotate
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

