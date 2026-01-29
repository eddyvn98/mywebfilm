import json
import os
from constants import CONFIG_FILE

TAGS_FILE = "tags.json"

class TagManager:
    def __init__(self):
        self.tags = self.load_tags()

    def load_tags(self):
        if os.path.exists(TAGS_FILE):
            try:
                with open(TAGS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            "genres": [],
            "actors": [],
            "studios": []
        }

    def save_tags(self):
        with open(TAGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.tags, f, ensure_ascii=False, indent=4)

    def get_all(self):
        return self.tags

    def add_tags(self, category, values):
        """
        category: 'genres', 'actors', or 'studios' (singular 'studio' mapped to 'studios')
        values: list of strings
        """
        if category == 'studio': category = 'studios'
        if category not in self.tags: return

        changed = False
        current_set = set(self.tags[category])
        
        for v in values:
            v_clean = v.strip()
            if v_clean and v_clean not in current_set:
                self.tags[category].append(v_clean)
                current_set.add(v_clean)
                changed = True
        
        if changed:
            # Sort for easier finding
            self.tags[category].sort()
            self.save_tags()

tag_manager = TagManager()
