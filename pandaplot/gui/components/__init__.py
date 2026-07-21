# MainMenu is NOT re-exported here to defer matplotlib loading
# CollapsibleSidebar and TabContainer are imported as needed
from pandaplot.gui.components.sidebar.sidebar import CollapsibleSidebar
from pandaplot.gui.components.tabs.tab_container import TabContainer

__all__ = ["CollapsibleSidebar", "TabContainer"]
