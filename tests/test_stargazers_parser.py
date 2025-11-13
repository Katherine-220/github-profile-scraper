import os
import sys
from textwrap import dedent

# Ensure src is importable when running pytest from repo root
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from parsers.stargazers_parser import extract_stargazer_profiles  # type: ignore

def _build_sample_stargazers_html() -> str:
    return dedent(
        """
        <html>
          <body>
            <ol class="user-list">
              <li>
                <a data-hovercard-type="user" href="/alice">Alice</a>
              </li>
              <li>
                <a data-hovercard-type="user" href="/bob">Bob</a>
              </li>
              <li>
                <a data-hovercard-type="user" href="https://github.com/charlie">Charlie</a>
              </li>
            </ol>
          </body>
        </html>
        """
    )

def test_extract_stargazer_profiles_basic():
    html = _build_sample_stargazers_html()
    profiles = extract_stargazer_profiles(html)

    assert "https://github.com/alice" in profiles
    assert "https://github.com/bob" in profiles
    assert "https://github.com/charlie" in profiles
    assert len(profiles) == 3

def test_extract_stargazer_profiles_empty_html():
    profiles = extract_stargazer_profiles("<html><body>No users here</body></html>")
    assert profiles == []