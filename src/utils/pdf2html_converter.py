import os
import subprocess
import tempfile
import shutil
import sys
import pathlib


def get_application_path():
    """获取应用程序根目录路径"""
    if getattr(sys, 'frozen', False):
        # 如果应用程序是作为打包/冻结的可执行文件运行（例如，由PyInstaller打包）
        application_path = os.path.dirname(sys.executable)
    else:
        # 假设当前文件在src/utils/目录下
        application_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    return application_path


class PDF2HTMLConverter:
    """PDF转HTML转换器，使用pdf2htmlEX工具"""
    
    def __init__(self):
        self.application_root = get_application_path()
        self.pdf2html_dir = os.path.join(self.application_root, "pdf2htmlEX-win32-0.13.6")
        self.pdf2html_exe = os.path.join(self.pdf2html_dir, "pdf2htmlEX.exe")
        
        # 验证pdf2htmlEX工具是否存在
        if not os.path.exists(self.pdf2html_exe):
            raise FileNotFoundError(f"pdf2htmlEX.exe 未找到。请确保 'pdf2htmlEX-win32-0.13.6' 目录已放置在项目根目录下，"  
                                   f"并且 'pdf2htmlEX.exe' 在该目录中。")
    
    def convert_pdf_to_html(self, pdf_path, output_html_path=None, options=None):
        """将PDF文件转换为HTML
        
        Args:
            pdf_path: PDF文件路径
            output_html_path: 输出HTML文件路径，如果为None则使用临时文件
            options: 额外的pdf2htmlEX命令行选项
            
        Returns:
            如果output_html_path为None，返回HTML内容字符串
            否则返回输出文件路径
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF文件未找到: {pdf_path}")
        
        # 创建临时目录用于处理文件
        temp_dir = tempfile.mkdtemp(prefix="pdf2html_")
        temp_pdf_path = None
        temp_html_path = None
        use_temp_output = output_html_path is None
        
        try:
            # 复制PDF文件到工具目录
            pdf_filename = os.path.basename(pdf_path)
            temp_pdf_path = os.path.join(temp_dir, pdf_filename)
            shutil.copy2(pdf_path, temp_pdf_path)
            
            # 设置输出HTML文件名
            if use_temp_output:
                html_filename = os.path.splitext(pdf_filename)[0] + ".html"
                temp_html_path = os.path.join(temp_dir, html_filename)
            else:
                html_filename = os.path.basename(output_html_path)
                temp_html_path = os.path.join(temp_dir, html_filename)
            
            # 构建命令
            cmd = [
                self.pdf2html_exe,
                pdf_filename,  # 使用文件名而不是完整路径，因为我们已经在工作目录中
                html_filename
            ]
            
            # 添加额外选项
            if options:
                cmd.extend(options)
            
            # 执行命令
            process = subprocess.run(
                cmd,
                cwd=temp_dir,  # 在临时目录中执行命令
                check=False,
                capture_output=True,
                text=True,
                shell=True,  # 使用shell执行以支持管理员权限
                creationflags=subprocess.CREATE_NO_WINDOW  # 不显示命令窗口
            )
            
            if process.returncode != 0:
                stderr_output = process.stderr[:1000] if process.stderr else "未知错误"
                raise RuntimeError(f"pdf2htmlEX转换失败 (代码: {process.returncode}):\n{stderr_output}")
            
            if not os.path.exists(temp_html_path):
                raise RuntimeError(f"pdf2htmlEX执行成功，但未找到预期的输出文件: {temp_html_path}")
            
            # 处理输出
            if use_temp_output:
                # 读取HTML内容并返回
                with open(temp_html_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                return html_content
            else:
                # 将生成的HTML文件复制到指定位置
                os.makedirs(os.path.dirname(output_html_path), exist_ok=True)
                shutil.copy2(temp_html_path, output_html_path)
                return output_html_path
            
        except Exception as e:
            raise RuntimeError(f"处理PDF时发生意外错误: {e}") from e
        
        finally:
            # 清理临时文件
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    def convert_with_admin_rights(self, pdf_path, output_html_path=None, options=None):
        """使用管理员权限执行PDF到HTML的转换
        
        此方法使用runas命令以管理员权限执行转换。
        注意：这将弹出UAC提示窗口，用户需要确认。
        
        Args:
            pdf_path: PDF文件路径
            output_html_path: 输出HTML文件路径，如果为None则使用临时文件
            options: 额外的pdf2htmlEX命令行选项
            
        Returns:
            如果output_html_path为None，返回HTML内容字符串
            否则返回输出文件路径
        """
        # 创建临时目录用于处理文件
        temp_dir = tempfile.mkdtemp(prefix="pdf2html_admin_")
        temp_pdf_path = None
        temp_html_path = None
        use_temp_output = output_html_path is None
        
        try:
            # 复制PDF文件到临时目录
            pdf_filename = os.path.basename(pdf_path)
            temp_pdf_path = os.path.join(temp_dir, pdf_filename)
            shutil.copy2(pdf_path, temp_pdf_path)
            
            # 设置输出HTML文件名
            if use_temp_output:
                html_filename = os.path.splitext(pdf_filename)[0] + ".html"
            else:
                html_filename = os.path.basename(output_html_path)
            
            temp_html_path = os.path.join(temp_dir, html_filename)
            
            # 构建命令字符串
            pdf2html_cmd = f'"{self.pdf2html_exe}" "{pdf_filename}" "{html_filename}"'
            
            # 添加额外选项
            if options:
                for option in options:
                    pdf2html_cmd += f" {option}"
            
            # 使用runas命令以管理员权限执行
            # 注意：这将弹出UAC提示窗口
            admin_cmd = f'powershell.exe -Command "Start-Process cmd -ArgumentList \"/c cd /d \\"{temp_dir}\\\" && {pdf2html_cmd}\" -Verb RunAs -Wait"'
            
            process = subprocess.run(
                admin_cmd,
                shell=True,
                check=False,
                capture_output=True,
                text=True
            )
            
            # 检查输出文件是否存在
            if not os.path.exists(temp_html_path):
                stderr_output = process.stderr if process.stderr else "未知错误"
                raise RuntimeError(f"pdf2htmlEX转换失败:\n{stderr_output}")
            
            # 处理输出
            if use_temp_output:
                # 读取HTML内容并返回
                with open(temp_html_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                return html_content
            else:
                # 将生成的HTML文件复制到指定位置
                os.makedirs(os.path.dirname(output_html_path), exist_ok=True)
                shutil.copy2(temp_html_path, output_html_path)
                return output_html_path
            
        except Exception as e:
            raise RuntimeError(f"处理PDF时发生意外错误: {e}") from e
        
        finally:
            # 清理临时文件
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)