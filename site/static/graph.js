/* Consecration Graph v2 (F2): time-layered DAG — consecration date flows
   top-to-bottom; jurisdiction = node color; verification status = ring
   color; principal vs co-consecrator edge styles. Trace mode: click a node
   to highlight its full consecration ancestry and descendants with a
   breadcrumb chain; ?trace=<person-id> pre-activates. Zoom/pan scoped to
   the SVG; static fallback tables below carry everything without JS. */
(function () {
  var host = document.getElementById("graph");
  if (!host || typeof d3 === "undefined") return;
  fetch("/data/graph-v2.json").then(function (r) { return r.json(); })
    .then(function (g) {
      var W = 1150, H = Math.max(600, 90 * g.layers.length);
      var statusStroke = { verified: "#2e7d32", unverified: "#b26a00",
                           disputed: "#b3261e" };
      var jurs = Array.from(new Set(g.nodes.map(function (n) { return n.jur; })))
        .sort();
      var color = d3.scaleOrdinal()
        .domain(jurs)
        .range(jurs.map(function (j, i) {
          return d3.hsl((i * 360 / jurs.length) % 360, 0.55, 0.55) + "";
        }));

      // layered layout: y by layer (time band), x spread within layer
      var byId = {};
      g.nodes.forEach(function (n) { byId[n.id] = n; });
      g.layers.forEach(function (layer, li) {
        var members = g.nodes.filter(function (n) { return n.layer === li; })
          .sort(function (a, b) {
            return a.jur < b.jur ? -1 : a.jur > b.jur ? 1 :
                   a.label < b.label ? -1 : 1;
          });
        members.forEach(function (n, i) {
          n.x = 90 + (W - 180) * (members.length === 1 ? 0.5
                : i / (members.length - 1));
          n.y = 60 + li * 90;
        });
      });

      var svg = d3.select(host).append("svg")
        .attr("viewBox", "0 0 " + W + " " + H).attr("width", "100%")
        .attr("role", "img")
        .attr("aria-label", "Consecration succession graph");
      var root = svg.append("g");
      svg.call(d3.zoom().scaleExtent([0.4, 6])
        .on("zoom", function (ev) { root.attr("transform", ev.transform); }));

      // year band labels
      g.layers.forEach(function (label, li) {
        root.append("text").attr("x", 6).attr("y", 64 + li * 90)
          .attr("font-size", "11px").attr("fill", "#7a7265").text(label);
      });

      var up = {}, down = {};
      g.links.forEach(function (l) {
        (up[l.target] = up[l.target] || []).push(l.source);
        (down[l.source] = down[l.source] || []).push(l.target);
      });

      var linkSel = root.append("g").selectAll("line").data(g.links).join("line")
        .attr("x1", function (d) { return byId[d.source].x; })
        .attr("y1", function (d) { return byId[d.source].y; })
        .attr("x2", function (d) { return byId[d.target].x; })
        .attr("y2", function (d) { return byId[d.target].y; })
        .attr("stroke", "#7a7265")
        .attr("stroke-width", function (d) { return d.principal ? 2.2 : 1.2; })
        .attr("stroke-dasharray", function (d) {
          return d.principal ? null : "4,3";
        });
      linkSel.append("title").text(function (d) {
        return byId[d.source].label + " → " + byId[d.target].label +
          (d.principal ? " (principal)" : " (co-consecrator)") +
          (d.year ? ", " + d.year : "");
      });

      var nodeSel = root.append("g").selectAll("g").data(g.nodes).join("g")
        .style("cursor", "pointer");
      nodeSel.append("circle")
        .attr("cx", function (d) { return d.x; })
        .attr("cy", function (d) { return d.y; })
        .attr("r", 8)
        .attr("fill", function (d) { return color(d.jur); })
        .attr("stroke", function (d) {
          return statusStroke[d.status] || "#777";
        })
        .attr("stroke-width", 2.5);
      nodeSel.append("text")
        .attr("x", function (d) { return d.x + 11; })
        .attr("y", function (d) { return d.y + 4; })
        .attr("font-size", "11px").attr("paint-order", "stroke")
        .attr("stroke", "#fff").attr("stroke-width", 3).attr("fill", "#333")
        .text(function (d) { return d.label; });
      nodeSel.append("title").text(function (d) {
        return d.label + " — " + d.jur + " · " + d.status +
          "\nclick: trace lineage · double-click: open person page";
      });

      var crumb = document.getElementById("traceCrumb");
      function chain(id, dir) {
        var out = [], seen = {}, stack = [id];
        while (stack.length) {
          var cur = stack.pop();
          (dir[cur] || []).forEach(function (nxt) {
            if (!seen[nxt]) { seen[nxt] = 1; out.push(nxt); stack.push(nxt); }
          });
        }
        return out;
      }
      function trace(id) {
        if (!byId[id]) return;
        var keep = {};
        keep[id] = 1;
        chain(id, up).forEach(function (x) { keep[x] = 1; });
        chain(id, down).forEach(function (x) { keep[x] = 1; });
        nodeSel.attr("opacity", function (d) { return keep[d.id] ? 1 : 0.12; });
        linkSel.attr("opacity", function (d) {
          return keep[d.source] && keep[d.target] ? 1 : 0.06;
        });
        if (crumb) {
          var members = g.nodes.filter(function (n) { return keep[n.id]; })
            .sort(function (a, b) { return (a.year || 0) - (b.year || 0); });
          crumb.innerHTML = "<strong>Trace:</strong> " + members.map(function (n) {
            return '<a href="' + n.url + '">' + n.label + "</a>" +
                   (n.year ? " (" + n.year + ")" : "");
          }).join(" → ") +
          ' <button id="clearTrace">clear trace</button>';
          var cb = document.getElementById("clearTrace");
          if (cb) cb.addEventListener("click", clear_);
        }
        try {
          history.replaceState(null, "",
            "?trace=" + encodeURIComponent(id));
        } catch (e) { /* file:// etc. */ }
      }
      function clear_() {
        nodeSel.attr("opacity", 1);
        linkSel.attr("opacity", 1);
        if (crumb) crumb.innerHTML = "";
        try { history.replaceState(null, "", location.pathname); } catch (e) {}
      }
      nodeSel.on("click", function (ev, d) { trace(d.id); });
      nodeSel.on("dblclick", function (ev, d) {
        if (d.url) window.location.href = d.url;
      });

      // search/focus typeahead
      var input = document.getElementById("graphJump");
      if (input) {
        var dl = document.getElementById("graphNodes");
        g.nodes.forEach(function (n) {
          var o = document.createElement("option");
          o.value = n.label;
          dl.appendChild(o);
        });
        input.addEventListener("change", function () {
          var q = input.value.trim().toLowerCase();
          var hit = g.nodes.filter(function (n) {
            return n.label.toLowerCase().indexOf(q) === 0;
          })[0];
          if (hit) trace(hit.id);
        });
      }

      // ?trace=<id> pre-activation (progressive enhancement)
      var m = /[?&]trace=([^&]+)/.exec(location.search);
      if (m) trace(decodeURIComponent(m[1]));

      // legend: jurisdictions
      var leg = document.getElementById("graphLegend");
      if (leg) {
        leg.innerHTML = jurs.map(function (j) {
          return '<span style="white-space:nowrap"><span style="color:' +
            color(j) + '">&#9679;</span> ' + j + "</span>";
        }).join(" · ");
      }
    })
    .catch(function (e) {
      host.innerHTML = '<p class="note">Graph unavailable (' + e +
        ') — the record tables below carry the full content.</p>';
    });
})();
