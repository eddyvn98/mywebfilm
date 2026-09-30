"""
sort_engine.py - Core engine for Video Auto-Sort Web Dashboard.
Handles: scan, classify, actress lookup (jav321), move files.
"""
import os, re, json, time, urllib.request, shutil
from collections import Counter
from datetime import datetime

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE    = os.path.join(BASE_DIR, "actress_cache.json")
DRIVE_MAP_FILE = os.path.join(BASE_DIR, "sorted_drive_map.json")
INCOMING_DIRS = ["E:\\Incoming", "G:\\Incoming", "H:\\Incoming"]
SORTED_ROOTS = ["G:\\Sorted_Videos", "H:\\Sorted_Videos", "E:\\Sorted_Videos"]
VIDEO_EXTS    = {".mp4",".mkv",".avi",".wmv",".mov",".flv",".mpeg",".3gp",".webm",".ts",".m2ts"}
SORT_DRIVE_ORDER = ["G", "H", "E"]
MIN_FREE_RATIO = 0.10

JAV_RE  = re.compile(r"\b([A-Za-z]{2,8})-([0-9]{3,5})\b")
THOT_RE = re.compile(r"\b([NnKk][0-9]{4})\b")
CAR_RE  = re.compile(r"\b([0-9]{6})-([0-9]{3})\b")

VN_KW = ["djt","dit","chich","thu dam","bu cu","ban tinh","nung","hoc sinh","em gai","co giao","ban than","quay len","nha ve sinh","tu suong","nen"]
ACCENTS = "aaaaaaaaaaaaaeeeeeeeeeeeiiiiiooooooooooooouuuuuuuuuuuyyyyyd"

HEADERS = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"}


