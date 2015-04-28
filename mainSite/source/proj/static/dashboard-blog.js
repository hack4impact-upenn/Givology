$(document).ready(function() {

	$("#volunteer-hours-form").submit(function(event) {
		event.preventDefault();
		var volunteerHours = $( "#volunteering-hours option:selected" ).val();
		var volunteerActivity = $( "#volunteering-activity option:selected" ).val(); 
		var now = new Date();

		$.ajax({
			url: "/save/",
			type: "POST",
			data: {
				volunteer_hours: volunteerHours, 
				volunteer_activity: volunteerActivity
			},
			success: function(response) {
				console.log(response);
				if (response != 'failed') {
					var month = now.getMonth() + 1;
					var date = now.getDate();
					var year = String(now.getFullYear()).substring(2, 4);
					console.log(year);
					var newHtml = 
					"<tr class='volunteering-row'>" + 
					"<td class='volunteer-text volunteer-date'>" + 
					month + "." + date + "." + year + 
					"</td>" + 
					"<td class='volunteer-text'>" + 
					"<div class='volunteer-minutes'>" + volunteerHours + " minutes</div> volunteering by " + '<div class="volunteer-activity">' + volunteerActivity + "</div>" + 
					"</td>" + 
					"</tr>"; 
					$("#blog-title").after(newHtml);
				} 
			},
			error: function(jqXHR, textStatus, errorThrown) {
				console.log(textStatus, errorThrown);
			}
		});
		return false; 
	});

});