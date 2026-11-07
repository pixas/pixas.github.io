"""Build the citation data shown on the academic homepage.

The payload is written to ``assets/data/citations.json`` on the site branch, so
the browser reads it from the same origin as the page: no cross-origin request,
no third-party CDN, no stale orphan branch.

Sources, in order:
  1. Google Scholar profile page, fetched directly and parsed as HTML. This is
     lighter and far more reliable than a headless scraper.
  2. ``scholarly`` (optional dependency), in case the direct request is blocked.
  3. OpenAlex works, matched by exact / near-exact title. A free API key
     (``OPENALEX_API_KEY``) is recommended: without one the daily budget is
     shared by everyone on the same IP.
  4. Semantic Scholar paper search (``S2_API_KEY`` optional).
  5. The last published ``citations.json``. We never publish an empty payload.

The Google Scholar id comes from ``GOOGLE_SCHOLAR_ID`` or, as a fallback, from
``author.googlescholar`` in ``_config.yml``.
"""

import html
import json
import os
import re
import signal
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "assets" / "data" / "citations.json"
LEGACY_FILE = ROOT / "google_scholar_crawler" / "results" / "gs_data.json"

AUTHOR_NAME = os.environ.get("AUTHOR_NAME", "Shuyang Jiang").strip()
MAILTO = os.environ.get("CONTACT_EMAIL", "jiangshuyang0@gmail.com").strip()
OPENALEX_KEY = os.environ.get("OPENALEX_API_KEY", "").strip()
S2_KEY = os.environ.get("S2_API_KEY", "").strip()
USER_AGENT = "acad-homepage-citations/1.0 (mailto:%s)" % MAILTO
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


def log(message):
    print("[citations] %s" % message, flush=True)


def scholar_id_from_config():
    try:
        config = (ROOT / "_config.yml").read_text(encoding="utf-8")
    except OSError:
        return ""
    match = re.search(
        r"googlescholar\s*:\s*[\"']?https?://scholar\.google\.com/citations\?user=([A-Za-z0-9_-]+)",
        config,
    )
    return match.group(1) if match else ""


SCHOLAR_ID = os.environ.get("GOOGLE_SCHOLAR_ID", "").strip() or scholar_id_from_config()
PROFILE_URL = "https://scholar.google.com/citations?user=%s" % SCHOLAR_ID


def norm_title(title):
    return re.sub(r"[^a-z0-9]+", "", (title or "").lower())


def same_title(a, b):
    na, nb = norm_title(a), norm_title(b)
    if not na or not nb or min(len(na), len(nb)) < 20:
        return False
    return na == nb or na in nb or nb in na or na[:30] == nb[:30]


def get_json(url, headers=None, timeout=15):
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json", **(headers or {})}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


class TimeoutGuard:
    def __init__(self, seconds):
        self.seconds = seconds
        self.supported = hasattr(signal, "SIGALRM")
        self.previous = None

    @staticmethod
    def _raise(signum, frame):
        raise TimeoutError("operation timed out")

    def __enter__(self):
        if self.supported:
            self.previous = signal.signal(signal.SIGALRM, self._raise)
            signal.alarm(self.seconds)
        return self

    def __exit__(self, *args):
        if self.supported:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, self.previous)


def load_previous():
    """Last published payload (or the legacy gs_data.json) as a fallback seed."""
    if DATA_FILE.exists():
        try:
            data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            publications = {}
            for key, value in (data.get("publications") or {}).items():
                publications[key] = {
                    "bib": {"title": value.get("title", "")},
                    "num_citations": int(value.get("num_citations") or 0),
                    "url": value.get("url") or "",
                }
            if publications:
                return {
                    "publications": publications,
                    "citedby": data.get("total_citations", 0),
                    "hindex": data.get("h_index", 0),
                    "i10index": data.get("i10_index", 0),
                    "updated": data.get("updated", ""),
                    "name": data.get("author", AUTHOR_NAME),
                }
        except (ValueError, OSError) as exc:
            log("cannot read previous payload: %s" % exc)
    if LEGACY_FILE.exists():
        try:
            data = json.loads(LEGACY_FILE.read_text(encoding="utf-8"))
            if isinstance(data.get("publications"), dict) and data["publications"]:
                for value in data["publications"].values():
                    value.setdefault("url", value.get("citedby_url") or PROFILE_URL)
                return data
        except (ValueError, OSError) as exc:
            log("cannot read legacy snapshot: %s" % exc)
    return None


