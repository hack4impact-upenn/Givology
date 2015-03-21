$(document).ready(function() {

  $("#sectionInfo").hide();

  console.log("here at least");

  var width = 960,
  height = 500,
  radius = Math.min(width, height) / 2;

  var color = d3.scale.ordinal()
  .range(["#98abc5", "#8a89a6", "#7b6888", "#6b486b", "#a05d56", "#d0743c", "#ff8c00"]);

  var arc = d3.svg.arc()
  .outerRadius(radius - 10)
  .innerRadius(radius - 70);

  var pie = d3.layout.pie()
  .sort(null)
  .value(function(d) { return d.population; });

  var svg = d3.select("body").append("svg")
  .attr("width", width)
  .attr("height", height)
  .append("g")
  .attr("transform", "translate(" + width / 2 + "," + height / 2 + ")");

  d3.csv("/static/impact_temp_data.csv", function(error, data) {

    data.forEach(function(d) {
      d.population = +d.population;
    });

    var g = svg.selectAll(".arc")
    .data(pie(data))
    .enter().append("g")
    .attr("class", "arc");

    g.append("path")
    .attr("d", arc)
    .style("fill", function(d) { return d3.rgb("#41B5D9"); })
    .on("mouseover", sectionMouseOver)
    .on("mouseout", sectionMouseOut);



    function sectionMouseOver(d) {
      d3.select(this).style("fill", function(d) {
        return d3.rgb("#EAC223");
      });

      $("#sectionInfo").show();
    }

    function sectionMouseOut(d) {
      d3.select(this).style("fill", function(d) {
        return d3.rgb("#41B5D9");
      });

      $("#sectionInfo").hide();
    }




});

});



