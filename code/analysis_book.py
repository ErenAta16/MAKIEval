import random
import pandas as pd
import time
from SPARQLWrapper import SPARQLWrapper, JSON
from analysis import process_wikidata_country_info

# Initialize SPARQL endpoint
sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
sparql.addCustomHttpHeader("User-Agent", "Mozilla/5.0")

def get_all_qids(term, lang, retries=3, delay=2):
    """Retrieve up to 5 possible QIDs for a given term and language."""
    term_clean = term.replace('"', '').replace("'", '').replace("《", "").replace("》", "").replace("「", "").replace("」", "")
    term_escaped = term_clean.replace('\\', '\\\\')
    
    query = f"""
    SELECT ?item WHERE {{
      {{ ?item rdfs:label "{term_escaped}"@{lang}. }}
      UNION
      {{ ?item skos:altLabel "{term_escaped}"@{lang}. }}
    }} LIMIT 5
    """
    for attempt in range(retries):
        try:
            sparql.setQuery(query)
            sparql.setReturnFormat(JSON)
            results = sparql.query().convert()
            bindings = results["results"]["bindings"]
            return [b["item"]["value"].split("/")[-1] for b in bindings] if bindings else []
        except Exception as e:
            print(f"SPARQL query failed: {term}, attempt {attempt + 1}: {e}")
            time.sleep(delay + random.uniform(0, 2))
    return []

def is_book_or_fiction(qid, retries=3, delay=2):
    """Check if the QID represents a book, novel, or fictional work."""
    if qid == "NA":
        return False
    query = f"""
    ASK {{
        {{ wd:{qid} (wdt:P31|wdt:P279*) wd:Q571 }}   # Book
        UNION
        {{ wd:{qid} (wdt:P31|wdt:P279*) wd:Q7725634 }} # Fictional Work
        UNION
        {{ wd:{qid} (wdt:P31|wdt:P279*) wd:Q47461344 }} # written Work
        UNION
        {{ wd:{qid} (wdt:P31|wdt:P279*) wd:Q8261 }} # Novel
        UNION
        {{ wd:{qid} (wdt:P31|wdt:P279*) wd:Q223393 }}# literary genre
    }}
    """
    for attempt in range(retries):
        try:
            sparql.setQuery(query)
            sparql.setReturnFormat(JSON)
            result = sparql.query().convert()
            return result["boolean"]
        except Exception as e:
            print(f"SPARQL query failed: {qid}, attempt {attempt + 1}: {e}")
            time.sleep(delay + random.uniform(0, 2))
    return False

def get_best_book_qid(term, lang, country_lang=None):
    """Find the best QID with priority: primary language, English, country language."""
    term_clean = term.replace('"', '').replace("'", '')
    primary_qids = get_all_qids(term_clean, lang)
    for qid in primary_qids:
        if is_book_or_fiction(qid):
            return qid, "Yes", primary_qids
    
    en_qids = get_all_qids(term_clean, "en")
    for qid in en_qids:
        if is_book_or_fiction(qid):
            return qid, "Yes", en_qids
    
    country_qids = []
    if country_lang and country_lang not in [lang, "en"]:
        country_qids = get_all_qids(term_clean, country_lang)
        for qid in country_qids:
            if is_book_or_fiction(qid):
                return qid, "Yes", country_qids
    
    combined_qids = list(set(primary_qids + en_qids + country_qids))
    if combined_qids:
        return combined_qids[0], "No", combined_qids
    
    return "NA", "No", []

def get_author_countries(author_qids, retries=3, delay=2):
    """Query country information for authors using multiple nationality properties."""
    countries = []
    for qid in author_qids:
        query = f"""
        SELECT DISTINCT ?countryLabel WHERE {{
            OPTIONAL {{ wd:{qid} wdt:P27 ?country. }}  # Citizenship
            OPTIONAL {{ wd:{qid} wdt:P495 ?country. }}  # Country of origin
            OPTIONAL {{ wd:{qid} wdt:P17 ?country. }}   # Located in
            SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        LIMIT 5
        """
        for attempt in range(retries):
            try:
                sparql.setQuery(query)
                sparql.setReturnFormat(JSON)
                results = sparql.query().convert()
                bindings = results["results"]["bindings"]
                if bindings:
                    countries.extend([b["countryLabel"]["value"] for b in bindings if "countryLabel" in b])
                break
            except Exception as e:
                print(f"Author country query failed: {qid}, attempt {attempt + 1}: {e}")
                time.sleep(delay + random.uniform(0, 2))
    return list(set(countries))  # Deduplicate

