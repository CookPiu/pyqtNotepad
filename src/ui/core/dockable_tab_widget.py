from PyQt6.QtWidgets import QTabWidget, QTabBar, QApplication
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRect, QByteArray # Added QByteArray
from PyQt6.QtGui import (QMouseEvent, QDrag, QPixmap, QPainter, 
                         QDragEnterEvent, QDropEvent, QDragMoveEvent, QDragLeaveEvent)

class DockableTabBar(QTabBar):
    """
    Custom QTabBar that handles tab dragging for potential docking/splitting.
    """
    splitRequested = pyqtSignal(int, QPoint) # index of tab, global drop position

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True) # Accept drops for reordering within the bar
        self._drag_start_position = QPoint()
        self._dragged_tab_index = -1

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_position = event.pos()
            self._dragged_tab_index = self.tabAt(event.pos())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if self._dragged_tab_index == -1:
            return
        if (event.pos() - self._drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return

        # Initiate drag
        drag = QDrag(self)
        
        # Create QMimeData directly in the DockableTabBar
        from PyQt6.QtCore import QMimeData # Ensure QMimeData is imported
        mime_data = QMimeData()
        # Use a custom MIME type to identify these draggable tabs
        mime_data.setData("application/x-qtabwidget-tabbar-tab", QByteArray()) # Empty data, type is key
        # Store necessary information as properties on the QMimeData object
        # This information will be retrieved by the drop target.
        mime_data.setProperty("dragged_tab_index", self._dragged_tab_index)
        # parentWidget() here is the DockableTabWidget instance
        mime_data.setProperty("source_tab_widget_id", id(self.parentWidget())) 
        # We might also need to store the actual widget being dragged, or its identifier,
        # if the drop target needs to reparent it. For now, index and source ID.

        # Create a pixmap of the tab for dragging
        tab_rect = self.tabRect(self._dragged_tab_index)
        pixmap = QPixmap(tab_rect.size())
        # pixmap.fill(Qt.GlobalColor.transparent) 
        # Fill with a semi-transparent color from the palette to make it more visible
        color = self.palette().window().color()
        color.setAlpha(180) # Adjust alpha for desired transparency
        pixmap.fill(color)

        painter = QPainter(pixmap)
        # Draw the tab text
        text_color = self.palette().text().color()
        painter.setPen(text_color)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, self.tabText(self._dragged_tab_index))
        
        # Optional: draw a border to make it look more like a tab
        border_color = self.palette().mid().color()
        painter.setPen(border_color)
        painter.drawRect(pixmap.rect().adjusted(0, 0, -1, -1)) # Draw rect inside the pixmap
        painter.end()
        
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos() - self.tabRect(self._dragged_tab_index).topLeft())
        drag.setMimeData(mime_data)

        # Store the index of the tab being dragged in the mimeData
        mime_data.setProperty("dragged_tab_index", self._dragged_tab_index)
        mime_data.setProperty("source_tab_widget_id", id(self.parentWidget()))


        # Execute the drag
        # Qt.DropAction.MoveAction indicates that the tab is moved out.
        # If it's dropped back onto a QTabBar, that QTabBar will handle it.
        # If it's dropped elsewhere (e.g., main window for splitting), we'll handle it there.
        if drag.exec(Qt.DropAction.MoveAction | Qt.DropAction.CopyAction) == Qt.DropAction.MoveAction:
            # If the drop was successful and resulted in a move (e.g., to another tab bar or split),
            # the source tab might need to be closed. This is often handled by the drop target.
            # For splitting, we emit a signal.
            pass
        
        self._dragged_tab_index = -1 # Reset after drag

    # dragEnterEvent, dragMoveEvent, dropEvent are for handling drops *onto* this tab bar (for reordering)
    # The main window or a dedicated drop area will handle drops for splitting.

