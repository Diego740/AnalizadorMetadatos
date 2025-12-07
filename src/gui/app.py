import sys
from pathlib import Path

# Ensure src is in python path to import core modules
current_dir = Path(__file__).resolve().parent
src_dir = current_dir.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from gui.main_window import MetadataAnalyzerApp

if __name__ == "__main__":
    app = MetadataAnalyzerApp()
    app.mainloop()
