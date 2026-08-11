#!/usr/bin/env python3
"""Render a TryHackMe profile badge PNG from a userPublicId.

Usage:
    python3 thm_badge.py <userPublicId> [output.png]
"""

import base64
import re
import subprocess
import sys
import time
from pathlib import Path

from curl_cffi import requests

WIDTH, HEIGHT = 329, 88
FALLBACK_AVATAR = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
    "width='60' height='60' viewBox='0 0 60 60'%3E"
    "%3Ccircle cx='30' cy='30' r='30' fill='%23333'/%3E%3C/svg%3E"
)

RANK_BY_HEX = {
    "0x1": "Neophyte",
    "0x2": "Apprentice",
    "0x3": "Pathfinder",
    "0x4": "Seeker",
    "0x5": "Visionary",
    "0x6": "Voyager",
    "0x7": "Adept",
    "0x8": "Hacker",
    "0x9": "Mage",
    "0xA": "Wizard",
    "0xB": "Master",
    "0xC": "Guru",
    "0xD": "Legend",
    "0xE": "Guardian",
    "0xF": "TITAN",
    "0x10": "SAGE",
    "0x11": "VANGUARD",
    "0x12": "SHOGUN",
    "0x13": "ASCENDED",
    "0x14": "MYTHIC",
    "0x15": "GRANDMASTER",
}


def rank_display(hex_level):
    return f"[{hex_level}][{RANK_BY_HEX.get(hex_level, hex_level)}]"


def fetch_badge_html(user_public_id):
    url = f"https://tryhackme.com/api/v2/badges/public-profile?userPublicId={user_public_id}"
    for attempt in range(5):
        try:
            r = requests.get(url, impersonate="chrome", timeout=30)
            if r.status_code == 429:
                print(f"rate limited, retrying in 3s ({attempt + 1}/5)")
                time.sleep(3)
                continue
            r.raise_for_status()
            return r.text
        except Exception as e:
            print(f"fetch failed ({attempt + 1}/5): {e}")
            time.sleep(2)
    raise RuntimeError("could not fetch badge HTML")


def extract_stats(html):
    username = (re.search(r'<span class="user_name">([^<]+)</span>', html) or [None, ""])[1].strip()
    rank_hex = (re.search(r'<span class="rank-title">\[([^\]]+)\]</span>', html) or [None, ""])[1].strip()
    avatar_url = None
    style_match = re.search(
        r'\.thm-avatar\s*{[^}]*background-image:\s*url\([\'"]?([^\'")]+)', html, re.I
    )
    if style_match:
        avatar_url = style_match.group(1)
    if avatar_url and not avatar_url.startswith("http"):
        avatar_url = "https://cdn-images.tryhackme.com/" + avatar_url.lstrip("/")
    stats = re.findall(r'<span class="details-text">([^<]+)</span>', html)
    if len(stats) < 4:
        raise RuntimeError(f"expected 4 stats, found {len(stats)}")
    return {
        "username": username,
        "rank_hex": rank_hex,
        "avatar_url": avatar_url,
        "points": stats[0],
        "streak": stats[1],
        "rank": stats[2],
        "rooms": stats[3],
    }


def fetch_total_points(username):
    url = f"https://tryhackme.com/api/v2/public-profile?username={username}"
    for attempt in range(5):
        try:
            r = requests.get(url, impersonate="chrome", timeout=30)
            if r.status_code == 429:
                print(f"rate limited, retrying in 3s ({attempt + 1}/5)")
                time.sleep(3)
                continue
            r.raise_for_status()
            return (r.json().get("data") or {}).get("totalPoints")
        except Exception as e:
            print(f"fetch failed ({attempt + 1}/5): {e}")
            time.sleep(2)
    raise RuntimeError("could not fetch public profile")


def avatar_data_uri(avatar_url):
    if not avatar_url:
        return FALLBACK_AVATAR
    try:
        r = requests.get(avatar_url, impersonate="chrome", timeout=20)
        r.raise_for_status()
        mime = r.headers.get("content-type", "image/png")
        return f"data:{mime};base64,{base64.b64encode(r.content).decode()}"
    except Exception as e:
        print(f"avatar download failed, using fallback: {e}")
        return FALLBACK_AVATAR


