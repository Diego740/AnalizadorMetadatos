import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from ..config import BG_COLOR, APP_TITLE, FONT_SMALL

class FileSelectFrame(tk.Frame):
    """
    Screen 1: File Selection
    """
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_COLOR)
        self.controller = controller

        # Layout configuration
        self.pack_propagate(False)
        
        # Center content
        content_frame = tk.Frame(self, bg=BG_COLOR)
        content_frame.place(relx=0.5, rely=0.5, anchor="center")

        # Title
        lbl_title = ttk.Label(content_frame, text=APP_TITLE, style="Header.TLabel")
        lbl_title.pack(pady=(0, 40))

        # Browse Button
        btn_browse = ttk.Button(content_frame, text="Browse files", command=self.browse_file)
        btn_browse.pack(pady=10, ipadx=20, ipady=5)

        # File Path Display
        self.ent_path = tk.Entry(content_frame, textvariable=self.controller.selected_file_path, 
                                 width=50, state="readonly", 
                                 bg="#505050", fg="white", 
                                 disabledbackground="#505050", disabledforeground="white",
                                 relief="flat", font=FONT_SMALL)
        self.ent_path.pack(pady=10, ipady=3)

        # Start Analysis Button
        btn_start = ttk.Button(content_frame, text="Start Analysis", command=self.start_analysis)
        btn_start.pack(pady=40, ipadx=20, ipady=5)
        
        # Footer
        lbl_footer = ttk.Label(self, text="Herramienta diseñada por Diego Aranda Gómez", style="Small.TLabel")
        lbl_footer.place(relx=0.5, rely=0.95, anchor="center")

    def browse_file(self):
        filename = filedialog.askopenfilename(title="Select a file to analyze")
        if filename:
            self.controller.selected_file_path.set(filename)

    def start_analysis(self):
        path = self.controller.get_selected_file()
        if not path:
            messagebox.showwarning("No File", "Please select a file first.")
            return
        
        # Here we would trigger the actual analysis
        print(f"Starting analysis for: {path}")
        self.controller.show_frame("ResultsFrame")
