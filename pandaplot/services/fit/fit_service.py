import logging
import re
from dataclasses import dataclass

import numpy as np

from pandaplot.models.events import FitEvents

FIT_DEFINITIONS = {
    "Linear": {
        "function": lambda x, a, b: a * x + b,
        "parameters": ["a", "b"],
        "equation": "a*x + b",
    },
    "Quadratic": {
        "function": lambda x, a, b, c: a * x ** 2 + b * x + c,
        "parameters": ["a", "b", "c"],
        "equation": "a*x**2 + b*x + c",
    },
    "Exponential": {
        "function": lambda x, a, b, c: a * np.exp(b * x) + c,
        "parameters": ["a", "b", "c"],
        "equation": "a*exp(b*x) + c",
    },
    "Power": {
        "function": lambda x, a, b, c: a * (x ** b) + c,
        "parameters": ["a", "b", "c"],
        "equation": "a*x**b + c",
    },
    "Logarithmic": {
        "function": lambda x, a, b: a * np.log(x) + b,
        "parameters": ["a", "b"],
        "equation": "a*ln(x) + b",
    },
}

@dataclass
class FitResult:
    fit_type: str
    parameters: np.ndarray
    errors: np.ndarray
    param_names: list[str]
    params: dict[str, float]
    r_squared: float | None
    x_fit: np.ndarray
    y_fit: np.ndarray
    x_data: np.ndarray
    y_data: np.ndarray
    covariance: np.ndarray
    confidence_lower: np.ndarray | None = None
    confidence_upper: np.ndarray | None = None
    source_dataset_id: str | None = None
    source_x_column: str | None = None
    source_y_column: str | None = None
    sigma_y: np.ndarray | None = None
    equation: str | None = None

