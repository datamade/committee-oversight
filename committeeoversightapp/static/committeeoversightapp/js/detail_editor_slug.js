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
        // Mimic the functionality of CommitteeOrganization.url_id
        // ocd-organization/80b44839-0c06-4569-9337-4dda052f5cd5 => committee-80b44839-0c06-4569-9337-4dda052f5cd5
        var slug = 'committee-' + e.params.data.id.split('/')[1];
        var title = e.params.data.text;
        $('#id_slug').val(slug);
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