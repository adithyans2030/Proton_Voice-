"""
Jarvis File Management Module
Handles file operations, searching, and organization
"""
import os
import json
from datetime import datetime
import glob
import shutil
import zipfile

class FileManager:
    def __init__(self):
        self.notes_path = os.path.join(os.path.dirname(__file__), "..", "data", "notes")
        self.ensure_notes_dir()
    
    def ensure_notes_dir(self):
        """Ensure notes directory exists"""
        os.makedirs(self.notes_path, exist_ok=True)
    
    def create_note(self, note_name, content):
        """Create a new note"""
        try:
            note_file = os.path.join(self.notes_path, f"{note_name}.txt")
            with open(note_file, 'w', encoding='utf-8') as f:
                f.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(content)
            return f"Note '{note_name}' created successfully"
        except Exception as e:
            return f"Failed to create note: {str(e)}"
    
    def read_note(self, note_name):
        """Read a note"""
        try:
            note_file = os.path.join(self.notes_path, f"{note_name}.txt")
            if not os.path.exists(note_file):
                return f"Note '{note_name}' not found."
            
            with open(note_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return f"Note '{note_name}':\n{content}"
        except Exception as e:
            return f"Failed to read note: {str(e)}"
    
    def list_notes(self):
        """List all notes"""
        try:
            notes = glob.glob(os.path.join(self.notes_path, "*.txt"))
            if not notes:
                return "No notes found."
            
            note_names = [os.path.basename(note).replace('.txt', '') for note in notes]
            result = f"You have {len(note_names)} note(s):\n"
            for name in note_names:
                result += f"- {name}\n"
            return result
        except Exception as e:
            return f"Failed to list notes: {str(e)}"
    
    def delete_note(self, note_name):
        """Delete a note"""
        try:
            note_file = os.path.join(self.notes_path, f"{note_name}.txt")
            if not os.path.exists(note_file):
                return f"Note '{note_name}' not found."
            
            os.remove(note_file)
            return f"Note '{note_name}' deleted successfully"
        except Exception as e:
            return f"Failed to delete note: {str(e)}"
    
    def search_files(self, search_path, query):
        """Search for files containing query in name"""
        try:
            if not os.path.exists(search_path):
                return f"Path '{search_path}' does not exist."
            
            found_files = []
            for root, dirs, files in os.walk(search_path):
                for file in files:
                    if query.lower() in file.lower():
                        found_files.append(os.path.join(root, file))
            
            if not found_files:
                return f"No files found matching '{query}' in {search_path}"
            
            result = f"Found {len(found_files)} file(s):\n"
            for file_path in found_files[:10]:  # Limit to 10 results
                result += f"- {file_path}\n"
            
            if len(found_files) > 10:
                result += f"... and {len(found_files) - 10} more"
            
            return result
        except Exception as e:
            return f"Failed to search files: {str(e)}"
    
    def get_file_info(self, file_path):
        """Get information about a file"""
        try:
            if not os.path.exists(file_path):
                return f"File '{file_path}' does not exist."
            
            stat = os.stat(file_path)
            size = stat.st_size
            modified = datetime.fromtimestamp(stat.st_mtime)
            
            size_mb = size / (1024 * 1024)
            return f"File: {os.path.basename(file_path)}\nSize: {size_mb:.2f} MB\nModified: {modified.strftime('%Y-%m-%d %H:%M:%S')}"
        except Exception as e:
            return f"Failed to get file info: {str(e)}"

    def file_ops(self, action, src, dest=None):
        """Perform move, copy, rename, or delete on files"""
        try:
            action = action.lower()
            if action in ["delete", "remove"]:
                if os.path.isfile(src):
                    os.remove(src)
                elif os.path.isdir(src):
                    shutil.rmtree(src)
                return f"Successfully deleted {src}"
            elif action in ["move", "rename"]:
                shutil.move(src, dest)
                return f"Successfully moved/renamed to {dest}"
            elif action == "copy":
                if os.path.isfile(src):
                    shutil.copy2(src, dest)
                else:
                    shutil.copytree(src, dest)
                return f"Successfully copied to {dest}"
            else:
                return f"Unknown file operation: {action}"
        except Exception as e:
            return f"File operation failed: {str(e)}"

    def zip_ops(self, action, zip_file, target=None):
        """Compress or extract zip files"""
        try:
            if action.lower() == "extract":
                if not target:
                    target = os.path.dirname(zip_file)
                with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                    zip_ref.extractall(target)
                return f"Successfully extracted to {target}"
            elif action.lower() == "compress":
                if not zip_file.endswith(".zip"):
                    zip_file += ".zip"
                with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
                    if os.path.isdir(target):
                        for root, dirs, files in os.walk(target):
                            for file in files:
                                file_path = os.path.join(root, file)
                                zip_ref.write(file_path, os.path.relpath(file_path, target))
                    else:
                        zip_ref.write(target, os.path.basename(target))
                return f"Successfully compressed {target} into {zip_file}"
        except Exception as e:
            return f"Zip operation failed: {str(e)}"

    def organize_downloads(self):
        """Organizes the user's Downloads folder by file extension"""
        try:
            downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
            categories = {
                "Images": [".jpg", ".jpeg", ".png", ".gif", ".webp"],
                "Documents": [".pdf", ".docx", ".txt", ".xlsx", ".pptx"],
                "Installers": [".exe", ".msi", ".iso"],
                "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"]
            }
            
            moved_count = 0
            for filename in os.listdir(downloads_dir):
                filepath = os.path.join(downloads_dir, filename)
                if not os.path.isfile(filepath):
                    continue
                    
                ext = os.path.splitext(filename)[1].lower()
                for category, extensions in categories.items():
                    if ext in extensions:
                        cat_dir = os.path.join(downloads_dir, category)
                        os.makedirs(cat_dir, exist_ok=True)
                        shutil.move(filepath, os.path.join(cat_dir, filename))
                        moved_count += 1
                        break
                        
            return f"Successfully organized {moved_count} files in Downloads."
        except Exception as e:
            return f"Failed to organize downloads: {str(e)}"

    def read_pdf(self, file_path):
        """Read and extract text from a local PDF file"""
        try:
            import PyPDF2
            if not os.path.exists(file_path):
                return f"File '{file_path}' does not exist."
                
            text = ""
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                num_pages = len(reader.pages)
                # Limit to first 10 pages to prevent token overflow
                limit = min(num_pages, 10)
                for i in range(limit):
                    page = reader.pages[i]
                    text += page.extract_text() + "\n"
                    
            if num_pages > 10:
                text += "\n[Note: Document truncated to first 10 pages.]"
                
            return f"Content of {os.path.basename(file_path)}:\n\n{text}"
        except ImportError:
            return "Error: PyPDF2 library not installed."
        except Exception as e:
            return f"Failed to read PDF: {str(e)}"
