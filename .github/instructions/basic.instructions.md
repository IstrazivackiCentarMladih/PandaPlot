---
applyTo: '**'
---

## Context
Project Type: GUI application for data visualization inspired by Sigmaplot, Origin Pro and LabPlot. The application has educational purposes and is designed to help users visualize and analyze data in a user-friendly manner.
Language: Python
Framework / Libraries: PySide6, Matplotlib, NumPy, Pandas, SciPy
Architecture: MVC, Clean Architecture, Event-Driven, Command pattern

## General Guidelines
Use Pythonic patterns (PEP8, PEP257).
Prefer named functions and class-based structures over inline lambdas.
Use type hints where applicable (typing module).
Follow black or isort for formatting and import order.
Use meaningful naming; avoid cryptic variables.
Emphasize simplicity, readability, and DRY principles.
Prefer existing eventbus implementation over Qt signals and slots.

### Python Environment
- **Always use virtual environments** when working with this project
- **Check for existing `.env` files** in the project root before creating new ones

## Running the Application

### Primary Application Entry Point
```bash
python -m pandaplot.app
```

if it doesn't work, try
```bash
.venv\Scripts\activate && python -m pandaplot.app
```

## Project Structure

### Core Modules
- `pandaplot/` - Main application package
  - `app.py` - Application entry point
  - `gui/` - User interface components
  - `models/` - Data models and business logic
  - `commands/` - Command pattern implementations
  - `services/` - Business services and data managers

### Testing
- Run tests from the project root
- Use the configured Python environment for test execution
- Tests are located in the `tests/` directory
- Use pytest for unit and integration tests