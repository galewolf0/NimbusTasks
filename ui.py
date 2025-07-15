"""
UI components for the Task Manager Widget application.
Contains all custom PyQt5 widgets and dialogs.
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QCalendarWidget, QListWidget, QListWidgetItem,
    QLineEdit, QPushButton, QHBoxLayout, QCheckBox, QLabel, QDialog, QDialogButtonBox, QFormLayout,
    QStyledItemDelegate, QMessageBox, QDateEdit, QGridLayout
)
from PyQt5.QtCore import Qt, QDate, QPoint, pyqtSignal
from PyQt5.QtGui import QCursor, QTextCharFormat, QColor, QFont, QIcon
import sys
from storage import date_to_str, add_task_to_db, add_recurring_tasks_to_db, get_tasks_for_date, complete_task, get_completed_tasks_for_date, uncomplete_task, delete_task as db_delete_task, delete_completed_task, get_all_task_dates
from desktop import set_as_desktop_widget
import os

class AddTaskDialog(QDialog):
    """Dialog for adding a new task, with UI for recursive tasks."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._original_geometry = None  # Store the original geometry (size and position)
        self.setWindowTitle('Add Task - NimbusTasks')
        self.setModal(True)
        self.setMinimumWidth(350)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setWindowIcon(QIcon('icon.ico'))
        layout = QFormLayout(self)
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText('Enter your task...')
        layout.addRow('Task:', self.task_input)
        # Recurrence UI
        self.recursive_checkbox = QCheckBox('Is this a recurring task?')
        self.recursive_checkbox.setStyleSheet('''
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:checked {
                image: none;
                border: 1.5px solid #388e3c;
                background: #388e3c;
                color: #fff;
            }
            QCheckBox::indicator:unchecked {
                image: none;
                border: 1.5px solid #888;
                background: #23272e;
            }
        ''')
        layout.addRow('', self.recursive_checkbox)
        # Recurrence details (hidden by default)
        self.recursive_details_widget = QWidget()
        details_layout = QFormLayout(self.recursive_details_widget)
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate())
        details_layout.addRow('Start date:', self.start_date_edit)
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())
        details_layout.addRow('End date:', self.end_date_edit)
        # Days of week checkboxes in rows of 3
        self.days_of_week = []
        days_grid = QGridLayout()
        day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        for i, day in enumerate(day_names):
            cb = QCheckBox(day)
            cb.setChecked(True)  # Default all days to checked
            # Custom style: show tick mark when checked, box when unchecked
            cb.setStyleSheet('''
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                }
                QCheckBox::indicator:checked {
                    image: none;
                    border: 1.5px solid #388e3c;
                    background: #388e3c;
                    color: #fff;
                }
                QCheckBox::indicator:unchecked {
                    image: none;
                    border: 1.5px solid #888;
                    background: #23272e;
                }
            ''')
            self.days_of_week.append(cb)
            row = i // 3
            col = i % 3
            days_grid.addWidget(cb, row, col)
        days_widget = QWidget()
        days_widget.setLayout(days_grid)
        details_layout.addRow('Days:', days_widget)
        self.recursive_details_widget.setVisible(False)
        layout.addRow('', self.recursive_details_widget)
        # Button box
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        self.setLayout(layout)
        # Enable OK only if text is not empty
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)
        self.task_input.textChanged.connect(self._on_text_changed)
        self.task_input.returnPressed.connect(self._on_return_pressed)
        self.warning_label = QLabel()
        self.warning_label.setStyleSheet('color: #d32f2f;')
        self.warning_label.setVisible(False)
        layout.insertRow(0, '', self.warning_label)
        # Show/hide recurrence details
        self.recursive_checkbox.stateChanged.connect(self._on_recursive_changed)

    def _on_recursive_changed(self, state):
        if self.recursive_checkbox.isChecked():
            self.recursive_details_widget.setVisible(True)
            self.adjustSize()
        else:
            self.recursive_details_widget.setVisible(False)
            if self._original_geometry is not None:
                self.setGeometry(self._original_geometry)

    def showEvent(self, event):
        super().showEvent(event)
        if self._original_geometry is None:
            self._original_geometry = self.geometry()
        self.task_input.setFocus()

    def _on_text_changed(self, text):
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(bool(text.strip()))
        self.warning_label.setVisible(False)

    def _on_return_pressed(self):
        if self.button_box.button(QDialogButtonBox.Ok).isEnabled():
            self.accept()
        else:
            self.warning_label.setText('Task cannot be empty!')
            self.warning_label.setVisible(True)

    def get_task(self):
        return self.task_input.text().strip()

    def is_recursive(self):
        return self.recursive_checkbox.isChecked()

    def get_recurring_details(self):
        if not self.is_recursive():
            return None
        start_date = self.start_date_edit.date().toString('yyyy-MM-dd')
        end_date = self.end_date_edit.date().toString('yyyy-MM-dd')
        days = [cb.text() for cb in self.days_of_week if cb.isChecked()]
        return {'start_date': start_date, 'end_date': end_date, 'days': days}

