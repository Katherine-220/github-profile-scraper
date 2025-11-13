import logging
from dataclasses import dataclass, asdict
from typing import List, Dict, Any

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

@dataclass
class PinnedRepo:
    name: str
    url: str
    description: str
    languages: List[str]
    stars: str
    forks: str

@dataclass
class GithubProfile:
    user: str
    name: str
    username: str
    followers: str
    following: str
    bio: str
    location: str
    emails: List[str]
    organization: str
    websites: List[str]
    achievements: List[str]
    sponsoring: List[str]
    last_year_contribution_number: str
    X: str
    LinkedIn: str
    highlights: List[str]
    organization_followed: List[str]
    first_year_commit: str
    pinned_repos: List[PinnedRepo]
    readme: List[str]

def _text_or_empty(el) -> str:
    if not el:
        return ""
    return " ".join(el.get_text(separator=" ", strip=True).split())

def _extract_followers_following(soup: BeautifulSoup) -> (str, str):
    followers = ""
    following = ""
    for a in soup.select("a[href$='?tab=followers'], a[href$='?tab=following']"):
        label = a.get_text(strip=True).lower()
        counter = a.select_one(".Counter, span")
        value = _text_or_empty(counter)
        if "follower" in label:
            followers = value
        elif "following" in label:
            following = value
    return followers, following

def _extract_emails(soup: BeautifulSoup) -> List[str]:
    emails = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("mailto:"):
            emails.add(href.replace("mailto:", "").strip())
    return sorted(emails)

def _extract_websites(soup: BeautifulSoup) -> List[str]:
    sites = set()
    # Primary website block
    for li in soup.select("li[itemprop='url'] a[href]"):
        href = li.get("href", "").strip()
        if href:
            sites.add(href)
    # Fallback: external links section
    for a in soup.select("a[href^='http']"):
        href = a.get("href", "")
        if "github.com" not in href:
            sites.add(href)
    return sorted(sites)

def _extract_social_links(soup: BeautifulSoup) -> (str, str):
    x_link = ""
    linkedin_link = ""
    for a in soup.select("a[href^='http']"):
        href = a.get("href", "")
        lower = href.lower()
        if "twitter.com" in lower or "x.com" in lower:
            x_link = href
        elif "linkedin.com" in lower:
            linkedin_link = href
    return x_link, linkedin_link

def _extract_achievements(soup: BeautifulSoup) -> (List[str], List[str]):
    achievements = set()
    highlights = set()
    # Achievement badges
    for img in soup.select("img[alt][data-view-component='true']"):
        alt = img.get("alt", "").strip()
        if "badge" in alt.lower() or "contributor" in alt.lower():
            achievements.add(alt)
    # Highlight pills (e.g. "Pro")
    for span in soup.select("span.Label, span[title]"):
        txt = _text_or_empty(span)
        if txt:
            highlights.add(txt)
    return sorted(achievements), sorted(highlights)

def _extract_orgs_followed(soup: BeautifulSoup) -> List[str]:
    orgs = set()
    for a in soup.select("a[data-hovercard-type='organization'][href]"):
        href = a.get("href", "").strip()
        if href:
            if href.startswith("http"):
                orgs.add(href)
            else:
                orgs.add(f"https://github.com{href}")
    return sorted(orgs)

def _extract_contributions_last_year(soup: BeautifulSoup) -> str:
    # Typical text: "1,444 contributions in the last year"
    for h2 in soup.select("h2"):
        text = _text_or_empty(h2)
        if "contributions in the last year" in text.lower():
            for token in text.split():
                if any(ch.isdigit() for ch in token):
                    return token
    return ""

def _extract_first_commit_year(soup: BeautifulSoup) -> str:
    # Use min year from contribution graph dates
    years = set()
    for rect in soup.select("rect[data-date]"):
        date = rect.get("data-date", "")
        if len(date) >= 4:
            years.add(date[:4])
    if not years:
        return ""
    return min(years)

