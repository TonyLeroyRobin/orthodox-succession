/* Ideas graph (C3.1): documented correspondence (Tier 1, solid) and
   citation/response (Tier 2, dashed); gated influence overlay (Tier 3,
   dotted purple, off by default). Never blended with the consecration
   graph. */
(function () {
  fetch("/data/ideas-graph.json").then(function (r) { return r.json(); })
    .then(function (g) {
      var W = 1100, H = 620;
      var svg = d3.select("#ideas").append("svg")
        .attr("viewBox", "0 0 " + W + " " + H).attr("width", "100%");
      var showT3 = false;
      var toggle = document.getElementById("tier3toggle");
      if (toggle) toggle.addEventListener("change", function () {
        showT3 = toggle.checked;
        update();
      });

      var sim = d3.forceSimulation(g.nodes)
        .force("link", d3.forceLink(g.links)
          .id(function (d) { return d.id; }).distance(120))
        .force("charge", d3.forceManyBody().strength(-350))
        .force("center", d3.forceCenter(W / 2, H / 2))
        .force("collide", d3.forceCollide(28));

      var linkG = svg.append("g");
      var nodeG = svg.append("g");

      var links = linkG.selectAll("g").data(g.links).join("g");
      var lines = links.append(function (d) {
        var a = document.createElementNS("http://www.w3.org/2000/svg", "a");
        if (d.work) a.setAttribute("href", d.work);
        return a;
      }).append("line")
        .attr("stroke", function (d) {
          return d.tier === 3 ? "#5d5480" : "#7a7265";
        })
        .attr("stroke-width", function (d) { return d.tier === 1 ? 2 : 1.4; })
        .attr("stroke-dasharray", function (d) {
          return d.tier === 2 ? "6,4" : d.tier === 3 ? "2,4" : null;
        });
      links.selectAll("line").append("title").text(function (d) {
        var t = "Tier " + d.tier + ": " + (d.title || "");
        if (d.locator) t += " — " + d.locator;
        return t;
      });

      var nodes = nodeG.selectAll("a").data(g.nodes).join("a")
        .attr("href", function (d) { return d.url || null; });
      nodes.each(function (d) {
        var el = d3.select(this);
        if (d.external) {
          el.append("rect").attr("width", 14).attr("height", 14)
            .attr("fill", "#b26a00").attr("stroke", "#fff")
            .attr("stroke-width", 1.5);
        } else {
          el.append("circle").attr("r", 8)
            .attr("fill", "#2456a8").attr("stroke", "#fff")
            .attr("stroke-width", 1.5);
        }
        el.append("text").attr("class", "map-label")
          .attr("dx", 11).attr("dy", 4).attr("font-size", "12px")
          .attr("paint-order", "stroke").attr("stroke", "#fff")
          .attr("stroke-width", 3).attr("fill", "#333")
          .text(d.label);
        el.append("title").text(d.label +
          (d.external ? " (external, out of scope — no person record)" : ""));
      });

      function update() {
        links.style("display", function (d) {
          return d.tier === 3 && !showT3 ? "none" : "";
        });
      }
      update();

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
      });
    });
})();
