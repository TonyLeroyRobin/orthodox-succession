#!/usr/bin/env python3
"""Static site generator (SITE_REFINEMENT R1).

Every page is generated at build time with its real content in the HTML —
JavaScript enhances (search, calendar, map interactivity) but never creates
content. Path-based entity URLs mirror record IDs:

    person/cyprus/barnabas-0045      -> /people/cyprus/barnabas-0045/
    see/ukraine/kyiv                 -> /sees/ukraine/kyiv/
    jurisdiction/church-of-serbia    -> /jurisdictions/church-of-serbia/
    event/council/ephesus-0431       -> /councils/ephesus-0431/

Output: build/site/ (the complete deployable site). Legacy /site/*.html
query-parameter URLs are kept as functional pages or redirectors (see
emit_legacy). Stdlib only — no template engine.
"""

from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.parse as urlparse
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import REPO_ROOT, date_year, load_all  # noqa: E402

OUT = REPO_ROOT / "build" / "site"
SITE_SRC = REPO_ROOT / "site"
# GitHub Pages serves this project at /orthodox-succession/ (no custom
# domain), so every internal root-absolute URL must carry the base path.
# Local preview from a bare web root: SITE_BASE="" python scripts/build_site.py
BASE = os.environ.get("SITE_BASE", "/orthodox-succession").rstrip("/")
STATUS_LABEL = {"verified": "verified", "unverified": "unverified",
                "disputed": "disputed"}
STATUS_COLOR = {"verified": "#2e7d32", "unverified": "#b26a00",
                "disputed": "#b3261e"}

NAV = [("Home", "/"), ("Jurisdictions", "/jurisdictions/"),
       ("Sees", "/sees/"), ("People", "/people/"),
       ("Councils", "/councils/"), ("Library", "/library/"),
       ("Saints", "/saints/"), ("Institutions", "/institutions/"),
       ("Map", "/map/"), ("Timeline", "/timeline/"),
       ("Controversies", "/controversies/"),
       ("Graph", "/graph/"), ("Ideas", "/ideas/"),
       ("About", "/about/")]


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def dataset_version():
    try:
        v = subprocess.run(["git", "describe", "--tags", "--abbrev=0"],
                           capture_output=True, text=True, cwd=REPO_ROOT,
                           timeout=15)
        return v.stdout.strip() or "unreleased"
    except Exception:
        return "unreleased"


VERSION = dataset_version()


def fmt_date(d):
    if not d or not d.get("value"):
        return "—"
    v = re.sub(r"^0+(\d)", r"\1", str(d["value"]))
    p = d.get("precision")
    year = v.split("-")[0]
    if p == "circa":
        s = f"c. {year}"
    elif p == "decade":
        s = f"{year}s"
    elif p == "disputed":
        s = f"{v} (disputed)"
    elif p in ("day", "month"):
        s = v
    else:
        s = year
    if d.get("calendar") == "julian":
        s += " (Julian)"
    return s


def fmt_range(frm, to, open_label="end unrecorded"):
    return f"{fmt_date(frm)} → {fmt_date(to) if to else open_label}"


def person_name(p):
    if not p:
        return "(unknown person)"
    n = p.get("names") or {}
    s = n.get("monastic") or p.get("id", "?")
    if n.get("family"):
        s += f" ({n['family']})"
    return s


def entity_url(rid):
    if rid.startswith("person/"):
        return "/people/" + rid.split("/", 1)[1] + "/"
    if rid.startswith("see/"):
        return "/sees/" + rid.split("/", 1)[1] + "/"
    if rid.startswith("jurisdiction/"):
        return "/jurisdictions/" + rid.split("/", 1)[1] + "/"
    if rid.startswith("event/council/"):
        return "/councils/" + rid.split("/", 2)[2] + "/"
    if rid.startswith("work/"):
        return "/library/" + rid.split("/", 1)[1] + "/"
    if rid.startswith("controversy/"):
        return "/controversies/" + rid.split("/", 1)[1] + "/"
    return None


def badge(status):
    return f'<span class="badge {esc(status)}">{esc(status)}</span>'


def citations_html(cits, sources_by_id):
    if not cits:
        return '<div class="citation">no citations</div>'
    out = []
    for c in cits:
        src = sources_by_id.get(c.get("ref"))
        title = src["data"].get("title") if src else c.get("ref")
        loc = f", {esc(c['locator'])}" if c.get("locator") else ""
        link = (f' <a href="{esc(src["data"]["url"])}">[link]</a>'
                if src and src["data"].get("url") else "")
        arch = c.get("archived_url") or (src and src["data"].get("archived_url"))
        alink = f' <a href="{esc(arch)}">[archived]</a>' if arch else ""
        # F5: sources without a resolvable URL render as plain print
        # citations - WorldCat is demoted to an unlinked mention at most,
        # never a linked affordance (it rate-limits referred lookups)
        note = (f' <span class="note">— {esc(c["note"])}</span>'
                if c.get("note") else "")
        out.append(f'<div class="citation"><span class="badge grade">'
                   f'{esc(c.get("reliability", "?"))}</span> {esc(title)}'
                   f'{loc}{link}{alink}{note}</div>')
    return "".join(out)


