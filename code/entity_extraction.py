import json
from openai import OpenAI
import time
import os
import requests
from collections import defaultdict

def get_topic_hint(topic):
    """Generate extraction hints based on topic category"""
    match topic:
        case "music":
            return "name of a song or genre of the music or name of the artist or place or listener's name"
        case "food":
            return "name of a dish or dish category or ingredient category or specific ingredient or place or name of a person"
        case "transportation":
            return "mode of transport or place name of a person"
        case "beverage":
            return "name of a drink or category of beverage or place name of a person"
        case "clothing":
            return "type of clothing or fashion style or place name of a person"
        case "book":
            return "book title or genre of the book or name of the author or place or reader's name"
        case _:
            return "unknown category"

def get_example_for_topic(topic):
    """Returns a string with examples depending on the topic."""
    if topic == "book":
        return """Return a dictionary like {"<book_title>": "book_title"} or {"book_genre>": "book_genre"} or {"<place>": "place"} or or {"<reader_name>": "reader_name"} or {"<author_name>": "name of author"}."""
    elif topic == "food":
        return """Return a dictionary like {"<dish_name>": "dish_name"} or {"<dish category>": "dish_category"} or {"<ingredient_category>": "ingredient_category"} or {"<specific_ingredient>": "specific_ingredient"} or {"<place>": "place"} or {"<person_name>": "person_name"}."""
    elif topic == "music":
        return """Return a dictionary like {"<song_name>": "song_name"} or {"<music_genre>": "music_genre"} or {"<artist_name>": "name of artist"} or {"<place>": "place"} or {"<listener_name>": "listener_name"}."""
    elif topic == "clothing":
        return """Return a dictionary like {"<clothing_type>": "clothing_type"} or {"<fashion_style>": "fashion_style"} or {"<place>": "place"} or {"<person_name>": "person_name"}."""
    elif topic == "transportation":
        return """Return a dictionary like {"<mode_of_transport>": "mode_of_transport"} or {"<vehicle_type>": "vehicle_type"} or {"<place>": "place"} or {"<person_name>": "person_name"}."""
    elif topic == "beverage":
        return """Return a dictionary like {"<drink_name>": "drink_name"} or {"<beverage_category>": "beverage_category"} or {"<place>": "place"} or {"<person_name>": "person_name"}."""
    else:
        return """- For unknown categories, return a dictionary in a similar format."""

def prepare_batch_requests(response_text_dict, category, client, filename="batch_requests.jsonl"):
    """ Generate a JSONL file for batch submission while retaining language and country information. """
    with open(filename, "wb") as f:
        request_id = 0
        for (language, country), response_list in response_text_dict.items():
            for response in response_list:
                request_id += 1
                example = get_example_for_topic(category)
                request_obj = {
                    "custom_id": f"{language}::{country}::{request_id}",  # Use "::" as a separator for easy parsing
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": "You are a helpful assistant."},
                            {
                                "role": "user",
                                "content": f"""Help me extract the words or phrases in the given text which are {get_topic_hint(category)}. 
Answer in a dictionary format, with the type of the extracted text labeled. 
{example}
Please ensure that you do not extract redundant entities. Do not provide any explanations, only output the dictionary in the format like:
{{"<extracted_text>": "type", "<extracted_text>": "type"}}
Text: {response}"""
                            }
                        ]
                    }
                }
                json_line = json.dumps(request_obj, ensure_ascii=False) + "\n"
                f.write(json_line.encode('utf-8'))  # Explicitly encode in UTF-8

    # Upload file to OpenAI
    file = client.files.create(
        file=open(filename, "rb"),
        purpose="batch"
    )
    return file.id

def submit_batch(client, file_id):
    """ Submit a batch API request. """
    batch = client.batches.create(
        input_file_id=file_id,
        endpoint="/v1/chat/completions",
        completion_window="24h"
    )
    print("Batch ID:", batch.id)
    return batch.id

def wait_for_batch_completion(batch_id, client):
    """ Poll the batch API until processing is completed. """
    while True:
        batch_status = client.batches.retrieve(batch_id)
        print(f"Batch Status: {batch_status.status}")
        
        if batch_status.status == "completed":
            return batch_status.output_file_id  # Return the result file URL
        elif batch_status.status == "failed":
            print("Batch failed!")
            return None
        
        time.sleep(10)  # Check every 10 seconds

def download_results(result_url, client, batch_id, save_dir="batch_results"):
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, f"batch_results_{batch_id}.jsonl")
    response = client.files.content(result_url)
    with open(save_path, "wb") as f:
        f.write(response.content)
    return save_path


def parse_batch_results(filename):
    """ Parse batch results and retain language and country information. """
    extracted_entities = []
    with open(filename, "r") as f:
        for line in f:
            data = json.loads(line)
            response_text =  data["response"]["body"]["choices"][0]["message"]["content"]
            
            # Parse custom_id to retrieve language and country
            custom_id = data["custom_id"]
            language, country, _ = custom_id.split("::")  # Extract language and country information
            
            extracted_entities.append({
                "language": language,
                "country": country,
                "response": response_text
            })
    return extracted_entities

# **Complete get_key_words function**
def get_key_words(response_text_dict, category):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY environment variable is required for entity extraction."
        )
    client = OpenAI(api_key=api_key)

    file_id = prepare_batch_requests(response_text_dict, category, client)  # Generate JSONL file
    batch_id = submit_batch(client, file_id)  # Submit batch request
    result_file = wait_for_batch_completion(batch_id, client)  # Wait for completion

    if result_file:
        save_path = download_results(result_file, client, batch_id)
        extracted_entities = parse_batch_results(save_path)  # Parse results
        return extracted_entities
    else:
        print("Batch processing failed.")
        return []
