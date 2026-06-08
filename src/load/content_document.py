"""Common document model for summarizable content."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ContentDocument:
    """Source-neutral content returned by content loaders."""

    id: str
    source_type: str
    url: str
    title: str
    language: str
    content: str
    thumbnail: str = ""
    metadata: dict[str, str] = field(default_factory=dict)
