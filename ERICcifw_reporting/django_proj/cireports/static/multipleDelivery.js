var warnings = [];
var dropName = "";
var packageFound = 0;
var doVerCheck = 1;
var groupId = "";
var kgb_check = false;
var kgb_published_reason = "";
var kgb_not_run_reason = "";
var kgb_extra_info = "";
var team_items = [""];
var cenmdgSum = 0;
var cenmdgIndex = 1;
var cenmdgForms = {};
var impacted_dg_items = [];
$(document).ready(function() {
    var kgb_select_box = $('#kgb_select_box_option');
    $("#empty_kgb_select").hide();
    var group_data = $('#hidden_group_div').html();
    var edit_mode = $('#hidden_edit_div').html();
    formNum = 0;
    formNumJira = 0;
    if (group_data) {
        group_info = jQuery.parseJSON(group_data);
        groupId = group_info.groupId;
        dropName = group_info.dropName;
        if (group_info.canEdit == 1) {
            if (group_info.packageRevisions.length != 0) {
                run_loop(group_info.packageRevisions.length);
                if (group_info.groupId == ""){
                   add_jira_selector();
                }
            } else {
                groupId = group_info.groupId;
                add_package_selector();
                add_jira_selector();
            }
            populate_existing_cenm_dg();
        } else {
            $("div.generic-sub-title").replaceWith('<div id=noEdit style = "float:left; display:inline-block; width:80%;">Group ' + group_info.groupId + ' is not queued and cannot be edited</div>').addClass('versionWarning')
            $("#noEdit").addClass('versionWarning')
        }
    } else {
        groupId = "None";
        group_info = false;
        add_package_selector();
        add_jira_selector();
    }
    $(function() {
        $("#kgb-dialog").dialog({
            closeOnEscape: false,
            modal: true,
            width: "500",
            height: "270",
            resizable: true,
            autoOpen: false,
            open: function(event, ui) {
                $(".ui-dialog-titlebar-close").hide();
            }
        });
    });
    $("#cancel").click(function(e) {
        kgb_check = false;
        kgb_published_reason = "";
        kgb_not_run_reason = "";
        kgb_extra_info = "";
        kgb_select_box.empty();
        $("#kgb-reason").val("");
        $("#kgb_extra_info").val("");
        $("#kgb-dialog").dialog("close");
    });
    $("#submit").click(function(e) {
        kgb_not_run_reason = $("#kgb_select_box_option option:selected").text();
        kgb_extra_info = $('#kgb_extra_info').val();
        if (kgb_not_run_reason == "Other" && kgb_extra_info == "") {
            alert("You Selected 'Other' as the reason for not having a passed KGB, Please add a comment, in the 'Comment' section with a reason.");
            $('#add_to_queue').attr('disabled', false);
            return;
        }
        if (kgb_not_run_reason == null || kgb_not_run_reason == "") {
            window.alert("Please select a Reason from the dropdown.");
            $('#add_to_queue').attr('disabled', false);
            return;
        }

        $("#kgb-reason").val(kgb_not_run_reason);
        $('#kgb_extra_info').val($('#kgb_extra_info').val());
        $("#kgb-dialog").dialog("close");
        add_group_to_stage();
    });

    function removeJiraAction(id) {
        var proceed = confirm("Do you really want to remove this JIRA Ticket Input?");
        if (proceed) {
            $("#jirasdiv_" + id).remove();
            var jiraTicketFound = 0;
            for (var i = 0; i < formNumJira; i++) {
                var jira = $('#jiras_' + i).val();
                if (typeof jira === 'undefined') {
                    continue;
                } else {
                    jiraTicketFound = 1;
                }
            }
        }
    }

    function removePackageAction(id) {
        var proceed = confirm("Do you really want to remove this Package Input?");
        if (proceed) {
            $("#packagesdiv_" + id).remove();

        }
        $('#add_to_queue').attr('disabled', false);
    }

    function setMissingDepCheckBox() {
        if (parseInt(edit_mode)) {
            var missingDep = group_info.missingDep;
            if (missingDep !== false) {
                $('#set_missingDep').prop('checked', true);
            }
        }
    }

    function removeCENMDGAction(linkNum) {
        let proceed = confirm("Do you really want to remove this field?");
        if (proceed) {
            $("#cenmdgdiv_" + linkNum).remove();
            delete cenmdgForms[linkNum];
            cenmdgSum = cenmdgSum - 1;
        }
    }

    setMissingDepCheckBox();
    drop_select_box = $('#drop');
    populate_drop_select();
    team_select_box = $('#team');
    populate_team_select();
    $('#add_artifact').click(add_package_selector);
    $('#add_cenmdg').click(add_cenmdg_selector);
    $('#add_jira').click(add_jira_selector);
    $('#add_to_queue').click(add_group_to_stage);
    populate_jira();

    function run_loop(howManyTimes) {
        promises = [];
        if (howManyTimes === 0) {
            groupId = group_info.groupId;
            group_info = false;
        } else {
            promises.push(add_package_selector());
            $.when.apply($, promises).then(function(json) {
                run_loop(howManyTimes - 1);
            });

        }
    }

    function populate_jira() {
        if (parseInt(edit_mode) && typeof group_info.jiraIssues !== 'undefined') {
            promisesJira = [];
            var jira_issue = group_info.jiraIssues;
            if (jira_issue.length != 0) {
                $.each(jira_issue, function(i, item) {
                    if (item.issue != "") {
                        promisesJira.push(add_jira_selector());
                        id = formNumJira - 1
                        $('#jiras_' + id).val(item.issue);
                        $('#add_jira').attr('disabled', false);
                        $('#add_to_queue').attr('disabled', false);
                    }
                });
            } else {
                add_jira_selector()
            }
        }
    }

    function populate_cenm_dg_select(elementId) {
        let input_element = $(elementId);
        if (impacted_dg_items.length > 1) {
            input_element.autocomplete({
                source: impacted_dg_items
            });
            return;
        }
        if (!dropName){
            dropName = drop_select_box[0].options[drop_select_box[0].selectedIndex].value;
        }
        dropName=dropName.slice(4);
        $.ajax({
            url: "/api/cloudNative/getDeliveryGroupsByDrop/CENM",
            dataType: "json",
            data: {
                "dropName": dropName
            },
            success: function(data) {
                $.each(data, function(i, item) {
                    result = String(item.id);
                    input_element.append('<option value="" id=""></option>');
                    input_element.append('<option value="' + result + '" id="' + result + '">' + result + '</option>');
                    impacted_dg_items.push(result);
                });
                input_element.autocomplete({
                    source: impacted_dg_items
                });
            },
            error: function(xhr, textStatus, errorThrown) {
                alert("Issue retrieving the list of CENM DG for drop " + dropName + ": " + xhr.responseText);
            }
        });
    }

    async function populate_existing_cenm_dg() {
        dg_beforeEdit = await $.ajax({
            url: "/api/cloudNative/deliveryQueue/getImpactedDeliveryGroupInfo/" + groupId,
            dataType: "json",
            data: {
                "queueType": "ENM"
            },
            success: function(data) {
                return data;
            },
            error: function(xhr, textStatus, errorThrown) {
                alert("Issue retrieving impacted DG data: " + xhr.responseText);
                return "";
            }
        });
        dg_beforeEdit.impactedDeliveryGroupNumberList.forEach(function(item, index) {
            add_cenmdg_selector(item);
        });
    }

    function populate_team_select() {
        if (parseInt(edit_mode)) {
            var team = group_info.creatorsTeam;
            team_select_box.append('<option value="' + team + '" id="' + team + '">' + team + '</option>');
            team_select_box.val(team);
            team_items.push(team);
            team_select_box.prop('disabled', 'disabled');
            return;
        }
        var local_group_info = group_info;
        $.ajax({
            url: "/api/cireports/component/ENM/Team/",
            dataType: "json",
            success: function(json) {
                team_select_box.append('<option value="" id=""></option>');
                $.each(json, function(i, item) {
                    team_select_box.append('<option value="' + item.element + '" id="' + item.element + '">' + item.element + '</option>');
                    team_items.push(item.element);
                });
                team_select_box.autocomplete({
                    source: team_items
                });
                if (local_group_info) {
                    team_select_box.val(local_group_info.creatorsTeam);
                } else {
                    team_select_box.val(team_items[0]);
                }
            },

            error: function(xhr, textStatus, errorThrown) {
                alert("Issue retrieving the list of Teams: " + (errorThrown ? errorThrown : xhr.status));
            }
        });
    }

    function validate_team(){
        var result = false;
        $.each(team_items,function(index,value) {
            if (value == $('#team').val()) {
                result = true;
            }
        });
        return result;
     }

    function populate_drop_select() {
        var frozen = 0;
        var closed = 0;
        $.ajax({
            url: "/getActiveDrops/",
            dataType: "json",
            data: {
                "product": 'ENM'
            },
            success: function(json) {
                var drop_items = [];
                $.each(json.Drops, function(i, item) {
                    if (item.indexOf('Frozen') > -1) {
                        $('#add_to_queue').attr('disabled', true);
                        window.alert(item);
                        frozen = 1;
                    } else {
                        closed = item;
                    }
                    drop_select_box.append('<option value="' + item + '" id="' + item + '">' + item + '</option>');
                    drop_items.push(item);
                });
                if (group_info.dropName && frozen == 0) {
                    drop_select_box.val(group_info.dropName);
                } else if (group_info && frozen == 0) {
                    drop_select_box.val(drop_items[0]);
                }
            },

            error: function(xhr, textStatus, errorThrown) {
                alert("Issue retrieving the list of Drops: " + (errorThrown ? errorThrown : xhr.status));
            }
        });
    }

    function populate_packages() {
        if (group_info) {
            $('#add_artifact').attr('disabled', true);
            if (group_info.packageRevisions.length != 0) {
                var package_name = group_info.packageRevisions[formNum - 1].name;
                var version = group_info.packageRevisions[formNum - 1].version;
                var team_pkg = group_info.packageRevisions[formNum - 1].team;
                populate_versions(package_name, version);
                $('#add_artifact').attr('disabled', false);
            }
        }
        return $.ajax({
            url: "/metrics/AllPackages/.json/",
            dataType: "json",
            success: function(json) {
                package_names = [""];
                $.each(json.packagesJson, function(i, item) {
                    package_names.push(item);
                });
                packages_select_box.autocomplete({
                    source: package_names
                });
                if (group_info && group_info.packageRevisions.length != 0) {
                    $('#add_artifact').attr('disabled', true);
                    packages_select_box.val(package_name);
                    versions_select_box.val(version);
                    if (typeof team_pkg === 'undefined') {
                        populate_teams(package_name, team_box);
                    } else {
                        team_box.val(team_pkg);
                    }
                    $('#add_artifact').attr('disabled', false);
                } else {
                    packages_select_box.val(package_names[0]);
                }
            },
            error: function(xhr, textStatus, errorThrown) {
                alert("Issue retrieving the All Package list: " + (errorThrown ? errorThrown : xhr.status));
            }
        });
    }

    function add_package_selector() {
        $('#add_artifact').attr('disabled', true);
        $("#empty_form").append("<div id='packagesdiv_" + formNum + "' class='delivery_packagesdiv'> <br><label for='packages_" + formNum + "'>Package:</label><input id='packages_" + formNum + "' class='delivery_form_package'><label for='version_" + formNum + "'>Version:</label><select id='version_" + formNum + "' class='delivery_form_version' ></select><label for='team_" + formNum + "'>Team(s):</label><textarea id='team_" + formNum + "' class='delivery_form_team' readonly></textarea><a id='packageremoves_" + formNum + "' class='img'> <img src='/static/images/delete.png' class='delivery_form_delete_img' title='Remove Package Input' /></a><br><p id='warning_" + formNum + "' class='delivery_form_warning'></p><br></div>");
        packages_select_box = $('#packages_' + formNum);
        versions_select_box = $('#version_' + formNum);
        team_box = $('#team_' + formNum);
        warning_section = $('#warning_' + formNum);
        warning_section.hide();
        team_box.prop('disabled', 'disabled');
        $('#packageremoves_' + formNum).click(function() {
            var id = $(this).attr('id');
            var selectId = id.split('_').pop();
            removePackageAction(selectId)
            $('#add_artifact').attr('disabled', false);
        });
        $('body').on('autocompletechange', '#packages_' + formNum, function() {
            var id = $(this).attr('id');
            var artifact = $('#' + id).val();
            var selectId = id.split('_').pop();
            versions_select_box = $('#version_' + selectId);
            versions_select_box.empty();
            $('#add_artifact').attr('disabled', true);
            populate_versions(artifact, versions_select_box, selectId);
            team_box = $('#team_' + selectId);
            team_box.val("");
            populate_teams(artifact, team_box)
            $('#add_artifact').attr('disabled', false);
        });
        $('#version_' + formNum).change(function() {
            var id = $(this).attr('id');
            var version = $('#' + id).val();
            var selectId = id.split('_').pop();
            var artifact = $('#packages_' + selectId).val();
            warning_section = $('#warning_' + selectId);
            warning_section.text("");
            version_check(artifact, version, warning_section, selectId)
        });
        formNum = formNum + 1;
        return populate_packages();
    }

    function populate_versions(artifact, versions_box, selectId) {
        $.ajax({
            url: "/getRevisionsOfPackage/",
            dataType: "json",
            data: {
                'package': artifact.toString()
            },
            success: function(json) {
                var versions = [];
                $.each(json.revisions, function(i, item) {
                    if (!group_info) {
                        if (typeof versions_box === 'string' || versions_box instanceof String) {
                            versions_select_box.prepend('<option class="All" value="' + item + '">' + item + '</option>');
                        } else {
                            versions_box.prepend('<option class="All" value="' + item + '">' + item + '</option>');
                        }
                    } else {
                        versions_select_box.prepend('<option class="All" value="' + item + '">' + item + '</option>');
                    }
                    versions.push(item);
                });
                if (!group_info) {
                    if (typeof versions_box === 'string' || versions_box instanceof String) {
                        versions_select_box.val(versions_box);
                    } else {
                        versions_select_box.val(versions[versions.length - 1]);
                    }
                }
                if (typeof selectId !== 'undefined') {
                    var version = $('#version_' + selectId).val();
                    var warning_section = $('#warning_' + selectId);
                    version_check(artifact, version, warning_section, selectId)
                }
            },
            error: function(xhr, textStatus, errorThrown) {
                alert("Issue retrieving revisions for " + artifact + ": " + (errorThrown ? errorThrown : xhr.status));
            }
        });
    }

    function populate_teams(artifact, team_textarea) {
        $.ajax({
            url: "/api/cireports/team/" + artifact + "/",
            dataType: "json",
            success: function(json) {
                var teamItems = [];
                team_textarea.val("");
                $.each(json, function(i, item) {
                    if (team_textarea.val() == "") {
                        team_textarea.val(item.team);
                    } else {
                        team_textarea.val(team_textarea.val() + ', ' + item.team);
                    }
                    teamItems.push(item.team);
                });
                if (team_textarea.val() == "") {
                    team_textarea.val("No Team Data");
                }
            },
            error: function(xhr, textStatus, errorThrown) {
                alert("Issue retrieving team(s) for " + artifact + ": " + (errorThrown ? errorThrown : xhr.status));
            }
        });
    }

    function add_jira_selector() {
        $('#add_jira').attr('disabled', true);
        $('#add_to_queue').attr('disabled', true);
        $("#empty_jira_form").append("<div id='jirasdiv_" + formNumJira  + "' class='jiradiv'><br><div id='jirasdiv_" + formNumJira + "'><br><label for='jiras_" + formNumJira + "' id='jiraslabel_" + formNumJira + "'>JIRA Ticket:</label><input id='jiras_" + formNumJira + "' class='delivery_form_jira'><a id='jiraremoves_" + formNumJira + "' class='img' > <img src='/static/images/delete.png' class='delivery_form_delete_img' title='Remove Jira Issue Input' /></a><br><p id='jira_warning_" + formNumJira + "' class='jira_form_warning'></p><br></div>");
        warning_section = $('#jira_warning_' + formNumJira);
        warning_section.hide();
        $('#jiraremoves_' + formNumJira).click(function() {
            var id = $(this).attr('id');
            var selectId = id.split('_').pop();
            removeJiraAction(selectId)
            $('#add_jira').attr('disabled', false);
            $('#add_to_queue').attr('disabled', false);
        });
        $('#jiras_' + formNumJira).change(function() {
            var id = $(this).attr('id');
            var jira = $('#' + id).val();
            var selectId = id.split('_').pop();
            jira_box = $('#jiras_' + selectId);
            warning_jira_section = $('#jira_warning_' + selectId);
            warning_jira_section.text("");
            warning_jira_section.hide();
            validate_jira(jira, warning_jira_section, jira_box, selectId);
        });
        formNumJira = formNumJira + 1;
    }

    function add_cenmdg_selector(cenmDgValue) {
        let formNum = cenmdgIndex
        cenmdgForms[formNum] = formNum;
        let $cenmdg_container = $("<div id='cenmdgdiv_" + formNum  + "' class='cenmdgdiv'></div>")
        let $cenmdg_label = $("<label for='cenmdg_" + formNum + "' id='cenmdglabel_" + formNum + "'>Impacted Cloud Native Delivery Group:</label>")
        let $cenmdg_input = $("<input id='cenmdg_" + formNum + "' class='delivery_form_enm_dg'>")
        let $cenmdg_removal = $("<a id='cenmdgremoves_" + formNum + "' class='img' > <img src='/static/images/delete.png' class='delivery_form_delete_img' title='Remove Impacted Cloud Native Devlivery Group Input' /></a>")
        $(document).on("click", "#cenmdgremoves_" + formNum, function() {
            removeCENMDGAction(formNum);
        });
        $cenmdg_container.prepend($cenmdg_label, [$cenmdg_input, $cenmdg_removal]);
        $("#add_cenmdg").before($cenmdg_container);
        populate_cenm_dg_select('#cenmdg_' + formNum);
        cenmdgIndex += 1;
        cenmdgSum += 1;
        if (cenmDgValue > 0) {
            $('#cenmdg_' + formNum).val(cenmDgValue);
        }
    }

    function validate_jira(jira, warning_jira_area, jira_box, selectId) {
        jira = jira.replace(/ /g, '');
        jira = jira.split(/[/ ]+/).pop();
        $.ajax({
            url: "/api/tools/jiravalidation/issue/" + jira + "/",
            dataType: "json",
            success: function(json) {
                var warnings = [];
                warning_jira_area.text("");
                $.each(json, function(i, item) {
                    if (item['warning'] != null){
                        warning_jira_area.text(item['warning']);
                        warning_jira_area.show();
                        $("#jirasdiv_" + selectId).addClass('jiraWarning');
                        warnings.push(item);
                        $('#add_jira').attr('disabled', true);
                        $('#add_to_queue').attr('disabled', true);
                    } else {
                        $("#jirasdiv_" + selectId).removeClass('jiraWarning');
                        warning_jira_area.hide();
                        $('#add_jira').attr('disabled', false);
                        $('#add_to_queue').attr('disabled', false);
                    }
                });
            },
            error: function(xhr, textStatus, errorThrown) {
                if (errorThrown === "NOT FOUND") {
                    alert("JIRA Ticket: " + jira + " is invalid. Please enter in a valid JIRA Ticket. (Example: CIS-11807 or https://jira-oss.seli.wh.rnd.internal.ericsson.com/browse/CIS-11807)");
                } else {
                    message = "Issue retrieving data from JIRA, would you like to proceed anyway?"
                    proceed_jira = confirm(message)
                }
                if (proceed_jira){
                    $('#add_jira').attr('disabled', false);
                    $('#add_to_queue').attr('disabled', false);
                }else {
                     jira_box.val("");
                }
            }
        });
    }


    function version_check(artifact, version, warning_area, selectId) {
        var dropData = $('#drop').val();
        var drop = "";
        if (dropData.indexOf('Closed') > -1) {
            var getDrop = $('#drop').val().split(':').pop();
            var drop = getDrop.slice(0, getDrop.indexOf(','));
        } else {
            drop = $('#drop').val().split(':').pop();
        }
        $.ajax({
            url: "/api/tools/packageversionvalidation/ENM/" + drop + "/" + artifact + "/" + version + "/" + groupId,
            dataType: "json",
            success: function(json) {
                var warnings = [];
                warning_area.text("");
                $.each(json, function(i, item) {
                    if (item != "") {
                        warning_area.text(item);
                        warning_area.show();
                        $("#packagesdiv_" + selectId).addClass('versionWarning');
                        warnings.push(item);
                    } else {
                        $("#packagesdiv_" + selectId).removeClass('versionWarning');
                        warning_area.hide();
                        warning_area.text("");
                        warning_area.val("");
                    }
                });
            },
            error: function(xhr, textStatus, errorThrown) {
                alert("Issue Checking Package Version: " + artifact + "-" + version + " " + (errorThrown ? errorThrown : xhr.status));
            }
        });
    }

    function get_kgb_reasons() {
        kgb_select_box.empty();
        $("#kgb_extra_info").val("");
        $.ajax({
            url: "/api/getreasonsfornokbgstatus/active/true",
            dataType: "json",
            success: function(json) {
                kgb_select_box.append('<option disabled selected value></option>');
                $.each(json, function(key, value) {
                    if (value['reason']) {
                        kgb_select_box.append('<option value="' + value['reason'] + '" id="kgb-reason">' + value['reason'] + '</option>');
                        $("#kgb-dialog").dialog("open");
                    }
                });
            },
            error: function(xhr, textStatus, errorThrown) {
                alert("Issue Getting Reasons for no reported KGB: " + (errorThrown ? errorThrown : xhr.status));
            }

        });
    }

    function wrapCENMDeliveryGroupData() {
        let cenmDgData = []
        Object.keys(cenmdgForms).forEach(key => {
            let cenmDgElement = $("#cenmdg_" + key);
            if (cenmDgElement.val().trim().length > 0) {
                cenmDgData.push(cenmDgElement.val());
            }
        });
        return cenmDgData;
    }

    function add_group_to_stage() {
        $('#add_to_queue').attr('disabled', true);
        var dropData = $('#drop').val();
        if (dropData.indexOf('Closed') > -1) {
            if (group_info) {
                window.alert("This Drop is Closed. You cannot Edit this Group for a Closed Drop");
            } else {
                window.alert(dropData);
            }
            $('#add_to_queue').attr('disabled', false);
            return
        }

        if ($('#team').val() == null || $('#team').val() == "") {
            window.alert("Please Add a 'Group Creators Team', to this Group.");
            $('#add_to_queue').attr('disabled', false);
            return
        }

        if (!(validate_team())) {
            window.alert("Please Add name of non-deprecated 'Group Creators Team', to this Group.");
            $('#add_to_queue').attr('disabled', false);
            return
        }

        var missing = $('#set_missingDep').prop('checked');
        var items = [];
        var warningItems = [];
        kgb_check = false;
        packageFound = 0;
        for (var i = 0; i < formNum; i++) {
            var artifact = $('#packages_' + i).val();
            if (artifact != "") {
                if (typeof artifact === 'undefined') {
                    continue;
                } else {
                    var ver = $('#version_' + i).val();
                    var checkTaf = artifact.indexOf('TAF');
                    var checkTw = artifact.indexOf('TW');
                    if ((checkTaf === 0 || checkTaf === -1) && (checkTw === 0 || checkTw === -1)){
                        packageFound = 1;
                    }
                    var warning = $('#warning_' + i).text();
                    var kgbWarning = warning.indexOf('KGB');
                    if (kgbWarning >= 0) {
                        kgb_check = true;
                    }
                    warningItems.push(warning)
                    var teamInfo = $('#team_' + i).val();
                    items.push({
                        'packageName': artifact,
                        'version': ver,
                        'pkgTeams': teamInfo
                    });
                }
            }
        }
        var comment = $('#comment').val();
        if (comment) {
            comment = comment + ".\n";
        }
        if (items.length === 0) {
            window.alert("Please add at least one Artifact to this Group");
            $('#add_to_queue').attr('disabled', false);
            return
        }
        var jiraItems = [];
        for (var i = 0; i < formNumJira; i++) {
            var jira = $('#jiras_' + i).val();
            if (jira != "") {
                if (typeof jira === 'undefined') {
                    continue;
                } else {
                    jiraItems.push({
                        'issue': jira
                    });
                }
            }
        }
        if (jiraItems.length === 0) {
            window.alert("Please add JIRA Ticket(s) associated with this Group");
            $('#add_to_queue').attr('disabled', false);
            return
        }
        kgb_not_run_reason = $('#kgb_select_box_option').val();
        kgb_extra_info = $('#kgb_extra_info').val();
        if (kgb_check) {
            if (kgb_not_run_reason == null || kgb_not_run_reason == "") {
                get_kgb_reasons();
                $('#add_to_queue').attr('disabled', false);
                return;
            }
        }
        if (kgb_published_reason == "") {
            if (kgb_not_run_reason != "" && kgb_not_run_reason != null) {
                kgb_published_reason = kgb_published_reason + kgb_not_run_reason;
            }
            if (kgb_extra_info != "" && kgb_extra_info != null) {
                kgb_published_reason = kgb_published_reason + "::" + kgb_extra_info
            }
        }
        if (kgb_not_run_reason != "" && kgb_not_run_reason != null) {
            comment = comment + "KGB Not Passed Selected Reason: " + kgb_not_run_reason + ".\n";
        }
        if (kgb_extra_info != "" && kgb_extra_info != null) {
            comment = comment + "KGB Not Passed Extra Information: " + kgb_extra_info + ".\n";
        }
        cenmDgList = wrapCENMDeliveryGroupData();
        var revisions = {
            'groupId': '',
            'drop': dropData,
            'comment': comment,
            'team': $('#team').val(),
            'missingDep': missing,
            'warning': warningItems,
            'cenmDgList': cenmDgList,
            'items': items,
            'jiraIssues': jiraItems,
            'kgb_published_reason': kgb_published_reason,

        };
        if (group_data) {
            revisions['groupId'] = groupId;
        }

        $.ajax({
            url: "/api/product/ENM/testwareartifacts/" + artifact + "/includedinprioritytestsuite/",
            dataType: "json",
            async: true,
            success: function(json) {
                $.each(json, function(i, item) {
                    result = item[0].priorityTestware;
                    msg = "This Group has been set to have Missing Dependencies and will be placed in the queued section. \n Do you want to proceed?"
                    if (packageFound == 0) {
                        if (typeof groupId === 'undefined') {
                            if (missing === false) {
                                if (result) {
                                    msg = "This Group contains: Priority Test Suite Testware Artifacts, so it will be queued. \n Do you want to proceed?"
                                } else {
                                    msg = "This Group only contains TESTWARE artifacts and will NOT be queued. This Group will be delivered directly to the " + $('#drop').val().split(':').pop() + " drop. \n Do you want to proceed?"
                                }
                            }
                        } else {
                            if (missing === false) {
                                if (result) {
                                    msg = "This Group contains: Priority Test Suite Testware Artifacts, so it will be queued. \n Do you want to proceed?"
                                } else {
                                    msg = "This Group will be updated with only containing TESTWARE artifacts and will NOT be in the queued section. This Group will be delivered directly to the " + $('#drop').val().split(':').pop() + " drop. \n Do you want to proceed?"
                                }
                            }
                        }
                    } else {
                        if (groupId === 'None') {
                            if (missing === false) {
                                msg = "Do you really want create a new Group with these Versions?"
                            }
                        } else {
                            if (missing === false) {
                                msg = "Do you want to update this Group: " + groupId + " with these Versions?"
                            }
                        }

                    }
                    if (warningItems.length === 0) {
                        proceed = confirm(msg);
                    } else {
                        proceed = confirm(warningItems + msg);
                    }
                    if (proceed) {
                        $('body').addClass('loading');
                        $('#add_to_queue').attr('disabled', true);
                        $.ajax({
                            type: "POST",
                            url: "/addDeliveryGroup/",
                            datatype: "json",
                            data: JSON.stringify(revisions),
                            success: function(json) {
                                if (json[0].error != 0 && json[0].testwareGrpId == "None") {
                                    $('body').removeClass('loading');
                                    window.alert(json[0].error)
                                    $('#add_to_queue').attr('disabled', false);
                                    packageFound = 0;
                                    $('div#dynamic').empty();
                                } else if (json[0].error != 0 && json[0].testwareGrpId != "None") {
                                    $('body').removeClass('loading');
                                    window.alert(json[0].error)
                                    window.location.href = "/ENM/queue/" + $('#drop').val().split(':').pop();
                                } else if (typeof groupId === 'undefined') {
                                    if (json[0].testwareGrpId != "None") {
                                        window.location.href = "/ENM/queue/" + $('#drop').val().split(':').pop() + "/" + json[0].testwareGrpId + "/success/?section=delivered";
                                    } else {
                                        window.location.href = "/ENM/queue/" + $('#drop').val().split(':').pop();
                                    }
                                } else {
                                    if (json[0].testwareGrpId != "None") {
                                        window.location.href = "/ENM/queue/" + $('#drop').val().split(':').pop() + "/" + json[0].testwareGrpId + "/success/?section=delivered";
                                    } else {
                                        window.location.href = "/ENM/queue/" + $('#drop').val().split(':').pop() + "/" + groupId;
                                    }
                                }
                            },
                            error: function(xhr, textStatus, errorThrown) {
                                $('body').removeClass('loading');
                                alert("Issue adding group: " + (errorThrown ? errorThrown : xhr.status));
                                $('#add_to_queue').attr('disabled', false);
                            }
                        });
                    } else {
                        $('#add_to_queue').attr('disabled', false);
                        packageFound = 0;
                        kgb_check = false;
                        kgb_published_reason = "";
                        kgb_not_run_reason = "";
                        kgb_extra_info = "";
                        kgb_select_box.empty();
                        $("#kgb-reason").val("");
                        $("#kgb_extra_info").val("");
                    }
                });
            },
            error: function(xhr, textStatus, errorThrown) {
                $('body').removeClass('loading');
                alert("Issue Checking Package Version: " + (errorThrown ? errorThrown : xhr.status));
            }
        });
    }
    $(document).ajaxStop(function() {
        if (group_data && doVerCheck == 1) {
            for (var i = 0; i < formNum; i++) {
                var artifact = $('#packages_' + i).val();
                if (typeof artifact === 'undefined' || artifact == "") {
                    continue;
                } else {
                    var version = $('#version_' + i).val();
                    var warning_section = $('#warning_' + i);
                    version_check(artifact, version, warning_section, i)
                }
            }
            doVerCheck = 0;
        }
    });

});
