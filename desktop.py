"""
Windows-specific logic for setting a PyQt5 widget as a desktop widget.
"""
import sys

def set_as_desktop_widget(widget):
    """On Windows, set the window as a desktop widget (below all windows, above wallpaper)."""
    if sys.platform.startswith('win'):
        try:
            import win32con, win32gui, win32api
            hwnd = int(widget.winId())
            progman = win32gui.FindWindow('Progman', None)
            # Set parent to Progman (desktop)
            win32gui.SetParent(hwnd, progman)
            # Set window position to bottom
            win32gui.SetWindowPos(hwnd, win32con.HWND_BOTTOM, 0, 0, 0, 0,
                                  win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)
        except ImportError:
            pass  # pywin32 not available, skip
        except Exception:
            pass  # fallback to normal window 