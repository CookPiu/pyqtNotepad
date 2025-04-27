import os
import shutil
import fitz  # PyMuPDF库
from PyQt6.QtWidgets import QMessageBox


def extract_pdf_content(pdf_path, parent_window=None):
    """
    从PDF文件中提取文本和图片，并转换为HTML格式
    
    Args:
        pdf_path: PDF文件路径
        parent_window: 父窗口，用于显示错误消息
        
    Returns:
        html_content: 转换后的HTML内容
        temp_dir: 临时图片目录路径
    """
    try:
        # 使用PyMuPDF打开PDF文件
        pdf_document = fitz.open(pdf_path)
        html_content = "<html><body>"
        
        # 创建临时目录存储提取的图片
        temp_dir = os.path.join(os.path.dirname(pdf_path), "temp_images")
        os.makedirs(temp_dir, exist_ok=True)
        
        # 提取所有页面的文本和图片
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            
            # 添加页面标题
            if page_num > 0:
                html_content += f"<hr><h2>第 {page_num + 1} 页</h2>"
            
            # 获取页面内容（文本和图片）
            text_dict = page.get_text("dict")
            image_list = page.get_images(full=True)
            
            # 创建一个包含所有元素的列表，以便后续按位置排序
            page_elements = []
            
            # 处理文本块
            for block in text_dict.get("blocks", []):
                if block.get("type") == 0:  # 文本块
                    # 获取文本块的位置信息（y0是块的顶部位置）
                    y_pos = block.get("bbox", [0, 0, 0, 0])[1]
                    
                    # 构建HTML内容
                    block_html = ""
                    for line in block.get("lines", []):
                        line_text = ""
                        for span in line.get("spans", []):
                            text = span.get("text", "")
                            font_size = span.get("size", 12)
                            font_color = span.get("color", "#000000")
                            is_bold = span.get("font", "").lower().find("bold") >= 0
                            is_italic = span.get("font", "").lower().find("italic") >= 0
                            
                            # 应用文本样式
                            style = f"font-size:{font_size}pt;color:{font_color};"
                            if is_bold:
                                style += "font-weight:bold;"
                            if is_italic:
                                style += "font-style:italic;"
                                
                            line_text += f"<span style='{style}'>{text}</span>"
                        block_html += f"<p>{line_text}</p>"
                    
                    # 将文本块添加到元素列表
                    page_elements.append({"type": "text", "y_pos": y_pos, "content": block_html})
            
            # 处理图片
            for img_index, img in enumerate(image_list):
                # 尝试获取图片在页面中的位置
                # 注意：PyMuPDF不直接提供图片位置，这里使用xref作为线索
                xref = img[0]  # 图片的xref
                
                # 提取图片并保存到临时文件
                base_image = pdf_document.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                # 保存图片到临时文件
                image_filename = f"page{page_num+1}_img{img_index+1}.{image_ext}"
                image_path = os.path.join(temp_dir, image_filename)
                with open(image_path, "wb") as img_file:
                    img_file.write(image_bytes)
                
                # 尝试从图片信息中获取位置
                # 由于PyMuPDF不直接提供图片位置，我们使用一个估计值
                # 这里使用img_index作为排序依据，实际应用中可能需要更复杂的逻辑
                y_pos = img_index * 100  # 这是一个估计值
                
                # 在页面中查找可能包含此图片的块
                for block in text_dict.get("blocks", []):
                    if block.get("type") == 1:  # 图片块
                        # 如果找到图片块，使用其位置信息
                        y_pos = block.get("bbox", [0, 0, 0, 0])[1]
                        break
                
                # 将图片添加到元素列表
                img_html = f"<div><img src='{image_path}' style='max-width:100%;'></div>"
                page_elements.append({"type": "image", "y_pos": y_pos, "content": img_html})
            
            # 按y_pos（垂直位置）对元素进行排序
            page_elements.sort(key=lambda x: x["y_pos"])
            
            # 按排序后的顺序将元素添加到HTML中
            for element in page_elements:
                html_content += element["content"]
        
        html_content += "</body></html>"
        pdf_document.close()
        
        return html_content, temp_dir
    except Exception as e:
        if parent_window:
            QMessageBox.critical(parent_window, "错误", f"无法处理PDF文件: {str(e)}")
        return None, None


def cleanup_temp_images(temp_dir):
    """
    清理临时图片目录
    
    Args:
        temp_dir: 临时图片目录路径
    """
    try:
        if os.path.exists(temp_dir) and os.path.isdir(temp_dir):
            shutil.rmtree(temp_dir)
    except Exception as e:
        print(f"清理临时文件失败: {str(e)}")