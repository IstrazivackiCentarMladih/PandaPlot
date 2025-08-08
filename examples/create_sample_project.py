"""
Example script showing how to use the new project structure system.
"""

import pandas as pd
import numpy as np
import os
from project_model import ProjectModel, ItemType, DatasetManager, ChartManager, NoteManager


def create_sample_project():
    """Create a sample project with multiple datasets, charts, and notes."""
    
    # Create project model and managers
    project = ProjectModel()
    project.project_name = "Sales Analysis Project"
    
    dataset_manager = DatasetManager()
    chart_manager = ChartManager()
    note_manager = NoteManager()
    
    # Create folder structure
    data_folder_id = project.create_item("Raw Data", ItemType.FOLDER)
    analysis_folder_id = project.create_item("Analysis", ItemType.FOLDER)
    reports_folder_id = project.create_item("Reports", ItemType.FOLDER)
    
    # Create datasets
    sales_dataset_id = project.create_item("Monthly Sales", ItemType.DATASET, data_folder_id)
    customer_dataset_id = project.create_item("Customer Data", ItemType.DATASET, data_folder_id)
    
    # Create sample data
    # Monthly Sales data
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
    sales_data = pd.DataFrame({
        'Month': months,
        'Sales': [12000, 15000, 13500, 16800, 18200, 21000],
        'Units': [120, 150, 135, 168, 182, 210],
        'Returns': [240, 300, 270, 336, 364, 420]
    })
    dataset_manager.add_dataset(sales_dataset_id, sales_data)
    
    # Customer data
    customer_data = pd.DataFrame({
        'Customer_ID': range(1, 101),
        'Age': np.random.randint(18, 65, 100),
        'Purchase_Amount': np.random.normal(500, 150, 100),
        'Satisfaction': np.random.randint(1, 6, 100)
    })
    dataset_manager.add_dataset(customer_dataset_id, customer_data)
    
    # Create charts
    sales_trend_id = project.create_item("Sales Trend", ItemType.CHART, analysis_folder_id)
    customer_dist_id = project.create_item("Customer Distribution", ItemType.CHART, analysis_folder_id)
    
    # Sample chart configurations
    sales_chart_config = {
        'chart_type': 'line',
        'x_column': 'Month',
        'y_column': 'Sales',
        'title': 'Monthly Sales Trend',
        'dataset_id': sales_dataset_id
    }
    chart_manager.add_chart(sales_trend_id, sales_chart_config)
    
    customer_chart_config = {
        'chart_type': 'histogram',
        'x_column': 'Age',
        'title': 'Customer Age Distribution',
        'dataset_id': customer_dataset_id
    }
    chart_manager.add_chart(customer_dist_id, customer_chart_config)
    
    # Create notes
    analysis_notes_id = project.create_item("Analysis Summary", ItemType.NOTE, reports_folder_id)
    methodology_id = project.create_item("Methodology", ItemType.NOTE, reports_folder_id)
    
    analysis_content = """# Sales Analysis Summary

## Key Findings:
- Sales show strong upward trend from January to June
- Peak sales occurred in June with $21,000
- Average monthly growth rate: ~12%
- Customer satisfaction average: 3.2/5

## Recommendations:
1. Investigate factors driving June peak
2. Focus on customer satisfaction improvement
3. Analyze return patterns for quality insights
"""

    methodology_content = """# Analysis Methodology

## Data Sources:
- Monthly sales data (6 months)
- Customer survey responses (100 customers)

## Techniques Used:
- Trend analysis
- Distribution analysis
- Statistical summaries

## Tools:
- Python/Pandas for data processing
- Matplotlib for visualization
- Statistical analysis
"""
    
    note_manager.add_note(analysis_notes_id, analysis_content)
    note_manager.add_note(methodology_id, methodology_content)
    
    # Save the project
    project_file = os.path.join(os.path.dirname(__file__), "sample_sales_project.pplot")
    project.save_project(project_file)
    
    print(f"Sample project created and saved to: {project_file}")
    print("\\nProject structure:")
    print_project_structure(project, project.root_id, 0)
    
    return project, dataset_manager, chart_manager, note_manager


def print_project_structure(project, item_id, indent_level):
    """Print the project structure in a tree format."""
    item = project.get_item(item_id)
    if not item:
        return
    
    indent = "  " * indent_level
    icon = {"folder": "📁", "dataset": "📊", "chart": "📈", "note": "📝"}.get(item.item_type.value, "📄")
    
    if item_id != project.root_id:  # Don't print root
        print(f"{indent}{icon} {item.name}")
    
    # Print children
    children = project.get_children(item_id)
    for child in children:
        print_project_structure(project, child.id, indent_level + 1)


if __name__ == "__main__":
    create_sample_project()