def layout(title, content, canonical, jsonld=None, active="",
           description=None, entity_id=None):
    nav = "".join(
        f'<a href="{href}"{" class=active" if label == active else ""}>'
        f'{label}</a>' for label, href in NAV)
    ld = (f'<script type="application/ld+json">{json.dumps(jsonld, indent=1)}'
          f'</script>' if jsonld else "")
    desc = description or ("Orthodox Apostolic Succession Database — sourced "
                           "records of sees, tenures, consecrations, councils, "
                           "canons, and works.")
    # Q8.3: report-a-correction link, prefilled with the entity id / page URL
    issue_url = ("https://github.com/TonyLeroyRobin/orthodox-succession/issues/"
                 "new?template=error-report.yml&title="
                 + urlparse.quote(f"[correction] {entity_id or title}")
                 + "&entity-id=" + urlparse.quote(entity_id or canonical))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} — Orthodox Apostolic Succession</title>
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Orthodox Apostolic Succession Database">
<meta name="description" content="{esc(desc)}">
<link rel="stylesheet" href="/assets/style.css">
{ld}</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
<header class="site-header">
<nav aria-label="Main">{nav}</nav>
<form class="searchbox" action="/search/" method="get">
<input type="search" name="q" placeholder="Search people, sees, councils, works…" aria-label="Search">
</form>
</header>
<main id="main">
{content}
</main>
<footer>Data: CC BY 4.0 · Code: MIT · Recognition disputes are recorded, not
adjudicated; <em>unverified</em> means no human has yet confirmed the claim
against a graded source.<br>
Cite this page: <code>{esc(canonical)}</code> — Orthodox Apostolic Succession
Database {esc(VERSION)}.<br>
<a href="{esc(issue_url)}" rel="nofollow">Report a correction for this page</a>
· <a href="/state/">State of the database</a>
· <a href="/research/">For researchers</a></footer>
<script src="/assets/site.js" defer></script>
</body>
</html>"""


SITEMAP_URLS = []


def write(path, text, sitemap=True):
    # Q2.3: collect page URLs for sitemap.xml (redirect stubs excluded)
    if sitemap and str(path).endswith("index.html"):
        rel = path.relative_to(OUT).parent.as_posix()
        rel = "" if rel == "." else rel + "/"
        SITEMAP_URLS.append(
            f"https://tonyleroyrobin.github.io/orthodox-succession/{rel}")
    # base-path rewrite: internal root-absolute references gain the Pages
    # project prefix; https:// (canonical) links are untouched.
    if BASE and str(path).endswith(".html"):
        for pat, rep in (('href="/', f'href="{BASE}/'),
                         ("href='/", f"href='{BASE}/"),
                         ('src="/', f'src="{BASE}/'),
                         ("src='/", f"src='{BASE}/"),
                         ("url=/", f"url={BASE}/")):
            text = text.replace(pat, rep)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main():
    records, problems = load_all()
    if problems:
        for path, msg in problems:
            print(f"build_site: load problem {path}: {msg}", file=sys.stderr)
        return 1

    by_kind = defaultdict(list)
    by_id = {}
    for r in records:
        by_kind[r["kind"]].append(r)
        if r["data"].get("id"):
            by_id[r["data"]["id"]] = r

    persons = {r["data"]["id"]: r["data"] for r in by_kind["person"]}
    sees = {r["data"]["id"]: r["data"] for r in by_kind["see"]}
    jurs = {r["data"]["id"]: r["data"] for r in by_kind["jurisdiction"]}
    sources_by_id = {r["data"]["id"]: r for r in by_kind["source"]}
    tenures = [r["data"] for r in by_kind["tenure"]]
    works = [r["data"] for r in by_kind["work"]]
    works_by_id = {w["id"]: w for w in works}
    institutions = {r["data"]["id"]: r["data"]
                    for r in by_kind["institution"] if r["data"].get("id")}
    associations = [r["data"] for r in by_kind["association"]]
    assoc_by_inst = defaultdict(list)
    assoc_by_person = defaultdict(list)
    for a_ in associations:
        assoc_by_inst[a_.get("institution")].append(a_)
        assoc_by_person[a_.get("person")].append(a_)
    councils = [r["data"] for r in by_kind["event"]
                if r["data"].get("type") != "context"]
    participations = [r["data"] for r in by_kind["participation"]]
    consecrations = [r["data"] for r in by_kind["consecration"]]

    tenures_by_person = defaultdict(list)
    tenures_by_see = defaultdict(list)
    for t in tenures:
        tenures_by_person[t.get("person")].append(t)
        tenures_by_see[t.get("see")].append(t)
    parts_by_person = defaultdict(list)
    parts_by_event = defaultdict(list)
    for pt in participations:
        parts_by_person[pt.get("person")].append(pt)
        parts_by_event[pt.get("event")].append(pt)
    # (relation, work) pairs — the relation is per person-work pair, not the
    # record's alone: the author keeps the record's curated relation, but a
    # subject_of person always sees "about" (Life of Clement is BY Theophylact
    # and ABOUT Clement).
    works_by_person = defaultdict(list)
    for w in works:
        if w.get("author"):
            works_by_person[w["author"]].append((w.get("relation", "by"), w))
        for s in w.get("subject_of") or []:
            works_by_person[s].append(("about", w))
    cons_by_person = defaultdict(list)
    cons_given = defaultdict(list)
    for c in consecrations:
        cons_by_person[c.get("consecrated")].append(c)
        if c.get("principal_consecrator"):
            cons_given[c["principal_consecrator"]].append(c)
        for k in c.get("co_consecrators") or []:
            cons_given[k].append(c)
    relationships = [r["data"] for r in by_kind["relationship"]]
    rels_by_person = defaultdict(list)
    for rel in relationships:
        rels_by_person[rel.get("from")].append(("from", rel))
        rels_by_person[rel.get("to")].append(("to", rel))

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    def plink(pid):
        p = persons.get(pid)
        url = entity_url(pid)
        return (f'<a href="{url}">{esc(person_name(p))}</a>'
                if p and url else esc(pid))

    # Q1.4 display-name formula: list entries render
    # "Name — epithet-or-primary-see, dates"; no bare ambiguous names on
    # list pages.
    def person_dates(p, pid):
        by = date_year((p.get("born") or {}).get("date"))
        dy = date_year((p.get("died") or {}).get("date"))
        if by or dy:
            return f"{by or '?'}–{dy or '?'}"
        ys = sorted(y for t in tenures_by_person.get(pid, [])
                    for y in (date_year(t.get("from")), date_year(t.get("to")))
                    if y is not None)
        if ys:
            return f"fl. {ys[0]}" + (f"–{ys[-1]}" if ys[-1] != ys[0] else "")
        return ""

    def person_qualifier(p, pid):
        if p.get("epithet"):
            return p["epithet"]
        ts = sorted(tenures_by_person.get(pid, []),
                    key=lambda t: date_year(t.get("from")) or 9999)
        for t in ts:
            s = sees.get(t.get("see"))
            if s:
                return s.get("name", "")
        return ""

    def person_entry_label(pid):
        p = persons.get(pid)
        if not p:
            return esc(pid)
        q, d_ = person_qualifier(p, pid), person_dates(p, pid)
        tail = ", ".join(x for x in (q, d_) if x)
        return esc(person_name(p)) + (f" — {esc(tail)}" if tail else "")

    def person_entry(pid):
        url = entity_url(pid)
        p = persons.get(pid)
        if not (p and url):
            return esc(pid)
        q, d_ = person_qualifier(p, pid), person_dates(p, pid)
        tail = ", ".join(x for x in (q, d_) if x)
        return (f'<a href="{url}">{esc(person_name(p))}</a>'
                + (f' <span class="note">— {esc(tail)}</span>' if tail else ""))

    def ord_suffix(n):
        if 10 <= n % 100 <= 20:
            return "th"
        return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")

    def slink(sid):
        s = sees.get(sid)
        url = entity_url(sid)
        return (f'<a href="{url}">{esc(s.get("name"))}</a>'
                if s and url else esc(sid))

    # ---------------- per-see static timeline SVG ----------------
    def see_timeline_svg(ts):
        spans = []
        for t in ts:
            f = date_year(t.get("from"))
            if f is None:
                continue
            e = date_year(t.get("to")) or f
            spans.append((f, max(e, f), t))
        if not spans:
            return ""
        y0 = min(s[0] for s in spans)
        y1 = max(s[1] for s in spans)
        y1 = max(y1, y0 + 10)
        W, H = 900, 46
        x = lambda yr: 10 + (yr - y0) / (y1 - y0) * (W - 20)
        bars = []
        for f, e, t in spans:
            color = STATUS_COLOR.get(t.get("status"), "#777")
            w = max(3, x(e) - x(f))
            p = persons.get(t.get("person"))
            tip = f"{person_name(p)} ({fmt_range(t.get('from'), t.get('to'))})"
            url = entity_url(t.get("person") or "") or "#"
            bars.append(
                f'<a href="{url}"><rect x="{x(f):.1f}" y="14" width="{w:.1f}"'
                f' height="14" rx="2" fill="{color}"><title>{esc(tip)}</title>'
                f'</rect></a>')
        return (f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" '
                f'aria-label="tenure timeline">'
                f'<text x="10" y="10" font-size="10" fill="#7a7265">{y0}</text>'
                f'<text x="{W-10}" y="10" font-size="10" fill="#7a7265" '
                f'text-anchor="end">{y1}</text>{"".join(bars)}</svg>')

    # ---------------- person pages ----------------
    for pid, p in persons.items():
        n = p.get("names") or {}
        url = entity_url(pid)
        canonical = f"https://tonyleroyrobin.github.io/orthodox-succession{url}"
        rows = [("Role", esc(p.get("role", "bishop")))]
        if n.get("baptismal"):
            rows.append(("Baptismal name", esc(n["baptismal"])))
        if n.get("family"):
            rows.append(("Family name", esc(n["family"])))
        if n.get("native"):
            rows.append(("Native script",
                         ", ".join(esc(x.get("value")) for x in n["native"])))
        if n.get("variants"):
            rows.append(("Variants", "; ".join(esc(v) for v in n["variants"])))
        if p.get("born"):
            rows.append(("Born", esc(fmt_date((p["born"] or {}).get("date")))
                         + (f" — {esc(p['born'].get('place'))}"
                            if p["born"].get("place") else "")))
        if p.get("died"):
            rows.append(("Died", esc(fmt_date((p["died"] or {}).get("date")))
                         + (f" — {esc(p['died'].get('place'))}"
                            if p["died"].get("place") else "")))
        ident = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows)

        ven = p.get("veneration")
        ven_html = ""
        if ven:
            vparts = [f"<p>Status: {badge(ven.get('status'))}"
                      + (" · " + ", ".join(esc(t) for t in ven["titles"])
                         if ven.get("titles") else "") + "</p>"]
            for rec in ven.get("recognition") or []:
                by = rec.get("by", "")
                if by.startswith("jurisdiction:"):
                    jid = by.split(":", 1)[1]
                    j = jurs.get(jid)
                    jurl = entity_url(jid)
                    label = (f'<a href="{jurl}">{esc(j.get("name"))}</a>'
                             if j and jurl else esc(jid))
                else:
                    label = esc(by)
                gd = rec.get("glorified_date")
                vparts.append(
                    "<p class=note>Recognized by " + label
                    + (f" · glorified {esc(fmt_date(gd))}" if gd else "")
                    + (f" — {esc(rec['note'])}" if rec.get("note") else "")
                    + "</p>")
            feasts = ven.get("feast_days") or []
            if feasts:
                vparts.append("<p>Feast days: " + "; ".join(
                    f"{esc(f['month_day'])} ({esc(f.get('calendar'))})"
                    + (f" — {esc(f['note'])}" if f.get("note") else "")
                    for f in feasts) + "</p>")
            ven_html = ("<div class=panel><h2>Veneration</h2>"
                        + "".join(vparts)
                        + citations_html(ven.get("sources"), sources_by_id)
                        + "</div>")

        my_tenures = tenures_by_person.get(pid, [])
        trows = "".join(
            f"<tr><td>{slink(t.get('see'))}</td>"
            f"<td>{esc(fmt_range(t.get('from'), t.get('to')))}</td>"
            f"<td>{esc(t.get('end_reason'))}</td>"
            f"<td>{badge(t.get('status'))}</td></tr>"
            f"<tr><td colspan=4>{citations_html(t.get('sources'), sources_by_id)}"
            + (f"<div class=note>{esc(t.get('notes'))}</div>" if t.get("notes")
               else "") + "</td></tr>"
            for t in sorted(my_tenures,
                            key=lambda t: date_year(t.get("from")) or 0))
        tenure_html = (f"<table><thead><tr><th>See</th><th>Tenure</th>"
                       f"<th>End</th><th>Status</th></tr></thead>"
                       f"<tbody>{trows}</tbody></table>" if trows
                       else "<p class=note>No tenure records.</p>")

        received = cons_by_person.get(pid, [])
        cons_html = ""
        for c in received:
            pc = (plink(c["principal_consecrator"])
                  if c.get("principal_consecrator") else "<em>not recorded</em>")
            cos = ", ".join(plink(x) for x in c.get("co_consecrators") or []) \
                or "<em>not yet recorded</em>"
            cons_html += (f"<p>Consecrated {esc(fmt_date(c.get('date')))}"
                          + (f" at {esc(c['place'])}" if c.get("place") else "")
                          + f" · principal: {pc} · co-consecrators: {cos} "
                          + badge(c.get("status")) + "</p>"
                          + citations_html(c.get("sources"), sources_by_id))
        if not cons_html:
            cons_html = ("<p><em>No consecration data recorded — absent, "
                         "not inferred.</em></p>")
        given = cons_given.get(pid, [])
        if given:
            cons_html += "<h3>Consecrations performed</h3><ul>" + "".join(
                f"<li>{plink(c.get('consecrated'))} — "
                f"{esc(fmt_date(c.get('date')))} {badge(c.get('status'))}</li>"
                for c in given) + "</ul>"

        parts_html = ""
        my_parts = parts_by_person.get(pid, [])
        if my_parts:
            prows = ""
            for pt in my_parts:
                ev = by_id.get(pt.get("event"))
                evd = ev["data"] if ev else {}
                evurl = entity_url(pt.get("event") or "")
                title = esc(evd.get("title", pt.get("event")))
                link = f'<a href="{evurl}">{title}</a>' if evurl else title
                prows += (f"<tr><td>{link}</td>"
                          f"<td>{esc(fmt_date((evd.get('date') or {}).get('from')))}</td>"
                          f"<td>{esc(pt.get('role'))}</td>"
                          f"<td>{badge(pt.get('status'))}</td></tr>")
            parts_html = (f"<div class=panel><h2>Councils</h2><table><thead>"
                          f"<tr><th>Council</th><th>Date</th><th>Role</th>"
                          f"<th>Status</th></tr></thead><tbody>{prows}"
                          f"</tbody></table></div>")

        works_html = ""
        my_works = works_by_person.get(pid, [])
        if my_works:
            groups = defaultdict(list)
            for relname, w in my_works:
                # Q4.2: secondary literature (about-relation modern studies)
                # renders as Further reading, apart from the ancient corpus
                if relname == "about" and w.get("genre") in ("study",):
                    groups["further"].append(w)
                else:
                    groups[relname].append(w)
            GROUP_LABEL = {"by": "By this person",
                           "about": "About this person",
                           "involving": "Involving this person",
                           "further": "Further reading"}
            sections = ""
            for relname in ("by", "about", "involving", "further"):
                ws = groups.get(relname)
                if not ws:
                    continue
                wrows = ""
                for w in sorted(ws, key=lambda w: w.get("title", "")):
                    eds = ""
                    for ed in w.get("editions") or []:
                        rd = (f' <a href="{esc(ed["url"])}">read</a>'
                              if ed.get("url") else "")
                        eds += (f"<div class=citation>{esc(ed.get('type'))} · "
                                f"{esc(ed.get('language'))} · "
                                f"{esc(ed.get('series', ''))} "
                                f"({esc(ed.get('rights'))}){rd}</div>")
                    surv = w.get("survival")
                    sbadge = (f' <span class="badge survival">{esc(surv)}'
                              f'</span>' if surv else "")
                    snote = (f"<p class=note>Survival: "
                             f"{esc(w['survival_note'])}</p>"
                             if w.get("survival_note") else "")
                    wnote = (f"<p class=note>{esc(w['notes'])}</p>"
                             if w.get("notes") else "")
                    wrows += (f"<h4 id=\"{esc(w['id'].split('/', 1)[1])}\">"
                              f"{esc(w.get('title'))}{sbadge} "
                              f"{badge(w.get('status'))}</h4>"
                              f"<p class=note>{esc(w.get('genre'))} · "
                              f"attribution: "
                              f"<strong>{esc(w.get('attribution'))}</strong>"
                              + (f" · {esc(w['cpg'])}" if w.get("cpg") else "")
                              + f" · {esc(fmt_date(w.get('date')))}</p>"
                              + wnote + snote + eds)
                sections += f"<h3>{GROUP_LABEL[relname]}</h3>{wrows}"
            corr_out = sorted({ad for _, w in my_works
                               for ad in (w.get("addressee") or [])
                               if w.get("author") == pid})
            corr_in = sorted({w.get("author") for w in works
                              if pid in (w.get("addressee") or [])
                              and w.get("author") and w.get("author") != pid})
            corr_html = ""
            if corr_out or corr_in:
                bits = []
                if corr_out:
                    bits.append("Letters to " +
                                ", ".join(plink(x) for x in corr_out))
                if corr_in:
                    bits.append("letters from " +
                                ", ".join(plink(x) for x in corr_in))
                corr_html = (f"<p class=note><strong>Correspondence:</strong> "
                             f"{'; '.join(bits)} — see the "
                             f"<a href='/ideas/'>ideas graph</a>.</p>")
            works_html = (f"<div class=panel><h2>Works</h2>{corr_html}"
                          f"{sections}</div>")
        form_bits = []
        for a_ in assoc_by_person.get(pid, []):
            iid_ = a_.get("institution")
            i_ = institutions.get(iid_)
            label_ = i_.get("name") if i_ else iid_
            form_bits.append(
                f"{esc(a_.get('role'))} — "
                f"<a href=\"/institutions/{iid_.split('/', 1)[1]}/\">"
                f"{esc(label_)}</a>")
        if form_bits:
            works_html = (f"<div class=panel><h2>Formation</h2><p>"
                          + "; ".join(form_bits) +
                          "</p><p class=note>Where the succession was made — "
                          "the institutions layer (I5.3).</p></div>"
                          + works_html)

        rel_html = ""
        my_rels = rels_by_person.get(pid, [])
        if my_rels:
            REL_VERB = {
                "tonsured": ("tonsured", "tonsured by"),
                "spiritual-father": ("spiritual father of",
                                     "spiritual child of"),
                "teacher": ("teacher of", "student of"),
                "influenced": ("influenced", "influenced by"),
                "consecrated": ("consecrated", "consecrated by"),
            }
            lines = ""
            for direction, rel in my_rels:
                other = rel["to"] if direction == "from" else rel["from"]
                fwd, back = REL_VERB.get(
                    rel.get("type"), (rel.get("type"), rel.get("type")))
                verb = fwd if direction == "from" else back
                lines += (f"<li>{esc(verb.capitalize())} {plink(other)}"
                          + (f" · {esc(fmt_date(rel.get('date')))}"
                             if rel.get("date") else "")
                          + f" {badge(rel.get('status'))}"
                          + (f"<div class=note>{esc(rel['notes'])}</div>"
                             if rel.get("notes") else "")
                          + citations_html(rel.get("sources"), sources_by_id)
                          + "</li>")
            rel_html = (f"<div class=panel><h2>Relationships</h2>"
                        f"<ul>{lines}</ul></div>")

        src_html = ("<div class=panel><h2>Sources</h2>"
                    + citations_html(p.get("sources"), sources_by_id)
                    + (f'<p class=note>{esc(p.get("notes"))}</p>'
                       if p.get("notes") else "") + "</div>")

        jsonld = {
            "@context": "https://schema.org", "@type": "Person",
            "name": person_name(p), "identifier": pid,
        }
        alt = [*(n.get("variants") or []),
               *(x.get("value") for x in n.get("native") or [])]
        if alt:
            jsonld["alternateName"] = alt
        ids = p.get("identifiers") or {}
        same = []
        if ids.get("wikidata"):
            same.append("https://www.wikidata.org/wiki/" + ids["wikidata"])
        if ids.get("viaf"):
            same.append("https://viaf.org/viaf/" + ids["viaf"])
        if same:
            jsonld["sameAs"] = same

        content = f"""<h1>{esc(person_name(p))} {badge(p.get('status'))}</h1>
<p class="subtitle">{esc(pid)} · attestation: <strong>{esc(p.get('attestation'))}</strong>
· role: <strong>{esc(p.get('role', 'bishop'))}</strong></p>
<div class="panel"><h2>Identity</h2><table><tbody>{ident}</tbody></table></div>
{ven_html}
<div class="panel"><h2>Sees held <span class="badge model">see-succession</span></h2>{tenure_html}</div>
<div class="panel"><h2>Consecration <span class="badge model">consecration-succession</span></h2>{cons_html}</div>
{works_html}{parts_html}{rel_html}{src_html}"""
        write(OUT / url.strip("/") / "index.html",
              layout(person_name(p), content, canonical, jsonld, "People",
                     description=person_entry_label(pid), entity_id=pid))

    # people index (Q1.4 display formula; F4 rail + filters + live count)
    def _p_century(p_, pid_):
        dy = date_year((p_.get("died") or {}).get("date"))
        if dy is None:
            ys = [date_year(t_.get("from"))
                  for t_ in tenures_by_person.get(pid_, [])]
            ys = [y for y in ys if y is not None]
            dy = ys[0] if ys else None
        return str((dy - 1) // 100 + 1) if dy else ""

    letters = defaultdict(list)
    p_roles, p_jurs, p_cents = set(), set(), set()
    for pid, p in sorted(persons.items(), key=lambda kv: person_name(kv[1])):
        role_ = p.get("role", "bishop")
        jur_ = pid.split("/")[1]
        cent_ = _p_century(p, pid)
        saint_ = "1" if (p.get("veneration") or {}).get("status") == "saint" else ""
        p_roles.add(role_)
        p_jurs.add(jur_)
        if cent_:
            p_cents.add(cent_)
        letters[person_name(p)[:1].upper()].append(
            f'<li data-role="{esc(role_)}" data-jurisdiction="{esc(jur_)}"'
            f' data-century="{esc(cent_)}"'
            f' data-status="{esc(p.get("status", "unverified"))}"'
            f' data-saint="{saint_}">{person_entry(pid)}</li>')
    az_rail = "".join(f'<a href="#az-{esc(k)}">{esc(k)}</a>'
                      for k, _ in sorted(letters.items()))
    people_idx = "".join(
        f'<h2 id="az-{esc(k)}">{esc(k)}</h2><ul class=person-list>'
        + "".join(vs) + "</ul>"
        for k, vs in sorted(letters.items()))

    def _psel(fid, label, options):
        opts = "".join(f'<option value="{esc(o)}">{esc(o)}</option>'
                       for o in sorted(options, key=lambda x: (len(x), x)))
        return (f'<label>{label} <select id="{fid}" class="ppl-filter">'
                f'<option value="">all</option>{opts}</select></label> ')

    people_idx = (
        f'<div class="filter-bar" id="pplFilters"><p class="lib-filters">'
        + _psel("p-role", "Role", p_roles)
        + _psel("p-jurisdiction", "Jurisdiction", p_jurs)
        + _psel("p-century", "Century", sorted(p_cents, key=int))
        + _psel("p-status", "Status", ["verified", "unverified", "disputed"])
        + '<label><input type="checkbox" id="p-saint"> saints only</label> '
        + '<span id="ppl-count" class="note"></span></p></div>'
        + f'<nav class="az-rail" aria-label="Jump to letter">{az_rail}</nav>'
        + people_idx
        + '<script src="/assets/people.js"></script>')
    write(OUT / "people" / "index.html",
          layout("People", f"<h1>People ({len(persons)})</h1>{people_idx}",
                 "https://tonyleroyrobin.github.io/orthodox-succession/people/",
                 active="People"))

    # ---------------- see pages ----------------
    for sid, s in sees.items():
        url = entity_url(sid)
        canonical = f"https://tonyleroyrobin.github.io/orthodox-succession{url}"
        ts = sorted(tenures_by_see.get(sid, []),
                    key=lambda t: date_year(t.get("from")) or 0)
        rows = "".join(
            f"<tr><td>{plink(t.get('person'))}</td>"
            f"<td>{esc(fmt_range(t.get('from'), t.get('to')))}</td>"
            f"<td>{esc(t.get('end_reason'))}</td>"
            f"<td>{badge(t.get('status'))}</td></tr>" for t in ts)
        table = (f"<table><thead><tr><th>Bishop</th><th>Tenure</th><th>End</th>"
                 f"<th>Status</th></tr></thead><tbody>{rows}</tbody></table>"
                 if rows else "<p class=note>No tenure records yet.</p>")
        loc = s.get("location") or {}
        locline = (f"<p>Location: {esc(loc.get('modern_place', '—'))} "
                   f"({loc.get('lat')}, {loc.get('lon')}) · "
                   f"<a href='/map/'>view on the map</a></p>"
                   if loc.get("lat") is not None else "")
        jsonld = {"@context": "https://schema.org", "@type": "Place",
                  "name": s.get("name"), "identifier": sid}
        if loc.get("lat") is not None:
            jsonld["geo"] = {"@type": "GeoCoordinates",
                             "latitude": loc["lat"], "longitude": loc["lon"]}
        content = f"""<h1>{esc(s.get('name'))} {badge(s.get('status'))}</h1>
