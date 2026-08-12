"""Input validation for Wiki.js MCP tools (port of the TS Zod schema constraints)."""
from __future__ import annotations

import re

# Maximum response size in characters to prevent overwhelming LLM context
CHARACTER_LIMIT = 100_000

# Maximum content size in characters for write operations
MAX_CONTENT_SIZE = 500_000

# Default pagination settings
DEFAULT_PAGE_LIMIT = 50
MAX_PAGE_LIMIT = 200

# Tag limits
MAX_TAG_LENGTH = 100
MAX_TAGS_PER_PAGE = 50

# update_page has no diff/merge — `content` replaces the whole page. Below
# this old-content length the guard is skipped (small pages, low blast radius).
CONTENT_SHRINK_GUARD_MIN_OLD_LEN = 200
# New content shorter than this fraction of the old content's length is
# treated as a likely accidental overwrite and blocked without confirmation.
CONTENT_SHRINK_GUARD_RATIO = 0.5

_LOCALE_RE = re.compile(r"^[a-z]{2}(-[A-Z]{2})?$")
_PATH_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9\-_/]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$")


def validate_locale(locale: str) -> str:
    """Validate a locale code (e.g. "en", "de", "en-US")."""
    if not _LOCALE_RE.match(locale):
        raise ValueError('Locale must be a valid language code (e.g., "en", "de", "en-US")')
    return locale


def validate_path(path: str) -> str:
    """Validate a page path without leading slash."""
    if not (1 <= len(path) <= 500):
        raise ValueError("Path must be between 1 and 500 characters")
    if not _PATH_RE.match(path):
        raise ValueError(
            "Path must contain only alphanumeric characters, hyphens, underscores, and forward slashes"
        )
    if ".." in path or "//" in path:
        raise ValueError('Path must not contain ".." or "//"')
    return path


def validate_tags(tags: list[str]) -> list[str]:
    """Validate a list of page tags."""
    if len(tags) > MAX_TAGS_PER_PAGE:
        raise ValueError(f"Maximum {MAX_TAGS_PER_PAGE} tags per page")
    for tag in tags:
        if not (1 <= len(tag) <= MAX_TAG_LENGTH):
            raise ValueError(f"Tag must not exceed {MAX_TAG_LENGTH} characters")
    return tags


def validate_content(content: str) -> str:
    """Validate page content (Markdown or HTML)."""
    if not (1 <= len(content) <= MAX_CONTENT_SIZE):
        raise ValueError(f"Content must not exceed {MAX_CONTENT_SIZE} characters")
    return content


def validate_page_id(page_id: int) -> int:
    """Validate a page ID (positive integer)."""
    if page_id <= 0:
        raise ValueError("Page ID must be a positive integer")
    return page_id


def validate_title(title: str) -> str:
    """Validate a page title (max 200 chars)."""
    if not (1 <= len(title) <= 200):
        raise ValueError("Title must be between 1 and 200 characters")
    return title


def validate_description(description: str) -> str:
    """Validate a page description / meta description (max 500 chars)."""
    if not (1 <= len(description) <= 500):
        raise ValueError("Description must be between 1 and 500 characters")
    return description
