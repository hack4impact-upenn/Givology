/* Author: Jeffrey Pia */

/* Global variable used for Highcharts */
var chart;

(function($){
	
	// Structuring elements with non-semantic markup for presentational purposes
	$('.section-heading').addClass('structured').wrapInner('<span />');
	$('body > header, #container, body > footer').wrapInner('<div class="inner" />');
	$('body > footer').addClass('structured').wrapInner('<div />');
	$('.button').addClass('structured').wrapInner('<span />');
	$('.widget .widget-title, #banner .widget-title').addClass('structured').wrapInner('<span />');

	$('#container .widget-content').before('<div class="widget-top" />').after('<div class="widget-bottom" />').parent().addClass('structured');

	$('.modal').prepend('<div class="modal-top" />').append('<div class="modal-bottom" />').addClass('structured');

	// Add even/odd row classes for IE
	$('.lt-ie9 .executive-team #content-main .article-content > ul li:nth-child(2n+1)').addClass('odd');

	// Add hover functionality to home page banner
	var bannerHalfwayMark = Math.round( $('#banner > ul > li').length / 2 );
	$('#banner > ul > li').each(function(i){
		if(i+1 > bannerHalfwayMark){
			$(this).addClass('popup-left');
		}
	}).hover(function(){
		$(this).addClass('hover');
	}, function(){
		$(this).removeClass('hover');
	});
	
	// Tabs on Dashboard
	$('.actions-filter li a').click(function(e){
		console.log($(this))
		if($(this).attr('actionchoice') === 'true'){
			e.preventDefault();
			$this = $(this).parent();
			$this.addClass('active').siblings().removeClass('active').closest('.widget-content').find('.actions-tabs li').eq( $this.index() ).addClass('active').siblings().removeClass('active');
		}
	});
	
	// Structure progress bar
	$('.progress').each(function(){
		$this = $(this);
		raised = $this.attr('data-raised');
		needed = $this.attr('data-needed');
		given = $this.attr('data-given');
		createProgressBar(raised,needed,$this,given);
	})
	
	// Add unique classes for each of the items on the media page for more effective css targetting, and adding extra markup for presentational purposes (play button)
	$('.media-items li').each(function(){
		var $this = $(this);
		$this.addClass('media-item-' + ( $this.index() +1 ) );
	}).find('.media-thumb a').append('<span class="play" />').parents('.media-items').addClass('structured');

	// Adding selected class for radio buttons in Create a Gift Card section to support styling in ie7-8
	$('#create-gift-card label').click(function(e){
		e.preventDefault();
		$(this).find('input[type="radio"]').attr('checked',true).closest('li').addClass('selected').siblings().removeClass('selected');
	});
	
	// Destroy filter result on click
	$('.filter-results a').click(function(e){
		e.preventDefault();
		var $this = $(this);
		if ( $this.parent().siblings().length == 0 ) {
			$this.closest('.filter-results').addClass('empty');
		}
		$this.parent().remove();
	});

	// Place label copy inside text inputs
	$('.profile-listing .profile-search label, #search label').inFieldLabels();

	// Structure selects for custom styling
	$('select:not(.uform-select)').styledSelect();

	// Structure checkboxes for custom styling
	$('input[type=checkbox]').wrap(function() {
		return ($(this).is(':checked')) ? '<div class="custom_checkbox selected" />' : '<div class="custom_checkbox" />';
	}).click(function () {
	    $(this).parent().toggleClass('selected');
	});

	// Add date-picker functionality
	$('#volunteering-field-date').datepick();

	// Structure File Upload button for custom styling and bind events to launch file upload window and capture file name
	$('.img-upload-preview input[type="file"]').change(function(){
		$this = $(this);
		var fileName = $this.val();
		if ( fileName ){
			if (navigator.userAgent.indexOf("Firefox")!=-1) {
				$this.siblings('input[type="text"]').val(fileName);
			} else {
				$this.siblings('input[type="text"]').val(fileName.substr(12));
			}
			$this.parent().addClass('file-present')
		} else {
			$this.parent().removeClass('file-present')
		}
	}).after('<img src="" width="162" height="92" alt="placeholder" /><a href="#" class="button structured"><span>Choose a file &hellip;</span></a><input type="text" />').parent().on('click', 'a' , function(e){
		e.preventDefault();
		$(this).siblings('input[type="file"]').trigger('click');
	}).on('focus', 'input[type="text"]', function(){
		$this = $(this);
		if( $this.siblings('input[type="file"]').val() == "" ) {
			$this.siblings('input[type="file"]').trigger('click');
		}
	});

	// View More / Less content on profile-detail page
	$('.profile-element.profile .view-more').click(function(e){
		e.preventDefault();
		$this = $(this);
		$profile = $this.closest('.profile');

		$(this).hide().next().show();
		$profile.find('p:not(:first-child)').slideDown();
	});
	$('.profile-element.profile .view-less').click(function(e){
		e.preventDefault();
		$this = $(this);
		$profile = $this.closest('.profile-element');

		$(this).hide().prev().show();
		$profile.find('p:not(:first-child)').slideUp();
	});

	$('.profile-element').find('.view-more').click(function(e){
		e.preventDefault();
		$this = $(this);
		$profile = $this.closest('.profile-element').children('ul');

		$(this).hide().next().show();
		$profile.find('li:gt(1)').slideDown();
	});
	$('.profile-element').find('.view-less').click(function(e){
		e.preventDefault();
		$this = $(this);
		$profile = $this.closest('.profile-element').children('ul');

		$(this).hide().prev().show();
		$profile.children('li:gt(1)').slideUp();
	});

	// View More / Less content on executive-team page
	$('.executive-bio .view-more').click(function(e){
		e.preventDefault();
		$this = $(this);
		$profile = $this.closest('.executive-bio');

		$profile.addClass('expanded').find('p:not(:first-child)').slideDown(500, "swing");
	})
	$('.executive-bio .view-less').click(function(e){
		e.preventDefault();
		$this = $(this);
		$profile = $this.closest('.executive-bio');

		$profile.find('p:not(:first-child)').slideUp(500, "swing", function() {
			$profile.removeClass('expanded')
		});
	})

	// Share popup
	$('#share').hover(function(){
		$(this).addClass('hover');
	}, function(){
		$(this).removeClass('hover');
	});

	// Modals	
	$('#modal-overlay, .modal-close').click(function(e){
		e.preventDefault();
		
		$('#modal-overlay, .modal').fadeOut();
		$('#modal-iframe').attr('src','');
	});
	
	// Video modal
	$('.media-videos .media-items a').click(function(e){
		e.preventDefault();

		$('#modal-iframe').attr('src','http://www.youtube.com/embed/' + $(this).attr('data-vidID') + '?wmode=opaque');
		$('#modal-title').text($(this).closest('article').find('.media-title').text());
		$('#modal-meta').text($(this).closest('article').find('.media-meta').text());

		$('#modal-overlay').fadeIn(500,function(){
			$('#modal-video').fadeIn().css('margin-top', -( Math.round( $('#modal-video').height() / 2) ));
		});
	});

        // Photo modal
	//$('.media-photos .media-items a').click(function(e){
	//	e.preventDefault();
		//alert('This should launch Flickr Galleria plugin modal once Flickr galleries are set up')
                
	//});
    
    window.activate_login_modal = function() {
	$('#modal-overlay').fadeIn(500,function(){
	    $('#modal-login').fadeIn().css('margin-top', -( Math.round( $('#modal-login').height() / 2) ));
	});
    }

	// Login modal
	$('#login').click(function(e){
		e.preventDefault();
            window.activate_login_modal();
	});

	// Delete Member modal
	$('#modal-delete-member .button').click(function(e){
		e.preventDefault();
		
		// If Yes button is clicked, close the modal and remove the member from the list; else just close the modal
		if( $(this).hasClass('delete-confirmed') ){
			$('#modal-overlay, .modal').fadeOut(function(){
				$('#delete-me').slideUp(500, "swing", function(){
					$(this).remove();
				});
			});
		} else {
			$('#modal-overlay, .modal').fadeOut(function(){
				$('#delete-me').attr('id', '');
			});
		}
	});

	// Carousels
	$('#featured-items').bjqs({
		'width' : 272,
		'height' : 263,
		'animation': 'slide',
		'automatic': false,
		'showControls' : true
	});
	$('#card-carousel').bjqs({
		'width' : 850,
		'height' : 268,
		'animation': 'slide',
		'automatic': false,
		'showControls' : true
	});

	// Construct chart for Teams profile page
	if ( $('#total-team-donation').length ) {
		chart = new Highcharts.Chart({
			chart: {
				plotBorderWidth: 1,
				renderTo: 'total-team-donation',
				type: 'line'
			},
			colors: [
				'#3ab4db'
			],
			credits: {
				enabled: false
			},
			legend: {
				enabled: false
			},
			xAxis: {
				categories: ['Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul']
			},
			yAxis: {
				labels: {
                	formatter: function() {
                    	return '$' + this.value;
                	}
                },
                min: -5,
				plotLines: [{
					value: 0,
					width: 1
				}],
				showFirstLabel: false,
				showLastLabel: false,
				tickInterval: 50000,
				title: {
					text: ''
				}
			},
			title: {
				text: ''
			},
			tooltip: {
				formatter: function() {
						return '$' + this.y;
				}
			},
			series: [{
				name: 'Team Donation',
				data: [1000, 5000, 20000, 80000, 150000, 200240]
			}]
		});
	}

	// Construct chart for Dashboard
	if ( $('#total-hours-donated').length ) {
		chart = new Highcharts.Chart({
			chart: {
				plotBorderWidth: 1,
				renderTo: 'total-hours-donated',
				type: 'line'
			},
			colors: [
				'#3ab4db'
			],
			credits: {
				enabled: false
			},
			legend: {
				enabled: false
			},
			xAxis: {
				categories: ['Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul']
			},
			yAxis: {
                min: -5,
				plotLines: [{
					value: 0,
					width: 1
				}],
				showFirstLabel: false,
				showLastLabel: false,
				tickInterval: 20,
				title: {
					text: ''
				}
			},
			title: {
				text: ''
			},
			tooltip: {
				formatter: function() {
						return this.y + 'hrs';
				}
			},
			series: [{
				name: 'Team Donation',
				data: [5, 10, 20, 40, 80, 100]
			}]
		});
	}

	// Edit button pseudo-functionality

	// Open File Upload box for iamge thumbnails
	/*$('.widget.actions .profile-thumb .edit, .widget.profile-info .widget-content .edit').after('<input type="file" />').click(function(e){
		e.preventDefault();
		$(this).next('input[type="file"]').trigger('click');
	});*/
	
	// Make Profile content area editable
	$('.profile-element.profile .edit').click(function(e){
		e.preventDefault();
		var $container = $(this).closest('.profile-element').find('.article-content');

		$container.replaceWith( $("<textarea />").blur(function() {
		    $(this).replaceWith( $('<div class="article-content" />').html( $(this).val() ) );
		}).val($container.html()) );
		
	});

	// Delete member from member listing page
	$('.profile-element.donors .delete').click(function(e){
		e.preventDefault();

		// Tag list item targetted for deletion and launch confirmation modal
		$(this).closest('li').attr('id', 'delete-me');
		$('#modal-overlay').fadeIn(500,function(){
			$('#modal-delete-member').fadeIn().css('margin-top', -( Math.round( $('#modal-delete-member').height() / 2) ));
		});
	});

})(jQuery);

