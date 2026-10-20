from app.core.keyword_matching import KEYWORD_ALIASES


def resolve_keyword(text: str) -> str | None:
    normalized = " ".join(text.casefold().split())

    return KEYWORD_ALIASES.get(normalized)