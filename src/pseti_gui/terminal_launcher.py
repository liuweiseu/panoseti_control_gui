"""Launch a detached, independent terminal-emulator window running a command.

Some `pseti` subcommands (e.g. `pseti stat --watch`) use Rich's `Live` view,
which redraws in place via ANSI cursor-repositioning escape codes. That's
fine in a real terminal but renders as garbage text if streamed into
`mainwin.py`'s plain `QPlainTextEdit` console pane the way `run_pseti()`
does for one-shot commands -- so buttons that need one of these must open an
actual terminal emulator instead.
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
import sys

# Linux terminal emulators to try, in order of preference, each paired with
# the argv suffix that makes it run *cmd* and then exit when it does.
_LINUX_TERMINALS: list[tuple[str, list[str]]] = [
    ("x-terminal-emulator", ["-e"]),
    ("gnome-terminal", ["--"]),
    ("konsole", ["-e"]),
    ("xfce4-terminal", ["-e"]),
    ("xterm", ["-e"]),
]


def open_terminal_with_command(cmd: list[str]) -> None:
    """Open a new terminal window and run *cmd* in it.

    Args:
        cmd: Argv to run, e.g. ``["pseti", "stat", "--watch"]``.

    Raises:
        RuntimeError: No supported terminal emulator could be found/launched.
    """
    if sys.platform == "darwin":
        # osascript needs the command as a single shell-quoted string, not argv.
        quoted = " ".join(shlex.quote(c) for c in cmd)
        script = f'tell application "Terminal" to do script "{quoted}"'
        subprocess.Popen(["osascript", "-e", script])
        return

    if sys.platform.startswith("linux"):
        for exe, prefix_args in _LINUX_TERMINALS:
            path = shutil.which(exe)
            if path is None:
                continue
            subprocess.Popen([path, *prefix_args, *cmd], start_new_session=True)
            return
        tried = ", ".join(name for name, _ in _LINUX_TERMINALS)
        raise RuntimeError(
            f"No terminal emulator found (tried: {tried}). "
            f"Run '{' '.join(cmd)}' manually in a terminal."
        )

    raise RuntimeError(
        f"Don't know how to open a terminal on platform '{sys.platform}'. "
        f"Run '{' '.join(cmd)}' manually in a terminal."
    )
