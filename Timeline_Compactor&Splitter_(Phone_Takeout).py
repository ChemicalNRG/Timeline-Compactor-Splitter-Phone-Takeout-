"""
NAME: Timeline Compactor & Splitter (Phone Takeout)
VERSION: 1.0
AUTHOR: Chemical NRG

DESCRIPTION:
This is a functional tool designed to process Google Timeline (Location History) 
JSON files downloaded SPECIFICALLY via Google Takeout on your phone. It is 
intended to prepare your Takeout export for import into 3rd-party Timeline 
viewers with possible file size limits.

CORE FUNCTIONS:
1. Compaction: Reduces file size by filtering redundant WiFi scans, 
   filtering low-confidence activities, and rounding coordinates.
2. Splitting: Divides large files into smaller, chronological parts based 
   on a user-defined size limit.

COMPATIBILITY:
Developed and tested for seamless import into Dawarich (free self-hosted 
location tracker). 

CONTRIBUTIONS:
Testing results with other importers and sharing findings is highly appreciated. 
Suggestions for improvements or code contributions are always welcome.

USAGE:
Change the settings to your liking and drag and drop your Google Takeout JSON file onto this script.
The status window will display the exact file size savings achieved by each individual setting.
"""

import json
import os
import sys
from collections import OrderedDict
from datetime import datetime, timezone

# ==============================================================================
# 1. GENERAL OUTPUT SETTINGS
# ==============================================================================
# Suffix used when SPLIT_BY_KEYS is False:
SUFFIX_SINGLE = "_mini"  

# ==============================================================================
# 2. SPLITTING & LIMITS
# ==============================================================================
# Set the maximum file size in MB (e.g., 10). Files exceeding this limit will 
# be split chronologically. Leave empty (None) to disable splitting.
MAX_FILE_SIZE_MB = 10    

# True: Save rawSignals and semanticSegments in separate files.
# False: Keep both keys together in one file.
SPLIT_BY_KEYS = False     

# Only used if SPLIT_BY_KEYS is False:
COMBINED_INDENT = 2      # Indentation (use 0 for minify)

# ==============================================================================
# 3. DATE FILTERS (Data outside this range will be REMOVED)
#    Format: "YYYY-MM-DD" | Leave empty "" for no filter.
# ==============================================================================
FILTER_START_DATE = ""   
FILTER_END_DATE   = ""   

# ==============================================================================
# 4. SETTINGS: semanticSegments
# ==============================================================================
SUFFIX_SEM = "_semanticSegments"
SEM_INDENT = 2           # Indentation (use 0 for minify)
SEM_ROUND_PROB = 1       # Decimals for 'probability'
SEM_ROUND_DIST = 1       # Decimals for 'distanceMeters'

# ==============================================================================
# 5. SETTINGS: rawSignals
# ==============================================================================
SUFFIX_RAW = "_rawSignals"
RAW_INDENT = 0           # Indentation (use 0 for minify)
RAW_WIFI_LIMIT = 3       # Max WiFi records per scan
RAW_FILTER_ACTIVITY = True # True: Keep only the activity with the highest score
# ==============================================================================

def format_size(size_bytes):
    size_mb = size_bytes / (1024 * 1024)
    if 0 < abs(size_mb) < 0.01:
        return f"{size_bytes / 1024:.2f} KB"
    return f"{size_mb:.2f} MB"

def get_timestamp(entry):
    ts_str = ""
    if "startTime" in entry: ts_str = entry["startTime"]
    elif "position" in entry: ts_str = entry["position"].get("timestamp", "")
    elif "wifiScan" in entry: ts_str = entry["wifiScan"].get("deliveryTime", "")
    elif "activityRecord" in entry: ts_str = entry["activityRecord"].get("timestamp", "")
    if ts_str:
        try: return datetime.fromisoformat(ts_str.replace("Z", "+00:00")).astimezone(timezone.utc)
        except: return None
    return None

