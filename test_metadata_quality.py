
from search_service import search_jav_context
from llm_service import normalize_metadata_with_llm
import json

def run_test(filename):
    print(f"\n[PHÂN TÍCH] File: {filename}")
    
    # 1. Tìm context
    context = search_jav_context(filename)
    print(f"Context tìm thấy: {context[:200]}...")
    
    # 2. LLM Xử lý
    print("AI đang chuẩn hóa (LLM)...")
    result = normalize_metadata_with_llm(filename, context)
    
    if result:
        print("KẾT QUẢ AI TRẢ VỀ:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("AI không trả về kết quả.")

if __name__ == "__main__":
    # Thử nghiệm với các loại tên file khác nhau
    samples = [
        "ADN-413-C.ts",           # Mã JAV rõ ràng
        "MEYD-855-uncensored.ts", # Mã JAV kèm tag rác
        "Gai xinh thu dam solo.mp4" # Tên file tiếng Việt ko có mã
    ]
    
    with open("final_test_results.txt", "w", encoding="utf-8") as f_out:
        for s in samples:
            print(f"Testing: {s}...")
            # Capture print outputs if needed, or just write to file directly
            context = search_jav_context(s)
            result = normalize_metadata_with_llm(s, context)
            
            f_out.write(f"\n[PHÂN TÍCH] File: {s}\n")
            f_out.write(f"Context Found: {context[:200]}...\n")
            if result:
                f_out.write("AI Result:\n")
                f_out.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
            else:
                f_out.write("AI failed to return result.\n")
            f_out.write("-" * 50 + "\n")
    print("Done! Check final_test_results.txt")