<p class="subtitle">{esc(sid)}</p>
{locline}
<div class="panel"><h2>Timeline</h2>{see_timeline_svg(ts) or '<p class=note>No dated tenures.</p>'}
<p class=note>Occupancy gaps are shown honestly — see the <a href="/gaps/">gap report</a>.</p></div>
<div class="panel"><h2>Succession ({len(ts)} tenures)</h2>{table}</div>
<div class="panel"><h2>Record</h2>{citations_html(s.get('sources'), sources_by_id)}
{f'<p class=note>{esc(s.get("notes"))}</p>' if s.get('notes') else ''}</div>"""
        write(OUT / url.strip("/") / "index.html",
              layout(s.get("name", sid), content, canonical, jsonld, "Sees"))

    sees_idx = "".join(
        f'<li><a href="{entity_url(sid)}">{esc(s.get("name"))}</a> '
        f'<span class=note>({len(tenures_by_see.get(sid, []))} tenures)</span></li>'
        for sid, s in sorted(sees.items(), key=lambda kv: kv[1].get("name", "")))
    write(OUT / "sees" / "index.html",
          layout("Sees", f"<h1>Sees ({len(sees)})</h1><ul>{sees_idx}</ul>",
                 "https://tonyleroyrobin.github.io/orthodox-succession/sees/",
                 active="Sees"))

    # ---------------- jurisdiction pages ----------------
    sees_by_jur_prefix = defaultdict(list)
    for sid in sees:
        sees_by_jur_prefix[sid.split("/")[1]].append(sid)
    for jid, j in jurs.items():
        url = entity_url(jid)
        canonical = f"https://tonyleroyrobin.github.io/orthodox-succession{url}"
        prim = j.get("primatial_see")
        prim_ts = sorted(tenures_by_see.get(prim, []),
                         key=lambda t: date_year(t.get("from")) or 0) \
            if prim else []
        related = [sid for sid in sees
                   if any((h.get("jurisdiction") == jid)
                          for h in sees[sid].get("jurisdiction_history") or [])]
        if prim and prim not in related:
            related.append(prim)
        see_list = "".join(f"<li>{slink(sid)}</li>" for sid in sorted(related)) \
            or "<li class=note>none recorded via jurisdiction_history</li>"
        instr_html = ""
        if j.get("related_works"):
            instr_lines = "".join(
                f'<li><a href="{entity_url(w)}">'
                f'{esc((works_by_id.get(w) or {}).get("title", w))}</a></li>'
                for w in j["related_works"])
            instr_html = (f'<div class="panel"><h2>Instruments</h2>'
                          f'<p class=note>The primary legal documents behind '
                          f'this jurisdiction\'s status (SEEDS §B) — '
                          f'document-backed, not merely asserted.</p>'
                          f'<ul>{instr_lines}</ul></div>')
        content = f"""<h1>{esc(j.get('name'))} {badge(j.get('status'))}</h1>
<p class="subtitle">{esc(jid)} · type: <strong>{esc(j.get('type'))}</strong></p>
{instr_html}
<div class="panel"><h2>Primatial timeline{f" — {slink(prim)}" if prim else ""}</h2>
{see_timeline_svg(prim_ts) or '<p class=note>No dated primatial tenures.</p>'}</div>
<div class="panel"><h2>Sees</h2><ul>{see_list}</ul></div>
<div class="panel"><h2>Record</h2>{citations_html(j.get('sources'), sources_by_id)}
{f'<p class=note>{esc(j.get("notes"))}</p>' if j.get('notes') else ''}</div>"""
        write(OUT / url.strip("/") / "index.html",
              layout(j.get("name", jid), content, canonical,
                     active="Jurisdictions"))

    jur_idx = "".join(
        f'<li><a href="{entity_url(jid)}">{esc(j.get("name"))}</a> '
        f'<span class="badge model">{esc(j.get("type"))}</span></li>'
        for jid, j in sorted(jurs.items(), key=lambda kv: kv[1].get("name", "")))
    write(OUT / "jurisdictions" / "index.html",
          layout("Jurisdictions",
                 f"<h1>Jurisdictions ({len(jurs)})</h1><ul>{jur_idx}</ul>",
                 "https://tonyleroyrobin.github.io/orthodox-succession/jurisdictions/",
                 active="Jurisdictions"))

    # ---------------- council pages ----------------
    works_by_id = {w["id"]: w for w in works}
    # Q5: canons grouped by council
    canons_by_council = defaultdict(list)
    for r in by_kind["canon"]:
        canons_by_council[r["data"].get("council")].append(r["data"])
    canon_titles = {r["data"]["id"]: r["data"] for r in by_kind["canon"]}

    def canon_anchor(cid):
        suffix, num = cid.rsplit("/", 2)[-2:]
        return f"{entity_url('event/council/' + suffix)}#canon-{num}"

    for ev in councils:
        rid = ev["id"]
        url = entity_url(rid)
        if not url:
            continue
        canonical = f"https://tonyleroyrobin.github.io/orthodox-succession{url}"
        prows = "".join(
            f"<tr><td>{plink(pt.get('person'))}</td>"
            f"<td>{esc(pt.get('role'))}</td>"
            f"<td>{badge(pt.get('status'))}</td></tr>"
            for pt in parts_by_event.get(rid, []))
        ptable = (f"<table><thead><tr><th>Participant</th><th>Role</th>"
                  f"<th>Status</th></tr></thead><tbody>{prows}</tbody></table>"
                  if prows else "<p class=note>No participation records yet.</p>")
        outcomes = "".join(f"<li>{esc(o)}</li>"
                           for o in ev.get("outcomes") or [])
        d = ev.get("date") or {}
        recp = ev.get("canonical_reception")
        recp_html = ""
        if recp:
            recp_html = (f'<div class="panel"><h2>Reception</h2>'
                         f'<p><span class="badge reception {esc(recp)}">'
                         f'{esc(recp)}</span></p>'
                         + (f'<p class=note>{esc(ev["reception_note"])}</p>'
                            if ev.get("reception_note") else "")
                         + "</div>")
        rec_entries = ev.get("recognition") or []
        recog_html = ""
        if rec_entries:
            rlines = "".join(
                f"<li>{esc((r.get('by') or '').split('/')[-1])} — "
                f"{badge(r.get('status'))}"
                + (f" <span class=note>{esc(r['note'])}</span>"
                   if r.get("note") else "") + "</li>"
                for r in rec_entries)
            recog_html = (f'<div class="panel"><h2>Recognition '
                          f'(per recognizer)</h2><ul>{rlines}</ul></div>')
        rel_works = ev.get("related_works") or []
        rw_html = ""
        if rel_works:
            rw_lines = "".join(
                f'<li><a href="{entity_url(w)}">'
                f'{esc(works_by_id.get(w, {}).get("title", w))}</a></li>'
                for w in rel_works)
            rw_html = (f'<div class="panel"><h2>Related works</h2>'
                       f'<ul>{rw_lines}</ul></div>')
        # Q5: render this council's canons (full public-domain text)
        cns = sorted(canons_by_council.get(rid, []),
                     key=lambda c: c.get("number", 0))
        canons_html = ""
        if cns:
            body = ""
            for c in cns:
                cites = ""
                if c.get("cites"):
                    cites = ("<p class=note>Cites: " + " · ".join(
                        f'<a href="{canon_anchor(x)}">'
                        f'{esc(x.split("/")[1].replace("-", " "))} '
                        f'canon {esc(x.split("/")[2])}</a>'
                        for x in c["cites"]) + "</p>")
                cnote = (f"<p class=note>{esc(c['note'])}</p>"
                         if c.get("note") else "")
                body += (f'<details id="canon-{c["number"]}">'
                         f'<summary>Canon {c["number"]} '
                         f'{badge(c.get("status"))}</summary>'
                         f'<blockquote>{esc(c.get("text", ""))}</blockquote>'
                         f'{cnote}{cites}'
                         f'{citations_html(c.get("sources"), sources_by_id)}'
                         f'</details>')
            canons_html = (
                f'<div class="panel"><h2>Canons ({len(cns)})</h2>'
                f'<p class=note>Text: Percival&#39;s public-domain translation '
                f'(NPNF II.14) — the received interpretation may cite the '
                f'Pedalion by page, but its in-copyright text is never '
                f'reproduced.</p>{body}</div>')
        jsonld = {"@context": "https://schema.org", "@type": "Event",
                  "name": ev.get("title"), "identifier": rid}
        content = f"""<h1>{esc(ev.get('title'))} {badge(ev.get('status'))}</h1>
<p class="subtitle">{esc(rid)} · {esc(ev.get('type'))} ·
{esc(fmt_range(d.get('from'), d.get('to'), 'single session'))}
{f" · {esc(ev.get('place'))}" if ev.get('place') else ''}</p>
{recp_html}{recog_html}
{f'<div class="panel"><h2>Outcomes</h2><ul>{outcomes}</ul></div>' if outcomes else ''}
<div class="panel"><h2>Participants</h2>{ptable}</div>
{canons_html}{rw_html}
<div class="panel"><h2>Record</h2>{citations_html(ev.get('sources'), sources_by_id)}
{f'<p class=note>{esc(ev.get("notes"))}</p>' if ev.get('notes') else ''}</div>"""
        write(OUT / url.strip("/") / "index.html",
              layout(ev.get("title", rid), content, canonical, jsonld,
                     "Councils", entity_id=rid))

    GROUPS = [
        ("received-universally", "Received universally",
         "The seven ecumenical councils, the councils Orthodoxy treats "
         "with near-ecumenical authority, and the local councils whose "
         "canons entered the universal corpus (Quinisext canon 2)."),
        ("received-locally", "Received locally",
         "Councils whose acts are operative in part of the church or "
         "whose reception is qualified — see each record's note."),
        ("historical-only", "Historical significance only",
         "Recorded for their historical weight; not part of the received "
         "canonical or dogmatic corpus."),
        ("condemned", "Condemned or annulled",
         "Councils Orthodoxy rejects — recorded, not erased."),
        (None, "Reception not yet assessed", ""),
    ]

    def century(ev):
        y = date_year((ev.get("date") or {}).get("from"))
        return (y - 1) // 100 + 1 if y else None

    def c_entry(ev):
        cent = century(ev)
        return (f'<li data-type="{esc(ev.get("type"))}" '
                f'data-century="{cent or ""}">'
                f'<a href="{entity_url(ev["id"])}">{esc(ev.get("title"))}</a> '
                f'<span class=note>'
                f'{esc(fmt_date((ev.get("date") or {}).get("from")))} '
                f'· {esc(ev.get("type"))}'
                + (f" · {cent}{ord_suffix(int(cent))} c." if cent else "") + "</span></li>")

    c_sorted = sorted(councils, key=lambda e: date_year(
        (e.get("date") or {}).get("from")) or 0)
    c_groups = ""
    for key, label, blurb in GROUPS:
        evs = [e for e in c_sorted if e.get("canonical_reception") == key]
        if not evs:
            continue
        c_groups += (f"<h2>{esc(label)} ({len(evs)})</h2>"
                     + (f"<p class=note>{esc(blurb)}</p>" if blurb else "")
                     + "<ul class=council-list>"
                     + "".join(c_entry(e) for e in evs) + "</ul>")
    filter_ui = """<div class="panel" id="councilFilter">
<label>Type <select id="cfType"><option value="">all</option>
<option>council-ecumenical</option><option>council-local</option>
<option>synod</option></select></label>
<label>Century <input id="cfCentury" type="number" min="1" max="21"
placeholder="any" style="width:5em"></label>
</div>
<script>
(function () {
  var t = document.getElementById('cfType'),
      c = document.getElementById('cfCentury');
  function apply() {
    document.querySelectorAll('.council-list li').forEach(function (li) {
      var ok = (!t.value || li.dataset.type === t.value) &&
               (!c.value || li.dataset.century === c.value);
      li.style.display = ok ? '' : 'none';
    });
  }
  t.addEventListener('change', apply);
  c.addEventListener('input', apply);
})();
</script>"""
    write(OUT / "councils" / "index.html",
          layout("Councils",
                 f"<h1>Councils &amp; synods ({len(councils)})</h1>"
                 f"<p class=note>Grouped by canonical reception — recorded, "
                 f"never adjudicated; nuance lives in each record's "
                 f"reception note. Context events are a background layer, "
                 f"not listed here.</p>"
                 f"{filter_ui}{c_groups}",
                 "https://tonyleroyrobin.github.io/orthodox-succession/councils/",
                 active="Councils"))

    # ---------------- library (P6): filterable index + work pages ----------
    works_by_id = {w["id"]: w for w in works}
    preservers = defaultdict(list)  # work id -> ids of works preserved IN it
    for w in works:
        for pin in w.get("preserved_in") or []:
            preservers[pin].append(w["id"])
    controversies_all = {r["data"]["id"]: r["data"]
                         for r in by_kind["controversy"]}

    def tag_ids(rec):
        out = []
        for t in rec.get("controversies") or []:
            out.append(t["id"] if isinstance(t, dict) else t)
        return out

    def clink(cid):
        c = controversies_all.get(cid)
        return (f'<a href="{entity_url(cid)}">{esc(c.get("label"))}</a>'
                if c else esc(cid))

    def wlink(wid):
        w = works_by_id.get(wid)
        return (f'<a href="{entity_url(wid)}">{esc(w.get("title"))}</a>'
                if w else esc(wid))

    def work_century(w):
        y = date_year(w.get("date"))
        return "" if y is None else str((y - 1) // 100 + 1)

    def author_label(w):
        if w.get("author"):
            p = persons.get(w["author"])
            return person_entry_label(w["author"]) if p else w["author"]
        return w.get("author_display", "—")

    SURV_LABEL = {"extant": "extant", "fragmentary": "FRAGMENTARY",
                  "lost": "LOST",
                  "extant-in-translation-only": "extant in translation only"}

    def surv_badge(w):
        s = w.get("survival")
        if not s:
            return '<span class="badge model">not yet assessed</span>'
        cls = {"extant": "verified", "fragmentary": "unverified",
               "lost": "disputed",
               "extant-in-translation-only": "unverified"}[s]
        return f'<span class="badge {cls}">{esc(SURV_LABEL[s])}</span>'

    # per-work pages
    for w in works:
        wid = w["id"]
        url = entity_url(wid)
        canonical = f"https://tonyleroyrobin.github.io/orthodox-succession{url}"
        chain = ""
        if w.get("preserved_in"):
            chain = ("<p><strong>Survives in quotations within</strong> → " +
                     " · ".join(wlink(x) for x in w["preserved_in"]) + "</p>")
        preserved_here = preservers.get(wid) or []
        if preserved_here:
            chain += ("<p><strong>Preserves quotations of</strong> → " +
                      " · ".join(wlink(x) for x in preserved_here) + "</p>")
        eds = ""
        for ed in w.get("editions") or []:
            bits = [esc(str(x)) for x in (ed.get("series"), ed.get("translator"),
                                          ed.get("year")) if x]
            if ed.get("locator"):
                bits.append(esc(ed["locator"]))
            links = []
            if ed.get("url"):
                links.append(f'<a href="{esc(ed["url"])}" rel="nofollow">read</a>')
            if ed.get("archived_url"):
                links.append(f'<a href="{esc(ed["archived_url"])}" rel="nofollow">archived</a>')
            idf = ed.get("identifiers") or {}
            # F5: WorldCat demoted (rate-limits referred lookups) - Open
            # Library is the primary find-this-book affordance; identifiers
            # render as plain copyable text
            if idf.get("isbn"):
                isbn_ = esc(idf["isbn"])
                links.append(
                    f'ISBN <code class="copyable">{isbn_}</code> '
                    f'<button class="copy-btn" data-copy="{isbn_}">copy</button>')
                links.append(f'<a href="https://openlibrary.org/isbn/{isbn_}" rel="nofollow">find this book (Open Library)</a>')
                links.append(f'<a href="https://books.google.com/books?vid=ISBN{isbn_}" rel="nofollow">Google Books</a>')
            elif idf.get("oclc") or idf.get("worldcat"):
                oclc_ = esc(idf.get("oclc") or idf.get("worldcat"))
                links.append(
                    f'OCLC <code class="copyable">{oclc_}</code> '
                    f'<button class="copy-btn" data-copy="{oclc_}">copy</button>')
                links.append(f'<a href="https://books.google.com/books?vid=OCLC{oclc_}" rel="nofollow">Google Books</a>')
            ed_note = (f'<br><span class=note>{esc(ed["notes"])}</span>'
                       if ed.get("notes") else "")
            # F5: an URL-less edition is a plain print citation - the
            # series/locator bits above are the affordance; no dead links
            eds += (f"<li>{esc(ed.get('type', ''))} ({esc(ed.get('language', ''))})"
                    f" — {', '.join(bits)}"
                    f"{' · ' + ' · '.join(links) if links else ''}{ed_note}</li>")
        subj = ""
        if w.get("subject_of"):
            subj = ("<p><strong>About</strong> " +
                    " · ".join(plink(p) for p in w["subject_of"]) + "</p>")
        tags = tag_ids(w)
        tag_html = ("<p><strong>Controversies</strong> " +
                    " · ".join(clink(c) for c in tags) + "</p>") if tags else ""
        author_html = (plink(w["author"]) if w.get("author")
                       else esc(w.get("author_display", "—")))
        if w.get("author") and w.get("author_display"):
            author_html += f' <span class=note>({esc(w["author_display"])})</span>'
        content = f"""<h1>{esc(w.get("title"))} {badge(w.get("status"))}</h1>
