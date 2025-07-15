"""
Entry point for the Task Manager Widget application.
Initializes and runs the main window.
"""
import sys
from PyQt5.QtWidgets import QApplication
from ui import TaskManagerWidget
from storage import ensure_db_files

import os
# Remove Windows startup registry code

if __name__ == '__main__':
    ensure_db_files()
    app = QApplication(sys.argv)
    widget = TaskManagerWidget()
    widget.show()
    sys.exit(app.exec_()) 