from pandaplot.gui.components.common.toggle_switch import knob_x_for_state


def test_knob_x_for_off_state_is_at_left_margin():
    assert knob_x_for_state(checked=False, track_width=26, knob_diameter=11, margin=2) == 2


def test_knob_x_for_on_state_is_at_right_margin():
    # track_width - knob_diameter - margin
    assert knob_x_for_state(checked=True, track_width=26, knob_diameter=11, margin=2) == 13


def test_knob_x_scales_with_custom_track_width():
    assert knob_x_for_state(checked=True, track_width=40, knob_diameter=15, margin=3) == 22
