$(document).ready(function () {
    var mediacontenttable = $('table#iso-content-table');
    if (!mediacontenttable.length)
    {
        return;
    }
    var product_name = $('#hidden_product_div').html();
    var drop_name = $('#hidden_drop_div').html();
    var media_artifact_name = $('#hidden_artifact_div').html();
    var version = $('#hidden_version_div').html();
    var testware = $('#hidden_testware_div').html();
    $('#dialog-alert').dialog({
        'autoOpen': false
    });

    function buildMediacontenttable() {
        $.ajax({
            type: 'GET',
            url: "/" + product_name + "/" + drop_name + "/mediaContentJson/" + media_artifact_name + "/" + version + "/" + testware + "/",
            dataType: 'json',
            cache: false,
            success: function (json, textStatus) {
                var product = json.product;
                var mediaArtMaps = json.mediaArtMaps;
                var delGroupMap = json.delGroupMap;
                var obsoleteData = json.obsoleteData;
                var isoDeltaDict = json.isoDeltaDict
                var nexusReleaseUrl = json.nexusReleaseUrl;
                var numPackages = mediaArtMaps.length;

                if (testware.toUpperCase() == 'FALSE') {
                    testware = false;
                } else {
                    testware = true;
                }

                if (numPackages === 0) {
                    no_results_string = '<tr> <td> This Artifact does not contain any packages </td> </tr>';
                    mediacontenttable.html(no_results_string);
                    return;
                }

                var keys = [];
                var headers = [];
                var fields = [];

                var field_mappings = [
                    ["pkgName", "Package", "pkgName"],
                    ["status", "Status", "status"],
                    ["pkgVersion", "Version", "pkgVersion"],
                    ["pkgRState", "RState", "package_revision__rstate"],
                    ["size", "Size(MB)","size"],
                    ["delGroup", "Delivery Group", "delGroup"],
                    ["date", "Build Date", "package_revision__date_created"],
                    ["platform", "Platform", "platform"],
                    ["category", "Media Category", "category"],
                    ["deliveredTo", "Delivered To", "deliveredTo"],
                    ["kgbTests", "KGB", "kgbTests"],
                    ["cidTests", "CID", "cidTests"],
                    ["cdbTests", "CDB", "cdbTests"],
                    ["obsolete", "Obsoleted", "obsolete"],
                    ["pri", "PRI", "pri"]
                ];
                var numFieldMappings = field_mappings.length;

                var x;
                var y;
                for (x = 0; x < numFieldMappings; x++) {
                    if (obsoleteData.length == 0 && field_mappings[x][0] === "obsolete"){
                        continue;
                    }
                    if (field_mappings[x][0] == "delGroup" && product_name != "ENM"){
                        continue;
                    }
                    if (field_mappings[x][0] == "status" || field_mappings[x][0] == "delGroup" || product[field_mappings[x][0]]) {
                        if (field_mappings[x][0] == "pri") {
                            if (testware == true || product_name == "None" || !product["pri"]) {
                                break;
                            }
                        }
                        keys.push(field_mappings[x][0]);
                        headers.push(field_mappings[x][1]);
                        fields.push(field_mappings[x][2]);
                    }
                }
                var numColumns = headers.length;
                var tr;
                var tr_string;
                var thead;

                tr = $('<tr/>');
                for (y = 0; y < numColumns; y++) {
                    if (keys[y] == "pkgName") {
                        tr_string = "<th>Name</th>";
                    } else {
                        tr_string = "<th>" + headers[y] + "</th>";
                    }
                    tr.append(tr_string);
                }
                thead = $('<thead>');
                thead.append(tr);
                mediacontenttable.append(thead);

                var platform_string = '';
                var td_string;
                var table_string = "";
                for (x=0; x<numPackages; x++) {
                    var item = mediaArtMaps[x];

                    var id = "";
                    var pkgStatus = "";
                    var otherStatus = "";
                    var isDelivered = false;
                    var isObsoleted = false;
                    var isUpdated = false;
                    var updatedKey = "";
                    var isDowngraded = false;

                    for (var p=0; p<obsoleteData.length; p++) {
                        var obsoleted = obsoleteData[p];
                        if (obsoleted['package_revision__id'] == item['package_revision__id']) {
                            isObsoleted = true;
                            break;
                        }
                    }

                    for (var key in isoDeltaDict){
                        values = isoDeltaDict[key];
                        for (var j=0; j<values.length; j++) {
                            var value = values[j].toString();
                            var check = value.indexOf('#');
                            if (check === 0 || check === -1) {
                                if (values[j] == item['package_revision__id']) {
                                    isUpdated = true;
                                    updatedKey = key;
                                    break;
                                }
                            } else {
                                var value = values[j].split('#');
                                if (value[0] == item['package_revision__id']) {
                                    isUpdated = true;
                                    updatedKey = key;
                                    if (value[1] == "true"){
                                        isDowngraded = true;
                                    }
                                    break;
                                }
                            }
                        }
                    }

                    for (var key in delGroupMap){
                        if (key == item['package_revision__id']) {
                            value = delGroupMap[key];
                            for (ind = 0; ind < value.length; ind++) {
                                var val = value[ind];
                                if (val['dropId'] == item['iso__drop__id']) {
                                    if (val['delivered'] == true) {
                                        isDelivered = true;
                                        break;
                                    }
                                }
                            }
                        }
                    }

                    if (isUpdated && isDelivered && !isObsoleted) {
                        pkgStatus = updatedKey;
                        id = updatedKey;
                    } else if (isObsoleted && isUpdated && isDelivered) {
                        pkgStatus = "obsolete";
                        otherStatus = updatedKey;
                        id = updatedKey;
                    } else if (isObsoleted && !isDelivered) {
                        pkgStatus = "obsolete";
                        id = "obsolete";
                    } else if (isUpdated) {
                        pkgStatus = updatedKey;
                        id = updatedKey;
                    } else {
                        pkgStatus = "unchanged";
                        id = "unchanged";
                    }

                    table_string += '<tr id="' + id + '">';
                    for (y = 0; y < numColumns; y++) {
                        if (keys[y] === "pkgName") {
                            td_string = '<td align=center><a href="/' + product_name + '/packages/' + item['package_revision__artifactId'] + '">' + item['package_revision__artifactId'] + '</a></td>';
                        } else if (keys[y] === "status") {
                            if (otherStatus != ""){
                                if (pkgStatus == "obsolete" && otherStatus == "updated") {
                                    td_string = '<td align=center title="Artifact version was obsoleted and now redelivered in this ISO version">updated from obsolete</td>';
                                } else if (pkgStatus == "obsolete" && otherStatus == "new") {
                                    td_string = '<td align=center title="Artifact version was obsoleted and now redelivered in this ISO version">new from obsolete</td>';
                                } else {
                                    td_string = "<td align=center>" + pkgStatus + "<br>" + otherStatus + "</td>";
                                }
                            } else {
                                if (pkgStatus == "obsolete"){
                                    td_string = "<td align=center title='Artifact Version obsoleted in this ISO Version'>" + pkgStatus + "</td>";
                                } else if (pkgStatus == "updated" && isDowngraded == true) {
                                    td_string = "<td align=center title='Artifact Version Downgraded " + pkgStatus + " in this ISO Version'>updated, version downgraded</td>";
                                } else {
                                    td_string = "<td align=center title='Artifact Version " + pkgStatus + " in this ISO Version'>" + pkgStatus + "</td>";
                                }
                            }
                        } else if (keys[y] === "pkgVersion") {
                            td_string = '<td align=center><a href="' + nexusReleaseUrl + '/' + item['package_revision__arm_repo'] + '/' + item['package_revision__groupId'] + '/' + item['package_revision__artifactId'] + '/' + item['package_revision__version'] + '/' + item['package_revision__artifactId'] + '-' + item['package_revision__version'] + '.' + item['package_revision__m2type'] + '">' + item['package_revision__version'] + '</a></td>';
                        } else if (keys[y] === "delGroup") {
                            td_string = '<td align=center>';
                            for (var key in delGroupMap){
                                value = delGroupMap[key];
                                if (key == item['package_revision__id']) {
                                    for (ind = 0; ind < value.length; ind++) {
                                        var val = value[ind];
                                        if (val['dropId'] == item['iso__drop__id']) {
                                            if (val['delivered'] == true)
                                                td_string += '<a title="delivered" href="/' + product_name + '/queue/' + drop_name + '/' + val['id'] + '/?section=delivered">' + val['id'];
                                            else if (val['deleted'] == true)
                                                td_string += '<a title="deleted" href="/' + product_name + '/queue/' + drop_name + '/' + val['id'] + '/?section=deleted">' + val['id'];
                                            else if (val['obsoleted'] == true)
                                                td_string += '<a title="obsoleted" href="/' + product_name + '/queue/' + drop_name + '/' + val['id'] + '/?section=obsoleted" style="color:red !important;">' + val['id'];
                                            if (ind < (value.length -1)) {
                                                td_string += ', ';
                                            }
                                            td_string += '</a>';
                                        }
                                    }
                                }
                            }
                            td_string += '</td>';
                        } else if (keys[y] === "platform" && product["platform"]) {
                            if (item['package_revision__platform'] == null) {
                                td_string = '<td></td>';
                            } else {
                                if (item['package_revision__platform'] = "i386") {
                                    td_string = '<td align=center>x86</td>';
                                } else {
                                    td_string = '<td align=center>' + item['package_revision__platform'] + '</td>';
                                }
                            }
                        } else if (keys[y] === "category") {
                            if (item['package_revision__infra']) {
                                td_string = '<td align=center>' + item['package_revision__category__name'] + '<br>Infrastructure</td>';
                            } else {
                                td_string = '<td align=center>' + item['package_revision__category__name'] + '</td>';
                            }
                        } else if (keys[y] === "deliveredTo") {
                            td_string = '<td align=center><a href="/' + product_name + '/drops/' + item['drop__name'] + '">' + item['drop__name'] + '</a></td>';
                        } else if (keys[y] === "kgbTests" && product.kgbTests) {
                            td_string = '<td align=center class="compile"><p align="center">';
                            if(item['kgb_test'] != "None" && product_name == "ENM"){
                                if (item['kgb_test'] == "not_started" || item['testReport'] == "" || item['kgb_test'] == "in_progress") {
                                    td_string += '<img src="/static/images/';
                                    if (item['kgb_snapshot_report'] == true){
                                        td_string += 'snapshot_' + item.kgb_test + '.png" title="Snapshot(s) Used in KGB Testing" alt="snapshot_';
                                    }else{
                                        td_string += item.kgb_test + '.png" alt="';
                                    }
                                    td_string += item.kgb_test + '" class="status-summary-img"><span style="display:none">' + item['kgb_test'];
                                }else{
                                    td_string += '<a href="'+ item['testReport'] + '"><img src="/static/images/';
                                    if (item['kgb_snapshot_report'] == true){
                                        td_string += 'snapshot_' + item.kgb_test + '.png" title="Snapshot(s) Used in KGB Testing" alt="snapshot_';
                                    } else {
                                        td_string += item.kgb_test + '.png" alt="';
                                    }
                                    td_string += item.kgb_test + '" class="status-summary-img"></a><span style="display:none">' + item['kgb_test'];
                                }
                            }else{
                                if (item['package_revision__kgb_test'] == "not_started" || item['package_revision__kgb_test'] == "in_progress") {
                                    td_string += '<img src="/static/images/';
                                    if (item['package_revision__kgb_snapshot_report'] == true){
                                        td_string += 'snapshot_' + item.package_revision__kgb_test + '.png" title="Snapshot(s) Used in KGB Testing" alt="snapshot_';
                                    } else {
                                        td_string += item.package_revision__kgb_test + '.png" alt="';
                                    }
                                    td_string += item.package_revision__kgb_test + '" class="status-summary-img"><span style="display:none">' + item['package_revision__kgb_test'];
                                } else {
                                    td_string += '<a href="/' + product_name + '/returnresults/' + item['package_revision__artifactId'] + '/' + item['package_revision__version'] + '/kgb/' + item['package_revision__m2type'] + '"><img src="/static/images/';
                                    if (item['package_revision__kgb_snapshot_report'] == true){
                                        td_string += 'snapshot_' + item.package_revision__kgb_test + '.png" title="Snapshot(s) Used in KGB Testing" alt="snapshot_';
                                    } else {
                                        td_string += item.package_revision__kgb_test + '.png" alt="';
                                    }
                                    td_string += item.package_revision__kgb_test + '"  class="status-summary-img"></a><span style="display:none">' + item['package_revision__kgb_test'];
                                }
                           }
                           td_string += '</span></p></td>';
                        } else if (keys[y] === "cidTests" && product.cidTests) {
                            td_string = '<td align=center><p align="center">';
                            if (item['package_revision__cid_test'] == "not_started") {
                                td_string += '<img src="/static/images/not_started.png" alt="not_started" class="status-summary-img"><span style="display:none">' + item['package_revision__cid_test'] + '</span>';
                            } else {
                                td_string += '<a href="/' + product_name + '/returnresults/' + item['package_revision__artifactId'] + '/' + item['package_revision__version'] + '/cid/' + item['package_revision__m2type'] + '"><img src="/static/images/' + item.package_revision__cid_test + '.png" alt="' + item.package_revision__cid_test + '" class="status-summary-img"></a><span style="display:none">' + item['package_revision__cid_test'] + '</span></p></td>';
                            }
                            td_string +='</p></td>';
                        } else if (keys[y] === "cdbTests" && product.cdbTests) {
                            td_string = '<td align=center><p align="center">';
                            if (item['overall_status'] != null) {
                                td_string += '<img id="' + item.overall_status__state + '" src="/static/images/' + item.overall_status__state + '.png" alt="' + item.overall_status__state + '" class="status-summary-img"><span style="display:none">' + item['overall_status__state'] + '</span>';
                            } else {
                                td_string += '<img src="/static/images/not_started.png" alt="not_started" class="status-summary-img"><span style="display:none">not_started</span>';
                            }
                           td_string +='</p></td>';
                        } else if (keys[y] === "obsolete" && product.obsolete) {
                            if (obsoleteData != null) {
                                td_string = '<td align=center>';
                                for (var z=0; z<obsoleteData.length; z++) {
                                    obsoleted = obsoleteData[z];
                                    if (obsoleted['package_revision__id'] == item['package_revision__id'] && obsoleted['drop__id'] == item['iso__drop__id']) {
                                        td_string += '<a href="/' + product_name + '/drops/' + obsoleted['drop__name'] + '/obsoleteInfo/">Obsolete Package History</a>';
                                        break;
                                    }
                                }
                                td_string += '</td>';
                            }
                        } else if (keys[y] === "pri") {
                            if (testware == false && product['pri']) {
                                td_string = '<td align=center><a href="/' + product_name + '/pri/' + item['package_revision__package__package_number'] + '/' + item['package_revision__platform'] + '/' + item['package_revision__version'] + '/' + item['package_revision__m2type'] + '">PRI</a></td>';
                            }
                        } else if (keys[y] === "size") {
                            var artifactSize = parseInt(item['package_revision__size']);
                            if (artifactSize == 0) {
                                artifactSize = "--";
                            } else {
                                artifactSize = Math.round((artifactSize/(1024*1024))*1000)/1000;
                            }
                            td_string = '<td align=center>' + artifactSize +  '</td>';
                        } else {
                            td_string = "<td align=center>" + item[fields[y]] + "</td>";
                       }
                          table_string += td_string;
                     }
                       table_string += '</tr>';
                }
                mediacontenttable.append(table_string);
                sortTable();
            },
            error: function (xhr, textStatus, errorThrown) {
                error_string = "<p />An error occurred: " + (errorThrown ? errorThrown : xhr.status);
                mediacontenttable.html(error_string);
            }
        });
    }

    buildMediacontenttable();
});
