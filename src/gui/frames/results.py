import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import webbrowser

from ..config import BG_COLOR, APP_TITLE

from core.analyze_metadata import extract_metadata_auto
from core.modify_metadata.wipe_metadata import (
    wipe_metadata_docx,
    wipe_metadata_image,
    wipe_metadata_pdf,
)
from core.modify_metadata.default_metadata import (
    apply_default_docx_metadata,
    apply_default_image_metadata,
    apply_default_pdf_metadata,
)
from core.file_loader import load_file_info
from core.detect_extension import (
    extension_matches_mime,
    suggest_correct_extension
)

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
        
        # Hyperlink tag
        self.txt_console.tag_config("hyperlink", foreground="#4FC1FF", underline=1)
        self.txt_console.tag_bind("hyperlink", "<Button-1>", self.open_url)
        self.txt_console.tag_bind("hyperlink", "<Enter>", lambda e: self.txt_console.config(cursor="hand2"))
        self.txt_console.tag_bind("hyperlink", "<Leave>", lambda e: self.txt_console.config(cursor=""))

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

    def open_url(self, event):
        """Opens the clicked URL in the default browser."""
        try:
            index = self.txt_console.index(f"@{event.x},{event.y}")
            tags = self.txt_console.tag_names(index)
            if "hyperlink" in tags:
                # Get the text range of the link
                start = self.txt_console.tag_prevrange("hyperlink", index + "+1c")
                if start:
                    url = self.txt_console.get(start[0], start[1]).strip('"')
                    webbrowser.open(url)
        except Exception as e:
            print(f"Error opening URL: {e}")

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
            # Check for URL
            if data.startswith("http://") or data.startswith("https://"):
                self.append_log(f'"{data}"', "hyperlink")
            else:
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
