import json
import re
import time
from llm_service import call_local_llm, parse_llm_json
from search_service import search_web, semantic_search
import config_manager as cfg

class ClauwbotAgent:
    def __init__(self):
        self.history = []
        self.tools = {
            "web_search": self._tool_web_search,
            "list_videos": self._tool_list_videos,
            "get_status": self._tool_get_status
        }

    def _tool_web_search(self, query):
        print(f"  [Clauwbot] Tool Use: web_search -> {query}")
        results = search_web(query)
        if not results:
            return "No information found on the web."
        return f"Web Search Results for '{query}':\n{results}\n\n[Instruction: Use this data to formulate your FINAL ANSWER]"

    def _tool_list_videos(self, query):
        print(f"  [Clauwbot] Tool Use: list_videos -> {query}")
        all_videos = cfg.load_cache()
        results, intent = semantic_search(query, all_videos)
        # Return only a summary to save tokens
        summary = [f"- {v['name']} (Path: {v['full_path']})" for v in results[:10]]
        if not summary:
            return "No videos found in the local library matching that query."
        return f"Local Library Results:\n" + "\n".join(summary)

    def _tool_get_status(self, _=None):
        try:
            import psutil
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            return f"System Status: CPU {cpu}%, RAM {mem}%. Server is running normally."
        except ImportError:
            return "System Status: [psutil not installed] Server is running normally, but detailed stats are unavailable."
        except Exception as e:
            return f"System Status: [Error getting stats: {e}] Server is running."

    def _build_system_prompt(self):
        return """
        ### ROLE
        You are "Clauwbot", a persistent and smart AI Assistant. 
        Your goal is to solve the user's request NO MATTER WHAT. If one approach fails, you MUST try a DIFFERENT one.

        ### TOOLS (CRITICAL DIFFERENCE)
        1. web_search(query): USE THIS for any information NOT ON THIS COMPUTER. Use it for movie metadata, actor info, external sites (like MissAV, JavLibrary), or general knowledge.
           - If no results, try keywords like: "actor name", "movie code JAV", "site:domain.com query".
        2. list_videos(query): ONLY USE THIS to find actual files ALREADY STORED in the local folders. 
           - DO NOT use this tool to search for general movie information or external websites.
        3. get_status(): Check server health (CPU/RAM).

        ### REACT PROCESS (MANDATORY)
        You must follow this loop:
        THOUGHT: <Reasoning in Vietnamese. Analyze the previous Observation.>
        ACTION: <tool_name>(<args>)
        OBSERVATION: <Data from tool>
        
        ### CRITICAL TOOL SYNTAX
        - WRONG: web_search(query="movie name")
        - RIGHT: web_search("movie name")
        - NEVER assign parameters like `query=` or `search_query=` inside the action. 
        - Just put the string inside the parentheses.
        
        ### RULES
        - **ANTI-LOOPING**: NEVER repeat the exact same ACTION if the previous OBSERVATION was empty or an error. If `list_videos` failed, DO NOT call it again for the same query; use `web_search` instead.
        - **PERSISTENCE**: If `web_search` returns nothing, try searching in English or searching for the specific movie code or actor.
        - **LANGUAGE**: Always answer the FINAL ANSWER in Vietnamese.
        - **ACCURACY**: Do not guess movie codes. If user says OKSN-230, search for OKSN-230.
        """

    def chat(self, user_input):
        print(f"\n  [Clauwbot] === New Request: {user_input} ===")
        
        # Detect if user is asking something completely new to clear old "confused" history
        # If the input contains a new movie code but history has a different one, clear it.
        code_match = re.search(r'([a-zA-Z]{2,6}[-_]?\d{2,5})', user_input)
        if code_match:
            new_code = code_match.group(1).upper()
            has_old_code = any(new_code not in str(h['content']) for h in self.history if 'OBSERVATION' not in str(h['content']))
            if has_old_code and len(self.history) > 2:
                print(f"  [Clauwbot] Context switch detected. Clearing old history.")
                self.history = []

        self.history.append({"role": "user", "content": user_input})
        
        # Max history to keep context tight
        if len(self.history) > 8:
            self.history = self.history[-8:]

        # Increased to 5 steps for persistence
        for i in range(5):
            prompt = self._build_system_prompt() + "\n\n"
            for h in self.history:
                prompt += f"{h['role'].upper()}: {h['content']}\n"
            
            prompt += "ASSISTANT:"
            
            res = call_local_llm(prompt, json_format=False)
            if not res: 
                return "Lỗi kết nối AI. Vui lòng kiểm tra Ollama đang chạy."

            # Clean output for easier parsing (Xóa các dấu nối chuỗi kỳ lạ của AI)
            res = res.strip()
            print(f"  [Clauwbot] Step {i+1} Raw Output: {res[:200]}...")
            # Xử lý trường hợp AI sinh ra: ACTION: web_search("phim" + " mã")
            res = re.sub(r'\"\s*\+\s*\"', '', res)
            
            print(f"  [Clauwbot] Step {i+1} Thought: {res.split('ACTION:')[0].strip()[:100]}...")

            # Check for Action
            action_match = re.search(r'ACTION:\s*(\w+)\((.*?)\)', res, re.IGNORECASE)
            if action_match:
                tool_name = action_match.group(1).lower()
                # Làm sạch args triệt để (Xử lý các lỗi phổ biến như query=, dấu ngoặc kép thừa)
                raw_args = action_match.group(2).strip("'\" ")
                # Xóa cụm 'query=' nếu AI lỡ viết vào
                clean_args = re.sub(r'^query\s*=\s*', '', raw_args).strip("'\" ")
                # Xử lý các dấu cộng kết nối chuỗi rác
                clean_args = clean_args.replace('"+ "', '').replace(' + ', '') 
                
                if tool_name in self.tools:
                    try:
                        obs = self.tools[tool_name](clean_args)
                        self.history.append({"role": "assistant", "content": res})
                        self.history.append({"role": "system", "content": f"OBSERVATION: {obs}"})
                        print(f"  [Clauwbot] Observation: {str(obs)[:100]}...")
                        continue
                    except Exception as te:
                        self.history.append({"role": "assistant", "content": res})
                        self.history.append({"role": "system", "content": f"OBSERVATION: Error using tool {tool_name}: {te}"})
                        continue
            
            # Check for Final Answer
            if "FINAL ANSWER:" in res:
                answer = res.split("FINAL ANSWER:")[1].strip()
                self.history.append({"role": "assistant", "content": res})
                return answer
            
            # Fallback for direct responses
            if i == 0 and "THOUGHT:" not in res and "ACTION:" not in res:
                self.history.append({"role": "assistant", "content": res})
                return res

            self.history.append({"role": "assistant", "content": res})

        return "Sau 5 lần cố gắng tìm kiếm, tôi vẫn chưa tìm thấy thông tin chính xác. Bạn có thể cung cấp thêm tên diễn viên hoặc từ khóa khác được không?"

agent = ClauwbotAgent()

if __name__ == "__main__":
    while True:
        inp = input("You: ")
        print("Clauwbot:", agent.chat(inp))
