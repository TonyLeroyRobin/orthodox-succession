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
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import REPO_ROOT, date_year, load_all  # noqa: E402

OUT = REPO_ROOT / "build" / "site"
SITE_SRC = REPO_ROOT / "site"
STATUS_LABEL = {"verified": "verified", "unverified": "unverified",
                "disputed": "disputed"}
STATUS_COLOR = {"verified": "#2e7d32", "unverified": "#b26a00",
                "disputed": "#b3261e"}

NAV = [("Home", "/"), ("Jurisdictions", "/jurisdictions/"),
       ("Sees", "/sees/"), ("People", "/people/"),
       ("Councils", "/councils/"), ("Library", "/library/"),
       ("Map", "/map/"), ("Graph", "/site/graph.html"),
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
        return "/library/#" + rid.split("/", 1)[1]
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
        note = (f' <span class="note">— {esc(c["note"])}</span>'
                if c.get("note") else "")
        out.append(f'<div class="citation"><span class="badge grade">'
                   f'{esc(c.get("reliability", "?"))}</span> {esc(title)}'
                   f'{loc}{link}{alink}{note}</div>')
    return "".join(out)


def layout(title, content, canonical, jsonld=None, active=""):
    nav = "".join(
        f'<a href="{href}"{" class=active" if label == active else ""}>'
        f'{label}</a>' for label, href in NAV)
    ld = (f'<script type="application/ld+json">{json.dumps(jsonld, indent=1)}'
          f'</script>' if jsonld else "")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} — Orthodox Apostolic Succession</title>
<link rel="canonical" href="{esc(canonical)}">
<link rel="stylesheet" href="/assets/style.css">
{ld}</head>
<body>
<header class="site-header">
<nav>{nav}</nav>
<form class="searchbox" action="/search/" method="get">
<input type="search" name="q" placeholder="Search people, sees, councils, works…" aria-label="Search">
</form>
</header>
<main>
{content}
</main>
<footer>Data: CC BY 4.0 · Code: MIT · Recognition disputes are recorded, not
adjudicated; <em>unverified</em> means no human has yet confirmed the claim
against a graded source.<br>
Cite this page: <code>{esc(canonical)}</code> — Orthodox Apostolic Succession
Database {esc(VERSION)}.</footer>
<script src="/assets/site.js" defer></script>
</body>
</html>"""


def write(path, text):
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
                groups[relname].append(w)
            GROUP_LABEL = {"by": "By this person",
                           "about": "About this person",
                           "involving": "Involving this person"}
            sections = ""
            for relname in ("by", "about", "involving"):
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
            works_html = f"<div class=panel><h2>Works</h2>{sections}</div>"

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
              layout(person_name(p), content, canonical, jsonld, "People"))

    # people index
    letters = defaultdict(list)
    for pid, p in sorted(persons.items(), key=lambda kv: person_name(kv[1])):
        letters[person_name(p)[:1].upper()].append(
            f'<a href="{entity_url(pid)}">{esc(person_name(p))}</a>')
    people_idx = "".join(
        f"<h2>{esc(k)}</h2><p>{' · '.join(v)}</p>"
        for k, v in sorted(letters.items()))
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
        content = f"""<h1>{esc(j.get('name'))} {badge(j.get('status'))}</h1>