<p class="subtitle">{esc(wid)} · {esc(w.get("genre", ""))} ·
{esc(fmt_date(w.get("date")))} · {esc(w.get("language", ""))}</p>
<div class="panel"><h2>Survival</h2>
<p>{surv_badge(w)}</p>
{f'<p>{esc(w.get("survival_note"))}</p>' if w.get("survival_note") else ''}
{chain}
<p class=note>Lost and fragmentary states are information, not defects —
absence of a text is part of its history.</p></div>
<div class="panel"><h2>Attribution &amp; author</h2>
<p><strong>{esc(w.get("attribution", ""))}</strong> · {author_html}</p>
{subj}
{f'<p>CPG/CPL: {esc(w.get("cpg"))}</p>' if w.get('cpg') else ''}
{tag_html}</div>
{f'<div class="panel"><h2>Editions &amp; read-links</h2><ul>{eds}</ul><p class=note>Links out only — texts are never re-hosted; archived copies are the fallback.</p></div>' if eds else ''}
<div class="panel"><h2>Record</h2>{citations_html(w.get('sources'), sources_by_id)}
{f'<p class=note>{esc(w.get("notes"))}</p>' if w.get('notes') else ''}</div>"""
        write(OUT / url.strip("/") / "index.html",
              layout(w.get("title", wid), content, canonical, active="Library",
                     description=author_label(w) + " · " + (w.get("genre") or "work"),
                     entity_id=wid))

    # filterable index
    def distinct(vals):
        return sorted({v for v in vals if v})

    authors_d = distinct(author_label(w) for w in works)
    genres_d = distinct(w.get("genre") for w in works)
    langs_d = distinct(w.get("language") for w in works)
    survs_d = distinct(w.get("survival", "not yet assessed") for w in works)
    cents_d = sorted({work_century(w) for w in works if work_century(w)},
                     key=int)

    def sel(fid, label, options):
        opts = "".join(f'<option value="{esc(o)}">{esc(o)}</option>'
                       for o in options)
        return (f'<label>{label} <select id="{fid}" class="lib-filter">'
                f'<option value="">all</option>{opts}</select></label> ')

    lib_works = [w for w in works if not w.get("external")]
    lib_rows = "".join(
        f'<tr id="{esc(w["id"].split("/", 1)[1])}"'
        f' data-author="{esc(author_label(w))}"'
        f' data-century="{esc(work_century(w))}"'
        f' data-genre="{esc(w.get("genre", ""))}"'
        f' data-language="{esc(w.get("language", ""))}"'
        f' data-survival="{esc(w.get("survival", "not yet assessed"))}">'
        f'<td><a href="{entity_url(w["id"])}">{esc(w.get("title"))}</a></td>'
        f'<td>{plink(w["author"]) if w.get("author") else esc(w.get("author_display", "—"))}</td>'
        f'<td>{esc(w.get("genre"))}</td>'
        f'<td>{esc(w.get("attribution"))}</td>'
        f'<td>{surv_badge(w)}</td>'
        f'<td>{esc(fmt_date(w.get("date")))}</td>'
        f'<td>{badge(w.get("status"))}</td></tr>'
        for w in sorted(lib_works, key=lambda w: w.get("title", "")))
    write(OUT / "library" / "index.html",
          layout("Library",
                 f"<h1>Library ({len(lib_works)} works)</h1>"
                 f"<p class=note>External (out-of-scope-author) works are excluded from the index and counts; they remain reachable from citing works and the <a href='/ideas/'>ideas graph</a>.</p>"
                 f"<p class=note>One Work, many Editions; each title opens "
                 f"the work page with survival, transmission, and "
                 f"read-links. See also the <a href='/bibliography/'>"
                 f"bibliography of sources</a>.</p>"
                 f"<div class=panel><p class='lib-filters'>"
                 + sel("f-author", "Author", authors_d)
                 + sel("f-century", "Century", cents_d)
                 + sel("f-genre", "Genre", genres_d)
                 + sel("f-language", "Language", langs_d)
                 + sel("f-survival", "Survival", survs_d)
                 + f"<span id='lib-count' class=note></span></p>"
                 f"<table><thead><tr><th>Title</th>"
                 f"<th>Author</th><th>Genre</th><th>Attribution</th>"
                 f"<th>Survival</th><th>Date</th><th>Status</th></tr></thead>"
                 f"<tbody id='lib-body'>{lib_rows}</tbody></table></div>"
                 f"<script src='/assets/library.js'></script>",
                 "https://tonyleroyrobin.github.io/orthodox-succession/library/",
                 active="Library"))

    # ---------------- controversy pages (P6) ----------------
    events_by_id = {r["data"]["id"]: r["data"] for r in by_kind["event"]
                    if r["data"].get("id")}
    tagged_events = defaultdict(list)
    tagged_parts = defaultdict(list)
    tagged_works = defaultdict(list)
    for r in by_kind["event"]:
        for cid in tag_ids(r["data"]):
            tagged_events[cid].append(r["data"])
    for pt in participations:
        for cid in tag_ids(pt):
            tagged_parts[cid].append(pt)
    for w in works:
        for cid in tag_ids(w):
            tagged_works[cid].append(w)

    for cid, c in controversies_all.items():
        url = entity_url(cid)
        canonical = f"https://tonyleroyrobin.github.io/orthodox-succession{url}"
        span = c.get("span") or {}
        span_txt = fmt_range(span.get("from"), span.get("to"),
                             open_label="ongoing")
        evs = sorted(tagged_events.get(cid, []),
                     key=lambda e: date_year((e.get("date") or {}).get("from")) or 0)
        ev_rows = ""
        for e in evs:
            y = date_year((e.get("date") or {}).get("from")) or "?"
            eurl = entity_url(e.get("id") or "")
            t_ = esc(e.get("title") or "")
            ev_rows += (f"<li>{y} — <a href=\"{eurl}\">{t_}</a></li>"
                        if eurl else f"<li>{y} — {t_}</li>")
        ev_rows = ev_rows or "<li class=note>none tagged yet</li>"
        pers_seen, pers_rows = set(), ""
        for pt in tagged_parts.get(cid, []):
            pid = pt.get("person")
            if pid in pers_seen:
                continue
            pers_seen.add(pid)
            evd = events_by_id.get(pt.get("event"))
            evt = evd.get("title") if evd else pt.get("event", "")
            pers_rows += (f"<li>{person_entry(pid)} — {esc(pt.get('role', ''))}, "
                          f"{esc(evt)}</li>")
        for e in evs:
            for pt in parts_by_event.get(e.get("id"), []):
                pid = pt.get("person")
                if pid not in pers_seen:
                    pers_seen.add(pid)
                    pers_rows += (f"<li>{person_entry(pid)} — "
                                  f"{esc(pt.get('role', ''))}, "
                                  f"{esc(e.get('title'))}</li>")
        wk_rows = "".join(
            f"<li>{wlink(w['id'])} — {esc(author_label(w))} {surv_badge(w)}</li>"
            for w in tagged_works.get(cid, [])) or "<li class=note>none tagged yet</li>"
        variants = ""
        for vt in c.get("variant_terms") or []:
            vnote = f" — {esc(vt['note'])}" if vt.get("note") else ""
            variants += f"<li><strong>{esc(vt.get('term'))}</strong>{vnote}</li>"
        content = f"""<h1>{esc(c.get("label"))} {badge(c.get("status"))}</h1>
<p class="subtitle">{esc(cid)} · {esc(span_txt)}</p>
<div class="panel"><p>{esc(c.get("description", ""))}</p>
{f'<h2>Recorded variant terms</h2><ul>{variants}</ul>' if variants else ''}
<p class=note>The database records where and when, never why — labels follow
the naming rule (docs/NAMING.md); variants are recorded, not endorsed.</p></div>
<div class="panel"><h2>Timeline of tagged events</h2><ul>{ev_rows}</ul></div>
<div class="panel"><h2>Persons (via participations)</h2><ul>{pers_rows or '<li class=note>none tagged yet</li>'}</ul></div>
<div class="panel"><h2>Works</h2><ul>{wk_rows}</ul></div>
<div class="panel"><h2>Record</h2>{citations_html(c.get('sources'), sources_by_id)}
{f'<p class=note>{esc(c.get("notes"))}</p>' if c.get('notes') else ''}</div>"""
        write(OUT / url.strip("/") / "index.html",
              layout(c.get("label", cid), content, canonical,
                     active="Controversies",
                     description=c.get("description", "")[:200],
                     entity_id=cid))

    contro_idx = "".join(
        f'<li><a href="{entity_url(cid)}">{esc(c.get("label"))}</a> '
        f'<span class=note>{esc(fmt_range((c.get("span") or {}).get("from"), (c.get("span") or {}).get("to"), open_label="ongoing"))}</span></li>'
        for cid, c in sorted(controversies_all.items(),
                             key=lambda kv: date_year((kv[1].get("span") or {}).get("from")) or 0))
    write(OUT / "controversies" / "index.html",
          layout("Controversies",
                 f"<h1>Controversies ({len(controversies_all)})</h1>"
                 f"<p class=note>A controlled thematic vocabulary (ceiling "
                 f"25). Each page assembles the story from tagged records — "
                 f"events, participations, works. Where and when, never "
                 f"why.</p><div class=panel><ul>{contro_idx}</ul></div>",
                 "https://tonyleroyrobin.github.io/orthodox-succession/controversies/",
                 active="Controversies"))

    # ---------------- bibliography page (P6) ----------------
    bib_groups = defaultdict(list)
    for sid_, r in sorted(sources_by_id.items()):
        bib_groups[r["data"].get("type", "other")].append(r["data"])
    bib_html = ""
    for typ in sorted(bib_groups):
        items = ""
        for s in sorted(bib_groups[typ], key=lambda s: s.get("title") or ""):
            links = []
            if s.get("url"):
                links.append(f'<a href="{esc(s["url"])}" rel="nofollow">link</a>')
            if s.get("archived_url"):
                links.append(f'<a href="{esc(s["archived_url"])}" rel="nofollow">archived</a>')
            author = f" — {esc(s['author'])}" if s.get("author") else ""
            s_note = (f"<br><span class=note>{esc(s['notes'])}</span>"
                      if s.get("notes") else "")
            # F5: URL-less sources are plain print citations (no WorldCat)
            items += (f"<li><strong>{esc(s.get('title'))}</strong>{author} "
                      f"{badge(s.get('status'))}"
                      f"{' · ' + ' · '.join(links) if links else ''}{s_note}</li>")
        bib_html += (f"<div class=panel><h2>{esc(typ)} "
                     f"({len(bib_groups[typ])})</h2><ul>{items}</ul></div>")
    write(OUT / "bibliography" / "index.html",
          layout("Bibliography",
                 f"<h1>Bibliography ({len(sources_by_id)} sources)</h1>"
                 f"<p class=note>Every Source record, grouped by type, with "
                 f"live and archived links. Reliability grades appear on "
                 f"each citation where the source is used.</p>{bib_html}",
                 "https://tonyleroyrobin.github.io/orthodox-succession/bibliography/",
                 active="Library"))

    # ---------------- glossary page (P6 draft) ----------------
    GLOSSARY = [
        ("autocephaly", "The status of a church that appoints its own primate and governs itself; the head of an autocephalous church commemorates no higher hierarch."),
        ("autonomy", "Self-governance short of autocephaly: the autonomous church's primate is confirmed by a mother church."),
        ("see", "A bishop's seat (cathedra) — the fixed point succession is counted against; this database's Tenure model attaches persons to sees."),
        ("jurisdiction", "A self-governing church body (patriarchate, autocephalous or autonomous church) grouping sees."),
        ("tenure", "One person's occupancy of one see over a date range — the unit of see-succession."),
        ("translation", "A bishop's move from one see to another; rendered here as one tenure ending (end_reason: translated) and another beginning."),
        ("locum tenens", "A caretaker administering a see during a vacancy; recorded here as a documented gap, not a tenure."),
        ("consecration", "The ordination of a bishop by other bishops — the edge of the consecration-succession DAG (principal consecrator vs. co-consecrators)."),
        ("synod", "A council of bishops; the endemousa (resident) synod of Constantinople was its standing form."),
        ("ecumenical council", "A council whose authority the whole church came to receive; this database records reception per recognizer rather than adjudicating the count."),
        ("canon", "A conciliar or patristic rule received into church law (e.g., the corpus collected in the Pedalion)."),
        ("glorification", "Formal recognition of a saint (canonization); veneration blocks in this database cite the recognizing authority."),
        ("oikonomia", "Pastoral flexibility in applying the canons for the salvation of persons — paired with akriveia, strict exactness."),
        ("akriveia", "Strict application of canonical norms; the pole opposite oikonomia."),
        ("metropolitan", "A bishop of a provincial capital with defined seniority over the province's bishops."),
        ("patriarch", "The primate of certain ancient or later-elevated jurisdictions; the five ancient patriarchates form the Pentarchy."),
        ("diptychs", "The ordered list of primates a church commemorates — the practical register of who recognizes whom."),
        ("tomos", "A formal synodal document, e.g. a tomos of autocephaly."),
        ("schism", "A break of communion without (in the first instance) a doctrinal condemnation."),
        ("anathema", "A formal conciliar condemnation excluding a person or teaching from communion."),
        ("deposition", "The removal of a bishop by synodal act; recorded here via participation roles (deposed-by) and tenure end_reasons."),
        ("recognition", "In this database: a per-recognizer statement of whether a tenure, autocephaly, or veneration is accepted — disputes are recorded, never adjudicated."),
        ("see-succession", "The order of occupants of a single see (the Tenure chain) — one of the two succession models, never conflated with the other."),
        ("consecration-succession", "The chain of episcopal consecrations (who ordained whom) — the second succession model, a DAG rather than a line."),
    ]
    gl_items = "".join(f"<dt>{esc(t)}</dt><dd>{esc(d)}</dd>"
                       for t, d in GLOSSARY)
    write(OUT / "glossary" / "index.html",
          layout("Glossary",
                 f"<h1>Glossary</h1>"
                 f"<div class=panel><p><span class='badge unverified'>DRAFT"
                 f"</span> Proposed definitions pending maintainer review "
                 f"(P6.5) — wording is not final until approved.</p></div>"
                 f"<div class=panel><dl class=glossary>{gl_items}</dl></div>",
                 "https://tonyleroyrobin.github.io/orthodox-succession/glossary/",
                 active="About"))

    # ---------------- gaps page ----------------
    gap_rows = ""
    for sid in sorted(tenures_by_see):
        ts = sorted(((date_year(t.get("from")), date_year(t.get("to")) or
                      date_year(t.get("from"))) for t in tenures_by_see[sid]
                     if date_year(t.get("from")) is not None))
        gaps, cursor = [], None
        for f, e in ts:
            if cursor is not None and f - cursor > 2:
                gaps.append(f"{cursor}–{f}")
            cursor = max(cursor or e, e)
        if gaps:
            gap_rows += (f"<tr><td>{slink(sid)}</td>"
                         f"<td>{esc(', '.join(gaps))}</td></tr>")
    # Q3.4: surface the latest link-rot report (written by check_links.py)
    link_report_html = ""
    lr_path = REPO_ROOT / "build" / "link-report.json"
    if lr_path.exists():
        try:
            lr = json.loads(lr_path.read_text(encoding="utf-8"))
            dead_rows = "".join(
                f"<tr><td>{esc(d['id'] or '?')}</td><td>{esc(d['where'])}</td>"
                f"<td>{esc(d['url'])}</td>"
                f"<td>{esc(d.get('suggested') or '(no archived_url!)')}</td></tr>"
                for d in lr.get("dead") or [])
            link_report_html = (
                f"<div class=panel><h2>Link health "
                f"<span class='badge model'>checked {esc(lr['checked_at'])}"
                f"</span></h2><p class=note>{lr['targets']} live URL "
                f"reference(s), {len(lr.get('dead') or [])} dead — from "
                f"scripts/check_links.py (reports only, never replaces).</p>"
                + (f"<table><thead><tr><th>Record</th><th>Where</th>"
                   f"<th>URL</th><th>Suggested replacement</th></tr></thead>"
                   f"<tbody>{dead_rows}</tbody></table>" if dead_rows else "")
                + "</div>")
        except Exception:
            pass
    write(OUT / "gaps" / "index.html",
          layout("Gap report",
                 "<h1>Occupancy gaps (&gt; 2 years)</h1>"
                 "<p class=note>Gaps are information, not defects: most are "
                 "documented suppressions, vacancies, or attestation "
                 "sparsity — each see record's notes explain its own. "
                 "Generated from the same data as scripts/gap_report.py.</p>"
                 f"<div class=panel><table><thead><tr><th>See</th>"
                 f"<th>Gaps</th></tr></thead><tbody>{gap_rows}</tbody>"
                 f"</table></div>" + link_report_html,
                 "https://tonyleroyrobin.github.io/orthodox-succession/gaps/"))

    # ---------------- home ----------------
    statuses = defaultdict(int)
    for r in records:
        st = r["data"].get("status")
        if st:
            statuses[st] += 1
    total = sum(statuses.values())
    prog = "".join(
        f'<span class="badge {k}">{k}: {v}</span> '
        for k, v in sorted(statuses.items()))
    counts_line = (f"{len(persons)} people · {len(sees)} sees · "
                   f"{len(jurs)} jurisdictions · {len(tenures)} tenures · "
                   f"{len(councils)} councils · {len(works)} works")
    home = f"""<h1>Orthodox Apostolic Succession Database</h1>
