import tkinter as tk
from tkinter import ttk, messagebox
import os

from ..config import BG_COLOR, FG_COLOR, APP_TITLE

from core.modify_metadata.custom_metadata import (
    apply_custom_pdf_metadata,
    apply_custom_docx_metadata,
    apply_custom_image_metadata
)

class CustomMetadataFrame(tk.Frame):
    """
    Screen 3: Modify/Add Custom Metadata
    """
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_COLOR)
        self.controller = controller
        self.entries = [] # List of (key_entry, value_entry) tuples

        # Header
        header_frame = tk.Frame(self, bg=BG_COLOR)
        header_frame.pack(side="top", fill="x", padx=20, pady=20)
        
        lbl_title = ttk.Label(header_frame, text=APP_TITLE, style="Header.TLabel")
        lbl_title.pack()
        
        ttk.Button(header_frame, text="Browse files", command=self.change_file).pack(pady=5)
        
        self.lbl_path = ttk.Label(self, text="File path...", style="Small.TLabel")
        self.lbl_path.pack(pady=(0, 10))

        lbl_subtitle = ttk.Label(self, text="Setting Custom Metadata", font=("Helvetica", 16, "bold"))
        lbl_subtitle.pack(pady=10)

        # Scrollable Form Area
        self.canvas = tk.Canvas(self, bg=BG_COLOR, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=BG_COLOR)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="top", fill="both", expand=True, padx=40)
        self.scrollbar.place(relx=1.0, rely=0, relheight=1.0, anchor="ne") # Simple placement

        # Footer Buttons
        footer_frame = tk.Frame(self, bg=BG_COLOR)
        footer_frame.pack(side="bottom", fill="x", pady=20, padx=40)

        ttk.Button(footer_frame, text="Cancel", command=self.cancel).pack(side="left", padx=10)
        ttk.Button(footer_frame, text="Save", command=self.save_changes).pack(side="right", padx=10)
        
        self.btn_add = ttk.Button(self.scrollable_frame, text="+", width=3, command=self.add_field)

    def on_show(self):
        path = self.controller.get_selected_file()
        self.lbl_path.config(text=f"Editing: {path}")
        self.populate_fields()

    def change_file(self):
        self.controller.show_frame("FileSelectFrame")

    def populate_fields(self):
        # Clear existing
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.entries = []

        # Headers
        tk.Label(self.scrollable_frame, text="Key", bg=BG_COLOR, fg=FG_COLOR, font=("Helvetica", 12, "bold")).grid(row=0, column=0, padx=10, pady=5, sticky="w")
        tk.Label(self.scrollable_frame, text="Value", bg=BG_COLOR, fg=FG_COLOR, font=("Helvetica", 12, "bold")).grid(row=0, column=1, padx=10, pady=5, sticky="w")

        # Data rows
        row = 1
        for key, value in self.controller.current_metadata.items():
            self._create_row(row, key, value)
            row += 1
        
        self.next_row = row
        
        # Check file type to conditionally show Add button
        file_path = self.controller.get_selected_file()
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext in [".docx", ".doc"]:
            # For DOCX, we restrict adding new fields
            lbl_info = tk.Label(self.scrollable_frame, text="(DOCX: Only existing fields can be modified)", 
                                bg=BG_COLOR, fg="#A0A0A0", font=("Helvetica", 10, "italic"))
            lbl_info.grid(row=self.next_row, column=0, columnspan=2, pady=10)
        else:
            # For other files, allow adding new fields
            self.btn_add = ttk.Button(self.scrollable_frame, text="+", width=5, command=self.add_field)
            self.btn_add.grid(row=self.next_row, column=1, sticky="e", pady=10)

    def _create_row(self, row, key_text="", val_text=""):
        key_entry = ttk.Entry(self.scrollable_frame, width=20)
        key_entry.insert(0, str(key_text))
        key_entry.grid(row=row, column=0, padx=10, pady=5)

        val_entry = ttk.Entry(self.scrollable_frame, width=40)
        val_entry.insert(0, str(val_text))
        val_entry.grid(row=row, column=1, padx=10, pady=5)
        
        self.entries.append((key_entry, val_entry))

    def add_field(self):
        # Move add button down
        self.btn_add.grid_forget()
        self._create_row(self.next_row)
        self.next_row += 1
        self.btn_add.grid(row=self.next_row, column=1, sticky="e", pady=10)

    def cancel(self):
        self.controller.show_frame("ResultsFrame")

    def save_changes(self):
        # Collect data
        new_metadata = {}
        for k_ent, v_ent in self.entries:
            k = k_ent.get().strip()
            v = v_ent.get().strip()
            if k:
                new_metadata[k] = v
        
        file_path = self.controller.get_selected_file()
        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            output_path = None
            if ext == ".pdf":
                output_path = apply_custom_pdf_metadata(file_path, new_metadata)
            elif ext in [".docx", ".doc"]:
                output_path = apply_custom_docx_metadata(file_path, new_metadata)
            elif ext in [".jpg", ".jpeg", ".png", ".heic"]:
                output_path = apply_custom_image_metadata(file_path, new_metadata)
            else:
                messagebox.showerror("Error", f"Unsupported file format for modification: {ext}")
                return

            if output_path:
                messagebox.showinfo("Success", f"Metadata saved successfully!\n\nNew file created at:\n{output_path}")
                # Show new file with results
                self.controller.selected_file_path.set(str(output_path))
                self.controller.show_frame("ResultsFrame")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save metadata: {e}")
            print(e)
