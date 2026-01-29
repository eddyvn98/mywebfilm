
from search_service import search_jav_context
from llm_service import normalize_metadata_with_llm
import json

def test_llm_pipeline(filename):
    print(f"\n" + "="*50)
    print(f"Testing Filename: {filename}")
    
    # 1. Search for context
    # Không dùng extract_code nữa, search thẳng bằng tên file
    context = search_jav_context(filename)
    print(f"Context Found (first 100 chars): {context[:100]}...")
    
    # 2. Call LLM
    print("Calling local LLM (Ollama)...")
    result = normalize_metadata_with_llm(filename, context)
    
    if result:
        print("LLM Result:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("LLM failed to return a valid result.")

if __name__ == "__main__":
    # Test cases
    test_cases = [
        "ADN-413.mp4",
        "MEYD-855-Uncensored.ts",
        "IMG_20220430_134834.jpg" # This should ideally be ignored by extract_code
    ]
    
    for tc in test_cases:
        test_llm_pipeline(tc)
