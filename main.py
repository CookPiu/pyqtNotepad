import sys
import os

# Add the 'src' directory to the Python path to allow absolute imports like 'from src.ui...'
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
# Now this import should work if src is in sys.path and src/ui/main has __init__.py
from src.ui.main.main_window import MainWindow # Updated import path

# Corrected indentation for the entire block below
if __name__ == "__main__":
    # Set Qt attribute to handle high DPI scaling if needed (optional but recommended)
    # QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling) # Removed due to AttributeError
    # QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)   # Removed due to AttributeError

    app = QApplication(sys.argv)

    # Ensure the application style is set early, if applicable
    # For example, if using Fusion style: app.setStyle("Fusion")

    print("▶ Creating MainWindow instance...")
    try:
        window = MainWindow()
        print("▶ MainWindow instance created.")
        print("▶ Calling window.show()...")
        window.show()
        print("▶ window.show() called.")
        print("▶ Starting app.exec()...")
        exit_code = app.exec()
        print(f"▶ app.exec() finished with exit code: {exit_code}")
        sys.exit(exit_code)
    except Exception as e:
        print(f"▶▶▶ ERROR during MainWindow initialization or execution: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) # Exit with error code
