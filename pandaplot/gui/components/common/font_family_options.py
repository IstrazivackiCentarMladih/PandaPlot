"""Font-family option list shared by every font-family picker added across
the Chart Properties panel (chart title/subtitle, axis titles, tick
values, legend text)."""


def list_available_font_families() -> list[tuple[str, str]]:
    """Sorted, deduplicated (label, value) pairs of font families installed
    for matplotlib to use, suitable for a ValueComboBox. Always includes
    "DejaVu Sans" (matplotlib's built-in default), which every new
    font-family config field also uses as its fallback default -- so a
    family chosen on one machine that's absent on another still resolves
    to a real, always-available font rather than silently falling back to
    something the user never selected."""
    from matplotlib import font_manager

    names = {font.name for font in font_manager.fontManager.ttflist}
    names.add("DejaVu Sans")
    return [(name, name) for name in sorted(names)]