class ClickableLabel(QLabel):
    """A QLabel that emits a signal when clicked."""
    clicked = pyqtSignal()
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

class TaskWidget(QWidget):
    """Widget representing a single task with a checkbox and delete button."""
    def __init__(self, text, done, delete_callback, state_changed_callback):
        super().__init__()
        self._raw_text = text
        self._delete_callback = delete_callback
        self._state_changed_callback = state_changed_callback
        self._init_layout()
        self.set_done(done)

    def _init_layout(self):
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.checkbox = QCheckBox()
        self.checkbox.stateChanged.connect(self._on_checkbox_state_changed)
        self.tick_label = ClickableLabel('✔')
        self.tick_label.setStyleSheet('font-size: 16px; color: #fff;')
        self.tick_label.setVisible(False)
        self.tick_label.clicked.connect(self._on_tick_clicked)
        self.layout.addWidget(self.checkbox)
        self.layout.addWidget(self.tick_label)
        self.delete_btn = QPushButton('🗑️')
        self.delete_btn.setFixedWidth(28)
        self.delete_btn.setToolTip('Delete task')
        self.delete_btn.clicked.connect(self._delete_callback)
        self.layout.addWidget(self.delete_btn)
        self.setLayout(self.layout)

    def set_done(self, checked):
        self.checkbox.setVisible(not checked)
        self.tick_label.setVisible(checked)
        if checked:
            self.tick_label.setText('✔ ' + self._raw_text)
        else:
            self.checkbox.setText(self._raw_text)
        self.update_background(checked)
        self.checkbox.setChecked(checked)

    def _on_checkbox_state_changed(self, state):
        checked = (state == Qt.Checked)
        self.set_done(checked)
        if self._state_changed_callback:
            self._state_changed_callback()

    def _on_tick_clicked(self):
        # Mark as incomplete
        self.set_done(False)
        if self._state_changed_callback:
            self._state_changed_callback()

    def isChecked(self):
        return self.checkbox.isChecked() or self.tick_label.isVisible()

    def text(self):
        return self._raw_text

    def update_background(self, checked):
        if checked:
            self.setStyleSheet('background: #388e3c; border-radius: 6px;')
        else:
            self.setStyleSheet('')

class HideOtherMonthDelegate(QStyledItemDelegate):
    """Delegate to hide days from other months in the calendar view."""
    def paint(self, painter, option, index):
        date = index.data(0x0100)  # Qt.UserRole
        if date:
            cal = option.widget.parent()
            if hasattr(cal, 'monthShown') and hasattr(cal, 'yearShown'):
                if (date.month() != cal.monthShown()) or (date.year() != cal.yearShown()):
                    return  # Don't paint anything for other months
        super().paint(painter, option, index)

