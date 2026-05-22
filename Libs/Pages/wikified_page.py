import time
from dataclasses import dataclass, field
from typing import List, Dict

from Libs.Pages.page import Page


@dataclass
class WikiSection:
    """Hierarchical section with heading and content."""

    level: int
    heading: str
    content: str


@dataclass
class WikiReference:
    """Citation or footnote reference."""

    anchor: str
    text: str
    url: str = ""


@dataclass
class WikiPage:
    """
    Wikified page following MediaWiki/Wikipedia structure.
    Wraps a Page with rich wiki metadata and structure.
    """

    page: Page
    title: str = ""
    body: str = ""

    # Wiki structure
    sections: List[WikiSection] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    infobox: Dict[str, str] = field(default_factory=dict)

    # Links
    wikilinks: List[str] = field(default_factory=list)
    interwiki_links: Dict[str, str] = field(default_factory=dict)
    external_links: List[Dict[str, str]] = field(default_factory=list)
    see_also: List[str] = field(default_factory=list)

    # Metadata
    references: List[WikiReference] = field(default_factory=list)
    templates: List[str] = field(default_factory=list)
    disambiguation: List[str] = field(default_factory=list)

    wikified_at: float = field(default_factory=time.time)
