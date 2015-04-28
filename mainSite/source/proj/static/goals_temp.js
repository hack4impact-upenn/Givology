$(document).ready(function() {
 

 	var dollars_goal = 100; // HARD CODED FOR NOW

	// calculating goal bar widths
	var dollars_given_width = Math.min(total_dollars_given/dollars_goal * 365, 365);
	

	console.log(total_dollars_given);

	$("#dollar-met").attr("style", "width: " + dollars_given_width + "px");

	$("#dollar-met-text").html("$" + total_dollars_given);

 
 });