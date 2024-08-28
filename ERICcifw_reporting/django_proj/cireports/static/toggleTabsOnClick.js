$(document).ready(function() {
    openItem("packages")
    function openItem(name) {
        var i, tabcontent, tablinks;
        tabcontent = document.getElementsByClassName("tabcontent");
        for (i = 0; i < tabcontent.length; i++) {
            tabcontent[i].style.display = "none";
        }
        tablinks = document.getElementsByClassName("tablinks");
        for (i = 0; i < tablinks.length; i++) {
            tablinks[i].className = tablinks[i].className.replace(" active", "");
        }
        document.getElementById(name).style.display = "block";
        document.getElementById(name + "-tab").className += " active";
    }

    $("#packages-tab").click(function() {
        openItem("packages");
    });
    $("#testware-tab").click(function() {
        openItem("testware");
    });
});
