# check_qax.py
import sys
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")

try:
    from PyQt6.QtAxContainer import QAxWidget
    print("Successfully imported QAxWidget from PyQt6.QtAxContainer")
    print(f"QAxWidget object: {QAxWidget}")
except ImportError as e:
    print(f"ERROR: Failed to import QAxWidget from PyQt6.QtAxContainer: {e}")
except Exception as e_other:
    print(f"ERROR: An unexpected error occurred during QAxWidget import: {e_other}")

print("-" * 20)

try:
    import PyQt6
    if hasattr(PyQt6, 'QtCore') and hasattr(PyQt6.QtCore, 'PYQT_VERSION_STR'):
        print(f"PyQt6 version: {PyQt6.QtCore.PYQT_VERSION_STR}")
    else:
        print("Could not determine PyQt6 version string.")
    print(f"PyQt6 location: {PyQt6.__file__}")
    # Check for QtAxContainer module path if possible (might not be straightforward)
    if hasattr(PyQt6, 'QtAxContainer'):
        print(f"PyQt6.QtAxContainer found as an attribute: {PyQt6.QtAxContainer}")
    else:
        print("PyQt6.QtAxContainer not found as a direct attribute of PyQt6 module.")

except ImportError as e_pyqt:
    print(f"ERROR: Failed to import PyQt6 base module: {e_pyqt}")
except Exception as e_pyqt_other:
    print(f"ERROR: An unexpected error occurred during PyQt6 base import: {e_pyqt_other}")
    
print("-" * 20)

try:
    import win32com
    print("Successfully imported win32com (from pywin32)")
    if hasattr(win32com, '__file__'):
        print(f"win32com location: {win32com.__file__}")
    else:
        print("win32com location attribute not found.")
except ImportError as e_win:
    print(f"ERROR: Failed to import win32com: {e_win}")
except Exception as e_win_other:
    print(f"ERROR: An unexpected error occurred during win32com import: {e_win_other}")

print("\nDiagnostic script finished.")