<p class="subtitle">{esc(jid)} · type: <strong>{esc(j.get('type'))}</strong></p>
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
        jsonld = {"@context": "https://schema.org", "@type": "Event",
                  "name": ev.get("title"), "identifier": rid}
        content = f"""<h1>{esc(ev.get('title'))} {badge(ev.get('status'))}</h1>
<p class="subtitle">{esc(rid)} · {esc(ev.get('type'))} ·
{esc(fmt_range(d.get('from'), d.get('to'), 'single session'))}
{f" · {esc(ev.get('place'))}" if ev.get('place') else ''}</p>
{recp_html}{recog_html}
{f'<div class="panel"><h2>Outcomes</h2><ul>{outcomes}</ul></div>' if outcomes else ''}
<div class="panel"><h2>Participants</h2>{ptable}</div>
{rw_html}
<div class="panel"><h2>Record</h2>{citations_html(ev.get('sources'), sources_by_id)}
{f'<p class=note>{esc(ev.get("notes"))}</p>' if ev.get('notes') else ''}</div>"""
        write(OUT / url.strip("/") / "index.html",
              layout(ev.get("title", rid), content, canonical, jsonld,
                     "Councils"))

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
                + (f" · {cent}th c." if cent else "") + "</span></li>")

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

    # ---------------- library ----------------
    lib_rows = "".join(
        f'<tr id="{esc(w["id"].split("/", 1)[1])}">'
        f'<td>{esc(w.get("title"))}</td>'
        f'<td>{plink(w["author"]) if w.get("author") else esc(w.get("author_display", "—"))}</td>'
        f'<td>{esc(w.get("genre"))}</td>'
        f'<td>{esc(w.get("attribution"))}</td>'
        f'<td>{esc(w.get("survival", "not assessed"))}</td>'
        f'<td>{esc(fmt_date(w.get("date")))}</td>'
        f'<td>{badge(w.get("status"))}</td></tr>'
        for w in sorted(works, key=lambda w: w.get("title", "")))
    write(OUT / "library" / "index.html",
          layout("Library",
                 f"<h1>Library ({len(works)} works)</h1>"
                 f"<p class=note>One Work, many Editions. Per-work pages, "
                 f"survival status, and filters arrive with P4/P6; editions "
                 f"and read-links live on the author pages meanwhile.</p>"
                 f"<div class=panel><table><thead><tr><th>Title</th>"
                 f"<th>Author</th><th>Genre</th><th>Attribution</th>"
                 f"<th>Survival</th><th>Date</th><th>Status</th></tr></thead>"
                 f"<tbody>{lib_rows}</tbody></table></div>",
                 "https://tonyleroyrobin.github.io/orthodox-succession/library/",
                 active="Library"))

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
    write(OUT / "gaps" / "index.html",
          layout("Gap report",
                 "<h1>Occupancy gaps (&gt; 2 years)</h1>"
                 "<p class=note>Gaps are information, not defects: most are "
                 "documented suppressions, vacancies, or attestation "
                 "sparsity — each see record's notes explain its own. "
                 "Generated from the same data as scripts/gap_report.py.</p>"
                 f"<div class=panel><table><thead><tr><th>See</th>"
                 f"<th>Gaps</th></tr></thead><tbody>{gap_rows}</tbody>"
                 f"</table></div>",
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
<li><a href="/site/graph.html">The consecration graph</a> (interactive).</li>
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
        docs.append({"id": pid, "type": "person", "name": person_name(p),
                     "variants": " ".join([*(n.get("variants") or []),
                                           *(x.get("value") for x in
                                             n.get("native") or [])]),
                     "url": entity_url(pid)})
    for sid, s in sees.items():
        docs.append({"id": sid, "type": "see", "name": s.get("name", sid),
                     "variants": (s.get("location") or {}).get("modern_place", ""),
                     "url": entity_url(sid)})
    for ev in councils:
        docs.append({"id": ev["id"], "type": "council",
                     "name": ev.get("title", ev["id"]), "variants": "",
                     "url": entity_url(ev["id"])})
    for w in works:
        docs.append({"id": w["id"], "type": "work",
                     "name": w.get("title", w["id"]), "variants": "",
                     "url": entity_url(w["id"])})
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
        map_rows.append({"id": sid, "name": s.get("name"),
                         "lat": loc["lat"], "lon": loc["lon"],
                         "url": entity_url(sid), "sup": sup, "t": spans})
    write(OUT / "data" / "map-data.json",
          json.dumps(map_rows, ensure_ascii=False))
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
<div id="map"></div>
<p class="note map-legend"><strong>Legend:</strong>
<span style="color:#2e7d32">&#9679;</span> filled = tenure active that year
(green verified, amber unverified, red disputed; dashed ring = recognition
disputed) &middot; &#9675; hollow = attested, no recorded occupant &middot;
<span style="color:#9a9a9a">&#8855;</span> grayed/crossed = suppressed (date in
the tooltip) &middot; Pentarchy sees stay labeled at all zooms; other labels
appear as you zoom. Scroll or pinch to zoom, drag to pan.</p>
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

    # ---------------- calendar data ----------------
    cal = []
    for pid, p in persons.items():
        ven = p.get("veneration")
        if not ven or ven.get("status") != "saint":
            continue
        feasts = [f for f in ven.get("feast_days") or [] if f.get("month_day")]
        if feasts:
            cal.append({"id": pid, "name": person_name(p),
                        "url": entity_url(pid),
                        "titles": ven.get("titles") or [],
                        "feasts": [{"md": f["month_day"],
                                    "cal": f.get("calendar", "gregorian"),
                                    "note": f.get("note", "")}
                                   for f in feasts]})
    write(OUT / "data" / "calendar-data.json",
          json.dumps(cal, ensure_ascii=False))

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

    # ---------------- assets ----------------
    assets = OUT / "assets"
    assets.mkdir(exist_ok=True)
    shutil.copy(SITE_SRC / "style.css", assets / "style.css")
    (assets / "vendor").mkdir(exist_ok=True)
    for f in (SITE_SRC / "vendor").iterdir():
        shutil.copy(f, assets / "vendor" / f.name)
    for name in ("site.js", "search.js", "map.js"):
        src = SITE_SRC / "static" / name
        if src.exists():
            shutil.copy(src, assets / name)

    # ---------------- legacy pages (query-URL fallbacks) ----------------
    legacy = OUT / "site"
    legacy.mkdir(exist_ok=True)
    # graph keeps working as-is (with its data at the legacy relative path)
    shutil.copy(SITE_SRC / "graph.html", legacy / "graph.html")
    shutil.copy(SITE_SRC / "app.js", legacy / "app.js")
    shutil.copy(SITE_SRC / "style.css", legacy / "style.css")
    (legacy / "locales").mkdir(exist_ok=True)
    shutil.copy(SITE_SRC / "locales" / "en.json",
                legacy / "locales" / "en.json")
    (legacy / "vendor").mkdir(exist_ok=True)
    for f in (SITE_SRC / "vendor").iterdir():
        shutil.copy(f, legacy / "vendor" / f.name)
    site_data_out = OUT / "build" / "site-data"
    site_data_src = REPO_ROOT / "build" / "site-data"
    if site_data_src.exists():
        shutil.copytree(site_data_src, site_data_out, dirs_exist_ok=True)
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

    pages = sum(1 for _ in OUT.rglob("index.html"))
    print(f"build_site: {pages} pages -> {OUT} (dataset {VERSION})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
