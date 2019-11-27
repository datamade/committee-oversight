// This DataTables sort function for letter grades relies on the insight from
// https://stackoverflow.com/a/58065608 that ',' is between '+' and '-' in
// the ASCII table. This sort appends ',' to any grade without a sign and then
// sorts normally

addCommaIfUnsigned = function(grade) {
    var last_char = grade.substr(-1)
    if (last_char != "-" && last_char != "+") {
      grade += ','
    }
    return grade
}

gradeSort = function(a, b) {
    a = addCommaIfUnsigned(a)
    b = addCommaIfUnsigned(b)
    return ((a < b) ? -1 : ((a > b) ? 1 : 0));
}

jQuery.extend( jQuery.fn.dataTableExt.oSort, {
    "grade-sort-asc": function ( a, b ) {
        return gradeSort(a, b);
    },

    "grade-sort-desc": function ( a, b ) {
        return gradeSort(a, b) * -1;
    }
} );
