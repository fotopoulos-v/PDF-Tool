
# import sys
# import fitz  # PyMuPDF
# from PyPDF2 import PdfReader
# from reportlab.pdfgen import canvas
# from reportlab.lib.pagesizes import letter
# from PIL import Image
# import io

# def compress_pdf_images(input_pdf, output_pdf, image_scale=0.5, image_quality=70):
#     """
#     Compress images in a PDF without losing text.
#     image_scale: scale factor for image dimensions (0.5 = 50%)
#     image_quality: JPEG quality for recompression (0-100)
#     """
#     doc = fitz.open(input_pdf)

#     for page in doc:
#         image_list = page.get_images(full=True)
#         for img in image_list:
#             xref = img[0]
#             base_image = doc.extract_image(xref)
#             img_bytes = base_image["image"]
#             img_ext = base_image["ext"]

#             # Open image in PIL
#             image = Image.open(io.BytesIO(img_bytes))

#             # Resize image
#             if image_scale < 1.0:
#                 new_width = int(image.width * image_scale)
#                 new_height = int(image.height * image_scale)
#                 image = image.resize((new_width, new_height), Image.LANCZOS)

#             # Convert to RGB for JPEG if needed
#             if image.mode in ("RGBA", "LA") or (image.mode == "P" and img_ext.lower() == "png"):
#                 image = image.convert("RGB")

#             # Save to bytes with compression
#             img_buffer = io.BytesIO()
#             image.save(img_buffer, format="JPEG", quality=image_quality)
#             img_buffer.seek(0)

#             # Replace image in PDF
#             doc.update_image(xref, img_buffer.read())

#     doc.save(output_pdf)
#     print(f"✅ Compressed PDF saved to: {output_pdf}")


# def extract_text_to_pdf(input_pdf, output_pdf):
#     """
#     Extract text from PDF and save it to a new text-only PDF.
#     """
#     reader = PdfReader(input_pdf)
#     text = ""
#     for page in reader.pages:
#         text += page.extract_text() or ""
#         text += "\n" + "-" * 80 + "\n"

#     c = canvas.Canvas(output_pdf, pagesize=letter)
#     width, height = letter
#     y = height - 50

#     for line in text.split("\n"):
#         if y < 50:  # New page
#             c.showPage()
#             y = height - 50
#         c.drawString(40, y, line[:1000])
#         y -= 12

#     c.save()
#     print(f"✅ Text-only PDF saved to: {output_pdf}")


# if __name__ == "__main__":
#     if len(sys.argv) < 4:
#         print("Usage:")
#         print("  python pdf_optimizer.py compress input.pdf output.pdf [image_scale] [image_quality]")
#         print("  python pdf_optimizer.py text input.pdf output.pdf")
#         sys.exit(1)

#     mode = sys.argv[1]
#     input_pdf = sys.argv[2]
#     output_pdf = sys.argv[3]

#     if mode == "compress":
#         image_scale = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5
#         image_quality = int(sys.argv[5]) if len(sys.argv) > 5 else 70
#         compress_pdf_images(input_pdf, output_pdf, image_scale, image_quality)
#     elif mode == "text":
#         extract_text_to_pdf(input_pdf, output_pdf)
#     else:
#         print("Unknown mode. Use 'compress' or 'text'.")

import sys
import os
import subprocess
import fitz  # PyMuPDF
from PyPDF2 import PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PIL import Image
import io


