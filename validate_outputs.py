import os
import pandas as pd
import json
from datetime import datetime
from processing.validation.validator import DataValidator

SILVER_PATH = "data/silver"
FAILED_PATH = "data/failed"
REPORT_PATH = "data/reports"

def run_validation():
    stats = {
        "total_files": 0,
        "total_records": 0,
        "valid_records": 0,
        "invalid_records": 0,
        "duplicates_found": 0,
        "schema_failures": 0,
        "execution_time": str(datetime.now()),
        "files_report": []
    }

    if not os.path.exists(SILVER_PATH):
        print("❌ Silver layer directory not found!")
        return

    for root, dirs, files in os.walk(SILVER_PATH):
        for file in files:
            if file.endswith(".csv"):
                stats["total_files"] += 1
                file_path = os.path.join(root, file)
                print(f"🔍 Validating: {file}")
                
                try:
                    df = pd.read_csv(file_path)
                except Exception as e:
                    print(f"❌ Could not read {file}: {e}")
                    continue

                # 1. Schema Validation
                missing_cols = DataValidator.check_schema(df)
                if missing_cols:
                    stats["schema_failures"] += 1
                    print(f"⚠️ Schema mismatch in {file}: Missing {missing_cols}")
                    continue

                # 2. Row Validation
                invalid_rows = []
                valid_rows_indices = []
                
                # Deduplication check (intra-file)
                initial_count = len(df)
                df_no_dupes = df.drop_duplicates(subset=['job_hash'])
                stats["duplicates_found"] += (initial_count - len(df_no_dupes))

                for index, row in df_no_dupes.iterrows():
                    errors = DataValidator.validate_row(row)
                    if errors:
                        row_dict = row.to_dict()
                        row_dict['validation_errors'] = "|".join(errors)
                        invalid_rows.append(row_dict)
                    else:
                        valid_rows_indices.append(index)

                # Update Stats
                stats["total_records"] += initial_count
                stats["valid_records"] += len(valid_rows_indices)
                stats["invalid_records"] += len(invalid_rows)

                # Save Failed Records if any
                if invalid_rows:
                    failed_df = pd.DataFrame(invalid_rows)
                    failed_file = os.path.join(FAILED_PATH, f"failed_{file}")
                    failed_df.to_csv(failed_file, index=False)
                    print(f"⚠️ Found {len(invalid_rows)} invalid rows. Saved to data/failed/")

                stats["files_report"].append({
                    "file": file,
                    "records": initial_count,
                    "valid": len(valid_rows_indices),
                    "invalid": len(invalid_rows)
                })

    # Save Final Report
    report_file = os.path.join(REPORT_PATH, f"qa_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(report_file, 'w') as f:
        json.dump(stats, f, indent=4)
    
    print("\n" + "="*30)
    print("🏁 VALIDATION COMPLETE")
    print(f"Total Records: {stats['total_records']}")
    print(f"Valid: {stats['valid_records']} ({(stats['valid_records']/stats['total_records']*100):.2f}%)")
    print(f"Invalid: {stats['invalid_records']}")
    print(f"Duplicates Removed: {stats['duplicates_found']}")
    print(f"Report saved to: {report_file}")
    print("="*30)

if __name__ == "__main__":
    run_validation()
