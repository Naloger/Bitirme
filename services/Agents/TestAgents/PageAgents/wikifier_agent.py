from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, List, Dict, Optional

from pydantic import BaseModel, Field, AliasChoices, model_validator
from pydantic_ai import Agent
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings
from services.Config import config as cfg


# ── Domain models ─────────────────────────────────────────────────────────────

class Page(BaseModel):
    url: str = ""
    raw_content: str = ""


class WikiSection(BaseModel):
    level: int = Field(default=1, ge=1, le=6)
    heading: str = ""
    content: str = ""


class WikiReference(BaseModel):
    anchor: str = ""
    text: str = ""
    url: str = ""

# ✅ give it the same treatment as references
class ExternalLink(BaseModel):
    text: str = ""
    url: str = ""


def _coerce_list(v: Any, item_fn=str) -> list:
    if v is None:
        return []
    if not isinstance(v, list):
        v = [v]
    result = []
    for x in v:
        try:
            coerced = item_fn(x)
            if coerced:
                result.append(coerced)
        except (TypeError, ValueError):
            pass
    return result


def _coerce_dict(v: Any) -> Dict[str, str]:
    """Anything → Dict[str, str]."""
    if isinstance(v, dict):
        return {str(k): str(val) for k, val in v.items() if k}
    if isinstance(v, list):
        out: Dict[str, str] = {}
        for item in v:
            if isinstance(item, dict):
                if "key" in item and "value" in item:
                    out[str(item["key"])] = str(item["value"])
                else:
                    out.update({str(k): str(val) for k, val in item.items()})
            elif isinstance(item, str) and ":" in item:
                k, _, val = item.partition(":")
                out[k.strip()] = val.strip()
        return out
    return {}


def _coerce_ext_links(v: Any) -> List[Dict[str, str]]:
    items = v if isinstance(v, list) else ([v] if v else [])
    result = []
    for item in items:
        if isinstance(item, dict):
            result.append({"text": str(item.get("text", "")), "url": str(item.get("url", ""))})
        elif isinstance(item, str):
            result.append({"text": item, "url": item})
    return result


def _coerce_section(x: Any) -> Optional[Dict]:
    if isinstance(x, dict):
        return x
    if isinstance(x, str) and x.strip():
        return {"heading": x, "content": x}
    return None

# coerce plain strings into a minimal WikiReference
def _coerce_reference(x: Any) -> Optional[Dict]:
    if isinstance(x, dict):
        return x
    if isinstance(x, WikiReference):
        return x.model_dump()
    if isinstance(x, str) and x.strip():
        return {"anchor": "", "text": x.strip(), "url": ""}
    return None



