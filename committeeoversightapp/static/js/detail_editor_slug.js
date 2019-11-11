$(function() {
  $('#id_category').on('change', function() {
      var text = this.options[this.selectedIndex].text;
      var text_slug = slugify(text)

      var newSlug = "category-" + text_slug;
      var newSeoTitle = "Category: " + text;

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
        // Mimic the functionality of CommitteeOrganization.url
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

  // taken from https://gist.github.com/mathewbyrne/1280286
  // to match Django slugify
  function slugify(text) {
    return text.toString().toLowerCase()
      .replace(/\s+/g, '-')           // Replace spaces with -
      .replace(/[^\w\-]+/g, '')       // Remove all non-word chars
      .replace(/\-\-+/g, '-')         // Replace multiple - with single -
      .replace(/^-+/, '')             // Trim - from start of text
      .replace(/-+$/, '');            // Trim - from end of text
  }
