"""A QComboBox whose list opens below the field, like a web-style dropdown."""

from PySide6.QtWidgets import QComboBox, QListView, QWidget


class DropDownComboBox(QComboBox):
    """QComboBox that drops its list below the field instead of over it.

    On macOS a combo box is a native popup button: the list opens *on top of*
    the field, positioned so the current item sits under the cursor. That is
    the platform convention, but it hides the field and reads as a menu
    appearing "in the middle" rather than as a dropdown.

    Two things are needed to get a real dropdown. Setting an explicit
    QListView opts out of the native menu-style popup (which cannot be
    repositioned), and moving the popup container after the base class has
    shown it puts the list under the field. The combo itself keeps its normal
    platform appearance -- only the popup placement changes.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        # Opts the popup out of the native menu container so it is an
        # ordinary widget whose geometry we can set.
        self.setView(QListView())

    def showPopup(self):
        super().showPopup()

        popup = self.view().window()
        # An explicit view sizes the container to its contents, which can come
        # out narrower than the field; a dropdown that is flush with the field
        # it belongs to reads better.
        if popup.width() < self.width():
            popup.resize(self.width(), popup.height())

        below = self.mapToGlobal(self.rect().bottomLeft())
        x, y = below.x(), below.y()

        # The popup is a top-level window, so it is not clipped by the dialog
        # -- but it should still not run off the screen. If there is no room
        # below the field, drop it above instead.
        screen = self.screen()
        if screen is not None:
            available = screen.availableGeometry()
            if y + popup.height() > available.bottom():
                above_y = self.mapToGlobal(self.rect().topLeft()).y() - popup.height()
                y = above_y if above_y >= available.top() else available.bottom() - popup.height()
            x = max(available.left(), min(x, available.right() - popup.width()))

        popup.move(x, y)