<p class="subtitle">A structured, sourced database of Eastern Orthodox
apostolic succession — strictly Chalcedonian in scope. Every substantive
claim carries a graded citation; recognition disputes are recorded, never
adjudicated.</p>
<div class="panel"><h2>The dataset</h2>
<p>{esc(counts_line)}</p>
<p>Verification progress across {total} records: {prog}</p>
<p class=note>Programmatic imports enter as <em>unverified</em> and stay
that way until the maintainer confirms them against a graded source.</p></div>
<div class="panel" id="calendarPanel"><h2>Commemorated today</h2>
<div id="calendar"><p class=note>Feast-day data is baked into this site;
today's commemorations are computed in your browser (the one genuinely
date-dependent element).</p></div></div>
<div class="panel"><h2>Explore</h2><ul>
<li><a href="/map/">The map</a> — every located see, 33 AD to today.</li>
<li><a href="/sees/">Sees</a> and their succession tables.</li>
<li><a href="/people/">People</a> — {len(persons)} bishops and connected figures.</li>
<li><a href="/councils/">Councils</a> and their subscription lists.</li>
<li><a href="/library/">The library</a> of works with read-links.</li>
<li><a href="/graph/">The consecration graph</a> (interactive, with lineage tracing).</li>
<li><a href="/gaps/">The gap report</a> — absence as information.</li>
</ul></div>"""
    write(OUT / "index.html",
          layout("Home", home,
                 "https://tonyleroyrobin.github.io/orthodox-succession/",
                 active="Home"))

    # ---------------- about ----------------
    about = f"""<h1>About</h1>
<div class="panel"><h2>Scope</h2>
<p>Canonical Chalcedonian Eastern Orthodox jurisdictions and their
historical antecedents. Contested canonical cases (OCA, OCU, the
Macedonian church) are in scope via per-recognizer recognition entries —
the data records disputes, it does not adjudicate them. Apostolic claims
without surviving lineage live as tradition records; Oriental Orthodox,
Church of the East, and Eastern Catholic churches are out of scope.</p></div>
<div class="panel"><h2>The two succession models</h2>
<p><strong>Succession of sees</strong> — ordered occupancy of a throne
(what ancient records preserve, back to the apostolic era) — and
<strong>succession of consecrations</strong> — who laid hands on whom, a
directed acyclic graph documentable mostly from the 15th century onward.
The two are never conflated; absent consecration data is stated, not
inferred.</p></div>
<div class="panel"><h2>Methodology</h2>
<p>Every substantive claim carries a citation graded
<em>primary · official-list · scholarly · tradition</em>; web sources carry
archive.org snapshots. Every record carries a verification status; only
human review against a graded source promotes a record to
<em>verified</em>, and imports are never auto-promoted. Records citing two
or more independent non-tradition sources wear a
<span class="badge corroborated">corroborated</span> badge.</p></div>
<div class="panel"><h2>Governance &amp; reuse</h2>
<p><a href="https://github.com/TonyLeroyRobin/orthodox-succession/blob/main/docs/NEUTRALITY.md">Neutrality</a> ·
<a href="https://github.com/TonyLeroyRobin/orthodox-succession/blob/main/docs/NAMING.md">Naming</a> ·
<a href="https://github.com/TonyLeroyRobin/orthodox-succession/blob/main/CONTRIBUTING.md">Contributing</a> ·
<a href="https://github.com/TonyLeroyRobin/orthodox-succession/blob/main/CHANGELOG.md">Changelog</a></p>
<p>Data: CC BY 4.0 · Code: MIT · Corrections come as pull requests with
graded sources; contact via
<a href="https://github.com/TonyLeroyRobin/orthodox-succession/issues">GitHub issues</a>.</p>
<p>Cite the dataset: Robinson, L. (2026). <em>Orthodox Apostolic Succession
Database</em> ({esc(VERSION)}) [Data set]. Zenodo.
<a href="https://doi.org/10.5281/zenodo.21382721">doi:10.5281/zenodo.21382721</a>
(concept DOI — always the latest version).</p></div>"""
    write(OUT / "about" / "index.html",
          layout("About", about,
                 "https://tonyleroyrobin.github.io/orthodox-succession/about/",
                 active="About"))

    # ---------------- search page + index ----------------
    docs = []
    for pid, p in persons.items():
        n = p.get("names") or {}
        docs.append({"id": pid, "type": "person",
                     "name": person_entry_label(pid),
                     "variants": " ".join([*(n.get("variants") or []),
                                           *(x.get("value") for x in
                                             n.get("native") or [])]),
                     "url": BASE + entity_url(pid)})
    for sid, s in sees.items():
        docs.append({"id": sid, "type": "see", "name": s.get("name", sid),
                     "variants": (s.get("location") or {}).get("modern_place", ""),
                     "url": BASE + entity_url(sid)})
    for ev in councils:
        docs.append({"id": ev["id"], "type": "council",
                     "name": ev.get("title", ev["id"]), "variants": "",
                     "url": BASE + entity_url(ev["id"])})
    for w in works:
        docs.append({"id": w["id"], "type": "work",
                     "name": w.get("title", w["id"]), "variants": "",
                     "url": BASE + entity_url(w["id"])})
    write(OUT / "data" / "search-index.json",
          json.dumps(docs, ensure_ascii=False))
    write(OUT / "search" / "index.html",
          layout("Search",
                 """<h1>Search</h1>
<div class="panel"><form id="searchform">
<input type="search" id="q" placeholder="Names, variants, native scripts, sees, councils, works…" style="width:100%;padding:.5rem">
</form><div id="results"><p class=note>Type to search; matching includes
name variants and native scripts.</p></div></div>
<script src="/assets/vendor/minisearch.min.js"></script>
<script src="/assets/search.js"></script>""",
                 "https://tonyleroyrobin.github.io/orthodox-succession/search/"))

    # ---------------- map page + data ----------------
    map_rows = []
    for sid, s in sees.items():
        loc = s.get("location") or {}
        if loc.get("lat") is None:
            continue
        spans = []
        for t in tenures_by_see.get(sid, []):
            f = date_year(t.get("from"))
            if f is None:
                continue
            open_ = not t.get("to")
            e = date_year(t.get("to")) or (2026 if (open_ and f > 1900) else f)
            p = persons.get(t.get("person"))
            disputed = any(r.get("status") in
                           ("disputed", "rival-claimant", "not-recognized")
                           for r in t.get("recognition") or [])
            spans.append({"f": f, "e": e, "s": t.get("status"),
                          "n": person_name(p), "p": t.get("person"),
                          "d": disputed})
        sup = date_year((s.get("suppressed") or {}).get("date"))
        # Q7: apostolic-foundation flag (distinct ring on the map)
        af = bool(s.get("apostolic_founder") or s.get("apostolic_founders"))
        map_rows.append({"id": sid, "name": s.get("name"),
                         "lat": loc["lat"], "lon": loc["lon"],
                         "url": BASE + entity_url(sid), "sup": sup,
                         "af": af, "t": spans})
    write(OUT / "data" / "map-data.json",
          json.dumps(map_rows, ensure_ascii=False))

    # controversy map layer (P6): geography derived from tagged data ONLY —
    # the sees of persons connected via tagged participations and tagged
    # works' authors. Council places have no coordinates and controversy
    # records name no structured regions, so neither renders (if it isn't
    # derivable from tagged records, it doesn't render).
    contro_geo = {}
    for cid, c in controversies_all.items():
        pids = {pt.get("person") for pt in tagged_parts.get(cid, [])}
        for e in tagged_events.get(cid, []):
            for pt in parts_by_event.get(e.get("id"), []):
                pids.add(pt.get("person"))
        for w in tagged_works.get(cid, []):
            if w.get("author"):
                pids.add(w["author"])
        pts, seen_sees = [], set()
        for pid in pids:
            for t in tenures_by_person.get(pid, []):
                sid = t.get("see")
                if sid in seen_sees:
                    continue
                s = sees.get(sid) or {}
                loc = s.get("location") or {}
                if loc.get("lat") is None:
                    continue
                seen_sees.add(sid)
                pts.append({"see": s.get("name"), "lat": loc["lat"],
                            "lon": loc["lon"],
                            "via": person_name(persons.get(pid))})
        span = c.get("span") or {}
        contro_geo[cid.split("/", 1)[1]] = {
            "label": c.get("label"),
            "f": date_year(span.get("from")),
            "e": date_year(span.get("to")),
            "points": pts,
        }
    write(OUT / "data" / "controversy-geo.json",
          json.dumps(contro_geo, ensure_ascii=False))
    map_page = """<h1>Sees over time</h1>
