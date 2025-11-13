import csv
import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Core fields flattened into CSV; nested structures will be JSON-encoded.
CORE_FIELDS = [
    "user",
    "name",
    "username",
    "followers",
    "following",
    "bio",
    "location",
    "organization",
    "last_year_contribution_number",
    "X",
    "LinkedIn",
    "first_year_commit",
]

def _serialize_value(value: Any) -> str:
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value) if value is not None else ""

def export_to_csv(records: List[Dict[str, Any]], path: str) -> None:
    """
    Export list of profile records to a CSV file.
    Lists and nested structures are JSON-encoded.
    """
    try:
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CORE_FIELDS)
            writer.writeheader()

            for record in records:
                row = {}
                for field in CORE_FIELDS:
                    row[field] = _serialize_value(record.get(field, ""))
                writer.writerow(row)

        logger.info("Exported %d records to CSV file %s", len(records), path)
    except Exception as e:
        logger.exception("Failed to export CSV to %s: %s", path, e)
        raise