def _extract_pinned_repos(soup: BeautifulSoup) -> List[PinnedRepo]:
    repos: List[PinnedRepo] = []
    # Modern GitHub pinned items
    pinned_containers = soup.select("li.pinned-item-list-item, div.js-pinned-items-reorder-container div.mb-3")
    for container in pinned_containers:
        name_el = container.select_one("span.repo, a[data-hovercard-type='repository']")
        name = _text_or_empty(name_el)

        href = ""
        if name_el and name_el.has_attr("href"):
            href = name_el["href"]
        if href and not href.startswith("http"):
            href = f"https://github.com{href}"

        desc_el = container.select_one("p.pinned-item-desc, p.color-fg-muted")
        description = _text_or_empty(desc_el)

        languages: List[str] = []
        for lang_el in container.select("span[itemprop='programmingLanguage']"):
            lang = _text_or_empty(lang_el)
            if lang:
                languages.append(lang)

        stars = ""
        forks = ""
        for a in container.select("a[href*='/stargazers'], a[href*='/network/members']"):
            label = _text_or_empty(a)
            if "star" in a.get("href", ""):
                stars = label
            elif "network" in a.get("href", ""):
                forks = label

        repos.append(
            PinnedRepo(
                name=name,
                url=href,
                description=description,
                languages=languages,
                stars=stars,
                forks=forks,
            )
        )
    return repos

def _extract_readme_lines(soup: BeautifulSoup) -> List[str]:
    article = soup.select_one("article.markdown-body")
    if not article:
        return []
    text = article.get_text("\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines

def parse_profile_html(html: str, profile_url: str) -> Dict[str, Any]:
    """
    Parse GitHub profile HTML into a structured dict.
    """
    soup = BeautifulSoup(html, "lxml")

    name_el = soup.select_one("span.p-name, span[itemprop='name']")
    username_el = soup.select_one("span.p-nickname, span[itemprop='additionalName'], span[itemprop='nickname']")
    bio_el = soup.select_one("div.p-note, div.user-profile-bio, div[data-bio-text]")
    location_el = soup.select_one("li[itemprop='homeLocation'], span[itemprop='homeLocation']")
    org_el = soup.select_one("li[itemprop='worksFor'], span[itemprop='worksFor']")

    name = _text_or_empty(name_el)
    username = _text_or_empty(username_el)
    bio = _text_or_empty(bio_el)
    location = _text_or_empty(location_el)
    organization = _text_or_empty(org_el)

    followers, following = _extract_followers_following(soup)
    emails = _extract_emails(soup)
    websites = _extract_websites(soup)
    x_link, linkedin_link = _extract_social_links(soup)
    achievements, highlights = _extract_achievements(soup)
    orgs_followed = _extract_orgs_followed(soup)
    last_year_contrib = _extract_contributions_last_year(soup)
    first_year_commit = _extract_first_commit_year(soup)
    pinned_repos = _extract_pinned_repos(soup)
    readme_lines = _extract_readme_lines(soup)

    sponsoring = []  # Can be extended if sponsorship info is needed.

    profile = GithubProfile(
        user=profile_url,
        name=name,
        username=username,
        followers=followers,
        following=following,
        bio=bio,
        location=location,
        emails=emails,
        organization=organization,
        websites=websites,
        achievements=achievements,
        sponsoring=sponsoring,
        last_year_contribution_number=last_year_contrib,
        X=x_link,
        LinkedIn=linkedin_link,
        highlights=highlights,
        organization_followed=orgs_followed,
        first_year_commit=first_year_commit,
        pinned_repos=pinned_repos,
        readme=readme_lines,
    )

    # Convert dataclasses to dict, including nested ones
    profile_dict = asdict(profile)
    profile_dict["pinned_repos"] = [asdict(repo) for repo in profile.pinned_repos]

    logger.debug("Parsed profile for %s: %s", profile_url, profile_dict)
    return profile_dict