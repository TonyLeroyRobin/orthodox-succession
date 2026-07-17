/* Formation network (F6.4): bipartite person-institution graph; founded_from
   edges dashed between institutions; century filter; zoom scoped to the SVG;
   the association table below is build-time HTML. */
(function () {
  var host = document.getElementById("formation");
  if (!host || typeof d3 === "undefined") return;
  fetch("/data/formation-graph.json").then(function (r) { return r.json(); })
    .then(function (g) {
      var W = 1100, H = 640;
      var svg = d3.select(host).append("svg")
        .attr("viewBox", "0 0 " + W + " " + H).attr("width", "100%")
        .attr("role", "img").attr("aria-label", "Formation network");
      var root = svg.append("g");
      svg.call(d3.zoom().scaleExtent([0.4, 6])
        .on("zoom", function (ev) { root.attr("transform", ev.transform); }));

      var sim = d3.forceSimulation(g.nodes)
        .force("link", d3.forceLink(g.links)
          .id(function (d) { return d.id; }).distance(110))
        .force("charge", d3.forceManyBody().strength(-300))
        .force("center", d3.forceCenter(W / 2, H / 2))
        .force("collide", d3.forceCollide(30));

      var lines = root.append("g").selectAll("line").data(g.links).join("line")
        .attr("stroke", "#7a7265").attr("stroke-width", 1.6)
        .attr("stroke-dasharray", function (d) {
          return d.kind === "founded_from" ? "6,4" : null;
        });
      lines.append("title").text(function (d) { return d.kind; });

      var nodes = root.append("g").selectAll("g").data(g.nodes).join("g")
        .style("cursor", "pointer")
        .on("click", function (ev, d) {
          if (d.url) window.location.href = d.url;
        });
      nodes.each(function (d) {
        var el = d3.select(this);
        if (d.kind === "institution") {
          el.append("rect").attr("width", 14).attr("height", 14)
            .attr("fill", "#8a7f6a").attr("stroke", "#fff")
            .attr("stroke-width", 1.5);
        } else {
          el.append("circle").attr("r", 8).attr("fill", "#2456a8")
            .attr("stroke", "#fff").attr("stroke-width", 1.5);
        }
        el.append("text").attr("dx", 11).attr("dy", 4)
          .attr("font-size", "11px").attr("paint-order", "stroke")
          .attr("stroke", "#fff").attr("stroke-width", 3).attr("fill", "#333")
          .text(d.label);
        el.append("title").text(d.label + (d.year ? " (" + d.year + ")" : ""));
      });

      var slider = document.getElementById("fgYear");
      var label = document.getElementById("fgYearLabel");
      function applyCentury() {
        var c = slider ? +slider.value : 21;
        if (label) label.textContent = c;
        function visible(d) {
          return d.year == null || Math.ceil(d.year / 100) <= c;
        }
        nodes.style("display", function (d) { return visible(d) ? "" : "none"; });
        lines.style("display", function (d) {
          return visible(d.source) && visible(d.target) ? "" : "none";
        });
      }
      if (slider) slider.addEventListener("input", applyCentury);

      sim.on("tick", function () {
        lines
          .attr("x1", function (d) { return d.source.x; })
          .attr("y1", function (d) { return d.source.y; })
          .attr("x2", function (d) { return d.target.x; })
          .attr("y2", function (d) { return d.target.y; });
        nodes.each(function (d) {
          var el = d3.select(this);
          el.select("circle").attr("cx", d.x).attr("cy", d.y);
          el.select("rect").attr("x", d.x - 7).attr("y", d.y - 7);
          el.select("text").attr("x", d.x).attr("y", d.y);
        });
        applyCentury();
      });
    })
    .catch(function (e) {
      host.innerHTML = '<p class="note">Graph unavailable (' + e +
        ') — the association table below carries the full content.</p>';
    });
})();
