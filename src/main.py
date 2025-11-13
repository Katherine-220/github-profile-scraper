import argparse
import json
import logging
import os
import sys
from typing import List, Dict, Any, Optional

# Make local imports work when running as `python src/main.py`
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from github_client import GithubClient
from parsers.profile_parser import parse_profile_html
from parsers.stargazers_parser import extract_stargazer_profiles
from outputs.json_exporter import export_to_json
from outputs.csv_exporter import export_to_csv

logger = logging.getLogger(__name__)

def load_profiles_from_file(path: str) -> List[str]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Profiles file not found: {path}")

    profiles: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            profiles.append(line)

    logger.info("Loaded %d profile URLs from %s", len(profiles), path)
    return profiles

def get_profiles_from_stargazers(client: GithubClient, url: str, max_profiles: Optional[int]) -> List[str]:
    logger.info("Discovering profiles from stargazers URL: %s", url)
    profiles: List[str] = []
    for page_html in client.fetch_stargazers_pages(url):
        page_profiles = extract_stargazer_profiles(page_html)
        for p in page_profiles:
            profiles.append(p)
            if max_profiles is not None and len(profiles) >= max_profiles:
                logger.info("Reached max_profiles limit: %d", max_profiles)
                return profiles
    logger.info("Discovered %d profile URLs from stargazers", len(profiles))
    return profiles

def scrape_profiles(
    client: GithubClient,
    profile_urls: List[str],
    max_profiles: Optional[int] = None,
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for idx, url in enumerate(profile_urls, start=1):
        if max_profiles is not None and len(results) >= max_profiles:
            logger.info("Reached max_profiles limit: %d", max_profiles)
            break

        try:
            logger.info("(%d/%d) Fetching profile: %s", idx, len(profile_urls), url)
            html = client.fetch_profile_html(url)
            profile = parse_profile_html(html, url)
            results.append(profile)
        except Exception as e:
            logger.exception("Failed to scrape profile %s: %s", url, e)
    logger.info("Successfully scraped %d profiles", len(results))
    return results

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="GitHub Profile Scraper - scrape profile metadata and contribution signals."
    )

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--profiles-file",
        help="Path to text file containing GitHub profile URLs (one per line).",
    )
    input_group.add_argument(
        "--stargazers-url",
        help="GitHub repository stargazers URL to discover profiles from.",
    )

    parser.add_argument(
        "--output",
        default=os.path.join(os.path.dirname(CURRENT_DIR), "data", "output.json"),
        help="Output file path (default: data/output.json).",
    )
    parser.add_argument(
        "--format",
        choices=["json", "csv"],
        default="json",
        help="Output format: json or csv (default: json).",
    )
    parser.add_argument(
        "--max-profiles",
        type=int,
        default=None,
        help="Maximum number of profiles to process (default: no limit).",
    )
    parser.add_argument(
        "--config",
        default=os.path.join(CURRENT_DIR, "config", "settings.example.json"),
        help="Path to settings JSON (default: settings.example.json).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO).",
    )
    return parser.parse_args(argv)

def load_settings(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        logger.warning("Settings file not found at %s, using defaults.", path)
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Failed to load settings file %s: %s", path, e)
        return {}

def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )

    settings = load_settings(args.config)
    client = GithubClient(settings=settings)

    # Build list of profile URLs
    if args.profiles_file:
        profile_urls = load_profiles_from_file(args.profiles_file)
    else:
        profile_urls = get_profiles_from_stargazers(client, args.stargazers_url, args.max_profiles)

    if not profile_urls:
        logger.error("No profile URLs to process. Exiting.")
        return

    profiles = scrape_profiles(client, profile_urls, max_profiles=args.max_profiles)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    if args.format == "json":
        export_to_json(profiles, args.output)
    else:
        export_to_csv(profiles, args.output)

    logger.info("Done. Wrote %d profiles to %s (%s).", len(profiles), args.output, args.format)

if __name__ == "__main__":
    main()