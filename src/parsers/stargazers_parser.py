import logging
from typing import List

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def extract_stargazer_profiles(html: str) -> List[str]:
    """
    Extract GitHub profile URLs from a stargazers page HTML.
    Returns absolute URLs like 'https://github.com/username'.
    """
    soup = BeautifulSoup(html, "lxml")
    profiles = set()

    # GitHub typically uses anchor tags with data-hovercard-type="user"
    for a in soup.select("a[data-hovercard-type='user'][href]"):
        href = a.get("href", "").strip()
        if not href:
            continue
        if href.startswith("http"):
            url = href
        else:
            url = f"https://github.com{href}"
        profiles.add(url)

    # Fallback: list items in stargazer/user lists
    if not profiles:
        for a in soup.select("ol li a[href^='/'"):
            href = a.get("href", "").strip()
            if href and href.count("/") == 1:  # looks like '/username'
                profiles.add(f"https://github.com{href}")

    result = sorted(profiles)
    logger.debug("Extracted %d stargazer profiles", len(result))
    return result