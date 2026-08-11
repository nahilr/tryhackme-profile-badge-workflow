# TryHackMe Profile Badge Workflow

A lightweight GitHub Action that renders a live TryHackMe profile badge from a `userPublicId` and commits the PNG to your repo — so your README always shows your current stats.

## What the badge looks like

![TryHackMe](https://raw.githubusercontent.com/nahilr/nahilr/main/assets/thm_badge.png)

## Setup

Star this repo and give me a follow :)

1. **Create a `.github/workflows` directory** in your username repo — the one named `<your-username>/<your-username>`, where your README is located.

2. **Create a file** named `tryhackme-badge.yml` inside of that folder.

3. **Place the following code** inside of the previously created file:

```yaml
name: TryHackMe Update Badge

on:
  schedule:
    - cron: '0 0 * * *'   # run every 24 hours
  workflow_dispatch:       # or run it manually from the Actions tab

permissions:
  contents: write

jobs:
  tryhackme-badge-update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: nahilr/tryhackme-profile-badge-workflow@main
        with:
          # Replace with your TryHackMe userPublicId
          user_public_id: "<YOUR_PUBLIC_ID>"
```

> GitHub Actions runs from your repo, so you get `GITHUB_TOKEN` automatically — no secrets needed.

4. **Find your `userPublicId`** — it's no longer shown in the TryHackMe UI. Download or copy `find_user_id.py` from this repository to your computer, then run:

```bash
pip install curl_cffi
curl -O https://raw.githubusercontent.com/nahilr/tryhackme-profile-badge-workflow/main/find_user_id.py
python3 find_user_id.py <your_tryhackme_username>
```

Put the number it prints in place of `<YOUR_PUBLIC_ID>` above.

5. **Add the following markdown** in your README and add your username:

```markdown
![tryhackme stats](https://raw.githubusercontent.com/<SET_USERNAME_HERE>/<SET_USERNAME_HERE>/main/assets/thm_badge.png)
```

Want the badge to link to your TryHackMe profile when clicked? Use this HTML instead (replace `<SET_USERNAME_HERE>` with your GitHub username and `<SET_THM_USERNAME>` with your TryHackMe username):

```html
<a href="https://tryhackme.com/p/<SET_THM_USERNAME>" target="_blank">
  <img src="https://raw.githubusercontent.com/<SET_USERNAME_HERE>/<SET_USERNAME_HERE>/main/assets/thm_badge.png" alt="tryhackme stats">
</a>
```

6. **Run the action** — go to your repo's **Actions** tab → **TryHackMe Update Badge** → **Run workflow**. After the first run, the badge shows in your README and auto-updates every 24 hours.

## Inputs

| Name | Description | Default |
|---|---|---|
| `user_public_id` | TryHackMe user public ID (required) | — |
| `image_path` | Where the badge PNG is saved | `assets/thm_badge.png` |
| `committer_username` | Git username for the commit | `github-actions[bot]` |
| `committer_email` | Git email for the commit | `41898282+github-actions[bot]@users.noreply.github.com` |
| `commit_message` | Commit message | `chore: update tryhackme badge` |

Set these options under the action's `with:` block. Only `user_public_id` is required; the other values can be left out to use their defaults.

```yaml
- uses: nahilr/tryhackme-profile-badge-workflow@main
  with:
    user_public_id: '<YOUR_PUBLIC_ID>'
    image_path: 'assets/custom_thm_badge.png'
    committer_username: 'github-actions[bot]'
    committer_email: '41898282+github-actions[bot]@users.noreply.github.com'
    commit_message: 'chore: update TryHackMe badge'
```

For example, if you change `image_path`, use the same path in the image URL in your README.

## How it works

The action renders a `329x88` PNG badge that mirrors TryHackMe's official design, then commits it to your repo on every run. It uses two public TryHackMe endpoints:

- **Badge HTML** — `https://tryhackme.com/api/v2/badges/public-profile?userPublicId=<ID>` returns the HTML for the badge shown on your TryHackMe profile.
- **Profile JSON** — `https://tryhackme.com/api/v2/public-profile?username=<you>` returns your stats as JSON: rank, rooms, badges, points, level, and league tier.

