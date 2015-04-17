/**
 *  https://github.com/PowerKiKi/ie_expand_select_width
 */
(function( $ ){ 
	"use strict";

	$.fn.ieExpandSelectWidth = function() {
		this.filter('select')
		.bind('mouseenter focus',function(event){
			open($(this), event.type == 'mouseenter');
		});

		return this;
	};
	
	/**
	 * Open the expanded select
	 * @param select jQuery object for the original select element
	 * @param openedViaMouse boolean whether the open was initiated via mouse or keyboard
	 */
	function open(select, openedViaMouse)
	{
		// Allow only one clone for one select to be opened at any given time
		// and only select in 'single choice' mode
		if ($.data(document.body, 'ie_expand_select_width_lock')
			|| select.data('ie_expand_select_width_clone')
			|| select.attr('multiple')
			|| select.attr('size') > 1
			|| select.data('ie_expand_select_width_ignore'))
		{
			return;
		}
		$.data(document.body, 'ie_expand_select_width_lock', true);

		// Clone the select to keep the layout intact
		var selectClone = select.clone();
		selectClone.val(select.val());
		select.data('ie_expand_select_width_clone', selectClone);
		
		var style = getComputedStyleMap(select);
		style['min-width'] = select.width(); // Cannot be shorter than current width
		style['max-width'] = 'none'; // Can be as long as it needs to be
		style['width'] = 'auto';
		style['z-index'] = 9999; // be sure it's always on top of everything else
		selectClone.css(style);

		// Insert the clone at the very end of document, so it does not break layout
		selectClone.appendTo('body');
		
		// If the clone is actually shorter than original, cancel everything and 
		// never expand this select anymore
		if (selectClone.width() <= select.width())
		{
			select.data('ie_expand_select_width_ignore', true);
			$.data(document.body, 'ie_expand_select_width_lock', false);
			close(select, selectClone);
			return;
		}
		
		// Move the clone as an overlay on top of the original
		reposition(select, selectClone);
		
		if (!openedViaMouse)
		{
			selectClone.focus();
		}
		
		// Bind events to close
		selectClone
		.bind('keydown keyup', function(event){
			selectClone.data('ie_expand_select_width_key_is_down', event.type == 'keydown');
		})
		.bind('mousedown mouseup', function(event){
			selectClone.data('ie_expand_select_width_mouse_is_down', event.type == 'mousedown');
		})
		.bind('blur', function(){
			close(select, selectClone);
		})
		.bind('change', function(){
			// Only close if the change was made via mouse
			if (!selectClone.data('ie_expand_select_width_key_is_down'))
				close(select, selectClone);
		});

		// Only close if we are doing a simple hover and not an a choice in a expanded select
		if (openedViaMouse)
		{
			selectClone.bind('mouseleave', function() {
				if (!selectClone.is(':focus'))
					close(select, selectClone);
			});
		}
		
		$(window).bind('resize.ie_expand_select_width', function() { reposition(select, selectClone); });
		
		// Remember we are the last select to have been cloned
		$.data(document.body, 'ie_expand_select_width_last_select', select);

		$.data(document.body, 'ie_expand_select_width_lock', false);
	}

	/**
	 * Close the expanded select
	 * @param select jQuery object for the original select element
	 * @param selectClone jQuery object for the cloned select element
	 */
	function close(select, selectClone)
	{
		if (!selectClone || $.data(document.body, 'ie_expand_select_width_lock'))
		{
			return;
		}
		
		// Update value if different
		var cloneValue = selectClone.val();
		if (cloneValue != select.val())
			select.val(cloneValue).change();
		
		selectClone.remove();
		select.data('ie_expand_select_width_clone', null);
		
		// If we are closing because another select opened, then we need
		// to reposition that second select's clone after destroying our clone
		var lastSelect = $.data(document.body, 'ie_expand_select_width_last_select');
		if (lastSelect)
		{
			var lastSelectClone = lastSelect.data('ie_expand_select_width_clone');
			reposition(lastSelect, lastSelectClone);
		}
		
		$(window).unbind('resize.ie_expand_select_width');
	}
	
	/**
	 * Reposition clone on top of its original
	 * @param select jQuery object for the original select element
	 * @param selectClone jQuery object for the cloned select element
	 */
	function reposition(select, selectClone)
	{
		if (!select || !selectClone)
			return;
		
		// Move the clone as an overlay on top of the original
		selectClone.position({
			my : 'left',
			at : 'left',
			of : select,
			collision: 'none'
		});
	}
	
	/**
	 * Returns a map of computed CSS style for the fiven element
	 * Highly inspired from http://stackoverflow.com/a/6416477/37706
	 */
	function getComputedStyleMap(element) {
		var dom = element.get(0);
		var style;
		var result = {};
		if (window.getComputedStyle) {
			style = window.getComputedStyle(dom, null);
			for (var i = 0; i < style.length; i++) {
				var prop = style[i];
				result[prop] = style.getPropertyValue(prop);
			}
		}
		else if (dom.currentStyle) {
			style = dom.currentStyle;
			for(var prop in style) {
				result[prop] = style[prop];
			}
		}
		
		return result;
	}
	
})( jQuery );