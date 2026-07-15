/* Shared enhancement layer for the static site (R1). Content is baked into
   the HTML at build time; this file only enhances. */

/* ---- home: commemorated today (the one genuinely date-dependent element;
   feast data is baked into /data/calendar-data.json at build) ---- */
(function () {
  var el = document.getElementById("calendar");
  if (!el) return;
  fetch("/data/calendar-data.json").then(function (r) { return r.json(); })
    .then(function (cal) {
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
          if (civilMd === today) hits.push({ p: p, f: f });
        });
      });
      var h = "<p><strong>" + civil.toISOString().slice(0, 10) + "</strong> — " +
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
    }).catch(function () { /* static fallback text remains */ });
})();
