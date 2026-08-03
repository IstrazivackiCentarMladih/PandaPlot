"""Curve fitting panel for performing regression analysis on chart data."""
import logging
from dataclasses import replace
from typing import Optional, override

import pandas as pd
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from pandaplot.gui.core.widget_extension import PWidget
from pandaplot.models.events import FitEvents, ChartEvents, UIEvents
from pandaplot.models.project.items import Dataset
from pandaplot.models.state import AppContext
from pandaplot.services.fit.fit_service import FitService
from pandaplot.services.theme import ThemeManager


class FitPanel(PWidget):
    """Side panel for performing curve fitting on chart data."""

    fit_completed = Signal(dict)  # Emitted when fit is completed with results
    fit_applied = Signal(dict)   # Emitted when fit should be applied to chart

    def __init__(self, app_context: AppContext, parent: Optional[QWidget]=None):
        super().__init__(app_context=app_context, parent=parent)
        self.fit_command=FitService(self)
        self.logger = logging.getLogger(self.__class__.__name__)

        self.app_context = app_context
        self.current_project = None
        self.current_chart = None
        self.fit_command.fit_results = None
        self.datasets = []

        # Check scipy availability lazily (only when FitPanel is instantiated)
        self.scipy_available = self._check_scipy_available()

        self._initialize()
        self._connect_signals()

        if not self.scipy_available:
            self._show_scipy_warning()

    def _check_scipy_available(self) -> bool:
        """Check if scipy is installed without importing it (import is deferred to fit time)."""
        import importlib.util
        return importlib.util.find_spec("scipy") is not None
    
    @override
    def _init_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        self.title_label = QLabel("Curve Fitting")
        layout.addWidget(self.title_label)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        
        # Data source section
        self._create_data_source_section(content_layout)
        
        # Fit configuration section
        self._create_fit_config_section(content_layout)
        
        # Results section
        self._create_results_section(content_layout)
        
        # Action buttons
        self._create_action_buttons(content_layout)
        
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

    @override
    def _apply_theme(self):
        """Apply theme styling to all components."""
        theme_manager = self.app_context.get_manager(ThemeManager)
        palette = theme_manager.get_surface_palette()

        # Get theme colors with fallbacks
        card_bg = palette.get("card_bg", "#ffffff")
        card_border = palette.get("card_border", "#dee2e6")
        base_fg = palette.get("base_fg", "#333333")
        card_hover = palette.get("card_hover", "#e5f3ff")

        # Apply theme to main widget
        self.setStyleSheet(f"""
            FitPanel {{
                background-color: {card_bg};
                color: {base_fg};
            }}
            QGroupBox {{
                font-weight: bold;
                font-size: 9pt;
                color: {base_fg};
                margin-top: 5px;
                padding-top: 10px;
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 4px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                background-color: {card_bg};
            }}
        """)

        # Title label with improved styling
        self.title_label.setStyleSheet(f"""
            QLabel {{
                font-size: 14px;
                font-weight: bold;
                color: {base_fg};
                padding: 5px;
                background-color: {card_border};
                border-radius: 3px;
            }}
        """)

        # Main action buttons
        self._apply_button_styling()

    def _apply_button_styling(self):
        """Apply theme styling to action buttons."""
        theme_manager = self.app_context.get_manager(ThemeManager)
        palette = theme_manager.get_surface_palette()

        # Get colors with fallbacks
        accent = palette.get("accent", "#4CAF50")
        secondary_fg = palette.get("secondary_fg", "#666666")
        card_hover = palette.get("card_hover", "#e5f3ff")
        base_fg = palette.get("base_fg", "#333333")
        card_border = palette.get("card_border", "#dee2e6")
        card_bg = palette.get("card_bg", "#ffffff")

        # Primary button (Perform Fit)
        primary_style = f"""
            QPushButton {{
                background-color: {accent};
                color: white;
                padding: 6px 14px;
                border: none;
                border-radius: 4px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {card_hover};
                color: {base_fg};
            }}
            QPushButton:pressed {{
                background-color: {card_border};
            }}
            QPushButton:disabled {{
                background-color: {secondary_fg};
                color: #999999;
            }}
        """
        self.fit_button.setStyleSheet(primary_style)

        # Secondary buttons (Apply to Chart, Clear Results)
        secondary_style = f"""
            QPushButton {{
                background-color: {card_hover};
                color: {base_fg};
                padding: 6px 14px;
                border: 1px solid {card_border};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {card_bg};
            }}
            QPushButton:pressed {{
                background-color: {card_border};
            }}
            QPushButton:disabled {{
                background-color: {card_hover};
                color: {secondary_fg};
            }}
        """
        for button in [self.apply_button, self.clear_button]:
            button.setStyleSheet(secondary_style)

    def _apply_menu_styling(self):
            """Apply theme styling to the function menu"""
            theme_manager = self.app_context.get_manager(ThemeManager)
            palette = theme_manager.get_surface_palette()

            # Get theme colors with fallbacks
            card_bg = palette.get("card_bg", "#ffffff")
            card_border = palette.get("card_border", "#dee2e6")
            base_fg = palette.get("base_fg", "#333333")
            card_hover = palette.get("card_hover", "#e5f3ff")
            secondary_fg = palette.get("secondary_fg", "#666666")

            # Function button styling
            function_button_style = f"""
            QPushButton {{
                background-color: {card_hover};
                color: {base_fg};
                padding: 6px 14px;
                border: 1px solid {card_border};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {card_bg};
            }}
            QPushButton:pressed {{
                background-color: {card_border};
            }}
            QPushButton:disabled {{
                background-color: {card_hover};
                color: {secondary_fg};
            }}
        """
            self.function_button.setStyleSheet(function_button_style)

            # Menu styling
            menu_style = f"""
                QMenu {{
                    background-color: {card_bg};
                    color: {base_fg};
                    border: 1px solid {card_border};
                    border-radius: 4px;
                }}
                QMenu::item {{
                    padding: 5px 20px;
                    background-color: transparent;
                }}
                QMenu::item:selected {{
                    background-color: {card_hover};
                    color: {base_fg};
                }}
                QMenu::item:pressed {{
                    background-color: {card_border};
                    color: {base_fg};
                }}
            """
            self.menu.setStyleSheet(menu_style)

    def _create_data_source_section(self, layout):
        """Create the data source selection section."""
        data_group = QGroupBox("Data Source")
        data_layout = QGridLayout(data_group)

        data_layout.addWidget(QLabel("Chart Series:"), 0, 0)

        self.series_combo = QComboBox()
        data_layout.addWidget(self.series_combo, 0, 1)

        data_layout.addWidget(QLabel("Data Points:"), 1, 0)
        self.data_points_label = QLabel("No data selected")
        data_layout.addWidget(self.data_points_label, 1, 1)
        
        layout.addWidget(data_group)
    
    def _create_fit_config_section(self, layout):
        """Create the fit configuration section."""
        fit_group = QGroupBox("Fit Configuration")
        fit_layout = QVBoxLayout(fit_group)
        
        # Fit type selection
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Fit Type:"))
        self.fit_type_combo = QComboBox()
        self.fit_type_combo.addItems([
            "Linear (y = ax + b)",
            "Quadratic (y = ax² + bx + c)", 
            "Exponential (y = ae^(bx) + c)",
            "Power (y = ax^b + c)",
            "Logarithmic (y = a*ln(x) + b)",
            "Custom Function"
        ])
        type_layout.addWidget(self.fit_type_combo)
        type_layout.addStretch()
        fit_layout.addLayout(type_layout)
        
        # Custom function input (initially hidden)
        self.custom_group = QGroupBox("Custom Function")
        custom_layout = QGridLayout(self.custom_group)
        
        custom_layout.addWidget(QLabel("Function:"), 0, 0)
        self.custom_function_edit = QLineEdit()
        self.custom_function_edit.setPlaceholderText("e.g., a*x**2 + b*x + c")
        custom_layout.addWidget(self.custom_function_edit, 0, 1)
        #show menu
        self.function_button = QPushButton("Functions")
        custom_layout.addWidget(self.function_button, 0, 2)
        self.menu = QMenu()
        self.function_names = ["sin", "cos","tan", "sqrt", "exp", "log", "arcsin", "arccos"]
        self._apply_menu_styling()

        for name in self.function_names:
            action = self.menu.addAction(name)
            action.triggered.connect(lambda checked, f=name: self.fit_command.insert_function(f + "("))

        #connect buttons to menu
        self.function_button.clicked.connect(
            lambda: self.menu.exec_(self.function_button.mapToGlobal(self.function_button.rect().bottomLeft()))
        )
        
        custom_layout.addWidget(QLabel("Parameters:"), 1, 0)
        self.custom_params_edit = QLineEdit()
        self.custom_params_edit.setPlaceholderText("e.g., a, b, c")
        custom_layout.addWidget(self.custom_params_edit, 1, 1)
        
        custom_layout.addWidget(QLabel("Define parameters values:"), 2, 0)
        self.initial_guess_edit = QLineEdit()
        self.initial_guess_edit.setPlaceholderText("e.g. b=2.1, c=1")
        custom_layout.addWidget(self.initial_guess_edit, 2, 1)
        # display that some parameters are free
        
        self.custom_group.setVisible(False)
        fit_layout.addWidget(self.custom_group)
        
        # Fit options
        options_layout = QGridLayout()
        
        # Number of fit points
        options_layout.addWidget(QLabel("Fit Points:"), 0, 0)
        self.fit_points_spin = QSpinBox()
        self.fit_points_spin.setRange(50, 5000)
        self.fit_points_spin.setValue(500)
        options_layout.addWidget(self.fit_points_spin, 0, 1)
        
        # Show confidence bands
        self.confidence_check = QCheckBox("Show Confidence Bands")
        self.confidence_check.setChecked(False)
        options_layout.addWidget(self.confidence_check, 1, 0, 1, 2)
        
        # R-squared calculation
        self.r_squared_check = QCheckBox("Calculate R²")
        self.r_squared_check.setChecked(True)
        options_layout.addWidget(self.r_squared_check, 2, 0, 1, 2)
        
        fit_layout.addLayout(options_layout)
        layout.addWidget(fit_group)
    
    def _create_results_section(self, layout):
        """Create the results display section."""
        results_group = QGroupBox("Fit Results")
        results_layout = QVBoxLayout(results_group)
        
        # Results text area
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setPlaceholderText("Fit results will appear here...")
        results_layout.addWidget(self.results_text, stretch=1)
        
        # Equation display
        equation_layout = QHBoxLayout()
        equation_layout.addWidget(QLabel("Equation:"))
        self.equation_label = QLabel("No fit performed")
        self.equation_label.setMaximumHeight(60)
        self.equation_label.setStyleSheet("font-family: monospace; background-color: #f5f5f5; color: #333333; padding: 5px; border: 1px solid #ddd;")
        equation_layout.addWidget(self.equation_label)
        results_layout.addLayout(equation_layout)
        
        layout.addWidget(results_group)
    
    def _create_action_buttons(self, layout):
        """Create action buttons."""
        button_layout = QHBoxLayout()

        self.fit_button = QPushButton("Perform Fit")
        self.fit_button.setEnabled(self.scipy_available)
        button_layout.addWidget(self.fit_button)

        self.apply_button = QPushButton("Apply to Chart")
        self.apply_button.setEnabled(False)
        button_layout.addWidget(self.apply_button)
        
        self.clear_button = QPushButton("Clear Results")
        button_layout.addWidget(self.clear_button)
        
        layout.addLayout(button_layout)
    
    def _connect_signals(self):
        """Connect widget signals."""
        self.fit_type_combo.currentTextChanged.connect(self._on_fit_type_changed)
        self.series_combo.currentIndexChanged.connect(self._on_series_changed)
        self.fit_button.clicked.connect(self.fit_command.perform_fit)
        self.apply_button.clicked.connect(self._apply_fit)
        self.clear_button.clicked.connect(self._clear_results)
    
    def setup_event_subscriptions(self):
        """Set up event subscriptions for tab changes."""
        self.subscribe_to_event(UIEvents.TAB_CHANGED, self._on_tab_changed)
        self.subscribe_to_event(ChartEvents.CHART_UPDATED, self._on_chart_updated)

    def _show_scipy_warning(self):
        """Show warning if scipy is not available."""
        warning_text = (
            "SciPy is not available. Curve fitting functionality is disabled.\n"
            "Please install SciPy to enable curve fitting: pip install scipy"
        )
        self.results_text.setPlainText(warning_text)
        self.results_text.setStyleSheet("color: red;")
    
    def set_project(self, project):
        """Set the current project."""
        self.current_project = project

    def get_current_data(self):
        """Get data from selected chart series."""
        series = self.series_combo.currentData()
        if not self.current_project:
            return None

        dataset = self.current_project.find_item(series.dataset_id)

        if not isinstance(dataset, Dataset):
            self.logger.warning("Dataset not found")
            return None

        if dataset.data is None:
            self.logger.warning("Dataset contains no data")
            return None

        df = dataset.data

        x_column = series.x_column
        y_column = series.y_column

        if x_column not in df.columns or y_column not in df.columns:
            return None

        mask = ~(pd.isna(df[x_column]) | pd.isna(df[y_column]))
        x_data = df[x_column][mask].values
        y_data = df[y_column][mask].values

        return df, mask, x_data, y_data, series

    def _on_tab_changed(self, event_data):
        """Handle tab change events to update context."""
        current_tab_type = event_data.get("tab_type")
        chart_id = event_data.get("chart_id")
        dataset_id = event_data.get("dataset_id")

        # Check if current tab is a chart tab
        if current_tab_type == "chart" and chart_id:
            # Get the chart from the project using chart_id
            project = self.app_context.app_state.current_project
            if project is not None:
                chart = project.find_item(chart_id)
                if chart:
                    # Load the chart into the fit panel for data analysis
                    self.set_project(project)
                    self.load_chart_object(chart)
                    self.logger.info("Fit panel context set to chart %s", chart.name)
                else:
                    self.logger.warning("Fit panel: chart id %s not found in project", chart_id)
            else:
                self.logger.warning("No current project available while switching tab")

        elif current_tab_type == "dataset" and dataset_id:
            # For dataset tabs, provide context for data fitting
            project = self.app_context.app_state.current_project
            if project is not None:
                dataset = project.find_item(dataset_id)
                if dataset:
                    # Set project context for dataset access
                    self.set_project(project)
                    self.load_chart_object(None)  # Clear chart context
                    self.logger.debug("Fit panel dataset context set for dataset %s", dataset.name)
        else:
            # Clear fit panel context when no relevant tab is active
            self.load_chart_object(None)
            self.logger.debug("Fit panel context cleared")

    def update_data_points_display(self):
        """Update the data points display."""
        current_data = self.get_current_data()
        if current_data is not None:
            df, mask, x_data, y_data, series = current_data
            self.data_points_label.setText(f"{len(x_data)} points")
            self.data_points_label.setStyleSheet("color: #333;")
        else:
            self.data_points_label.setText("No data selected")
            self.data_points_label.setStyleSheet("color: #666; font-style: italic;")
    
    def _on_fit_type_changed(self):
        """Handle fit type selection change."""
        fit_type = self.fit_type_combo.currentText()
        self.custom_group.setVisible("Custom" in fit_type)
    

    
    def display_results(self):
        """Display the fitting results."""
        if not self.fit_command.fit_results:
            return
        
        results = self.fit_command.fit_results
        fit_type = results.fit_type
        popt = results.parameters
        perr = results.errors
        param_names = results.param_names
        r_squared = results.r_squared
        params = results.params

        # Format equation
        equation = self.fit_command.format_equation(fit_type, params)
        self.equation_label.setText(equation)

        # Format results text
        results_text = f"Fit Type: {fit_type}\n\n"
        results_text += "Parameters:\n"
        results_text += self.fit_command.format_parameters(param_names, params, perr)

        if r_squared is not None:
            results_text += f"\nR² = {r_squared:.6f}\n"

        results_text += f"\nData points: {len(results.x_data)}\n"
        results_text += f"Fit points: {len(results.x_fit)}"
        
        self.results_text.setPlainText(results_text)

    def _apply_fit(self):
        """Apply the fit to the current chart."""
        if self.fit_command.fit_results:
            series = self.series_combo.currentData()

            if series is None:
                self.logger.warning("No selected series for applying fit")
                return

            dataset_id = series.dataset_id
            x_column = series.x_column
            y_column = series.y_column

            dataset_name = str(series.label)
            
            # Add source dataset info to fit results
            enhanced_fit_results = replace(
                self.fit_command.fit_results,
                source_dataset_id=dataset_id,
                source_x_column=x_column,
                source_y_column=y_column,
            )
            
            # Publish fit applied event
            self.publish_event(FitEvents.FIT_APPLIED, {
                "fit_results": enhanced_fit_results,
                "chart_id": self.current_chart.id if self.current_chart else None,
                "chart": self.current_chart,
                "fit_type": self.fit_command.fit_results.fit_type,
                "dataset_name": dataset_name
            })
    
    def _clear_results(self):
        """Clear the fit results."""
        self.fit_command.fit_results = None
        self.results_text.clear()
        self.equation_label.setText("No fit performed")
        self.apply_button.setEnabled(False)

    def load_chart_object(self, chart):
        """Load a Chart object for fitting analysis."""
        self.current_chart = chart
        self.series_combo.clear()

        if chart is None:
            return

        self.current_project = self.app_context.app_state.current_project

        for series in chart.data_series:
            label = series.label or f"{series.y_column} vs {series.x_column}"
            self.series_combo.addItem(label, series)

        if self.series_combo.count() > 0:
            self.series_combo.setCurrentIndex(0)
            self._on_series_changed()

    def _on_series_changed(self):
        series = self.series_combo.currentData()
        if series is None:
            return
        self.update_data_points_display()

    def _on_chart_updated(self, event_data):
        chart = event_data.get("chart")

        if not chart:
            return

        if self.current_chart and chart.id != self.current_chart.id:
            return

        self.current_project = self.app_context.app_state.current_project

        self.load_chart_object(chart)