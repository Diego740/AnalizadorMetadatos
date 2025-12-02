import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
from pathlib import Path

# Ensure src is in python path to import core modules
current_dir = Path(__file__).resolve().parent
src_dir = current_dir.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from core.analyze_metadata import extract_metadata_auto
from core.modify_metadata.custom_metadata import (
    apply_custom_pdf_metadata,
    apply_custom_docx_metadata,
    apply_custom_image_metadata
)
from core.modify_metadata.default_metadata import (
    apply_default_docx_metadata,
    apply_default_image_metadata,
    apply_default_pdf_metadata,
)
from core.modify_metadata.wipe_metadata import (
    wipe_metadata_docx,
    wipe_metadata_image,
    wipe_metadata_pdf,
)
from core.file_loader import load_file_info
from core.detect_extension import (
    extension_matches_mime,
    suggest_correct_extension
)

# --- Constants & Config ---
APP_TITLE = "ANALIZADOR METADATOS"
WINDOW_SIZE = "900x650"
BG_COLOR = "#404040"  # Dark grey background
FG_COLOR = "#FFFFFF"  # White text
ACCENT_COLOR = "#A0A0A0" # Light grey for accents/buttons
BUTTON_BG = "#606060"
BUTTON_FG = "#FFFFFF"
FONT_MAIN = ("Helvetica", 14)
FONT_HEADER = ("Helvetica", 24, "bold")
FONT_SMALL = ("Helvetica", 11)

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


