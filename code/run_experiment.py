import json
from datetime import datetime
import argparse
import os
import logging
from entity_extraction import get_key_words
from analysis_food import fetch_wikidata_food_info
from analysis_beverage import fetch_wikidata_beverage_info
from analysis_clothing import fetch_wikidata_clothing_info
from analysis_music import fetch_wikidata_music_info
from analysis_transportation import fetch_wikidata_transportation_info
from analysis_book import fetch_wikidata_book_info
from tqdm import tqdm
import torch
import pandas as pd
import sys
import json
import shlex
from collections import defaultdict, Counter
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import prompt_construct
import lm_utils
import re
import gc

# Set up result directory
RESULT_DIR = "results"
os.makedirs(RESULT_DIR, exist_ok=True)

deep_seek_api_keys = []
if __name__ == "__main__":
    

    # Argument parsing
    argParser = argparse.ArgumentParser()
    argParser.add_argument("-m", "--model", help="which language model to use: \"mistral\", \"llama2_7/13/70b\", \"chatgpt\"")
    argParser.add_argument("-l", "--language", default="all", help="which language the prompt should use")
    argParser.add_argument("-c", "--category", default="food", help="which category to test")
    argParser.add_argument("-b", "--bias", default="non-bias", help="which kind of bias should test, non-bias, country, male, female")
    argParser.add_argument("-country", "--country", default="null", help="which country should be tested for culture bias")
    argParser.add_argument("-n", "--num_response", default=100, help="amounts of responses to each prompt")
    argParser.add_argument("-k", "--key", default=0, help="api")
    args = argParser.parse_args()

    model_name = args.model
    language = args.language
    category = args.category
    bias = args.bias
    country = args.country
    deep_seek_api =  deep_seek_api_keys[int(args.key)]
    num_response = int(args.num_response)

    # Create a unique subdirectory for each run based on timestamp
    run_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    run_dir = os.path.join(RESULT_DIR, f"{run_timestamp}_{model_name}_{bias}_{category}_{country}_{num_response}")
    os.makedirs(run_dir, exist_ok=True)

    # Configure logging
    log_filename = os.path.join(run_dir, "log.txt")
    logging.basicConfig(
        filename=log_filename,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    start_time = datetime.now()  # Record start time
    logging.info("Program execution started")
    logging.info(f"Arguments: {vars(args)}")

    # Initialize language model
    lm_utils.llm_init(model_name)

        # Save prompt configuration
    prompt_config_path = os.path.join(run_dir, "prompt.json")
    prompt_data = {
        "model": model_name,
        "language": language,
        "category": category,
        "bias": bias,
        "country": country,
        "num_response": num_response,
        "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    with open(prompt_config_path, "w", encoding="utf-8") as f:
        json.dump(prompt_data, f, indent=4, ensure_ascii=False)
    
    logging.info(f"Prompt settings saved to {prompt_config_path}")
    with open("meta_info/name.json", "r", encoding="utf-8") as file:
        name_data = json.load(file)

    # Construct prompts based on language selection
    if language == "all":
        print(category)
        print(bias)
        prompts_group = prompt_construct.search_category_bias("meta_info/prompt.json", category, bias)
        prompts = []
        for entry in prompts_group:
            if entry['text']:
                prompts.append({entry['language']: entry['text']})
    else:
        print(prompt_construct.search_category_bias("meta_info/prompt_backup.json", category, bias, language_filter=language))
        prompts = [{f"{language}": prompt_construct.search_category_bias("meta_info/prompt.json", category, bias, language_filter=language)[0]['text']}]
        print(prompts)

    # Load country list
    with open("meta_info/country.json", "r", encoding="utf-8") as file:
        country_list = json.load(file)

    prompts_filled = defaultdict(list)  # Store prompts by language
    country_info_list = defaultdict(list)  # Store corresponding country information by language

    # Fill placeholders with country names (only if bias is not 'nonbias')
    match bias:
        case "nonbias":
            for prompt_dict in prompts:
                language = list(prompt_dict.keys())[0]
                filled_prompt = prompt_dict[language]  # No .format()
                prompts_filled[language].append(filled_prompt)
                country_info_list[language].append("null")  # or "N/A"

        case "name_male" | "name_female":
            if not country or country == "all":
                for country_name, country_info in country_list.items():
                    for prompt_dict in prompts:
                        language = list(prompt_dict.keys())[0]
                        localized_country = country_info['name'].get(language, country_name)

                        if country_name in name_data:
                            name_info = name_data[country_name]['common_names'][bias]
                            first_name = name_info['first'][0]
                            last_name = name_info['last'][0]
                            full_name = f"{first_name} {last_name}"
                        else:
                            full_name = "John Doe"  # fallback

                        filled_prompt = prompt_dict[language].format(
                            **{bias: full_name}
                        )
                        prompts_filled[language].append(filled_prompt)
                        country_info_list[language].append(country_name)
            else:
                for prompt_dict in prompts:
                    language = list(prompt_dict.keys())[0]
                    if country not in country_list:
                        raise ValueError(f"Country '{country}' not found in country_list.")
                    localized_country = country_list[country]['name'].get(language, country)

                    if country in name_data:
                        name_info = name_data[country]['common_names'][bias]
                        first_name = name_info['first'][0]
                        last_name = name_info['last'][0]
                        full_name = f"{first_name} {last_name}"
                    else:
                        print("NO NAME FOUND")
                    filled_prompt = prompt_dict[language].format(
                        **{bias: full_name}
                    )
                    prompts_filled[language].append(filled_prompt)
                    country_info_list[language].append(country)

        case _:  # default: other bias values
            if not country or country == "all":
                for country_name, country_info in country_list.items():
                    for prompt_dict in prompts:
                        language = list(prompt_dict.keys())[0]
                        localized_country = country_info['name'].get(language, country_name)
                        filled_prompt = prompt_dict[language].format(
                            country=localized_country
                        )
                        prompts_filled[language].append(filled_prompt)
                        country_info_list[language].append(country_name)
            else:
                for prompt_dict in prompts:
                    language = list(prompt_dict.keys())[0]
                    if country not in country_list:
                        raise ValueError(f"Country '{country}' not found in country_list.")
                    localized_country = country_list[country]['name'].get(language, country)
                    filled_prompt = prompt_dict[language].format(
                        country=localized_country
                    )
                    prompts_filled[language].append(filled_prompt)
                    country_info_list[language].append(country)


    # Generate responses and organize them in the final dictionary
    response_text = {}
    for language, language_prompts in prompts_filled.items():
        print(f"Generating responses for language: {language}...")
        response_text[language] = []
        SAVE_INTERVAL = 50  # 每 5 个 prompt 就保存一次
        save_counter = 0

        for idx, prompt in enumerate(language_prompts):
            country_name = country_info_list[language][idx]  # Get the country corresponding to the current prompt
            responses = lm_utils.llm_response([prompt], model_name, num_response, language, run_dir, deep_seek_api)
            response_text[language].append({
                "prompt": prompt,
                "category": category,
                "bias": bias,
                "country": country_name,  # Store country information
                "responses": responses
            })
            save_counter += 1
            if model_name.lower() == "deepseek" and save_counter % SAVE_INTERVAL == 0:
                tmp_path = os.path.join(run_dir, f"tmp_{model_name}_{category}_{bias}_{country}_{num_response}.json")
                with open(tmp_path, "w", encoding="utf-8") as file:
                    json.dump(response_text, file, indent=4, ensure_ascii=False)
                logging.info(f"[Auto-Save] Saved intermediate responses to {tmp_path}")

    # Save the generated responses to a JSON file
    generated_text_dir = os.path.join(run_dir, "generated_text")
    os.makedirs(generated_text_dir, exist_ok=True)  # Ensure the directory exists
    generated_text_path = os.path.join(generated_text_dir, f"{model_name}_{category}_{bias}_{country}_{num_response}.json")
    with open(generated_text_path, "w", encoding="utf-8") as file:
        json.dump(response_text, file, indent=4, ensure_ascii=False)

    excluded_models = ["chatgpt", "deepseek"]
    if torch.cuda.is_available() and all(name not in args.model.lower() for name in excluded_models):
        del lm_utils.model
        del lm_utils.tokenizer
        gc.collect()
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()
        logging.info("GPU memory released after response generation.")

    extracted_entities = []
    # Iterate through the response_text and extract entities
    for language, language_responses in response_text.items():
        for entry in language_responses:
            category = entry["category"]
            country_name = entry["country"]
            for response in tqdm(entry["responses"]):
                # Note: get_key_words now returns a dictionary format
                entities = get_key_words(response, category)
                extracted_entities.append({
                    "language": language,
                    "category": category,
                    "country": country_name,
                    "response": response,
                    "entities": entities
                })
    #batch api too slow, batch backup
    # Create a dictionary to store all responses grouped by the same language and country
    # grouped_responses = defaultdict(list)

    # # Group by language and country
    # for language, language_responses in response_text.items():
    #     for entry in language_responses:
    #         category = entry["category"]
    #         country_name = entry["country"]
    #         responses = entry["responses"]
    #         grouped_responses[(language, country_name, category)].extend(responses)

    # extracted_entities = []
    # for (language, country_name, category), responses in grouped_responses.items():
    #     # Pass the entire response list while retaining mapping information
    #     response_text_dict = {(language, country_name): responses}  # Maintain structure
    #     entities_list = get_key_words(response_text_dict, category)  

    #     # Ensure correct mapping of extracted entities to original responses
    #     for entity_info in entities_list:
    #         extracted_entities.append({
    #             "language": entity_info["language"],
    #             "category": category,
    #             "country": entity_info["country"],
    #             "entities": entity_info["response"]  # Extracted keywords
    #         })
    # Save extracted entities to a JSON file
    entity_dir = os.path.join(run_dir, "entity")
    os.makedirs(entity_dir, exist_ok=True)  # Ensure the directory exists
    entity_path = os.path.join(entity_dir, f"{model_name}_{category}_{bias}_{country}_{num_response}.json")
    with open(entity_path, "w", encoding="utf-8") as file:
        json.dump(extracted_entities, file, indent=4, ensure_ascii=False)
        # Read the JSON file
    with open(entity_path, "r", encoding="utf-8") as file:
        extracted_entities = json.load(file)

    wikidata_results = defaultdict(list)

# Group entities by (language, country, category) and count their frequency,
    # while also storing the entity type.
    grouped_entities = defaultdict(dict)  # key: (language, country, category), value: {entity: {"type": ..., "count": ...}}

    for entry in tqdm(extracted_entities, desc="Collecting entities"):
        language = entry["language"].lower()
        country = entry["country"]
        if country is None:
            country = "null"
        else:
            country = country.lower()
        category = entry["category"]
        #entities = entry["entities"].replace("“", "\"").replace("”", "\"").replace("\n", "").replace("{{", "{").replace("}}", "}")  # Format: {entity: type, ...}
        try:
            entities = entry["entities"].replace("“", "\"").replace("”", "\"") \
                                       .replace("\n", "") \
                                       .replace("{{", "{").replace("}}", "}")
            print(entities)
            entities = json.loads(re.sub(r"},\s*{", ", ", entities))
        except json.JSONDecodeError as e:
            print(f"Skipping entry due to JSON error: {e}")
            
            continue
        key = (language, country, category)
        for entity, ent_type in entities.items():
            # Skip place and person name entities
            if ent_type.lower() in ['place', 'person_name']:
                continue
            if entity in grouped_entities[key]:
                grouped_entities[key][entity]["count"] += 1
            else:
                grouped_entities[key][entity] = {"type": ent_type, "count": 1}

    # For each (language, country, category) group, fetch corresponding Wikidata info
    for (language, country, category), entity_info in tqdm(grouped_entities.items(), desc="Fetching Wikidata info"):
        # Filter out place and person entities before processing
        filtered_entity_info = {
            entity: info 
            for entity, info in entity_info.items()
            if info['type'].lower() not in ['place', 'person_name', 'listener_name', 'reader_name']
        }
        
        entity_list = list(filtered_entity_info.keys())  # Get filtered entities
        
        if entity_list:
            fetch_function_name = f"fetch_wikidata_{category}_info"
            if fetch_function_name in globals():
                fetch_function = globals()[fetch_function_name]
            else:
                print(f"Warning: Function {fetch_function_name} not found. Skipping category '{category}'.")
                continue

            df_wikidata = fetch_function(entity_list, language)  # Fetch Wikidata data for the group

            # Distribute the Wikidata results back to the corresponding group in each entry
            for entry in extracted_entities:
                if country == None:
                    country = "null"
                if entry["country"] ==None:
                    entry["country"] = "null"
                if entry["language"].lower() == language and entry["country"].lower() == country and entry["category"] == category:
                    try:
                        cleaned = entry["entities"].replace("“", "\"").replace("”", "\"") \
                                                .replace("\n", "") \
                                                .replace("{{", "{").replace("}}", "}")
                        entry_entities = set(json.loads(re.sub(r"},\s*{", ", ", cleaned)).keys())
                    except json.JSONDecodeError as e:
                        print(f"Skipping entry due to JSON error: {e}")
                        continue# Filter rows corresponding to the current entry's entities
                    filtered_df = df_wikidata[df_wikidata["Original Label"].isin(entry_entities)].copy()
                    if not filtered_df.empty:
                        # Add Frequency column safely
                        filtered_df.loc[:, "Frequency"] = filtered_df["Original Label"].map(
                            lambda x: filtered_entity_info.get(x, {}).get("count", 0)
                        )
                        # Add Entity_Type column to store the type information
                        filtered_df.loc[:, "Entity_Type"] = filtered_df["Original Label"].map(
                            lambda x: filtered_entity_info.get(x, {}).get("type", "")
                        )
                        wikidata_results[(language, country, category)].append(filtered_df)
                    else:
                        print(f"No matching Wikidata results for {(language, country, category)}")
        else:
            print(f"No valid entities to process for ({language}, {country}).")

        # Merge and save Wikidata results for each (language, country, category) group
        for (language, country, category), df_list in wikidata_results.items():
            merged_df = pd.concat(df_list, ignore_index=True)  # Combine all DataFrames
            merged_df = merged_df.drop_duplicates()  # Remove duplicate rows

            # Convert 'Original Label' to lowercase for comparison
            merged_df["Original Label Lower"] = merged_df["Original Label"].str.lower()
            duplicate_labels = merged_df["Original Label Lower"].duplicated(keep=False)

            # Filter out rows where there are duplicates and one of them has Q_ID as "NA"
            def filter_nan_qid(group):
                if len(group) > 1 and "NA" in group["Q_ID"].values:
                    return group[group["Q_ID"] != "NA"]
                return group
            merged_df = merged_df.groupby("Original Label Lower", group_keys=False).apply(filter_nan_qid)
            
            merged_df["Specificity Level"] = ""
            merged_df["Universality"] = ""
            merged_df = merged_df.drop(columns=["Original Label Lower"])

            wiki_dir = os.path.join(run_dir, "wikidata_results")
            os.makedirs(wiki_dir, exist_ok=True)
            wiki_path = os.path.join(wiki_dir, f"{model_name}_{category}_{bias}_{language}_{country}_{num_response}.csv")

            # Save the full dataset
            merged_df.to_csv(wiki_path, index=False, encoding="utf-8-sig")
            
            # Save filtered dataset (only records where is_category is 'Yes')
            filtered_df = merged_df[merged_df['is_category'] == 'Yes']
            filtered_wiki_path = os.path.join(wiki_dir, f"{model_name}_{category}_{bias}_{language}_{country}_{num_response}_filtered.csv")
            filtered_df.to_csv(filtered_wiki_path, index=False, encoding="utf-8-sig")
            
            print(f"Saved merged Wikidata results to {wiki_path}")

        print("\nAll Wikidata analyses have been saved successfully.")

        # Record the end time
        end_time = datetime.now()
        elapsed_time = (end_time - start_time).total_seconds()
        logging.info(f"Program execution completed, total time: {elapsed_time:.2f} seconds")

        # Save runtime log
        runtime_log_path = os.path.join(run_dir, "runtime.json")
        runtime_data = {
            "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed_time_seconds": elapsed_time,
            "elapsed_time_hours": elapsed_time / 3600
        }
        with open(runtime_log_path, "w", encoding="utf-8") as f:
            json.dump(runtime_data, f, indent=4, ensure_ascii=False)
        logging.info(f"Execution time log saved to {runtime_log_path}")