def previous_titles(previous):
    if not previous:
        return []
    return [
        (pub.get("bib") or {}).get("title")
        for pub in previous["publications"].values()
        if (pub.get("bib") or {}).get("title")
    ]


def fetch_google_scholar_html():
    if not SCHOLAR_ID:
        log("no Google Scholar id found, skipping direct profile fetch")
        return None
    hosts = ["scholar.google.com", "scholar.google.co.jp", "scholar.google.com.hk"]
    for attempt, host in enumerate(hosts, 1):
        url = (
            "https://%s/citations?user=%s&hl=en"
            "&view_op=list_works&sortby=pubdate&pagesize=100" % (host, SCHOLAR_ID)
        )
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": BROWSER_UA,
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml",
                },
            )
            with urllib.request.urlopen(request, timeout=25) as response:
                page = response.read().decode("utf-8", "replace")
            if "gsc_a_tr" not in page or "unusual traffic" in page.lower():
                raise ValueError("profile page blocked or empty")

            metrics = []
            table = re.search(r'<table id="gsc_rsb_st".*?</table>', page, re.S)
            if table:
                for row in re.findall(r"<tr>(.*?)</tr>", table.group(0), re.S):
                    cell = re.search(r'<td class="gsc_rsb_std">(\d+)</td>', row)
                    if cell:
                        metrics.append(int(cell.group(1)))
            metrics += [0, 0, 0]

            publications = []
            for row in re.findall(r'<tr class="gsc_a_tr".*?</tr>', page, re.S):
                link = re.search(r'<a[^>]*class="gsc_a_at"[^>]*>(.*?)</a>', row, re.S)
                if not link:
                    continue
                title = html.unescape(re.sub(r"<[^>]+>", "", link.group(1))).strip()
                cites_cell = re.search(r'<td class="gsc_a_c">(.*?)</td>', row, re.S)
                count = re.search(r">(\d+)</a>", cites_cell.group(1)) if cites_cell else None
                pub = re.search(r'citation_for_view=([^"&]+)', row)
                pub_id = urllib.parse.unquote(pub.group(1)) if pub else ""
                publications.append(
                    {
                        "title": title,
                        "num_citations": int(count.group(1)) if count else 0,
                        "url": (
                            "https://scholar.google.com/citations?view_op=view_citation"
                            "&user=%s&hl=en&citation_for_view=%s"
                            % (SCHOLAR_ID, urllib.parse.quote(pub_id, safe=":_-"))
                        ),
                        "source": "google_scholar",
                    }
                )
            if not publications:
                raise ValueError("no publications parsed")
            if len(publications) >= 100:
                log("warning: 100 publications returned, paging is not implemented")

            title_match = re.search(r"<title>(.*?)</title>", page, re.S)
            author = AUTHOR_NAME
            if title_match:
                author = html.unescape(
                    re.sub(r"<[^>]+>", "", title_match.group(1))
                ).split(" - ")[0].strip("\u200f\u200e\u202a\u202c\u202d ") or AUTHOR_NAME

            total = metrics[0] or sum(item["num_citations"] for item in publications)
            log("Google Scholar HTML OK: %d publications, %d citations" % (len(publications), total))
            return {
                "source": "google_scholar",
                "source_label": "Google Scholar",
                "author": author,
                "total_citations": total,
                "h_index": metrics[1],
                "i10_index": metrics[2],
                "publications": publications,
            }
        except Exception as exc:
            log("Google Scholar HTML via %s failed: %s" % (host, exc))
            time.sleep(2)
    return None


