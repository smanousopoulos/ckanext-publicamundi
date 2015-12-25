"use strict"; 

ckan.module('dataset-rating', function($, _) {
    return {
        initialize: function() {
            var console = window.console;
            var debug = $.proxy(console, 'debug');
            $.proxyAll(this, /_on/);
            
            this.rating = parseInt(this.options.rating);
            this.name = this.options.pkg_name;
            this.stars = $(this.el).find('a');
            
            for (var i=1; i<=5; i++) {
                if (i<=this.rating){
                    this.status.push('icon-star');
                }
                else{
                    this.status.push('icon-star-empty');
                }
            }
            this.effectInitialization();

            $(this.stars).on('click', this._onClick);
            
            
        },
        stars : null,
        status: [],
        effectInitialization: function() {
            var self = this;
            $(this.stars).each(function(idx) {
                $(this).on('mouseenter', function(e) {
                    self.rating = parseInt($(this).data('rating'));
                    $(self.stars).each(function(idx2) {
                        var icon = $(this).children()[0];
                        if (idx2 <= idx){
                            $(icon).removeClass();
                            $(icon).addClass('icon-star');
                        }
                        else{
                            $(icon).removeClass();
                            $(icon).addClass('icon-star-empty');
                        }
                    });
                });
                
            });
            $(this.el).on('mouseleave', function(e) {
                $(self.stars).each(function(idx) {
                    var icon = $(this).children()[0];
                    $(icon).removeClass();
                    $(icon).addClass(self.status[idx]);
                })
            });

        },
        _onClick: function(event) {
            var self= this;
            var res = this.sandbox.client.call('POST', 'rating_create', {'package':this.name, 'rating':this.rating} , function(json) { 
                if (json.success == true){
                    $('#rating-count').text(json.result['rating count']);
                    $('#rating-average').text(json.result['rating average']);
                    self.update_status();
                }

            });            
        },
        update_status: function(){
            var self = this;
            var rating_avg = parseFloat($('#rating-average').text());
            this.stars.each(function(idx){
                var icon = $(this).children()[0];
                $(icon).removeClass();
                var curr_rating = parseInt($(this).data('rating'));
                if (curr_rating <= rating_avg){
                    $(icon).addClass('icon-star');
                }
                else if ((curr_rating > rating_avg) && (curr_rating <= (rating_avg + 0.5))){
                    $(icon).addClass('icon-star-half-full');
                }
                else{
                    $(icon).addClass('icon-star-empty');
                }
                self.status[idx]= $(icon).attr('class');
            });
            
        },

}
});
