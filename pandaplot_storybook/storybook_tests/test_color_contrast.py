import pytest
from pandaplot.models.events.event_bus import EventBus
from pandaplot.models.state.config import ApplicationConfig, Theme
from pandaplot.services.theme.theme_manager import ThemeManager

from pandaplot_storybook.color_contrast import contrast_ratio


class _StaticConfigProvider:
    def __init__(self, config):
        self.config = config


def _tokens_for(theme: Theme) -> dict:
    event_bus = EventBus()
    config = ApplicationConfig.default()
    config.appearance.theme = theme
    theme_manager = ThemeManager(event_bus, config_provider=_StaticConfigProvider(config))
    theme_manager.apply_from_config(config)
    return theme_manager.get_design_tokens()


def test_white_vs_black_is_max_contrast():
    assert contrast_ratio("#FFFFFF", "#000000") == pytest.approx(21.0, abs=0.01)


def test_black_vs_white_is_symmetric():
    assert contrast_ratio("#000000", "#FFFFFF") == pytest.approx(21.0, abs=0.01)


def test_same_color_is_no_contrast():
    assert contrast_ratio("#4A56C6", "#4A56C6") == pytest.approx(1.0, abs=0.001)


def test_known_w3c_example_gray_on_white():
    # #767676 on #FFFFFF is a commonly cited "just passes AA" gray, ~4.54:1.
    ratio = contrast_ratio("#767676", "#FFFFFF")
    assert ratio == pytest.approx(4.54, abs=0.05)


def test_contrast_ratio_accepts_hex_without_hash():
    assert contrast_ratio("FFFFFF", "000000") == pytest.approx(21.0, abs=0.01)


@pytest.mark.parametrize("theme", [Theme.LIGHT, Theme.DARK])
def test_segmented_control_override_meets_wcag_aa_against_real_tokens(theme):
    from pandaplot_storybook.color_contrast import SEGMENTED_SELECTED_TEXT

    tokens = _tokens_for(theme)
    bg = tokens["accent_selected_bg"]
    text = SEGMENTED_SELECTED_TEXT[theme.value]
    assert contrast_ratio(text, bg) >= 4.5
