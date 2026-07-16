/* Library index filters (P6): author / century / genre / language /
   survival, ANDed over the static table rows. */
(function () {
  var filters = document.querySelectorAll(".lib-filter");
  var rows = document.querySelectorAll("#lib-body tr");
  var count = document.getElementById("lib-count");
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
    if (count) count.textContent = shown + " of " + rows.length + " works";
  }
  filters.forEach(function (f) { f.addEventListener("change", apply); });
  apply();
})();
