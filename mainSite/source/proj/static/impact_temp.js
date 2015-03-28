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
=======
	$("#sectionInfo").hide();

	// set svg properties
	var width = 300;
	var height = 300;
	var svg = d3.select("#display")
	.append("svg")
	.attr("width", width)
	.attr("height", height)
	.append("g")
	.attr("transform", "translate(" + width / 2 + "," + height / 2 + ")");

	// set radii of arcs
	var radius = Math.min(width, height) / 2;
	var arc = d3.svg.arc()
	.outerRadius(radius - 10)
	.innerRadius(radius - 55);

	// pull in arc values from template
	var arcvalues = [];
	impact_organizations.forEach( function (arrayItem){
		arcvalues.push(arrayItem.given);
	});

	// create chart with values
	var pie = d3.layout.pie(arcvalues)
	.sort(null);
	
	// create svg groups with pie values
	var g = svg.selectAll(".arc")
	.data(pie(arcvalues))
	.enter().append("g")
	.attr("class", "arc")
	.on("mouseover", sectionMouseOver)
	.on("mouseout", sectionMouseOut);

	// add arcs to pie
	g.append("path")
	.attr("d", arc)
	.style("fill", function(d) { return d3.rgb("#41B5D9"); });
	
	// add unique ids to arcs for later identification
    $(".arc").each(function(i) {
    	console.log("here?");
    	$(this).attr("id", impact_organizations[i].name);
    });

    // when mouse over arc
	function sectionMouseOver(d) {

		// change color to yellow
		d3.select(this).select("path").style("fill", function(d) {
			return d3.rgb("#EAC223");
		});

		// pull out specific organization info
		var picurl, name, given, have, need;
		for (i = 0; i < impact_organizations.length; i++) {
			if (impact_organizations[i].name == $(this).attr("id")) {
				picurl = impact_organizations[i].pic;
				name = impact_organizations[i].name;
				given = impact_organizations[i].given;
				have = impact_organizations[i].sofar;
				need = impact_organizations[i].need;
				break;
			}
		}

		// load html
		$("#sectionInfo")
		.append(
			$("<div>").attr("class", "picname")
			.append(
				$("<div>").attr("class", "pic").html("<img src=" + picurl + " >")
				)
			.append (
				$("<div>").attr("class", "name").html(name)
				)
			)
		.append(
			$("<div>").attr("class", "funds")
			.append(
				$("<div>").attr("class", "given").html(given)
				)
			.append(
				$("<div>").attr("class", "progressbar").html("progress bar")
				)
			.append(
				$("<div>").attr("class", "wantneed").html(have + " -- " + need)
				)
			);

		$("#sectionInfo").show();
	}

	function sectionMouseOut(d) {
		d3.select(this).select("path").style("fill", function(d) {
			return d3.rgb("#41B5D9");
		});

		$("#sectionInfo").empty();
		// $("#sectionInfo").hide();
	}

});



