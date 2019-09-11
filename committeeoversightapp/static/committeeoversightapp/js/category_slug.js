$(function() {
  $('#id_detail_object').on('change', function() {
      var value = this.value;
      var newSlug = "category-" + value;
      var newSeoTitle = "Category " + value;
      $('#id_slug').val(newSlug);
      $('#id_seo_title').val(newSeoTitle);
  });
});
