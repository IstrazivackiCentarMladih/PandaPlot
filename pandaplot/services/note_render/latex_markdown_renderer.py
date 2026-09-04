"""Render note source (Markdown + LaTeX math) into self-contained HTML.

Math delimited by ``$...$`` (inline) and ``$$...$$`` (display) is rendered to
PNG images via matplotlib's ``mathtext`` engine -- a LaTeX-math subset that
covers the notation typical of scientific notes (fractions, integrals, sums,
Greek letters, matrices, sub/superscripts, symbols). Each equation is embedded
as a base64 ``data:`` URI, so the resulting HTML is fully offline and portable
into both the Qt preview (``QTextBrowser``) and the PDF export
(``QTextDocument``).

This module is intentionally free of any Qt dependency so it can be unit
tested and reused headlessly.
"""

import base64
import io
import logging
import re
import struct
import uuid
from dataclasses import dataclass
from typing import Optional

from markdown import markdown

logger = logging.getLogger(__name__)

# Render at a multiple of the display resolution so equations stay crisp on
# high-DPI screens; the <img> is then scaled back down by the same factor.
# 4x covers up to 400% OS display scaling before the PNG itself becomes the
# resolution bottleneck; equations are tiny so the extra pixels cost little.
_RENDER_SCALE = 16
_BASE_DPI = 100

# Placeholders swapped in for math while Markdown runs, so Markdown never sees
# (and never mangles) the LaTeX source. Pure alphanumerics survive Markdown
# untouched. \x00 guards escaped dollar signs.
_ESCAPED_DOLLAR = "\x00"
_MATH_TOKEN = "zzmathplaceholder{index}zz"
_MATH_TOKEN_RE = re.compile(r"zzmathplaceholder(\d+)zz")

_DISPLAY_MATH_RE = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)
_INLINE_MATH_RE = re.compile(r"\$(.+?)\$", re.DOTALL)

# Image size modifier: Typora-style `![alt](target =WxH)`, with width and/or
# height optional (`=300x`, `=x200`, `=300x200`). Bare `=WxH` isn't valid
# CommonMark, so it's stripped before Markdown parses the link and reapplied
# as width/height attributes on the rendered <img> afterwards. The stripped
# size is carried through as a URL fragment tagged with a token unique to
# this render call, so a user's own URL that happens to already end in
# something like "#pandaimgsize3" is never mistaken for one of ours.
# The leading (?<!\\) skips a `\![...]` the user escaped to be literal text
# (no image is emitted there, so there'd be no <img> to reapply a size to).
_IMAGE_SIZE_RE = re.compile(r"(?<!\\)!\[([^\]]*)\]\(([^\s)]+)\s+=(\d*)x(\d*)\)")
_IMG_SIZE_FRAGMENT = "pandaimgsize"

# Fenced/inline code spans aren't image links even if they contain
# "![...](... =WxH)"-shaped text; both are stashed as inert placeholders for
# the duration of `_extract_image_sizes` only, then restored verbatim so
# Markdown still renders them as ordinary code afterwards.
_FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
_CODE_TOKEN = "zzcodeplaceholder{index}zz"
_CODE_TOKEN_RE = re.compile(r"zzcodeplaceholder(\d+)zz")
_IMG_TAG_RE = re.compile(r"(<img\b[^>]*?)(/?)>")


def _img_size_src_re(token: str) -> re.Pattern:
    return re.compile(rf'src="([^"]*)#{_IMG_SIZE_FRAGMENT}-{re.escape(token)}-(\d+)"')

# Cache rendered equations for the session; keyed on everything that affects
# the pixels. data: URIs are large but bounded by the number of distinct
# equations edited in a session.
_equation_cache: dict[tuple, "RenderedEquation"] = {}


@dataclass(frozen=True)
class RenderedEquation:
    """A single equation rendered to an embeddable image."""

    data_uri: str
    width: int
    height: int
    valign: float  # baseline offset in display px (negative sinks below baseline)
    ok: bool
    latex: str


def _png_dimensions(data: bytes) -> tuple[int, int]:
    """Read (width, height) from a PNG byte string's IHDR chunk."""
    width, height = struct.unpack(">II", data[16:24])
    return int(width), int(height)


