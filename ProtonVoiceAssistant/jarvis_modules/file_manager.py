"""
Jarvis File Management Module
Handles file operations, searching, and organization
"""
import os
import json
from datetime import datetime
import glob

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


