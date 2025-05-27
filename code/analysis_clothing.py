import random
import pandas as pd
import time
from collections import defaultdict
from SPARQLWrapper import SPARQLWrapper, JSON
from analysis import process_wikidata_country_info

# Initialize SPARQL endpoint
sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
sparql.addCustomHttpHeader("User-Agent", "Mozilla/5.0")

def get_all_qids(term, lang, retries=3, delay=2):
    """Retrieve up to possible QIDs for a given term."""
    query = f"""
    SELECT ?item WHERE {{
      {{ ?item rdfs:label "{term}"@{lang}. }}
      UNION
      {{ ?item skos:altLabel "{term}"@{lang}. }}
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
            print(f"SPARQL query failed: '{term}', attempt {attempt + 1}: {e}")
            time.sleep(delay + random.uniform(0, 2))
    return []

def is_clothing(qid, retries=3, delay=2):
    """Check if the given QID represents clothing or its subclasses."""
    if qid == "NA":
        return False
    query = f"""
    ASK {{ wd:{qid} (wdt:P31|wdt:P279*) wd:Q11460. }}
    """
    for attempt in range(retries):
        try:
            sparql.setQuery(query)
            sparql.setReturnFormat(JSON)
            result = sparql.query().convert()
            return result["boolean"]
        except Exception as e:
            print(f"SPARQL query failed: '{qid}', attempt {attempt + 1}: {e}")
            time.sleep(delay + random.uniform(0, 2))
    return False

def get_best_clothing_qid(term, lang):
    """Find the best matching clothing QID for a given term."""
    candidate_qids = get_all_qids(term, lang)
    if candidate_qids:
        for qid in candidate_qids:
            if is_clothing(qid):
                return qid, "Yes", candidate_qids 
    
    candidate_qids_lower = []
    term_lower = term.lower()
    if term_lower != term:
        candidate_qids_lower = get_all_qids(term_lower, lang)
        if candidate_qids_lower:
            for qid in candidate_qids_lower:
                if is_clothing(qid):
                    return qid, "Yes", candidate_qids_lower 
    
    all_candidate_qids = candidate_qids + candidate_qids_lower
    non_na_qids = [qid for qid in all_candidate_qids if qid != "NA"]
    if non_na_qids:
        chosen_qid = random.choice(candidate_qids_lower) if candidate_qids_lower else random.choice(non_na_qids)
        return chosen_qid, "No", all_candidate_qids
    
    return "NA", "No", all_candidate_qids

def get_wikidata_info(qid, original_label, retries=3, delay=2):
    """Retrieve Wikidata information for a given QID."""
    if qid == "NA":
        return {
            "Q_ID": "NA",
            "Original Label": original_label,
            "Label": "NA",
            "Information": "NA",
            "Alternative QIDs": "NA",
            "is_category": "NA"
        }
    
    query = f"""
    SELECT 
        (GROUP_CONCAT(DISTINCT ?itemLabelLang; separator=", ") AS ?labels)
        (GROUP_CONCAT(DISTINCT ?description; separator=", ") AS ?descriptions)
        (GROUP_CONCAT(DISTINCT ?countryLabel; separator=", ") AS ?countries)
        WHERE {{
          wd:{qid} rdfs:label ?itemLabel.
          BIND(CONCAT(LANG(?itemLabel), ": ", ?itemLabel) AS ?itemLabelLang)
          OPTIONAL {{ wd:{qid} schema:description ?description. FILTER(LANG(?description) = "en") }}
          OPTIONAL {{ wd:{qid} (wdt:P495|wdt:P17) ?country. ?country rdfs:label ?countryLabel. FILTER(LANG(?countryLabel) = "en") }}
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
            countries = bindings.get("countries", {}).get("value", "")
            labels = bindings.get("labels", {}).get("value", "NA")
            
            information_values = [descriptions, countries]
            information = ", ".join(filter(None, information_values))
            
            return {
                "Q_ID": qid,
                "Original Label": original_label,
                "Label": labels,
                "Information": information if information else "NA"
            }
        except Exception as e:
            print(f"SPARQL query failed: '{qid}', attempt {attempt + 1}: {e}")
            time.sleep(delay + random.uniform(0, 2))
    
    return {
        "Q_ID": qid,
        "Original Label": original_label,
        "Label": "NA",
        "Information": "NA"
    }

def fetch_wikidata_clothing_info(clothing_list, query_lang):
    """Fetch detailed Wikidata information for a given list of clothing items."""
    results = []
    
    for term in clothing_list:
        qid, is_clothing, alternative_qids = get_best_clothing_qid(term, query_lang)
        wikidata_info = get_wikidata_info(qid, term)
        wikidata_info["Alternative QIDs"] = ", ".join(alternative_qids) if is_clothing == "No" else "NA"
        wikidata_info["is_category"] = "Yes" if is_clothing == "Yes" else "No" if qid != "NA" else "NA"
        results.append(wikidata_info)
    
    return process_wikidata_country_info(pd.DataFrame(results))
