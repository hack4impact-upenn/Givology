$(document).ready(function() {

	$('#carousel').rcarousel({
		width: 100,
		height: 100,
		orientation: "vertical",
		navigation: {
			next: "#scroll-up",
			prev: "#scroll-down"
		},
		step: 1,
		margin: 10
	});

	$('#carousel2').rcarousel({
		width: 100,
		height: 100,
		orientation: "vertical",
		navigation: {
			next: "#scroll-up2",
			prev: "#scroll-down2"
		},
		step: 1,
		margin: 10
	});
});