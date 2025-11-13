import logging
import time
from typing import Dict, Any, Iterable, Generator, Optional
from urllib.parse import urljoin, urlencode, urlparse, parse_qsl

import requests

logger = logging.getLogger(__name__)

class GithubClient:
    """
    Lightweight HTML client for GitHub profile and stargazers pages.
    Uses requests with sensible defaults and simple retry logic.
    """

    def __init__(self, settings: Optional[Dict[str, Any]] = None) -> None:
        settings = settings or {}
        self.base_url = "https://github.com"
        self.user_agent = settings.get(
            "user_agent",
            "Mozilla/5.0 (compatible; GitHubProfileScraper/1.0; +https://bitbash.dev)",
        )
        self.timeout = settings.get("request_timeout", 15)
        self.max_retries = settings.get("max_retries", 3)
        self.sleep_between_requests = float(settings.get("sleep_between_requests", 1.0))

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})

    def _request(self, url: str) -> str:
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug("Requesting %s (attempt %d)", url, attempt)
                resp = self.session.get(url, timeout=self.timeout)
                if resp.status_code == 429:
                    # Rate limited, back off more aggressively
                    wait_for = self.sleep_between_requests * 2 * attempt
                    logger.warning("Received 429 Too Many Requests, sleeping for %.1fs", wait_for)
                    time.sleep(wait_for)
                    continue
                resp.raise_for_status()
                return resp.text
            except Exception as e:
                last_exc = e
                logger.warning("Request to %s failed (attempt %d/%d): %s", url, attempt, self.max_retries, e)
                time.sleep(self.sleep_between_requests * attempt)

        assert last_exc is not None
        logger.error("All retries failed for %s", url)
        raise last_exc

    def fetch_profile_html(self, profile_url: str) -> str:
        """
        Fetch raw HTML for a GitHub profile.
        Accepts either full URLs or paths like '/username'.
        """
        if profile_url.startswith("http://") or profile_url.startswith("https://"):
            url = profile_url
        else:
            url = urljoin(self.base_url, profile_url.lstrip("/"))

        logger.debug("Fetching profile HTML from %s", url)
        return self._request(url)

    def _normalize_stargazers_url(self, url: str) -> str:
        """
        Ensure the stargazers URL includes the '/stargazers' path.
        """
        parsed = urlparse(url)
        if "github.com" not in parsed.netloc:
            raise ValueError(f"Not a valid GitHub URL: {url}")

        path_parts = parsed.path.rstrip("/").split("/")
        if len(path_parts) >= 3 and path_parts[-1] != "stargazers":
            # Assume /owner/repo -> append stargazers
            path_parts.append("stargazers")
        normalized_path = "/".join(path_parts)

        return parsed._replace(path=normalized_path).geturl()

    def fetch_stargazers_pages(self, url: str) -> Generator[str, None, None]:
        """
        Yield HTML content for one or more stargazers pages, following simple pagination.
        """
        base_url = self._normalize_stargazers_url(url)
        page = 1

        while True:
            page_url = self._set_query_param(base_url, "page", page)
            logger.debug("Fetching stargazers page %d: %s", page, page_url)
            html = self._request(page_url)
            yield html

            # Naive termination: if there are no "Next" buttons, stop.
            if 'rel="next"' not in html and 'Next' not in html:
                break
            page += 1

    @staticmethod
    def _set_query_param(url: str, key: str, value: Any) -> str:
        parsed = urlparse(url)
        query = dict(parse_qsl(parsed.query))
        query[key] = str(value)
        new_query = urlencode(query)
        return parsed._replace(query=new_query).geturl()