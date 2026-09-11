"""
Batch-processes a folder of test documents through the full pipeline and
writes each result as JSON into sample_outputs/ - used to produce the
"sample JSON outputs for processed test documents" deliverable (spec
section 11). Requires GEMINI_API_KEY to be set.

Usage:
    python scripts/generate_samples.py

Edit DATASET_DIR below (or pass it as sys.argv[1]) to point at your local
copy of the case-study dataset folder.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.database import SessionLocal, init_db  # noqa: E402
from app.pipeline import process_document  # noqa: E402

DATASET_DIR = sys.argv[1] if len(sys.argv) > 1 else "./dataset"
OUTPUT_DIR = "./sample_outputs"
DELAY_BETWEEN_CALLS_SECONDS = 4  # keeps us comfortably under free-tier RPM limits

FOLDER_TO_DOC_TYPE = {
    "Balance Sheet": "BALANCE_SHEET",
    "Profit & Loss": "PROFIT_AND_LOSS",
    "Cash Flows": "CASH_FLOW",
    "Invoices": "INVOICE",
}


def main():
    init_db()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    db = SessionLocal()

    for folder_name, doc_type in FOLDER_TO_DOC_TYPE.items():
        folder_path = os.path.join(DATASET_DIR, folder_name)
        if not os.path.isdir(folder_path):
            print(f"Skipping missing folder: {folder_path}")
            continue

        for filename in sorted(os.listdir(folder_path)):
            file_path = os.path.join(folder_path, filename)
            if not os.path.isfile(file_path):
                continue
            print(f"Processing [{doc_type}] {filename} ...")
            try:
                with open(file_path, "rb") as fp:
                    content = fp.read()
                record = process_document(db, filename, doc_type, content)
                out_path = os.path.join(OUTPUT_DIR, f"{os.path.splitext(filename)[0]}.json")
                with open(out_path, "w") as out:
                    json.dump({
                        "document_name": record.document_name,
                        "document_type": record.document_type,
                        "status": record.status,
                        "file_validation": record.file_validation,
                        "extracted_data": record.extracted_data,
                        "validations": record.validations,
                        "processing_metadata": record.processing_metadata,
                    }, out, indent=2)
                print(f"  -> wrote {out_path}")
            except Exception as exc:
                print(f"  !! FAILED: {exc}")
            time.sleep(DELAY_BETWEEN_CALLS_SECONDS)

    db.close()


if __name__ == "__main__":
    main()