d3.json("/fem/jobStatus", function(json) {
    var data = [parseInt(json["success"]),parseInt(json["unstable"]),parseInt(json["failed"])];
    var width = 500,
        height = 500,
        outerRadius = Math.min(width, height) / 2,
        innerRadius = outerRadius * .1,
        //color = d3.scale.category20(),
        color = ["#89ba17", "#fabb00", "#e32119"],
        donut = d3.layout.pie(),
        arc = d3.svg.arc().innerRadius(innerRadius).outerRadius(outerRadius);

    var vis = d3.select("#pie-view")
      .append("svg")
      .data([data])
      .attr("width", width)
      .attr("height", height);

    var arcs = vis.selectAll("g.arc")
      .data(donut)
      .enter().append("g")
      .attr("class", "arc")
      .attr("transform", "translate(" + outerRadius + "," + outerRadius + ")");

    arcs.append("path")
      .attr("fill", function(d, i) { return color[i]; })
      .attr("d", arc);

    arcs.append("text")
      .attr("transform", function(d) { return "translate(" + arc.centroid(d) + ")"; })
      .attr("dy", ".35em")
      .attr("text-anchor", "middle")
      .attr("display", function(d) { return d.value > .15 ? null : "none"; })
      .text(function(d, i) { return d.value; });
});

