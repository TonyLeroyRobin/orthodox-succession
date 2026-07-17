/* People index (F4): role/jurisdiction/century/status filters + saints
   toggle, live count, combined with the A-Z rail (letters with no visible
   entries hide their headers). */
(function () {
  var filters = document.querySelectorAll(".ppl-filter");
  var saint = document.getElementById("p-saint");
  var count = document.getElementById("ppl-count");
  var items = Array.prototype.slice.call(
    document.querySelectorAll("ul.person-list > li"));
  if (!items.length) return;
  function apply() {
    var crit = {};
    filters.forEach(function (f) {
      if (f.value) crit[f.id.slice(2)] = f.value;
    });
    var wantSaint = saint && saint.checked;
    var shown = 0;
    items.forEach(function (li) {
      var ok = true;
      for (var k in crit) {
        if ((li.dataset[k] || "") !== crit[k]) { ok = false; break; }
      }
      if (ok && wantSaint && li.dataset.saint !== "1") ok = false;
      li.style.display = ok ? "" : "none";
      if (ok) shown++;
    });
    document.querySelectorAll("ul.person-list").forEach(function (ul) {
      var any = ul.querySelector("li:not([style*='none'])");
      var h = ul.previousElementSibling;
      ul.style.display = any ? "" : "none";
      if (h && h.tagName === "H2") h.style.display = any ? "" : "none";
    });
    if (count) count.textContent = shown + " of " + items.length + " shown";
  }
  filters.forEach(function (f) { f.addEventListener("change", apply); });
  if (saint) saint.addEventListener("change", apply);
  apply();
})();
