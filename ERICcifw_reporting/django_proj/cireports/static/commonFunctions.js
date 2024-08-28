function createTableRowContent(rowObject, data, cellType){
    var rowContent = document.createElement(cellType);
    var cell = document.createTextNode(data);
    rowContent.appendChild(cell);
    rowObject.appendChild(rowContent);
}


function createTableData(rowObject, data){
    createTableRowContent(rowObject, data, 'td');
}

function createTableHeader(rowObject, data){
    createTableRowContent(rowObject, data, 'th');
}

function checkAction(msg, link) {
    var go = confirm(msg);
    if (go == true) {
        window.location = link;
    }
}

function createTableRowLink(rowObject, var1,href, txt){
    var rowContent = document.createElement('td');
    var link = document.createElement("a");
    link.setAttribute("href", href+var1)
    var linkText = document.createTextNode(txt);
    link.appendChild(linkText);
    rowObject.appendChild(link);
}

function askUser(rowObject,option,ID,question,url){
    var td = document.createElement("td");
    td.innerHTML =  option;
    td.addEventListener("click", function() {
        checkAction(question,url);
    });
    rowObject.appendChild(td);
}
function loadingBodyNormal(json){
    var jsondoc = eval('(' + json + ')');
    if(jsondoc.data.length > 0){
        displayData(jsondoc);
    }
    else{
        document.getElementById('mytable').innerHTML='No records found!';
    }
}

