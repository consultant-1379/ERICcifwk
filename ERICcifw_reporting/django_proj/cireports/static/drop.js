$(document).ready(function () {
    var packagestable = $('table#drop-packages');
    var testwaretable = $('table#drop-testware');
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
    if (!packagestable.length)
    {
        return;
    }
    var product_name = $('#hidden_product_div').html();
    var drop_name = $('#hidden_drop_div').html();
    $('#dialog-alert').dialog({
        'autoOpen': false
    });

    function genericDialog(message) {
        $('#dialog-alert').dialog('open');
        $("#dialog-alert").text(message);
        $("#dialog-alert").dialog({
            resizable: true,
            height: 200,
            width: 500,
            modal: true,
            buttons: {
                "OK": function () {
                    $(this).dialog("close");
                }
            }
        });
    }

    function buildDropPackagesResults(filterElements) {
        $.ajax({
            type: 'GET',
            url: "/" + product_name + "/drops/" + drop_name + "/" + filterElements + "/json/",
            dataType: 'json',
            cache: false,
            success: function (json, textStatus) {
                var product = json.product;
                var packages = json.dropPackageMappings;
                var numPackages = packages.length;

                if (numPackages === 0) {
                    no_results_string = '<tr> <td> No deliveries found </td> </tr>';
                    packagestable.html(no_results_string);
                    testwaretable.html(no_results_string);
                    return;
                }

                var table_array = [packagestable, testwaretable];

                var keys = [];
                var headers = [];
                var fields = [];

                var intended_drop_string = 'Intended Drop';
                var field_mappings = [
                    ["pkgName", "Name", ""],
                    ["pkgVersion", "Version", ""],
                    ["pkgRState", "RState", "RState"],
                    ["size", "Size(MB)","size"],
                    ["platform", "Platform", ""],
                    ["category", "Media Category", ""],
                    ["intendedDrop", intended_drop_string, "package_revision__autodrop"],
                    ["deliveredTo", "Delivered To", "drop__name"],
                    ["date", "Date Delivered", "date_created"],
                    ["kgbTests", "Known Good Baseline", "package_revision__kgb_test"],
                    ["obsolete", "", ""]
                ];
                var numFieldMappings = field_mappings.length;

                var x;
                var y;
                for (x = 0; x < numFieldMappings; x++) {
                    if (product[field_mappings[x][0]]) {
                        keys.push(field_mappings[x][0]);
                        headers.push(field_mappings[x][1]);
                        fields.push(field_mappings[x][2]);
                    }
                }
                var numColumns = headers.length;
                var tr;
                var tr_string;
                var thead;
                for (x = 0; x < table_array.length; x++) {
                    tr = $('<tr/>');
                    for (y = 0; y < numColumns; y++) {
                        if (keys[y] == "obsolete") {
                            tr_string = '<th class="obsolete" style="width:5%;">Action</th>';
                        }else if(keys[y] == "pkgName"){
                            tr_string = '<th style="width:25%;">'  + headers[y] + '</th>';
                        } else {
                            tr_string = "<th>" + headers[y] + "</th>";
                        }
                        tr.append(tr_string);
                    }
                    thead = $('<thead>');
                    thead.append(tr);
                    table_array[x].empty();
                    table_array[x].append(thead);
                }

                var table_strings = {
                    'testware': '',
                    'packages': ''
                };
                var platform_string = '';
                var td_string;
                for (x = 0; x < numPackages; x++) {
                    if (packages[x].package_revision__category__name == "testware") {
                        type = "testware";
                    } else {
                        type = "packages";
                    }
                    table_strings[type] += '<tr>';
                    for (y = 0; y < numColumns; y++) {
                        if (keys[y] === "pkgName") {
                            td_string = '<td id="package"><a href="/' + product_name + '/packages/' + packages[x].package_revision__package__name + '">' + packages[x].package_revision__package__name + '</a></td>';
                        } else if (keys[y] === "pkgVersion") {
                            td_string = '<td><a href="' + packages[x].nexusUrl + '">' + packages[x].package_revision__version + '</a></td>';
                        } else if (keys[y] === "size") {
                            var artifactSize = parseInt(packages[x].package_revision__size);
                            if (artifactSize == 0){
                                artifactSize = "--";
                            } else {
                                artifactSize = Math.round((artifactSize/(1024*1024))*1000)/1000;
                            }
                            td_string = '<td align=center>' + artifactSize +  '</td>';
                        } else if (keys[y] === "category") {
                            if (packages[x].package_revision__isoExclude) {
                                if (packages[x].package_revision__infra) {
                                    td_string = '<td><span style="display:none">_</span>' + packages[x].package_revision__category__name + ':Exclude<br>Infrastructure</td>';
                                } else {
                                    td_string = '<td>' + packages[x].package_revision__category__name + ':Exclude</td>';
                                }
                            } else {
                                if (packages[x].package_revision__infra) {
                                    td_string = '<td><span style="display:none">_</span>' + packages[x].package_revision__category__name + '<br>Infrastructure</td>';
                                } else {
                                    td_string = '<td>' + packages[x].package_revision__category__name + '</td>';
                                }
                            }
                        } else if (keys[y] === "platform") {
                            if (packages[x].package_revision__platform === "None") {
                                platform_strign = "";
                            } else if (packages[x].package_revision__platform === "i386") {
                                platform_string = "x86";
                            } else {
                                platform_string = packages[x].package_revision__platform;
                            }
                            td_string = "<td>" + platform_string + "</td>";
                        } else if (keys[y] === "kgbTests") {
                            td_string = '<td><p align="center">';
                            if (packages[x].kgb_test != null && product_name == "ENM"){
                                if (packages[x].kgb_test == "not_started" || packages[x].kgb_test == "in_progress" || packages[x].testReport == "" || packages[x].testReport == null) {
                                    td_string += '<img src="/static/images/';
                                    if (packages[x].kgb_snapshot_report == true) {
                                        td_string += 'snapshot_' + packages[x].kgb_test + '.png" title="Snapshot(s) Used in KGB Testing" alt="snapshot_';
                                    }  else {
                                        td_string += packages[x].kgb_test + '.png" alt="';
                                    }
                                    td_string += packages[x].kgb_test + '" class="status-summary-img"><span style="display:none">' + packages[x].kgb_test;
                                }else{
                                    td_string += '<a href="'+ packages[x].testReport +'"><img src="/static/images/';
                                    if (packages[x].kgb_snapshot_report == true) {
                                        td_string += 'snapshot_' + packages[x].kgb_test + '.png" alt="snapshot_';
                                    }  else {
                                        td_string +=  packages[x].kgb_test + '.png" alt="';
                                    }
                                    td_string += packages[x].kgb_test + '" class="status-summary-img"></a><span style="display:none">' + packages[x].kgb_test;
                               }
                            } else{
                                if (packages[x][fields[y]] == "not_started" || packages[x].package_revision__kgb_test == "in_progress") {
                                    td_string += '<img src="/static/images/';
                                    if (packages[x].package_revision__kgb_snapshot_report == true) {
                                        td_string += 'snapshot_' + packages[x].package_revision__kgb_test + '.png" title="Snapshot(s) Used in KGB Testing" alt="snapshot_';
                                    }  else {
                                        td_string += packages[x].package_revision__kgb_test + '.png" alt="';
                                    }
                                    td_string += packages[x].package_revision__kgb_test + '" class="status-summary-img"><span style="display:none">' + packages[x].package_revision__kgb_test;
                                } else {
                                    td_string += '<a href="/' + product_name + '/returnresults/' + packages[x].package_revision__package__name + '/' + packages[x].package_revision__version + '/kgb/' + packages[x].package_revision__m2type + '"> <img src="/static/images/';
                                    if (packages[x].package_revision__kgb_snapshot_report == true) {
                                        td_string += 'snapshot_' + packages[x].package_revision__kgb_test + '.png" title="Snapshot(s) Used in KGB Testing" alt="snapshot_';
                                    }  else {
                                        td_string += packages[x].package_revision__kgb_test + '.png" alt="';
                                    }
                                    td_string +=  packages[x].package_revision__kgb_test + '" class="status-summary-img"></a><span style="display:none">' + packages[x].package_revision__kgb_test;
                               }
                           }
                           td_string +='</span></p></td>';
                        } else if (keys[y] === "obsolete") {
                            td_string = '<td><a href="/' + product_name + '/drops/' + drop_name + '/obsoleteVersion/?id=' + packages[x].id + '&package=' + packages[x].package_revision__package__name + '&version=' + packages[x].package_revision__version + '&platform=' + packages[x].package_revision__platform + '" title="Obsolete">Obsolete</a></td>';
                        } else {
                            td_string = "<td>" + packages[x][fields[y]] + "</td>";
                        }

                        table_strings[type] += td_string;
                    }
                    table_strings[type] += '</tr>';
                }

                packagestable.append(table_strings['packages']);
                testwaretable.append(table_strings['testware']);

                sortTable();
                openItem('packages');
            },
            error: function (xhr, textStatus, errorThrown) {
                error_string = "<p />An error occurred: " + (errorThrown ? errorThrown : xhr.status);
                packagestable.html(error_string);
                testwaretable.html(error_string);
            }
        });
    }

    var clear_filter_button = $('#clear_filter_button');
    clear_filter_button.hide();
    var divClone = $("#generic-sub-title").clone();
    var filterElements = null;
    buildDropPackagesResults(filterElements);
    $('#outerdrop-filter').hide();
    $('#showfilter').click(function () {
        var $this = $(this);
        $('#outerdrop-filter').toggle();
        if ($this.text() === "Show Drop Filter") {
            $this.text("Hide Drop Filter");
        } else {
            $this.text("Show Drop Filter");
        }
    });

    var labels_select_box = $('#labels');
    var parents_select_box = $('#parents');
    var parents_check_box = $('#allparents');
    var children_select_box = $('#children');
    var children_check_box = $('#allchildren');
    var filter_button = $('#filter_button');

    function disable_interaction() {
        labels_select_box.prop('disabled', true);
        parents_check_box.prop('disabled', true);
        parents_select_box.prop('disabled', true);
        children_check_box.prop('disabled', true);
        children_select_box.prop('disabled', true);
        filter_button.prop('disabled', true);
    }

    function enable_interaction() {
        labels_select_box.prop('disabled', false);
        parents_check_box.prop('disabled', false);
        if (!parents_check_box.is(':checked')) {
            parents_select_box.prop('disabled', false);
        }
        children_check_box.prop('disabled', false);
        if (!children_check_box.is(':checked')) {
            children_select_box.prop('disabled', false);
        }
        filter_button.prop('disabled', false);
    }

    function populate_labels_select() {
        disable_interaction();
        labels_select_box.empty();
        labels_select_box.append('<option value="0" disabled>Loading...</option>');
        $.ajax({
            url: "/" + product_name + "/getProductLabels/.json/",
            dataType: "json",
            success: function (json) {
                labels_select_box.empty();
                $.each(json.Label, function (i, item) {
                    labels_select_box.append('<option value="' + item.name + '" id="' + item.name + '">' + item.name + '</option>');
                });
                var opts_list = labels_select_box.find('option');
                opts_list.sort(function (a, b) {
                    return $(a).text() > $(b).text();
                });
                labels_select_box.empty();
                labels_select_box.append(opts_list);
                labels_select_box.change();
            },

            error: function (xhr, textStatus, errorThrown) {
                labels_select_box.empty();
                labels_select_box.append('<option value="0" disabled>Error...</option>');
                genericDialog("Issue retrieving the " + product_name + " Label list: " + (errorThrown ? errorThrown : xhr.status));
                return;
            }
        });
    }

    labels_select_box.change(function () {
        disable_interaction();
        parents_select_box.empty();
        children_select_box.empty();
        setParentLabel();
        populate_parents_select();
    });

    function setParentLabel() {
        var value = labels_select_box.val();
        $("#parentLabel").text("Select " + value + " from List:");
        $("#parentSelectAllLabel").text("Select All " + value + "s");
    }


    function populate_parents_select() {
        disable_interaction();
        var label = labels_select_box.val();
        parents_select_box.empty();
        parents_select_box.append('<option value="0" disabled>Loading...</option>');
        children_select_box.empty();

        $.ajax({
            url: "/" + product_name + "/" + label + "/getParentComponentsOfLabel/.json/",
            dataType: "json",
            success: function (json) {
                parents_select_box.empty();
                $.each(json.Parents, function (i, item) {
                    parents_select_box.append('<option value="' + item.name + '" id="' + item.name + '">' + item.name + '</option>');
                });
                var opts_list = parents_select_box.find('option');
                opts_list.sort(function (a, b) {
                    return $(a).text() > $(b).text();
                });
                parents_select_box.empty();
                parents_select_box.append(opts_list);
                parents_check_box.change();
            },
            error: function (xhr, textStatus, errorThrown) {
                genericDialog("Issue retrieving Parent Components associated with " + label + ": " + (errorThrown ? errorThrown : xhr.status));
                return;
            }
        });
    }

    parents_select_box.change(function () {
        disable_interaction();
        setChildLabel();
        populate_children_select();
    });

    parents_check_box.change(function () {
        if ($(this).is(':checked')) {
            $('#parents option').prop('selected', true);
        }
        parents_select_box.change();
    });

    function setChildLabel() {
        var parentElement = $("#parents option:first").val();
        $.ajax({
            url: "/" + product_name + "/" + parentElement + "/getChildLabelFromParentLabel/.json/",
            dataType: "json",
            success: function (json) {
                $.each(json.ChildLabel, function (i, item) {
                    if (item.name === "None") {
                        children_select_box.prop('disabled', true);
                        children_check_box.attr('disabled', true);
                    }
                    $("#childLabel").text("Select " + item.name + " from List:");
                    $("#childSelectAllLabel").text("Select All " + item.name + "s");
                });
            },
            error: function (xhr, textStatus, errorThrown) {
                genericDialog("Issue getting child label associated with " + parentElement + ": " + (errorThrown ? errorThrown : xhr.status));
                return;
            }
        });
    }

    function populate_filter_data(children_list) {
        packagestable.html("<tr><td> Loading Data ... </td></tr>");
        testwaretable.html("<tr><td> Loading Data ... </td></tr>");
        buildDropPackagesResults(children_list);
    }

    function childComponentsInParentComponent(parentComponent) {
        return $.ajax({
            url: "/childComponentsInParentComponent/",
            dataType: "json",
            data: {
                "product": product_name,
                "parentComponent": parentComponent
            },
            success: function (json) {
                $.each(json.ChildComponents, function (i, item) {
                    children_select_box.append('<option class="' + parentComponent + '" value="' + item + '" id="' + item + '">' + item + '</option>');
                });
            },
            error: function (xhr, textStatus, errorThrown) {
                genericDialog("Issue retrieving childComponents associated with " + parentComponent + ": " + (errorThrown ? errorThrown : xhr.status));
            }
        });
    }

    function populate_children_select() {
        children_select_box.empty();
        var selected_parents = $('#parents').children('option:selected');
        if (selected_parents.length === 0) {
            children_select_box.empty();
        }
        var promises = [];
        $('#parents').children('option:selected').each(function () {
            promises.push(childComponentsInParentComponent($(this).val()));
        });
        $.when.apply($, promises).then(function () {
            var opts_list = children_select_box.find('option');
            opts_list.sort(function (a, b) {
                return $(a).text() > $(b).text();
            });
            children_select_box.empty();
            children_select_box.append(opts_list);
            children_check_box.change();
        });
    }

    children_select_box.change(function () {
        enable_interaction();
        if ($('#children option:selected').length === 0) {
            filter_button.prop("disabled", true);
        } else {
            filter_button.prop("disabled", false);
        }
    });

    children_check_box.change(function () {
        if ($(this).is(':checked')) {
            $('#children option').prop('selected', true);
        }
        children_select_box.change();
    });

    filter_button.click(function () {
        var children_list = [];
        $('#children option:selected').each(function () {
            children_list.push($(this).val());
        });
        $("#generic-sub-title").replaceWith(divClone.clone());
        populate_filter_data(children_list);
        clear_filter_button.show();
    });

    clear_filter_button.click(function () {
        var children_list = null;
        $("#generic-sub-title").replaceWith(divClone.clone());
        populate_filter_data(children_list);
    });
    populate_labels_select();
});
