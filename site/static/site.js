/* Shared enhancement layer for the static site (R1). Content is baked into
   the HTML at build time; this file only enhances. */

/* ---- home: commemorated today (the one genuinely date-dependent element;
   feast data is baked into /data/calendar-data.json at build) ---- */
(function () {
  var el = document.getElementById("calendar");
  if (!el) return;
  fetch("/data/calendar-data.json").then(function (r) { return r.json(); })
    .then(function (cal) {
      var mode = "new";  // Q6.2: new-calendar vs old-calendar reckoning
      function render() { paint(cal, mode); }
      window.__calToggle = function (m) { mode = m; render(); };
      render();
    }).catch(function () { /* static fallback text remains */ });

  function paint(cal, mode) {
      var now = new Date();
      var civil = new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()));
      function mmdd(dt) {
        return String(dt.getUTCMonth() + 1).padStart(2, "0") + "-" +
               String(dt.getUTCDate()).padStart(2, "0");
      }
      var today = mmdd(civil);
      var hits = [];
      cal.forEach(function (p) {
        p.feasts.forEach(function (f) {
          var civilMd = f.md;
          if (f.cal === "julian") {
            var parts = f.md.split("-");
            var dt = new Date(Date.UTC(civil.getUTCFullYear(),
                                       parseInt(parts[0], 10) - 1,
                                       parseInt(parts[1], 10)));
            dt.setUTCDate(dt.getUTCDate() + 13);
            civilMd = mmdd(dt);
          }
          if (mode === "old") {
            // old-calendar reckoning: julian feasts match the Julian date
            // (civil minus 13 days); no shift applied to the feast itself
            var jd = new Date(civil); jd.setUTCDate(jd.getUTCDate() - 13);
            civilMd = (f.cal === "julian") ? f.md : civilMd;
            if (f.cal === "julian" ? (f.md === mmdd(jd)) : false) {
              hits.push({ p: p, f: f });
            }
            return;
          }
          if (civilMd === today) hits.push({ p: p, f: f });
        });
      });
      var jd2 = new Date(civil); jd2.setUTCDate(jd2.getUTCDate() - 13);
      var dateLabel = (mode === "old")
        ? civil.toISOString().slice(0, 10) + " (Julian: " + jd2.toISOString().slice(5, 10) + ")"
        : civil.toISOString().slice(0, 10);
      var toggle = '<p class="note">Reckoning: ' +
        '<button id="calNew"' + (mode === "new" ? " disabled" : "") + '>new calendar</button> ' +
        '<button id="calOld"' + (mode === "old" ? " disabled" : "") + '>old calendar (Julian)</button></p>';
      var h = toggle + "<p><strong>" + dateLabel + "</strong> — " +
              (hits.length ? hits.length + " commemoration(s)" :
               "no commemorations recorded for this date (the veneration " +
               "layer is populated opportunistically)") + "</p>";
      if (hits.length) {
        h += "<ul>" + hits.map(function (x) {
          var titles = x.p.titles.length ?
            ' <span class="note">' + x.p.titles.join(", ") + "</span>" : "";
          return '<li><a href="' + x.p.url + '">' + x.p.name + "</a>" +
                 titles + (x.f.note ? " — " + x.f.note : "") + "</li>";
        }).join("") + "</ul>";
      }
      el.innerHTML = h;
      var bn = document.getElementById("calNew");
      var bo = document.getElementById("calOld");
      if (bn) bn.addEventListener("click", function () { window.__calToggle("new"); });
      if (bo) bo.addEventListener("click", function () { window.__calToggle("old"); });
  }
})();
