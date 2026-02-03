import json
import os

def recover_f_drive_videos():
    cache_file = "movies_cache.json"
    output_file = "F_drive_recovered_list.txt"
    
    if not os.path.exists(cache_file):
        print(f"Error: {cache_file} not found.")
        return

    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        f_drive_videos = []
        for video in data:
            full_path = video.get("full_path", "")
            if full_path.lower().startswith("f:"):
                # Extract useful info
                name = video.get("name", "Unknown Name")
                jav_code = ""
                jav_title = ""
                
                jav_meta = video.get("jav_metadata")
                if jav_meta:
                    jav_code = jav_meta.get("code", "")
                    jav_title = jav_meta.get("title", "")
                
                # Format the output line
                # Priority: JAV Code -> JAV Title -> Name -> Path
                display_line = ""
                if jav_code:
                     display_line += f"[{jav_code}] "
                
                if jav_title:
                    display_line += f"{jav_title}"
                else:
                    display_line += f"{name}"
                
                display_line += f"  (Path: {full_path})"
                
                f_drive_videos.append(display_line)
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"Total found: {len(f_drive_videos)}\n")
            f.write("="*50 + "\n")
            for line in f_drive_videos:
                f.write(line + "\n")
                
        print(f"Successfully recovered {len(f_drive_videos)} videos. Saved to {output_file}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    recover_f_drive_videos()
