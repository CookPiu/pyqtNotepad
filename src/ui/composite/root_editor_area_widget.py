from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSplitter, QApplication, QRubberBand, QLabel
from PyQt6.QtCore import Qt, QPoint, QRect, QMimeData, QSize
from PyQt6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent, QDragLeaveEvent, QCursor

from .editor_group_widget import EditorGroupWidget
from ..core.dockable_tab_widget import DockableTabWidget

class RootEditorAreaWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.editor_groups: list[EditorGroupWidget] = []
        self._split_drop_indicator: QRubberBand | None = None
        self._current_split_orientation: Qt.Orientation | None = None
        self._drop_target_is_first_in_splitter: bool = True
        self._currently_getting_active_group: bool = False 

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0,0,0,0)
        self.setLayout(self._main_layout)

        self.setAcceptDrops(True)
        self._setup_initial_group()

    def _setup_initial_group(self):
        initial_group = EditorGroupWidget(self)
        initial_group.setObjectName("InitialEditorGroupWidget")
        self.editor_groups.append(initial_group)
        self._main_layout.addWidget(initial_group)
        initial_group.gainedFocus.connect(self._on_editor_group_focused)
        if hasattr(initial_group, 'groupEmpty'):
            initial_group.groupEmpty.connect(self._handle_empty_group_widget)
        self._update_active_group(initial_group)
        print(f"DEBUG: RootEditorAreaWidget - Initial group {id(initial_group)} setup.")

    def get_initial_tab_widget(self) -> DockableTabWidget | None: # Method re-added
        print(f"DEBUG: RootEditorAreaWidget.get_initial_tab_widget called for {id(self)}")
        if not self.editor_groups:
            print(f"DEBUG: RootEditorAreaWidget.get_initial_tab_widget - self.editor_groups is EMPTY.")
            return None
        
        first_group = self.editor_groups[0]
        if first_group is None: # Should not happen if list is not empty and contains valid groups
            print(f"CRITICAL DEBUG: RootEditorAreaWidget.get_initial_tab_widget - self.editor_groups[0] is None!")
            return None
            
        tab_widget_instance = first_group.get_tab_widget()
        if tab_widget_instance is None:
            print(f"CRITICAL DEBUG: RootEditorAreaWidget.get_initial_tab_widget - first_group.get_tab_widget() returned None.")
        return tab_widget_instance

    def get_active_editor_group(self) -> EditorGroupWidget | None:
        if self._currently_getting_active_group:
            return None 
        self._currently_getting_active_group = True
        active_group = None
        try:
            main_win = self.window()
            if hasattr(main_win, 'ui_manager') and main_win.ui_manager and \
               hasattr(main_win.ui_manager, 'active_editor_group'):
                candidate = main_win.ui_manager.active_editor_group
                if candidate in self.editor_groups:
                    active_group = candidate
            if active_group is None and self.editor_groups:
                active_group = self.editor_groups[0]
        finally:
            self._currently_getting_active_group = False
        return active_group

    def _on_editor_group_focused(self, focused_group: EditorGroupWidget):
        self._update_active_group(focused_group)

    def _update_active_group(self, group: EditorGroupWidget | None):
        main_win = self.window()
        if hasattr(main_win, 'ui_manager') and main_win.ui_manager:
            main_win.ui_manager.set_active_editor_group(group)

    def _get_editor_group_at_pos(self, global_pos: QPoint) -> EditorGroupWidget | None:
        widget_at_pos = QApplication.widgetAt(global_pos)
        current_widget = widget_at_pos
        while current_widget:
            if isinstance(current_widget, EditorGroupWidget) and current_widget in self.editor_groups:
                return current_widget
            for group_iter in self.editor_groups: 
                if current_widget is group_iter.get_tab_widget() or \
                   (group_iter.get_tab_widget() and current_widget.parentWidget() == group_iter.get_tab_widget()):
                    return group_iter
            try:
                current_widget = current_widget.parentWidget()
            except RuntimeError: 
                return None
        return None

    def _show_split_indicator(self, target_group: EditorGroupWidget, global_pos: QPoint):
        if self._split_drop_indicator is None:
            self._split_drop_indicator = QRubberBand(QRubberBand.Shape.Rectangle, self.window())
        
        group_rect = target_group.rect()
        local_pos = target_group.mapFromGlobal(global_pos)
        
        edge_ratio = 0.20 
        hotzone_w = int(group_rect.width() * edge_ratio)
        hotzone_h = int(group_rect.height() * edge_ratio)
        min_size = 30 

        determined_orientation = None
        indicator_rect = QRect()
        
        # mapToGlobal is needed for QRubberBand geometry
        group_global_top_left = target_group.mapToGlobal(group_rect.topLeft())

        if local_pos.x() < hotzone_w and group_rect.width() > min_size:
            determined_orientation = Qt.Orientation.Horizontal
            self._drop_target_is_first_in_splitter = True
            indicator_rect = QRect(group_global_top_left, QSize(group_rect.width() // 2, group_rect.height()))
        elif local_pos.x() > group_rect.width() - hotzone_w and group_rect.width() > min_size:
            determined_orientation = Qt.Orientation.Horizontal
            self._drop_target_is_first_in_splitter = False
            indicator_rect = QRect(target_group.mapToGlobal(QPoint(group_rect.width() // 2, 0)), QSize(group_rect.width() // 2, group_rect.height()))
        elif local_pos.y() < hotzone_h and group_rect.height() > min_size:
            determined_orientation = Qt.Orientation.Vertical
            self._drop_target_is_first_in_splitter = True
            indicator_rect = QRect(group_global_top_left, QSize(group_rect.width(), group_rect.height() // 2))
        elif local_pos.y() > group_rect.height() - hotzone_h and group_rect.height() > min_size:
            determined_orientation = Qt.Orientation.Vertical
            self._drop_target_is_first_in_splitter = False
            indicator_rect = QRect(target_group.mapToGlobal(QPoint(0, group_rect.height() // 2)), QSize(group_rect.width(), group_rect.height() // 2))

        if determined_orientation is not None:
            self._current_split_orientation = determined_orientation
            self._split_drop_indicator.setGeometry(indicator_rect)
            self._split_drop_indicator.show()
        else:
            self._current_split_orientation = None
            if self._split_drop_indicator: self._split_drop_indicator.hide()

    def _hide_split_indicator(self):
        if self._split_drop_indicator:
            self._split_drop_indicator.hide()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasFormat("application/x-qtabwidget-tabbar-tab"):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent):
        if event.mimeData().hasFormat("application/x-qtabwidget-tabbar-tab"):
            target_group = self._get_editor_group_at_pos(QCursor.pos())
            if target_group:
                self._show_split_indicator(target_group, QCursor.pos())
                event.accept()
            else:
                self._hide_split_indicator()
                event.ignore()
        else:
            super().dragMoveEvent(event)

    def dragLeaveEvent(self, event: QDragLeaveEvent):
        self._hide_split_indicator()
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent):
        orientation_at_drop = self._current_split_orientation
        self._hide_split_indicator()
        self._current_split_orientation = None 

        mime_data = event.mimeData()
        if not mime_data.hasFormat("application/x-qtabwidget-tabbar-tab"):
            super().dropEvent(event); return

        source_id_prop = mime_data.property("source_tab_widget_id")
        tab_index_prop = mime_data.property("dragged_tab_index")

        source_id = source_id_prop.toInt()[0] if hasattr(source_id_prop, 'toInt') else int(source_id_prop)
        tab_index = tab_index_prop.toInt()[0] if hasattr(tab_index_prop, 'toInt') else int(tab_index_prop)

        target_editor_group = self._get_editor_group_at_pos(QCursor.pos())
        if not target_editor_group: event.ignore(); return

        source_editor_group = None
        for group in self.editor_groups:
            if id(group.get_tab_widget()) == source_id:
                source_editor_group = group; break
        
        if not source_editor_group or not (0 <= tab_index < source_editor_group.count()):
            event.ignore(); return

        widget_to_move = source_editor_group.widget(tab_index)
        title_to_move = source_editor_group.tab_text(tab_index)
        if not widget_to_move: event.ignore(); return

        source_editor_group.remove_editor_tab(tab_index) 
        widget_to_move.setParent(None)

        if orientation_at_drop is not None: 
            self._perform_split(target_editor_group, source_editor_group, widget_to_move, title_to_move, orientation_at_drop)
        else: 
            if source_editor_group != target_editor_group:
                target_editor_group.add_editor_tab(widget_to_move, title_to_move)
                target_editor_group.get_tab_widget().setCurrentWidget(widget_to_move)
                if source_editor_group.count() == 0:
                    self._remove_editor_group(source_editor_group)
            else: 
                target_editor_group.add_editor_tab(widget_to_move, title_to_move) 
                target_editor_group.get_tab_widget().setCurrentWidget(widget_to_move)
        event.acceptProposedAction()

    def _perform_split(self, target_group: EditorGroupWidget, source_group: EditorGroupWidget, 
                       widget_to_add: QWidget, tab_title: str, split_orientation: Qt.Orientation):
        new_editor_group = EditorGroupWidget(self) 
        new_editor_group.setObjectName(f"EditorGroupWidget_{id(new_editor_group)}")
        new_editor_group.add_editor_tab(widget_to_add, tab_title)
        new_editor_group.gainedFocus.connect(self._on_editor_group_focused)
        if hasattr(new_editor_group, 'groupEmpty'):
            new_editor_group.groupEmpty.connect(self._handle_empty_group_widget)
        if new_editor_group not in self.editor_groups:
            self.editor_groups.append(new_editor_group)
        new_editor_group.show() 

        if source_group != target_group and source_group.count() == 0 and source_group in self.editor_groups:
             self._remove_editor_group(source_group)

        new_splitter = QSplitter(split_orientation)
        new_splitter.setObjectName(f"QSplitter_{id(new_splitter)}")
        new_splitter.setChildrenCollapsible(False)
        new_splitter.setHandleWidth(2)
        
        parent_of_target = target_group.parentWidget()
        if parent_of_target == self:
            self._main_layout.removeWidget(target_group)
            if self._drop_target_is_first_in_splitter:
                new_splitter.addWidget(new_editor_group); new_splitter.addWidget(target_group)
            else:
                new_splitter.addWidget(target_group); new_splitter.addWidget(new_editor_group)
            self._main_layout.addWidget(new_splitter)
        elif isinstance(parent_of_target, QSplitter):
            original_index = parent_of_target.indexOf(target_group)
            if original_index != -1:
                parent_of_target.replaceWidget(original_index, new_splitter)
                if self._drop_target_is_first_in_splitter:
                    new_splitter.addWidget(new_editor_group); new_splitter.addWidget(target_group)
                else:
                    new_splitter.addWidget(target_group); new_splitter.addWidget(new_editor_group)
            else: 
                self._main_layout.addWidget(new_splitter)
                if self._drop_target_is_first_in_splitter: new_splitter.addWidget(new_editor_group)
                else: new_splitter.addWidget(target_group)
        else: 
            self._main_layout.addWidget(new_splitter)
            if self._drop_target_is_first_in_splitter: new_splitter.addWidget(new_editor_group)
            else: new_splitter.addWidget(target_group)

        new_editor_group.show(); target_group.show(); new_splitter.show()
        
        total_size = new_splitter.width() if split_orientation == Qt.Orientation.Horizontal else new_splitter.height()
        if total_size > 50 : new_splitter.setSizes([total_size // 2, total_size - (total_size // 2)])
        else: new_splitter.setSizes([100,100])

        self._update_active_group(new_editor_group)
        new_editor_group.get_tab_widget().setCurrentWidget(widget_to_add)
        widget_to_add.setFocus()
        QApplication.processEvents()

    def _remove_editor_group(self, group_to_remove: EditorGroupWidget):
        if group_to_remove not in self.editor_groups: return
        print(f"DEBUG: _remove_editor_group: Removing group {id(group_to_remove)}")
        self.editor_groups.remove(group_to_remove)
        if hasattr(group_to_remove, 'groupEmpty'):
            try: group_to_remove.groupEmpty.disconnect(self._handle_empty_group_widget)
            except TypeError: pass
        
        parent_widget = group_to_remove.parentWidget()
        group_to_remove.setParent(None)
        group_to_remove.deleteLater()

        if isinstance(parent_widget, QSplitter):
            if parent_widget.count() == 1: 
                remaining_widget = parent_widget.widget(0)
                grandparent_widget = parent_widget.parentWidget()
                if remaining_widget: remaining_widget.setParent(None) 
                else: parent_widget.setParent(None); parent_widget.deleteLater(); return

                if grandparent_widget == self:
                    idx = self._main_layout.indexOf(parent_widget)
                    if idx != -1: self._main_layout.replaceWidget(parent_widget, remaining_widget)
                    else: self._main_layout.addWidget(remaining_widget)
                elif isinstance(grandparent_widget, QSplitter):
                    idx = grandparent_widget.indexOf(parent_widget)
                    if idx != -1: grandparent_widget.replaceWidget(idx, remaining_widget)
                    else: grandparent_widget.addWidget(remaining_widget)
                else: 
                    self._main_layout.addWidget(remaining_widget)
                parent_widget.setParent(None); parent_widget.deleteLater()
            elif parent_widget.count() == 0: 
                parent_widget.setParent(None); parent_widget.deleteLater()
        
        if not self.editor_groups:
            self._setup_initial_group()
        elif self.editor_groups:
            self._update_active_group(self.editor_groups[-1])
            if self.editor_groups[-1].count() > 0:
                current_active_tab_content = self.editor_groups[-1].current_widget()
                if current_active_tab_content: current_active_tab_content.setFocus()
            else:
                self.editor_groups[-1].setFocus()

    def _handle_empty_group_widget(self, group_widget: EditorGroupWidget):
        print(f"DEBUG: RootEditorAreaWidget._handle_empty_group_widget: Received for group {id(group_widget)}")
        if group_widget in self.editor_groups:
            self._remove_editor_group(group_widget)
        else: 
            print(f"WARN: RootEditorAreaWidget._handle_empty_group_widget: Group {id(group_widget)} not in known list.")
            group_widget.deleteLater() 

if __name__ == '__main__':
    app = QApplication([])
    main_win = QWidget()
    layout = QVBoxLayout(main_win)
    root_area = RootEditorAreaWidget()
    layout.addWidget(root_area)
    
    initial_tab_widget = root_area.get_initial_tab_widget()
    if initial_tab_widget:
        from PyQt6.QtWidgets import QLabel
        initial_tab_widget.addTab(QLabel("Tab 1"), "Tab 1")
        initial_tab_widget.addTab(QLabel("Tab 2"), "Tab 2")

    main_win.setWindowTitle("RootEditorAreaWidget Test")
    main_win.resize(800, 600)
    main_win.show()
    app.exec()
