import os
import tempfile
import shutil
from pathlib import Path

from ..utils.pdf2html_converter import PDF2HTMLConverter


class PDFConversionService:
    """PDF转换服务，提供PDF到HTML的转换功能"""
    
    def __init__(self):
        """初始化PDF转换服务"""
        self.converter = PDF2HTMLConverter()
    
    def convert_pdf_to_html(self, pdf_path, output_html_path=None, use_admin=True, options=None):
        """将PDF文件转换为HTML
        
        Args:
            pdf_path: PDF文件路径
            output_html_path: 输出HTML文件路径，如果为None则返回HTML内容
            use_admin: 是否使用管理员权限执行转换
            options: 额外的pdf2htmlEX命令行选项
            
        Returns:
            如果output_html_path为None，返回HTML内容字符串
            否则返回输出文件路径
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF文件未找到: {pdf_path}")
        
        try:
            # 根据是否需要管理员权限选择不同的转换方法
            if use_admin:
                return self.converter.convert_with_admin_rights(pdf_path, output_html_path, options)
            else:
                return self.converter.convert_pdf_to_html(pdf_path, output_html_path, options)
        except Exception as e:
            raise RuntimeError(f"PDF转换失败: {e}") from e
    
    def convert_and_get_html_content(self, pdf_path, use_admin=True, options=None):
        """转换PDF并返回HTML内容
        
        Args:
            pdf_path: PDF文件路径
            use_admin: 是否使用管理员权限执行转换
            options: 额外的pdf2htmlEX命令行选项
            
        Returns:
            HTML内容字符串
        """
        return self.convert_pdf_to_html(pdf_path, None, use_admin, options)
    
    def convert_to_temp_file(self, pdf_path, use_admin=True, options=None):
        """转换PDF到临时文件并返回文件路径
        
        Args:
            pdf_path: PDF文件路径
            use_admin: 是否使用管理员权限执行转换
            options: 额外的pdf2htmlEX命令行选项
            
        Returns:
            临时HTML文件路径
        """
        temp_dir = tempfile.mkdtemp(prefix="pdf2html_service_")
        html_filename = Path(pdf_path).stem + ".html"
        temp_html_path = os.path.join(temp_dir, html_filename)
        
        try:
            return self.convert_pdf_to_html(pdf_path, temp_html_path, use_admin, options)
        except Exception as e:
            # 清理临时目录
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            raise e