class DockableTabWidget(QTabWidget):
    """
    A QTabWidget that uses DockableTabBar and can be part of a splitting layout.
    It will emit signals when a tab is dragged out in a way that suggests a split.
    """
    # Signal: index of tab, global drop position, suggested split orientation (e.g., "left", "right", "top", "bottom")
    splitAttempted = pyqtSignal(int, QPoint, str) 
    # Signal: widget of the tab being dragged out, new desired parent (another DockableTabWidget or a placeholder for a new group)
    tabDraggedOut = pyqtSignal(int, object) # index, drop target identifier

    def __init__(self, parent=None):
        super().__init__(parent)
        self._custom_tab_bar = DockableTabBar(self)
        self.setTabBar(self._custom_tab_bar)
        self.setMovable(True) # Allow moving tabs within the bar
        self.setTabsClosable(True) # Ensure tabs have close buttons
        self.setAcceptDrops(True) # Important for receiving drops from other DockableTabWidgets

    # def tabMimeData(self, index: int): # This method is removed from DockableTabWidget
    #     """ Returns MIME data for a tab, used for dragging. """
    #     mime_data = super().tabMimeData(index) if hasattr(super(), 'tabMimeData') else None
    #     if mime_data is None: # Fallback for older Qt or if super doesn't provide
    #         from PyQt6.QtCore import QMimeData
    #         mime_data = QMimeData()
    #     
    #     # We need a way to identify the widget being dragged.
    #     # Storing a pointer or ID. For now, let's assume we can retrieve it later.
    #     # mime_data.setProperty("source_widget_id", id(self.widget(index))) # Not ideal, widget might be reparented
    #     return mime_data

    # The actual splitting logic will be handled by a parent container (e.g., MainWindow or RootEditorArea)
    # This widget's main role is to facilitate the tab dragging out of itself.
    # The DockableTabBar's mouseMoveEvent initiates the QDrag.
    # The parent container will need to have setAcceptDrops(True) and implement dragEnterEvent, dragMoveEvent, dropEvent.

    def dragEnterEvent(self, event: QDragEnterEvent):
        mime_data = event.mimeData()
        if mime_data.hasFormat("application/x-qtabwidget-tabbar-tab"):
            source_id_qvariant = mime_data.property("source_tab_widget_id")
            actual_source_id = None
            if hasattr(source_id_qvariant, 'toLongLong'): val, ok = source_id_qvariant.toLongLong(); actual_source_id = val if ok else None
            elif isinstance(source_id_qvariant, int): actual_source_id = source_id_qvariant

            if actual_source_id is not None and actual_source_id != id(self):
                # This is a drag from another DockableTabWidget.
                # We only want to accept it if it's dropped onto our TabBar.
                # If it's dropped onto the content area, RootEditorAreaWidget should handle it for "add to middle".
                target_widget = self.childAt(event.position().toPoint())
                if isinstance(target_widget, QTabBar): # Or self.tabBar()
                    print(f"DEBUG: DockableTabWidget {id(self)} dragEnter: Accepting drop from other widget {actual_source_id} onto TabBar.")
                    event.acceptProposedAction()
                else:
                    print(f"DEBUG: DockableTabWidget {id(self)} dragEnter: Ignoring drop from other widget {actual_source_id} onto content area. Event pos: {event.position().toPoint()}")
                    event.ignore() # Let RootEditorAreaWidget handle it
                return 
        super().dragEnterEvent(event) # Handle internal reordering or other cases

    def dropEvent(self, event: QDropEvent):
        print(f"DEBUG: DockableTabWidget {id(self)} dropEvent: Called. Event source: {type(event.source())}")
        mime_data = event.mimeData()
        
        if mime_data.hasFormat("application/x-qtabwidget-tabbar-tab"):
            source_tab_widget_id_qvariant = mime_data.property("source_tab_widget_id")
            actual_source_tab_widget_id = None
            if hasattr(source_tab_widget_id_qvariant, 'toLongLong'): val, ok = source_tab_widget_id_qvariant.toLongLong(); actual_source_tab_widget_id = val if ok else None
            elif isinstance(source_tab_widget_id_qvariant, int): actual_source_tab_widget_id = source_tab_widget_id_qvariant

            print(f"DEBUG: DockableTabWidget {id(self)} dropEvent: Mime format OK. Source ID: {actual_source_tab_widget_id}, Self ID: {id(self)}")

            if actual_source_tab_widget_id is not None and actual_source_tab_widget_id != id(self):
                # Tab from another DockableTabWidget.
                # This should only be accepted if dragEnterEvent accepted it (i.e., onto TabBar).
                target_widget = self.childAt(event.position().toPoint())
                if isinstance(target_widget, QTabBar): # Or self.tabBar()
                    print(f"DEBUG: DockableTabWidget {id(self)} dropEvent: Processing drop from other widget {actual_source_tab_widget_id} onto TabBar.")
                    # Here, we need to extract the tab content and add it.
                    # This is the complex part that was previously crashing and is still not fully implemented.
                    # The RootEditorAreaWidget's dropEvent (middle drop) handles the actual tab transfer.
                    # This dropEvent in DockableTabWidget should ideally only facilitate if the drop is on its *own* tab bar
                    # from another widget.
                    # For now, if RootEditorAreaWidget handles the "add to middle" correctly, this path might not be hit
                    # if the drop is on the content area. If it *is* hit (drop on tab bar), we need robust logic.
                    
                    # Let's assume RootEditorAreaWidget's "add to middle" will handle the tab transfer.
                    # This dropEvent should then probably ignore if it's not a simple reorder.
                    # However, if dragEnterEvent accepted, we should technically handle it.
                    
                    # This is a placeholder. The actual tab transfer is complex.
                    # The RootEditorAreaWidget's "add to middle" logic is now the primary handler for this.
                    # If the drop is on the tab bar of *this* widget from *another* widget,
                    # it implies merging tab groups by adding to the tab bar.
                    
                    # For now, let's print and accept, but the actual tab content transfer is missing here.
                    # This functionality (merging by dropping on another tab bar) is secondary to splitting and adding to middle.
                    print(f"INFO: DockableTabWidget {id(self)}: Tab from {actual_source_tab_widget_id} dropped on my TabBar. Needs implementation for tab content transfer.")
                    # super().dropEvent(event) # This might try to interpret it as a standard Qt tab move.
                    event.acceptProposedAction() # Accept the drop, but content transfer is TBD.
                    print(f"Drop event accepted by DockableTabWidget {id(self)} for tab from another widget.")
                    return # Explicitly return after handling
                else:
                    # Drop from another widget onto content area - should have been ignored by dragEnterEvent
                    # and handled by RootEditorAreaWidget. If we reach here, something is unexpected.
                    print(f"WARN: DockableTabWidget {id(self)} dropEvent: Drop from other widget {actual_source_tab_widget_id} on content area. Should be handled by parent. Ignoring.")
                    event.ignore()
                    return

        # If it's an internal move (source_id == id(self)) or not our custom mime type, let superclass handle.
        print(f"DEBUG: DockableTabWidget {id(self)} dropEvent: Passing to super.dropEvent.")
        super().dropEvent(event)

if __name__ == '__main__':
    app = QApplication([])
    main_window = QWidget()
    layout = QVBoxLayout(main_window)
    
    tab_widget1 = DockableTabWidget()
    tab_widget1.addTab(QLabel("Tab 1 in Widget 1"), "Tab 1.1")
    tab_widget1.addTab(QLabel("Tab 2 in Widget 1"), "Tab 1.2")
    
    tab_widget2 = DockableTabWidget()
    tab_widget2.addTab(QLabel("Tab 1 in Widget 2"), "Tab 2.1")
    
    layout.addWidget(tab_widget1)
    layout.addWidget(tab_widget2)
    
    main_window.setWindowTitle("DockableTabWidget Test")
    main_window.resize(600, 400)
    main_window.show()
    app.exec()