def fetch_scholarly():
    if not SCHOLAR_ID:
        return None
    try:
        from scholarly import scholarly
    except Exception as exc:
        log("scholarly is unavailable: %s" % exc)
        return None
    try:
        with TimeoutGuard(90):
            author = scholarly.search_author_id(SCHOLAR_ID)
            scholarly.fill(author, sections=["basics", "indices", "counts", "publications"])
        publications = []
        for pub in author.get("publications", []):
            title = (pub.get("bib") or {}).get("title")
            if not title:
                continue
            publications.append(
                {
                    "title": title,
                    "num_citations": int(pub.get("num_citations") or 0),
                    "url": pub.get("citedby_url") or PROFILE_URL,
                    "source": "google_scholar",
                }
            )
        if not publications:
            raise ValueError("profile returned no publications")
        log("scholarly OK: %d publications" % len(publications))
        return {
            "source": "google_scholar",
            "source_label": "Google Scholar",
            "author": author.get("name", AUTHOR_NAME),
            "total_citations": int(author.get("citedby") or 0),
            "h_index": int(author.get("hindex") or 0),
            "i10_index": int(author.get("i10index") or 0),
            "publications": publications,
        }
    except Exception as exc:
        log("scholarly failed: %s" % exc)
        return None


def fetch_openalex(titles):
    if not titles:
        return []
    matched = []
    for index, title in enumerate(titles):
        params = urllib.parse.urlencode(
            {"filter": "title.search:" + title, "per-page": "3", "select": "title,cited_by_count,doi,id"}
        )
        if OPENALEX_KEY:
            params += "&api_key=" + urllib.parse.quote(OPENALEX_KEY)
        try:
            data = get_json("https://api.openalex.org/works?" + params)
        except Exception as exc:
            log("OpenAlex request failed: %s" % exc)
            if index == 0:
                return []
            break
        for work in data.get("results", []):
            if not same_title(title, work.get("title", "")):
                continue
            doi = work.get("doi") or ""
            matched.append(
                {
                    "title": title,
                    "num_citations": int(work.get("cited_by_count") or 0),
                    "url": doi if doi.startswith("http") else (work.get("id") or ""),
                    "source": "openalex",
                }
            )
            break
        time.sleep(0.15)
    log("OpenAlex matched %d/%d titles" % (len(matched), len(titles)))
    return matched


def fetch_semantic_scholar(titles):
    if not titles:
        return []
    headers = {"x-api-key": S2_KEY} if S2_KEY else {}
    matched = []
    for index, title in enumerate(titles):
        params = urllib.parse.urlencode(
            {"query": title, "limit": "3", "fields": "title,citationCount,externalIds,url"}
        )
        try:
            data = get_json(
                "https://api.semanticscholar.org/graph/v1/paper/search?" + params,
                headers=headers,
            )
        except Exception as exc:
            log("Semantic Scholar request failed: %s" % exc)
            if index == 0:
                return []
            break
        for paper in data.get("data", []):
            if not same_title(title, paper.get("title", "")):
                continue
            matched.append(
                {
                    "title": title,
                    "num_citations": int(paper.get("citationCount") or 0),
                    "url": paper.get("url") or "",
                    "source": "semantic_scholar",
                }
            )
            break
        time.sleep(1.1 if not S2_KEY else 0.2)
    log("Semantic Scholar matched %d/%d titles" % (len(matched), len(titles)))
    return matched


def same_stats(a, b):
    """Compare citation values while ignoring the refresh timestamp."""
    def signature(payload):
        return (
            payload.get("source"),
            payload.get("total_citations"),
            payload.get("h_index"),
            payload.get("i10_index"),
            payload.get("stale"),
            payload.get("note"),
            sorted(
                (key, value.get("num_citations"), value.get("source"), value.get("url"))
                for key, value in (payload.get("publications") or {}).items()
            ),
        )
    return signature(a) == signature(b)


