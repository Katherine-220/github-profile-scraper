import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def export_to_json(records: List[Dict[str, Any]], path: str) -> None:
    """
    Export list of profile records to a JSON file.
    """
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        logger.info("Exported %d records to JSON file %s", len(records), path)
    except Exception as e:
        logger.exception("Failed to export JSON to %s: %s", path, e)
        raise