def get_wikidata_info(qid, original_label, retries=3, delay=2):
    """Retrieve Wikidata details including author countries."""
    if qid == "NA":
        return {
            "Q_ID": "NA", 
            "Original Label": original_label, 
            "Label": "NA",
            "Information": "NA", 
            "Discovery Year": "NA",
            "Author Countries": "NA",
            "is_category": "NA",
            "Alternative QIDs": "NA"
        }

    query = f"""
    SELECT 
        (GROUP_CONCAT(DISTINCT ?itemLabelLang; separator=", ") AS ?labels)
        (GROUP_CONCAT(DISTINCT ?description; separator=", ") AS ?descriptions)
        (GROUP_CONCAT(DISTINCT ?languageLabel; separator=", ") AS ?languages)
        (SAMPLE(?discoveryDate) AS ?discovery)
        (GROUP_CONCAT(DISTINCT ?author; separator=", ") AS ?author_qids)
        (GROUP_CONCAT(DISTINCT ?authorLabel; separator=", ") AS ?authors)
    WHERE {{
        wd:{qid} rdfs:label ?itemLabel.
        BIND(CONCAT(LANG(?itemLabel), ": ", ?itemLabel) AS ?itemLabelLang)
        OPTIONAL {{ wd:{qid} schema:description ?description. FILTER(LANG(?description) = "en") }}
        OPTIONAL {{ wd:{qid} wdt:P407 ?language. ?language rdfs:label ?languageLabel. FILTER(LANG(?languageLabel) = "en") }}
        OPTIONAL {{ wd:{qid} wdt:P577 ?discoveryDate. }}
        OPTIONAL {{ wd:{qid} wdt:P50 ?author.  # Author property
            ?author rdfs:label ?authorLabel. 
            FILTER(LANG(?authorLabel) = "en") }}
        SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    GROUP BY ?item
    """

    for attempt in range(retries):
        try:
            sparql.setQuery(query)
            sparql.setReturnFormat(JSON)
            results = sparql.query().convert()
            bindings = results["results"]["bindings"][0] if results["results"]["bindings"] else {}

            # Extract author QIDs
            author_qids = []
            if "author_qids" in bindings:
                raw_qids = bindings["author_qids"]["value"].split(", ")
                author_qids = [qid.split("/")[-1] for qid in raw_qids if qid.startswith("http")]
            
            # Query author countries
            countries = get_author_countries(author_qids) if author_qids else []

            descriptions = bindings.get("descriptions", {}).get("value", "")
            languages = bindings.get("languages", {}).get("value", "")
            discovery_year = bindings.get("discovery", {}).get("value", "NA")[:4] if bindings.get("discovery") else "NA"
            labels = bindings.get("labels", {}).get("value", "NA")
            authors = bindings.get("authors", {}).get("value", "NA")

            information_values = [descriptions, languages]
            information = ", ".join(filter(None, information_values))

            return {
                "Q_ID": qid,
                "Original Label": original_label,
                "Label": labels,
                "Information": information if information else "NA",
                "Discovery Year": discovery_year,
                "Author Countries": ", ".join(countries) if countries else "NA",
                "is_category": "Yes" if authors != "NA" else "No"
            }
        except Exception as e:
            print(f"SPARQL query failed: {qid}, attempt {attempt + 1}: {e}")
            time.sleep(delay + random.uniform(0, 2))
    
    return {
        "Q_ID": qid,
        "Original Label": original_label,
        "Label": "NA",
        "Information": "NA",
        "Discovery Year": "NA",
        "Author Countries": "NA",
        "is_category": "No"
    }

# Modified get_best_book_qid to include is_category
def get_best_book_qid(term, lang, country_lang=None):
    """Find the best QID with category verification."""
    term_clean = term.replace('"', '').replace("'", '')
    primary_qids = get_all_qids(term_clean, lang)
    for qid in primary_qids:
        if is_book_or_fiction(qid):
            return qid, "Yes", primary_qids, "Yes"  # Add is_category
    
    en_qids = get_all_qids(term_clean, "en")
    for qid in en_qids:
        if is_book_or_fiction(qid):
            return qid, "Yes", en_qids, "Yes"
    
    country_qids = []
    if country_lang and country_lang not in [lang, "en"]:
        country_qids = get_all_qids(term_clean, country_lang)
        for qid in country_qids:
            if is_book_or_fiction(qid):
                return qid, "Yes", country_qids, "Yes"
    
    combined_qids = list(set(primary_qids + en_qids + country_qids))
    if combined_qids:
        return combined_qids[0], "No", combined_qids, "No"
    
    return "NA", "No", [], "No"

def fetch_wikidata_book_info(book_list, query_lang, country_lang=None):
    """Main function to fetch book information with country analysis."""
    results = []
    
    for term in book_list:
        qid, is_book, alternative_qids, is_category = get_best_book_qid(term, query_lang, country_lang)
        wikidata_info = get_wikidata_info(qid, term)
        wikidata_info.update({
            "Alternative QIDs": ", ".join(alternative_qids) if is_book == "No" else "NA",
            "is_category": is_category
        })
        results.append(wikidata_info)

    return process_wikidata_country_info(pd.DataFrame(results))