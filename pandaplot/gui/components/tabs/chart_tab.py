"""
Chart tab widget for displaying and editing charts in the main tab container.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QFrame, QToolBar, QSizePolicy)
from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction, QKeySequence

from pandaplot.models.state.app_context import AppContext
from pandaplot.models.project.items.chart import Chart
from pandaplot.commands.project.item.rename_item_command import RenameItemCommand
from pandaplot.models.events.event_types import (
    UIEvents, ChartEvents, FitEvents
)
from pandaplot.models.events.mixins import EventBusComponentMixin

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
import pandas as pd


class ChartCanvas(FigureCanvas):
    """Custom matplotlib canvas for displaying charts."""
    
    def __init__(self, width=10, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor='white')
        super().__init__(self.fig)
        self.axes = self.fig.add_subplot(111)
        self.setParent(None)


class ChartEditorWidget(EventBusComponentMixin, QWidget):
    """
    A chart editor widget with configuration options and live preview.
    """
    
    def __init__(self, app_context: AppContext, chart: Chart, parent=None):
        super().__init__(event_bus=app_context.event_bus, parent=parent)
        self.app_context = app_context
        self.chart = chart
        self.is_modified = False
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_timer.setSingleShot(True)
        
        # Sample data for preview
        self.sample_data = self.generate_sample_data()
        
        self.setup_ui()
        self.setup_event_subscriptions()
        self.load_chart_config()
        self.setup_connections()
        self.update_chart()
    
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)
        
        # Header section with chart title and info
        self.create_header_section(layout)
        
        # Main content area with splitter
        self.create_content_section(layout)
        
        # Status bar
        self.create_status_section(layout)
    
    def setup_event_subscriptions(self):
        """Set up event subscriptions for the chart editor."""
        # Subscribe to relevant events if needed
        pass
    
    def create_header_section(self, layout):
        """Create the header section with chart title and metadata."""
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 6px;
                padding: 2px;
            }
        """)
        # Set fixed height to prevent expansion
        header_frame.setFixedHeight(60)
        header_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(8, 2, 8, 2)
        header_layout.setSpacing(2)
        
        # Title row
        title_layout = QHBoxLayout()
        
        title_label = QLabel("Chart Title:")
        title_label.setStyleSheet("font-weight: bold; color: #495057;")
        title_layout.addWidget(title_label)
        
        self.title_edit = QLineEdit(self.chart.name)
        self.title_edit.setStyleSheet("""
            QLineEdit {
                padding: 4px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QLineEdit:focus {
                border-color: #007bff;
                outline: none;
            }
        """)
        title_layout.addWidget(self.title_edit)
        
        self.save_title_btn = QPushButton("Save Title")
        self.save_title_btn.setEnabled(False)
        self.save_title_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                padding: 4px 8px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
        """)
        self.save_title_btn.clicked.connect(self.save_title)
        title_layout.addWidget(self.save_title_btn)
        
        header_layout.addLayout(title_layout)
        
        # Metadata row
        metadata_layout = QHBoxLayout()
        
        self.created_label = QLabel(f"Created: {self.chart.created_at[:19] if self.chart.created_at else 'Unknown'}")
        self.created_label.setStyleSheet("color: #6c757d; font-size: 12px;")
        metadata_layout.addWidget(self.created_label)
        
        metadata_layout.addStretch()
        
        self.modified_label = QLabel(f"Modified: {self.chart.modified_at[:19] if self.chart.modified_at else 'Unknown'}")
        self.modified_label.setStyleSheet("color: #6c757d; font-size: 12px;")
        metadata_layout.addWidget(self.modified_label)
        
        header_layout.addLayout(metadata_layout)
        
        layout.addWidget(header_frame)
    
    def create_content_section(self, layout):
        """Create the main content section with chart preview only."""
        # Chart preview section (full width, no configuration panel)
        self.create_chart_preview_section(layout)
    
    def create_chart_preview_section(self, layout):
        """Create the chart preview section."""
        preview_frame = QFrame()
        preview_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e9ecef;
                border-radius: 6px;
            }
        """)
        # Set size policy to expand and take all available space
        preview_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(10, 10, 10, 10)
        
        # Preview toolbar
        preview_toolbar = QToolBar()
        preview_toolbar.setStyleSheet("""
            QToolBar {
                background-color: #f8f9fa;
                border-bottom: 1px solid #e9ecef;
                padding: 4px;
            }
        """)
        
        # Add chart actions
        self.create_chart_toolbar_actions(preview_toolbar)
        preview_layout.addWidget(preview_toolbar)
        
        # Chart canvas
        self.chart_canvas = ChartCanvas(width=8, height=6, dpi=100)
        self.chart_canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        preview_layout.addWidget(self.chart_canvas)
        
        layout.addWidget(preview_frame)
    
    def create_status_section(self, layout):
        """Create the status section."""
        status_frame = QFrame()
        status_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 6px;
                padding: 1px;
            }
        """)
        # Set fixed height to prevent expansion
        status_frame.setFixedHeight(30)
        status_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(8, 1, 8, 1)
        status_layout.setSpacing(4)
        
        datasets = self.chart.get_all_datasets()
        dataset_text = f"Datasets: {', '.join(datasets)}" if datasets else "Sample Data"
        self.dataset_label = QLabel(dataset_text)
        self.dataset_label.setStyleSheet("color: #6c757d; font-size: 12px;")
        status_layout.addWidget(self.dataset_label)
        
        status_layout.addStretch()
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #28a745; font-size: 12px; font-weight: bold;")
        status_layout.addWidget(self.status_label)
        
        layout.addWidget(status_frame)
    
    def create_chart_toolbar_actions(self, toolbar):
        """Create toolbar actions for chart operations."""
        # Save chart action
        save_action = QAction("💾 Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_chart)
        toolbar.addAction(save_action)
        
        # Export action
        export_action = QAction("📤 Export", self)
        export_action.triggered.connect(self.export_chart)
        toolbar.addAction(export_action)
        
        toolbar.addSeparator()
        
        # Reset action
        reset_action = QAction("🔄 Reset", self)
        reset_action.triggered.connect(self.reset_chart)
        toolbar.addAction(reset_action)
    
    def setup_connections(self):
        """Set up widget connections."""
        self.title_edit.textChanged.connect(self.on_title_changed)
    
    def generate_sample_data(self):
        """Generate sample data for chart preview."""
        np.random.seed(42)  # For consistent sample data
        x = np.linspace(0, 10, 50)
        y1 = np.sin(x) + np.random.normal(0, 0.1, 50)
        y2 = np.cos(x) + np.random.normal(0, 0.1, 50)
        
        return pd.DataFrame({
            'x': x,
            'y1': y1,
            'y2': y2,
            'category': ['A', 'B'] * 25,
            'values': np.random.normal(0, 1, 50)
        })
    
    def load_chart_config(self):
        """Load chart configuration into UI controls."""
        # No configuration UI to load since it's now in the side panel
        pass
    
    def on_title_changed(self):
        """Handle title changes."""
        current_title = self.title_edit.text().strip()
        self.save_title_btn.setEnabled(current_title != self.chart.name and bool(current_title))
    
    def update_chart(self):
        """Update the chart preview."""
        try:
            # Clear the current plot
            self.chart_canvas.axes.clear()
            
            # If no data series, show sample data
            if not self.chart.data_series:
                # Use sample data for preview
                x_data = self.sample_data['x']
                y_data = self.sample_data['y1']
                
                if self.chart.chart_type == 'line':
                    self.chart_canvas.axes.plot(x_data, y_data, linewidth=2, marker='o', markersize=6)
                elif self.chart.chart_type == 'scatter':
                    self.chart_canvas.axes.scatter(x_data, y_data, s=60)
                elif self.chart.chart_type == 'bar':
                    self.chart_canvas.axes.bar(range(len(y_data[:10])), y_data[:10])
                elif self.chart.chart_type == 'hist':
                    self.chart_canvas.axes.hist(y_data, bins=20)
            else:
                # Plot actual data series from real datasets
                for i, series in enumerate(self.chart.data_series):
                    # Get the actual dataset from the project
                    project = self.app_context.get_app_state().current_project
                    if project:
                        dataset_item = project.find_item(series.dataset_id)
                        from pandaplot.models.project.items.dataset import Dataset
                        
                        if isinstance(dataset_item, Dataset) and dataset_item.data is not None:
                            # Use real data from the dataset
                            df = dataset_item.data
                            
                            # Check if the required columns exist
                            if series.x_column in df.columns and series.y_column in df.columns:
                                x_data = df[series.x_column]
                                y_data = df[series.y_column]
                                
                                # Plot based on chart type for regular data series
                                if self.chart.chart_type == 'line':
                                    self.chart_canvas.axes.plot(x_data, y_data, 
                                                               color=series.color,
                                                               linewidth=series.line_width,
                                                               marker='o' if series.marker_style == 'circle' else 's',
                                                               markersize=series.marker_size,
                                                               label=series.label,
                                                               alpha=1.0 if series.visible else 0.3)
                                elif self.chart.chart_type == 'scatter':
                                    self.chart_canvas.axes.scatter(x_data, y_data,
                                                                  c=series.color,
                                                                  s=series.marker_size*10,
                                                                  label=series.label,
                                                                  alpha=1.0 if series.visible else 0.3)
                                elif self.chart.chart_type == 'bar':
                                    self.chart_canvas.axes.bar(x_data, y_data,
                                                              color=series.color,
                                                              label=series.label,
                                                              alpha=1.0 if series.visible else 0.3)
                                elif self.chart.chart_type == 'hist':
                                    self.chart_canvas.axes.hist(y_data, bins=20,
                                                               color=series.color,
                                                               label=series.label,
                                                               alpha=0.7 if series.visible else 0.3)
                            else:
                                # Column not found - use sample data as fallback
                                x_data = self.sample_data['x']
                                y_col = 'y1' if i == 0 else 'y2'
                                y_data = self.sample_data[y_col] if y_col in self.sample_data.columns else self.sample_data['y1']
                                
                                if self.chart.chart_type == 'line':
                                    self.chart_canvas.axes.plot(x_data, y_data, 
                                                               color=series.color,
                                                               linewidth=series.line_width,
                                                               marker='o' if series.marker_style == 'circle' else 's',
                                                               markersize=series.marker_size,
                                                               label=f"{series.label} (Column not found)",
                                                               alpha=0.5, linestyle='--')
                        else:
                            # Dataset not found - use sample data as fallback
                            x_data = self.sample_data['x']
                            y_col = 'y1' if i == 0 else 'y2'
                            y_data = self.sample_data[y_col] if y_col in self.sample_data.columns else self.sample_data['y1']
                            
                            if self.chart.chart_type == 'line':
                                self.chart_canvas.axes.plot(x_data, y_data, 
                                                           color=series.color,
                                                           linewidth=series.line_width,
                                                           marker='o' if series.marker_style == 'circle' else 's',
                                                           markersize=series.marker_size,
                                                           label=f"{series.label} (Dataset not found)",
                                                           alpha=0.5, linestyle=':')
                
                # Plot fit data from chart.fit_data
                for i, fit in enumerate(self.chart.fit_data):
                    if fit.visible:
                        # Plot the fit line
                        line_style = '--' if fit.line_style == 'dashed' else '-'
                        self.chart_canvas.axes.plot(fit.x_data, fit.y_data,
                                                   color=fit.color,
                                                   linewidth=fit.line_width,
                                                   linestyle=line_style,
                                                   label=fit.label,
                                                   alpha=1.0)
            
            # Apply chart configuration
            config = self.chart.config
            self.chart_canvas.axes.set_title(config.get('title', self.chart.name), fontsize=14, fontweight='bold')
            self.chart_canvas.axes.set_xlabel(config.get('x_label', ''))
            self.chart_canvas.axes.set_ylabel(config.get('y_label', ''))
            
            if config.get('show_grid', True):
                self.chart_canvas.axes.grid(True, alpha=config.get('grid_alpha', 0.3))
            
            if config.get('show_legend', True) and (self.chart.data_series or self.chart.fit_data):
                self.chart_canvas.axes.legend(loc=config.get('legend_position', 'upper right'))
            
            # Refresh canvas
            self.chart_canvas.draw()
            
        except Exception as e:
            print(f"Error updating chart: {e}")
            self.update_status(f"Chart error: {str(e)}")
    
    def save_chart(self):
        """Save the chart configuration."""
        try:
            # Update modification time
            self.chart.update_modified_time()
            
            # Update UI
            self.is_modified = False
            self.update_status("Saved ✓")
            self.update_metadata()
            
            # Publish chart updated event
            self.publish_event(ChartEvents.CHART_UPDATED, {
                'chart_id': self.chart.id,
                'chart_name': self.chart.name
            })
            
            # Reset status after 2 seconds
            QTimer.singleShot(2000, lambda: self.update_status("Ready"))
            
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
    
    def save_title(self):
        """Save the chart title."""
        try:
            new_title = self.title_edit.text().strip()
            if not new_title:
                self.update_status("Error: Title cannot be empty")
                return
            
            if new_title == self.chart.name:
                return
            
            old_name = self.chart.name
            
            # Execute rename command
            command = RenameItemCommand(self.app_context, self.chart.id, new_title)
            self.app_context.get_command_executor().execute_command(command)
            
            # Update local chart object
            self.chart.update_name(new_title)
            
            # Update UI
            self.save_title_btn.setEnabled(False)
            self.update_status("Title saved ✓")
            self.update_metadata()
            
            # Publish chart renamed events
            self.publish_event(ChartEvents.CHART_UPDATED, {
                'chart_id': self.chart.id,
                'chart_name': new_title,
                'old_name': old_name
            })
            self.publish_event(UIEvents.TAB_TITLE_CHANGED, {
                'old_title': old_name,
                'new_title': new_title,
                'tab_type': 'chart'
            })
            
            # Reset status after 2 seconds
            QTimer.singleShot(2000, lambda: self.update_status("Ready"))
            
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
    
    def auto_save(self):
        """Auto-save the chart configuration."""
        if self.is_modified:
            self.save_chart()
    
    def export_chart(self):
        """Export the chart to file."""
        try:
            # Save the current figure
            filename = f"{self.chart.name}.png"
            self.chart_canvas.fig.savefig(filename, dpi=300, bbox_inches='tight')
            self.update_status(f"Exported to {filename} ✓")
            
            # Reset status after 3 seconds
            QTimer.singleShot(3000, lambda: self.update_status("Ready"))
            
        except Exception as e:
            self.update_status(f"Export error: {str(e)}")
    
    def reset_chart(self):
        """Reset chart to default configuration."""
        self.chart._init_default_config()
        self.update_chart()
        self.update_status("Reset to defaults ✓")
        
        # Reset status after 2 seconds
        QTimer.singleShot(2000, lambda: self.update_status("Ready"))
    
    def update_status(self, status: str):
        """Update the status label."""
        self.status_label.setText(status)
        
        # Update color based on status
        if "Modified" in status:
            self.status_label.setStyleSheet("color: #ffc107; font-size: 12px; font-weight: bold;")
        elif "Saved" in status or "Exported" in status:
            self.status_label.setStyleSheet("color: #28a745; font-size: 12px; font-weight: bold;")
        elif "Error" in status:
            self.status_label.setStyleSheet("color: #dc3545; font-size: 12px; font-weight: bold;")
        else:
            self.status_label.setStyleSheet("color: #6c757d; font-size: 12px; font-weight: bold;")
    
    def update_metadata(self):
        """Update the metadata labels."""
        self.modified_label.setText(f"Modified: {self.chart.modified_at[:19] if self.chart.modified_at else 'Unknown'}")
    
    def get_chart(self) -> Chart:
        """Get the current chart object."""
        return self.chart
    
    def refresh_chart(self):
        """Refresh the chart preview when configuration changes from external sources."""
        self.update_chart()
        self.update_metadata()
        
        # Update dataset label in status
        datasets = self.chart.get_all_datasets()
        dataset_text = f"Datasets: {', '.join(datasets)}" if datasets else "Sample Data"
        self.dataset_label.setText(dataset_text)


class ChartTab(EventBusComponentMixin, QWidget):
    """
    Main chart tab widget that contains the chart editor.
    """
    
    def __init__(self, app_context: AppContext, chart: Chart, parent=None):
        super().__init__(event_bus=app_context.event_bus, parent=parent)
        self.app_context = app_context
        self.chart = chart
        self.setup_ui()
        self.setup_event_subscriptions()
    
    def setup_ui(self):
        """Set up the chart tab UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create chart editor
        self.chart_editor = ChartEditorWidget(self.app_context, self.chart)
        
        layout.addWidget(self.chart_editor)
    
    def setup_event_subscriptions(self):
        """Set up event subscriptions for tab title changes and chart updates."""
        self.subscribe_to_event(UIEvents.TAB_TITLE_CHANGED, self.on_tab_title_changed)
        self.subscribe_to_event(ChartEvents.CHART_UPDATED, self.on_chart_updated)
        self.subscribe_to_event(FitEvents.FIT_APPLIED, self.on_fit_applied)
    
    def on_tab_title_changed(self, event_data: dict):
        """Handle tab title change events."""
        # Check if this title change is for our chart
        chart_name = event_data.get('new_title') 
        if chart_name and event_data.get('tab_type') == 'chart':
            # This is handled by the tab container - we just need to acknowledge the event
            pass
    
    def on_chart_updated(self, event_data: dict):
        """Handle chart update events from other components."""
        updated_chart_id = event_data.get('chart_id')
        
        # Only respond if this is our chart
        if updated_chart_id == self.chart.id:
            # Refresh the chart display
            if hasattr(self.chart_editor, 'refresh_chart'):
                self.chart_editor.refresh_chart()
                print(f"Chart tab refreshed for chart: {self.chart.name}")
    
    def on_fit_applied(self, event_data: dict):
        """Handle fit applied events to add fit curves to the chart."""
        fit_chart_id = event_data.get('chart_id')
        
        # Only respond if this is our chart
        if fit_chart_id == self.chart.id:
            fit_results = event_data.get('fit_results', {})
            fit_type = fit_results.get('fit_type', 'Unknown')
            source_dataset_name = event_data.get('dataset_name', 'Unknown')
            
            # Get the source dataset info from the fit results
            source_dataset_id = fit_results.get('source_dataset_id', '')
            source_x_column = fit_results.get('source_x_column', '')
            source_y_column = fit_results.get('source_y_column', '')
            
            # Generate unique color for fit line based on fit type
            fit_colors = {
                'Linear': '#ff0000',      # Red
                'Polynomial': '#00aa00',  # Green  
                'Exponential': '#0066cc', # Blue
                'Logarithmic': '#ff6600', # Orange
                'Power': '#cc00cc',       # Magenta
                'Gaussian': '#00cccc',    # Cyan
            }
            fit_color = fit_colors.get(fit_type, '#ff0000')  # Default to red
            
            # Add fit data directly to the chart
            import numpy as np
            x_fit = np.array(fit_results.get('x_fit', []))
            y_fit = np.array(fit_results.get('y_fit', []))
            
            fit_params = fit_results.get('fit_params', {})
            fit_stats = fit_results.get('fit_stats', {})
            
            self.chart.add_fit_data(
                source_dataset_id=source_dataset_id,
                source_x_column=source_x_column,
                source_y_column=source_y_column,
                fit_type=fit_type,
                x_data=x_fit,
                y_data=y_fit,
                label=f"{fit_type} Fit ({source_dataset_name})",
                color=fit_color,
                line_style="dashed",
                line_width=2.0,
                fit_params=fit_params,
                fit_stats=fit_stats
            )
            
            # Refresh the chart display to show the new fit
            if hasattr(self.chart_editor, 'refresh_chart'):
                self.chart_editor.refresh_chart()
            
            # Publish chart updated event to notify other components
            self.publish_event(ChartEvents.CHART_UPDATED, {
                'chart_id': self.chart.id,
                'chart': self.chart,
                'update_type': 'fit_added'
            })
    
    def get_tab_title(self) -> str:
        """Get the tab title."""
        return f"📈 {self.chart.name}"
    
    def get_chart(self) -> Chart:
        """Get the chart object."""
        return self.chart
    
    def refresh_chart(self):
        """Refresh the chart display when properties are updated externally."""
        if hasattr(self.chart_editor, 'refresh_chart'):
            self.chart_editor.refresh_chart()
