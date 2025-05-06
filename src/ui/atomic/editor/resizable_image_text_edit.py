# src/ui/atomic/editor/resizable_image_text_edit.py
import uuid
from PyQt6.QtWidgets import QTextEdit, QMenu, QInputDialog
from PyQt6.QtGui import QTextDocument, QTextImageFormat, QImage, QTextCursor, QAction
from PyQt6.QtCore import QMimeData, QUrl, Qt, QSize, QPoint

class ResizableImageTextEdit(QTextEdit):
    """
    A QTextEdit subclass that inserts pasted images with a default maximum width.
    """
    DEFAULT_IMAGE_WIDTH = 200 # Default width for pasted images

    def __init__(self, parent=None):
        super().__init__(parent)

    def insertFromMimeData(self, source: QMimeData):
        """
        Overrides the default paste behavior to handle images with resizing.
        """
        if source.hasImage():
            try:
                # Extract image data
                image_data = source.imageData()
                if isinstance(image_data, QImage) and not image_data.isNull():
                    image = image_data
                    # Generate a unique name for the image resource
                    image_name = f"pasted_image_{uuid.uuid4()}.png"
                    # Add the image to the document's resource cache
                    self.document().addResource(QTextDocument.ResourceType.ImageResource, QUrl(image_name), image)

                    # Create an image format
                    image_format = QTextImageFormat()
                    image_format.setName(image_name)

                    # --- Apply Size Constraint ---
                    original_size = image.size()
                    target_width = self.DEFAULT_IMAGE_WIDTH
                    if original_size.width() > target_width:
                        # Calculate aspect ratio
                        aspect_ratio = original_size.height() / original_size.width()
                        target_height = int(target_width * aspect_ratio)
                        image_format.setWidth(target_width)
                        image_format.setHeight(target_height)
                    else:
                        # Use original size if smaller than default width
                        image_format.setWidth(original_size.width())
                        image_format.setHeight(original_size.height())
                    # -----------------------------

                    # Insert the image at the current cursor position
                    cursor = self.textCursor()
                    cursor.insertImage(image_format)
                    return # Prevent default handling
                else:
                    print("Pasted image data is invalid or not a QImage.")
                    super().insertFromMimeData(source) # Fallback for invalid image data

            except Exception as e:
                print(f"Error processing pasted image: {e}")
                super().insertFromMimeData(source) # Fallback on error
        else:
            # Handle other data types (text, html, etc.) using the default method
            super().insertFromMimeData(source)

    # Optional: Add context menu for resizing later?
    def contextMenuEvent(self, event):
        """Overrides the context menu to add image resizing."""
        menu = self.createStandardContextMenu(event.pos())

        print(f"DEBUG: contextMenuEvent triggered at pos: {event.pos()}")
        # Get cursor at the event position
        cursor = self.cursorForPosition(event.pos())
        print(f"DEBUG: Initial cursor position: {cursor.position()}")
        image_format = None
        image_start_pos = -1
        image_end_pos = -1

        # Check if the exact cursor position is an image
        current_char_format = cursor.charFormat()
        print(f"DEBUG: Format at cursor pos {cursor.position()}: isImage={current_char_format.isImageFormat()}, objectType={current_char_format.objectType()}")

        if current_char_format.isImageFormat():
            image_format = current_char_format.toImageFormat()
            # Select the image character to get its bounds. An image is treated as one character.
            # Move left to be *before* the image character, then right keeping anchor to select it.
            cursor.movePosition(QTextCursor.MoveOperation.Left)
            cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, 1)
            image_start_pos = cursor.selectionStart()
            image_end_pos = cursor.selectionEnd()
            print(f"DEBUG: Image found directly at cursor. Pos: {image_start_pos}-{image_end_pos}, Name: {image_format.name()}")
        else:
            # If not directly on it, check the character immediately before the cursor
            # Create a temporary cursor to check without moving the main one yet
            check_cursor = QTextCursor(cursor)
            check_cursor.movePosition(QTextCursor.MoveOperation.Left)
            prev_char_format = check_cursor.charFormat()
            print(f"DEBUG: Format at pos {check_cursor.position()} (before cursor): isImage={prev_char_format.isImageFormat()}, objectType={prev_char_format.objectType()}")
            if prev_char_format.isImageFormat():
                 image_format = prev_char_format.toImageFormat()
                 # Select the image character
                 cursor = check_cursor # Use the cursor that's now positioned correctly
                 cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor, 1) # Select the image char itself
                 image_start_pos = cursor.selectionStart()
                 image_end_pos = cursor.selectionEnd()
                 print(f"DEBUG: Image found before cursor. Pos: {image_start_pos}-{image_end_pos}, Name: {image_format.name()}")


        if image_format and image_start_pos != -1:
            image_name = image_format.name() # Get image name for resource lookup
            print(f"DEBUG: Creating and adding resize action for image: {image_name}")

            resize_action = QAction("调整图片大小...", self)
            # Use a lambda and ensure default arguments capture the loop variables correctly if this were in a loop (it's not, but good practice)
            # Pass the image position and format to the slot
            resize_action.triggered.connect(lambda checked=False, start=image_start_pos, end=image_end_pos, fmt=image_format: self._show_resize_image_dialog(start, end, fmt))
            # Insert before the first separator or at the end
            first_separator = next((action for action in menu.actions() if action.isSeparator()), None)
            if first_separator:
                menu.insertAction(first_separator, resize_action)
            else:
                menu.addAction(resize_action)

        # Ensure the menu is executed even if no image is found
        menu.exec(event.globalPos())

    def _show_resize_image_dialog(self, image_start_pos: int, image_end_pos: int, image_format: QTextImageFormat):
        """Shows a dialog to get new width and resizes the image at the given position."""
        doc = self.document()
        image_name = image_format.name()
        image_resource = doc.resource(QTextDocument.ResourceType.ImageResource, QUrl(image_name))

        # Determine original size more reliably
        original_width = 0
        original_height = 0
        if isinstance(image_resource, QImage) and not image_resource.isNull():
            original_width = image_resource.width()
            original_height = image_resource.height()

        # Fallback using format if resource failed or size is invalid
        if original_width <= 0 or original_height <= 0:
             format_width = image_format.width()
             format_height = image_format.height()
             if format_width > 0 and format_height > 0:
                 original_width = format_width
                 original_height = format_height
             else:
                 # Ultimate fallback
                 original_width = 100
                 print("Warning: Could not determine original image size, using fallback 100x100.")

        # Use the format's current width for the dialog default
        current_width = int(image_format.width()) if image_format.width() > 0 else int(original_width)

        new_width, ok = QInputDialog.getInt(self, "调整图片大小", "输入新的宽度 (像素):",
                                            value=current_width, min=10, max=4000) # Increased max width

        if ok and new_width > 0:
            # Calculate new height based on original aspect ratio
            aspect_ratio = original_height / original_width if original_width > 0 else 1.0
            new_height = int(new_width * aspect_ratio)

            if new_height > 0:
                new_image_format = QTextImageFormat()
                new_image_format.setName(image_name) # Use the stored name
                new_image_format.setWidth(new_width)
                new_image_format.setHeight(new_height)

                # Create a new cursor and select the exact image position
                resize_cursor = QTextCursor(doc)
                resize_cursor.setPosition(image_start_pos)
                # Select the single image character (QTextEdit treats images like characters)
                resize_cursor.setPosition(image_end_pos, QTextCursor.MoveMode.KeepAnchor)

                # Apply the new format to the selected image character
                resize_cursor.setCharFormat(new_image_format)
                self.document().setModified(True) # Mark document as modified
                print(f"Image resized to {new_width}x{new_height}")
            else:
                 QMessageBox.warning(self, "调整失败", "计算出的图片高度无效。")
        else:
             print("Image resize cancelled or invalid width entered.")
