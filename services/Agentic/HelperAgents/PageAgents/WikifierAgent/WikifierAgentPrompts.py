# Pipeline definition
STEPS = [
    (
        "overview",
        "Extract only the page title and introductory body text. Ignore everything else.",
    ),
    (
        "sections",
        "Extract only the section hierarchy (level, heading, content). Ignore everything else.",
    ),
    (
        "categories",
        "Extract only categories and disambiguation terms. Ignore everything else.",
    ),
    (
        "links",
        "Extract only wikilinks, interwiki_links, external_links, and see_also. Ignore everything else.",
    ),
    (
        "metadata",
        "Extract only infobox key-value pairs, references, and templates. Ignore everything else.",
    ),
]

SYSTEM_PROMPT = (
    "You are an expert Wikipedia editor. Return only structured data matching the schema.\n"
    "CRITICAL: The output MUST be a JSON object matching the WikiExtraction schema. "
    "DO NOT return a JSON array/list directly under any circumstances. "
    "If extracting sections, categories, see_also, external_links, or references, wrap them "
    "under their corresponding keys inside the root JSON object."
)

