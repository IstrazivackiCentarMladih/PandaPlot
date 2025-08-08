"""
Example extension showing how to add custom item types to the project structure.
This example adds support for "Report" items that can contain formatted analysis reports.
"""

from enum import Enum
from project_model import ItemType, ProjectModel
from file_tree_widget import FileTreeWidget


# Extend the ItemType enum (in a real implementation, you'd modify the original)
class ExtendedItemType(Enum):
    """Extended item types including custom report type."""
    FOLDER = "folder"
    DATASET = "dataset" 
    CHART = "chart"
    NOTE = "note"
    REPORT = "report"  # New custom type


class ReportManager:
    """Manages report items with structured content."""
    
    def __init__(self):
        self.reports = {}
    
    def add_report(self, item_id: str, report_data: dict):
        """Add a new report."""
        self.reports[item_id] = {
            'title': report_data.get('title', 'Untitled Report'),
            'summary': report_data.get('summary', ''),
            'sections': report_data.get('sections', []),
            'charts': report_data.get('charts', []),
            'datasets': report_data.get('datasets', []),
            'created_at': report_data.get('created_at', ''),
            'author': report_data.get('author', '')
        }
    
    def get_report(self, item_id: str):
        """Get report data."""
        return self.reports.get(item_id)
    
    def update_report(self, item_id: str, report_data: dict):
        """Update existing report."""
        if item_id in self.reports:
            self.reports[item_id].update(report_data)
    
    def remove_report(self, item_id: str):
        """Remove a report."""
        if item_id in self.reports:
            del self.reports[item_id]


class ExtendedFileTreeWidget(FileTreeWidget):
    """Extended file tree widget with support for custom report items."""
    
    def __init__(self, parent, project_model, config=None):
        super().__init__(parent, project_model, config)
        self.report_manager = ReportManager()
        
        # Add report button to toolbar
        self.add_report_button()
        
        # Register report handler
        self.register_report_handler()
    
    def add_report_button(self):
        """Add report button to toolbar."""
        import tkinter as tk
        from tkinter import ttk
        
        ttk.Button(
            self.toolbar_frame,
            text="Add Report",
            command=self.add_report,
            width=12
        ).pack(side=tk.LEFT, padx=2)
    
    def register_report_handler(self):
        """Register handler for report items."""
        # In a real implementation, you'd extend the ItemType enum properly
        # For this example, we'll handle it as a special note type
        pass
    
    def add_report(self):
        """Add a new report item."""
        from tkinter import simpledialog
        
        parent_id = self.get_selected_item_id()
        if parent_id:
            parent_item = self.project_model.get_item(parent_id)
            if parent_item and parent_item.item_type.value != 'folder':
                parent_id = parent_item.parent_id
        
        if not parent_id:
            parent_id = self.project_model.root_id
        
        name = simpledialog.askstring("New Report", "Enter report name:", initialvalue="New Report")
        if name:
            try:
                # Create as a special note type with report metadata
                item_id = self.project_model.create_item(
                    name, 
                    self.project_model.items[self.project_model.root_id].item_type.__class__.NOTE,  # Use NOTE type
                    parent_id,
                    {"item_subtype": "report"}  # Mark as report in metadata
                )
                
                # Initialize report data
                report_data = {
                    'title': name,
                    'summary': 'This is a new analysis report.',
                    'sections': [
                        {'title': 'Introduction', 'content': ''},
                        {'title': 'Methodology', 'content': ''},
                        {'title': 'Results', 'content': ''},
                        {'title': 'Conclusions', 'content': ''}
                    ],
                    'charts': [],
                    'datasets': []
                }
                self.report_manager.add_report(item_id, report_data)
                
                print(f"Created report: {name}")
                
            except ValueError as e:
                from tkinter import messagebox
                messagebox.showerror("Error", str(e))
    
    def _get_item_icon(self, item_type):
        """Override to add report icon."""
        # Check if item has report metadata
        # In a real implementation, you'd check the actual item data
        icons = {
            'folder': "📁",
            'dataset': "📊", 
            'chart': "📈",
            'note': "📝",
            'report': "📋"  # Report icon
        }
        return icons.get(item_type.value, "📄")


def demo_extended_system():
    """Demonstrate the extended project system with reports."""
    import tkinter as tk
    
    # Create test window
    root = tk.Tk()
    root.title("Extended Project System Demo")
    root.geometry("800x600")
    
    # Create project model
    project = ProjectModel()
    
    # Create some sample structure
    analysis_folder = project.create_item("Analysis Project", ItemType.FOLDER)
    data_folder = project.create_item("Data", ItemType.FOLDER, analysis_folder)
    
    # Add some datasets and charts
    project.create_item("Sales Data", ItemType.DATASET, data_folder)
    project.create_item("Sales Trend", ItemType.CHART, analysis_folder)
    
    # Create extended file tree
    tree_widget = ExtendedFileTreeWidget(root, project)
    tree_widget.pack(fill=tk.BOTH, expand=True)
    
    print("Extended project system demo running...")
    print("Try adding a report using the 'Add Report' button!")
    root.mainloop()


if __name__ == "__main__":
    demo_extended_system()
