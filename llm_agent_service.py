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
        return search_web(query)

    def _tool_list_videos(self, query):
        print(f"  [Clauwbot] Tool Use: list_videos -> {query}")
        all_videos = cfg.load_cache()
        results, intent = semantic_search(query, all_videos)
        # Return only a summary to save tokens
        summary = [f"{v['name']} ({v['full_path']})" for v in results[:10]]
        return f"Found {len(results)} videos. Top matching: " + ", ".join(summary)

    def _tool_get_status(self, _=None):
        import psutil
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        return f"System Status: CPU {cpu}%, RAM {mem}%. Server is running normally."

    def _build_system_prompt(self):
        return """
        ### ROLE
        You are "Clauwbot", a powerful AI Assistant integrated into a private Media Server. 
        You are smart, proactive, and speak natural Vietnamese.

        ### CAPABILITIES
        You can reason through complex tasks and use TOOLS if needed.
        
        ### TOOLS AVAILABLE
        1. web_search(query): Search the internet for latest info.
        2. list_videos(query): Search the internal video library.
        3. get_status(): Check server health.

        ### EXECUTION STYLE (THINK THEN ACT)
        If a task requires outside info, call a tool. 
        Format your reasoning as:
        THOUGHT: <your reasoning in Vietnamese>
        ACTION: <tool_name>(<arguments>)
        OBSERVATION: <result will be provided>
        ... repeat if needed ...
        FINAL ANSWER: <your comprehensive answer in Vietnamese>

        ### RULES
        - Always answer in Vietnamese.
        - Be concise but helpful.
        - If you don't need a tool, just give the FINAL ANSWER.
        """

    def chat(self, user_input):
        self.history.append({"role": "user", "content": user_input})
        
        # Max 3 reasoning steps to prevent loops
        for i in range(3):
            prompt = self._build_system_prompt() + "\n\n"
            for h in self.history:
                prompt += f"{h['role'].upper()}: {h['content']}\n"
            
            prompt += "ASSISTANT:"
            
            # Using LLM with json_format=False for reasoning/chat
            res = call_local_llm(prompt, json_format=False)
            
            if not res: return "Lỗi kết nối AI."

            # If LLM is forced to JSON, we need to extract the parts.
            # Let's assume for now Clauwbot follows the prompt.
            
            # Check for Action
            action_match = re.search(r'ACTION:\s*(\w+)\((.*?)\)', res)
            if action_match:
                tool_name = action_match.group(1)
                args = action_match.group(2).strip("'\"")
                
                if tool_name in self.tools:
                    obs = self.tools[tool_name](args)
                    self.history.append({"role": "assistant", "content": res})
                    self.history.append({"role": "system", "content": f"OBSERVATION: {obs}"})
                    continue
            
            # Check for Final Answer
            if "FINAL ANSWER:" in res:
                answer = res.split("FINAL ANSWER:")[1].strip()
                self.history.append({"role": "assistant", "content": res})
                return answer
            
            return res # Fallback

agent = ClauwbotAgent()

if __name__ == "__main__":
    while True:
        inp = input("You: ")
        print("Clauwbot:", agent.chat(inp))
