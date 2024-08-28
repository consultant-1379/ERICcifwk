
var nodes = {};

// Compute the distinct nodes from the links.
links.forEach(function(link) {
  link.source = nodes[link.source] || (nodes[link.source] = {name: link.source});
  link.target = nodes[link.target] || (nodes[link.target] = {name: link.target});
});

var width = 1600,
    height = 1200;

var force = d3.layout.force()
    .nodes(d3.values(nodes))
    .links(links)
    .size([width, height])
    .linkDistance(300)
    .charge(-1600)
    .on("tick", tick)
    .start();


var zoom = d3.behavior.zoom().on("zoom", zoomed);

function zoomed() {
  svg.attr("transform", "translate(" + d3.event.translate + ")scale(" + d3.event.scale + ")");
}

var svg = d3.select("#canvas").append("svg")
    .attr("viewBox", "0 0 " + width + " " + height )
    .attr("height", height).call(zoom).append("g");

svg.append("defs").selectAll("marker")
    .data(["RPMDependency", "BuildDependency", "ThirdPPDependency"])
    .enter().append("marker")
    .attr("id", function(idObject) { return idObject; })
    .attr("viewBox", "0 -5 10 10")
    .attr("refX", 15)
    .attr("refY", -1.5)
    .attr("markerWidth", 12)
    .attr("markerHeight", 12)
    .attr("orient", "auto")
    .append("path")
    .attr("d", "M0,-5L10,0L0,5");

var path = svg.append("g").selectAll("path")
    .data(force.links())
    .enter().append("path")
    .attr("class", function(d3Object) { return "link " + d3Object.type; })
    .attr("marker-end", function(d3Object) { return "url(#" + d3Object.type + ")"; });

var circle = svg.append("g").selectAll("circle")
    .data(force.nodes())
    .enter().append("circle")
    .attr("r", 20)
    .on("click", redirectToDependencyMap)
    .call(force.drag);

var text = svg.append("g").selectAll("text")

    .data(force.nodes())
    .enter().append("text")
    .style("font-size", "15px")
    .attr("x", 8)
    .attr("dy", 28)
    .attr("xlink:href","#path1")
    .attr("xlink:href", function (xlinkObject) { return xlinkObject.name; })
    .text(function (textObject) { return textObject.name; });

// Use elliptical arc path segments to doubly-encode directionality.
function tick() {
  path.attr("d", linkArc);
  circle.attr("transform", transform);
  text.attr("transform", transform);
}

function linkArc(linkObject) {
  var dx = linkObject.target.x - linkObject.source.x,
      dy = linkObject.target.y - linkObject.source.y,
      dr = Math.sqrt(dx * dx + dy * dy);
  return "M" + linkObject.source.x + "," + linkObject.source.y + "A" + dr + "," + dr + " 0 0,1 " + linkObject.target.x + "," + linkObject.target.y;
}

function transform(d3Object) {
  return "translate(" + d3Object.x + "," + d3Object.y + ")";
}

function redirectToDependencyMap(clickObject) {
    
    var labelName = clickObject.name;
    var labelNameSpilt = labelName.split("_");
    var pkgName = (labelNameSpilt[0] + "_" + labelNameSpilt[1]);
    var pkgVersion = (labelNameSpilt[2]);
    var baseURL = window.location.origin;

    var stringToOpen= baseURL.concat("/showPackageCompleteDependenciesMap","/",pkgName,"/",pkgVersion,"/");
    window.open(stringToOpen,"_self");
}
