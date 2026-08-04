import sys
import tkinter as tk

from .presentation.app import TimetableApp

def main() -> None:
    try:
        TimetableApp().mainloop()
    except tk.TclError as exc:
        message = (
            "The timetable interface could not start because this Python installation "
            "cannot load its Tk/Tcl desktop components.\n\n"
            "Repair or reinstall Python with 'tcl/tk and IDLE' enabled, then run the "
            "application again.\n\n"
            f"Technical detail: {exc}"
        )
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(0, message, "Peripatetic Timetable Optimiser", 0x10)
                return
            except OSError:
                pass
        print(message, file=sys.stderr)

if __name__ == "__main__":
    main()
