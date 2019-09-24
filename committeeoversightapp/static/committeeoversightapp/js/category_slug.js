$(function() {
  $('#id_category').on('change', function() {
      var value = this.value;
      var newSlug = "category-" + value;
      var newSeoTitle = "Category " + value;
      $('#id_slug').val(newSlug);
      $('#id_seo_title').val(newSeoTitle);
  });
});

// Use the correct jQuery to hook into the committee Select2 widget via Django
// https://github.com/yourlabs/django-autocomplete-light/issues/793#issuecomment-273765174
try {
  (function($){
    $(document).ready(function () {
      $('#id_committee').on('select2:select', function(e) {
        var title = e.params.data.text;
        $('#id_seo_title').val(title);
      });
    });
  })(django.jQuery);
} catch (err) {
  if ( err.message.indexOf('django is not defined') < 0 ) {
    console.error(err);
  } else {
    console.log('Did not find django.jQuery, skipping autocomplete listener')
  }
}
