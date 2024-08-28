$(document).ready(function() {

    var url = document.URL;
    var drop = url.split('/').filter(function (s) { return !!s }).pop();

    //Button to export to csv
    $(".export").on('click', function (event) {
        ExportToCsv('Buildlog '+drop, 'buildLogTable');
        return true;
    });

    function ExportToCsv(fileName, tableName) {
      var data = GetCellValues(tableName);
      var csv = ConvertToCsv(data);
      if (navigator.userAgent.search("Trident") >= 0) {
        window.CsvExpFrame.document.open("text/html", "replace");
        window.CsvExpFrame.document.write(csv);
        window.CsvExpFrame.document.close();
        window.CsvExpFrame.focus();
        window.CsvExpFrame.document.execCommand('SaveAs', true, fileName + ".csv");
      } else {
        var uri = "data:text/csv;charset=utf-8," + escape(csv);
        var downloadLink = document.createElement("a");
        downloadLink.href = uri;
        downloadLink.download = fileName + ".csv";
        document.body.appendChild(downloadLink);
        downloadLink.click();
        document.body.removeChild(downloadLink);
      }
    };

    function GetCellValues(tableName) {
      var table = document.getElementById(tableName);
      var tableArray = [];
      var str = 'save', replacement = '';
      
      for (var r = 0, n = table.rows.length; r < n; r++) {
        tableArray[r] = [];
        for (var c = 0, m = table.rows[r].cells.length; c < m; c++) {
          var text = table.rows[r].cells[c].textContent || table.rows[r].cells[c].innerText;
          text = text.replace(/Save(?![\s\S]*Save)/, '');
          text = text.replace(/Cancel(?![\s\S]*Cancel)/, '');
          tableArray[r][c] = text.trim();
        }
      }
      return tableArray;
    }

    function ConvertToCsv(objArray) {
      var array = typeof objArray != "object" ? JSON.parse(objArray) : objArray;
      var str = "sep=,\r\n";
      var line = "";
      var index;
      var value;
      for (var i = 0; i < array.length; i++) {
        line = "";
        var array1 = array[i];
        for (index in array1) {
          if (array1.hasOwnProperty(index)) {
            value = array1[index] + "";
            line += "\"" + value.replace(/"/g, "\"\"") + "\",";
          }
        }
        line = line.slice(0, -1);
        str += line + "\r\n";
      }
      return str;
    };

});