$(document).ready(function() {

	$("#sectionInfo").hide();

	// set svg properties
	var width = 960;
	var height = 500;
	var svg = d3.select("body").append("svg")
	.attr("width", width)
	.attr("height", height)
	.append("g")
	.attr("transform", "translate(" + width / 2 + "," + height / 2 + ")");

	// set radii of arcs
	var radius = Math.min(width, height) / 2;
	var arc = d3.svg.arc()
	.outerRadius(radius - 10)
	.innerRadius(radius - 70);

	// pull in arc values from template
	var arcvalues = [];
	impact_organizations.forEach( function (arrayItem){
		arcvalues.push(arrayItem.given);
	});

	// create chart with values
	var pie = d3.layout.pie(arcvalues)
	.sort(null);
	

	var g = svg.selectAll(".arc")
	.data(pie(arcvalues))
	.enter().append("g")
	.attr("class", "arc")
	.on("mouseover", sectionMouseOver)
	.on("mouseout", sectionMouseOut);

	g.append("path")
	.attr("d", arc)
	.style("fill", function(d) { return d3.rgb("#41B5D9"); });
	

    $(".arc").each(function(i) {
    	console.log("here?");
    	$(this).attr("id", impact_organizations[i].name);
    });

	function sectionMouseOver(d) {
		d3.select(this).select("path").style("fill", function(d) {
			return d3.rgb("#EAC223");
		});

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

		$("#sectionInfo")
		.append(
			$("<div>").attr("class", "picname")
			.append(
				$("<div>").attr("class", "pic").html(picurl)
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
		$("#sectionInfo").hide();
	}

});



