"""Unit tests for list_available_font_families(), the pure helper backing
every new font-family QComboBox added in this plan."""
from pandaplot.gui.components.common.font_family_options import list_available_font_families


def test_returns_nonempty_sorted_deduplicated_pairs():
    families = list_available_font_families()
    assert len(families) > 0
    names = [label for label, _value in families]
    assert names == sorted(names)
    assert len(names) == len(set(names))


def test_every_item_is_a_label_value_pair_with_matching_label_and_value():
    families = list_available_font_families()
    for label, value in families:
        assert label == value
        assert isinstance(label, str) and label


def test_dejavu_sans_is_always_present():
    families = list_available_font_families()
    assert "DejaVu Sans" in [label for label, _value in families]