def build_html(stats, avatar_uri, total_points, rank_hex):
    rank = rank_display(rank_hex)
    return f"""<!DOCTYPE html>
<html>
<head>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" crossorigin="anonymous" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Ubuntu:ital,wght@0,400;0,500;1,400;1,500&display=swap" rel="stylesheet" />
  <style>
    body {{ width: 329px; height: 88px; margin: 0; background: transparent; }}
    #thm-badge {{
      width: 329px; height: 88px;
      background-image: url('https://tryhackme.com/img/thm_public_badge_bg.svg');
      background-size: cover;
      display: flex; align-items: center; gap: 12px;
      user-select: none; cursor: pointer; border-radius: 12px;
    }}
    .thm-avatar-outer {{
      width: 60px; height: 60px; border-radius: 50%;
      background: linear-gradient(to bottom left, #a3ea2a, #2e4463);
      padding: 2px; margin-left: 10px;
    }}
    .thm-avatar {{
      background-image: url('{avatar_uri}');
      width: 60px; height: 60px;
      background-size: cover; background-position: center;
      border-radius: 50%; background-color: #121212;
      box-shadow: 0 0 3px 0 #303030;
    }}
    .badge-user-details {{ display: flex; flex-direction: column; gap: 8px; }}
    .details-wrapper {{ display: flex; gap: 8px; }}
    .details-icon-wrapper {{ display: flex; gap: 5px; }}
    .title-wrapper {{ display: flex; align-items: center; gap: 6px; }}
    .user_name {{
      font-family: 'Ubuntu', sans-serif; font-weight: 500; font-size: 14px;
      color: #f9f9fb; max-width: 135px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }}
    .rank-icon {{ color: #ffbb45; font-size: 10px; }}
    .rank-title {{ font-family: Ubuntu, sans-serif; font-weight: 500; font-size: 12px; color: #ffffff; }}
    .crosshair-icon {{ color: #a3ea2a; font-size: 12px; }}
    .detail-icons {{ font-weight: 900; font-size: 11px; }}
    .trophy-icon {{ color: #9ca4b4; }}
    .fire-icon {{ color: #a3ea2a; font-size: 13px; }}
    .award-icon {{ color: #d752ff; font-size: 13px; }}
    .door-closed-icon {{ color: #719cf9; font-size: 12px; }}
    .details-text {{ font-family: Ubuntu, sans-serif; font-weight: 400; font-size: 11px; color: #ffffff; }}
    .thm-link {{ font-family: Ubuntu, sans-serif; font-size: 11px; color: #f9f9fb; text-decoration: none; }}
  </style>
</head>
<body>
  <div id="thm-badge">
    <div class="thm-avatar-outer"><div class="thm-avatar"></div></div>
    <div class="badge-user-details">
      <div class="title-wrapper">
        <span class="user_name">{stats['username']}</span>
        <div><i class="fa-solid fa-bolt-lightning rank-icon"></i><span class="rank-title">{rank}</span></div>
      </div>
      <div class="details-wrapper">
        <div class="details-icon-wrapper"><i class="fa-solid fa-trophy detail-icons trophy-icon"></i><span class="details-text">{stats['points']}</span></div>
        <div class="details-icon-wrapper"><i class="fa-solid fa-fire detail-icons fire-icon"></i><span class="details-text">{stats['streak']}</span></div>
        <div class="details-icon-wrapper"><i class="fa-solid fa-award detail-icons award-icon"></i><span class="details-text">{stats['rank']}</span></div>
        <div class="details-icon-wrapper"><i class="fa-solid fa-door-closed detail-icons door-closed-icon"></i><span class="details-text">{stats['rooms']}</span></div>
      </div>
      <div class="details-icon-wrapper"><i class="fa-solid fa-crosshairs crosshair-icon"></i><span class="details-text">{total_points} pts</span></div>
    </div>
  </div>
</body>
</html>"""


def find_chrome():
    for c in ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]:
        try:
            subprocess.run([c, "--version"], capture_output=True, check=True)
            return c
        except Exception:
            continue
    raise RuntimeError("no chrome binary found")


def render(html, output):
    chrome = find_chrome()
    tmp = Path("/tmp") / f"thm_badge_{int(time.time())}.html"
    tmp.write_text(html)
    cmd = [
        chrome,
        "--headless=new", "--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage",
        "--default-background-color=00000000",
        f"--virtual-time-budget=15000",
        f"--window-size={WIDTH},{HEIGHT}",
        f"--screenshot={output}",
        f"file://{tmp}",
    ]
    subprocess.run(cmd, check=True)
    if not Path(output).exists():
        raise RuntimeError("screenshot was not produced")


def main():
    if len(sys.argv) < 2:
        print("usage: thm_badge.py <userPublicId> [output.png]")
        sys.exit(1)
    user_public_id = sys.argv[1]
    output = Path(sys.argv[2] if len(sys.argv) > 2 else "thm_badge.png")
    output.parent.mkdir(parents=True, exist_ok=True)

    print("fetching badge html...")
    html = fetch_badge_html(user_public_id)
    stats = extract_stats(html)
    print(f"got {stats['username']} ([{stats['rank_hex']}]) stats: {stats['points']}, {stats['streak']}, {stats['rank']}, {stats['rooms']} rooms")

    print("fetching total points...")
    total_points = fetch_total_points(stats["username"])

    print("downloading avatar...")
    avatar_uri = avatar_data_uri(stats["avatar_url"])

    print("rendering badge...")
    render(build_html(stats, avatar_uri, total_points, stats["rank_hex"]), output)
    print(f"saved {output} ({output.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
