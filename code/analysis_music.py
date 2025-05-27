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

def is_song_or_music(qid, retries=3, delay=2):
    """Check if the QID represents a song or musical work."""
    if qid == "NA":
        return False
    query = f"""
    ASK {{
        {{ wd:{qid} (wdt:P31|wdt:P279*) wd:Q7366. }}   # Song
        UNION
        {{ wd:{qid} (wdt:P31|wdt:P279*) wd:Q2188189. }} # Musical work
        UNION
        {{ wd:{qid} (wdt:P31|wdt:P279*) wd:Q105543609.}} # Musical composition
        UNION
        {{ wd:{qid} (wdt:P31|wdt:P279*) wd:Q188451.}} # Musical Genre
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

def get_best_song_qid(term, lang, country_lang=None):
    """Find the best QID with category verification."""
    term_clean = term.replace('"', '').replace("'", '')
    qid_list = get_all_qids(term_clean, lang) or get_all_qids(term_clean, "en")
    
    for qid in qid_list:
        if is_song_or_music(qid):
            return qid, "Yes", qid_list, "Yes"
    
    return (qid_list[0] if qid_list else "NA"), "No", qid_list, ("No" if qid_list else "NA")

def get_performer_countries(performer_qids, retries=3, delay=2):
    """Query country information for performers using multiple nationality properties."""
    countries = []
    for qid in performer_qids:
        query = f"""
        SELECT ?countryLabel WHERE {{
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
                print(f"Performer country query failed: {qid}, attempt {attempt + 1}: {e}")
                time.sleep(delay + random.uniform(0, 2))
    return list(set(countries))  # Deduplicate

def get_wikidata_info(qid, original_label):
    """Retrieve Wikidata details including performer countries."""
    if qid == "NA":
        return {
            "Q_ID": "NA", "Original Label": original_label, "Label": "NA",
            "Description": "NA", "Language": "NA", "Discovery Year": "NA",
            "Genre": "NA", "Performer": "NA", "Performer Countries": "NA",
            "is_category": "NA"
        }
    
    query = f"""
    SELECT 
        (GROUP_CONCAT(DISTINCT ?itemLabel; separator=", ") AS ?labels)
        (GROUP_CONCAT(DISTINCT ?description; separator=", ") AS ?descriptions)
        (GROUP_CONCAT(DISTINCT ?languageLabel; separator=", ") AS ?languages)
        (SAMPLE(?discoveryDate) AS ?discovery)
        (GROUP_CONCAT(DISTINCT ?genreLabel; separator=", ") AS ?genres)
        (GROUP_CONCAT(DISTINCT ?performer; separator=", ") AS ?performer_qids)
        (GROUP_CONCAT(DISTINCT ?performerLabel; separator=", ") AS ?performers)
    WHERE {{
        wd:{qid} rdfs:label ?itemLabel.
        OPTIONAL {{ wd:{qid} schema:description ?description. FILTER(LANG(?description) = "en") }}
        OPTIONAL {{ wd:{qid} wdt:P407 ?language. ?language rdfs:label ?languageLabel. FILTER(LANG(?languageLabel) = "en") }}
        OPTIONAL {{ wd:{qid} wdt:P577 ?discoveryDate. }}
        OPTIONAL {{ wd:{qid} wdt:P136 ?genre. ?genre rdfs:label ?genreLabel. FILTER(LANG(?genreLabel) = "en") }}
        OPTIONAL {{ wd:{qid} wdt:P175 ?performer. 
            ?performer rdfs:label ?performerLabel. 
            FILTER(LANG(?performerLabel) = "en") }}
    }}
    GROUP BY ?item
    """
    try:
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()
        bindings = results["results"]["bindings"][0] if results["results"]["bindings"] else {}
        
        # Extract performer QIDs
        performer_qids = []
        if "performer_qids" in bindings:
            raw_qids = bindings["performer_qids"]["value"].split(", ")
            performer_qids = [qid.split("/")[-1] for qid in raw_qids if qid.startswith("http")]
        
        # Query performer countries
        countries = get_performer_countries(performer_qids) if performer_qids else []
        
        return {
            "Q_ID": qid,
            "Original Label": original_label,
            "Label": bindings.get("labels", {}).get("value", "NA"),
            "Description": bindings.get("descriptions", {}).get("value", "NA"),
            "Language": bindings.get("languages", {}).get("value", "NA"),
            "Discovery Year": bindings.get("discovery", {}).get("value", "NA")[:4] if bindings.get("discovery") else "NA",
            "Genre": bindings.get("genres", {}).get("value", "NA"),
            "Performer": bindings.get("performers", {}).get("value", "NA"),
            "Performer Countries": ", ".join(countries) if countries else "NA",
            "is_category": "Yes"
        }
    except Exception as e:
        print(f"SPARQL query failed: {qid}: {e}")
        return {"Q_ID": qid, "Original Label": original_label, "is_category": "NA"}

def fetch_wikidata_music_info(song_list, query_lang, country_lang=None):
    """Main function to fetch music information with country analysis."""
    results = []
    for term in song_list:
        qid, is_song, alternative_qids, is_category = get_best_song_qid(term, query_lang, country_lang)
        wikidata_info = get_wikidata_info(qid, term)
        wikidata_info.update({
            "Alternative QIDs": ", ".join(alternative_qids) if is_song == "No" else "NA",
            "is_category": is_category
        })
        results.append(wikidata_info)
    return process_wikidata_country_info(pd.DataFrame(results))