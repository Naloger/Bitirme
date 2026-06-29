import os
import sys
from pathlib import Path
from typing import List

# Ensure project root is in sys.path before importing local services
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_here, "..", "..", "..", "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from services.Agentic.HelperAgents.PageAgents.WikifierAgent.WikifierAgentModels import (
    Page,
    WikiPage,
)
from services.Agentic.HelperAgents.PageAgents.WikifierAgent.WikifierAgentStates import (
    WikifierAgentState,
)
from services.Agentic.HelperAgents.PageAgents.WikifierAgent.WikifierGraphBuilder import (
    build_wikifier_graph,
)


def _safe_filename(name: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in name).strip("-")
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned or "wikified-page"


def render_markdown(wiki: WikiPage) -> str:
    lines: List[str] = []
    title = wiki.title.strip() or "Wikified Page"

    lines.append(f"# {title}")
    if wiki.body.strip():
        lines.append("")
        lines.append(wiki.body.strip())

    if wiki.infobox:
        lines.append("")
        lines.append("## Infobox")
        lines.append("")
        for key, value in wiki.infobox.items():
            lines.append(f"- **{key}**: {value}")

    if wiki.sections:
        lines.append("")
        lines.append("## Sections")
        lines.append("")
        for section in wiki.sections:
            heading_level = max(3, min(6, section.level + 2))
            if section.heading.strip():
                lines.append(f"{'#' * heading_level} {section.heading}")
            if section.content.strip():
                lines.append(section.content.strip())
            lines.append("")

    if wiki.categories:
        lines.append("## Categories")
        lines.append("")
        lines.append(", ".join(f"`{category}`" for category in wiki.categories))

    if wiki.wikilinks:
        lines.append("")
        lines.append("## Wikilinks")
        lines.append("")
        for link in wiki.wikilinks:
            lines.append(f"- {link}")

    if wiki.interwiki_links:
        lines.append("")
        lines.append("## Interwiki Links")
        lines.append("")
        for name, target in wiki.interwiki_links.items():
            lines.append(f"- **{name}**: {target}")

    if wiki.external_links:
        lines.append("")
        lines.append("## External Links")
        lines.append("")
        for item in wiki.external_links:
            text = (item.text or item.url).strip()
            url = item.url.strip()
            if url:
                lines.append(f"- [{text}]({url})")

    if wiki.see_also:
        lines.append("")
        lines.append("## See Also")
        lines.append("")
        for item in wiki.see_also:
            lines.append(f"- {item}")

    if wiki.references:
        lines.append("")
        lines.append("## References")
        lines.append("")
        for ref in wiki.references:
            ref_text = ref.text.strip() or ref.anchor.strip()
            if ref.url.strip():
                lines.append(f"- [{ref.anchor or 'ref'}] [{ref_text}]({ref.url})")
            else:
                lines.append(f"- [{ref.anchor or 'ref'}] {ref_text}")

    if wiki.templates:
        lines.append("")
        lines.append("## Templates")
        lines.append("")
        for item in wiki.templates:
            lines.append(f"- `{item}`")

    if wiki.disambiguation:
        lines.append("")
        lines.append("## Disambiguation")
        lines.append("")
        for item in wiki.disambiguation:
            lines.append(f"- {item}")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*Source:* {wiki.page.url}")
    lines.append(f"*Wikified at:* {wiki.wikified_at.strftime('%Y-%m-%d %H:%M:%S')}")
    return "\n".join(lines).strip() + "\n"


def main():
    page = Page(
        url="https://example.com/python_history",
        raw_content="""
        Python (programming language)
        Python is a high-level, general-purpose programming language.

        Conceived in the late 1980s by Guido van Rossum at CWI in the Netherlands.[1]

        Programming languages, Object-oriented programming languages.

        [1] "Python 3.13.1 is now available". Python Software Foundation. December 2024. https://python.org
        """,
    )

    initial_state: WikifierAgentState = {
        "page": page,
        "current_wiki": None,
        "error": None,
    }

    graph = build_wikifier_graph()
    print("Executing WikifierAgent LangGraph...")
    result = graph.invoke(initial_state)

    if result.get("error"):
        print(f"Wikifier execution failed: {result['error']}")
        sys.exit(1)

    wiki = result["current_wiki"]
    assert wiki is not None

    markdown = render_markdown(wiki)
    output_path = Path(__file__).parent / f"{_safe_filename(wiki.title)}.md"
    output_path.write_text(markdown, encoding="utf-8")

    print(f"Saved Markdown to: {output_path}")
    print("\n--- Output Markdown ---")
    print(markdown)


if __name__ == "__main__":
    main()