// Create Progress Bars
function createProgressBar(amountRaised, amountNeeded, target, amountGiven) {
	var raised = Math.round(amountRaised.replace(',', ''));
	var needed = Math.round(amountNeeded.replace(',',''));
	var percentage = Math.round(raised/needed*100);
	target.append('<span class="progress-total-bar"><span class="progress-current-bar"><span class="progress-current-amount"></span></span></span>'+'<span class="progress-total-amount">$'+amountNeeded+'</span>')

	var progressBar = target.find( $(".progress-current-bar") );
	var progressBarText = target.find( $(".progress-current-amount") );
	progressBarText.hide();
	progressBarText.html("$"+amountRaised);
	
	if (percentage < 10 && percentage != 0) {
			progressBar.delay(1000).animate({ width: "10%" }, 2000, "swing", function() {
				progressBarText.fadeIn(500);																								  
			});
	} else if(percentage == 0) {
			progressBarText.css("position", "absolute");
			progressBarText.css("left", "10px");
			progressBarText.css("top", "1px");
			progressBarText.css("color", "#646464");
			progressBar.delay(1000).animate({ width: percentage+"%" }, 2000, "swing", function() {
				progressBarText.fadeIn(500);
			});
	} else if (percentage >= 100) {
		progressBarText.html("100%");
		progressBar.delay(1000).animate({width: "100%"}, 2000, "swing", function() {
			progressBarText.fadeIn(500);
		});
	}	else {
		progressBar.delay(1000).animate({ width: percentage+"%" }, 2000, "swing", function() {
			progressBarText.fadeIn(500);																									  
		});
	}
	if (amountGiven){
		var given = Math.round(amountGiven.replace(',', ''));
		var impact = Math.round(given / needed * 100);
		progressBar.after('<span class="progress-given-bar" />').next().delay(1000).animate({ width: impact+"%" }, 2000, "swing");
	}
}