class ResultsFrame(tk.Frame):
    """
    Screen 2: Analysis Results
    """
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_COLOR)
        self.controller = controller

        # Header
        header_frame = tk.Frame(self, bg=BG_COLOR)
        header_frame.pack(side="top", fill="x", padx=20, pady=20)
        
        lbl_title = ttk.Label(header_frame, text=APP_TITLE, style="Header.TLabel")
        lbl_title.pack()
        
        # Browse Button (Small, to change file)
        btn_browse = ttk.Button(header_frame, text="Browse files", command=self.change_file)
        btn_browse.pack(pady=5)

        # File Path Label
        self.lbl_path = ttk.Label(self, text="File path...", style="Small.TLabel")
        self.lbl_path.pack(pady=(0, 10))

        # Console Output Area
        self.console_frame = tk.Frame(self, bg=BG_COLOR)
        self.console_frame.pack(fill="both", expand=True, padx=40, pady=10)
        
        self.txt_console = tk.Text(self.console_frame, bg="#1E1E1E", fg="#D4D4D4", 
                                   font=("Menlo", 12), relief="flat", padx=10, pady=10)
        self.txt_console.pack(side="left", fill="both", expand=True)
        self.txt_console.config(state="disabled") # Make read-only by default
        
        scrollbar = ttk.Scrollbar(self.console_frame, orient="vertical", command=self.txt_console.yview)
        scrollbar.pack(side="right", fill="y")
        self.txt_console.config(yscrollcommand=scrollbar.set)
        
        # Configure tags for syntax highlighting
        self.txt_console.tag_config("key", foreground="#9CDCFE")       # Light Blue
        self.txt_console.tag_config("string", foreground="#CE9178")    # Orange/Brown
        self.txt_console.tag_config("number", foreground="#B5CEA8")    # Light Green
        self.txt_console.tag_config("bracket", foreground="#FFD700")   # Gold
        self.txt_console.tag_config("header", foreground="#569CD6", font=("Menlo", 12, "bold")) # Blue
        self.txt_console.tag_config("error", foreground="#F44747")     # Red
        self.txt_console.tag_config("warning", foreground="#CCA700")   # Dark Yellow
        self.txt_console.tag_config("info", foreground="#D4D4D4")      # Default

        # Buttons Area
        btn_frame = tk.Frame(self, bg=BG_COLOR)
        btn_frame.pack(side="bottom", fill="x", pady=30, padx=40)
        
        # Grid for buttons to align them nicely
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
        btn_frame.columnconfigure(2, weight=1)
        btn_frame.columnconfigure(3, weight=1)

        ttk.Button(btn_frame, text="Save Report", command=self.save_report).grid(row=0, column=0, padx=5, sticky="ew")
        ttk.Button(btn_frame, text="Delete All Metadata", command=self.delete_metadata).grid(row=0, column=1, padx=5, sticky="ew")
        ttk.Button(btn_frame, text="Set Default Metadata", command=self.set_default_metadata).grid(row=0, column=2, padx=5, sticky="ew")
        ttk.Button(btn_frame, text="Set Custom Metadata", command=self.go_to_custom).grid(row=0, column=3, padx=5, sticky="ew")

    def on_show(self):
        """Called when frame is shown."""
        path = self.controller.get_selected_file()
        self.lbl_path.config(text=f"Analyzing: {path}")
        self.run_analysis(path)

    def change_file(self):
        self.controller.show_frame("FileSelectFrame")

    def append_log(self, text, tag=None):
        """Helper to append text to read-only console."""
        self.txt_console.config(state="normal")
        self.txt_console.insert(tk.END, text, tag)
        self.txt_console.see(tk.END)
        self.txt_console.config(state="disabled")

    def clear_log(self):
        """Helper to clear console."""
        self.txt_console.config(state="normal")
        self.txt_console.delete("1.0", tk.END)
        self.txt_console.config(state="disabled")

    def format_json_colored(self, data, indent=0, override_tag=None):
        """Recursively formats dictionary as colored JSON."""
        spaces = " " * (indent * 4)
        
        if isinstance(data, dict):
            self.append_log("{\n", override_tag or "bracket")
            for i, (key, value) in enumerate(data.items()):
                self.append_log(spaces + "    ")
                
                # Special handling for security analysis
                current_tag = override_tag
                if key == "security_analysis":
                    # Check if it's actually suspicious before highlighting
                    if isinstance(value, dict) and value.get("is_suspicious"):
                        current_tag = "warning"
                        self.append_log(f'"{key}"', "warning")
                    else:
                        self.append_log(f'"{key}"', "key")
                else:
                    self.append_log(f'"{key}"', override_tag or "key")
                    
                self.append_log(": ", override_tag or "info")
                
                # Pass the current tag down (if it's warning, everything inside is warning)
                self.format_json_colored(value, indent + 1, current_tag)
                
                if i < len(data) - 1:
                    self.append_log(",\n", override_tag or "info")
                else:
                    self.append_log("\n", override_tag or "info")
            self.append_log(spaces + "}", override_tag or "bracket")
            
        elif isinstance(data, list):
            self.append_log("[\n", override_tag or "bracket")
            for i, item in enumerate(data):
                self.append_log(spaces + "    ")
                self.format_json_colored(item, indent + 1, override_tag)
                if i < len(data) - 1:
                    self.append_log(",\n", override_tag or "info")
                else:
                    self.append_log("\n", override_tag or "info")
            self.append_log(spaces + "]", override_tag or "bracket")
            
        elif isinstance(data, str):
            self.append_log(f'"{data}"', override_tag or "string")
            
        elif isinstance(data, (int, float)):
            self.append_log(f"{data}", override_tag or "number")
            
        elif data is None:
            self.append_log("null", override_tag or "number")
            
        else:
            self.append_log(str(data), override_tag or "info")

    def run_analysis(self, path):
        """Runs the actual analysis and updates console."""
        # Reset previous data
        self.clear_log()
        self.controller.current_metadata = {} 
        
        self.append_log(f"--- Analysis Results ---\n", "header")
        
        # Check for extension mismatch
        try:
            if not extension_matches_mime(path):
                suggestion = suggest_correct_extension(path)
                msg = f"Warning: The file extension does not match its content."
                if suggestion:
                    msg += f"\nSuggested extension: {suggestion}"
                
                # Log to console
                self.append_log(f"WARNING: {msg}\n", "warning")
                
                # Show popup
                messagebox.showwarning("Extension Mismatch", msg)
        except Exception as e:
            self.append_log(f"Error checking extension: {e}\n", "error")

        try:
            # Run the actual analysis
            result = extract_metadata_auto(path)
            
            # Store metadata for editing
            self.controller.current_metadata = result.get("metadata", {})
            
            # Display formatted JSON
            self.format_json_colored(result)
            self.append_log("\n")
            
            self.append_log("------------------------\n", "header")

        except Exception as e:
            self.append_log(f"Critical Error during analysis: {e}\n", "error")
            import traceback
            traceback.print_exc()

    def save_report(self):
        # Placeholder: In a real app, this would save the JSON content to a file
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(self.controller.current_metadata, f, indent=4, ensure_ascii=False)
                messagebox.showinfo("Success", f"Report saved to {path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save report: {e}")

    def delete_metadata(self):
        if not messagebox.askyesno("Confirm", "Are you sure you want to delete all metadata?"):
            return
            
        path = self.controller.get_selected_file()
        try:
            file_info = load_file_info(path)
            file_type = file_info["type"]
            
            new_path = None
            if file_type == "pdf":
                new_path = wipe_metadata_pdf(path)
            elif file_type == "docx":
                new_path = wipe_metadata_docx(path)
            elif file_type == "image":
                new_path = wipe_metadata_image(path)
            else:
                messagebox.showwarning("Unsupported", "We don't support wiping metadata for this file type yet.")
                return

            if new_path:
                messagebox.showinfo("Success", f"Clean file saved to:\n{new_path}")
                self.controller.selected_file_path.set(str(new_path))
                self.run_analysis(str(new_path)) # Refresh view
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to wipe metadata: {e}")

    def set_default_metadata(self):
        if not messagebox.askyesno("Confirm", "Apply default metadata template?"):
            return

        path = self.controller.get_selected_file()
        try:
            file_info = load_file_info(path)
            file_type = file_info["type"]
            
            new_path = None
            if file_type == "pdf":
                new_path = apply_default_pdf_metadata(path)
            elif file_type == "docx":
                new_path = apply_default_docx_metadata(path)
            elif file_type == "image":
                new_path = apply_default_image_metadata(path)
            else:
                messagebox.showwarning("Unsupported", "Unsupported file format for default metadata.")
                return

            if new_path:
                messagebox.showinfo("Success", f"File with default metadata created at:\n{new_path}")
                self.controller.selected_file_path.set(str(new_path))
                self.run_analysis(str(new_path)) # Refresh view
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply default metadata: {e}")

    def go_to_custom(self):
        self.controller.show_frame("CustomMetadataFrame")


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
                # Update controller to point to new file? Or keep original?
                # Usually better to switch to the new file so we see the results
                self.controller.selected_file_path.set(str(output_path))
                self.controller.show_frame("ResultsFrame")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save metadata: {e}")
            print(e)


if __name__ == "__main__":
    app = MetadataAnalyzerApp()
    app.mainloop()