def load_drive_map():
    if not os.path.exists(DRIVE_MAP_FILE):
        return {}
    try:
        with open(DRIVE_MAP_FILE, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_drive_map(data):
    try:
        with open(DRIVE_MAP_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def drive_free_ratio(letter):
    root = f"{letter}:\\"
    try:
        total, used, free = shutil.disk_usage(root)
        if total <= 0:
            return 0.0
        return free / total
    except Exception:
        return 0.0


def pick_destination_drive(group_key, drive_map):
    mapped = drive_map.get(group_key)
    if mapped in SORT_DRIVE_ORDER and drive_free_ratio(mapped) > MIN_FREE_RATIO:
        return mapped

    available = [d for d in SORT_DRIVE_ORDER if os.path.isdir(f"{d}:\\")]
    for d in available:
        if drive_free_ratio(d) > MIN_FREE_RATIO:
            drive_map[group_key] = d
            save_drive_map(drive_map)
            return d

    fallback = max(available or SORT_DRIVE_ORDER, key=drive_free_ratio)
    drive_map[group_key] = fallback
    save_drive_map(drive_map)
    return fallback

def load_cache():
    return json.load(open(CACHE_FILE,encoding="utf-8")) if os.path.exists(CACHE_FILE) else {}

def save_cache(c):
    json.dump(c, open(CACHE_FILE,"w",encoding="utf-8"), ensure_ascii=False, indent=2)

def classify(fn):
    fl = fn.lower()
    m = JAV_RE.search(fn);
    if m: return "JAV", m.group(1).upper()
    if THOT_RE.search(fn): return "JAV","TOKYO_HOT"
    if CAR_RE.search(fn):  return "JAV","CARIBBEANCOM"
    if "screenrecorder" in fl or fl.startswith("vid_") or "video_download_" in fl: return "Recordings_and_Clips",None
    if any(k in fl for k in VN_KW): return "Vietnamese_Leaks",None
    # Vietnamese accent detection
    if any(c in fn for c in "\u00e1\u00e0\u1ea3\u00e3\u1ea1\u0103\u1eaf\u1eb1\u00e2\u1ea5\u00e9\u00e8\u1ebb\u1eb9\u1ebf\u00ed\u00ec\u1ecb\u00f3\u00f2\u1ecf\u00f4\u1ed1\u01a1\u1edb\u00fa\u00f9\u1ee7\u01b0\u1ee9\u00fd\u1ef3\u0111"): return "Vietnamese_Leaks",None
    return "Uncategorized",None

def jav_code(fn):
    m = JAV_RE.search(fn)
    return f"{m.group(1).upper()}-{m.group(2)}" if m else None

def jav321_id(code):
    m = JAV_RE.match(code)
    return f"{m.group(1).lower()}{m.group(2).zfill(5)}" if m else None

def fetch_actresses(code, retries=2):
    jid = jav321_id(code)
    if not jid: return []
    url = f"https://www.jav321.com/video/{jid}"
    for _ in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            html = urllib.request.urlopen(req, timeout=10).read().decode("utf-8","replace")
            sec = re.search(r"\u51fa\u6f14\u8005.*?<br", html, re.DOTALL)
            if sec:
                names = re.findall(r"/star/\d+/1\">(.*?)</a>", sec.group())
                if names: return [n.strip() for n in names]
            return []
        except urllib.error.HTTPError as e:
            if e.code == 404: return []
            time.sleep(1)
        except: time.sleep(2)
    return []

def others_group(p):
    c = p[0].upper() if p else ""
    if not c or not c.isalpha(): return "Others_Numbers"
    if c<="D": return "Others_A_D"
    if c<="H": return "Others_E_H"
    if c<="L": return "Others_I_L"
    if c<="P": return "Others_M_P"
    if c<="T": return "Others_Q_T"
    return "Others_U_Z"

def date_prefix(fn, mtime):
    m = re.search(r"(20[0-2][0-9])[-_]([0-1][0-9])[-_][0-3][0-9]", fn)
    if m: return f"{m.group(1)}-{m.group(2)}"
    m = re.search(r"(20[0-2][0-9])([0-1][0-9])[0-3][0-9]", fn)
    if m: return f"{m.group(1)}-{m.group(2)}"
    return datetime.fromtimestamp(mtime).strftime("%Y-%m") if mtime else "Unknown"

def sanitize(n):
    for c in r'<>:"/\|?*': n = n.replace(c,"_")
    return n.strip()

def unique_path(src, dst):
    if os.path.abspath(src)==os.path.abspath(dst): return dst
    if not os.path.exists(dst): return dst
    base,ext = os.path.splitext(dst); i=1
    while True:
        cand=f"{base}_{i}{ext}"
        if not os.path.exists(cand): return cand
        i+=1

class SortEngine:
    def __init__(self, on_progress=None, dry_run=True):
        self.on_progress = on_progress
        self.dry_run = dry_run
        self.cache = load_cache()
        self.drive_map = load_drive_map()
        self._state = {"status":"idle","total":0,"done":0,"current_file":"","moved":[],"pending_review":[],"errors":[]}

    def _emit(self, **kw):
        self._state.update(kw)
        if self.on_progress: self.on_progress(dict(self._state))

    def _scan_roots(self, roots):
        videos = []
        for d in roots:
            if not os.path.isdir(d):
                continue
            drv = d[0]
            for root,dirs,files in os.walk(d):
                dirs[:] = [x for x in dirs if x not in {"Sorted_Videos","$RECYCLE.BIN","System Volume Information",".mycinema"}]
                if ".mycinema" in root:
                    continue
                for fn in files:
                    if os.path.splitext(fn)[1].lower() in VIDEO_EXTS:
                        fp = os.path.join(root,fn)
                        try: mt = os.path.getmtime(fp)
                        except: mt = 0.0
                        videos.append({"path":fp,"drive":drv,"filename":fn,"mtime":mt})
        return videos

    def scan(self):
        return self._scan_roots(INCOMING_DIRS)

    def scan_sorted_library(self):
        return self._scan_roots(SORTED_ROOTS)

    def lookup_actress(self, code):
        if code in self.cache: return self.cache[code]
        actresses = fetch_actresses(code)
        self.cache[code] = actresses
        save_cache(self.cache)
        return actresses

    def plan_move(self, v, pcounts):
        drv,fn,src,mt = v["drive"],v["filename"],v["path"],v["mtime"]
        cat,sub = classify(fn)
        if cat=="JAV":
            sf = sub if sub in {"TOKYO_HOT","CARIBBEANCOM"} else (sub if pcounts[sub]>=5 else others_group(sub))
            group_key = f"JAV/{sf}"
            dest_drive = pick_destination_drive(group_key, self.drive_map)
            sdst = unique_path(src, os.path.join(f"{dest_drive}:\\Sorted_Videos","JAV",sf,fn))
            code = jav_code(fn); actresses=[]
            if code and sub not in {"TOKYO_HOT","CARIBBEANCOM"}:
                actresses = self.lookup_actress(code)
                time.sleep(0.3)
            if actresses:
                adsts=[{"actress":n,"dst":unique_path(src,os.path.join(f"{dest_drive}:\\Sorted_Videos","JAV_By_Actress",sanitize(n),fn))} for n in actresses]
                pending=False
            else:
                adsts=[{"actress":"PENDING_REVIEW","dst":unique_path(src,os.path.join(f"{dest_drive}:\\Sorted_Videos","JAV_By_Actress","PENDING_REVIEW",fn))}]
                pending=True
            return {"src":src,"cat":cat,"sub":sub,"studio_dst":sdst,"actress_dsts":adsts,"actresses":actresses,"pending":pending,"code":code,"filename":fn}
        else:
            dp = date_prefix(fn,mt)
            group_key = f"{cat}/{dp}"
            dest_drive = pick_destination_drive(group_key, self.drive_map)
            dst = unique_path(src,os.path.join(f"{dest_drive}:\\Sorted_Videos",cat,dp,fn))
            return {"src":src,"cat":cat,"sub":sub,"studio_dst":dst,"actress_dsts":[],"actresses":[],"pending":False,"code":None,"filename":fn}

    def execute_move(self, plan):
        src,dst = plan["src"],plan["studio_dst"]
        if not os.path.exists(src):
            self._state["errors"].append(f"Missing: {plan['filename']}")
            return False
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.abspath(src) == os.path.abspath(dst):
                return True
            shutil.move(src, dst)
            return True
        except Exception as e:
            self._state["errors"].append(f"Failed: {plan['filename']}: {e}")
            return False

    def rebalance(self):
        self._emit(status="scanning")
        videos = self.scan_sorted_library()
        if not videos:
            self._emit(status="done", total=0, done=0)
            return dict(self._state)

        # Rebuild the drive map from scratch so the current free-space order wins.
        self.drive_map = {}

        pcounts = Counter()
        for v in videos:
            _,sub = classify(v["filename"])
            if sub and sub not in {"TOKYO_HOT","CARIBBEANCOM"}: pcounts[sub]+=1

        self._emit(status="sorting", total=len(videos), done=0)
        for i,v in enumerate(videos):
            self._emit(current_file=v["filename"], done=i)
            plan = self.plan_move(v, pcounts)
            if not self.dry_run:
                self.execute_move(plan)
            if plan["pending"]:
                self._state["pending_review"].append({"src":plan["src"],"code":plan.get("code",""),"filename":v["filename"]})
            else:
                self._state["moved"].append({"filename":v["filename"],"dst":plan["studio_dst"],"actresses":plan["actresses"]})
        if not self.dry_run:
            save_cache(self.cache)
        self._emit(status="done", done=len(videos))
        return dict(self._state)

    def run(self):
        self._emit(status="scanning")
        videos = self.scan()
        if not videos:
            self._emit(status="done",total=0,done=0)
            return dict(self._state)
        pcounts = Counter()
        for v in videos:
            _,sub = classify(v["filename"])
            if sub and sub not in {"TOKYO_HOT","CARIBBEANCOM"}: pcounts[sub]+=1
        self._emit(status="sorting",total=len(videos),done=0)
        for i,v in enumerate(videos):
            self._emit(current_file=v["filename"],done=i)
            plan = self.plan_move(v, pcounts)
            if not self.dry_run: self.execute_move(plan)
            if plan["pending"]:
                self._state["pending_review"].append({"src":plan["src"],"code":plan.get("code",""),"filename":v["filename"]})
            else:
                self._state["moved"].append({"filename":v["filename"],"dst":plan["studio_dst"],"actresses":plan["actresses"]})
        if not self.dry_run: save_cache(self.cache)
        self._emit(status="done",done=len(videos))
        return dict(self._state)

    def retry_lookup(self, code):
        self.cache.pop(code, None)
        actresses = fetch_actresses(code)
        self.cache[code] = actresses
        save_cache(self.cache)
        return actresses

    def get_library(self):
        library={}
        for drv in ["E","G","H"]:
            root=f"{drv}:\\Sorted_Videos\\JAV_By_Actress"
            if not os.path.isdir(root): continue
            for af in os.listdir(root):
                fp=os.path.join(root,af)
                if not os.path.isdir(fp): continue
                count=len([f for f in os.listdir(fp) if os.path.splitext(f)[1].lower() in VIDEO_EXTS])
                if af not in library: library[af]={"actress":af,"count":0,"drives":[]}
                library[af]["count"]+=count
                library[af]["drives"].append(drv)
        return sorted(library.values(),key=lambda x:-x["count"])