def render_equation(latex: str, *, color: str, fontsize: float, display: bool) -> RenderedEquation:
    """Render a single LaTeX-math string to a base64 PNG data URI.

    On a parse error, returns a ``RenderedEquation`` with ``ok=False`` and an
    empty ``data_uri`` so the caller can fall back to showing the raw source
    instead of crashing the whole preview.
    """
    key = (latex, color, round(fontsize, 2), display)
    cached = _equation_cache.get(key)
    if cached is not None:
        return cached

    # Import lazily: matplotlib is heavy and not every session touches notes.
    from matplotlib import figure
    from matplotlib.font_manager import FontProperties
    from matplotlib.mathtext import MathTextParser

    # Display equations render a touch larger, matching common note styling.
    effective_size = fontsize * (1.3 if display else 1.0)
    buf = io.BytesIO()
    try:
        # Reimplements matplotlib.mathtext.math_to_image, but saves with a
        # transparent background instead of the opaque white figure facecolor
        # -- otherwise every equation shows as a white box in a dark theme.
        prop = FontProperties(size=effective_size)
        expr = f"${latex.strip()}$"
        parser = MathTextParser("path")
        width, height, depth, _, _ = parser.parse(expr, dpi=72, prop=prop)

        fig = figure.Figure(figsize=(width / 72.0, height / 72.0))
        fig.text(0, depth / height, expr, fontproperties=prop, color=color)
        fig.savefig(
            buf,
            dpi=_BASE_DPI * _RENDER_SCALE,
            format="png",
            transparent=True,
        )
    except Exception as exc:  # invalid syntax, unknown symbol, etc.
        logger.debug("mathtext failed to render %r: %s", latex, exc)
        result = RenderedEquation("", 0, 0, 0.0, ok=False, latex=latex)
        _equation_cache[key] = result
        return result

    data = buf.getvalue()
    px_w, px_h = _png_dimensions(data)
    data_uri = "data:image/png;base64," + base64.b64encode(data).decode("ascii")
    result = RenderedEquation(
        data_uri=data_uri,
        width=round(px_w / _RENDER_SCALE),
        height=round(px_h / _RENDER_SCALE),
        valign=-(float(depth) / _RENDER_SCALE),
        ok=True,
        latex=latex,
    )
    _equation_cache[key] = result
    return result


def _equation_img(latex: str, *, color: str, fontsize: float, display: bool) -> str:
    """Build the HTML fragment for one equation (image, or error fallback)."""
    eq = render_equation(latex, color=color, fontsize=fontsize, display=display)
    if not eq.ok:
        # Show the offending source so the user can fix it, rather than a blank.
        safe = _escape_html(latex)
        return f'<code class="math-error" style="color:#dc3545;">${safe}$</code>'

    if display:
        return (
            f'<img class="math-display" src="{eq.data_uri}" '
            f'width="{eq.width}" height="{eq.height}" alt="{_escape_html(latex)}" '
            f'style="display:block;margin:8px auto;">'
        )
    return (
        f'<img class="math-inline" src="{eq.data_uri}" '
        f'width="{eq.width}" height="{eq.height}" alt="{_escape_html(latex)}" '
        f'style="vertical-align:{eq.valign:.1f}px;">'
    )


def _protect_code_regions(text: str) -> tuple[str, list[str]]:
    """Stash fenced and inline code spans behind inert placeholder tokens.

    Used only around `_extract_image_sizes`: that regex operates on raw text
    ahead of Markdown's own parsing, so without this it would also rewrite
    "![...](... =WxH)"-shaped text sitting inside a code span/block, leaving
    our internal fragment marker visible in the rendered code (Markdown
    doesn't emit an <img> there for `_apply_image_sizes` to attach it to).
    """
    blocks: list[str] = []

    def _stash(m: re.Match) -> str:
        idx = len(blocks)
        blocks.append(m.group(0))
        return _CODE_TOKEN.format(index=idx)

    text = _FENCED_CODE_RE.sub(_stash, text)
    text = _INLINE_CODE_RE.sub(_stash, text)
    return text, blocks


def _restore_code_regions(text: str, blocks: list[str]) -> str:
    def _restore(m: re.Match) -> str:
        idx = int(m.group(1))
        return blocks[idx] if idx < len(blocks) else m.group(0)

    return _CODE_TOKEN_RE.sub(_restore, text)


def _extract_image_sizes(
    text: str,
) -> tuple[str, list[tuple[Optional[str], Optional[str]]], str]:
    """Strip `=WxH` size modifiers from image links, stashing them by index.

    Each stripped modifier is tagged onto its link target as a URL fragment
    (`target#pandaimgsize-{token}-N`) so Markdown's own link parsing carries
    it through to the `<img src="...">` untouched, ready for
    `_apply_image_sizes` to pull back out. `token` is unique to this call, so
    a user-authored URL that already ends in something shaped like our own
    fragment is never mistaken for one.
    """
    token = uuid.uuid4().hex
    sizes: list[tuple[Optional[str], Optional[str]]] = []

    def _stash(m: re.Match) -> str:
        alt, target, width, height = m.groups()
        if not width and not height:
            return m.group(0)
        idx = len(sizes)
        sizes.append((width or None, height or None))
        return f"![{alt}]({target}#{_IMG_SIZE_FRAGMENT}-{token}-{idx})"

    return _IMAGE_SIZE_RE.sub(_stash, text), sizes, token


