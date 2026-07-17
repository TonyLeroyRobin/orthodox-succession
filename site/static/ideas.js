/* Ideas graph (C3.1, reworked in F1): documented correspondence (Tier 1,
   solid) and citation/response (Tier 2, dashed); gated influence overlay
   (Tier 3, dotted purple, off by default). Zoom/pan scoped to the SVG only —
   the page scrolls normally outside it; nodes click through to person pages,
   edges to the evidencing work; touch (pinch/tap) supported via d3.zoom.
   The static edge table below the canvas is build-time HTML — the page is
   fully informative with JavaScript disabled. */
(function () {
  var host = document.getElementById("ideas");
  if (!host || typeof d3 === "undefined") return;
  fetch("/data/ideas-graph.json").then(function (r) { return r.json(); })
    .then(function (g) {
      var W = 1100, H = 620;
      var svg = d3.select(host).append("svg")
        .attr("viewBox", "0 0 " + W + " " + H)
        .attr("width", "100%")
        .attr("role", "img")
        .attr("aria-label", "Correspondence and citation network");
      var root = svg.append("g");

      // zoom/pan scoped to this SVG; wheel outside it scrolls the page
      svg.call(d3.zoom().scaleExtent([0.4, 6])
        .on("zoom", function (ev) { root.attr("transform", ev.transform); }));

      var sim = d3.forceSimulation(g.nodes)
        .force("link", d3.forceLink(g.links)
          .id(function (d) { return d.id; }).distance(120))
        .force("charge", d3.forceManyBody().strength(-350))
        .force("center", d3.forceCenter(W / 2, H / 2))
        .force("collide", d3.forceCollide(30));

      var linkSel = root.append("g").selectAll("a")
        .data(g.links).join("a")
        .attr("href", function (d) { return d.work || null; });
      var lines = linkSel.append("line")
        .attr("stroke", function (d) {
          return d.tier === 3 ? "#5d5480" : "#7a7265";
        })
        .attr("stroke-width", function (d) { return d.tier === 1 ? 2.5 : 1.6; })
        .attr("stroke-dasharray", function (d) {
          return d.tier === 2 ? "6,4" : d.tier === 3 ? "2,4" : null;
        });
      lines.append("title").text(function (d) {
        var t = "Tier " + d.tier + ": " + (d.title || "");
        if (d.locator) t += " — " + d.locator;
        return t;
      });

      var nodeSel = root.append("g").selectAll("g")
        .data(g.nodes).join("g")
        .style("cursor", "pointer")
        .call(d3.drag()
          .on("start", function (ev, d) {
            if (!ev.active) sim.alphaTarget(0.3).restart();
            d.fx = d.x; d.fy = d.y;
          })
          .on("drag", function (ev, d) { d.fx = ev.x; d.fy = ev.y; })
          .on("end", function (ev, d) {
            if (!ev.active) sim.alphaTarget(0);
            d.fx = null; d.fy = null;
          }))
        .on("click", function (ev, d) {
          // explicit navigation — independent of SVG <a> quirks
          if (d.url && !ev.defaultPrevented) window.location.href = d.url;
        });
      nodeSel.each(function (d) {
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
        el.append("text")
          .attr("dx", 11).attr("dy", 4).attr("font-size", "12px")
          .attr("paint-order", "stroke").attr("stroke", "#fff")
          .attr("stroke-width", 3).attr("fill", "#333")
          .text(d.label);
        el.append("title").text(d.label +
          (d.external ? " (external, out of scope — no person record)" : ""));
      });

      var showT3 = false;
      var toggle = document.getElementById("tier3toggle");
      function applyT3() {
        linkSel.style("display", function (d) {
          return d.tier === 3 && !showT3 ? "none" : "";
        });
      }
      if (toggle) toggle.addEventListener("change", function () {
        showT3 = toggle.checked;
        applyT3();
      });
      applyT3();

      sim.on("tick", function () {
        lines
          .attr("x1", function (d) { return d.source.x; })
          .attr("y1", function (d) { return d.source.y; })
          .attr("x2", function (d) { return d.target.x; })
          .attr("y2", function (d) { return d.target.y; });
        nodeSel.each(function (d) {
          var el = d3.select(this);
          el.select("circle").attr("cx", d.x).attr("cy", d.y);
          el.select("rect").attr("x", d.x - 7).attr("y", d.y - 7);
          el.select("text").attr("x", d.x).attr("y", d.y);
        });
      });
    })
    .catch(function (e) {
      host.innerHTML = '<p class="note">Graph unavailable (' + e +
        ') — the edge table below carries the full content.</p>';
    });
})();
