import os
import sys
import tempfile

# 添加项目根目录到Python路径，以便导入模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.utils.pdf2html_converter import PDF2HTMLConverter


def test_pdf_to_html_conversion():
    """测试PDF到HTML的转换功能"""
    try:
        # 初始化转换器
        converter = PDF2HTMLConverter()
        print("PDF2HTMLConverter初始化成功")
        
        # 获取测试PDF文件路径（用户需要替换为实际的PDF文件路径）
        pdf_path = input("请输入要转换的PDF文件的完整路径: ")
        if not os.path.exists(pdf_path):
            print(f"错误: 文件 {pdf_path} 不存在")
            return
        
        # 创建临时输出目录
        output_dir = tempfile.mkdtemp(prefix="pdf2html_test_")
        output_html_path = os.path.join(output_dir, os.path.splitext(os.path.basename(pdf_path))[0] + ".html")
        
        print(f"开始转换 {pdf_path} 到 {output_html_path}...")
        
        # 执行转换（使用管理员权限）
        result = converter.convert_with_admin_rights(pdf_path, output_html_path)
        
        print(f"转换成功! 输出文件: {result}")
        print(f"请在浏览器中打开此文件查看结果")
        
        # 自动打开结果文件
        try:
            import webbrowser
            webbrowser.open(f"file://{result}")
        except Exception as e:
            print(f"无法自动打开文件: {e}")
        
    except Exception as e:
        print(f"转换过程中发生错误: {e}")


if __name__ == "__main__":
    test_pdf_to_html_conversion()