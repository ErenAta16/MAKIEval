import random
import pandas as pd
import time
from SPARQLWrapper import SPARQLWrapper, JSON
from analysis import process_wikidata_country_info

# Initialize SPARQL endpoint
sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
sparql.addCustomHttpHeader("User-Agent", "Mozilla/5.0")

def get_all_qids(term, lang, retries=3, delay=2):
    """Retrieve up to possible QIDs for a given term and language."""
    term_clean = term.replace('"', '').replace("'", '')
    term_escaped = term_clean.replace('\\', '\\\\')
    
    query = f"""
    SELECT ?item WHERE {{
      {{ ?item rdfs:label "{term_escaped}"@{lang}. }}
      UNION
      {{ ?item skos:altLabel "{term_escaped}"@{lang}. }}
    }}
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

def is_transport_related(qid, retries=3, delay=2):
    """Check if the QID represents a transport vehicle (Q334166) or transport mode (Q42889)."""
    if qid == "NA":
        return False
    query = f"""
    ASK {{
        {{ wd:{qid} (wdt:P31|wdt:P279*) wd:Q334166. }}   # Transport vehicle
        UNION
        {{ wd:{qid} (wdt:P31|wdt:P279*) wd:Q42889. }}   # Transport mode
        UNION
        {{ wd:{qid} (wdt:P31|wdt:P279*) wd:Q16858238.}} # train and rail category
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

def get_best_transport_qid(term, lang, country_lang=None):
    """Find the best QID with priority order."""
    term_clean = term.replace('"', '').replace("'", '')
    
    primary_qids = get_all_qids(term_clean, lang)
    for qid in primary_qids:
        if is_transport_related(qid):
            return qid, "Yes", primary_qids

    en_qids = get_all_qids(term_clean, "en")
    for qid in en_qids:
        if is_transport_related(qid):
            return qid, "Yes", en_qids
    
    country_qids = []
    if country_lang and country_lang not in [lang, "en"]:
        country_qids = get_all_qids(term_clean, country_lang)
        for qid in country_qids:
            if is_transport_related(qid):
                return qid, "Yes", country_qids
    
    combined_qids = list(set(primary_qids + en_qids + country_qids))
    if combined_qids:
        return combined_qids[0], "No", combined_qids

    return "NA", "No", []

def get_wikidata_info(qid, original_label, retries=3, delay=2):
    """Retrieve Wikidata details."""
    if qid == "NA":
        return {
            "Q_ID": "NA",
            "Original Label": original_label,
            "Label": "NA",
            "Information": "NA",
            "Discovery Year": "NA",
            "Alternative QIDs": "NA",
            "is_category": "NA"
        }
    
    query = f"""
    SELECT 
        (GROUP_CONCAT(DISTINCT ?itemLabelLang; separator=", ") AS ?labels)
        (GROUP_CONCAT(DISTINCT ?description; separator=", ") AS ?descriptions)
        (GROUP_CONCAT(DISTINCT ?languageLabel; separator=", ") AS ?languages)
        (SAMPLE(?discoveryDate) AS ?discovery)
    WHERE {{
        wd:{qid} rdfs:label ?itemLabel.
        BIND(CONCAT(LANG(?itemLabel), ": ", ?itemLabel) AS ?itemLabelLang)
        OPTIONAL {{ wd:{qid} schema:description ?description. FILTER(LANG(?description) = "en") }}
        OPTIONAL {{ wd:{qid} wdt:P407 ?language. ?language rdfs:label ?languageLabel. FILTER(LANG(?languageLabel) = "en") }}
        OPTIONAL {{ wd:{qid} wdt:P577 ?discoveryDate. }}
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

            descriptions = bindings.get("descriptions", {}).get("value", "")
            languages = bindings.get("languages", {}).get("value", "")
            discovery_year = bindings.get("discovery", {}).get("value", "NA")[:4]
            labels = bindings.get("labels", {}).get("value", "NA")
            
            information = ", ".join(filter(None, [descriptions, languages]))
            
            return {
                "Q_ID": qid,
                "Original Label": original_label,
                "Label": labels,
                "Information": information if information else "NA",
                "Discovery Year": discovery_year
            }
        except Exception as e:
            print(f"SPARQL query failed: {qid}, attempt {attempt + 1}: {e}")
            time.sleep(delay + random.uniform(0, 2))
    
    return {
        "Q_ID": qid,
        "Original Label": original_label,
        "Label": "NA",
        "Information": "NA",
        "Discovery Year": "NA"
    }

def fetch_wikidata_transportation_info(transport_list, query_lang, country_lang=None):
    """Fetch Wikidata transport info."""
    results = []
    for term in transport_list:
        qid, is_transport, alternative_qids = get_best_transport_qid(term, query_lang, country_lang)
        wikidata_info = get_wikidata_info(qid, term)
        wikidata_info["Alternative QIDs"] = ", ".join(alternative_qids) if is_transport == "No" else "NA"
        wikidata_info["is_category"] = "Yes" if is_transport == "Yes" else "No" if qid != "NA" else "NA"
        results.append(wikidata_info)
    return process_wikidata_country_info(pd.DataFrame(results))
