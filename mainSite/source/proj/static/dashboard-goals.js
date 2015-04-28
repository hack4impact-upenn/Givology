$(document).ready(function() {

	var dollar_switch = 0;
	var hours_switch = 0;
 

 	var dollars_goal = 100; // HARD CODED FOR NOW

	// calculating goal bar widths
	var dollars_given_width = Math.min(total_dollars_given/dollars_goal * 365, 365);
	

	console.log(total_dollars_given);

	$("#dollar-met").attr("style", "width: " + dollars_given_width + "px");

	$("#dollar-met-text").html("$" + total_dollars_given);

	$("#dollars-toggle").html(

		"<img src=/images/goal-toggle-left.png>"
		
		);

	$("#hours-toggle").html(

		"<img src=/images/goal-toggle-left.png>"
		
		);

	$("#dollars-toggle").on("click", function() {

		dollar_switch = !dollar_switch;

		console.log("hellow");

		if (dollar_switch == 0) {
			$("#dollars-toggle").html(
				"<img src=/images/goal-toggle-left.png>"
			);
		}
		else {
			$("#dollars-toggle").html(
				"<img src=/images/goal-toggle-right.png>"
			);
		}
	});

	$("#hours-toggle").on("click", function() {

		hours_switch = !hours_switch;

		console.log("hellow");

		if (hours_switch == 0) {
			$("#hours-toggle").html(
				"<img src=/images/goal-toggle-left.png>"
			);
		}
		else {
			$("#hours-toggle").html(
				"<img src=/images/goal-toggle-right.png>"
			);
		}
	});
 
 });