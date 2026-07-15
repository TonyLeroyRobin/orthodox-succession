/* Search page (R1.3): MiniSearch over the build-generated index, including
   name variants and native scripts. Runs entirely client-side. */
(function () {
  var input = document.getElementById("q");
  var results = document.getElementById("results");
  var mini = null;

  fetch("/data/search-index.json").then(function (r) { return r.json(); })
    .then(function (docs) {
      mini = new MiniSearch({
        fields: ["name", "variants", "id"],
        storeFields: ["name", "type", "url", "id"],
        searchOptions: { prefix: true, fuzzy: 0.2 },
      });
      mini.addAll(docs);
      var q = new URLSearchParams(location.search).get("q");
      if (q) { input.value = q; run(q); }
    });

  function run(q) {
    if (!mini || !q) return;
    var hits = mini.search(q).slice(0, 50);
    results.innerHTML = hits.length
      ? "<ul>" + hits.map(function (h) {
          return '<li><a href="' + h.url + '">' + h.name +
                 '</a> <span class="badge model">' + h.type +
                 '</span> <span class="note">' + h.id + "</span></li>";
        }).join("") + "</ul>"
      : '<p class="note">No matches.</p>';
  }

  input.addEventListener("input", function () { run(input.value); });
  document.getElementById("searchform").addEventListener("submit",
    function (e) { e.preventDefault(); run(input.value); });
})();
