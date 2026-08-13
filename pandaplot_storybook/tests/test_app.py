from pandaplot_storybook.app import build_main_window


def test_build_main_window_returns_a_populated_window(qtbot, qapp):
    window = build_main_window(qapp)
    qtbot.addWidget(window)
    assert window.current_preview_widget() is not None