def compress_pdf_images(input_pdf, output_pdf, image_scale=0.5, image_quality=70):
    """
    Compress images in a PDF by extracting, resizing, and re-embedding them.
    image_scale: scale factor for image dimensions (0.5 = 50%)
    image_quality: JPEG quality for recompression (0-100)
    """
    try:
        if not os.path.exists(input_pdf):
            print(f"❌ Error: Input file '{input_pdf}' not found.")
            return
        
        # Create temp directory for extracted images
        temp_dir = "/tmp/pdf_compress_temp"
        os.makedirs(temp_dir, exist_ok=True)
        
        doc = fitz.open(input_pdf)
        images_compressed = 0
        image_xrefs = {}
        
        # Extract all images and compress them
        for page_num, page in enumerate(doc):
            image_list = page.get_images(full=True)
            for img_idx, img in enumerate(image_list):
                xref = img[0]
                if xref in image_xrefs:
                    continue
                
                try:
                    base_image = doc.extract_image(xref)
                    if not base_image:
                        continue
                    
                    img_bytes = base_image["image"]
                    img_ext = base_image["ext"]
                    
                    # Open image in PIL
                    pil_image = Image.open(io.BytesIO(img_bytes))
                    original_size = len(img_bytes)
                    
                    # Resize image
                    if image_scale < 1.0:
                        new_width = int(pil_image.width * image_scale)
                        new_height = int(pil_image.height * image_scale)
                        pil_image = pil_image.resize((new_width, new_height), Image.LANCZOS)
                    
                    # Convert to RGB for JPEG if needed
                    if pil_image.mode in ("RGBA", "LA") or (pil_image.mode == "P"):
                        pil_image = pil_image.convert("RGB")
                    
                    # Save to bytes with compression
                    img_buffer = io.BytesIO()
                    pil_image.save(img_buffer, format="JPEG", quality=image_quality, optimize=True)
                    img_buffer.seek(0)
                    compressed_data = img_buffer.read()
                    compressed_size = len(compressed_data)
                    
                    # Store info for replacement
                    image_xrefs[xref] = {
                        'data': compressed_data,
                        'width': pil_image.width,
                        'height': pil_image.height,
                        'original_size': original_size,
                        'compressed_size': compressed_size
                    }
                    images_compressed += 1
                    
                except Exception as img_err:
                    pass
        
        # Replace images in the document
        for xref, img_info in image_xrefs.items():
            try:
                # Access the image object and replace its stream
                img_obj = doc.xref_object(xref)
                if img_obj:
                    doc._update_object(xref, img_info['data'], raw=True)
            except:
                pass
        
        # Save with maximum compression
        doc.save(output_pdf, garbage=4, deflate=True)
        doc.close()
        
        print(f"✅ Compressed PDF saved to: {output_pdf}")
        print(f"   Images processed: {images_compressed}")
        
        # Show file size reduction
        if os.path.exists(input_pdf) and os.path.exists(output_pdf):
            original_size = os.path.getsize(input_pdf) / (1024 * 1024)
            compressed_size = os.path.getsize(output_pdf) / (1024 * 1024)
            reduction = ((original_size - compressed_size) / original_size) * 100
            print(f"   Original: {original_size:.2f} MB → Compressed: {compressed_size:.2f} MB")
            print(f"   Reduction: {reduction:.1f}%")
    
    except Exception as e:
        print(f"❌ Error during compression: {e}")


def extract_text_to_pdf(input_pdf, output_pdf):
    """
    Extract text from PDF and save it to a new text-only PDF.
    """
    try:
        if not os.path.exists(input_pdf):
            print(f"❌ Error: Input file '{input_pdf}' not found.")
            return
        
        reader = PdfReader(input_pdf)
        text = ""
        
        for page_num, page in enumerate(reader.pages):
            extracted = page.extract_text()
            if extracted:
                text += extracted
            text += "\n" + "-" * 80 + "\n"
        
        c = canvas.Canvas(output_pdf, pagesize=letter)
        width, height = letter
        y = height - 50
        
        for line in text.split("\n"):
            if y < 50:  # New page
                c.showPage()
                y = height - 50
            
            # Safely handle line content
            safe_line = line[:1000] if line else ""
            if safe_line.strip():  # Only draw non-empty lines
                c.drawString(40, y, safe_line)
            y -= 12
        
        c.save()
        print(f"✅ Text-only PDF saved to: {output_pdf}")
    
    except Exception as e:
        print(f"❌ Error during text extraction: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage:")
        print("  python3 pdf_optimizer.py compress input.pdf output.pdf [image_scale] [image_quality]")
        print("  python3 pdf_optimizer.py text input.pdf output.pdf")
        print("\nExamples:")
        print("  python3 pdf_optimizer.py compress document.pdf compressed.pdf 0.5 70")
        print("  python3 pdf_optimizer.py text document.pdf extracted.pdf")
        sys.exit(1)
    
    mode = sys.argv[1]
    input_pdf = sys.argv[2]
    output_pdf = sys.argv[3]
    
    if mode == "compress":
        image_scale = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5
        image_quality = int(sys.argv[5]) if len(sys.argv) > 5 else 70
        compress_pdf_images(input_pdf, output_pdf, image_scale, image_quality)
    elif mode == "text":
        extract_text_to_pdf(input_pdf, output_pdf)
    else:
        print("❌ Unknown mode. Use 'compress' or 'text'.")
        sys.exit(1)