import sys
# 从 core 模块导入主应用程序运行器
# 这个导入将在 core/app.py 正确设置后生效
from src.core.app import run_application

if __name__ == '__main__':
    # 运行应用程序
    run_application()
