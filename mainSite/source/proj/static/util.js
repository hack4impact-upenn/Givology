var shorten_string = function(str, len) {
    var words = str.split(/\s+/);
    var i;
    var word_length;
    
    var short_str = words[0];
    var length_so_far = short_str.length;

    for (i = 1; i < words.length; i++) {
        word_length = words[i].length;

        if ( length_so_far + word_length + 1 > len - 4) {
            return (short_str + ' ...');
        }

        short_str += ' ' + words[i];
        length_so_far += 1 + word_length;
    }

    return short_str;
}
