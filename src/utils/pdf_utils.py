import os
import subprocess
import tempfile
import shutil
import pathlib
import sys
import base64
import mimetypes
import re
from bs4 import BeautifulSoup
from .pdf2html_converter import PDF2HTMLConverter
# import fitz # No longer needed for HTML conversion, but PdfViewerView still uses it for image preview

def get_application_path():
    if getattr(sys, 'frozen', False):
        # If the application is run as a bundle/frozen executable (e.g., by PyInstaller)
        application_path = os.path.dirname(sys.executable)
    else:
        # Assuming pdf_utils.py is in src/utils/
        # So, ../../ gives the project root (F:/Project/pyqtNotepad)
        application_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    return application_path

APPLICATION_ROOT = get_application_path()
# 不再使用mupdf，改为使用pdf2htmlEX
# PDF2HTMLConverter类会在初始化时检查工具是否存在

# Helper function to embed resources found in CSS url()
def _embed_css_resource_url(match_obj, base_dir: pathlib.Path):
    url_content = match_obj.group(1).strip().strip("'\"")

    if url_content.startswith(('data:', 'http:', 'https:')):
        return match_obj.group(0) 

    try:
        # Resolve path, handling potential relative paths like "../fonts/" if any
        resource_path = (base_dir / url_content).resolve()
        
        # Security check: ensure resolved path is still within base_dir
        if not str(resource_path).startswith(str(base_dir.resolve())):
            print(f"警告: CSS引用的资源路径 '{url_content}' 解析到基础目录之外，跳过嵌入。")
            return match_obj.group(0)

        if resource_path.exists() and resource_path.is_file():
            data = base64.b64encode(resource_path.read_bytes()).decode()
            mime_type, _ = mimetypes.guess_type(resource_path)
            if not mime_type:
                ext = resource_path.suffix.lower()
                if ext == '.ttf': mime_type = 'font/ttf'
                elif ext == '.otf': mime_type = 'font/otf'
                elif ext == '.woff': mime_type = 'font/woff'
                elif ext == '.woff2': mime_type = 'font/woff2'
                elif ext == ".png": mime_type = "image/png"
                elif ext in [".jpg", ".jpeg"]: mime_type = "image/jpeg"
                elif ext == ".gif": mime_type = "image/gif"
                elif ext == ".svg": mime_type = "image/svg+xml"
                elif ext == ".webp": mime_type = "image/webp"
                else: mime_type = 'application/octet-stream'
            return f"url(data:{mime_type};base64,{data})"
        else:
            # print(f"警告: CSS引用的资源未找到: {resource_path} (原始url: {url_content})")
            return match_obj.group(0) 
    except Exception as e:
        print(f"嵌入CSS资源 {url_content} 时出错: {e}")
        return match_obj.group(0)

def _inline_resources(html_text: str, base_dir_str: str) -> str:
    base_dir = pathlib.Path(base_dir_str)
    soup = BeautifulSoup(html_text, "lxml")

    for img_tag in soup.find_all("img", src=True):
        src_val = img_tag["src"]
        if not src_val or src_val.startswith(('data:', 'http:', 'https:')):
            continue

        try:
            img_path = (base_dir / src_val).resolve()
            if not str(img_path).startswith(str(base_dir.resolve())):
                print(f"警告: 图片路径 '{src_val}' 解析到基础目录之外，跳过嵌入。")
                continue
                
            if img_path.exists() and img_path.is_file():
                mime_type, _ = mimetypes.guess_type(img_path)
                if not mime_type:
                    ext = img_path.suffix.lower()
                    if ext == ".png": mime_type = "image/png"
                    elif ext in [".jpg", ".jpeg"]: mime_type = "image/jpeg"
                    elif ext == ".gif": mime_type = "image/gif"
                    elif ext == ".svg": mime_type = "image/svg+xml"
                    elif ext == ".webp": mime_type = "image/webp"
                    else: mime_type = "application/octet-stream"
                
                img_data = base64.b64encode(img_path.read_bytes()).decode()
                img_tag["src"] = f"data:{mime_type};base64,{img_data}"
            else:
                # print(f"警告: 图片文件未找到，无法嵌入: {img_path} (原始src: {src_val})")
                pass # Silently skip if not found, or could log
        except Exception as e:
            print(f"嵌入图片 {src_val} 时出错: {e}")

    for tag_with_style in soup.find_all(style=True):
        if tag_with_style.string: # Check if style attribute has content (it always does if attr exists)
             tag_with_style["style"] = re.sub(
                r'url\(([^)]+)\)',
                lambda m: _embed_css_resource_url(m, base_dir),
                tag_with_style["style"]
            )
            
    for style_tag in soup.find_all("style"):
        if style_tag.string:
            style_tag.string = re.sub(
                r'url\(([^)]+)\)',
                lambda m: _embed_css_resource_url(m, base_dir),
                style_tag.string
            )
            
    return str(soup)

def extract_pdf_content(pdf_path: str) -> str:
    """将PDF文件转换为HTML内容
    
    此函数保持与原有接口兼容，但内部实现已从mupdf切换到pdf2htmlEX
    
    Args:
        pdf_path: PDF文件路径
        
    Returns:
        转换后的HTML内容字符串
        
    Raises:
        FileNotFoundError: 当PDF文件或pdf2htmlEX工具不存在时
        RuntimeError: 当转换过程中发生错误时
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF 文件未找到: {pdf_path}")

    try:
        # 使用PDF2HTMLConverter类进行转换
        converter = PDF2HTMLConverter()
        html_content = converter.convert_pdf_to_html(pdf_path)
        
        # 保持与原有功能一致，将pt单位转换为px
        html_content = re.sub(r'([\d.]+)pt', lambda m: f"{float(m.group(1)) * 96/72:.2f}px", html_content)
        
        return html_content

    except Exception as e:
        # 捕获并重新抛出异常，保持与原有错误处理一致
        raise RuntimeError(f"处理 PDF 时发生意外错误: {e}") from e