def _apply_image_sizes(
    html: str, sizes: list[tuple[Optional[str], Optional[str]]], token: str
) -> str:
    """Reapply width/height attributes stashed by `_extract_image_sizes`."""
    if not sizes:
        return html
    size_src_re = _img_size_src_re(token)

    def _fix_tag(m: re.Match) -> str:
        body, slash = m.group(1), m.group(2)
        size_match = size_src_re.search(body)
        if not size_match:
            return m.group(0)
        src, idx = size_match.group(1), int(size_match.group(2))
        if idx >= len(sizes):
            # Not one of ours (shouldn't happen given the per-render token,
            # but never trust an index into someone else's data).
            return m.group(0)
        width, height = sizes[idx]
        body = size_src_re.sub(f'src="{src}"', body).rstrip()
        if width:
            body += f' width="{width}"'
        if height:
            body += f' height="{height}"'
        return f"{body}{' ' + slash if slash else ''}>"

    return _IMG_TAG_RE.sub(_fix_tag, html)


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_body_html(source: str, *, color: str = "#000000", fontsize: float = 11.0) -> str:
    """Render note ``source`` (Markdown + LaTeX) to an HTML body fragment.

    ``color`` and ``fontsize`` control how the equation images are rasterised
    so the math visually matches the surrounding text.
    """
    # 1. Protect escaped dollars so they are never treated as math delimiters.
    text = source.replace(r"\$", _ESCAPED_DOLLAR)

    # 1b. Strip `=WxH` image size modifiers before Markdown sees the links,
    # without touching any that merely appear inside code spans/blocks.
    text, code_blocks = _protect_code_regions(text)
    text, image_sizes, image_size_token = _extract_image_sizes(text)
    text = _restore_code_regions(text, code_blocks)

    equations: list[str] = []
    display_flags: list[bool] = []

    def _stash(latex: str, *, display: bool) -> str:
        equations.append(latex)
        display_flags.append(display)
        return _MATH_TOKEN.format(index=len(equations) - 1)

    # 2. Extract display math first (so $$ is never split by the inline $ pass),
    #    then inline math. Each becomes an inert alphanumeric placeholder token
    #    that Markdown passes through untouched.
    text = _DISPLAY_MATH_RE.sub(lambda m: _stash(m.group(1), display=True), text)
    text = _INLINE_MATH_RE.sub(lambda m: _stash(m.group(1), display=False), text)

    # 3. Run Markdown on the now math-free text.
    html = markdown(text, extensions=["tables", "fenced_code"])

    # 4. Swap placeholders back out for rendered equation images.
    def _restore(match: re.Match) -> str:
        idx = int(match.group(1))
        return _equation_img(
            equations[idx], color=color, fontsize=fontsize, display=display_flags[idx]
        )

    html = _MATH_TOKEN_RE.sub(_restore, html)

    # 5. Reapply any stripped image size modifiers to their <img> tags.
    html = _apply_image_sizes(html, image_sizes, image_size_token)

    # 6. Restore any literal (escaped) dollar signs.
    html = html.replace(_ESCAPED_DOLLAR, "$")
    return html


def wrap_document(
    body_html: str,
    *,
    color: str = "#000000",
    background: str = "#ffffff",
    border: str = "#dddddd",
    fontsize: float = 11.0,
) -> str:
    """Wrap a rendered body fragment in a styled, self-contained HTML document.

    Used for both the live preview (theme colours) and PDF export (print
    colours). Styling is kept inline and simple because it is consumed by Qt's
    limited HTML rendering (``QTextBrowser`` / ``QTextDocument``), not a full
    browser.
    """
    return f"""<html><head><style>
body {{ color: {color}; background-color: {background};
       font-family: 'Segoe UI', Arial, sans-serif; font-size: {fontsize}pt;
       line-height: 1.5; }}
h1, h2, h3, h4 {{ color: {color}; }}
a {{ color: #4A90E2; }}
p {{ margin: 4px 0; }}
code, pre {{ background-color: rgba(128,128,128,0.15); border-radius: 4px;
            font-family: 'Consolas', 'Courier New', monospace; }}
pre {{ padding: 8px; }}
code {{ padding: 1px 4px; }}
table {{ border-collapse: collapse; }}
th, td {{ border: 1px solid {border}; padding: 4px 8px; }}
blockquote {{ border-left: 3px solid {border}; margin-left: 0;
             padding-left: 12px; color: {color}; }}
</style></head><body>{body_html}</body></html>"""