def build_payload(source, label, author, total, h_index, i10_index, publications, stale=False, note=""):
    indexed = {}
    for pub in publications:
        key = norm_title(pub["title"])
        if not key:
            continue
        current = indexed.get(key)
        if current is None or pub["num_citations"] > current["num_citations"]:
            indexed[key] = {
                "title": pub["title"],
                "num_citations": int(pub["num_citations"] or 0),
                "url": pub.get("url") or "",
                "source": pub.get("source") or source,
            }
    return {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": source,
        "source_label": label,
        "author": author,
        "total_citations": int(total or 0),
        "h_index": int(h_index or 0),
        "i10_index": int(i10_index or 0),
        "stale": stale,
        "note": note,
        "publications": indexed,
    }


def main():
    previous = load_previous()
    titles = previous_titles(previous)
    result = fetch_google_scholar_html() or fetch_scholarly()

    if result:
        payload = build_payload(
            result["source"], result["source_label"], result["author"],
            result["total_citations"], result["h_index"], result["i10_index"],
            result["publications"],
        )
    else:
        if previous:
            log("Google Scholar unavailable; keeping the existing snapshot unchanged")
            return 0
        openalex = fetch_openalex(titles)
        found = {norm_title(pub["title"]) for pub in openalex}
        missing = [title for title in titles if norm_title(title) not in found]
        semantic = fetch_semantic_scholar(missing)
        combined = openalex + semantic
        covered = {norm_title(pub["title"]) for pub in combined}

        if combined and previous:
            for pub in previous["publications"].values():
                title = (pub.get("bib") or {}).get("title")
                if not title or norm_title(title) in covered:
                    continue
                combined.append(
                    {
                        "title": title,
                        "num_citations": int(pub.get("num_citations") or 0),
                        "url": pub.get("url") or PROFILE_URL,
                        "source": "cached_google_scholar",
                    }
                )
            source = "openalex" if openalex else "semantic_scholar"
            label = "OpenAlex + Semantic Scholar" if openalex and semantic else (
                "OpenAlex" if openalex else "Semantic Scholar"
            )
            if any(pub.get("source") == "cached_google_scholar" for pub in combined):
                label += " + 缓存"
            payload = build_payload(
                source, label, previous.get("name", AUTHOR_NAME),
                previous.get("citedby") or sum(pub["num_citations"] for pub in combined),
                previous.get("hindex", 0), previous.get("i10index", 0), combined,
                note="Google Scholar 暂不可用；单篇引用来自开放学术 API 或上次快照，总引用沿用上次 Google Scholar 数值",
            )
        elif previous:
            cached = [
                {
                    "title": (pub.get("bib") or {}).get("title", ""),
                    "num_citations": int(pub.get("num_citations") or 0),
                    "url": pub.get("url") or PROFILE_URL,
                    "source": "cached_google_scholar",
                }
                for pub in previous["publications"].values()
            ]
            payload = build_payload(
                "google_scholar", "Google Scholar", previous.get("name", AUTHOR_NAME),
                previous.get("citedby", 0), previous.get("hindex", 0),
                previous.get("i10index", 0), cached, stale=True,
                note="自动更新暂不可用，显示上一次成功抓取的数据",
            )
            snapshot_date = str(previous.get("updated") or "")[:10]
            if snapshot_date:
                payload["updated"] = snapshot_date
        else:
            log("no citation source available and no previous payload found")
            return 1

    if DATA_FILE.exists():
        try:
            existing = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            if same_stats(existing, payload):
                log("citation values unchanged; file left untouched")
                return 0
        except (ValueError, OSError) as exc:
            log("cannot compare with the existing file: %s" % exc)

    parent = DATA_FILE.parent
    if not parent.exists():
        parent.mkdir(parents=True)
    DATA_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    log(
        "wrote assets/data/citations.json: %s, %d papers, %d total citations%s"
        % (payload["source_label"], len(payload["publications"]),
           payload["total_citations"], " (stale)" if payload["stale"] else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
