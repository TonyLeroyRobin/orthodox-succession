/* Map v2 (Milestone R2): persistence rule (filled / hollow / suppressed,
   never unmounted while the see exists), Mediterranean default viewport with
   zoom/pan and reset, era presets, permanent Pentarchy labels, 24px minimum
   hit targets, click-through to see pages. Reads /data/map-data.json. */
(function () {
  var statusFill = { verified: "#2e7d32", unverified: "#b26a00",
                     disputed: "#b3261e" };
  var PENTARCHY = {
    "see/pre-schism-rome/rome": 1,
    "see/constantinople/constantinople": 1,
    "see/alexandria/alexandria": 1,
    "see/antioch/antioch": 1,
    "see/jerusalem/jerusalem": 1
  };
  Promise.all([
    fetch("/data/map-data.json").then(function (r) { return r.json(); }),
    fetch("/assets/vendor/countries-110m.json").then(function (r) { return r.json(); }),
    fetch("/data/controversy-geo.json").then(function (r) { return r.json(); })
      .catch(function () { return {}; }),
  ]).then(function (loaded) {
    var seesData = loaded[0], world = loaded[1], controGeo = loaded[2];
    var land = topojson.feature(world, world.objects.countries);
    var W = 1150, H = 560;
    var projection = d3.geoNaturalEarth1();
    // R2.2: default viewport = Mediterranean / Near East bounding box,
    // not the world and not the dataset's full extent.
    var MED_BBOX = { type: "FeatureCollection", features: [
      { type: "Feature", geometry: { type: "Point", coordinates: [-12, 22] } },
      { type: "Feature", geometry: { type: "Point", coordinates: [55, 57] } },
    ] };
    projection.fitExtent([[30, 20], [W - 30, H - 20]], MED_BBOX);
    var path = d3.geoPath(projection);
    var svg = d3.select("#map").append("svg")
      .attr("viewBox", "0 0 " + W + " " + H).attr("width", "100%");
    var root = svg.append("g");
    root.append("g").selectAll("path").data(land.features).join("path")
      .attr("d", path).attr("class", "map-land");
    var g = root.append("g");
    var k = 1;  // current zoom scale, for screen-constant sizes

    var zoom = d3.zoom().scaleExtent([1, 12])
      .on("zoom", function (ev) {
        k = ev.transform.k;
        root.attr("transform", ev.transform);
        render(currentYear);
      });
    svg.call(zoom);
    document.getElementById("resetView").addEventListener("click", function () {
      svg.transition().duration(300)
         .call(zoom.transform, d3.zoomIdentity);
    });

    // R2.1: a see renders from its first attested date onward and never
    // disappears while it exists. States: active (filled, colored by tenure
    // status), attested (hollow), suppressed (grayed, crossed). A tenure
    // active after a suppression date (a revival) outranks the suppression.
    function stateAt(s, year) {
      var earliest = Infinity, active = null;
      s.t.forEach(function (t) {
        earliest = Math.min(earliest, t.f);
        if (t.f <= year && year <= t.e) active = t;
      });
      if (s.sup != null) earliest = Math.min(earliest, s.sup);
      if (active) return { kind: "active", t: active };
      if (s.sup != null && year >= s.sup) return { kind: "suppressed" };
      if (earliest <= year) return { kind: "attested" };
      return { kind: "hidden" };
    }

    // P6: controversy overlay — rings on the sees derivable from tagged
    // records (participants' and authors' sees); band span shown in the
    // option label; the time slider stays live underneath.
    var controLayer = root.append("g");
    var controSel = document.getElementById("controSel");
    if (controSel) {
      Object.keys(controGeo).sort().forEach(function (k) {
        var c = controGeo[k];
        if (!c.points.length) return;
        var opt = document.createElement("option");
        opt.value = k;
        opt.textContent = c.label +
          (c.f ? " (" + c.f + (c.e ? "–" + c.e : "") + ")" : "");
        controSel.appendChild(opt);
      });
      controSel.addEventListener("change", renderContro);
    }
    function renderContro() {
      controLayer.selectAll("*").remove();
      var k = controSel && controSel.value;
      if (!k || !controGeo[k]) return;
      controGeo[k].points.forEach(function (p) {
        var xy = projection([p.lon, p.lat]);
        controLayer.append("circle")
          .attr("cx", xy[0]).attr("cy", xy[1])
          .attr("r", 10 / Math.sqrt(k0()))
          .attr("fill", "none").attr("stroke", "#5d5480")
          .attr("stroke-width", 2 / Math.sqrt(k0()))
          .attr("stroke-opacity", 0.85)
          .append("title")
          .text(controGeo[k].label + " — " + p.see + " (via " + p.via + ")");
      });
    }
    function k0() { return k || 1; }

    var currentYear = 2026;
    function render(year) {
      currentYear = year;
      renderContro();
      document.getElementById("yearLabel").textContent = year;
      var data = seesData.map(function (s) {
        return { s: s, st: stateAt(s, year) };
      }).filter(function (d) { return d.st.kind !== "hidden"; });
      g.selectAll("g.see").remove();
      var nodes = g.selectAll("g.see").data(data).join("g")
        .attr("class", "see");
      var a = nodes.append("a")
        .attr("href", function (d) { return d.s.url; });

      function cx(d) { return projection([d.s.lon, d.s.lat])[0]; }
      function cy(d) { return projection([d.s.lon, d.s.lat])[1]; }

      // R2.4: minimum hit area 24px on screen — a transparent hit circle of
      // 12px screen radius, counter-scaled against the zoom.
      a.append("circle")
        .attr("cx", cx).attr("cy", cy)
        .attr("r", 12 / k)
        .attr("fill", "transparent").attr("stroke", "none");

      a.each(function (d) {
        var el = d3.select(this);
        var r = (d.st.kind === "active" ? 6 : 3.5) / Math.sqrt(k);
        if (d.st.kind === "suppressed") {
          // grayed, crossed marker
          el.append("circle").attr("cx", cx(d)).attr("cy", cy(d))
            .attr("r", r).attr("fill", "none")
            .attr("stroke", "#9a9a9a").attr("stroke-width", 1.2 / k);
          var s = r * 0.9;
          el.append("path")
            .attr("d", "M" + (cx(d) - s) + "," + (cy(d) - s) +
                       "L" + (cx(d) + s) + "," + (cy(d) + s) +
                       "M" + (cx(d) - s) + "," + (cy(d) + s) +
                       "L" + (cx(d) + s) + "," + (cy(d) - s))
            .attr("stroke", "#9a9a9a").attr("stroke-width", 1.2 / k);
        } else {
          el.append("circle").attr("cx", cx(d)).attr("cy", cy(d))
            .attr("r", r)
            .attr("class", "map-see")
            .attr("fill", d.st.kind === "active"
                  ? (statusFill[d.st.t.s] || "#777") : "none")
            .attr("stroke", d.st.kind !== "active" ? "#7a7265"
                  : (d.st.t.d ? "#b3261e" : "#fff"))
            .attr("stroke-dasharray",
                  d.st.kind === "active" && d.st.t.d ? "3,2" : null)
            .attr("stroke-width", 1.5 / Math.sqrt(k));
        }
        var title = d.s.name;
        if (d.st.kind === "active") {
          title += "\n" + d.st.t.n + " (" + d.st.t.f + "–" + d.st.t.e + ")";
        } else if (d.st.kind === "suppressed") {
          title += "\nsuppressed " + d.s.sup;
        } else {
          title += "\nno recorded occupant in " + year;
        }
        el.append("title").text(title);
        // R2.4: permanent labels for the Pentarchy at all zooms; other
        // labels appear on zoom (k >= 3); hover keeps the tooltip.
        if (PENTARCHY[d.s.id] || k >= 3) {
          el.append("text")
            .attr("x", cx(d) + 8 / k).attr("y", cy(d) + 4 / k)
            .attr("class", "map-label")
            .attr("font-size", (PENTARCHY[d.s.id] ? 13 : 11) / k + "px")
            .attr("font-weight", PENTARCHY[d.s.id] ? "600" : "400")
            .attr("paint-order", "stroke")
            .attr("stroke", "#fff").attr("stroke-width", 3 / k)
            .attr("fill", "#333")
            .text(d.s.name);
        }
      });
    }

    var slider = document.getElementById("yearSlider");
    slider.addEventListener("input", function () { render(+slider.value); });

    // R2.3: era presets
    document.querySelectorAll(".era-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        slider.value = btn.dataset.year;
        render(+slider.value);
      });
    });

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
