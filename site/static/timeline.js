/* Timeline v2 (Milestone R3): jump-to-see typeahead and scope-filtering of
   the context layer (era bands / markers) to the expanded jurisdictions. */
(function () {
  function refreshBands() {
    var openJids = {};
    document.querySelectorAll("details.tl-jur[open]").forEach(function (d) {
      if (d.dataset.jid) openJids[d.dataset.jid] = 1;
    });
    document.querySelectorAll(".tl-band, .tl-mark").forEach(function (b) {
      var jid = b.dataset.jid || "";
      b.style.display = (!jid || openJids[jid]) ? "" : "none";
    });
  }
  document.querySelectorAll("details.tl-jur").forEach(function (d) {
    d.addEventListener("toggle", refreshBands);
  });
  refreshBands();

  var jump = document.getElementById("tlJump");
  if (!jump) return;
  jump.addEventListener("change", function () {
    var q = jump.value.trim().toLowerCase();
    if (!q) return;
    var rows = document.querySelectorAll(".tl-row");
    for (var i = 0; i < rows.length; i++) {
      if (rows[i].dataset.name === q ||
          rows[i].dataset.name.indexOf(q) === 0) {
        var det = rows[i].closest("details");
        if (det) det.open = true;
        refreshBands();
        rows[i].scrollIntoView({ block: "center", behavior: "smooth" });
        rows[i].classList.add("tl-hit");
        setTimeout(function (r) { r.classList.remove("tl-hit"); }
                   .bind(null, rows[i]), 2500);
        return;
      }
    }
  });
})();