Both endpoints sit behind Vercel's anti-bot challenge, which serves a JavaScript checkpoint page to any non-browser TLS fingerprint — plain `requests` or `urllib` get blocked instantly. Every fetch therefore goes through a `curl_cffi` helper that reproduces a real Chrome TLS handshake, which the checkpoint accepts.

Here's what happens on each run:

1. **Fetch the badge HTML** from the badge API — this is the source of the official design: icons, colors, and layout.
2. **Fetch total points** from the profile API and derive your rank title (e.g. `0xA`). The rank title is looked up from a hex-to-name map, since the badge API itself doesn't return a readable rank name.
3. **Embed your avatar as a base64 data URI.** The avatar is downloaded once and inlined into the HTML page, so rendering makes zero external requests — fully self-contained.
4. **Render the badge to PNG** with headless Chromium — the action builds a self-contained HTML page from the badge HTML, injects the avatar and extra stats, then screenshots it at `329x88`.
5. **Commit the PNG back to your repo.** The action checks via `git diff` whether the badge actually changed; if it did, it commits `image_path` and pushes. If nothing changed, it skips the commit to avoid cluttering your history.

On top of what TryHackMe's own badge shows (level, rooms, badges, streak, global rank), this badge adds **total points** — the one stat that only exists in the profile JSON and never appears on THM's own badge image.

## Finding your `userPublicId`

The action needs your numeric `userPublicId`, but TryHackMe no longer shows it anywhere in its UI. The included `find_user_id.py` script finds it for you by binary search: it probes the badge API, reads each candidate user's join date from the profile API, and compares it to your username's join date to home in on your ID.

```bash
pip install curl_cffi
python3 find_user_id.py <your_tryhackme_username>
```

It assumes IDs are assigned incrementally at signup time. The default search range is `1 8600000`. You can pass a custom range if needed:

```bash
python3 find_user_id.py <your_tryhackme_username> 100000 4000000
```

It ends by printing your found ID and the command to render your badge with it.

## Embed your TryHackMe badge

Once you know your `userPublicId`, you can also embed your TryHackMe badge anywhere that supports HTML or iframes:

```html
<script src="https://tryhackme.com/badge/<userPublicId>"></script>
```

Or embed the public badge HTML in an iframe:

```html
<iframe src="https://tryhackme.com/api/v2/badges/public-profile?userPublicId=<userPublicId>"></iframe>
```

## Project Background

This project is inspired by and intended as a successor to [`p4p1/tryhackme-badge-workflow`](https://github.com/p4p1/tryhackme-badge-workflow). It keeps the same core idea: automatically update a TryHackMe badge in your GitHub profile README.

The original action was archived on 2026-04-19. Its dynamic mode used the TryHackMe badge API, which now blocks plain HTTP clients with an anti-bot challenge. Its static mode depended on `https://tryhackme-badges.s3.amazonaws.com/<username>.png`, a bucket that has been frozen since 2024.

This version uses `curl_cffi` to fetch the current badge HTML and profile data with a Chrome-like TLS handshake. It then renders the badge with headless Chromium and commits the resulting PNG to your repository. In addition to the official badge stats, it adds total points from the public profile API.

## Running locally

Two scripts are included in this repository:

- `thm_badge.py` — renders the badge PNG from a `userPublicId`
- `find_user_id.py` — finds your `userPublicId` from your username

```bash
git clone https://github.com/nahilr/tryhackme-profile-badge-workflow.git
cd tryhackme-profile-badge-workflow

pip install curl_cffi

# 1. From a local copy of this repository, find your ID
python3 find_user_id.py <your_username>

# 2. Render your badge
python3 thm_badge.py <userPublicId> [output.png]
```

Requires `google-chrome`, `chromium`, or `chromium-browser` on PATH (GitHub Actions runners have Chrome preinstalled).

## AI Disclosure

This project was created with assistance from AI tools. The code and documentation were reviewed and tested by the maintainer.

## License

MIT