def print_settings():
    W = 45 
    print("="*100)
    print(" TIMELINE COMPACTOR & SPLITTER (PHONE TAKEOUT) - STATUS ")
    print("="*100)
    limit_text = f"{MAX_FILE_SIZE_MB} MB (Split: True)" if MAX_FILE_SIZE_MB else "NO LIMIT (Split: False)"
    print(f"[-] {'Max File Size':<{W}}: {limit_text}")
    print(f"[-] {'Split by Keys':<{W}}: {SPLIT_BY_KEYS}")
    
    if not SPLIT_BY_KEYS:
        print(f"[-] {'Suffix':<{W}}: {SUFFIX_SINGLE}")
        c_ind = f"{COMBINED_INDENT} (minify)" if not COMBINED_INDENT else COMBINED_INDENT
        print(f"[-] {'Indent':<{W}}: {c_ind}")
        
    start_str = FILTER_START_DATE or "Start"
    end_str = FILTER_END_DATE or "End"
    date_range = "None" if not (FILTER_START_DATE or FILTER_END_DATE) else f"{start_str} to {end_str}"
    print(f"[-] {'Date Filter':<{W}}: {date_range}")
    print("-" * 100)
    
    print("[semanticSegments]")
    if SPLIT_BY_KEYS:
        print(f"    [-] {'Suffix':<{W-4}}: {SUFFIX_SEM}")
        print(f"    [-] {'Indent':<{W-4}}: {SEM_INDENT if SEM_INDENT else '0 (minify)'}")
    print(f"    [-] {'Round probability':<{W-4}}: {SEM_ROUND_PROB} decimal(s)")
    print(f"    [-] {'Round distanceMeters':<{W-4}}: {SEM_ROUND_DIST} decimal(s)")
    print()
    
    print("[rawSignals]")
    if SPLIT_BY_KEYS:
        print(f"    [-] {'Suffix':<{W-4}}: {SUFFIX_RAW}")
        print(f"    [-] {'Indent':<{W-4}}: {RAW_INDENT if RAW_INDENT else '0 (minify)'}")
    print(f"    [-] {'Max WiFi records per scan':<{W-4}}: {RAW_WIFI_LIMIT}")
    print(f"    [-] {'Filter Activity':<{W-4}}: {RAW_FILTER_ACTIVITY}")
    print("="*100 + "\n")

def get_js_args(indent_val):
    minify = not indent_val
    return {"ensure_ascii": False, "sort_keys": False, "separators": (',', ':') if minify else None, "indent": None if minify else indent_val}

def estimate_size(data_dict, indent_val=2):
    return len(json.dumps(data_dict, **get_js_args(indent_val)).encode('utf-8'))

