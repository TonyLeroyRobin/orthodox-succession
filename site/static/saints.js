/* Saints index (Q6.1): jurisdiction/century filters + sort-by-feast-day. */
(function () {
  var filters = document.querySelectorAll(".saints-filter");
  var body = document.getElementById("saints-body");
  var count = document.getElementById("saints-count");
  if (!body) return;
  var rows = Array.prototype.slice.call(body.querySelectorAll("tr"));
  function apply() {
    var crit = {};
    filters.forEach(function (f) {
      if (f.value) crit[f.id.slice(2)] = f.value;
    });
    var shown = 0;
    rows.forEach(function (r) {
      var ok = true;
      for (var k in crit) {
        if ((r.dataset[k] || "") !== crit[k]) { ok = false; break; }
      }
      r.style.display = ok ? "" : "none";
      if (ok) shown++;
    });
    if (count) count.textContent = shown + " shown";
  }
  filters.forEach(function (f) { f.addEventListener("change", apply); });
  var sorted = false;
  var btn = document.getElementById("s-sortfeast");
  if (btn) btn.addEventListener("click", function () {
    sorted = !sorted;
    var order = rows.slice().sort(function (a, b) {
      var fa = a.dataset.feast || "99-99", fb = b.dataset.feast || "99-99";
      return fa < fb ? -1 : fa > fb ? 1 : 0;
    });
    (sorted ? order : rows).forEach(function (r) { body.appendChild(r); });
    btn.textContent = sorted ? "sort by name" : "sort by feast day";
  });
  apply();
})();
