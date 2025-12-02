import tkinter as tk
from tkinter import ttk

from .config import (
    APP_TITLE, WINDOW_SIZE, BG_COLOR, FG_COLOR, 
    ACCENT_COLOR, BUTTON_BG, BUTTON_FG, 
    FONT_MAIN, FONT_HEADER, FONT_SMALL
)

from .frames.file_select import FileSelectFrame
from .frames.results import ResultsFrame
from .frames.custom_metadata import CustomMetadataFrame

class MetadataAnalyzerApp(tk.Tk):
    """
    Main Application Class.
    Manages the main window and switching between frames.
    """
    def __init__(self):
        super().__init__()

        self.title(APP_TITLE)
        self.geometry(WINDOW_SIZE)
        self.configure(bg=BG_COLOR)
        
        # Shared Data
        self.selected_file_path = tk.StringVar()
        self.metadata_results = [] # Placeholder for analysis results
        self.current_metadata = {} # Placeholder for current metadata dict

        # Style Configuration
        self._configure_styles()

        # Container for frames
        self.container = tk.Frame(self, bg=BG_COLOR)
        self.container.pack(fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        
        # Initialize Frames
        for F in (FileSelectFrame, ResultsFrame, CustomMetadataFrame):
            page_name = F.__name__
            frame = F(parent=self.container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("FileSelectFrame")

    def _configure_styles(self):
        style = ttk.Style()
        style.theme_use("clam") # 'clam' usually allows more color customization than 'aqua' on Mac

        # Frame Style
        style.configure("TFrame", background=BG_COLOR)
        
        # Label Style
        style.configure("TLabel", background=BG_COLOR, foreground=FG_COLOR, font=FONT_MAIN)
        style.configure("Header.TLabel", font=FONT_HEADER, background=BG_COLOR, foreground=FG_COLOR)
        style.configure("Small.TLabel", font=FONT_SMALL, background=BG_COLOR, foreground=FG_COLOR)

        # Button Style
        style.configure("TButton", 
                        font=FONT_MAIN, 
                        background=BUTTON_BG, 
                        foreground=BUTTON_FG, 
                        borderwidth=0, 
                        focuscolor="none")
        style.map("TButton", 
                  background=[("active", ACCENT_COLOR)], 
                  foreground=[("active", "black")])

        # Entry Style
        style.configure("TEntry", fieldbackground="#505050", foreground="white", insertcolor="white")

    def show_frame(self, page_name):
        """Show a frame for the given page name."""
        frame = self.frames[page_name]
        frame.tkraise()
        # Optional: Call an 'on_show' method if the frame has it to refresh data
        if hasattr(frame, "on_show"):
            frame.on_show()

    def get_selected_file(self):
        return self.selected_file_path.get()
