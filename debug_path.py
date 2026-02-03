import os
import unicodedata

path = r"C:\Users\hatha\Downloads\Video\YMDS-220 Con gái của một con sói. Cha dượng và anh trai.ts"

print(f"Checking: {path}")
print(f"Exists (original): {os.path.exists(path)}")

forms = ['NFC', 'NFD']
for form in forms:
    norm_path = unicodedata.normalize(form, path)
    print(f"Exists ({form}): {os.path.exists(norm_path)}")

# Also check parent directory
parent = os.path.dirname(path)
if os.path.exists(parent):
    print(f"Parent directory exists: {parent}")
    print("Files in parent:")
    try:
        for f in os.listdir(parent):
            if f.startswith("YMDS-220"):
                print(f" - Found match: {f}")
                print(f"   Name Normalization: {[unicodedata.name(c) for c in f if ord(c) > 127]}")
    except Exception as e:
        print(f"Error listing parent: {e}")
else:
    print(f"Parent directory NOT FOUND: {parent}")