<p class="subtitle">Every see with recorded coordinates renders from its first
attested date onward and never disappears while it exists. The marker links to
the see page.</p>
<div class="panel">
<div class="map-controls">
<label for="yearSlider">Year: <strong id="yearLabel"></strong></label>
<input type="range" id="yearSlider" min="33" max="2026" value="2026" step="1">
<button id="playBtn">&#9654; play</button>
<button id="resetView">reset view</button>
<label for="controSel"> Controversy layer:
<select id="controSel"><option value="">off</option></select></label>
</div>
<div class="map-controls" role="group" aria-label="highlight toggles">
<label><input type="checkbox" class="hl-toggle" value="pent"> highlight Pentarchy</label>
<label><input type="checkbox" class="hl-toggle" value="af"> apostolic foundations</label>
<label><input type="checkbox" class="hl-toggle" value="today"> active today</label>
<label><input type="checkbox" id="instToggle" checked> institutions (triangles)</label>
</div>
<div class="map-controls era-presets" role="group" aria-label="era presets">
<button class="era-btn" data-year="33">33</button>
<button class="era-btn" data-year="325">325</button>
<button class="era-btn" data-year="451">451</button>
<button class="era-btn" data-year="787">787</button>
<button class="era-btn" data-year="1054">1054</button>
<button class="era-btn" data-year="1204">1204</button>
<button class="era-btn" data-year="1453">1453</button>
<button class="era-btn" data-year="1917">1917</button>
<button class="era-btn" data-year="2026">today</button>
</div>
<div id="map" role="img" aria-label="Map of sees over time; the year slider and era buttons control the displayed year"></div>
<p class="note map-legend"><strong>Legend:</strong>
<span style="color:#2e7d32">&#9679;</span> filled = tenure active that year
(green verified, amber unverified, red disputed; dashed ring = recognition
disputed) &middot; &#9675; hollow = attested, no recorded occupant &middot;
<span style="color:#9a9a9a">&#8855;</span> grayed/crossed = suppressed (date in
the tooltip) &middot; <span style="color:#5d5480">&#9678;</span> outer dashed
ring = apostolic foundation &middot; triangle = institution (monastery/school;
hollow gray = suppressed or closed at the slider date) (a distinct shape channel - fill still means
verification status, one channel one meaning) &middot; Pentarchy sees stay
labeled at all zooms; other labels appear as you zoom. Highlight toggles dim
non-matching markers. Scroll or pinch to zoom, drag to pan.</p>
<p class=note>Basemap: Natural Earth, bundled — the site makes no external
requests. Coverage reflects the dataset, not history (see the
<a href="/gaps/">gap report</a>).</p>
</div>
<script src="/assets/vendor/d3.v7.min.js"></script>
<script src="/assets/vendor/topojson-client.min.js"></script>
<script src="/assets/map.js"></script>"""
    write(OUT / "map" / "index.html",
          layout("Map", map_page,
                 "https://tonyleroyrobin.github.io/orthodox-succession/map/",
                 active="Map"))

    # ---------------- timeline overview page (R3) ----------------
    # Jurisdiction accordions (Pentarchy expanded), sticky axis + see-name
    # column, jump-to-see typeahead, 3px minimum bars with overflow class,
    # era bands from duration context events, scope-filtered to open groups.
    TL_START, TL_END, TL_SCALE = 33, 2026, 0.75
    def tl_x(year):
        return (max(TL_START, min(TL_END, year)) - TL_START) * TL_SCALE
    tl_width = int(tl_x(TL_END)) + 1
    PENT_PREFIXES = ("constantinople", "alexandria", "antioch", "jerusalem",
                     "pre-schism-rome")
    prefix_jid = {}
    for jid, j in jurs.items():
        prim = j.get("primatial_see")
        if prim and len(prim.split("/")) > 2:
            prefix_jid.setdefault(prim.split("/")[1], jid)

    def tl_rows_html(prefix):
        rows = []
        for sid in sees_by_jur_prefix[prefix]:
            s = sees[sid]
            spans = []
            earliest = 9999
            for t in tenures_by_see.get(sid, []):
                f = date_year(t.get("from"))
                if f is None:
                    continue
                open_ = not t.get("to")
                e = date_year(t.get("to")) or (2026 if (open_ and f > 1900) else f)
                p = persons.get(t.get("person"))
                disputed = any(r.get("status") in
                               ("disputed", "rival-claimant", "not-recognized")
                               for r in t.get("recognition") or [])
                spans.append((f, max(e, f), t, p, disputed))
                earliest = min(earliest, f)
            rows.append((earliest, sid, s, spans))
        rows.sort(key=lambda r: (r[0], r[2].get("name") or ""))
        out = []
        for earliest, sid, s, spans in rows:
            bars = []
            for f, e, t, p, disputed in sorted(spans, key=lambda x: (x[0], x[1])):
                left = tl_x(f)
                raw_w = tl_x(e) - left
                w = max(raw_w, 3)
                cls = "tl-bar " + (t.get("status") or "unverified")
                if disputed:
                    cls += " disputed-rec"
                if raw_w < 3:
                    cls += " tl-ovf"  # overflow marker: inflated to minimum width
                nm = person_name(p)
                purl = entity_url(t.get("person")) or "#"
                bars.append(
                    f'<a class="{esc(cls)}" href="{purl}" '
                    f'style="left:{left:.1f}px;width:{w:.1f}px" '
                    f'title="{esc(nm)} ({f}–{e}) · {esc(t.get("status") or "")}"></a>')
            sup = date_year((s.get("suppressed") or {}).get("date"))
            if sup is not None:
                bars.append(
                    f'<span class="tl-sup" style="left:{tl_x(sup):.1f}px" '
                    f'title="suppressed {sup}">×</span>')
            out.append(
                f'<div class="tl-row" data-name="{esc((s.get("name") or "").lower())}">'
                f'<div class="tl-name"><a href="{entity_url(sid)}">'
                f'{esc(s.get("name") or sid)}</a></div>'
                f'<div class="tl-track" style="width:{tl_width}px">{"".join(bars)}</div>'
                f'</div>')
        return "".join(out)

    axis_ticks = "".join(
        f'<span class="tl-tick" style="left:{tl_x(y):.1f}px">{y}</span>'
        for y in [33] + list(range(200, 2001, 200)) + [2026])
    band_divs, mark_divs = [], []
    for r in by_kind["event"]:
        d = r["data"]
        if d.get("type") != "context":
            continue
        dt = d.get("date") or {}
        f = date_year(dt.get("from"))
        if f is None:
            continue
        e = date_year(dt.get("to"))
        scope = d.get("scope") or "global"
        jid = scope.split(":", 1)[1] if scope.startswith("jurisdiction:") else ""
        title = esc(d.get("title") or "")
        if e is not None and e > f:
            band_divs.append(
                f'<div class="tl-band" data-jid="{esc(jid)}" '
                f'style="left:{tl_x(f):.1f}px;width:{max(tl_x(e)-tl_x(f),2):.1f}px" '
                f'title="{title} ({f}–{e})"><span>{title}</span></div>')
        else:
            mark_divs.append(
                f'<span class="tl-mark" data-jid="{esc(jid)}" '
                f'style="left:{tl_x(f):.1f}px" title="{title} ({f})"></span>')

    groups_html = []
    datalist = set()
    for prefix in sorted(sees_by_jur_prefix,
                         key=lambda p: (p not in PENT_PREFIXES, p)):
        jid = prefix_jid.get(prefix)
        jname = jurs[jid]["name"] if jid and jid in jurs else prefix.replace("-", " ").title()
        n = len(sees_by_jur_prefix[prefix])
        open_attr = " open" if prefix in PENT_PREFIXES else ""
        groups_html.append(
            f'<details class="tl-jur" data-jid="{esc(jid or "")}"{open_attr}>'
            f'<summary>{esc(jname)} <span class="badge model">{n} see{"s" if n != 1 else ""}</span></summary>'
            f'{tl_rows_html(prefix)}</details>')
        for sid in sees_by_jur_prefix[prefix]:
            nm = sees[sid].get("name")
            if nm:
                datalist.add(nm)
    datalist_html = "".join(f"<option value=\"{esc(n)}\">"
                            for n in sorted(datalist))
    timeline_page = f"""<h1>Timeline of the sees</h1>
<p class="subtitle">Jurisdiction accordions (the Pentarchy expanded by
default); every dated tenure as a bar (minimum 3px — outlined bars are
shorter than they render), click-through to the person; era bands and event
markers from the context layer, filtered to the expanded jurisdictions plus
global events. Detail lives on the per-see pages.</p>
<div class="panel">
<div class="map-controls">
<label for="tlJump">Jump to see: </label>
<input id="tlJump" list="tlSees" placeholder="type a see name…">
<datalist id="tlSees">{datalist_html}</datalist>
</div>
<div class="tl-wrap">
<div class="tl-inner" style="width:{tl_width + 180}px">
<div class="tl-axis"><div class="tl-name tl-axis-name"></div>
<div class="tl-track" style="width:{tl_width}px">{axis_ticks}</div></div>
<div class="tl-bands"><div class="tl-name tl-band-name">context</div>
<div class="tl-track" style="width:{tl_width}px">{''.join(band_divs)}{''.join(mark_divs)}</div></div>
{''.join(groups_html)}
</div>
</div>
<p class=note>Bars are colored by record status (green verified, amber
unverified, red disputed); dashed outline = recognition disputed;
× = see suppressed. The context layer renders era bands (events with
durations) and point markers — <a href="/about/">about the layers</a>.</p>
</div>
<script src="/assets/timeline.js"></script>"""
    write(OUT / "timeline" / "index.html",
          layout("Timeline", timeline_page,
                 "https://tonyleroyrobin.github.io/orthodox-succession/timeline/",
                 active="Timeline"))

    # ---------------- calendar data ----------------
    cal = []
    for pid, p in persons.items():
        ven = p.get("veneration")
        if not ven or ven.get("status") != "saint":
            continue
        feasts = [f for f in ven.get("feast_days") or [] if f.get("month_day")]
        if feasts:
            cal.append({"id": pid, "name": person_name(p),
                        "url": BASE + entity_url(pid),
                        "titles": ven.get("titles") or [],
                        "feasts": [{"md": f["month_day"],
                                    "cal": f.get("calendar", "gregorian"),
                                    "note": f.get("note", "")}
                                   for f in feasts]})
    write(OUT / "data" / "calendar-data.json",
          json.dumps(cal, ensure_ascii=False))

    # ---------------- ideas graph (C3.1) ----------------
    # Three networks, three meanings: documented correspondence (Tier 1) and
    # documented citation/response (Tier 2); the gated influence
    # relationships overlay as Tier 3, off by default.
    ideas_nodes, ideas_links = {}, []

    def _inode(key, label=None, external=False):
        if key not in ideas_nodes:
            if external:
                ideas_nodes[key] = {"id": key, "label": label or key,
                                    "url": None, "external": True}
            else:
                p_ = persons.get(key)
                ideas_nodes[key] = {
                    "id": key,
                    "label": person_name(p_) if p_ else key,
                    "url": BASE + (entity_url(key) or ""),
                    "external": False}
        return key

    def _author_key(w):
        if w.get("author"):
            return _inode(w["author"])
        if w.get("external"):
            nm = w.get("author_name") or w.get("title")
            return _inode("ext:" + nm, label=nm, external=True)
        return None

    cite_indegree = defaultdict(int)
    for w in works:
        has_edges = (w.get("addressee") or w.get("cites")
                     or w.get("responds_to"))
        a = _author_key(w) if (has_edges or w.get("external")) else None
        for ad in w.get("addressee") or []:
            if a:
                ideas_links.append({
                    "source": a, "target": _inode(ad), "tier": 1,
                    "work": BASE + (entity_url(w["id"]) or ""),
                    "title": w.get("title"), "locator": ""})
        for c in w.get("cites") or []:
            tw = works_by_id.get(c.get("work"))
            cite_indegree[c.get("work")] += 1
            if not tw:
                continue
            b = _author_key(tw) if (tw.get("author") or tw.get("external")) \
                else None
            if a and b and a != b:
                ideas_links.append({
                    "source": a, "target": b, "tier": 2,
                    "work": BASE + (entity_url(w["id"]) or ""),
                    "title": w.get("title"),
                    "locator": c.get("locator", "")})
        for rid_ in (w.get("responds_to") or []) + (w.get("preserved_in") or []):
            tw = works_by_id.get(rid_)
            cite_indegree[rid_] += 1
            if not tw:
                continue
            b = _author_key(tw) if (tw.get("author") or tw.get("external")) \
                else None
            if a and b and a != b:
                ideas_links.append({
                    "source": a, "target": b, "tier": 2,
                    "work": BASE + (entity_url(w["id"]) or ""),
                    "title": w.get("title"),
                    "locator": "responds to / preserves"})
    for rel_ in relationships:
        if rel_.get("type") == "influenced":
            ideas_links.append({
                "source": _inode(rel_.get("from")),
                "target": _inode(rel_.get("to")), "tier": 3,
                "work": "", "title": "influenced (scholarly-gated)",
                "locator": ""})
    write(OUT / "data" / "ideas-graph.json",
          json.dumps({"nodes": list(ideas_nodes.values()),
                      "links": ideas_links}, ensure_ascii=False),
          sitemap=False)
    # C3.4: info-level analytics in the build report
    top_cited = sorted(cite_indegree.items(), key=lambda kv: -kv[1])[:5]
    if top_cited:
        print("build_site: most-cited works (citation in-degree): " +
              "; ".join(f"{works_by_id.get(k, {}).get('title', k)} ({v})"
                        for k, v in top_cited))
    # F1.3: static fallback — the page must be fully informative with JS off
    TIER_LABEL = {1: "Tier 1 · correspondence", 2: "Tier 2 · citation/response",
                  3: "Tier 3 · influence (gated)"}
    edge_rows = ""
    def _unbase(u):
        # JSON urls carry BASE for the JS layer; build-time HTML must not,
        # or write() double-prefixes them (caught by the F3.2 link gate)
        return u[len(BASE):] if BASE and u and u.startswith(BASE + "/") else u

    for l_ in sorted(ideas_links, key=lambda x: (x["tier"], x.get("title") or "")):
        src_n = ideas_nodes.get(l_["source"], {})
        tgt_n = ideas_nodes.get(l_["target"], {})
        def _nlabel(n):
            return (f'<a href="{_unbase(n["url"])}">{esc(n.get("label", "?"))}</a>'
                    if n.get("url") else esc(n.get("label", "?")) + " (external)")
        wcell = (f'<a href="{_unbase(l_["work"])}">{esc(l_.get("title") or "")}</a>'
                 if l_.get("work") else esc(l_.get("title") or "—"))
        if l_.get("locator"):
            wcell += f' <span class=note>({esc(l_["locator"])})</span>'
        edge_rows += (f"<tr><td>{_nlabel(src_n)}</td><td>{wcell}</td>"
                      f"<td>{_nlabel(tgt_n)}</td>"
                      f'<td><span class="badge model">{TIER_LABEL[l_["tier"]]}'
                      f"</span></td></tr>")
    ideas_table = (f'<div class="panel"><h2>All documented edges '
                   f'({len(ideas_links)})</h2>'
                   f"<table><thead><tr><th>From</th><th>Evidencing work</th>"
                   f"<th>To</th><th>Tier</th></tr></thead>"
                   f"<tbody>{edge_rows}</tbody></table>"
                   f"<p class=note>This table is the complete graph content, "
                   f"rendered at build time — no JavaScript required.</p></div>")
    ideas_page = """<h1>The succession of ideas</h1>
<p class="subtitle">The database renders three successions, never blended:
hands (the <a href="/graph/">consecration graph</a>), formation
(teacher/tonsure relationships on person pages), and IDEAS — documented
correspondence and citation, shown here. The graph is smaller than the truth
and never larger.</p>
<div class="panel">
<p class="map-controls"><label><input type="checkbox" id="tier3toggle">
show Tier 3 (inferred influence, scholarly-gated) overlay</label></p>
<div id="ideas"></div>
<p class="note"><strong>Legend:</strong> solid = Tier 1, documented
correspondence (a surviving letter with an addressee) &middot; dashed =
Tier 2, documented citation/response (passage-sourced) &middot; dotted
purple = Tier 3, inferred influence (exists only via the gated
<code>influenced</code> relationship; off by default). Edge tooltips name
the evidencing work and locator; click a node for the person, an edge for
the work. Squares are external (out-of-scope) authors.</p>
</div>
<script src="/assets/vendor/d3.v7.min.js"></script>
<script src="/assets/ideas.js"></script>""" + ideas_table
    write(OUT / "ideas" / "index.html",
          layout("Ideas graph", ideas_page,
                 "https://tonyleroyrobin.github.io/orthodox-succession/ideas/"))

    # ---------------- works timeline (C3.2) ----------------
    WT_SCALE = 0.75

    def wt_x(y):
        return (max(33, min(2026, y)) - 33) * WT_SCALE

    wt_width = int(wt_x(2026)) + 1
    genres_present = sorted({w.get("genre") for w in works
                             if w.get("genre") and date_year(w.get("date"))})
    wt_rows = ""
    for gname in genres_present:
        dots = ""
        for w in works:
            if w.get("genre") != gname:
                continue
            y = date_year(w.get("date"))
            if y is None:
                continue
            tags_ = [x if isinstance(x, str) else x.get("id", "")
                     for x in w.get("controversies") or []]
            color = "#5d5480" if tags_ else "#8a7f6a"
            tagtxt = (" · " + ", ".join(x.replace("controversy/", "")
                                        for x in tags_)) if tags_ else ""
            dots += (f'<a class="wt-dot" href="{entity_url(w["id"])}" '
                     f'style="left:{wt_x(y):.1f}px;background:{color}" '
                     f'title="{esc(w.get("title", ""))} ({y}){esc(tagtxt)}"></a>')
        wt_rows += (f'<div class="tl-row">'
                    f'<div class="tl-name">{esc(gname)}</div>'
                    f'<div class="tl-track" style="width:{wt_width}px">{dots}</div>'
                    f'</div>')
    wt_axis = "".join(
        f'<span class="tl-tick" style="left:{wt_x(y):.1f}px">{y}</span>'
        for y in [33] + list(range(200, 2001, 200)) + [2026])
    wt_bands = ""
    for r_ in by_kind["event"]:
        d_ = r_["data"]
        if d_.get("type") != "context" or d_.get("scope") != "global":
            continue
        dt_ = d_.get("date") or {}
        f_, e_ = date_year(dt_.get("from")), date_year(dt_.get("to"))
        if f_ is None or e_ is None or e_ <= f_:
            continue
        wt_bands += (f'<div class="tl-band" '
                     f'style="left:{wt_x(f_):.1f}px;'
                     f'width:{max(wt_x(e_) - wt_x(f_), 2):.1f}px" '
                     f'title="{esc(d_.get("title", ""))} ({f_}–{e_})">'
                     f'<span>{esc(d_.get("title", ""))}</span></div>')
    wt_page = f"""<h1>Works on the time axis</h1>
