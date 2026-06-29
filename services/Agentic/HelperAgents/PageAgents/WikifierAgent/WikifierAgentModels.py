from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import AliasChoices, BaseModel, Field, model_validator


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
            result.append(
                {"text": str(item.get("text", "")), "url": str(item.get("url", ""))}
            )
        elif isinstance(item, str):
            result.append({"text": item, "url": item})
    return result


def _coerce_section(x: Any) -> Optional[Dict]:
    if isinstance(x, dict):
        return x
    if isinstance(x, str) and x.strip():
        return {"heading": x, "content": x}
    return None


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
    body: str = Field(
        default="", validation_alias=AliasChoices("body", "introductory_body")
    )
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
        d["sections"] = [
            s for s in (_coerce_section(x) for x in (d.get("sections") or [])) if s
        ]
        d["categories"] = _coerce_list(d.get("categories"))
        d["infobox"] = _coerce_dict(d.get("infobox") or {})
        d["wikilinks"] = _coerce_list(d.get("wikilinks"))
        d["interwiki_links"] = _coerce_dict(d.get("interwiki_links") or {})
        d["external_links"] = _coerce_ext_links(d.get("external_links"))
        d["see_also"] = _coerce_list(d.get("see_also"))
        d["references"] = [
            r for r in map(_coerce_reference, d.get("references") or []) if r
        ]
        d["templates"] = _coerce_list(d.get("templates"))
        d["disambiguation"] = _coerce_list(d.get("disambiguation"))
        return d


class WikiPage(WikiExtraction):
    page: Page
    wikified_at: datetime = Field(default_factory=datetime.now)

class WikifierAgentState(BaseModel):
    """The state payload carrying context and progress through the Wikifier pipeline."""

    page: Page
    current_wiki: Optional[WikiPage]
    error: Optional[str]
