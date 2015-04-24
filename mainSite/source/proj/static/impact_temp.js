$(document).ready(function() {
 
 	// set svg properties
 	var width = 220;
 	var height = 220;
 	var svg = d3.select("#display").append("svg")
 	.attr("width", width)
 	.attr("height", height)
 	.append("g")
 	.attr("transform", "translate(" + width / 2 + "," + height / 2 + ")");
 
 	// set radii of arcs
 	var radius = Math.min(width, height) / 2;
 	var arc = d3.svg.arc()
 	.outerRadius(radius - 10)
 	.innerRadius(radius - 45);
 
 	// pull in arc values from template
 	var arcvalues = [];
 	impact_organizations.forEach( function (arrayItem){
 		arcvalues.push(arrayItem.given);
 	});

	if (arcvalues.length == 0) arcvalues.push(-1);
 
 	// create chart with values
 	var pie = d3.layout.pie(arcvalues)
 	.sort(null);
 	

	// create svg groups with pie values
 	var g = svg.selectAll(".arc")
 	.data(pie(arcvalues))
 	.enter().append("g")
 	.attr("class", "arc")
 	.on("mouseover", sectionMouseOver)
 	.on("mouseout", sectionMouseOut)
 	.on("click" , sectionMouseClick);
 
	// add arcs to pie
 	g.append("path")
 	.attr("d", arc)
 	.style("fill", function(d) { 
 		if (arcvalues[0] == -1) {
 			return d3.rgb("#EEEEEE");
 		}
 		else {
 			return d3.rgb("#41B5D9"); 
 		}

 	});
 	

	// add unique ids to arcs for later identification
	$(".arc").each(function(i) {
		$(this).attr("id", impact_organizations[i].name);
	});
 
    // when mouse over arc
 	function sectionMouseOver(d) {

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

 		$("#sectionInfo").empty();

 		var hover_color;

 		// when nothing donated
 		if (arcvalues[0] == -1) {

 			hover_color = "#DDDDDD";

			// load html
	 		$("#sectionInfo")
	 		.append(
	 			$("<div>").attr("class", "nothing").html("You haven't made any donations yet. Click to Giv Now!")
	 			)
 		}

 		else {

 			hover_color = "#EAC223"

	 		// calculating progress bar widths
	 		var have_width = Math.min(have/need * 365, 365);
	 		var given_width = Math.min(given/need * 365, 365);
	 
			// load html
	 		$("#sectionInfo")
	 		.append(
	 			$("<div>").attr("class", "picname")
	 			.append(
					$("<div>").attr("class", "pic").html("<img src=" + picurl + " >")
	 				)
	 			.append (
	 				$("<div>").attr("class", "nameouter").append(
	 					$("<div>").attr("class", "name").append(
	 						$("<span>").html(name)
	 						)
	 					)
	 				)
	 			)
	 		.append(
	 			$("<div>").attr("class", "funds")
	 			.append(
	 				$("<div>").attr("class", "given").html("<span style='color:#E98A23'>$" + given + "</span> contributed")
	 				)
	 			.append(
	 				$("<div>").attr("class", "progress")
	 				.append(
	 					$("<div>").attr("id", "progressbar")
	 					.append(
	 						$("<div>").attr("id", "sofar").attr("style", "width: " + have_width + "px")
	 						.append(
	 							$("<div>").attr("id", "given").attr("style", "width: " + given_width + "px")
	 							)
	 						)
	 					.append(
	 						$("<div>").attr("id", "sofarnum").html("$" + have)
	 						)
	 					)
	 				)
	 			.append(
	 				$("<div>").attr("class", "wantneed").html("<span style='color:#41B5D9'>$" + have + "</span> raised out of <span style='color:#7DC031'>$" + need + "</span> needed")
	 				)
	 			);
	 		
	 		$(".name").bigtext();
 		}

 		// set hover_color
 		d3.select(this).select("path").style("fill", function(d) {
	 			return d3.rgb(hover_color);
	 		});

 	}
 
 	function sectionMouseOut(d) {
 		var color;
 		if (arcvalues[0] == -1 ) {
 			color = "#EEEEEE";
 		}
 		else {
 			color = "#41B5D9";
 		}
 		d3.select(this).select("path").style("fill", function(d) {
 				return d3.rgb(color);
 			});


 		$("#sectionInfo").empty();

 		reloadSection();


 	}

 	function reloadSection() {
 		$("#sectionInfo").append(
 			$("<div>").attr("class", "test")
 			
 			);
 	}

 	function sectionMouseClick(d) {

 		var url;

 		if (arcvalues[0] == -1) {

 			url = "/giv-now/"
 		}
 		else {

 			// pull out specific organization url
	 		for (i = 0; i < impact_organizations.length; i++) {
	 			if (impact_organizations[i].name == $(this).attr("id")) {
	 				url = impact_organizations[i].url;
	 				break;
 				}
 			}
 		}

 		console.log(url);

 		var win = window.open(url, '_blank');
  		win.focus();

 	}
 
 });