<p class="subtitle">Every dated work, laned by genre; purple = tagged with a
controversy (the tooltip names it); global era bands behind. Pure rendering
of existing data.</p>
<div class="panel">
<div class="tl-wrap">
<div class="tl-inner" style="width:{wt_width + 180}px">
<div class="tl-axis"><div class="tl-name tl-axis-name"></div>
<div class="tl-track" style="width:{wt_width}px">{wt_axis}</div></div>
<div class="tl-bands"><div class="tl-name tl-band-name">eras</div>
<div class="tl-track" style="width:{wt_width}px">{wt_bands}</div></div>
{wt_rows}
</div></div>
<p class=note>Linked from the <a href="/library/">library</a>; dots click
through to work pages.</p></div>"""
    write(OUT / "works-timeline" / "index.html",
          layout("Works timeline", wt_page,
                 "https://tonyleroyrobin.github.io/orthodox-succession/works-timeline/",
                 active="Library"))

    # ---------------- institutions (I5) ----------------

    def ilink(iid):
        i_ = institutions.get(iid)
        return (f'<a href="/institutions/{iid.split("/", 1)[1]}/">'
                f'{esc(i_.get("name"))}</a>' if i_ else esc(iid))

    for iid, inst in institutions.items():
        slug_ = iid.split("/", 1)[1]
        canonical = (f"https://tonyleroyrobin.github.io/orthodox-succession"
                     f"/institutions/{slug_}/")
        jh = ""
        for h in inst.get("jurisdiction_history") or []:
            j_ = h.get("jurisdiction", "")
            jname = (jurs.get(j_) or {}).get("name", j_)
            jlink = (f'<a href="{entity_url(j_)}">{esc(jname)}</a>'
                     if entity_url(j_) else esc(jname))
            span_ = fmt_range(h.get("from"), h.get("to"), "present")
            jh += (f"<li>{jlink} — {esc(span_)}"
                   + (f" <span class=note>{esc(h['note'])}</span>"
                      if h.get("note") else "") + "</li>")
        hist = ""
        for h in inst.get("history") or []:
            hist += (f"<li><strong>{esc(h.get('event'))}</strong> "
                     f"{esc(fmt_date(h.get('date')))}"
                     + (f" — {esc(h['note'])}" if h.get("note") else "")
                     + "</li>")
        founded_ = inst.get("founded") or {}
        people_rows = "".join(
            f"<li>{person_entry(a_.get('person'))} — "
            f"<strong>{esc(a_.get('role'))}</strong>"
            + (f" <span class=note>{esc(a_.get('notes', ''))}</span>"
               if a_.get("notes") else "") + "</li>"
            for a_ in assoc_by_inst.get(iid, []))
        osite = inst.get("official_site") or {}
        olinks = []
        if osite.get("url"):
            olinks.append(f'<a href="{esc(osite["url"])}" rel="nofollow">official site</a>')
        if osite.get("archived_url"):
            olinks.append(f'<a href="{esc(osite["archived_url"])}" rel="nofollow">archived</a>')
        content = f"""<h1>{esc(inst.get("name"))} {badge(inst.get("status"))}</h1>
<p class="subtitle">{esc(iid)} · {esc(inst.get("type"))} ·
current status: <strong>{esc(inst.get("current_status", "?"))}</strong>
{" · " + " · ".join(olinks) if olinks else ""}</p>
<div class="panel"><h2>Lifecycle</h2>
{f'<p>Founded {esc(fmt_date(founded_.get("date")))}' + (f' — {esc(founded_.get("note"))}' if founded_.get('note') else '') + '</p>' if founded_ else ''}
{f'<ul>{hist}</ul>' if hist else '<p class=note>No suppression/refoundation events recorded.</p>'}
</div>
<div class="panel"><h2>Jurisdiction history</h2><ul>{jh or '<li class=note>to be refined at verification</li>'}</ul></div>
{f'<div class="panel"><h2>Formation (persons)</h2><ul>{people_rows}</ul><p class=note>In-scope persons only — institutions never grow abbot lists or faculty rosters (I3/I6).</p></div>' if people_rows else ''}
{f'<div class="panel"><h2>Notable heads</h2><p>{esc(inst.get("notable_heads"))}</p></div>' if inst.get('notable_heads') else ''}
<div class="panel"><h2>Record</h2>{citations_html(inst.get('sources'), sources_by_id)}
{f'<p class=note>{esc(inst.get("notes"))}</p>' if inst.get('notes') else ''}</div>"""
        write(OUT / "institutions" / slug_ / "index.html",
              layout(inst.get("name", iid), content, canonical,
                     active="Institutions", entity_id=iid))

    inst_types = sorted({i.get("type") for i in institutions.values()})
    inst_stats = sorted({i.get("current_status", "") for i in institutions.values() if i.get("current_status")})
    inst_jurs = sorted({(h.get("jurisdiction") or "").split("/")[-1]
                        for i in institutions.values()
                        for h in i.get("jurisdiction_history") or []
                        if h.get("jurisdiction")})

    def isel(fid, label, options):
        opts = "".join(f'<option value="{esc(o)}">{esc(o)}</option>'
                       for o in options)
        return (f'<label>{label} <select id="{fid}" class="saints-filter">'
                f'<option value="">all</option>{opts}</select></label> ')

    inst_rows = ""
    for iid, inst in sorted(institutions.items(),
                            key=lambda kv: kv[1].get("name", "")):
        jur0 = ""
        for h in inst.get("jurisdiction_history") or []:
            if h.get("jurisdiction"):
                jur0 = h["jurisdiction"].split("/")[-1]
                break
        fy = date_year((inst.get("founded") or {}).get("date"))
        inst_rows += (
            f'<tr data-jurisdiction="{esc(jur0)}"'
            f' data-type="{esc(inst.get("type", ""))}"'
            f' data-status="{esc(inst.get("current_status", ""))}">'
            f"<td>{ilink(iid)}</td><td>{esc(inst.get('type'))}</td>"
            f"<td>{esc(jur0)}</td>"
            f"<td>{fy if fy else '—'}</td>"
            f"<td>{esc(inst.get('current_status', ''))}</td>"
            f"<td>{badge(inst.get('status'))}</td></tr>")
    write(OUT / "institutions" / "index.html",
          layout("Institutions",
                 f"<h1>Institutions ({len(institutions)})</h1>"
                 f"<p class=note>The seedbeds of the episcopate — monasteries "
                 f"and schools where the people of the succession graphs were "
                 f"formed. Tier-gated: this is deliberately NOT a complete "
                 f"catalog and never will be (I2/I6); institutions also "
                 f"render on the <a href='/map/'>map</a> as triangles.</p>"
                 f"<div class=panel><p class='lib-filters'>"
                 + isel("s-type", "Type", inst_types)
                 + isel("s-jurisdiction", "Jurisdiction", inst_jurs)
                 + isel("s-status", "Current status", inst_stats)
                 + "<span id='saints-count' class=note></span></p>"
                 f"<table><thead><tr><th>Name</th><th>Type</th>"
                 f"<th>Jurisdiction</th><th>Founded</th><th>Current status</th>"
                 f"<th>Record</th></tr></thead>"
                 f"<tbody id='saints-body'>{inst_rows}</tbody></table></div>"
                 f"<script src='/assets/saints.js'></script>",
                 "https://tonyleroyrobin.github.io/orthodox-succession/institutions/",
                 active="Institutions"))

    # institutions map layer data
    inst_map = []
    for iid, inst in institutions.items():
        loc = inst.get("location") or {}
        if loc.get("lat") is None:
            continue
        events_ = []
        fy = date_year((inst.get("founded") or {}).get("date"))
        if fy:
            events_.append({"e": "founded", "y": fy})
        for h in inst.get("history") or []:
            hy = date_year(h.get("date"))
            if hy:
                events_.append({"e": h.get("event"), "y": hy})
        inst_map.append({"id": iid, "name": inst.get("name"),
                         "type": inst.get("type"),
                         "lat": loc["lat"], "lon": loc["lon"],
                         "url": BASE + "/institutions/" + iid.split("/", 1)[1] + "/",
                         "cs": inst.get("current_status"),
                         "st": inst.get("status"),
                         "ev": sorted(events_, key=lambda x: x["y"])})
    write(OUT / "data" / "institutions-map.json",
          json.dumps(inst_map, ensure_ascii=False), sitemap=False)


    # ---------------- saints index (Q6.1) ----------------
    # Derived entirely from existing veneration data - no new data class;
    # the admission rule still governs who can ever appear.
    saint_rows = ""
    n_saints = 0
    for pid, p in sorted(persons.items(), key=lambda kv: person_name(kv[1])):
        ven = p.get("veneration") or {}
        if ven.get("status") != "saint":
            continue
        n_saints += 1
        jur = pid.split("/")[1]
        dy = date_year((p.get("died") or {}).get("date"))
        if dy is None:
            ys = [date_year(t.get("from"))
                  for t in tenures_by_person.get(pid, [])]
            ys = [y for y in ys if y is not None]
            dy = ys[0] if ys else None
        cent = str((dy - 1) // 100 + 1) if dy else ""
        feasts = ven.get("feast_days") or []
        first_md = feasts[0].get("month_day", "") if feasts else ""
        feast_html = " · ".join(
            esc(f.get("month_day", "")) +
            (f" ({esc(f.get('calendar', ''))})" if f.get("calendar") else "")
            for f in feasts) or "—"
        titles = ", ".join(ven.get("titles") or [])
        saint_rows += (
            f'<tr data-jurisdiction="{esc(jur)}" data-century="{esc(cent)}"'
            f' data-feast="{esc(first_md)}">'
            f'<td>{person_entry(pid)}</td>'
            f'<td>{esc(jur)}</td>'
            f'<td>{esc(cent + (ord_suffix(int(cent)) + " c." if cent else ""))}</td>'
            f'<td>{feast_html}</td>'
            f'<td>{esc(titles)}</td></tr>')
    saint_jurs = sorted({pid.split("/")[1] for pid, p in persons.items()
                         if (p.get("veneration") or {}).get("status") == "saint"})
    saint_cents = sorted({str((date_year((p.get("died") or {}).get("date")) - 1) // 100 + 1)
                          for p in persons.values()
                          if (p.get("veneration") or {}).get("status") == "saint"
                          and date_year((p.get("died") or {}).get("date"))},
                         key=int)
    def _sel(fid, label, options):
        opts = "".join(f'<option value="{esc(o)}">{esc(o)}</option>'
                       for o in options)
        return (f'<label>{label} <select id="{fid}" class="saints-filter">'
                f'<option value="">all</option>{opts}</select></label> ')
    write(OUT / "saints" / "index.html",
          layout("Saints",
                 f"<h1>Saints ({n_saints})</h1>"
                 f"<p class=note>Every person whose veneration block records "
                 f"saint status - derived entirely from existing data (the "
                 f"admission rule governs who can appear; there is no mass "
                 f"hagiographic import). Feast dates carry their stated "
                 f"calendar; see the home page for today's commemorations.</p>"
                 f"<div class=panel><p class='lib-filters'>"
                 + _sel("s-jurisdiction", "Jurisdiction", saint_jurs)
                 + _sel("s-century", "Century", saint_cents)
                 + "<button id='s-sortfeast'>sort by feast day</button>"
                 + "<span id='saints-count' class=note></span></p>"
                 f"<table><thead><tr><th>Saint</th><th>Jurisdiction</th>"
                 f"<th>Century</th><th>Feast day(s)</th><th>Titles</th></tr>"
                 f"</thead><tbody id='saints-body'>{saint_rows}</tbody>"
                 f"</table></div>"
                 f"<script src='/assets/saints.js'></script>",
                 "https://tonyleroyrobin.github.io/orthodox-succession/saints/",
                 active="Saints"))

    # ---------------- per-jurisdiction chunks ----------------
    chunk_index = defaultdict(lambda: defaultdict(int))
    chunks = defaultdict(lambda: defaultdict(list))
    for kind in ("person", "see", "tenure", "consecration"):
        for r in by_kind[kind]:
            rid = r["data"].get("id", "")
            parts = rid.split("/")
            jur = parts[1] if len(parts) > 2 else "global"
            chunks[jur][kind].append(r["data"])
            chunk_index[jur][kind] += 1
    for jur, kinds in chunks.items():
        for kind, items in kinds.items():
            write(OUT / "data" / "chunks" / jur / f"{kind}.json",
                  json.dumps(items, ensure_ascii=False))
    write(OUT / "data" / "chunks" / "index.json",
          json.dumps({j: dict(k) for j, k in chunk_index.items()}, indent=1))

    # ---------------- state of the database (Q8.1) ----------------
    jur_stats = defaultdict(lambda: defaultdict(int))
    for r in records:
        rid = r["data"].get("id", "")
        parts_ = rid.split("/")
        if r["kind"] in ("person", "see", "tenure", "consecration") \
                and len(parts_) > 2:
            jur = parts_[1]
            st = r["data"].get("status", "unverified")
            jur_stats[jur]["total"] += 1
            jur_stats[jur][st] += 1
    state_rows = ""
    for jur in sorted(jur_stats):
        s_ = jur_stats[jur]
        tot = s_["total"]
        ver = s_.get("verified", 0)
        pct = round(100 * ver / tot) if tot else 0
        state_rows += (f"<tr><td>{esc(jur)}</td><td>{tot}</td>"
                       f"<td>{ver} ({pct}%)</td>"
                       f"<td>{s_.get('unverified', 0)}</td>"
                       f"<td>{s_.get('disputed', 0)}</td></tr>")
    kind_counts = defaultdict(int)
    for r in records:
        kind_counts[r["kind"]] += 1
    kind_html = " · ".join(f"{k}: {n}" for k, n in sorted(kind_counts.items()))
    open_leads = 0
    leads_path = REPO_ROOT / "docs" / "COUNCIL_LEADS.md"
    if leads_path.exists():
        for line in leads_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("|") and line.count("|") >= 5 \
                    and not line.startswith("|---") and "Lead |" not in line:
                if line.rstrip().endswith("| |") or line.rstrip().endswith("|  |"):
                    open_leads += 1
    write(OUT / "state" / "index.html",
          layout("State of the database",
                 f"<h1>State of the database</h1>"
                 f"<p class=note>Honest and current on every build "
                 f"(dataset {esc(VERSION)}). <em>Verified</em> means a human "
                 f"confirmed the claim against a graded source; most records "
                 f"are unverified by design until the verification pass "
                 f"reaches them.</p>"
                 f"<div class=panel><h2>Records</h2><p>{kind_html}</p></div>"
                 f"<div class=panel><h2>Verification progress by "
                 f"jurisdiction</h2><table><thead><tr><th>Jurisdiction</th>"
                 f"<th>Records</th><th>Verified</th><th>Unverified</th>"
                 f"<th>Disputed</th></tr></thead>"
                 f"<tbody>{state_rows}</tbody></table>"
                 f"<p class=note>Person/see/tenure/consecration records only "
                 f"(jurisdiction-filed kinds).</p></div>"
                 f"<div class=panel><h2>Known gaps</h2><p>"
                 f"<a href='/gaps/'>Occupancy-gap report and link health</a> "
                 f"· {open_leads} open council lead(s) in the capture log "
                 f"(docs/COUNCIL_LEADS.md).</p></div>",
                 "https://tonyleroyrobin.github.io/orthodox-succession/state/"))

    # ---------------- for researchers (Q8.2) ----------------
    schema_list = "".join(
        f"<li><code>{esc(f.name)}</code></li>"
        for f in sorted((REPO_ROOT / 'schemas').glob('*.json')))
    write(OUT / "research" / "index.html",
          layout("For researchers",
                 f"""<h1>For researchers</h1>
