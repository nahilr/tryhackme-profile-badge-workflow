#!/usr/bin/env python3
"""Find a TryHackMe userPublicId from a username.

The public userPublicId is no longer shown in the TryHackMe UI, but the badge
API still accepts it. IDs are assigned incrementally at signup time, so we can
binary search: probe an ID, read that user's join date via the public profile
API, and compare it against the target username's join date to halve the range.

Usage:
    python3 find_user_id.py <username> [low] [high]
    python3 find_user_id.py <your_username>
    python3 find_user_id.py <your_username> 100000 8600000
"""

import re
import sys
import time
from datetime import datetime

from curl_cffi import requests

DEFAULT_LOW = 1
DEFAULT_HIGH = 8_600_000
PROBE_WINDOW = 300
NEIGHBORHOOD = 4


def get_json(url):
    for _ in range(5):
        try:
            r = requests.get(url, impersonate="chrome", timeout=30)
            if r.status_code == 429:
                time.sleep(3)
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"  fetch failed: {e}")
            time.sleep(2)
    return None


def get_badge_html(user_public_id):
    url = f"https://tryhackme.com/api/v2/badges/public-profile?userPublicId={user_public_id}"
    for _ in range(5):
        try:
            r = requests.get(url, impersonate="chrome", timeout=30)
            if r.status_code == 429:
                time.sleep(3)
                continue
            r.raise_for_status()
            return r.text
        except Exception as e:
            print(f"  fetch failed: {e}")
            time.sleep(2)
    return None


def username_for(user_public_id):
    html = get_badge_html(user_public_id)
    if not html:
        return None
    m = re.search(r'<span class="user_name">([^<]+)</span>', html)
    return m.group(1).strip() if m else None


def join_ts(username):
    data = get_json(f"https://tryhackme.com/api/v2/public-profile?username={username}")
    ds = (data or {}).get("data", {}).get("dateSignUp")
    if not ds:
        return None
    return datetime.fromisoformat(ds.replace("Z", "+00:00")).timestamp()


def join_ts_for(user_public_id):
    uname = username_for(user_public_id)
    if not uname:
        return None
    return join_ts(uname)


def fmt(ts):
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def find_user_public_id(username, low, high):
    target = join_ts(username)
    if not target:
        print(f"could not look up join date for '{username}'")
        return None
    print(f"target '{username}' joined {fmt(target)}")

    lo, hi = low, high
    iterations = 0
    while lo <= hi:
        mid = (lo + hi) // 2
        probe_ts, probe_id = None, None
        off = 0
        while probe_ts is None and off <= PROBE_WINDOW:
            for candidate in ([mid] if off == 0 else [mid - off, mid + off]):
                if not (low <= candidate <= high):
                    continue
                ts = join_ts_for(candidate)
                if ts is not None:
                    probe_ts, probe_id = ts, candidate
                    break
            off += 1
        if probe_ts is None:
            print(f"no live users around {mid}; try a wider range")
            return None
        iterations += 1
        rel = ">=" if probe_ts >= target else "<"
        print(f"  [{probe_id}] {fmt(probe_ts)} {rel} target")
        if probe_ts >= target:
            hi = mid - 1
        else:
            lo = mid + 1

    start, end = max(low, lo - NEIGHBORHOOD), min(high, lo + NEIGHBORHOOD)
    print(f"scanning neighborhood {start}..{end}")
    for uid in range(start, end + 1):
        uname = username_for(uid)
        if uname and uname.lower() == username.lower():
            ts = join_ts(uname)
            print(f"FOUND: userPublicId = {uid}  ({uname}, joined {fmt(ts) if ts else '?'})")
            return uid
    print(f"not found in {start}..{end}; check around {lo} manually")
    return lo


def main():
    if len(sys.argv) < 2:
        print("usage: find_user_id.py <username> [low] [high]")
        sys.exit(1)
    username = sys.argv[1]
    low = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_LOW
    high = int(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_HIGH
    found = find_user_public_id(username, low, high)
    if found is not None:
        print(f"\nuse: python3 thm_badge.py {found}")


if __name__ == "__main__":
    main()
