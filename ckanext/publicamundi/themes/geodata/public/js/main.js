this.ckanext || (this.ckanext = {})
this.ckanext.publicamundi || (this.ckanext.publicamundi = {})

jQuery(document).ready(function ($) {
    
    var console = window.console
    var debug = $.proxy(console, 'debug') 
    
    init();
});

function init() {

    var obj = $('.nav-pills > li > a[href$="/group"]');
    
    // Mouse enter and leave listeners on groups button
    obj.on('mouseenter', function(){
        $('#menu-block').addClass('enabled');
        $('#menu-block-home').addClass('enabled');
        obj.parent().addClass('painted');
    });
    obj.on('mouseleave', function(){
        $('#menu-block').removeClass('enabled');
        $('#menu-block-home').removeClass('enabled');
        obj.parent().removeClass('painted');
    });

    // Add listeners also on menu itself to keep it enabled
    $('#menu-block').on('mouseenter', function(){
        $('#menu-block').addClass('enabled');
        obj.parent().addClass('painted');
    });
    $('#menu-block').on('mouseleave', function(){
        $('#menu-block').removeClass('enabled');
        obj.parent().removeClass('painted');
    });
    $('#menu-block-home').on('mouseenter', function(){
        $('#menu-block-home').addClass('enabled');
        obj.parent().addClass('painted');
    });
    $('#menu-block-home').on('mouseleave', function(){
        $('#menu-block-home').removeClass('enabled');
        obj.parent().removeClass('painted');

    });

    //Upload button hover
    $('.image-upload input[type="file"]').on('mouseenter', function(){
        $(this).parent().find('.btn:first').addClass('btn-hover');
    });

    $('.image-upload input[type="file"]').on('mouseleave', function(){
        
        $(this).parent().find('.btn:first').removeClass('btn-hover');
    });

    // Detect OS for applying OS-specific styles
    
    var os = navigator.platform;
    console.log('Detected platform: ' + os);
    if (os.indexOf('Linux') == 0) {
        $('head').append('<link rel="stylesheet" href="/css/linux-override.css" type="text/css" />');
    }

    //Breadcrumbs auto hide all but last element
    var bread_items = $('.breadcrumb li:first').next().nextAll();
    bread_items = bread_items.not(':last');

    bread_items.each(function(idx) {
        $(this).addClass('breadcrumb-hide-text');
    });
       
    var toolbar = $('.toolbar');
    toolbar.on('mouseenter', function(){
        bread_items.each(function(idx) {
            $(this).removeClass('breadcrumb-hide-text');
        });
    });

    toolbar.on('mouseleave', function(){
        bread_items.each(function(idx) {
            $(this).addClass('breadcrumb-hide-text');
        });
    });

}