<div class=panel><h2>Downloads</h2>
<ul>
<li><strong>Per release</strong> (versioned, citable):
<a href="https://github.com/TonyLeroyRobin/orthodox-succession/releases" rel="nofollow">
GitHub releases</a> carry the YAML source; the archived deposit is on Zenodo
(DOI <code>10.5281/zenodo.21384060</code>).</li>
<li><strong>This build's JSON</strong>: per-jurisdiction chunks under
<a href="/data/chunks/index.json">/data/chunks/</a> (person, see, tenure,
consecration), plus <a href="/data/map-data.json">map-data</a>,
<a href="/data/search-index.json">search-index</a>, and
<a href="/data/calendar-data.json">calendar-data</a>.</li>
<li><strong>SQLite and GraphML</strong>: built by <code>make build</code>
from the repository (<code>build/succession.sqlite</code>,
<code>build/graph.graphml</code>) — clone and build, or take them from a
release's assets.</li>
</ul></div>
<div class=panel><h2>Schema overview</h2>
<p>YAML records under <code>data/</code>, one entity per file, validated by
JSON Schema (draft 2020-12):</p><ul>{schema_list}</ul>
<p class=note>Two succession models, never conflated: see-succession
(Tenure order) and consecration-succession (the consecration DAG). Absent
consecration data is stated, not inferred.</p></div>
<div class=panel><h2>How to cite</h2>
<p><code>Orthodox Apostolic Succession Database, {esc(VERSION)},
doi:10.5281/zenodo.21384060</code> — or cite a page by its canonical URL
(every footer shows it).</p></div>""",
                 "https://tonyleroyrobin.github.io/orthodox-succession/research/"))

    # ---------------- alias redirect stubs (Q2.1 infrastructure) -----------
    # data/aliases.yaml maps retired IDs (Q1 merges, future Q2 migrations) to
    # canonical IDs; each old URL gets a redirect stub so no published link
    # ever dies.
    alias_file = REPO_ROOT / "data" / "aliases.yaml"
    if alias_file.exists():
        import yaml as _yaml
        alias_map = _yaml.safe_load(
            alias_file.read_text(encoding="utf-8")).get("aliases", {})
        stubs = 0
        for old_id, new_id in alias_map.items():
            old_url, new_url = entity_url(old_id), entity_url(new_id)
            if not (old_url and new_url):
                continue
            target = OUT / old_url.strip("/") / "index.html"
            if target.exists():
                print(f"build_site: alias target collides with a live page: "
                      f"{old_id}", file=sys.stderr)
                continue
            write(target,
                  f'<!DOCTYPE html><meta charset="utf-8">'
                  f'<meta http-equiv="refresh" content="0; url={new_url}">'
                  f'<link rel="canonical" href="https://tonyleroyrobin.github.io/orthodox-succession{new_url}">'
                  f'<a href="{new_url}">This record has been merged — '
                  f'continue to the canonical page.</a>', sitemap=False)
            stubs += 1
        print(f"build_site: {stubs} alias redirect stub(s)")

    # ---------------- assets ----------------
    assets = OUT / "assets"
    assets.mkdir(exist_ok=True)
    shutil.copy(SITE_SRC / "style.css", assets / "style.css")
    (assets / "vendor").mkdir(exist_ok=True)
    for f in (SITE_SRC / "vendor").iterdir():
        shutil.copy(f, assets / "vendor" / f.name)
    for name in ("site.js", "search.js", "map.js", "timeline.js",
                 "library.js", "saints.js", "ideas.js", "graph.js",
                 "people.js"):
        src = SITE_SRC / "static" / name
        if src.exists():
            js = src.read_text(encoding="utf-8")
            if BASE:
                js = js.replace('fetch("/', f'fetch("{BASE}/')
            (assets / name).write_text(js, encoding="utf-8")

    # ---------------- consecration graph v2 (F2) ----------------
    cons_nodes = {}
    cons_links = []

    def _gnode(pid_):
        if pid_ and pid_ not in cons_nodes:
            p_ = persons.get(pid_)
            cons_nodes[pid_] = {
                "id": pid_,
                "label": person_name(p_) if p_ else pid_,
                "url": BASE + (entity_url(pid_) or ""),
                "jur": pid_.split("/")[1] if len(pid_.split("/")) > 2 else "?",
                "status": (p_ or {}).get("status", "unverified"),
                "year": None}
        return pid_

    for c_ in consecrations:
        tgt = c_.get("consecrated")
        y_ = date_year(c_.get("date"))
        _gnode(tgt)
        if tgt and y_ and not cons_nodes[tgt]["year"]:
            cons_nodes[tgt]["year"] = y_
        srcs_ = []
        if c_.get("principal_consecrator"):
            srcs_.append((c_["principal_consecrator"], True))
        for k_ in c_.get("co_consecrators") or []:
            srcs_.append((k_, False))
        for pid_, principal_ in srcs_:
            _gnode(pid_)
            if tgt:
                cons_links.append({"source": pid_, "target": tgt,
                                   "principal": principal_, "year": y_})
    # consecrators without their own consecration date: earliest outgoing year
    for l_ in cons_links:
        n_ = cons_nodes[l_["source"]]
        if l_["year"] and (n_["year"] is None or l_["year"] - 1 < n_["year"]):
            if n_["year"] is None:
                n_["year"] = l_["year"] - 1
    years_ = sorted({n_["year"] for n_ in cons_nodes.values()
                     if n_["year"] is not None})
    if years_:
        y0, y1 = years_[0], years_[-1]
        band = max(10, (y1 - y0) // 12 or 10)
        layer_labels = []
        cur = y0
        while cur <= y1:
            layer_labels.append(f"{cur}–{min(cur + band - 1, y1)}")
            cur += band
        for n_ in cons_nodes.values():
            n_["layer"] = (min((n_["year"] or y0) - y0, y1 - y0) // band)
    else:
        layer_labels = ["undated"]
        for n_ in cons_nodes.values():
            n_["layer"] = 0
    write(OUT / "data" / "graph-v2.json",
          json.dumps({"nodes": list(cons_nodes.values()),
                      "links": cons_links,
                      "layers": layer_labels}, ensure_ascii=False),
          sitemap=False)

    # static fallback: counts, largest lineage components, per-jur tables
    parent_ = {}

    def _find(x):
        while parent_.get(x, x) != x:
            parent_[x] = parent_.get(parent_[x], parent_[x])
            x = parent_[x]
        return x

    def _union(a, b):
        parent_.setdefault(a, a)
        parent_.setdefault(b, b)
        ra, rb = _find(a), _find(b)
        if ra != rb:
            parent_[ra] = rb

    for l_ in cons_links:
        _union(l_["source"], l_["target"])
    comp_sizes = defaultdict(int)
    for n_ in cons_nodes:
        comp_sizes[_find(n_)] += 1
    largest = sorted(comp_sizes.items(), key=lambda kv: -kv[1])[:3]
    comp_html = " · ".join(
        f"{cons_nodes[root_]['label']}-component: {size_} persons"
        for root_, size_ in largest) or "none"

    cons_by_jur = defaultdict(list)
    for c_ in consecrations:
        tgt = c_.get("consecrated") or ""
        jur_ = tgt.split("/")[1] if len(tgt.split("/")) > 2 else "?"
        cons_by_jur[jur_].append(c_)
    cons_tables = ""
    for jur_ in sorted(cons_by_jur):
        rows_ = ""
        for c_ in sorted(cons_by_jur[jur_],
                         key=lambda c: date_year(c.get("date")) or 0):
            cos_ = ", ".join(plink(k_) for k_ in c_.get("co_consecrators") or [])
            rows_ += (f"<tr><td>{plink(c_.get('consecrated'))}</td>"
                      f"<td>{esc(fmt_date(c_.get('date')))}</td>"
                      f"<td>{plink(c_.get('principal_consecrator')) if c_.get('principal_consecrator') else '—'}</td>"
                      f"<td>{cos_ or '—'}</td></tr>")
        cons_tables += (f"<details open><summary>{esc(jur_)} "
                        f"({len(cons_by_jur[jur_])})</summary>"
                        f"<table><thead><tr><th>Consecrated</th><th>Date</th>"
                        f"<th>Principal</th><th>Co-consecrators</th></tr>"
                        f"</thead><tbody>{rows_}</tbody></table></details>")
    graph_page = f"""<h1>Consecration graph</h1>
<p class="subtitle">The succession of hands: consecration date flows top to
bottom; node color = jurisdiction, ring color = verification status; solid
edges = principal consecrator, dashed = co-consecrators. Click a node to
TRACE its full lineage (ancestry and descendants); double-click opens the
person page. Share a trace with ?trace=&lt;person-id&gt;.</p>
<div class="panel">
<p class="map-controls"><label for="graphJump">Find: </label>
<input id="graphJump" list="graphNodes" placeholder="type a name…">
<datalist id="graphNodes"></datalist></p>
<div id="traceCrumb" class="note"></div>
<div id="graph"></div>
<p id="graphLegend" class="note"></p>
<p class="note">Absent consecration data is stated, not inferred — the graph
renders only recorded consecrations ({len(consecrations)} records,
{len(cons_nodes)} persons). Largest lineage components: {comp_html}.</p>
</div>
<div class="panel"><h2>All consecration records</h2>
<p class=note>Build-time HTML — complete without JavaScript.</p>
{cons_tables}</div>
<script src="/assets/vendor/d3.v7.min.js"></script>
<script src="/assets/graph.js"></script>"""
    write(OUT / "graph" / "index.html",
          layout("Consecration graph", graph_page,
                 "https://tonyleroyrobin.github.io/orthodox-succession/graph/",
                 active="Graph"))


    # ---------------- legacy pages (query-URL fallbacks) ----------------
    # F3.1: the pre-R1 dashboard is retired - nothing is copied; every old
    # /site/* URL is a redirect stub or a query-URL redirector.
    legacy = OUT / "site"
    legacy.mkdir(exist_ok=True)
    write(legacy / "graph.html", """<!DOCTYPE html><meta charset="utf-8">
<meta http-equiv="refresh" content="0; url=/graph/">
<link rel="canonical" href="https://tonyleroyrobin.github.io/orthodox-succession/graph/">
<a href="/graph/">The consecration graph has moved.</a>""", sitemap=False)
    write(legacy / "index.html", """<!DOCTYPE html><meta charset="utf-8">
<meta http-equiv="refresh" content="0; url=/">
<a href="/">The dashboard has moved to the site root.</a>""", sitemap=False)
    # redirectors
    write(legacy / "person.html", """<!DOCTYPE html><meta charset="utf-8">
<title>Redirecting…</title>
<script>
var id = new URLSearchParams(location.search).get("id");
location.replace(id ? "/people/" + id.split("/").slice(1).join("/") + "/" : "/people/");
</script>
<noscript><p>This page has moved. Find the person via
<a href="/people/">the people index</a>.</p></noscript>""")
    write(legacy / "index.html", """<!DOCTYPE html><meta charset="utf-8">
<meta http-equiv="refresh" content="0; url=/">
<a href="/">Orthodox Apostolic Succession Database</a>""")
    write(legacy / "map.html", """<!DOCTYPE html><meta charset="utf-8">
<meta http-equiv="refresh" content="0; url=/map/">
<a href="/map/">The map has moved.</a>""")

    # Q2.3: sitemap.xml + robots.txt
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in sorted(set(SITEMAP_URLS)):
        sm.append(f"<url><loc>{esc(u)}</loc></url>")
    sm.append("</urlset>")
    (OUT / "sitemap.xml").write_text("\n".join(sm), encoding="utf-8")
    (OUT / "robots.txt").write_text(
        "User-agent: *\nAllow: /\nSitemap: https://tonyleroyrobin.github.io"
        "/orthodox-succession/sitemap.xml\n", encoding="utf-8")

    # ---------------- F3.2: internal-link gate (error level) ---------------
    href_re = re.compile(r"""(?:href|src)=["']([^"'#]+)""")
    existing = set()
    for f_ in OUT.rglob("*"):
        if f_.is_file():
            existing.add(f_.relative_to(OUT).as_posix())
    link_errors = []
    checked_cache = {}
    for page in OUT.rglob("*.html"):
        html_text = page.read_text(encoding="utf-8")
        page_dir = page.parent.relative_to(OUT).as_posix()
        for target in set(href_re.findall(html_text)):
            if target.startswith(("http://", "https://", "mailto:",
                                  "data:", "//")):
                continue
            key = (page_dir, target)
            if key in checked_cache:
                ok = checked_cache[key]
            else:
                path_part = target.split("?")[0]
                if BASE and path_part.startswith(BASE + "/"):
                    path_part = path_part[len(BASE):]
                if path_part.startswith("/"):
                    rel = path_part.lstrip("/")
                else:
                    base_dir = page_dir if page_dir != "." else ""
                    parts = (base_dir.split("/") if base_dir else []) +                         path_part.split("/")
                    stack = []
                    for seg in parts:
                        if seg in ("", "."):
                            continue
                        if seg == "..":
                            if stack:
                                stack.pop()
                        else:
                            stack.append(seg)
                    rel = "/".join(stack)
                rel = rel.rstrip("/")
                ok = (rel in existing or f"{rel}/index.html" in existing
                      or (rel == "" and "index.html" in existing))
                checked_cache[key] = ok
            if not ok:
                link_errors.append(f"{page.relative_to(OUT)}: {target}")
    if link_errors:
        for e_ in sorted(set(link_errors))[:40]:
            print(f"build_site: BROKEN INTERNAL LINK {e_}", file=sys.stderr)
        print(f"build_site: {len(set(link_errors))} broken internal link(s) "
              f"- 404s are unshippable (F3.2)", file=sys.stderr)
        return 1

    pages = sum(1 for _ in OUT.rglob("index.html"))
    print(f"build_site: {pages} pages -> {OUT} (dataset {VERSION})"
          f" · sitemap: {len(set(SITEMAP_URLS))} URLs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
