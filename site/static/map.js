/* Map page (R1 port of the C1 map, reading the compact build-generated
   /data/map-data.json; the full R2 persistence/suppression rendering is a
   later milestone). */
(function () {
  var statusFill = { verified: "#2e7d32", unverified: "#b26a00",
                     disputed: "#b3261e" };
  Promise.all([
    fetch("/data/map-data.json").then(function (r) { return r.json(); }),
    fetch("/assets/vendor/countries-110m.json").then(function (r) { return r.json(); }),
  ]).then(function (loaded) {
    var seesData = loaded[0], world = loaded[1];
    var land = topojson.feature(world, world.objects.countries);
    var W = 1150, H = 560;
    var projection = d3.geoNaturalEarth1();
    projection.fitExtent([[30, 20], [W - 30, H - 20]], {
      type: "FeatureCollection",
      features: seesData.map(function (s) {
        return { type: "Feature",
                 geometry: { type: "Point", coordinates: [s.lon, s.lat] } };
      }),
    });
    var path = d3.geoPath(projection);
    var svg = d3.select("#map").append("svg")
      .attr("viewBox", "0 0 " + W + " " + H).attr("width", "100%");
    svg.append("g").selectAll("path").data(land.features).join("path")
      .attr("d", path).attr("class", "map-land");
    var g = svg.append("g");

    function stateAt(s, year) {
      var earliest = Infinity, active = null;
      s.t.forEach(function (t) {
        earliest = Math.min(earliest, t.f);
        if (t.f <= year && year <= t.e) active = t;
      });
      if (active) return { kind: "active", t: active };
      if (earliest <= year) return { kind: "attested" };
      return { kind: "hidden" };
    }

    function render(year) {
      document.getElementById("yearLabel").textContent = year;
      var data = seesData.map(function (s) {
        return { s: s, st: stateAt(s, year) };
      }).filter(function (d) { return d.st.kind !== "hidden"; });
      g.selectAll("a").remove();
      var nodes = g.selectAll("a").data(data).join("a")
        .attr("href", function (d) { return d.s.url; });
      nodes.append("circle")
        .attr("cx", function (d) { return projection([d.s.lon, d.s.lat])[0]; })
        .attr("cy", function (d) { return projection([d.s.lon, d.s.lat])[1]; })
        .attr("r", function (d) { return d.st.kind === "active" ? 6 : 3.5; })
        .attr("class", "map-see")
        .attr("fill", function (d) {
          return d.st.kind === "active"
            ? (statusFill[d.st.t.s] || "#777") : "none";
        })
        .attr("stroke", function (d) {
          if (d.st.kind !== "active") return "#7a7265";
          return d.st.t.d ? "#b3261e" : "#fff";
        })
        .attr("stroke-dasharray", function (d) {
          return d.st.kind === "active" && d.st.t.d ? "3,2" : null;
        })
        .attr("stroke-width", 1.5)
        .append("title").text(function (d) {
          return d.s.name + (d.st.kind === "active"
            ? "\n" + d.st.t.n + " (" + d.st.t.f + "–" + d.st.t.e + ")"
            : "\nno recorded occupant in " + year);
        });
    }

    var slider = document.getElementById("yearSlider");
    slider.addEventListener("input", function () { render(+slider.value); });
    render(+slider.value);

    var timer = null;
    var playBtn = document.getElementById("playBtn");
    playBtn.addEventListener("click", function () {
      if (timer) { clearInterval(timer); timer = null;
                   playBtn.innerHTML = "&#9654; play"; return; }
      if (+slider.value >= 2026) slider.value = 33;
      playBtn.innerHTML = "&#9208; pause";
      timer = setInterval(function () {
        slider.value = Math.min(2026, +slider.value + 8);
        render(+slider.value);
        if (+slider.value >= 2026) { clearInterval(timer); timer = null;
                                     playBtn.innerHTML = "&#9654; play"; }
      }, 60);
    });
  });
})();
