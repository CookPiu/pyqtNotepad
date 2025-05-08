import os
import fitz  # PyMuPDF
# from PyQt6.QtWidgets import QMessageBox # No longer needed here, errors will be raised

def extract_pdf_content(pdf_path: str) -> str: # parent_window removed
    """
    Converts a PDF file to HTML using PyMuPDF (fitz).
    
    Args:
        pdf_path: Path to the PDF file.
        
    Returns:
        HTML content as a string.
        
    Raises:
        FileNotFoundError: If pdf_path is invalid.
        RuntimeError: If PyMuPDF fails to process the PDF.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF 文件未找到: {pdf_path}")

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        # err_msg = f"使用 PyMuPDF 打开 PDF 文件失败: {e}" # Original message
        # if parent_window: # Removed
            # QMessageBox.critical(parent_window, "PDF 处理错误", err_msg) # Removed
        raise RuntimeError(f"使用 PyMuPDF 打开 PDF 文件失败: {e}") from e

    html_parts = []
    page_errors = [] # Collect page-specific errors
    try:
        for i, page in enumerate(doc):
            try:
                page_html = page.get_text("html") 
                html_parts.append(page_html)
            except Exception as e_page:
                page_err_msg = f"处理 PDF 第 {i+1} 页时出错: {e_page}"
                print(page_err_msg) 
                html_parts.append(f"<!-- Error processing page {i+1}: {page_err_msg} -->")
                page_errors.append(page_err_msg)
                # if parent_window: # Removed
                     # QMessageBox.warning(parent_window, "页面处理警告", page_err_msg) # Removed

        if page_errors: # If there were page errors, append them to the main error message or handle as needed
            # For now, we just print them and include placeholders in HTML.
            # The main RuntimeError below will be more generic if this block isn't hit.
            # Consider if a partial success (some pages converted) should still return HTML or raise specific error.
            # For now, it will proceed to return the HTML with error placeholders.
            pass

        # Basic HTML structure
        # The HTML from get_text("html") is a fragment, often starting with <div id="page0">...
        # We need to wrap it in a full HTML document.
        # PyMuPDF's output already includes CSS for positioning and images as base64.
        
        full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <title>{os.path.basename(pdf_path)}</title>
    <style>
        body {{ margin: 0; background-color: #f0f0f0; }} /* Basic body style */
        .pdf-page-container {{ 
            margin: 20px auto; /* Center pages with some margin */
            overflow: hidden; /* Important for page dimensions */
            /* background-color: white; */ /* Set by PyMuPDF's output divs usually */
            /* box-shadow: 0 0 10px rgba(0,0,0,0.5); */ /* Optional shadow for pages */
        }}
        /* PyMuPDF pages are often in divs like <div id="page0" style="width:..."> */
        /* No additional global CSS should be strictly necessary for layout if PyMuPDF handles it well */
    </style>
</head>
<body>
"""
        # Concatenate all page HTML parts
        # Each part from page.get_text("html") is usually a self-contained div for that page.
        # We can wrap each page's HTML in a container for better structure if needed,
        # but PyMuPDF's output might already be structured per page.
        # For simplicity, just join them. If styling per page is needed, wrap here.
        for part in html_parts:
            # Example of wrapping each page for potential styling/separation:
            # full_html += f'<div class="pdf-page-container">{part}</div>\n'
            # However, PyMuPDF's output usually has its own page div e.g. <div id="page0"...>
            # So direct concatenation should be fine.
            full_html += part + "\n"

        full_html += """
</body>
</html>
"""
        return full_html

    except Exception as e:
        # err_msg = f"使用 PyMuPDF 转换 PDF 为 HTML 时出错: {e}" # Original message
        # if parent_window: # Removed
            # QMessageBox.critical(parent_window, "PDF 转换失败", err_msg) # Removed
        raise RuntimeError(f"使用 PyMuPDF 转换 PDF 为 HTML 时出错: {e}") from e
    finally:
        if 'doc' in locals() and doc:
            try:
                doc.close()
            except Exception as e_close:
                print(f"关闭 PDF 文档时出错: {e_close}")


# def cleanup_temp_images(temp_dir):
#     # This function was for the old PyMuPDF image extraction or pdf2htmlEX.
#     # It's no longer needed as PyMuPDF's get_text("html") embeds images
#     # and we are not using pdf2htmlEX which created external files.
#     """
#     清理临时图片目录 (不再使用)
#     """
#     # try:
#     #     if os.path.exists(temp_dir) and os.path.isdir(temp_dir):
#     #         shutil.rmtree(temp_dir)
#     # except Exception as e:
#     #     print(f"清理临时文件失败: {str(e)}")
#     pass
