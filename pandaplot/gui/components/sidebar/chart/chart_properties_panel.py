"""Chart properties side panel for configuring chart appearance and data."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QComboBox, QPushButton, QSpinBox, QDoubleSpinBox, QLineEdit, 
    QColorDialog, QCheckBox, QGroupBox, QScrollArea,
    QTabWidget, QListWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from typing import Optional, List

from pandaplot.models.chart.chart_configuration import (
    ChartConfiguration, ChartType, LineStyleType, MarkerType, 
    ScaleType, LegendPosition, LineStyle, MarkerStyle, AxisStyle, LegendStyle
)
from pandaplot.models.chart.chart_style_manager import ChartStyleManager
from pandaplot.models.events.mixins import EventBusComponentMixin
from pandaplot.models.events.event_types import UIEvents, ChartEvents
from pandaplot.models.state.app_context import AppContext


class ColorButton(QPushButton):
    """A button that displays and allows selection of colors."""
    
    colorChanged = Signal(str)
    
    def __init__(self, color: str = "#1f77b4", parent=None):
        super().__init__(parent)
        self._color = color
        self.setFixedSize(30, 25)
        self.clicked.connect(self._select_color)
        self._update_appearance()
    
    def set_color(self, color: str):
        """Set the button color."""
        self._color = color
        self._update_appearance()
        self.colorChanged.emit(color)
    
    def get_color(self) -> str:
        """Get the current color."""
        return self._color
    
    def _select_color(self):
        """Open color dialog to select a new color."""
        color = QColorDialog.getColor(QColor(self._color), self, "Select Color")
        if color.isValid():
            self.set_color(color.name())
    
    def _update_appearance(self):
        """Update button appearance to show current color."""
        self.setStyleSheet(f"QPushButton {{ background-color: {self._color}; border: 1px solid #ccc; }}")


class ChartPropertiesPanel(EventBusComponentMixin, QWidget):
    """Side panel for configuring chart properties."""
    
    chart_created = Signal(str)  # chart_id
    chart_updated = Signal(str)  # chart_id
    preview_requested = Signal(ChartConfiguration)
    
    def __init__(self, app_context: AppContext, parent=None):
        super().__init__(event_bus=app_context.event_bus, parent=parent)
        self.app_context = app_context
        self.command_executor = app_context.command_executor
        self.style_manager = ChartStyleManager()
        self.current_project = None
        self.current_chart_id: Optional[str] = None
        self.current_chart = None  # Current Chart object being edited
        self.datasets: List = []
        
        self._setup_ui()
        self._connect_signals()
        self._setup_event_subscriptions()
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title_label = QLabel("Chart Properties")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
        layout.addWidget(title_label)
        
        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        
        # Chart info section (basic chart settings)
        self._create_chart_info_section(content_layout)
        
        # Data Series Management section (moved above tabs)
        self._create_series_management_section(content_layout)
        
        # Tab widget for organizing other properties
        self.tab_widget = QTabWidget()
        
        # Style tab (simplified, no data source controls)
        self.style_tab = self._create_style_tab()
        self.tab_widget.addTab(self.style_tab, "Style")
        
        # Axes tab
        self.axes_tab = self._create_axes_tab()
        self.tab_widget.addTab(self.axes_tab, "Axes")
        
        # Legend tab
        self.legend_tab = self._create_legend_tab()
        self.tab_widget.addTab(self.legend_tab, "Legend")
        
        content_layout.addWidget(self.tab_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.preview_button = QPushButton("Preview")
        self.apply_button = QPushButton("Apply")
        self.reset_button = QPushButton("Reset")
        
        button_layout.addWidget(self.preview_button)
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.reset_button)
        
        content_layout.addLayout(button_layout)
        
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
    
    def _create_chart_info_section(self, layout):
        """Create the basic chart information section."""
        # Chart info group
        info_group = QGroupBox("Chart Information")
        info_layout = QGridLayout(info_group)
        
        info_layout.addWidget(QLabel("Title:"), 0, 0)
        self.title_edit = QLineEdit()
        info_layout.addWidget(self.title_edit, 0, 1)
        
        info_layout.addWidget(QLabel("Chart Type:"), 1, 0)
        self.chart_type_combo = QComboBox()
        for chart_type in ChartType:
            self.chart_type_combo.addItem(chart_type.value.title(), chart_type)
        info_layout.addWidget(self.chart_type_combo, 1, 1)
        
        layout.addWidget(info_group)
    
    def _create_series_management_section(self, layout):
        """Create the data series management section."""
        # Data Series group
        series_group = QGroupBox("Data Series")
        series_layout = QVBoxLayout(series_group)
        
        # Series list and controls
        series_controls_layout = QHBoxLayout()
        
        self.series_list = QListWidget()
        self.series_list.setMaximumHeight(120)
        self.series_list.currentRowChanged.connect(self._on_series_selection_changed)
        series_controls_layout.addWidget(self.series_list)
        
        # Series control buttons
        series_buttons_layout = QVBoxLayout()
        self.add_series_button = QPushButton("Add Series")
        self.add_series_button.clicked.connect(self._add_series)
        series_buttons_layout.addWidget(self.add_series_button)
        
        self.remove_series_button = QPushButton("Remove Series")
        self.remove_series_button.clicked.connect(self._remove_series)
        self.remove_series_button.setEnabled(False)
        series_buttons_layout.addWidget(self.remove_series_button)
        
        series_buttons_layout.addStretch()
        series_controls_layout.addLayout(series_buttons_layout)
        
        series_layout.addLayout(series_controls_layout)
        
        # Series configuration
        series_config_group = QGroupBox("Series Configuration")
        series_config_layout = QGridLayout(series_config_group)
        
        series_config_layout.addWidget(QLabel("Dataset:"), 0, 0)
        self.dataset_combo = QComboBox()
        series_config_layout.addWidget(self.dataset_combo, 0, 1)
        
        series_config_layout.addWidget(QLabel("X Column:"), 1, 0)
        self.x_column_combo = QComboBox()
        series_config_layout.addWidget(self.x_column_combo, 1, 1)
        
        series_config_layout.addWidget(QLabel("Y Column:"), 2, 0)
        self.y_column_combo = QComboBox()
        series_config_layout.addWidget(self.y_column_combo, 2, 1)
        
        series_config_layout.addWidget(QLabel("Label:"), 3, 0)
        self.series_label_edit = QLineEdit()
        series_config_layout.addWidget(self.series_label_edit, 3, 1)
        
        # Disable series configuration initially
        series_config_group.setEnabled(False)
        self.series_config_group = series_config_group
        
        series_layout.addWidget(series_config_group)
        layout.addWidget(series_group)
    
    def _create_style_tab(self) -> QWidget:
        """Create the style configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Line style group
        line_group = QGroupBox("Line Style")
        line_layout = QGridLayout(line_group)
        
        line_layout.addWidget(QLabel("Color:"), 0, 0)
        self.line_color_button = ColorButton()
        line_layout.addWidget(self.line_color_button, 0, 1)
        
        line_layout.addWidget(QLabel("Width:"), 1, 0)
        self.line_width_spin = QDoubleSpinBox()
        self.line_width_spin.setRange(0.1, 10.0)
        self.line_width_spin.setSingleStep(0.1)
        self.line_width_spin.setValue(2.0)
        line_layout.addWidget(self.line_width_spin, 1, 1)
        
        line_layout.addWidget(QLabel("Style:"), 2, 0)
        self.line_style_combo = QComboBox()
        for style in LineStyleType:
            self.line_style_combo.addItem(style.value.title(), style)
        line_layout.addWidget(self.line_style_combo, 2, 1)
        
        line_layout.addWidget(QLabel("Transparency:"), 3, 0)
        self.line_transparency_spin = QDoubleSpinBox()
        self.line_transparency_spin.setRange(0.0, 1.0)
        self.line_transparency_spin.setSingleStep(0.1)
        self.line_transparency_spin.setValue(1.0)
        line_layout.addWidget(self.line_transparency_spin, 3, 1)
        
        layout.addWidget(line_group)
        
        # Marker style group
        marker_group = QGroupBox("Marker Style")
        marker_layout = QGridLayout(marker_group)
        
        marker_layout.addWidget(QLabel("Type:"), 0, 0)
        self.marker_type_combo = QComboBox()
        for marker in MarkerType:
            self.marker_type_combo.addItem(marker.value.title(), marker)
        marker_layout.addWidget(self.marker_type_combo, 0, 1)
        
        marker_layout.addWidget(QLabel("Size:"), 1, 0)
        self.marker_size_spin = QDoubleSpinBox()
        self.marker_size_spin.setRange(1.0, 20.0)
        self.marker_size_spin.setValue(6.0)
        marker_layout.addWidget(self.marker_size_spin, 1, 1)
        
        marker_layout.addWidget(QLabel("Color:"), 2, 0)
        self.marker_color_button = ColorButton()
        marker_layout.addWidget(self.marker_color_button, 2, 1)
        
        marker_layout.addWidget(QLabel("Edge Color:"), 3, 0)
        self.marker_edge_color_button = ColorButton("#000000")
        marker_layout.addWidget(self.marker_edge_color_button, 3, 1)
        
        layout.addWidget(marker_group)
        
        layout.addStretch()
        return widget
    
    def _create_axes_tab(self) -> QWidget:
        """Create the axes configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # X Axis group
        x_axis_group = QGroupBox("X Axis")
        x_axis_layout = QGridLayout(x_axis_group)
        
        x_axis_layout.addWidget(QLabel("Label:"), 0, 0)
        self.x_label_edit = QLineEdit()
        x_axis_layout.addWidget(self.x_label_edit, 0, 1)
        
        x_axis_layout.addWidget(QLabel("Font Size:"), 1, 0)
        self.x_font_size_spin = QSpinBox()
        self.x_font_size_spin.setRange(6, 24)
        self.x_font_size_spin.setValue(12)
        x_axis_layout.addWidget(self.x_font_size_spin, 1, 1)
        
        x_axis_layout.addWidget(QLabel("Scale:"), 2, 0)
        self.x_scale_combo = QComboBox()
        for scale in ScaleType:
            self.x_scale_combo.addItem(scale.value.title(), scale)
        x_axis_layout.addWidget(self.x_scale_combo, 2, 1)
        
        self.x_grid_check = QCheckBox("Show Grid")
        self.x_grid_check.setChecked(True)
        x_axis_layout.addWidget(self.x_grid_check, 3, 0, 1, 2)
        
        layout.addWidget(x_axis_group)
        
        # Y Axis group
        y_axis_group = QGroupBox("Y Axis")
        y_axis_layout = QGridLayout(y_axis_group)
        
        y_axis_layout.addWidget(QLabel("Label:"), 0, 0)
        self.y_label_edit = QLineEdit()
        y_axis_layout.addWidget(self.y_label_edit, 0, 1)
        
        y_axis_layout.addWidget(QLabel("Font Size:"), 1, 0)
        self.y_font_size_spin = QSpinBox()
        self.y_font_size_spin.setRange(6, 24)
        self.y_font_size_spin.setValue(12)
        y_axis_layout.addWidget(self.y_font_size_spin, 1, 1)
        
        y_axis_layout.addWidget(QLabel("Scale:"), 2, 0)
        self.y_scale_combo = QComboBox()
        for scale in ScaleType:
            self.y_scale_combo.addItem(scale.value.title(), scale)
        y_axis_layout.addWidget(self.y_scale_combo, 2, 1)
        
        self.y_grid_check = QCheckBox("Show Grid")
        self.y_grid_check.setChecked(True)
        y_axis_layout.addWidget(self.y_grid_check, 3, 0, 1, 2)
        
        layout.addWidget(y_axis_group)
        
        layout.addStretch()
        return widget
    
    def _create_legend_tab(self) -> QWidget:
        """Create the legend configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Legend group
        legend_group = QGroupBox("Legend")
        legend_layout = QGridLayout(legend_group)
        
        self.legend_show_check = QCheckBox("Show Legend")
        self.legend_show_check.setChecked(True)
        legend_layout.addWidget(self.legend_show_check, 0, 0, 1, 2)
        
        legend_layout.addWidget(QLabel("Position:"), 1, 0)
        self.legend_position_combo = QComboBox()
        for position in LegendPosition:
            self.legend_position_combo.addItem(position.value.title(), position)
        legend_layout.addWidget(self.legend_position_combo, 1, 1)
        
        legend_layout.addWidget(QLabel("Font Size:"), 2, 0)
        self.legend_font_size_spin = QSpinBox()
        self.legend_font_size_spin.setRange(6, 18)
        self.legend_font_size_spin.setValue(10)
        legend_layout.addWidget(self.legend_font_size_spin, 2, 1)
        
        legend_layout.addWidget(QLabel("Background:"), 3, 0)
        self.legend_bg_color_button = ColorButton("#ffffff")
        legend_layout.addWidget(self.legend_bg_color_button, 3, 1)
        
        layout.addWidget(legend_group)
        
        layout.addStretch()
        return widget
    
    def _connect_signals(self):
        """Connect widget signals."""
        self.dataset_combo.currentTextChanged.connect(self._on_dataset_changed)
        self.preview_button.clicked.connect(self._on_preview)
        self.apply_button.clicked.connect(self._on_apply)
        self.reset_button.clicked.connect(self._on_reset)
        
        # Connect series configuration change signals
        self.x_column_combo.currentTextChanged.connect(self._on_series_config_changed)
        self.y_column_combo.currentTextChanged.connect(self._on_series_config_changed)
        self.series_label_edit.textChanged.connect(self._on_series_config_changed)
        
        # Connect style change signals
        self.line_color_button.colorChanged.connect(self._on_style_changed)
        self.line_width_spin.valueChanged.connect(self._on_style_changed)
        self.marker_size_spin.valueChanged.connect(self._on_style_changed)
    
    def _setup_event_subscriptions(self):
        """Set up event subscriptions for tab changes."""
        self.subscribe_to_event(UIEvents.TAB_CHANGED, self._on_tab_changed)
        self.subscribe_to_event(ChartEvents.CHART_UPDATED, self._on_chart_updated)
    
    def _on_tab_changed(self, event_data):
        """Handle tab change events to update context."""
        current_tab_type = event_data.get('tab_type')
        chart_id = event_data.get('chart_id')
        dataset_id = event_data.get('dataset_id')
        
        # Check if current tab is a chart tab
        if current_tab_type == 'chart' and chart_id:
            # Get the chart from the project using chart_id
            project = self.app_context.app_state.current_project
            if project is not None:
                chart = project.find_item(chart_id)
                if chart:
                    # Load the chart into the properties panel
                    self.load_chart_object(chart)
                    print(f"Chart properties panel updated with chart: {chart.name}")
                else:
                    print(f"Chart with ID {chart_id} not found in project")
            else:
                print("No current project available")
                        
        elif current_tab_type == 'dataset' and dataset_id:
            # For dataset tabs, provide context for creating new charts
            project = self.app_context.app_state.current_project
            if project is not None:
                dataset = project.find_item(dataset_id)
                if dataset:
                    self.set_project(project)
                    self.load_chart_object(None)  # Clear chart for new creation
                    print(f"Chart properties panel updated with project for dataset: {dataset.name}")
        else:
            # Clear chart properties panel context when no relevant tab is active
            self.load_chart_object(None)
            print("Chart properties panel context cleared")
    
    def _on_chart_updated(self, event_data):
        """Handle chart updated events to refresh the panel."""
        chart_id = event_data.get('chart_id')
        update_type = event_data.get('update_type', '')
        
        # If this is our current chart, refresh the display
        if self.current_chart and chart_id == self.current_chart.id:
            # Refresh the series list to show new series (like fit lines)
            if update_type in ['fit_added', 'series_added', 'series_updated']:
                self._update_series_list()
                print(f"Chart properties panel refreshed for update: {update_type}")
    
    def _add_series(self):
        """Add a new data series."""
        if not self.current_chart:
            return
        
        # Create a new series with default values
        dataset_id = self.dataset_combo.currentData() if self.dataset_combo.count() > 0 else ""
        dataset_name = self.dataset_combo.currentText() if self.dataset_combo.count() > 0 else ""
        x_column = self.x_column_combo.currentText() if self.x_column_combo.count() > 0 else ""
        y_column = self.y_column_combo.currentText() if self.y_column_combo.count() > 0 else ""
        
        if dataset_id and x_column and y_column:
            # Add series to chart
            self.current_chart.add_data_series(
                dataset_id=dataset_id,
                x_column=x_column,
                y_column=y_column,
                label=f"{dataset_name}:{y_column}",
                color=self._get_next_series_color()
            )
            
            # Update the series list
            self._update_series_list()
            
            # Select the new series
            self.series_list.setCurrentRow(len(self.current_chart.data_series) - 1)
    
    def _remove_series(self):
        """Remove the selected data series."""
        if not self.current_chart or not self.current_chart.data_series:
            return
        
        current_row = self.series_list.currentRow()
        if current_row >= 0 and current_row < len(self.current_chart.data_series):
            # Remove the series
            self.current_chart.remove_data_series(current_row)
            
            # Update the series list
            self._update_series_list()
            
            # Select previous series or disable if no series left
            if self.current_chart.data_series:
                new_row = min(current_row, len(self.current_chart.data_series) - 1)
                self.series_list.setCurrentRow(new_row)
            else:
                self.series_config_group.setEnabled(False)
    
    def _on_series_selection_changed(self, current_row: int):
        """Handle series selection change."""
        if not self.current_chart or current_row < 0:
            self.series_config_group.setEnabled(False)
            return
        
        total_series = len(self.current_chart.data_series)
        total_items = total_series + len(self.current_chart.fit_data)
        
        if current_row >= total_items:
            self.series_config_group.setEnabled(False)
            return
        
        # Enable configuration
        self.series_config_group.setEnabled(True)
        
        if current_row < total_series:
            # This is a data series
            series = self.current_chart.data_series[current_row]
            self._load_series_into_controls(series)
        else:
            # This is fit data
            fit_index = current_row - total_series
            fit = self.current_chart.fit_data[fit_index]
            self._load_fit_into_controls(fit)
        
        # Enable/disable remove button
        self.remove_series_button.setEnabled(total_items > 0)
    
    def _on_series_config_changed(self):
        """Handle series configuration changes."""
        if not self.current_chart:
            return
        
        current_row = self.series_list.currentRow()
        if current_row < 0:
            return
        
        total_series = len(self.current_chart.data_series)
        
        if current_row < total_series:
            # Updating a data series
            if current_row >= len(self.current_chart.data_series):
                return
            
            series = self.current_chart.data_series[current_row]
            
            # Update series properties
            if self.dataset_combo.currentData():
                series.dataset_id = self.dataset_combo.currentData()
            series.x_column = self.x_column_combo.currentText()
            series.y_column = self.y_column_combo.currentText()
            series.label = self.series_label_edit.text()
        else:
            # Updating fit data (only label is editable)
            fit_index = current_row - total_series
            if fit_index >= len(self.current_chart.fit_data):
                return
            
            fit = self.current_chart.fit_data[fit_index]
            fit.label = self.series_label_edit.text()
        
        # Update the series list display
        self._update_series_list()
        self.series_list.setCurrentRow(current_row)  # Maintain selection
    
    def _on_style_changed(self):
        """Handle style changes."""
        if not self.current_chart:
            return
        
        current_row = self.series_list.currentRow()
        if current_row < 0:
            return
        
        total_series = len(self.current_chart.data_series)
        
        if current_row < total_series:
            # Updating a data series
            if current_row >= len(self.current_chart.data_series):
                return
            
            series = self.current_chart.data_series[current_row]
            series.color = self.line_color_button.get_color()
            series.line_width = self.line_width_spin.value()
            series.marker_size = self.marker_size_spin.value()
        else:
            # Updating fit data
            fit_index = current_row - total_series
            if fit_index >= len(self.current_chart.fit_data):
                return
            
            fit = self.current_chart.fit_data[fit_index]
            fit.color = self.line_color_button.get_color()
            fit.line_width = self.line_width_spin.value()
            # Note: fit data doesn't use marker_size
    
    def _update_series_list(self):
        """Update the series list widget."""
        self.series_list.clear()
        
        if not self.current_chart:
            return
        
        # Add data series
        for i, series in enumerate(self.current_chart.data_series):
            label = series.label or f"Series {i+1}"
            self.series_list.addItem(label)
        
        # Add fit data as separate items
        for i, fit in enumerate(self.current_chart.fit_data):
            label = f"🔧 {fit.label}" # Wrench emoji to distinguish fit data
            self.series_list.addItem(label)
        
        # Enable/disable controls
        has_items = len(self.current_chart.data_series) > 0 or len(self.current_chart.fit_data) > 0
        self.remove_series_button.setEnabled(has_items)
    
    def _load_series_into_controls(self, series):
        """Load a data series into the configuration controls."""
        # Enable all controls for series editing
        self._reset_controls_for_series()
        
        # Set dataset
        for i in range(self.dataset_combo.count()):
            if self.dataset_combo.itemData(i) == series.dataset_id:
                self.dataset_combo.setCurrentIndex(i)
                break
        
        # Set columns
        x_index = self.x_column_combo.findText(series.x_column)
        if x_index >= 0:
            self.x_column_combo.setCurrentIndex(x_index)
        
        y_index = self.y_column_combo.findText(series.y_column)
        if y_index >= 0:
            self.y_column_combo.setCurrentIndex(y_index)
        
        # Set label
        self.series_label_edit.setText(series.label)
        
        # Update style controls to reflect this series
        self.line_color_button.set_color(series.color)
        self.line_width_spin.setValue(series.line_width)
        self.marker_size_spin.setValue(series.marker_size)
    
    def _load_fit_into_controls(self, fit):
        """Load fit data into the configuration controls."""
        # For fit data, disable dataset/column controls since they're not editable
        self.dataset_combo.setEnabled(False)
        self.x_column_combo.setEnabled(False)
        self.y_column_combo.setEnabled(False)
        
        # Show fit info in the label
        self.series_label_edit.setText(fit.label)
        
        # Update style controls to reflect this fit
        self.line_color_button.set_color(fit.color)
        self.line_width_spin.setValue(fit.line_width)
        self.marker_size_spin.setValue(0.0)  # Fit lines typically don't have markers
    
    def _reset_controls_for_series(self):
        """Reset controls for editing regular data series."""
        self.dataset_combo.setEnabled(True)
        self.x_column_combo.setEnabled(True)
        self.y_column_combo.setEnabled(True)
    
    def _get_next_series_color(self) -> str:
        """Get the next color for a new series."""
        colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", 
                 "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]
        
        if not self.current_chart or not self.current_chart.data_series:
            return colors[0]
        
        return colors[len(self.current_chart.data_series) % len(colors)]

    def set_project(self, project):
        """Set the current project."""
        self.current_project = project
        self._update_datasets()
    
    def _update_datasets(self):
        """Update the available datasets."""
        self.dataset_combo.clear()
        self.datasets = []
        
        if self.current_project:
            # Iterate through all items in the project to find datasets
            from pandaplot.models.project.items.dataset import Dataset
            for item in self.current_project.get_all_items():
                if isinstance(item, Dataset):
                    self.dataset_combo.addItem(item.name, item.id)
                    self.datasets.append(item)
    
    def _on_dataset_changed(self):
        """Handle dataset selection change."""
        dataset_id = self.dataset_combo.currentData()
        if dataset_id and self.current_project:
            dataset = self.current_project.find_item(dataset_id)
            from pandaplot.models.project.items.dataset import Dataset
            if isinstance(dataset, Dataset) and dataset.data is not None:
                columns = list(dataset.data.columns)
                
                # Update column combos
                self.x_column_combo.clear()
                self.y_column_combo.clear()
                
                for column in columns:
                    self.x_column_combo.addItem(column)
                    self.y_column_combo.addItem(column)
                
                # Set defaults if possible
                if len(columns) >= 2:
                    self.x_column_combo.setCurrentIndex(0)
                    self.y_column_combo.setCurrentIndex(1)
    
    def _get_current_configuration(self) -> ChartConfiguration:
        """Get the current configuration from UI."""
        config = ChartConfiguration()
        
        # Basic info
        config.title = self.title_edit.text()
        config.chart_type = self.chart_type_combo.currentData() or ChartType.LINE
        config.dataset_id = self.dataset_combo.currentData() or ""
        config.x_column = self.x_column_combo.currentText()
        config.y_column = self.y_column_combo.currentText()
        
        # Line style
        config.line_style = LineStyle(
            color=self.line_color_button.get_color(),
            width=self.line_width_spin.value(),
            style=self.line_style_combo.currentData() or LineStyleType.SOLID,
            transparency=self.line_transparency_spin.value()
        )
        
        # Marker style
        config.marker_style = MarkerStyle(
            type=self.marker_type_combo.currentData() or MarkerType.CIRCLE,
            size=self.marker_size_spin.value(),
            color=self.marker_color_button.get_color(),
            edge_color=self.marker_edge_color_button.get_color()
        )
        
        # Axes
        config.x_axis = AxisStyle(
            label=self.x_label_edit.text(),
            font_size=self.x_font_size_spin.value(),
            scale=self.x_scale_combo.currentData() or ScaleType.LINEAR,
            show_grid=self.x_grid_check.isChecked()
        )
        
        config.y_axis = AxisStyle(
            label=self.y_label_edit.text(),
            font_size=self.y_font_size_spin.value(),
            scale=self.y_scale_combo.currentData() or ScaleType.LINEAR,
            show_grid=self.y_grid_check.isChecked()
        )
        
        # Legend
        config.legend = LegendStyle(
            show=self.legend_show_check.isChecked(),
            position=self.legend_position_combo.currentData() or LegendPosition.UPPER_RIGHT,
            font_size=self.legend_font_size_spin.value(),
            background_color=self.legend_bg_color_button.get_color()
        )
        
        return config
    
    def _on_preview(self):
        """Handle preview button click."""
        config = self._get_current_configuration()
        # Publish chart preview event
        self.publish_event(ChartEvents.CHART_PREVIEW_REQUESTED, {
            'chart_config': config,
            'chart_id': self.current_chart_id
        })
    
    def _on_apply(self):
        """Handle apply button click."""
        if self.current_chart:
            # Apply changes to the current chart object
            self.apply_to_chart(self.current_chart)
            
            # Publish chart updated event
            self.publish_event(ChartEvents.CHART_UPDATED, {
                'chart_id': self.current_chart.id,
                'chart': self.current_chart
            })
    
    def _on_reset(self):
        """Handle reset button click."""
        self.load_chart(None)
    
    def load_chart(self, chart_id: Optional[str]):
        """Load a chart configuration into the panel.
        
        Args:
            chart_id: The chart ID to load, or None for new chart
        """
        self.current_chart_id = chart_id
        
        if chart_id and self.current_project:
            # Load existing chart
            if hasattr(self.current_project, 'charts') and chart_id in self.current_project.charts:
                chart_dict = self.current_project.charts[chart_id]
                config = ChartConfiguration.from_dict(chart_dict)
                self._load_configuration(config)
            else:
                self._load_default_configuration()
        else:
            # New chart
            self._load_default_configuration()
    
    def load_chart_object(self, chart):
        """Load a Chart object into the panel for editing.
        
        Args:
            chart: Chart object to load, or None to clear
        """
        self.current_chart = chart
        
        if chart:
            # Load basic info
            self.title_edit.setText(chart.config.get('title', chart.name))
            
            # Set chart type
            chart_type_map = {
                'line': ChartType.LINE,
                'scatter': ChartType.SCATTER,
                'bar': ChartType.BAR,
                'hist': ChartType.HISTOGRAM,
                'box': ChartType.BOX,
                'violin': ChartType.VIOLIN
            }
            chart_type = chart_type_map.get(chart.chart_type, ChartType.LINE)
            for i in range(self.chart_type_combo.count()):
                if self.chart_type_combo.itemData(i) == chart_type:
                    self.chart_type_combo.setCurrentIndex(i)
                    break
            
            # Update series list
            self._update_series_list()
            
            # If there are data series, select the first one
            if chart.data_series:
                self.series_list.setCurrentRow(0)
                self._load_series_into_controls(chart.data_series[0])
                self.series_config_group.setEnabled(True)
                
                # Set style from first series for the style tab
                first_series = chart.data_series[0]
                self.line_color_button.set_color(first_series.color)
                self.line_width_spin.setValue(first_series.line_width)
                self.marker_size_spin.setValue(first_series.marker_size)
            else:
                self.series_config_group.setEnabled(False)
            
            # Load configuration
            config = chart.config
            self.x_label_edit.setText(config.get('x_label', ''))
            self.y_label_edit.setText(config.get('y_label', ''))
            self.x_grid_check.setChecked(config.get('show_grid', True))
            self.y_grid_check.setChecked(config.get('show_grid', True))
            self.legend_show_check.setChecked(config.get('show_legend', True))
            
        else:
            # Clear/default values
            self._load_default_configuration()
            self.series_list.clear()
            self.series_config_group.setEnabled(False)
    
    def apply_to_chart(self, chart):
        """Apply current panel settings to a Chart object.
        
        Args:
            chart: Chart object to update
        """
        if not chart:
            return
        
        # Update basic chart properties
        chart.config['title'] = self.title_edit.text()
        chart.config['x_label'] = self.x_label_edit.text()
        chart.config['y_label'] = self.y_label_edit.text()
        chart.config['show_grid'] = self.x_grid_check.isChecked() and self.y_grid_check.isChecked()
        chart.config['show_legend'] = self.legend_show_check.isChecked()
        
        # Update chart type
        chart_type_map = {
            ChartType.LINE: 'line',
            ChartType.SCATTER: 'scatter',
            ChartType.BAR: 'bar',
            ChartType.HISTOGRAM: 'hist',
            ChartType.BOX: 'box',
            ChartType.VIOLIN: 'violin'
        }
        chart_type = self.chart_type_combo.currentData()
        if chart_type in chart_type_map:
            chart.chart_type = chart_type_map[chart_type]
        
        # Update style properties for all series (apply current style to all)
        style_updates = {
            'color': self.line_color_button.get_color(),
            'line_width': self.line_width_spin.value(),
            'marker_size': self.marker_size_spin.value()
        }
        
        # Apply style updates to the currently selected series only
        current_row = self.series_list.currentRow()
        if (current_row >= 0 and current_row < len(chart.data_series)):
            series = chart.data_series[current_row]
            print(f"DEBUG: Updating series {current_row}: {series.label} (dataset_id: {series.dataset_id})")
            print(f"DEBUG: Style updates: {style_updates}")
            for key, value in style_updates.items():
                if hasattr(series, key):
                    print(f"DEBUG: Setting {key} = {value}")
                    setattr(series, key, value)
        
        # If no series exist but we have configuration, create a default series
        if not chart.data_series:
            dataset_id = self.dataset_combo.currentData()
            dataset_name = self.dataset_combo.currentText()
            x_column = self.x_column_combo.currentText()
            y_column = self.y_column_combo.currentText()
            
            if dataset_id and x_column and y_column:
                chart.add_data_series(
                    dataset_id=dataset_id,
                    x_column=x_column,
                    y_column=y_column,
                    color=self.line_color_button.get_color(),
                    line_width=self.line_width_spin.value(),
                    marker_size=self.marker_size_spin.value(),
                    label=f"{dataset_name}:{y_column}"
                )
        
        chart.update_modified_time()
    
    def _load_configuration(self, config: ChartConfiguration):
        """Load a configuration into the UI widgets."""
        # Basic info
        self.title_edit.setText(config.title)
        
        # Find and set chart type
        for i in range(self.chart_type_combo.count()):
            if self.chart_type_combo.itemData(i) == config.chart_type:
                self.chart_type_combo.setCurrentIndex(i)
                break
        
        # Find and set dataset
        for i in range(self.dataset_combo.count()):
            if self.dataset_combo.itemData(i) == config.dataset_id:
                self.dataset_combo.setCurrentIndex(i)
                break
        
        # Set columns
        x_index = self.x_column_combo.findText(config.x_column)
        if x_index >= 0:
            self.x_column_combo.setCurrentIndex(x_index)
        
        y_index = self.y_column_combo.findText(config.y_column)
        if y_index >= 0:
            self.y_column_combo.setCurrentIndex(y_index)
        
        # Line style
        self.line_color_button.set_color(config.line_style.color)
        self.line_width_spin.setValue(config.line_style.width)
        
        for i in range(self.line_style_combo.count()):
            if self.line_style_combo.itemData(i) == config.line_style.style:
                self.line_style_combo.setCurrentIndex(i)
                break
        
        self.line_transparency_spin.setValue(config.line_style.transparency)
        
        # Marker style
        for i in range(self.marker_type_combo.count()):
            if self.marker_type_combo.itemData(i) == config.marker_style.type:
                self.marker_type_combo.setCurrentIndex(i)
                break
        
        self.marker_size_spin.setValue(config.marker_style.size)
        self.marker_color_button.set_color(config.marker_style.color)
        self.marker_edge_color_button.set_color(config.marker_style.edge_color)
        
        # Axes
        self.x_label_edit.setText(config.x_axis.label)
        self.x_font_size_spin.setValue(config.x_axis.font_size)
        self.x_grid_check.setChecked(config.x_axis.show_grid)
        
        for i in range(self.x_scale_combo.count()):
            if self.x_scale_combo.itemData(i) == config.x_axis.scale:
                self.x_scale_combo.setCurrentIndex(i)
                break
        
        self.y_label_edit.setText(config.y_axis.label)
        self.y_font_size_spin.setValue(config.y_axis.font_size)
        self.y_grid_check.setChecked(config.y_axis.show_grid)
        
        for i in range(self.y_scale_combo.count()):
            if self.y_scale_combo.itemData(i) == config.y_axis.scale:
                self.y_scale_combo.setCurrentIndex(i)
                break
        
        # Legend
        self.legend_show_check.setChecked(config.legend.show)
        self.legend_font_size_spin.setValue(config.legend.font_size)
        self.legend_bg_color_button.set_color(config.legend.background_color)
        
        for i in range(self.legend_position_combo.count()):
            if self.legend_position_combo.itemData(i) == config.legend.position:
                self.legend_position_combo.setCurrentIndex(i)
                break
    
    def _load_default_configuration(self):
        """Load default configuration."""
        config = self.style_manager.get_default_configuration()
        self._load_configuration(config)
