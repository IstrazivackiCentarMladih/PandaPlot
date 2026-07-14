import numpy as np
from scipy.optimize import curve_fit
import logging

from pandaplot.models.events import FitEvents


#performs fit, doesn't include combobox methods
class FitService:
    def __init__(self, fit_panel):
        self.fixed_params = None
        self.fit_results = None
        self.fit_panel = fit_panel
        self.logger = logging.getLogger(__name__)

    def _get_fit_func(self, fit_type: str):
        """Get the fitting function based on the selected type."""
        if "Linear" in fit_type:
            return lambda x, a, b: a * x + b, ["a", "b"]
        elif "Quadratic" in fit_type:
            return lambda x, a, b, c: a * x ** 2 + b * x + c, ["a", "b", "c"]
        elif "Exponential" in fit_type:
            return lambda x, a, b, c: a * np.exp(b * x) + c, ["a", "b", "c"]
        elif "Power" in fit_type:
            return lambda x, a, b, c: a * (x ** b) + c, ["a", "b", "c"]
        elif "Logarithmic" in fit_type:
            return lambda x, a, b: a * np.log(x) + b, ["a", "b"]
        elif "Custom" in fit_type:
            return self._create_custom_function()
        else:
            self.logger.error("Unknown fit type: %s", fit_type)
            raise ValueError(f"Unknown fit type: {fit_type}")

    def insert_function(self, function_str):
        cursor_pos = self.fit_panel.custom_function_edit.cursorPosition()
        current_text = self.fit_panel.custom_function_edit.text()
        new_text = current_text[:cursor_pos] + function_str + current_text[cursor_pos:]
        self.fit_panel.custom_function_edit.setText(new_text)
        self.fit_panel.custom_function_edit.setCursorPosition(cursor_pos + len(function_str))

    def _create_custom_function(self):
        """Create a custom fitting function from user input."""
        function_str = self.fit_panel.custom_function_edit.text().strip()
        params_str = self.fit_panel.custom_params_edit.text().strip()
        initial_str = self.fit_panel.initial_guess_edit.text().strip()  # use as predefined values, not initial guess

        if not function_str or not params_str:
            self.logger.warning("Custom function or parameters not specified")
            raise ValueError("Custom function and parameters must be specified")

        # add prefix np. to func
        func_list = self.fit_panel.function_names
        for func in func_list:
            function_str = function_str.replace(f"{func}(", f"np.{func}(")
            function_str = function_str.replace(f"np.np.{func}(", f"np.{func}(") #avoid np.np

        # Parse parameters
        params = [p.strip() for p in params_str.split(",")]

        # Parse initial values (fixed params)
        fixed_params = {}
        if initial_str:
            for item in initial_str.split(","):
                if "=" in item:
                    key, val = item.split("=")
                    fixed_params[key.strip()] = float(val)

        self.fixed_params = fixed_params.copy()
        free_params = [p for p in params if p not in fixed_params] #free parameters for fit

        # Create function dynamically
        def custom_func(x, *free_args):
            local_vars = {"x": x, "np": np}
            # Fill in predefined fixed values
            for k, v in fixed_params.items():
                local_vars[k] = v
            # Fill in free values
            for i, p in enumerate(free_params):
                local_vars[p] = free_args[i]
            return eval(function_str, {"__builtins__": {}}, local_vars)

        return custom_func, params

    def perform_fit(self): #fit_services
        """Perform the curve fitting."""

        # Get data
        data = self.fit_panel.get_current_data()
        if data is None:
            self.fit_panel.results_text.setPlainText("Please select valid data columns.")
            self.logger.debug("No valid data columns selected, get_current_data() returned None")
            return

        x_data, y_data = data

        if len(x_data) < 2:
            self.fit_panel.results_text.setPlainText("At least 2 data points are required for fitting.")
            self.logger.debug("Received %d data points, at least 2 data points are required for fitting.", len(x_data))
            return

        try:
            # Get fit function
            fit_type = self.fit_panel.fit_type_combo.currentText()
            fit_func, param_names = self._get_fit_func(fit_type)

            # Perform fit
            popt, pcov = curve_fit(fit_func, x_data, y_data, p0=[1] * len(param_names))

            # Calculate errors
            perr = np.sqrt(np.diag(pcov))

            # Calculate R-squared if requested
            r_squared = None
            if self.fit_panel.r_squared_check.isChecked():
                y_pred = fit_func(x_data, *popt)
                ss_res = np.sum((y_data - y_pred) ** 2)
                y_data_np = np.asarray(y_data)
                ss_tot = np.sum((y_data_np - np.mean(y_data_np)) ** 2)
                r_squared = 1 - (ss_res / ss_tot)

            # Generate fit data for plotting
            x_fit = np.linspace(x_data.min(), x_data.max(), self.fit_panel.fit_points_spin.value())
            y_fit = fit_func(x_fit, *popt)

            # param dictionary define
            fixed_params = dict(self.fixed_params) if self.fixed_params else {}
            params = {}
            popt_index = 0

            for name in param_names:
                if name in fixed_params:
                    params[name] = fixed_params[name]
                else:
                    params[name] = popt[popt_index]
                    popt_index += 1

            # Store results
            self.fit_results = {
                'fit_type': fit_type,
                'parameters': popt,
                'errors': perr,
                'param_names': param_names,
                'params': params,
                'r_squared': r_squared,
                'x_fit': x_fit,
                'y_fit': y_fit,
                'x_data': x_data,
                'y_data': y_data,
                'covariance': pcov
            }

            # Display results
            self.fit_panel.display_results()

            # Enable apply button
            self.fit_panel.apply_button.setEnabled(True)

            # Publish fit completed event
            self.fit_panel.publish_event(FitEvents.FIT_COMPLETED, {
                'fit_results': self.fit_results,
                'chart_id': self.fit_panel.current_chart.id if self.fit_panel.current_chart else None,
                'fit_type': self.fit_results.get('fit_type', 'Unknown')
            })

        except Exception as e:
            self.logger.error("Fit failed: %s", str(e), exc_info=True)
            self.fit_panel.results_text.setPlainText(f"Fit failed: {str(e)}")
            self.fit_panel.equation_label.setText("Fit failed")
            self.fit_panel.apply_button.setEnabled(False)

    def format_equation(self, fit_type: str, params: dict):
        if "Linear" in fit_type:
            equation = "a*x + b"
        elif "Quadratic" in fit_type:
            equation = "a*x**2 + b*x + c"
        elif "Exponential" in fit_type:
            equation = "a*exp(b*x) + c"
        elif "Power" in fit_type:
            equation = "a*x**b + c"
        elif "Logarithmic" in fit_type:
            equation = "a*ln(x) + b"
        elif "Custom" in fit_type:
            equation = self.fit_panel.custom_function_edit.text().strip()
        else:
            return "Unknown equation"

        for name, value in params.items():
            try:
                num = float(value)
                equation = equation.replace(name, f"{num:.6g}")
            except ValueError:
                equation = equation.replace(name, str(value))

        equation = equation.replace("+-", "-").replace("+ -", "-")
        return f"y = {equation}"

    def format_parameters(self, param_names, params, errors):
        """format fitted parameters for display"""
        lines = []
        fixed_params = self.fixed_params or {}
        free_index = 0

        for name in param_names:
            value = params[name]
            if name in fixed_params:
                lines.append(f"  {name} = {value:.6g}  (fixed)")
            else:
                error = errors[free_index]
                if np.isinf(error) or np.isnan(error):
                    lines.append(f"  {name} = {value:.6g}  (no error estimate)")
                else:
                    lines.append(f"  {name} = {value:.6g} ± {error:.6g}")
                free_index += 1

        return "\n".join(lines)