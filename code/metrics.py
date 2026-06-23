"""MAKIEval cultural-awareness metrics (paper Section 4)."""

from __future__ import annotations

from typing import Any, Iterable

# Granularity: 1 = specific entity, 0 = category-level entity (Appendix B.2 / Section 4.1).
CATEGORY_ENTITY_TYPES = frozenset(
    {
        "dish_category",
        "ingredient_category",
        "beverage_category",
        "book_genre",
        "music_genre",
        "fashion_style",
        "vehicle_type",
    }
)

SPECIFIC_ENTITY_TYPES = frozenset(
    {
        "dish_name",
        "dish",
        "specific_ingredient",
        "drink_name",
        "book_title",
        "song_name",
        "clothing_type",
        "mode_of_transport",
        "artist_name",
        "author_name",
    }
)

# Country aliases for matching target regions in culture specificity.
COUNTRY_ALIASES: dict[str, set[str]] = {
    "united states": {"united states", "us", "usa", "u.s.", "america"},
    "united kingdom": {"united kingdom", "uk", "u.k.", "britain", "great britain"},
    "south korea": {"south korea", "korea", "republic of korea"},
    "united arab emirates": {"united arab emirates", "uae"},
    "taiwan": {"taiwan", "republic of china"},
    "china": {"china", "people's republic of china", "prc"},
    "mexico": {"mexico"},
    "spain": {"spain"},
    "argentina": {"argentina"},
    "germany": {"germany"},
    "iran": {"iran"},
    "india": {"india"},
    "italy": {"italy"},
    "japan": {"japan"},
    "thailand": {"thailand"},
    "turkey": {"turkey", "türkiye"},
    "canada": {"canada"},
    "australia": {"australia"},
    "nigeria": {"nigeria"},
}


def _normalize_country(name: str) -> str:
    return " ".join(name.strip().lower().replace("_", " ").split())


def _entity_type(entity: dict[str, Any]) -> str:
    return str(entity.get("entity_type", "")).lower()


def _entity_qid(entity: dict[str, Any]) -> str | None:
    qid = entity.get("qid")
    if qid is None or qid == "" or str(qid).upper() == "NA":
        return None
    return str(qid)


def _granularity_score(entity: dict[str, Any]) -> float | None:
    entity_type = _entity_type(entity)
    if entity_type in CATEGORY_ENTITY_TYPES:
        return 0.0
    if entity_type in SPECIFIC_ENTITY_TYPES:
        return 1.0
    # Unknown types are excluded from the average (paper uses typed cultural entities).
    return None


def granularity(entities: Iterable[dict[str, Any]]) -> float:
    """
    Eq. (1): Granularity = (1/|E|) * sum(Gran(e)).

    Specific cultural entities score 1; category-level entities score 0.
    Entities with unknown types are excluded from |E|.
    """
    scores = [s for s in (_granularity_score(e) for e in entities) if s is not None]
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def diversity(entities: Iterable[dict[str, Any]]) -> int:
    """
    Section 4.2: count of unique Wikidata QIDs in entity set E.

    Rows with null/NA QIDs are excluded from diversity (QID-required metric).
    """
    qids = {_entity_qid(e) for e in entities}
    qids.discard(None)
    return len(qids)


def _countries_match(target_country: str, origin_country: str) -> bool:
    target_norm = _normalize_country(target_country)
    origin_norm = _normalize_country(origin_country)

    if target_norm == origin_norm:
        return True

    for canonical, aliases in COUNTRY_ALIASES.items():
        if target_norm in aliases or target_norm == canonical:
            if origin_norm in aliases or origin_norm == canonical:
                return True
    return False


def culture_specificity(
    entities: Iterable[dict[str, Any]],
    target_country: str,
    country_lookup: dict[str, str],
) -> float:
    """
    Section 4.3: proportion of entities whose origin country matches target_country.

    country_lookup maps QID -> English country label from Wikidata (P495/P17).
    Entities without a QID or without lookup metadata are excluded from the denominator.
    """
    eligible = []
    matches = 0
    for entity in entities:
        qid = _entity_qid(entity)
        if not qid:
            continue
        origin = country_lookup.get(qid)
        if not origin or origin == "NA":
            continue
        eligible.append(entity)
        if _countries_match(target_country, origin):
            matches += 1

    if not eligible:
        return 0.0
    return matches / len(eligible)


def culture_consensus(qids_lang_a: Iterable[str], qids_lang_b: Iterable[str]) -> float:
    """
    Eq. (2) in Section 4.4: Jaccard similarity |Q_A ∩ Q_B| / |Q_A ∪ Q_B|.
    """
    set_a = {qid for qid in qids_lang_a if qid}
    set_b = {qid for qid in qids_lang_b if qid}
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def collect_qids(entities: Iterable[dict[str, Any]]) -> set[str]:
    qids = {_entity_qid(e) for e in entities}
    qids.discard(None)
    return qids
