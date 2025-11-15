"""Cross-platform helpers for enabling TAB-based file path autocompletion."""
from __future__ import annotations

import os
from typing import List, Optional

READLINE = None

try:
    import readline as _readline  # type: ignore

    READLINE = _readline
except ImportError:  # pragma: no cover - platform dependent fallback
    try:
        import pyreadline3 as _readline  # type: ignore

        READLINE = _readline
    except ImportError:
        READLINE = None


def _split_path(raw_path: str) -> tuple[str, str, str]:
    """Return (directory_to_list, prefix_in_dir, base_display_prefix)."""
    separators = {os.sep}
    if os.altsep:
        separators.add(os.altsep)
    # If there is no input yet, use current directory as base.
    if not raw_path:
        return os.curdir, "", ""

    # If the raw path ends with a separator we need to list that directory.
    if raw_path.endswith(tuple(separators)):
        directory = raw_path
        prefix = ""
        base_display = raw_path
    else:
        directory = os.path.dirname(raw_path) or os.curdir
        prefix = os.path.basename(raw_path)
        base_display = raw_path[: len(raw_path) - len(prefix)]

    # Expand user-only at listing time to keep the original text for display.
    expanded_dir = os.path.expanduser(directory) if directory else os.curdir
    return expanded_dir, prefix, base_display


def _candidate_paths(directory: str, prefix: str) -> List[str]:
    """Return sorted entries from *directory* that match *prefix*."""
    try:
        entries = os.listdir(directory or os.curdir)
    except OSError:
        return []
    matches = [entry for entry in entries if entry.startswith(prefix)]
    matches.sort()
    return matches


def file_path_completer(text: str, state: int) -> Optional[str]:
    """Completer used by readline for file-system paths."""
    if READLINE is None:
        return None

    buffer = READLINE.get_line_buffer()
    raw_input = buffer if buffer else text
    if raw_input is None:
        raw_input = ""

    directory, prefix, base_display = _split_path(raw_input)
    candidates = _candidate_paths(directory, prefix)

    if state < len(candidates):
        entry = candidates[state]
        candidate_path = base_display + entry
        full_path = os.path.join(directory, entry)
        if os.path.isdir(full_path):
            candidate_path += "/"
        return candidate_path
    return None


def enable_autocomplete() -> None:
    """Register the completer with readline and bind the TAB key."""
    if READLINE is None:
        return
    READLINE.set_completer(file_path_completer)
    READLINE.parse_and_bind("tab: complete")
