var sortTable = function(){
    var blocks = 3, digits = 3;
    $.tablesorter.addParser({
              id: "versions",
              is: function (s) {
              return false;
      },

    format: function (s, table) {
              var i,
              version_Split_Array= s ? s.split(".") : [],
              r = "",
              d = new Array(digits + 1).join('0');

              if (version_Split_Array.length==1){
                    var array_Value = version_Split_Array[0];
                    array_Value = array_Value.split("-")[0];
                    version_Split_Array[0] = array_Value;
                    version_Split_Array[1] = version_Split_Array[2] = "0";
              };

              if (version_Split_Array.length==2){
                    var array_Value = version_Split_Array[1];
                    array_Value = array_Value.split("-")[0];
                    version_Split_Array[1] = array_Value;
                    version_Split_Array[2] = "0";
              };

              if (version_Split_Array.length>=3){
                    var array_Value = version_Split_Array[2];
                    array_Value = array_Value.split("-")[0];
                    version_Split_Array[2] = array_Value;
              };

              for (i = 0; i < blocks; i++) {
                  r += (d + (version_Split_Array[i] || 0)).slice(-digits);
              }

              return s ? $.tablesorter.formatFloat(r, table) : s;
            },
                type: "numeric"
    });

    var inner = {};
    $('table tr th').each(function(index) {
            var value = $(this).text();
            if (value == "Version"){
                  inner[$('table th').index(this)] = {sorter : "versions"}
            }

            if(value == "Media Category"){
                  inner[$('table th').index(this)] = {sorter : "text"}
            }

            if (value == "Delivered To"){
                  inner[$('table th').index(this)] = {sorter : "versions"}
            }
        });
    $("table").tablesorter({headers:inner});
};

