import search_service
import json

code = "ATID-583"
print(f"DEBUG: Searching context for {code}...")
context = search_service.search_jav_context(code)
print("-" * 50)
print("CONTEXT RETRIEVED:")
print(context)
print("-" * 50)