class TaskManagerWidget(QWidget):
    """Main widget for the Task Manager application."""
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setWindowTitle('NimbusTasks')
        self.setWindowIcon(QIcon('icon.ico'))
        self.resize(350, 500)
        self.tasks_by_date = {} # This will be removed
        self.current_date = QDate.currentDate()
        self.dragging = False
        self.drag_position = QPoint()
        self.init_ui()
        self.load_tasks_for_date(self.current_date)
        self.update_calendar_task_highlights()
        self.move_to_top_right()
        set_as_desktop_widget(self)

    def apply_dark_mode(self):
        """Applies a dark mode stylesheet and palette to the application widgets."""
        dark_style = """
        QWidget {
            background: #23272e;
            color: #f1f1f1;
        }
        QCalendarWidget QWidget {
            background: #23272e;
            color: #f1f1f1;
        }
        QCalendarWidget QAbstractItemView, QCalendarWidget QTableView {
            background: #23272e;
            color: #f1f1f1;
            selection-background-color: #444b5a;
            selection-color: #fff;
            gridline-color: #444b5a;
        }
        QCalendarWidget QToolButton {
            background: #23272e;
            color: #f1f1f1;
            border: none;
            min-width: 28px;
            qproperty-iconSize: 16px 16px;
            text-align: center;
        }
        QCalendarWidget QToolButton#qt_calendar_prevmonth, QCalendarWidget QToolButton#qt_calendar_nextmonth {
            min-width: 28px;
            max-width: 28px;
            text-align: center;
            padding: 0;
        }
        QCalendarWidget QSpinBox {
            background: #23272e;
            color: #f1f1f1;
            border: none;
            min-width: 28px;
            font-size: 14px;
            qproperty-buttonSymbols: NoButtons;
            text-align: center;
        }
        QCalendarWidget QMenu {
            background: #23272e;
            color: #f1f1f1;
        }
        QCalendarWidget QHeaderView {
            background: #23272e;
            color: #f1f1f1;
        }
        QCalendarWidget QAbstractItemView:enabled {
            background: #23272e;
            color: #f1f1f1;
        }
        QCalendarWidget QAbstractItemView:disabled {
            color: transparent;
            background: transparent;
        }
        QCalendarWidget QTableView QTableCornerButton::section {
            background: #23272e;
        }
        QCalendarWidget QTableView::item:selected {
            background: #444b5a;
            color: #fff;
        }
        QCalendarWidget QTableView::item:enabled {
            color: #f1f1f1;
        }
        QCalendarWidget QTableView::item:disabled {
            color: #888;
        }
        QCalendarWidget QTableView::item#qt_calendar_today {
            border: 1px solid #d32f2f;
            background: #2d313a;
            color: #fff;
        }
        QLineEdit {
            background: #23272e;
            color: #f1f1f1;
            border: 1px solid #444b5a;
            border-radius: 4px;
        }
        QLineEdit:focus {
            border: 1.5px solid #5a6273;
        }
        QListWidget {
            background: #23272e;
            color: #f1f1f1;
            border: 1px solid #444b5a;
        }
        QCheckBox {
            background: transparent;
            color: #f1f1f1;
        }
        QCheckBox::indicator {
            background: #23272e;
            border: 1px solid #888;
            width: 14px;
            height: 14px;
            border-radius: 3px;
        }
        QCheckBox::indicator:checked {
            background: #5a6273;
            border: 1.5px solid #d32f2f;
        }
        QCheckBox::indicator:unchecked {
            background: #23272e;
            border: 1px solid #888;
        }
        QLabel {
            background: transparent;
            color: #f1f1f1;
        }
        QPushButton {
            background: #444b5a;
            color: #f1f1f1;
            border: none;
            border-radius: 6px;
            padding: 2px 8px;
        }
        QPushButton:hover {
            background: #5a6273;
        }
        QPushButton:pressed {
            background: #23272e;
        }
        QScrollBar:vertical {
            background: #23272e;
            width: 8px;
            margin: 0px 0px 0px 0px;
        }
        QScrollBar::handle:vertical {
            background: #444b5a;
            min-height: 20px;
            border-radius: 4px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        QCalendarWidget QToolButton::menu-indicator {
            image: none;
            width: 0px;
            height: 0px;
        }
        """
        self.setStyleSheet(dark_style)
        # Drag handle and close button custom style
        self.drag_handle.setStyleSheet('background: #2d313a; border-radius: 6px; font-size: 16px; color: #aaa;')
        self.close_btn.setStyleSheet('background: #d32f2f; color: white; border: none; border-radius: 6px; font-size: 14px;')

        # Set dark palette for better consistency
        from PyQt5.QtGui import QPalette, QColor
        from PyQt5.QtWidgets import QApplication
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor('#23272e'))
        palette.setColor(QPalette.WindowText, QColor('#f1f1f1'))
        palette.setColor(QPalette.Base, QColor('#23272e'))
        palette.setColor(QPalette.AlternateBase, QColor('#2d313a'))
        palette.setColor(QPalette.ToolTipBase, QColor('#23272e'))
        palette.setColor(QPalette.ToolTipText, QColor('#f1f1f1'))
        palette.setColor(QPalette.Text, QColor('#f1f1f1'))
        palette.setColor(QPalette.Button, QColor('#444b5a'))
        palette.setColor(QPalette.ButtonText, QColor('#f1f1f1'))
        palette.setColor(QPalette.BrightText, QColor('#d32f2f'))
        palette.setColor(QPalette.Highlight, QColor('#444b5a'))
        palette.setColor(QPalette.HighlightedText, QColor('#fff'))
        QApplication.setPalette(palette)

    def init_ui(self):
        """Initializes the UI layout and widgets for the main window."""
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Top bar: Logo + Drag handle + Close button
        top_bar = QHBoxLayout()
        self.logo_label = QLabel()
        self.logo_label.setPixmap(QIcon('icon.png').pixmap(24, 24))
        self.logo_label.setFixedSize(28, 28)
        top_bar.addWidget(self.logo_label)

        self.drag_handle = QLabel('≡')
        self.drag_handle.setFixedHeight(18)
        self.drag_handle.setAlignment(Qt.AlignCenter)
        self.drag_handle.setCursor(Qt.OpenHandCursor)
        self.drag_handle.mousePressEvent = self.start_drag
        self.drag_handle.mouseMoveEvent = self.do_drag
        self.drag_handle.mouseReleaseEvent = self.end_drag
        top_bar.addWidget(self.drag_handle)

        self.close_btn = QPushButton('×')
        self.close_btn.setFixedSize(22, 18)
        self.close_btn.setToolTip('Close')
        self.close_btn.clicked.connect(self.close)
        top_bar.addWidget(self.close_btn)
        top_bar.setAlignment(self.close_btn, Qt.AlignRight)
        top_bar.setSpacing(4)
        layout.addLayout(top_bar)

        # Calendar widget
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setSelectedDate(self.current_date)
        self.calendar.selectionChanged.connect(self.on_date_changed)
        self.calendar.setDateEditEnabled(False)
        self.calendar.setVerticalHeaderFormat(self.calendar.ISOWeekNumbers)
        self.calendar.setHorizontalHeaderFormat(self.calendar.ShortDayNames)
        self.calendar.setNavigationBarVisible(True)
        self.calendar.setFirstDayOfWeek(Qt.Monday)
        # self.calendar.setStyleSheet(self.styleSheet())  # Style applied globally
        # Hide other month days using delegate
        view = self.calendar.findChild(type(self.calendar), "qt_calendar_calendarview")
        if view:
            view.setItemDelegate(HideOtherMonthDelegate(self.calendar))
        layout.addWidget(self.calendar)

        # Task list widget
        self.task_list = QListWidget()
        layout.addWidget(self.task_list)

        # Add task input (hidden, replaced by popup dialog)
        input_layout = QHBoxLayout()
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText('Add a new task...')
        self.task_input.setVisible(False)
        self.add_btn = QPushButton('Add')
        self.add_btn.clicked.connect(self.show_add_task_dialog)
        input_layout.addWidget(self.task_input)
        input_layout.addWidget(self.add_btn)
        layout.addLayout(input_layout)

        # Startup checkbox (Windows only)
        if sys.platform.startswith('win'):
            self.startup_checkbox = QCheckBox('Start NimbusTasks at Windows launch')
            self.startup_checkbox.setStyleSheet('''
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                }
                QCheckBox::indicator:checked {
                    image: none;
                    border: 1.5px solid #388e3c;
                    background: #388e3c;
                    color: #fff;
                }
                QCheckBox::indicator:unchecked {
                    image: none;
                    border: 1.5px solid #888;
                    background: #23272e;
                }
            ''')
            self.startup_checkbox.stateChanged.connect(self.on_startup_checkbox_changed)
            layout.addWidget(self.startup_checkbox)
            self._update_startup_checkbox()

        self.setLayout(layout)
        self.apply_dark_mode()

    def show_add_task_dialog(self):
        dialog = AddTaskDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            text = dialog.get_task()
            if text:
                if dialog.is_recursive():
                    details = dialog.get_recurring_details()
                    self.add_task(text, recurring_details=details)
                else:
                    self.add_task(text)

    def add_task(self, text, recurring_details=None):
        if recurring_details is None:
            date_str = date_to_str(self.current_date)
            add_task_to_db(date_str, text)
        else:
            # Add multiple entries for each date in the recurrence using batch insert
            from PyQt5.QtCore import QDate
            start = QDate.fromString(recurring_details['start_date'], 'yyyy-MM-dd')
            end = QDate.fromString(recurring_details['end_date'], 'yyyy-MM-dd')
            days = set(recurring_details['days'])
            day_name_map = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            task_entries = []
            d = QDate(start)
            while d <= end:
                if day_name_map[d.dayOfWeek()-1] in days:
                    task_entries.append((date_to_str(d), text))
                d = d.addDays(1)
            add_recurring_tasks_to_db(task_entries)
        self.load_tasks_for_date(self.current_date)
        self.update_calendar_task_highlights()

    def _add_task_widget(self, text, done, return_widget=False, is_recurring=False, task_id=None, is_completed=False):
        item = QListWidgetItem()
        def delete_task():
            widget.delete_btn.setEnabled(False)
            widget.checkbox.setEnabled(False)
            if is_completed:
                delete_completed_task(task_id)
            else:
                db_delete_task(task_id)
            self.load_tasks_for_date(self.current_date)
            self.update_calendar_task_highlights()
        widget = TaskWidget(text, done, delete_task, None)
        def state_changed_callback():
            widget.checkbox.setEnabled(False)
            widget.delete_btn.setEnabled(False)
            if widget.isChecked() and not is_completed:
                complete_task(task_id, date_to_str(self.current_date), text)
                self.load_tasks_for_date(self.current_date)
                self.update_calendar_task_highlights()
            elif not widget.isChecked() and is_completed:
                uncomplete_task(task_id, date_to_str(self.current_date), text)
                self.load_tasks_for_date(self.current_date)
                self.update_calendar_task_highlights()
        widget._state_changed_callback = state_changed_callback
        self.task_list.addItem(item)
        self.task_list.setItemWidget(item, widget)
        if return_widget:
            return widget

    def save_current_date_tasks_and_update(self):
        # This method is no longer needed as tasks are directly managed by the database
        pass

    def save_current_date_tasks(self):
        # This method is no longer needed as tasks are directly managed by the database
        pass

    def load_tasks_for_date(self, qdate):
        self.task_list.clear()
        date_str = date_to_str(qdate)
        tasks = get_tasks_for_date(date_str)
        completed_tasks = get_completed_tasks_for_date(date_str)
        is_past = qdate < QDate.currentDate()
        # Show incomplete tasks
        for task in tasks:
            widget = self._add_task_widget(task['text'], False, return_widget=True, task_id=task['id'], is_completed=False)
            if is_past:
                widget.checkbox.setEnabled(False)
                widget.delete_btn.setEnabled(False)
                widget.setStyleSheet('background: #d32f2f; border-radius: 6px;')
        # Show completed tasks (checked, disabled, green background)
        for task in completed_tasks:
            widget = self._add_task_widget(task['text'], True, return_widget=True, task_id=task['id'], is_completed=True)
            widget.checkbox.setEnabled(True)  # Allow unchecking
            widget.delete_btn.setEnabled(False)
            widget.setStyleSheet('background: #388e3c; border-radius: 6px;')
        self.task_input.setEnabled(not is_past)
        self.add_btn.setEnabled(not is_past)
        self.update_calendar_task_highlights()

    def on_date_changed(self):
        self.current_date = self.calendar.selectedDate()
        self.load_tasks_for_date(self.current_date)
        self.update_calendar_task_highlights()

    def update_calendar_task_highlights(self):
        """Highlight calendar dates based on task completion and reset Saturday to default color."""
        from PyQt5.QtGui import QTextCharFormat, QColor, QFont
        from PyQt5.QtCore import Qt, QDate
        self.calendar.setDateTextFormat(QDate(), QTextCharFormat())
        today = QDate.currentDate()
        
        # Get the currently visible month from the calendar's selected date
        visible_date = self.calendar.selectedDate()
        visible_year = visible_date.year()
        visible_month_num = visible_date.month()
        
        # Get all dates with any tasks
        all_dates = get_all_task_dates()
        for date_str in all_dates:
            qdate = QDate.fromString(date_str, 'yyyy-MM-dd')
            
            # Only highlight dates in the currently visible month
            if qdate.year() != visible_year or qdate.month() != visible_month_num:
                continue
                
            if qdate == today:
                continue  # Never set red/green for today
            incomplete_tasks = get_tasks_for_date(date_str)
            completed_tasks = get_completed_tasks_for_date(date_str)
            fmt = QTextCharFormat()
            if incomplete_tasks:
                if qdate < today:
                    fmt.setBackground(QColor('#d32f2f'))  # Red background for past days with incomplete tasks
                    fmt.setForeground(QColor('#fff'))
                else:
                    continue  # No special formatting for future days with incomplete tasks
            elif completed_tasks:
                # All tasks completed for this day
                fmt.setBackground(QColor('#388e3c'))  # Green background
                fmt.setForeground(QColor('#fff'))
            else:
                continue  # No tasks at all (shouldn't happen)
            self.calendar.setDateTextFormat(qdate, fmt)
        today_fmt = self.calendar.dateTextFormat(today)
        today_fmt.setBackground(QColor('#1976d2'))  # blue background
        today_fmt.setForeground(QColor('#fff'))     # white text
        today_fmt.setFontWeight(QFont.Bold)
        self.calendar.setDateTextFormat(today, today_fmt)
        # Set Sunday to red, Saturday to default
        sunday_format = QTextCharFormat()
        sunday_format.setForeground(QColor('#d32f2f'))
        self.calendar.setWeekdayTextFormat(Qt.Sunday, sunday_format)
        self.calendar.setWeekdayTextFormat(Qt.Saturday, QTextCharFormat())

    def move_to_top_right(self):
        """Move the window to the top right corner of the primary screen with a larger left margin."""
        from PyQt5.QtWidgets import QApplication
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.right() - self.width() - 100  # 100px margin from right
        y = screen.top() + 20  # 20px margin from top
        self.move(x, y)

    def start_drag(self, event):
        """Initiate window dragging when the drag handle is pressed."""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            self.drag_handle.setCursor(Qt.ClosedHandCursor)
            event.accept()

    def do_drag(self, event):
        """Move the window as the mouse moves while dragging."""
        if self.dragging and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def end_drag(self, event):
        """End the dragging operation when the mouse is released."""
        self.dragging = False
        self.drag_handle.setCursor(Qt.OpenHandCursor)
        event.accept()

    def closeEvent(self, event):
        from PyQt5.QtWidgets import QApplication
        QApplication.quit() 

    def _update_startup_checkbox(self):
        # Check if CalenDo is set to run at startup (Windows registry)
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r"Software\\Microsoft\\Windows\\CurrentVersion\\Run", 0, winreg.KEY_READ)
            value, _ = winreg.QueryValueEx(key, 'CalenDo')
            winreg.CloseKey(key)
            self.startup_checkbox.blockSignals(True)
            self.startup_checkbox.setChecked(True)
            self.startup_checkbox.blockSignals(False)
        except Exception:
            self.startup_checkbox.blockSignals(True)
            self.startup_checkbox.setChecked(False)
            self.startup_checkbox.blockSignals(False)

    def on_startup_checkbox_changed(self, state):
        # Add or remove CalenDo from Windows startup
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r"Software\\Microsoft\\Windows\\CurrentVersion\\Run", 0, winreg.KEY_SET_VALUE)
            exe_path = os.path.abspath(sys.argv[0])
            python_path = sys.executable
            # Use pythonw.exe to avoid console window if available
            if python_path.lower().endswith('python.exe'):
                pythonw = python_path[:-10] + 'pythonw.exe'
                if os.path.exists(pythonw):
                    python_path = pythonw
            cmd = f'"{python_path}" "{exe_path}"'
            if state == Qt.Checked:
                winreg.SetValueEx(key, 'CalenDo', 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, 'CalenDo')
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception:
            pass 