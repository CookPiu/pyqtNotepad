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
MUTOOL_DIR_NAME = "mupdf-1.25.2-windows" 
MUTOOL_EXE_NAME = "mutool.exe"

mutool_directory_path = os.path.join(APPLICATION_ROOT, MUTOOL_DIR_NAME)
MUTOOL_PATH = os.path.join(mutool_directory_path, MUTOOL_EXE_NAME)

if not os.path.exists(MUTOOL_PATH):
    mutool_bin_path_attempt = os.path.join(mutool_directory_path, "bin", MUTOOL_EXE_NAME)
    if os.path.exists(mutool_bin_path_attempt):
        MUTOOL_PATH = mutool_bin_path_attempt
    else:
        pass # Error will be raised in extract_pdf_content if still not found

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
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF 文件未找到: {pdf_path}")

    if not os.path.exists(MUTOOL_PATH):
        primary_expected_path = os.path.join(APPLICATION_ROOT, MUTOOL_DIR_NAME, MUTOOL_EXE_NAME)
        bin_expected_path = os.path.join(APPLICATION_ROOT, MUTOOL_DIR_NAME, "bin", MUTOOL_EXE_NAME)
        error_msg = (
            f"mutool.exe 未找到。\n"
            f"尝试路径 1: {primary_expected_path}\n"
            f"尝试路径 2: {bin_expected_path}\n"
            f"请确保 MuPDF ('{MUTOOL_DIR_NAME}') 已放置在项目根目录下，"
            f"并且 '{MUTOOL_EXE_NAME}' 在该目录中 (或其 'bin' 子目录中)。"
        )
        raise FileNotFoundError(error_msg)

    tmp_output_dir = tempfile.mkdtemp(prefix="mutool_")
    try:
        base_name = pathlib.Path(pdf_path).stem
        output_html_file = pathlib.Path(tmp_output_dir, base_name + ".html")

        cmd_final = [
            MUTOOL_PATH,
            "convert",
            "-o", str(output_html_file),
            "-F", "html",
            "-O", tmp_output_dir, 
            pdf_path
        ]
        
        process = subprocess.run(cmd_final, check=False, capture_output=True, text=False)

        if process.returncode != 0:
            stderr_output = process.stderr.decode('utf-8', errors='replace')[:1000]
            raise RuntimeError(f"mutool 转换失败 (代码: {process.returncode}):\n{stderr_output}")

        if not output_html_file.exists():
            raise RuntimeError(f"mutool 执行成功，但未找到预期的输出文件: {output_html_file}")

        html_content = output_html_file.read_text(encoding="utf-8")
        
        html_content = _inline_resources(html_content, tmp_output_dir)
        
        html_content = re.sub(r'([\d.]+)pt', lambda m: f"{float(m.group(1)) * 96/72:.2f}px", html_content)

        return html_content

    except Exception as e: # Catch any broad error during processing
        # Ensure specific errors from mutool or file ops are caught above if possible
        raise RuntimeError(f"处理 PDF 时发生意外错误: {e}") from e
    finally:
        if 'tmp_output_dir' in locals() and os.path.exists(tmp_output_dir):
            shutil.rmtree(tmp_output_dir, ignore_errors=True)
