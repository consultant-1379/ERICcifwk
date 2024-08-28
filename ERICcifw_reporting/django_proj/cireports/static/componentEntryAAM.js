$(document).ready(function () {
    var product = $('#hidden_product_div').html();
    $('#dialog-alert').dialog({'autoOpen':false});
    $('#confirm-dialog').dialog({'autoOpen':false});
    var options_select_box = $('#options');

    var labels_names = [];
    var labels_select_box = $('#labels');
    function populate_labels_select(labels){
    if (!labels){
         labels_select_box.append('<option value="0" disabled>Loading...</option>');
         $.ajax({
            url: "/"+ product +"/getProductLabels/.json/",
            dataType: "json",
            success: function (json) {
                labels_select_box.empty();
                $.each(json.Label, function (i, item) {
                    labels_select_box.append('<option value="' + item.name + '" id="' + item.name + '">' + item.name + '</option>');
                    labels_names.push(item.name);
                });
                labels_select_box.prop("disabled", false);
                $("#labels option:first").attr('selected','selected');
                $("#parentLabel").text("Select "  + $('#labels').val() + " from List:");
                populate_parents_select($('#labels').val());
            },

            error: function (xhr, textStatus, errorThrown) {
                genericDialog("Issue retrieving the "+ product +" Label list: " + (errorThrown ? errorThrown : xhr.status));
                return;
            }
        });
     }
    }
    $('#labels').change(function(){
        var $this = $(this);
        $("#parentLabel").text("Select "  + $('#labels').val() + " from List:");
        populate_parents_select($this.val());
    });

    var parentComponent_names = [];
    var parentComponent_select_box = $('#parentComponent');
    function populate_parents_select(label){
        $('#parentComponent').empty();
        $.ajax({
            url: "/"+ product +"/" +label+ "/getParentComponentsOfLabel/.json",
            dataType: "json",
            success: function (json) {
                parentComponent_names = [];
                    $.each(json.Parents, function (i, item) {
                        parentComponent_select_box.append('<option value="' + item.name + '" id="' + item.name + '">' + item.name + '</option>');
                        parentComponent_names.push(item.name);
                    });
                    parentComponent_select_box.prop("disabled", false)
                    $("#parentComponent option:first").attr('selected','selected');
                    getChildLabel($('#parentComponent').children('option:selected').val())
                    populate_children_select($('#parentComponent').children('option:selected').val());
            },
            error: function (xhr, textStatus, errorThrown) {
                genericDialog("Issue retrieving Parent Components associated with "+label+": " + (errorThrown ? errorThrown : xhr.status));
                return;
            }
        });
    }

    $('#parentComponent').change(function(){
        var $this = $(this);
        populate_children_select($this.val());

    });

    $('#packageType').change(function(){
        $('#packages').empty();
        loadProductPackageList();
    });

    var childComponent_names = [];
    var childComponent_select_box = $('#childComponent');
    function populate_children_select(parentComponent){
        $('#childComponent').empty();
        $.ajax({
            url: "/childComponentsInParentComponent/",
            dataType: "json",
            data: {"product": product,  "parentComponent": parentComponent},
            success: function (json) {
                $.each(json.ChildComponents, function (i, item) {
                    if (item === "None"){
                        childComponent_select_box.prop('disabled', true);
                    }
                    else{
                        childComponent_select_box.prop('disabled', false);
                    }

                    childComponent_select_box.append('<option class="' + parentComponent + '" value="' + item + '" id="' + item + '">' + item + '</option>');
                    childComponent_names.push(item);
                });
                displayOverview(parentComponent);
            },
            error: function (xhr, textStatus, errorThrown) {
                genericDialog("Issue retrieving childComponents associated with "+parentComponent+": " + (errorThrown ? errorThrown : xhr.status));
                return;
            }
        });
    }

    function getChildLabel(parentElement){
        $.ajax({
            url: "/"+ product +"/" +parentElement+ "/getChildLabelFromParentLabel/.json",
            dataType: "json",
            success: function (json) {
                    $.each(json.ChildLabel, function (i, item) {
                       $("#childLabel").text("Select "  + item.name + " from List:");
                    });
            },
            error: function (xhr, textStatus, errorThrown) {
                genericDialog("Issue getting child label associated with "+parentElement+": " + (errorThrown ? errorThrown : xhr.status));
                return;
            }
        });
    }

    parentComponent_select_box.change(getSelectedParentComponents);

    $('#options').change(function(){
          var parentComponent = "";
          var childComponent = "";
          if ($(this).children('option:selected').val() === "add") {
            loadProductPackageList();
            populate_labels_select($('#labels').index());
            return;
          } else if($(this).children('option:selected').val() === "remove") {
            $('#packages').empty();
            clearSelectedComponent();
            populate_labels_select($('#labels').index());
            return;
          }
    });
    $('#childComponent').change(function(){
        var parentValue = "";
        var childValue = "";
        if ($('#parentComponent').children('option:selected').val()) {
            if ($('#options').children('option:selected').val() == 'remove') {
                $('#packages').empty();
                parentValue = $('#parentComponent').children('option:selected').val();
                childValue = $('#childComponent').children('option:selected').val();
                getPackagesAssociatedWithComponent(parentValue, childValue);
            }
        } else{
            genericDialog("Please select a Parent Component from the list");
            return;
        }
    });

    $('#save_button').click(updateComponent);
    $('#clear_button').click(clearSelectedComponent);

    $('#parentComponent').click(function() {
        $('#parentComponent').css({"pointer-events": "none"});
        var promises = []
        $('#parentComponent option:selected').each(function(i){
            promises.push(populate_labels_select($(this).val()));
        });
        $.when.apply($,promises).then(function(json) {
            $('#parentComponent').css({"pointer-events": "auto"});
        });
    });
    $("#allpackages").change(searchAllPackages);
    $("#packages").change(uncheckAllPackages);

    var packages_select_box = $('#packages');
    var childComponent_select_box = $('#childComponent');


    function getSelectedParentComponents() {
        $('#parentComponent option:not(:selected)').each(function () {
            $('#childComponent .' + $(this).text()).hide();
            $('#childComponent .' + $(this).text()).attr('disabled', 'disabled');
        });
        $('#parentComponent option:selected').each(function () {
            $('#childComponent .' + $(this).text()).show();
            $('#childComponent .' + $(this).text()).attr('disabled', false);
        });
        if ($("#allpackages").is(":checked")) {
            $('#packages option').prop('selected', false);
            $('#packages option:enabled').prop('selected', true);
        }else {
            $('#packages option').removeAttr('selected');
        }
    }

    function searchAllPackages() {
        if ($("#allpackages").is(":checked")) {
              $('#packages').attr('enabled', 'enabled');
              getSelectedParentComponents();
        } else {
            $('#packages').attr('disabled', 'disabled');
            $('#packages').removeAttr('disabled');
            getSelectedParentComponents();
        }
    }

    function uncheckAllPackages(){
    if ($('#allpackages').is(':checked')) {
            if ($('#packages option:selected')) {
                $('#allpackages').attr('checked', false);
            }
        }
    }

    function updateComponent() {
        var componentObj = new Object();
        var parentarr = [];
        var childarr = [];
        var packagearr = [];
        var componentResult = [];
        var result;

        $('#parentComponent option:selected').each(function () {
            componentObj.parent = $(this).text();
            parentarr.push($(this).text());
        });
        if (parentarr.length === 0) {
            genericDialog("Please select a Parent Component from the list");
            return;
        }

        $('#childComponent option:selected').each(function () {
            componentObj.child = $(this).text();
            childarr.push($(this).text());
        });
        if (childarr.length === 0) {
            genericDialog("Please select a Sub Component from the list");
            return;
        }

        $('#packages option:selected').each(function () {
            packagearr.push($(this).text());
        });
        if (packagearr.length === 0) {
            genericDialog("Please select a Package from the list or use Select All Packages checkbox");
            return;

        }
        componentObj.artifacts = packagearr;
        componentResult = JSON.stringify(componentObj);
        if ($('#options').children('option:selected').val() === "add") {
            genericConfirmDialog("Are you sure you want to save this Data to the CI Database",componentResult, "add");
        } else if ($('#options').children('option:selected').val() === "remove") {
            genericConfirmDialog("Are you sure you want to remove this Data from the CI Database",componentResult, "remove");
        }
    }

    function clearSelectedComponent(){
        uncheckAllPackages();
        $('#parentComponent option').removeAttr('selected');
        $('#childComponent option').removeAttr('selected');
        $('#packages option').removeAttr('selected');
    }

    function publishComponentData(componentResult) {
        $('#save_button').attr('disabled', 'disabled');
        $.ajax({
            type: "POST",
            url: "/"+ product +"/importComponents/",
            dataType: "html",
            data: {
                "componentResult": componentResult
            },
            success: function (html) {
                $('div#dynamic').html(html);
                $('#save_button').attr('disabled', false);
                genericDialog("Data Successfully Loaded into the CI Database");
                location.reload();
            },
            error: function (xhr, textStatus, errorThrown) {
                genericDialog("Could not publish to CI Database: " + (errorThrown ? errorThrown : xhr.status));
                return;
            },
            dataType: "json",
        });
    }

    function removeComponentData(componentResult) {
        $('#save_button').attr('disabled', 'disabled');
        $.ajax({
            type: "POST",
            url: "/"+ product +"/removeComponents/",
            dataType: "html",
            data: {
                "componentResult": componentResult
            },
            success: function (html) {
                $('div#dynamic').html(html);
                $('#save_button').attr('disabled', false);
                genericDialog("Data Successfully Removed from the CI DB");
                $('#options').val('#add');
                location.reload();
            },
            error: function (xhr, textStatus, errorThrown) {
                genericDialog("Could not publish to CI Database: " + (errorThrown ? errorThrown : xhr.status));
                return;
            },
            dataType: "json",
        });
    }

    function loadProductPackageList() {
        options_select_box.prop('disabled',true);
        $('div#loader').html('<img src = "/static/images/loader.gif" style="margin-top:32px; margin-left:150px;" width="150" height="100" alt="processing">');
        $.ajax({
            url: "/artifactsInProduct/",
            dataType: "json",
            data: {"product": product, "packageType": $('#packageType').val() },
            success: function (json) {
                options_select_box.prop('disabled',false);
                $('div#loader').html('');
                package_names = [];
                $.each(json.Packages, function (i, item) {
                    if (!$("#packages option[id='"+item+"']").length) {
                        packages_select_box.append('<option class="'+ product +'" value="' + item + '" id="' + item + '">' + item + '</option>');
                        package_names.push(item);
                    }
                });
            },
            error: function (xhr, textStatus, errorThrown) {
                genericDialog("Issue retrieving packages delivered to "+ product +": " + (errorThrown ? errorThrown : xhr.status));
                return;
            }
        });
    }

    function getPackagesAssociatedWithComponent(parentValue, childValue) {
        $('div#loader').html('<img src = "/static/images/loader.gif" style="margin-top:32px; margin-left:150px;" width="150" height="100" alt="processing">');
        $.ajax({
            url: "/packagesInComponent/",
            dataType: "json",
            data: {"product":product, "parentValue":parentValue, "childValue":childValue},
            success: function (json) {
                $('div#loader').html('');
                package_names = [];
                $.each(json.Componentpackages, function (i, item) {
                    if (!$("#packages option[id='"+item+"']").length) {
                        packages_select_box.append('<option class="'+ product +'" value="' + item + '" id="' + item + '">' + item + '</option>');
                        package_names.push(item);
                    }
                });
            },
            error: function (xhr, textStatus, errorThrown) {
                genericDialog("Issue retrieving packages delivered to "+ product + " associated with Parent: " + parentValue+ " and Child: " + childValue + ". " + (errorThrown ? errorThrown : xhr.status));
                return;
            }
        });
    }

    function genericDialog(message){
        $('#dialog-alert').dialog('open');
        $("#dialog-alert").text(message);
        $( "#dialog-alert" ).dialog({
            resizable: true,
            height:200,
            width:500,
            modal: true,
            buttons: {
                "OK": function() {
                    $(this).dialog("close");
                }
            }
        });
    }

    function genericConfirmDialog(message,componentResult,action) {
        $("#dialog-confirm").html("Confirm Dialog Box");
        $("#dialog-confirm").text(message);
        $("#dialog-confirm").dialog({
            resizable: false,
            modal: true,
            height: 200,
            width: 500,
            buttons: {
                "Yes": function () {
                    $(this).dialog('close');
                    callback(true,componentResult,action);
                },
                "No": function () {
                    $(this).dialog('close');
                    callback(false,componentResult,action);
                }
            }
        });
    }

    function callback(value,componentResult,action) {
        if (value) {
            $('div#dynamic').html('<img src = "/static/images/loader.gif" >');
            if (action === "add"){
                publishComponentData(componentResult);
            } else {
                removeComponentData(componentResult);
            }
        } else {
            return false;
        }
    }

    function displayOverview(parent) {
        $('div#overview').html('<img src = "/static/images/loader.gif" style="margin-top:32px; margin-left:50px;" width="350" height="300" alt="processing">');
        $.ajax({
            type: "GET",
            url: "/"+ product +"/getComponentInformation/",
            dataType: "html",
            data: {"parent": parent},
            success: function (html) {
                $('div#overview').html(html);
            },
            error: function (xhr, textStatus, errorThrown) {
                genericDialog("Could not query information from the CI Database: " + (errorThrown ? errorThrown : xhr.status));
                return;
            },
            dataType: "html",
        });
    }

    loadProductPackageList();
    populate_labels_select(0);
});

