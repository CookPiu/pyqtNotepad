# minimal_preview_test.py
import sys, os
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import QUrl
# Assuming src is in the PYTHONPATH or script is run from project root
from src.ui.views.editable_html_preview_widget import EditableHtmlPreviewWidget
from PyQt6.QtWebEngineCore import QWebEngineSettings

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    main_win = QMainWindow()
    preview = EditableHtmlPreviewWidget(main_win)
    # DeveloperExtrasEnabled might not be available or needed if console logs print to terminal
    # preview.page().settings().setAttribute(QWebEngineSettings.WebAttribute.DeveloperExtrasEnabled, True) 
    main_win.setCentralWidget(preview)
    main_win.setWindowTitle("Minimal Preview Test")
    main_win.setGeometry(100, 100, 800, 600)

    # Create a test HTML and CSS content
    test_html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Test</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <h1>Hello World</h1>
    <p>This is a test.</p>
    <img src="test_image.png" alt="Test Image Placeholder" width="100" height="50">
    <script>
        console.log("Test HTML script executed.");
    </script>
</body>
</html>
    """
    test_css_content = "h1 { color: red; }"

    # Save test files in the script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    html_file_path = os.path.join(script_dir, "test_generated.html") # Use a different name to avoid conflict if test.html already exists
    css_file_path = os.path.join(script_dir, "style.css")
    
    try:
        with open(html_file_path, "w", encoding="utf-8") as f: f.write(test_html_content)
        print(f"Generated HTML file: {html_file_path}")
        with open(css_file_path, "w", encoding="utf-8") as f: f.write(test_css_content)
        print(f"Generated CSS file: {css_file_path}")
        
        # Ensure test_image.png exists (content doesn't matter for path test)
        image_file_path = os.path.join(script_dir, "test_image.png")
        if not os.path.exists(image_file_path):
            with open(image_file_path, "w", encoding="utf-8") as f: f.write("dummy image placeholder")
            print(f"Generated placeholder image: {image_file_path}")

    except Exception as e:
        print(f"Error creating test files: {e}")
        sys.exit(1)

    base_url = QUrl.fromLocalFile(script_dir + os.path.sep)
    print(f"Base URL for preview: {base_url.toString()}")
    
    # Load the generated HTML content directly
    preview.setHtml(test_html_content, base_url)
    # Alternatively, load the generated file:
    # preview.load(QUrl.fromLocalFile(html_file_path))


    main_win.show()
    sys.exit(app.exec())
