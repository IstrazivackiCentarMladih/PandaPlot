
import sys
from PySide6.QtWidgets import QApplication

from pandaplot.commands.command_executor import CommandExecutor
from pandaplot.gui.main_window import PandaMainWindow
from pandaplot.models.events.event_bus import EventBus
from pandaplot.models.state.app_context import AppContext
from pandaplot.models.state.app_state import AppState
from pandaplot.gui.controllers.ui_controller import UIController
from pandaplot.utils.log import setup_logging

def main():
    # Setup logging 
    setup_logging()
    # Load configuration

    # Initialize application state
    event_bus = EventBus()
    app_state = AppState(event_bus)
    
    # Create UI controller (will be updated with main window reference later)
    ui_controller = UIController()
    
    # Create command executor
    command_executor = CommandExecutor()
    app_context = AppContext(
        app_state=app_state,
        event_bus=event_bus,
        command_executor=command_executor,
        ui_controller=ui_controller
    )

    # Initialize GUI components

    app = QApplication(sys.argv)
    
    # Set global application stylesheet with black text color as default
    app.setStyleSheet("""
        * {
            color: black;
            background-color: white;
        }
    """)
    
    main_window = PandaMainWindow(app_context)
    
    # Update UI controller with main window reference
    ui_controller.set_parent_widget(main_window)
    
    main_window.show()
    
    # Start the main event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
    # TODO: fix remove series