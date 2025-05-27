from tqdm import tqdm
import transformers
import torch
from openai import OpenAI
import os
import time
import json
import numpy as np
import time
import wikipedia as wp
from transformers import AutoModelForCausalLM, AutoTokenizer

def llm_init(model_name):
    global device
    global model
    global tokenizer
    global pipeline

    if model_name == "mistral":
        
        device = "cuda"
        model = AutoModelForCausalLM.from_pretrained("mistralai/Mistral-7B-Instruct-v0.1", torch_dtype=torch.bfloat16)
        tokenizer = AutoTokenizer.from_pretrained("mistralai/Mistral-7B-Instruct-v0.1")
        model.to(device)

    if model_name == "llama3_70b":
        device = "cuda"
        model = AutoModelForCausalLM.from_pretrained("meta-llama/Llama-3.1-70B-Instruct", device_map="auto", torch_dtype=torch.bfloat16)
        tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-70B-Instruct")

    if model_name == "llama2_7b":
        device = "cuda"
        model = AutoModelForCausalLM.from_pretrained("meta-llama/Llama-2-7b-chat-hf", torch_dtype=torch.bfloat16)
        tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-2-7b-chat-hf")
        model.to(device)

    if model_name == "llama2_13b":
        device = "cuda"
        model = AutoModelForCausalLM.from_pretrained("meta-llama/Llama-2-13b-chat-hf", device_map="auto", torch_dtype=torch.bfloat16)
        tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-2-13b-chat-hf")
    
    if model_name == "llama3":
        device = "cuda"
        model = AutoModelForCausalLM.from_pretrained("meta-llama/Llama-3.1-8B-Instruct", device_map="auto", torch_dtype=torch.bfloat16)
        tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-8B-Instruct")
        #model.to(device)
    if model_name == "qwen":
        device = "cuda"
        model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-7B-Instruct", device_map="auto", torch_dtype=torch.bfloat16)
        tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-7B-Instruct")
    if model_name == "aya":
        device = "cuda"
        model = AutoModelForCausalLM.from_pretrained("CohereLabs/aya-expanse-8b", device_map="auto", torch_dtype=torch.bfloat16)
        tokenizer = AutoTokenizer.from_pretrained("CohereLabs/aya-expanse-8b")
    if model_name == "deepseek":
        client = OpenAI(api_key="sk-fe66b828e09e45a3ba34ec9b3caf05ee", base_url="https://api.deepseek.com")


    if model_name == "chatgpt":
        client = OpenAI(api_key="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")  # Fill in your API key

def llm_response(prompt, model_name, num_responses, language=None, save_path = None, deep_seek_api = "sk-fe66b828e09e45a3ba34ec9b3caf05ee",temperature = 0.7, max_new_tokens = 100):
    language_instruction_map = {
    "en": "Please answer in English.",
    "zh": "请用中文作答。",
    "zh-tw": "請用繁體中文作答。",
    "de": "Bitte antworten Sie auf Deutsch.",
    "it": "Si prega di rispondere in italiano.",
    "yo": "Jọwọ dahun ni ede Yoruba.",
    "ha": "Don Allah ku amsa da Hausa.",
    "ar": "يرجى الرد باللغة العربية.",
    "tr": "Lütfen Türkçe cevap verin.",
    "fa": "لطفاً به زبان فارسی پاسخ دهید.",
    "th": "กรุณาตอบเป็นภาษาไทย",
    "ja": "日本語で答えてください。",
    "ko": "한국어로 대답해주세요.",
    "hi": "कृपया हिंदी में उत्तर दें।"
}

    if model_name in ["mistral", "llama3","llama3_70b","qwen","aya"]:
        if model_name == "mistral":
            if language is not None:
                instruction = language_instruction_map.get(language, f"Please answer in {language}.")
                prompt = prompt[0] + instruction
        messages = [
        {"role": "user", "content": prompt},
        ]
        if model_name == "aya":
            if language is not None:
                instruction = language_instruction_map.get(language, f"Please answer in {language}.")
                prompt = prompt[0] #+ instruction
        messages = [
        {"role": "user", "content": prompt},
        ]
        if model_name == "qwen":
            if language is not None:
                instruction = language_instruction_map.get(language, f"Please answer in {language}.")
                prompt = prompt[0] + instruction
            messages = [
    {"role": "system", "content": "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."},
    {"role": "user", "content": prompt}
]

        encodeds = tokenizer.apply_chat_template(messages, return_tensors="pt")

        model_inputs = encodeds.to(device)

        outputs = model.generate(
        model_inputs,
        max_new_tokens=100,
        do_sample=True,
        return_dict_in_generate=True,
        output_scores=True,
        temperature=0.8,
        pad_token_id=tokenizer.eos_token_id,
        num_return_sequences=num_responses  # Generate multiple responses
    )
        generated_texts = []
        prefix = "assistant\n\n"
        input_length = encodeds.shape[1]
        for seq in outputs.sequences:
            generated_ids = seq[input_length:]
            generated_text = tokenizer.decode(generated_ids, skip_special_tokens=True)
            if generated_text.startswith(prefix):
                generated_text = generated_text[len(prefix):]
            generated_texts.append(generated_text)
    
        return generated_texts
    
    if model_name == "chatgpt":
        responses = []
        client = OpenAI(api_key="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")  # Fill in your API key

        for i in range(num_responses):
            response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt[0]}
        ]
    )
            responses.append(response.choices[0].message.content)
            time.sleep(0.1)
        return responses
    if model_name == "deepseek":
        responses = []
        # for backward compatibility, you can still use `https://api.deepseek.com/v1` as `base_url`.
        client = OpenAI(api_key=deep_seek_api, base_url="https://api.deepseek.com")

        for i in range(num_responses):

            response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": prompt[0]},
        ]
        )
            responses.append(response.choices[0].message.content)
            if save_path:
                tmp_response_path = os.path.join(save_path, f"tmp_{language}_{model_name}.json")
                with open(tmp_response_path, "w", encoding="utf-8") as f:
                    json.dump(responses, f, indent=2, ensure_ascii=False)
            #print("!TEXT!",response.choices[0].message.content)
            time.sleep(0.1)
        return responses
        
    
