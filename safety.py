"""Output-safety helpers for rendering untrusted search data.

Everything returned by SerpApi (titles, companies, snippets, URLs) and by the optional
LLM planner is third-party content. These helpers keep it from being interpreted as
HTML, Markdown links, spreadsheet formulas, or URL path segments.
"""
from __future__ import annotations

import html
import re
from typing import Any
from urllib.parse import urlparse

_MARKDOWN_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!|<>~$:])")
_MODEL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def escape_html(value: Any) -> str:
    """Escape text before placing it inside an ``unsafe_allow_html`` block."""
    return html.escape("" if value is None else str(value), quote=True)


def escape_markdown(value: Any) -> str:
    """Neutralize Markdown/HTML syntax so untrusted text renders literally."""
    text = "" if value is None else str(value)
    text = re.sub(r"[\r\n]+", " ", text)
    return _MARKDOWN_SPECIAL.sub(r"\\\1", text)


def safe_http_url(value: Any) -> str:
    """Return the URL only if it is an absolute http(s) URL; otherwise an empty string."""
    url = "" if value is None else str(value).strip()
    if not url or any(ch in url for ch in "\r\n\t <>\"'`"):
        return ""
    parsed = urlparse(url)
    return url if parsed.scheme in {"http", "https"} and parsed.netloc else ""


def csv_safe(value: Any) -> str:
    """Prevent CSV/spreadsheet formula injection (e.g. ``=HYPERLINK(...)``)."""
    text = "" if value is None else str(value)
    return "'" + text if text.startswith(_CSV_FORMULA_PREFIXES) else text


def is_valid_model_name(value: str) -> bool:
    """Model names are inserted into a URL path, so allow only a strict character set."""
    return bool(_MODEL_NAME.fullmatch(value or ""))
