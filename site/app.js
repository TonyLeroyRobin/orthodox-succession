/* Shared data loading + rendering helpers for the prototype dashboard.
   Reads the JSON exported by scripts/export_graph.py into build/site-data/.
   Serve the repo root over HTTP (python -m http.server) — file:// will not
   allow fetch. */

const DATA_BASE = "../build/site-data/";

async function loadData(names) {
  const out = {};
  await Promise.all(
    names.map(async (n) => {
      const resp = await fetch(DATA_BASE + n + ".json");
      if (!resp.ok) throw new Error(`failed to load ${n}.json (${resp.status})`);
      out[n] = await resp.json();
    })
  );
  return out;
}

function byId(list) {
  const m = new Map();
  for (const r of list) m.set(r.id, r);
  return m;
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

/* ---- dates ---------------------------------------------------------- */

function dateYearNum(d) {
  if (!d || !d.value) return null;
  const m = String(d.value).match(/^(-?)(\d{4})/);
  if (!m) return null;
  return (m[1] ? -1 : 1) * parseInt(m[2], 10);
}

function fmtDate(d) {
  if (!d || !d.value) return "—";
  let v = d.value.replace(/^0+(\d)/, "$1");
  let s;
  switch (d.precision) {
    case "circa": s = "c. " + v.split("-")[0]; break;
    case "decade": s = v.split("-")[0] + "s"; break;
    case "century": s = (Math.floor(parseInt(v, 10) / 100) + 1) + "th c. (approx.)"; break;
    case "disputed": s = v + " (disputed)"; break;
    case "year": s = v.split("-")[0]; break;
    default: s = v;
  }
  if (d.calendar === "julian") s += " (Julian)";
  if (d.calendar === "anno-mundi") s += " (from Anno Mundi)";
  return s;
}

function fmtRange(from, to, openLabel) {
  const a = fmtDate(from);
  const b = to ? fmtDate(to) : (openLabel || "end unrecorded");
  return `${a} → ${b}`;
}

/* ---- record display -------------------------------------------------- */

function statusBadge(status) {
  return `<span class="badge ${esc(status)}">${esc(status)}</span>`;
}

function personName(p) {
  if (!p) return "(unknown person)";
  const n = p.names || {};
  let s = n.monastic || p.id;
  if (n.family) s += ` (${n.family})`;
  return s;
}

function personLink(p) {
  if (!p) return "(unknown person)";
  return `<a href="person.html?id=${encodeURIComponent(p.id)}">${esc(personName(p))}</a>`;
}

function citationsHtml(cits, sourcesMap) {
  if (!cits || !cits.length) return '<div class="citation">no citations</div>';
  return cits
    .map((c) => {
      const src = sourcesMap.get(c.ref);
      const title = src ? src.title : c.ref;
      const link = src && src.url ? ` <a href="${esc(src.url)}">[link]</a>` : "";
      const arch = c.archived_url || (src && src.archived_url);
      const archLink = arch ? ` <a href="${esc(arch)}">[archived]</a>` : "";
      const loc = c.locator ? `, ${esc(c.locator)}` : "";
      return `<div class="citation"><span class="badge grade">${esc(c.reliability)}</span> ` +
             `${esc(title)}${loc}${link}${archLink}` +
             (c.note ? ` <span class="note">— ${esc(c.note)}</span>` : "") +
             `</div>`;
    })
    .join("");
}