class WikiExtraction(BaseModel):
    """Single schema used for every pipeline step."""
    title: str = Field(default="")
    body: str = Field(default="", validation_alias=AliasChoices("body", "introductory_body"))
    sections: List[WikiSection] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    infobox: Dict[str, str] = Field(default_factory=dict)
    wikilinks: List[str] = Field(default_factory=list)
    interwiki_links: Dict[str, str] = Field(default_factory=dict)
    external_links: List[ExternalLink] = Field(default_factory=list)
    see_also: List[str] = Field(default_factory=list)
    references: List[WikiReference] = Field(default_factory=list)
    templates: List[str] = Field(default_factory=list)
    disambiguation: List[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        d = dict(data)
        if "body" not in d and "introductory_body" in d:
            d["body"] = d.pop("introductory_body")
        d["sections"] = [s for s in (_coerce_section(x) for x in (d.get("sections") or [])) if s]
        d["categories"] = _coerce_list(d.get("categories"))
        d["infobox"] = _coerce_dict(d.get("infobox") or {})
        d["wikilinks"] = _coerce_list(d.get("wikilinks"))
        d["interwiki_links"] = _coerce_dict(d.get("interwiki_links") or {})
        d["external_links"] = _coerce_ext_links(d.get("external_links"))
        d["see_also"] = _coerce_list(d.get("see_also"))
        d["references"] = [r for r in map(_coerce_reference, d.get("references") or []) if r]
        d["templates"] = _coerce_list(d.get("templates"))
        d["disambiguation"] = _coerce_list(d.get("disambiguation"))
        return d


class WikiPage(WikiExtraction):
        page: Page
        wikified_at: datetime = Field(default_factory=datetime.now)


# ── Pipeline definition ───────────────────────────────────────────────────────

STEPS = [
    ("overview",    "Extract only the page title and introductory body text. Ignore everything else."),
    ("sections",    "Extract only the section hierarchy (level, heading, content). Ignore everything else."),
    ("categories",  "Extract only categories and disambiguation terms. Ignore everything else."),
    ("links",       "Extract only wikilinks, interwiki_links, external_links, and see_also. Ignore everything else."),
    ("metadata",    "Extract only infobox key-value pairs, references, and templates. Ignore everything else."),
]


# ── Agent / model ─────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _model():
    provider = str(getattr(cfg, "PROVIDER", "ollama") or "ollama").lower()
    name = str(getattr(cfg, "MODEL", "llama3.1") or "llama3.1")
    url = str(getattr(cfg, "BASE_URL", "http://localhost:11434") or "http://localhost:11434")
    key = getattr(cfg, "API_KEY", None)
    if provider == "ollama":
        return OllamaModel(name, provider=OllamaProvider(base_url=url, api_key=key))
    if provider in ("openai", "deepseek"):
        return OpenAIChatModel(name, provider=OpenAIProvider(base_url=url, api_key=key))
    return name


_AGENT = Agent(
    _model(),
    system_prompt="You are an expert Wikipedia editor. Return only structured data matching the schema.",
    output_type=WikiExtraction,
    tool_retries=max(0, int(getattr(cfg, "MAX_LOOPS", 0) or 0)),   # ❌ wrong param name
    output_retries=max(0, int(getattr(cfg, "MAX_LOOPS", 0) or 0)),
)

_SETTINGS = ModelSettings(
    temperature=float(getattr(cfg, "TEMPERATURE", 0.0) or 0.0),
    max_tokens=int(getattr(cfg, "MAX_TOKENS", 0) or 0),            # ❌ 0 is invalid/ambiguous
    timeout=float(getattr(cfg, "TIMEOUT", 60.0) or 60.0),
)



# ── Core logic ────────────────────────────────────────────────────────────────

def _merge(base: Optional[WikiPage], update: WikiExtraction, page: Page) -> WikiPage:
    result = base.model_copy(deep=True) if base else WikiPage(page=page)
    for field in WikiExtraction.model_fields:
        val = getattr(update, field)
        if val:  # skip empty strings, lists, dicts
            setattr(result, field, val)
    return result


def wikify(page: Page) -> WikiPage:
    result: Optional[WikiPage] = None
    for step_name, instruction in STEPS:
        update: WikiExtraction = _AGENT.run_sync(
            f"Step: {step_name}\n{instruction}\n\nPage text:\n{page.raw_content}",
            model_settings=_SETTINGS,
        ).output
        result = _merge(result, update, page)
    assert result is not None
    return result


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
            if section.heading.strip():                          # ✅ fix 4: guard empty headings
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
    lines.append(f"*Wikified at:* {wiki.wikified_at.strftime('%Y-%m-%d')}")  # ✅ fix 3: was '%d%m%y'
    return "\n".join(lines).strip() + "\n"


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    page = Page(
        url="https://example.com/python_history",
        raw_content="""
        Python (programming language)
        Python is a high-level, general-purpose programming language.

        == History ==
        Conceived in the late 1980s by Guido van Rossum at CWI in the Netherlands.[1]

        == Categories ==
        Programming languages, Object-oriented programming languages.

        [1] "Python 3.13.1 is now available". Python Software Foundation. December 2024. https://python.org
        """,
    )

    wiki = wikify(page)
    markdown = render_markdown(wiki)
    output_path = Path(__file__).with_name(f"{_safe_filename(wiki.title)}.md")
    output_path.write_text(markdown, encoding="utf-8")
    print(f"Saved Markdown to: {output_path}")
    print(markdown)


if __name__ == "__main__":
    main()