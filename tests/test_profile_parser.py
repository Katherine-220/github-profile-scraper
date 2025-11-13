import os
import sys
from textwrap import dedent

import pytest

# Ensure src is importable when running pytest from repo root
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from parsers.profile_parser import parse_profile_html  # type: ignore

def _build_sample_profile_html() -> str:
    return dedent(
        """
        <html>
          <body>
            <main>
              <div class="h-card">
                <span class="p-name">Sebastian Raschka</span>
                <span class="p-nickname">rasbt</span>
                <div class="p-note user-profile-bio">
                  Machine Learning and AI researcher &amp; currently research engineer at a startup
                </div>
              </div>
              <ul>
                <li itemprop="homeLocation">
                  <span>Madison, WI</span>
                </li>
                <li itemprop="worksFor">
                  <span>@Lightning-AI</span>
                </li>
                <li itemprop="url">
                  <a href="https://magazine.sebastianraschka.com">https://magazine.sebastianraschka.com</a>
                </li>
              </ul>

              <a href="mailto:test@example.com">test@example.com</a>
              <a href="https://twitter.com/rasbt">Twitter</a>
              <a href="https://www.linkedin.com/in/sebastianraschka/">LinkedIn</a>

              <a href="/rasbt?tab=followers">
                <span class="Counter">19.9k</span> followers
              </a>
              <a href="/rasbt?tab=following">
                <span class="Counter">39</span> following
              </a>

              <h2>1,444 contributions in the last year</h2>

              <svg>
                <rect data-date="2013-01-01"></rect>
                <rect data-date="2014-01-01"></rect>
              </svg>

              <ul class="pinned-items-list">
                <li class="pinned-item-list-item">
                  <span class="repo">LLMs-from-scratch</span>
                  <a href="/rasbt/LLMs-from-scratch">Repo link</a>
                  <p class="pinned-item-desc">
                    Implementing a ChatGPT-like LLM from scratch, step by step
                  </p>
                  <span itemprop="programmingLanguage">Jupyter Notebook</span>
                  <a href="/rasbt/LLMs-from-scratch/stargazers">11.3k</a>
                  <a href="/rasbt/LLMs-from-scratch/network/members">904</a>
                </li>
              </ul>

              <article class="markdown-body">
                <h1>Hi there, I am Sebastian 👋</h1>
                <p>and I am a machine learning and AI researcher with a strong passion for education!</p>
              </article>
            </main>
          </body>
        </html>
        """
    )

def test_parse_profile_html_basic_fields():
    html = _build_sample_profile_html()
    url = "https://github.com/rasbt"

    profile = parse_profile_html(html, url)

    assert profile["user"] == url
    assert profile["name"] == "Sebastian Raschka"
    assert profile["username"] == "rasbt"
    assert profile["bio"].startswith("Machine Learning and AI researcher")
    assert profile["location"] == "Madison, WI"
    assert profile["organization"] == "@Lightning-AI"
    assert profile["followers"] == "19.9k"
    assert profile["following"] == "39"
    assert profile["last_year_contribution_number"] == "1,444"
    assert profile["first_year_commit"] == "2013"

    assert "https://magazine.sebastianraschka.com" in profile["websites"]
    assert profile["X"] == "https://twitter.com/rasbt"
    assert profile["LinkedIn"] == "https://www.linkedin.com/in/sebastianraschka/"

    assert len(profile["pinned_repos"]) == 1
    pinned = profile["pinned_repos"][0]
    assert pinned["name"] == "LLMs-from-scratch"
    assert pinned["url"] == "https://github.com/rasbt/LLMs-from-scratch"
    assert pinned["stars"] == "11.3k"
    assert pinned["forks"] == "904"

    assert any("Hi there, I am Sebastian" in line for line in profile["readme"])

def test_parse_profile_html_handles_missing_fields_gracefully():
    # Minimal HTML without optional sections
    html = "<html><body><span class='p-nickname'>user123</span></body></html>"
    url = "https://github.com/user123"

    profile = parse_profile_html(html, url)

    assert profile["user"] == url
    assert profile["username"] == "user123"
    # Optional fields should not raise errors and default to empty-ish values
    assert isinstance(profile["emails"], list)
    assert isinstance(profile["pinned_repos"], list)
    assert isinstance(profile["readme"], list)