def process_file(input_path):
    if FILTER_START_DATE and FILTER_END_DATE and FILTER_START_DATE > FILTER_END_DATE:
        print(f"ERROR: Start date ({FILTER_START_DATE}) cannot be later than end date ({FILTER_END_DATE})!")
        return

    print_settings()
    orig_total_size_bytes = os.path.getsize(input_path)
    base, _ = os.path.splitext(input_path)

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f, object_pairs_hook=OrderedDict)

        # 1. ORIGINAL FILE ANALYSIS
        print("="*100)
        print(" ORIGINAL FILE ANALYSIS ")
        print("="*100)
        W_A = 48
        key_orig_sizes = {}
        for k, v in data.items():
            size_b = estimate_size({k: v}, 2)
            key_orig_sizes[k] = size_b
            print(f"[-] {k:<{W_A-4}}: {format_size(size_b)}")
        print("-" * 100)
        print(f"{'TOTAL ORIGINAL SIZE':<{W_A}}: {format_size(orig_total_size_bytes)}\n")

        start_dt = datetime.fromisoformat(FILTER_START_DATE).replace(tzinfo=timezone.utc) if FILTER_START_DATE else None
        end_dt = datetime.fromisoformat(FILTER_END_DATE).replace(tzinfo=timezone.utc) if FILTER_END_DATE else None
        
        # --- rawSignals PROCESSING ---
        raw_list = data.get("rawSignals", [])
        curr_raw_b = key_orig_sizes.get("rawSignals", 0)
        raw_list = [r for r in raw_list if not (ts := get_timestamp(r)) or ((not start_dt or ts >= start_dt) and (not end_dt or ts <= end_dt))]
        new_size_b = estimate_size({"rawSignals": raw_list}, 2)
        s_raw_date_b = curr_raw_b - new_size_b; curr_raw_b = new_size_b
        
        for r in raw_list:
            if "wifiScan" in r and "devicesRecords" in r["wifiScan"]:
                r["wifiScan"]["devicesRecords"] = r["wifiScan"]["devicesRecords"][:RAW_WIFI_LIMIT]
        new_size_b = estimate_size({"rawSignals": raw_list}, 2)
        s_raw_wifi_b = curr_raw_b - new_size_b; curr_raw_b = new_size_b
        
        if RAW_FILTER_ACTIVITY:
            for r in raw_list:
                if "activityRecord" in r and (acts := r["activityRecord"].get("probableActivities")):
                    m_c = max(a.get("confidence", 0) for a in acts)
                    r["activityRecord"]["probableActivities"] = [a for a in acts if a.get("confidence") == m_c]
        new_size_b = estimate_size({"rawSignals": raw_list}, 2)
        s_raw_act_b = curr_raw_b - new_size_b; curr_raw_b = new_size_b
        
        raw_before_indent_b = curr_raw_b
        target_raw_ind = RAW_INDENT if SPLIT_BY_KEYS else COMBINED_INDENT
        raw_after_indent_est_b = estimate_size({"rawSignals": raw_list}, target_raw_ind)
        s_raw_indent_b = raw_before_indent_b - raw_after_indent_est_b

        # --- semanticSegments PROCESSING ---
        sem_list = data.get("semanticSegments", [])
        curr_sem_b = key_orig_sizes.get("semanticSegments", 0)
        sem_list = [s for s in sem_list if not (ts := get_timestamp(s)) or ((not start_dt or ts >= start_dt) and (not end_dt or ts <= end_dt))]
        new_size_b = estimate_size({"semanticSegments": sem_list}, 2)
        s_sem_date_b = curr_sem_b - new_size_b; curr_sem_b = new_size_b
        
        for s in sem_list:
            if "activity" in s and "topCandidate" in s["activity"]:
                if "probability" in s["activity"]["topCandidate"]: s["activity"]["topCandidate"]["probability"] = round(float(s["activity"]["topCandidate"]["probability"]), SEM_ROUND_PROB)
            if "visit" in s:
                if "probability" in s["visit"]: s["visit"]["probability"] = round(float(s["visit"]["probability"]), SEM_ROUND_PROB)
                if (top := s["visit"].get("topCandidate")):
                    if "probability" in top: top["probability"] = round(float(top["probability"]), SEM_ROUND_PROB)
        new_size_b = estimate_size({"semanticSegments": sem_list}, 2)
        s_sem_round_prob_b = curr_sem_b - new_size_b; curr_sem_b = new_size_b
        
        for s in sem_list:
            if "activity" in s and "distanceMeters" in s["activity"]:
                s["activity"]["distanceMeters"] = round(float(s["activity"]["distanceMeters"]), SEM_ROUND_DIST)
        new_size_b = estimate_size({"semanticSegments": sem_list}, 2)
        s_sem_round_dist_b = curr_sem_b - new_size_b; curr_sem_b = new_size_b
        
        sem_before_indent_b = curr_sem_b
        target_sem_ind = SEM_INDENT if SPLIT_BY_KEYS else COMBINED_INDENT
        sem_after_indent_est_b = estimate_size({"semanticSegments": sem_list}, target_sem_ind)
        s_sem_indent_b = sem_before_indent_b - sem_after_indent_est_b

        print("Processing and Saving...")

        def split_chronologically(target_list_dict, suffix, indent_val):
            all_entries = []
            for k, l in target_list_dict.items():
                for item in l: all_entries.append({'k': k, 'd': item, 'ts': get_timestamp(item)})
            all_entries.sort(key=lambda x: x['ts'] if x['ts'] else datetime.min.replace(tzinfo=timezone.utc))
            
            batches, current_batch, marge = [], {k: [] for k in target_list_dict}, 0.94
            for entry in all_entries:
                current_batch[entry['k']].append(entry['d'])
                if sum(len(v) for v in current_batch.values()) % 25 == 0:
                    if estimate_size(current_batch, indent_val) > (MAX_FILE_SIZE_MB * 1024 * 1024 * marge):
                        batches.append(current_batch)
                        current_batch = {k: [] for k in target_list_dict}
            if any(current_batch.values()): batches.append(current_batch)
            
            mb_on_disk = 0
            for i, batch in enumerate(batches):
                final_batch = {k: v for k, v in batch.items() if v}
                p_s = f"_part{i+1}" if len(batches) > 1 else ""
                file_path = f"{base}{suffix}{p_s}.json"
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(final_batch, f, **get_js_args(indent_val))
                size_b = os.path.getsize(file_path)
                print(f"    -> Saved: {os.path.basename(file_path)} ({format_size(size_b)})")
                mb_on_disk += size_b
            return mb_on_disk

        if SPLIT_BY_KEYS:
            total_raw_disk_b = split_chronologically({"rawSignals": raw_list}, SUFFIX_RAW, RAW_INDENT)
            total_sem_disk_b = split_chronologically({"semanticSegments": sem_list}, SUFFIX_SEM, SEM_INDENT)
        else:
            total_combined_disk_b = split_chronologically({"semanticSegments": sem_list, "rawSignals": raw_list}, SUFFIX_SINGLE, COMBINED_INDENT)
            total_raw_disk_b, total_sem_disk_b = 0, total_combined_disk_b

        # --- SAVINGS OVERVIEW ---
        W_S = 55
        print("\n" + "="*100)
        print(" SAVINGS OVERVIEW ")
        print("="*100)
        
        print("[semanticSegments]")
        if s_sem_date_b > 500: print(f"[*] {'Date Filter':<{W_S-4}}: {format_size(s_sem_date_b)}")
        print(f"[*] {'Round probability':<{W_S-4}}: {format_size(s_sem_round_prob_b)}")
        print(f"[*] {'Round distanceMeters':<{W_S-4}}: {format_size(s_sem_round_dist_b)}")
        print(f"[*] {'Indent':<{W_S-4}}: {format_size(s_sem_indent_b)}")
        if SPLIT_BY_KEYS:
            s_sem_overhead = sem_after_indent_est_b - total_sem_disk_b
            print(f"[*] {'File structure overhead':<{W_S-4}}: {format_size(s_sem_overhead)}")
            print(f"{'SUBTOTAL SAVINGS':<{W_S}}: {format_size(key_orig_sizes.get('semanticSegments',0) - total_sem_disk_b)}\n")

        print("[rawSignals]")
        if s_raw_date_b > 500: print(f"[*] {'Date Filter':<{W_S-4}}: {format_size(s_raw_date_b)}")
        print(f"[*] {'Max WiFi records per scan':<{W_S-4}}: {format_size(s_raw_wifi_b)}")
        print(f"[*] {'Filter Activity':<{W_S-4}}: {format_size(s_raw_act_b)}")
        print(f"[*] {'Indent':<{W_S-4}}: {format_size(s_raw_indent_b)}")
        if SPLIT_BY_KEYS:
            s_raw_overhead = raw_after_indent_est_b - total_raw_disk_b
            print(f"[*] {'File structure overhead':<{W_S-4}}: {format_size(s_raw_overhead)}")
            print(f"{'SUBTOTAL SAVINGS':<{W_S}}: {format_size(key_orig_sizes.get('rawSignals',0) - total_raw_disk_b)}")
        
        if not SPLIT_BY_KEYS:
            s_comb_overhead = (raw_after_indent_est_b + sem_after_indent_est_b) - total_combined_disk_b
            print("-" * 100)
            print(f"[*] {'File structure overhead':<{W_S-4}}: {format_size(s_comb_overhead)}")
            comb_orig = key_orig_sizes.get('semanticSegments',0) + key_orig_sizes.get('rawSignals',0)
            print(f"{'SUBTOTAL SAVINGS (Combined)':<{W_S}}: {format_size(comb_orig - total_combined_disk_b)}")

        print("-" * 100)
        for k, v in data.items():
            if k not in ["rawSignals", "semanticSegments"]:
                m_size_b = key_orig_sizes[k]
                if m_size_b > 0: print(f"[*] {'Removed Key: ' + k:<{W_S-4}}: {format_size(m_size_b)}")
        
        final_disk_total = total_raw_disk_b + total_sem_disk_b if SPLIT_BY_KEYS else total_combined_disk_b
        total_savings_final_b = orig_total_size_bytes - final_disk_total
        print("-" * 100)
        print(f"{'TOTAL PROJECT SAVINGS':<{W_S}}: {format_size(total_savings_final_b)}")
        print("="*100)

    except Exception as e: print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1: process_file(sys.argv[1])
    else: print("USAGE: Drag and drop a Google Timeline JSON file onto this script.")
    input("\nPress Enter to exit...")