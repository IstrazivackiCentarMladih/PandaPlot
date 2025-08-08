"""
Dataset model for managing data table items in the project.
"""

from datetime import datetime
from typing import Optional, Dict, Any
import pandas as pd
from pandaplot.models.project.items.item import Item


class Dataset(Item):
    """
    Represents a dataset item in the project.
    
    A dataset contains tabular data (typically from CSV or other data sources).
    It's part of the hierarchical project structure.
    """
    
    def __init__(self, id: Optional[str] = None, name: str = "", 
                 data: Optional[pd.DataFrame] = None, source_file: Optional[str] = None):
        # Call parent constructor with DATASET item type
        super().__init__(id, name)
        
        # Set dataset-specific attributes
        self.data: Optional[pd.DataFrame] = data
        self.source_file: Optional[str] = source_file
        self.column_info: Dict[str, Any] = {}
        
        # Initialize column info if data is provided
        if self.data is not None:
            self._update_column_info()
    
    def set_data(self, data: pd.DataFrame) -> None:
        """Set the dataset data and update metadata."""
        self.data = data
        self._update_column_info()
        self.update_modified_time()
    
    def update_name(self, new_name: str) -> None:
        """Update the dataset name and modification timestamp."""
        self.name = new_name
        self.update_modified_time()
    
    def _update_column_info(self) -> None:
        """Update column information metadata."""
        if self.data is not None:
            self.column_info = {
                'columns': list(self.data.columns),
                'dtypes': {col: str(dtype) for col, dtype in self.data.dtypes.items()},
                'shape': self.data.shape,
                'memory_usage': self.data.memory_usage(deep=True).sum()
            }
    
    def get_preview(self, n_rows: int = 5) -> Dict[str, Any]:
        """Get a preview of the dataset."""
        if self.data is None:
            return {'preview': None, 'message': 'No data available'}
        
        return {
            'preview': self.data.head(n_rows).to_dict('records'),
            'shape': self.data.shape,
            'columns': list(self.data.columns),
            'dtypes': {col: str(dtype) for col, dtype in self.data.dtypes.items()}
        }
    
    def get_summary_stats(self) -> Optional[Dict[str, Any]]:
        """Get summary statistics for the dataset."""
        if self.data is None:
            return None
        
        numeric_data = self.data.select_dtypes(include=['number'])
        if numeric_data.empty:
            return {'message': 'No numeric columns found'}
        
        return {
            'stats': numeric_data.describe().to_dict(),
            'missing_values': self.data.isnull().sum().to_dict(),
            'duplicates': self.data.duplicated().sum()
        }
    
    def search_data(self, query: str) -> bool:
        """Search for a query string in the dataset name or data."""
        query_lower = query.lower()
        
        # Search in name
        if query_lower in self.name.lower():
            return True
        
        # Search in column names
        if self.data is not None:
            for col in self.data.columns:
                if query_lower in str(col).lower():
                    return True
        
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert dataset to dictionary for serialization."""
        data = super().to_dict()
        data.update({
            'source_file': self.source_file,
            'column_info': self.column_info,
            'has_data': self.data is not None
        })
        
        # Note: We don't serialize the actual DataFrame data here
        # Data should be stored separately or reconstructed from source
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Dataset':
        """Create dataset from dictionary."""
        dataset = cls(
            id=data.get('id'),
            name=data.get('name', ''),
            source_file=data.get('source_file')
        )
        
        # Set inherited attributes
        dataset.parent_id = data.get('parent_id')
        dataset.created_at = data.get('created_at', datetime.now().isoformat())
        dataset.modified_at = data.get('modified_at', dataset.created_at)
        dataset.metadata = data.get('metadata', {})
        dataset.column_info = data.get('column_info', {})
        
        return dataset
        