#performs fit, doesn't include combobox methods
class FitService:
    def __init__(self, fit_panel):
        self.fixed_params = {}
        self.fit_results = None
        self.fit_panel = fit_panel
        self.logger = logging.getLogger(__name__)

    def _get_fit_name(self, fit_type: str) -> str:
        return fit_type.split(" (")[0]

    def _get_fit_func(self, fit_type: str):
        """Get the fitting function based on the selected type."""
        fit_name = self._get_fit_name(fit_type)
        if fit_name == "Custom Function":
            return self._create_custom_function()

        fit = FIT_DEFINITIONS.get(fit_name)
        if fit is None:
            self.logger.error("Unknown fit type: %s", fit_type)
            raise ValueError(f"Unknown fit type: {fit_type}")

        return fit["function"], fit["parameters"]

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
        from scipy.optimize import curve_fit

        # Get data
        data = self.fit_panel.get_current_data()
        if data is None:
            self.fit_panel.results_text.setPlainText("Please select valid data columns.")
            self.logger.debug("No valid data columns selected, get_current_data() returned None")
            return

        df, mask, x_data, y_data, series = data

        if len(x_data) < 2:
            self.fit_panel.results_text.setPlainText("At least 2 data points are required for fitting.")
            self.logger.debug("Received %d data points, at least 2 data points are required for fitting.", len(x_data))
            return

        try:
            # Get fit function
            fit_type = self.fit_panel.fit_type_combo.currentText()
            fit_func, param_names = self._get_fit_func(fit_type)

            # Extract y uncertainties (if available)
            sigma_y = self._extract_sigma_y(df, mask, series)

            fit_options = {"p0": [1] * len(param_names)}

            self.logger.debug("Weighted fit: %s", sigma_y is not None)

            if sigma_y is not None:
                self.logger.info("sigma_y range: %.3f - %.3f, n=%d",sigma_y.min(),sigma_y.max(),len(sigma_y))
                fit_options["sigma"] = sigma_y
                fit_options["absolute_sigma"] = True

            # Perform fit
            popt, pcov = curve_fit(fit_func, x_data, y_data, **fit_options)

            # Calculate errors
            perr = np.sqrt(np.diag(pcov))

            # Calculate R-squared if requested
            r_squared = None
            if self.fit_panel.r_squared_check.isChecked():
                y_pred = fit_func(x_data, *popt)

                if sigma_y is not None:
                    # Weighted R-squared
                    weights = 1 / sigma_y ** 2
                    y_mean = np.sum(weights * y_data) / np.sum(weights)
                    ss_res = np.sum(weights * (y_data - y_pred) ** 2)
                    ss_tot = np.sum(weights * (y_data - y_mean) ** 2)

                else:
                    # Standard R-squared
                    ss_res = np.sum((y_data - y_pred) ** 2)
                    y_mean = np.mean(y_data)
                    ss_tot = np.sum((y_data - y_mean) ** 2)

                if ss_tot != 0:
                    r_squared = 1 - (ss_res / ss_tot)

            # Generate fit data for plotting
            x_fit = np.linspace(x_data.min(), x_data.max(), self.fit_panel.fit_points_spin.value())
            y_fit = fit_func(x_fit, *popt)

            confidence_lower = None
            confidence_upper = None
            if self.fit_panel.confidence_check.isChecked():
                confidence_lower, confidence_upper = self._calculate_confidence_band(fit_func, x_fit, popt, pcov, x_data)

            # param dictionary define
            fixed_params = dict(self.fixed_params)
            params = {}
            popt_index = 0

            for name in param_names:
                if name in fixed_params:
                    params[name] = fixed_params[name]
                else:
                    params[name] = popt[popt_index]
                    popt_index += 1

            # Store results
            self.fit_results = FitResult(
                fit_type=fit_type,
                parameters=popt,
                errors=perr,
                param_names=param_names,
                params=params,
                r_squared=r_squared,
                x_fit=x_fit,
                y_fit=y_fit,
                x_data=x_data,
                y_data=y_data,
                covariance=pcov,
                confidence_lower=confidence_lower,
                confidence_upper=confidence_upper,
                sigma_y=sigma_y,
                equation=self.format_equation(fit_type, params)
            )

            # Display results
            self.fit_panel.display_results()

            # Enable apply button
            self.fit_panel.apply_button.setEnabled(True)

            # Publish fit completed event
            self.fit_panel.publish_event(FitEvents.FIT_COMPLETED, {
                "fit_results": self.fit_results,
                "chart_id": self.fit_panel.current_chart.id if self.fit_panel.current_chart else None,
                "fit_type": self.fit_results.fit_type
            })

        except Exception as e:
            self.logger.error("Fit failed: %s", str(e), exc_info=True)
            self.fit_panel.results_text.setPlainText(f"Fit failed: {str(e)}")
            self.fit_panel.equation_label.setText("Fit failed")
            self.fit_panel.apply_button.setEnabled(False)

    def format_equation(self, fit_type: str, params: dict) -> str:
        fit_name = self._get_fit_name(fit_type)
        if fit_name == "Custom Function":
            equation = self.fit_panel.custom_function_edit.text().strip()
        else:
            fit = FIT_DEFINITIONS.get(fit_name)
            if fit is None:
                return "Unknown equation"
            equation = fit["equation"]

        for name, value in params.items():
            try:
                num = float(value)
                replacement = f"{num:.6g}"
            except (ValueError, TypeError):
                replacement = str(value)

            equation = re.sub(
                rf"\b{re.escape(name)}\b",
                replacement,
                equation,
            )

        equation = equation.replace("+-", "-").replace("+ -", "-")
        return f"y = {equation}"

    def format_parameters(self, param_names, params, errors) -> str:
        """format fitted parameters for display"""
        lines = []
        fixed_params = self.fixed_params
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

    def _calculate_confidence_band(self, fit_func, x_fit, popt, pcov, x_data, confidence=0.95,):
        """Calculate confidence band for fitted curve."""
        from scipy.stats import t

        y_fit = fit_func(x_fit, *popt)
        n = len(x_data)
        p = len(popt)
        dof = max(0, n - p)

        if dof <= 0:
            return None, None

        tval = t.ppf((1 + confidence) / 2.0, dof)
        eps = np.sqrt(np.finfo(float).eps)
        jacobian = np.zeros((len(x_fit), len(popt)))

        for i in range(len(popt)):
            dp = np.zeros_like(popt)
            dp[i] = eps * np.maximum(np.abs(popt[i]), 1.0)
            y1 = fit_func(x_fit, *(popt + dp))
            y2 = fit_func(x_fit, *(popt - dp))
            jacobian[:, i] = (y1 - y2) / (2 * dp[i])

        variance = np.einsum("ij,jk,ik->i", jacobian, pcov, jacobian)
        sigma = np.sqrt(np.maximum(variance, 0))
        lower = y_fit - tval * sigma
        upper = y_fit + tval * sigma

        return lower, upper

    def _extract_sigma_y(self, df, mask, series) -> np.ndarray | None:
        """Extract y-axis uncertainties for weighted fitting.
            Supports symmetric and asymmetric error bar configurations."""

        if series is None:
            return None

        # Asymmetric error bars
        if series.y_error_column and series.y_error_minus_column:
            plus_column = series.y_error_column
            minus_column = series.y_error_minus_column

            if (
                    plus_column not in df.columns
                    or minus_column not in df.columns
            ):
                return None

            sigma_plus = df.loc[mask, plus_column].to_numpy(dtype=float)
            sigma_minus = df.loc[mask, minus_column].to_numpy(dtype=float)

            # Approximate asymmetric uncertainties by their average
            # TODO: see in future
            sigma = 0.5 * (sigma_plus + sigma_minus)

        # Symmetric error bars
        else:
            column = series.y_error_column

            if not column or column not in df.columns:
                return None

            sigma = df.loc[mask, column].to_numpy(dtype=float)

        if np.any(~np.isfinite(sigma)) or np.any(sigma <= 0):
            return None

        return sigma
