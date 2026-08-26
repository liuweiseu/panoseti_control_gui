"""Convert ANSI-colored terminal output into HTML fragments for QTextEdit.

The `pseti` CLI renders through Rich, which normally strips its own ANSI
color codes when stdout isn't a real terminal -- as is the case here, piped
through `QProcess` (see mainwin.py's `FORCE_COLOR` env var, which keeps the
child's Rich Console emitting them anyway). This module turns those codes
back into HTML `console_output` (a `QTextEdit`) can render, using Rich's own
ANSI parser (`AnsiDecoder`) so every color/style Rich can produce -- not
just a hand-picked subset -- is handled correctly.
"""

from __future__ import annotations

import io
import re

from rich.ansi import AnsiDecoder
from rich.console import Console

_CODE_BLOCK_RE = re.compile(r"<code[^>]*>(.*)</code>", re.DOTALL)

# Matches Rich's own export_html() font stack so wrapped/colored output
# still lines up like it would in a real terminal (box-drawing characters,
# table columns, ...) -- QTextEdit's default font is proportional, and
# without this the literal spaces Rich pads tables with wouldn't align.
_PRE_STYLE = (
    "margin:0; white-space:pre-wrap; word-break:break-all; "
    "font-family:Menlo,'DejaVu Sans Mono',Consolas,'Courier New',monospace;"
)

# Rich renders `[green]`/`[bold green]` (used throughout panoseti/control's
# CLI for success/OK/running status) as #008000 regardless of terminal color
# depth. On this console pane's actual background that reads as too bright/
# hard to read, so it's remapped to a calmer, darker green that still reads
# clearly as "green" without the harshness. Keyed on Rich's hex so it only
# touches this one color -- red/yellow/etc. stay at Rich's defaults.
_COLOR_OVERRIDES = {
    "008000": "1b5e20",
}


def _apply_color_overrides(html_fragment: str) -> str:
    for old, new in _COLOR_OVERRIDES.items():
        html_fragment = html_fragment.replace(f"#{old}", f"#{new}")
    return html_fragment


class AnsiToHtml:
    """Stateful ANSI-to-HTML converter; reuses one Rich Console/decoder.

    Reuse (rather than constructing a new `Console`/`AnsiDecoder` per call)
    matters because `Console.export_html()` only exists on a `record=True`
    console, and recreating one per line would throw away nothing -- but a
    single decoder does let escape sequences that (in principle) span
    multiple `decode()` calls resolve correctly, so this class exists as a
    single long-lived instance rather than free functions.
    """

    def __init__(self, width: int = 1000) -> None:
        self._decoder = AnsiDecoder()
        self._console = Console(record=True, force_terminal=True, width=width, file=io.StringIO())

    def convert(self, text: str) -> str:
        """Convert *text* (may contain ANSI SGR codes and multiple lines) to an HTML fragment.

        Returns "" for text that's empty after stripping trailing newlines
        (callers should skip inserting anything in that case).
        """
        text = text.rstrip("\n")
        if not text:
            return ""
        for line in self._decoder.decode(text):
            self._console.print(line)
        raw_html = self._console.export_html(inline_styles=True, clear=True)
        match = _CODE_BLOCK_RE.search(raw_html)
        inner = match.group(1) if match else text
        inner = inner.rstrip("\n")
        inner = _apply_color_overrides(inner)
        return f'<pre style="{_PRE_STYLE}">{inner}</pre>'
