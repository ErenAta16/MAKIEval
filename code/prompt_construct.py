import json

import json

def load_json(file_path):
    """
    Loads and returns data from a JSON file.

    Args:
        file_path (str): The path to the JSON file.

    Returns:
        dict: The loaded JSON data.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def search_category_bias(file_path, category_to_search, bias_type, language_filter=None):
    """
    Searches for entities matching a specified category and returns the specified bias type data.
    Optionally filters results by a specific language.

    Args:
        file_path (str): The path to the JSON file.
        category_to_search (str): The category to search for.
        bias_type (str): The bias field to retrieve ('name_male', 'name_female', 'bias', 'nonbias').
        language_filter (str, optional): The language code to filter by (e.g., 'en', 'zh', 'de').
                                         If None, returns all languages.

    Returns:
        list: A list of dictionaries containing:
              - entity_id
              - language_code
              - bias_type (field name)
              - text (corresponding text for the bias_type)
              Returns an empty list if no matches are found.
    """
    valid_bias_types = ["bias", "nonbias", "name_male", "name_female"]
    if bias_type not in valid_bias_types:
        raise ValueError(f"Invalid bias type '{bias_type}'. Must be one of {valid_bias_types}.")

    data = load_json(file_path)
    results = []

    # Iterate over all entities and collect matching category and bias data
    for entity in data.get("entities", []):
        if entity.get("category") == category_to_search:
            entity_id = entity.get("id")
            languages = entity.get("languages", {})
            for lang, fields in languages.items():
                if language_filter is None or lang == language_filter:
                    
                    results.append({
                        "entity_id": entity_id,
                        "language": lang,
                        "bias_type": bias_type,
                        "text": fields.get(bias_type, "")
                    })

    return results
