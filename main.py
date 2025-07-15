"""
Entry point for the Task Manager Widget application.
Initializes and runs the main window.
"""
import sys
from PyQt5.QtWidgets import QApplication
from ui import TaskManagerWidget
from storage import ensure_db_files

import os
if sys.platform.startswith('win'):
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\\Microsoft\\Windows\\CurrentVersion\\Run", 0, winreg.KEY_SET_VALUE)
        exe_path = os.path.abspath(__file__)
        python_path = sys.executable
        # Use pythonw.exe to avoid console window if available
        if python_path.lower().endswith('python.exe'):
            pythonw = python_path[:-10] + 'pythonw.exe'
            if os.path.exists(pythonw):
                python_path = pythonw
        cmd = f'\"{python_path}\" \"{exe_path}\"'
        winreg.SetValueEx(key, 'NimbusTasks', 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
    except Exception as e:
        pass  # Ignore errors, e.g., if not running on Windows or no permissions

if __name__ == '__main__':
    ensure_db_files()
    app = QApplication(sys.argv)
    widget = TaskManagerWidget()
    widget.show()
    sys.exit(app.exec_()) 