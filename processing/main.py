import os
import json
import pandas as pd
from datetime import datetime
from processing.processors.bayt import BaytProcessor
from processing.processors.wuzzuf import WuzzufProcessor
from processing.processors.indeed import IndeedProcessor
from processing.processors.others import ForasnaProcessor, JobzellaProcessor

MANIFEST_PATH = "data/meta/manifest.json"

def load_manifest():
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, 'r') as f:
            return json.load(f)
    return {"processed_files": []}

def save_manifest(manifest):
    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
    with open(MANIFEST_PATH, 'w') as f:
        json.dump(manifest, f)

def run_pipeline():
    manifest = load_manifest()
    processors = {
        "bayt": BaytProcessor(),
        "wuzzuf": WuzzufProcessor(),
        "indeed": IndeedProcessor(),
        "forasna": ForasnaProcessor(),
        "jobzella": JobzellaProcessor(),
    }

    base_raw_path = "data/raw"
    
    for source, processor in processors.items():
        source_path = os.path.join(base_raw_path, source)
        if not os.path.exists(source_path):
            continue

        # Traverse dates
        for date_dir in os.listdir(source_path):
            date_path = os.path.join(source_path, date_dir)
            
            for file_name in os.listdir(date_path):
                    full_path = os.path.join(date_path, file_name)
                    manifest_key = f"{source}/{date_dir}/{file_name}"
                    
                    if manifest_key not in manifest["processed_files"]:
                        print(f"🚀 Processing {source}: {file_name}")
                        
                        processed_records = processor.run(full_path)
                        
                        if processed_records:
                            df = pd.DataFrame(processed_records)
                            
                            silver_dir = f"data/silver/{source}/{date_dir}"
                            os.makedirs(silver_dir, exist_ok=True)
                            
                            output_file = file_name.replace(".json", ".csv")
                            df.to_csv(os.path.join(silver_dir, output_file), index=False, encoding='utf-8-sig')
                            
                            manifest["processed_files"].append(manifest_key)
                            print(f"✅ Saved to Silver: {output_file}")

    save_manifest(manifest)

if __name__ == "__main__":
    run_pipeline()
