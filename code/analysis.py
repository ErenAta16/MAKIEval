# RECONSTRUCTED from paper Section 3.3 & 4.3; original analysis.py was not released in upstream repo.

import re
import time
from functools import lru_cache

import pandas as pd
from SPARQLWrapper import SPARQLWrapper, JSON

sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
sparql.addCustomHttpHeader("User-Agent", "MAKIEval/1.0 (cultural-awareness-evaluation)")

COUNTRY_SOURCE_COLUMNS = (
    "Author Countries",
    "Performer Countries",
    "Origin Countries",
)


@lru_cache(maxsize=4096)
def _query_wikidata_origin_country(qid: str) -> str:
    """Resolve origin country for a QID (P495 preferred, then P17)."""
    if not qid or qid == "NA":
        return "NA"

    query = f"""
    SELECT ?countryLabel WHERE {{
      OPTIONAL {{ wd:{qid} wdt:P495 ?country. }}
      OPTIONAL {{ wd:{qid} wdt:P17 ?country. }}
      ?country rdfs:label ?countryLabel.
      FILTER(LANG(?countryLabel) = "en")
    }}
    LIMIT 1
    """
    for attempt in range(3):
        try:
            sparql.setQuery(query)
            sparql.setReturnFormat(JSON)
            results = sparql.query().convert()
            bindings = results["results"]["bindings"]
            if bindings and "countryLabel" in bindings[0]:
                return bindings[0]["countryLabel"]["value"]
            return "NA"
        except Exception:
            time.sleep(1 + attempt)
    return "NA"


def _parse_countries_from_information(information: str) -> str:
    """Best-effort parse of country names embedded in the Information field."""
    if not information or information == "NA":
        return "NA"

    # Wikidata info strings often end with comma-separated English country labels.
    parts = [part.strip() for part in information.split(",") if part.strip()]
    if not parts:
        return "NA"

    # Heuristic: trailing tokens that look like country names (Title Case words).
    country_like = []
    for part in reversed(parts):
        if re.match(r"^[A-Z][a-zA-Z\s\-']+$", part):
            country_like.insert(0, part)
        else:
            break

    return ", ".join(country_like) if country_like else "NA"


def _row_origin_country(row: pd.Series) -> str:
    for column in COUNTRY_SOURCE_COLUMNS:
        if column in row.index and row[column] not in (None, "", "NA"):
            return str(row[column])

    information = row.get("Information", "NA")
    parsed = _parse_countries_from_information(str(information))
    if parsed != "NA":
        return parsed

    qid = row.get("Q_ID", "NA")
    return _query_wikidata_origin_country(str(qid))


def process_wikidata_country_info(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enrich Wikidata entity rows with origin-country metadata for culture specificity.

    Expected input columns include:
    Q_ID, Original Label, Label, Information, is_category, Alternative QIDs
    """
    if df.empty:
        return df

    result = df.copy()
    result["Origin Country"] = result.apply(_row_origin_country, axis=1)
    return result
