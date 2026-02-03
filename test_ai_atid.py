import llm_service
import search_service
import json

filename = "ATID-583.mp4"
print(f"1. Searching context for {filename}...")
context = search_service.search_jav_context(filename)

print(f"2. Calling AI with refined prompt...")
prompt = llm_service.create_analyzer_prompt(filename, context)
print("-" * 30)
print("PROMPT:")
print(prompt)
print("-" * 30)

response = llm_service.call_local_llm(prompt)
print("RAW RESPONSE:")
print(response)
print("-" * 30)

result = llm_service.parse_llm_json(response)
print("PARSED RESULT:")
print(json.dumps(result, indent=4, ensure_ascii=False))
