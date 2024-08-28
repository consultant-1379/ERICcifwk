$(document).ready(function() {
    let globalArtifactIndex = 1;
    let globalArtifactSum = 0;
    let dropName = '';
    let jiraSum = 0;
    let jiraIndexes = [];
    let enmdgSum = 0;
    let enmdgIndexes = [];
    let team_items = [];
    let service_group_items = [];
    let integration_chart_items = [];
    let integration_value_items = [];
    let impacted_dg_items = [];
    let artifact_autocomplete_items = [];
    let deliveryGroupNumber = $('#hidden_deliveryGroupNumber_div').html();
    let team_select_box = $('#team');
    let serviceGroupData_beforeEdit;
    let serviceGroupData_afterEdit = {};
    let integrationChart_beforeEdit;
    let integrationChart_afterEdit = {};
    let pipeline_beforeEdit;
    let pipeline_afterEdit = {};
    let integrationValue_beforeEdit;
    let integrationValue_afterEdit = {};
    let jira_beforeEdit;
    let jira_afterEdit = {};
    let dg_beforeEdit;
    let dg_afterEdit = {};
    let artifactFormList = [];
    let is_service_group_edited = false;
    let is_impacted_dg_edited = false;
    let is_integration_chart_edited = false;
    let is_integration_value_edited = false;
    let is_jira_edited = false;
    let is_pipeline_edited = false;
    $('#add_artifact').click(add_artifact_form);
    $('#add_jira').click(add_jira_selector);

    initPage(deliveryGroupNumber);

    async function initPage(deliveryGroupNumber) {
        populate_team_select();
        populate_service_group_select();
        populate_integration_chart();
        populate_integration_value();
        populate_existing_service_group();
        populate_existing_integration_chart();
        populate_existing_integration_value();
        populate_existing_pipeline();
        populate_existing_jira();
        populate_existing_impacted_dg();
    }

    async function populate_existing_service_group() {
        serviceGroupData_beforeEdit = await $.ajax({
            url: "/api/cloudNative/deliveryQueue/getServiceGroupInfo/" + deliveryGroupNumber,
            dataType: "json",
            success: function(data) {
                return data;
            },
            error: function(xhr, textStatus, errorThrown) {
                alert("Issue retrieving the service group data: " + (errorThrown ? errorThrown : xhr.status));
                return "";
            }
        });
        $('#drop').val(serviceGroupData_beforeEdit.drop);
        serviceGroupData_beforeEdit.teamEmail = serviceGroupData_beforeEdit.teamEmail || "";
        $('#team_email').val(serviceGroupData_beforeEdit.teamEmail);
        $('#team').val(serviceGroupData_beforeEdit.team);
        dropName = serviceGroupData_beforeEdit.drop;
        dropName = dropName.split(" ").pop();
        serviceGroupData_beforeEdit.serviceGroups.forEach(function(item, index) {
            add_artifact_form(item.serviceGroupName, item.gerritLinks,"service_group");
        });
    }

    async function populate_existing_integration_chart() {
        integrationChart_beforeEdit = await $.ajax({
            url: "/api/cloudNative/deliveryQueue/getIntegrationChartInfo/" + deliveryGroupNumber,
            dataType: "json",
            success: function(data) {
                return data;
            },
            error: function(xhr, textStatus, errorThrown) {
                alert("Issue retrieving integration chart data: " + xhr.responseText);
                return "";
            }
        });
        integrationChart_beforeEdit.integrationCharts.forEach(function(item, index) {
            add_artifact_form(item.integrationChartName, item.gerritLinks,"integration_chart");
        });
    }

    async function populate_existing_integration_value() {
        integrationValue_beforeEdit = await $.ajax({
            url: "/api/cloudNative/deliveryQueue/getIntegrationValueInfo/" + deliveryGroupNumber,
            dataType: "json",
            success: function(data) {
                return data;
            },
            error: function(xhr, textStatus, errorThrown) {
                alert("Issue retrieving integration value data: " + xhr.responseText);
                return "";
            }
        });
        integrationValue_beforeEdit.integrationValues.forEach(function(item, index) {
            add_artifact_form(item.integrationValueName, item.gerritLinks,"integration_value");
        });
    }

    async function populate_existing_pipeline() {
        pipeline_beforeEdit = await $.ajax({
            url: "/api/cloudNative/deliveryQueue/getPipelineInfo/" + deliveryGroupNumber,
            dataType: "json",
            success: function(data) {
                return data;
            },
            error: function(xhr, textStatus, errorThrown) {
                alert("Issue retrieving pipeline data: " + xhr.responseText);
                return "";
            }
        });
        pipeline_beforeEdit.pipelines.forEach(function(item, index) {
            add_artifact_form(item.pipelineName, item.gerritLinks,"pipeline");
        });
    }

    async function populate_existing_impacted_dg() {
        dg_beforeEdit = await $.ajax({
            url: "/api/cloudNative/deliveryQueue/getImpactedDeliveryGroupInfo/" + deliveryGroupNumber,
            dataType: "json",
            data: {
                "queueType": "CENM"
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
            add_enmdg_selector(item, dropName);
        });
        $(document).on("click", "#add_enmdg", function() {
            add_enmdg_selector("", dropName);
        });
    }

    async function populate_existing_jira() {
        jira_beforeEdit = await $.ajax({
            url: "/api/cloudNative/deliveryQueue/getJiraInfo/" + deliveryGroupNumber,
            dataType: "json",
            success: function(data) {
                return data;
            },
            error: function(xhr, textStatus, errorThrown) {
                alert("Issue retrieving jira data: " + (errorThrown ? errorThrown : xhr.status));
                return "";
            }
        });
        jira_beforeEdit.jiraList.forEach(function(item, index) {
            add_jira_selector(item);
        });
        $(document).on("click", "#edit_delivery_group", function() {
            edit_delivery_group();
        });
    }

    function populate_team_select() {
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
            },
            error: function(xhr, textStatus, errorThrown) {
                alert("Issue retrieving the list of Teams: " + (errorThrown ? errorThrown : xhr.status));
            }
        });
        let $team_form_warning = $("<br><p id='team_warning' class='team_form_warning'></p><br>");
        $(document).on("blur", '#team', function() {
            let teamValue = $('#team').val();
            team_warning_section = $('#team_warning');
            team_warning_section.text("");
            team_warning_section.hide();
            validate_team(teamValue, team_warning_section);
        });
        $team_form_warning.text("");
        $team_form_warning.hide();
        team_select_box.after($team_form_warning);
    }

    function populate_enm_dg_select(dropNumber, elementId) {
        let input_element = $(elementId);
        if (impacted_dg_items.length > 1) {
            input_element.autocomplete({
                source: impacted_dg_items
            });
            return;
        }
        $.ajax({
            url: "/api/cloudNative/getDeliveryGroupsByDrop/ENM",
            dataType: "json",
            data: {
                "dropName": dropNumber
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
                alert("Issue retrieving the list of ENM DG for drop " + dropName + ": " + xhr.responseText);
            }
        });
    }

    function validate_team(teamValue, team_warning_section) {
        if (teamValue.trim().length === 0) {
            let warningText = "ERROR: Team name can not be empty";
            team_warning_section.text(warningText);
            team_warning_section.show();
            $('#edit_service_group').attr('disabled', true);
        } else {
            team_warning_section.text("");
            team_warning_section.hide();
            $('#edit_service_group').attr('disabled', false);
        }
    }

    function validateGerritLinkbyContainer() {
        let gerritInputIdList = [];
        $(' .artifact_input_form_gerrit_input').each(function() {
            gerritInputIdList.push(this.id);
        });
        let errFlag = false;
        for (let i = 0; i < gerritInputIdList.length; i++) {
            let currValue = $('#' + gerritInputIdList[i]).val().trim();
            let currWarningId = 'gerrit_warning_' + gerritInputIdList[i].split('gerrit_input_')[1];
            if (currValue.length === 0) {
                errFlag = true;
                $('#' + currWarningId).text('Gerrit link can not be empty.');
                $('#' + currWarningId).show();
                $('#edit_delivery_group').attr('disabled', true);
                continue;
            } else {
                $('#' + currWarningId).text('');
                $('#' + currWarningId).hide();
            }
            for (let j = i + 1; j < gerritInputIdList.length; j++) {
                let nextValue = $('#' + gerritInputIdList[j]).val().trim();
                let nextWarningId = 'gerrit_warning_' + gerritInputIdList[j].split('gerrit_input_')[1];
                if (nextValue.length === 0) {
                    errFlag = true;
                    $('#' + nextWarningId).text('Gerrit link can not be empty.');
                    $('#' + nextWarningId).show();
                    $('#edit_delivery_group').attr('disabled', true);
                    continue;
                } else if (currValue == nextValue) {
                    errFlag = true;
                    $('#' + currWarningId).text('Duplicate gerrit value found. Please modify.');
                    $('#' + currWarningId).show();
                    $('#' + nextWarningId).text('Duplicate gerrit value found. Please modify.');
                    $('#' + nextWarningId).show();
                    $('#edit_delivery_group').attr('disabled', true);
                    continue;
                }
            }
        }
        if (errFlag === false) {
            $('#edit_delivery_group').attr('disabled', false);
        }
    }

    function validateArtifactbyContainer() {
        let artifactInputList = [];
        if ($('.artifact_input_form').length === 0) {
            $('#edit_delivery_group').attr('disabled', false);
            return;
        }
        $(' .artifact_input_form').each(function() {
            artifactInputList.push(this.id);
        });
        let errFlag = false;
        for (let i = 0; i < artifactInputList.length; i++) {
            let currValue = $('#' + artifactInputList[i]).val().trim();
            let currWarningId = 'warning_' + artifactInputList[i].split('input_')[1];
            if (currValue.length === 0) {
                errFlag = true;
                $('#' + currWarningId).text('Artifact can not be empty.');
                $('#' + currWarningId).show();
                $('#edit_delivery_group').attr('disabled', true);
                break;
            } else {
                $('#' + currWarningId).text('');
                $('#' + currWarningId).hide();
            }
            for (let j = i + 1; j < artifactInputList.length; j++) {
                let nextValue = $('#' + artifactInputList[j]).val().trim();
                let nextWarningId = 'warning_' + artifactInputList[j].split('input_')[1];
                if (nextValue.length === 0) {
                    errFlag = true;
                    $('#' + nextWarningId).text('Artifact can not be empty.');
                    $('#' + nextWarningId).show();
                    $('#edit_delivery_group').attr('disabled', true);
                    break;
                } else if (currValue === nextValue) {
                    errFlag = true;
                    $('#' + currWarningId).text('Duplicate Artifact found. Please modify.');
                    $('#' + currWarningId).show();
                    $('#' + nextWarningId).text('Duplicate Artifact found. Please modify.');
                    $('#' + nextWarningId).show();
                    $('#edit_delivery_group').attr('disabled', true);
                    break;
                } else {
                    $('#' + currWarningId).text('');
                    $('#' + currWarningId).hide();
                    $('#' + nextWarningId).text('');
                    $('#' + nextWarningId).hide();
                }
            }
        }
        if (errFlag === false) {
            $('#edit_delivery_group').attr('disabled', false);
        }
        return errFlag;
    }

    function autoCompleteHandler(artifactForm,formNum){
        if (artifactForm.find('#input_hidden_'+formNum).val() === "integration_chart" || artifactForm.find('#category_'+formNum).val() === "integration_chart"){
            artifact_autocomplete_items = integration_chart_items;
        }else if (artifactForm.find('#input_hidden_'+formNum).val() === "integration_value" || artifactForm.find('#category_'+formNum).val() === "integration_value"){
            artifact_autocomplete_items = integration_value_items;
        }else if (artifactForm.find('#input_hidden_'+formNum).val() === "service_group" || artifactForm.find('#category_'+formNum).val() === "service_group"){
            artifact_autocomplete_items = service_group_items;
        }else{
            artifact_autocomplete_items = [];
        }
        artifactForm.find("#input_"+formNum).autocomplete({
            source: artifact_autocomplete_items
        });
    }

    function add_artifact_form(artifact_name,gerritLinks,artifact_type){
        let formNum = globalArtifactIndex;
        let formLabel = {"service_group":"Service Group","integration_value":"Integration Value","pipeline":"Pipeline","integration_chart":"Integration Chart"}
        let formCategory = "";
        let $artifact_form_label = "";
        let $artifact_form_input = "";
        let $category_select = "";
        let $artifact_form_hidden_input = "";
        artifactFormList.push(formNum);
        let $artifact_form_container = $("<div id='div_"+formNum+"' class='artifact_div' style='border-style: groove'></div>");
        let $artifact_form_removal = $("<a id='remove_"+formNum+"' class='img'><img src='/static/images/delete.png' class='artifact_input_form_delete_img' title='Remove Package Input' /></a><br>");
        let $artifact_form_warning = $("<br><p id='warning_" + formNum + "' class='artifact_input_form_warning'></p><br>");
        let $artifact_form_gerrit_container = $("<div id='gerrit_div_" + formNum + "' class='gerrit_container'></div>");
        let $artifact_form_gerrit_label = $("<label for='gerrit_label_" + formNum + "'>Gerrit Link:</label>");
        let $artifact_form_gerrit_input = $("<input id='gerrit_input_" + formNum + "' class='artifact_input_form_gerrit_input'>");
        let $artifact_form_gerrit_warning = $("<p id='gerrit_warning_" + formNum + "' class='artifact_input_form_warning'></p><br>");

        if(artifact_type){
            formCategory=artifact_type;
            $artifact_form_label = $("<br><label for='input_"+formNum+"'>"+formLabel[formCategory]+":</label>");
            $artifact_form_input = $("<input id='input_"+formNum+"' class='artifact_input_form'>" );
            $artifact_form_hidden_input = $("<input id='input_hidden_"+formNum+"' value='"+formCategory+"' type='hidden'>" );
            $(document).on("click", ".artifact_input_form", function() {
                autoCompleteHandler($artifact_form_container,formNum);
            });
        }else{
            $category_select = $('<label>Category:</label><select id="category_'+formNum+'"><option value="none" selected>...</option><option value="service_group" id="service_group">Service Group</option><option value="integration_chart" id="integration_chart">Integration Chart</option><option value="integration_value" id="integration_value">Integration Value</option><option value="pipeline" id="pipeline">Pipeline Code</option></select>');
            $artifact_form_label = $("<br><label for='input_"+formNum+"'>Repository:</label>");
            $artifact_form_input = $("<input id='input_"+formNum+"' class='artifact_input_form'>" );
            $(document).on("change", "#category_"+formNum, function() {
                autoCompleteHandler($artifact_form_container,formNum);
            });
        }

        $(document).on("click", "#remove_" + formNum, function() {
            removeArtifactAction(formNum);
        });
        $(document).on("blur", "#gerrit_input_" + formNum , function() {
            validateGerritLinkbyContainer();
        });
        $(document).on("blur", '#input_' + formNum, function() {
            validateArtifactbyContainer();
        });

        $artifact_form_warning.hide();
        $artifact_form_gerrit_warning.hide();
        $artifact_form_gerrit_container.prepend($artifact_form_gerrit_label, [$artifact_form_gerrit_input, $artifact_form_gerrit_warning]);
        $artifact_form_container.prepend($category_select,$artifact_form_label, [$artifact_form_hidden_input,$artifact_form_input, $artifact_form_removal, $artifact_form_warning, $artifact_form_gerrit_container]);
        globalArtifactIndex += 1;
        globalArtifactSum += 1;
        if(artifact_name.length>0){
            $artifact_form_input.val(artifact_name);
            $artifact_form_gerrit_input.val(gerritLinks)
        }
        $('#add_artifact').before($artifact_form_container);
    }

    function populate_service_group_select() {
        $.ajax({
            url: "/api/cloudNative/getCNImage/",
            dataType: "json",
            success: function(data) {
                $.each(data, function(i, item) {
                    service_group_items.push(item.image_name);
                });
            },
            error: function(xhr, textStatus, errorThrown) {
                alert("Issue retrieving the list of service groups: " + xhr.responseText);
            }
        });
    }

    function populate_integration_chart() {
        $.ajax({
            url: "/api/cloudNative/getCNProduct/Integration Chart",
            dataType: "json",
            success: function(json) {
                $.each(json, function(i, item) {
                    integration_chart_items.push(item.product_name);
                });
            },
            error: function(xhr, textStatus, errorThrown) {
                alert("Issue retrieving the list of integration charts: " + xhr.responseText);
            }
        });
    }

    function populate_integration_value() {
        $.ajax({
            url: "/api/cloudNative/getCNProduct/Integration Value",
            dataType: "json",
            success: function(json) {
                $.each(json, function(i, item) {
                    integration_value_items.push(item.product_name);
                });
            },
            error: function(xhr, textStatus, errorThrown) {
                alert("Issue retrieving the list of integration values: " + xhr.responseText);
            }
        });
    }

    function add_jira_selector(jiraValue) {
        let formNumJira = jiraSum + 1;
        let $jira_container = $("<div id='jirasdiv_" + formNumJira  + "' class='jiradiv'></div>")
        let $jira_label = $("<br><label for='jiras_" + formNumJira + "' id='jiraslabel_" + formNumJira + "'>JIRA Ticket:</label>")
        let $jira_input = $("<input id='jiras_input_" + formNumJira + "' class='delivery_form_jira'>")
        let $jira_removal = $("<a id='jiraremoves_" + formNumJira + "' class='img' > <img src='/static/images/delete.png' class='delivery_form_delete_img' title='Remove Jira Issue Input' /></a>")
        let $jira_warning = $("<br><p id='jira_warning_" + formNumJira + "' class='jira_form_warning'></p><br>")
        $(document).on("click", "#jiraremoves_" + formNumJira, function() {
            removeJiraAction(formNumJira);
        });
        $(document).on("blur", '#jiras_input_' + formNumJira, function() {
            let jiraNum = $('#jiras_input_' + formNumJira).val();
            warning_jira_section = $('#jira_warning_' + formNumJira);
            warning_jira_section.text("");
            warning_jira_section.hide();
            validate_jira(jiraNum, warning_jira_section, formNumJira);
        });
        $jira_container.prepend($jira_label, [$jira_input, $jira_removal, $jira_warning]);
        $("#add_jira").before($jira_container);
        warning_section = $('#jira_warning_' + formNumJira);
        warning_section.hide();
        jiraIndexes.push(formNumJira);
        jiraSum = jiraSum + 1;
        if (jiraValue.length>0) {
            $('#jiras_input_' + formNumJira).val(jiraValue);
        }
    }

    function add_enmdg_selector(enmDgValue, dropName) {
        let formNum = enmdgSum + 1;
        let $enmdg_container = $("<div id='enmdgdiv_" + formNum  + "' class='enmdgdiv'></div>")
        let $enmdg_label = $("<br><label for='enmdg_" + formNum + "' id='enmdglabel_" + formNum + "'>Impacted ENM Delivery Group:</label>")
        let $enmdg_input = $("<input id='enmdg_" + formNum + "' class='delivery_form_enm_dg'>")
        let $enmdg_removal = $("<a id='enmdgremoves_" + formNum + "' class='img' > <img src='/static/images/delete.png' class='delivery_form_delete_img' title='Remove Impacted ENM Devlivery Group Input' /></a>")
        let $enmdg_warning = $("<br><p id='enmdg_warning_" + formNum + "' class='delivery_form_warning'></p><br>")
        $(document).on("click", "#enmdgremoves_" + formNum, function() {
            removeENMDGAction(formNum);
        });
        $(document).on("blur", '#enmdg_' + formNum, function() {
            warning_section = $('#enmdg_warning_' + formNum);
            warning_section.text("");
            warning_section.hide();
            validateENMDGField(warning_section, formNum);
        });
        $enmdg_container.prepend($enmdg_label, [$enmdg_input, $enmdg_removal, $enmdg_warning]);
        $("#add_enmdg").before($enmdg_container);
        populate_enm_dg_select(dropName, '#enmdg_' + formNum);
        warning_section = $('#enmdg_warning_' + formNum);
        warning_section.hide();
        enmdgIndexes.push(formNum);
        enmdgSum = enmdgSum + 1;
        if (enmDgValue) {
            $('#enmdg_' + formNum).val(enmDgValue);
        }
    }

    function removeArtifactAction(formNum) {
        $("#div_" + formNum).remove();
        validateArtifactbyContainer();
        let index = artifactFormList.indexOf(formNum);
        artifactFormList.splice(index,1);
        globalArtifactSum = globalArtifactSum - 1;
    }

    function validateENMDGField(warning_section, formNum) {
        $('#edit_delivery_group').attr('disabled', true);
        $('#add_enmdg').attr('disabled', true);
        if ($('#enmdgdiv_' + formNum + ' .delivery_form_enm_dg').length === 0) {
            $('#edit_delivery_group').attr('disabled', false);
            $('#add_enmdg').attr('disabled', false);
            return;
        }
        let enmDgValue = $('#enmdgdiv_' + formNum + ' .delivery_form_enm_dg').val();
        for(let i = 0; i < enmdgIndexes.length; i++) {
            let index = enmdgIndexes[i];
            let divId = '#enmdgdiv_' + index;
            let enmDgQuery = $('.delivery_form_enm_dg');
            let currentENMDGName = $(divId).find(enmDgQuery).val();
            if (currentENMDGName === enmDgValue && formNum != index && currentENMDGName.trim().length != 0) {
                let warningText = "ERROR: Duplicate Impacted ENM delivery group number found for " + currentENMDGName;
                warning_section.text(warningText);
                warning_section.show();
                $('#edit_delivery_group').attr('disabled', true);
                $('#add_enmdg').attr('disabled', true);
                break;
            } else {
                warning_section.text("");
                warning_section.hide();
                $('#edit_delivery_group').attr('disabled', false);
                $('#add_enmdg').attr('disabled', false);
            }
        }
    }

    function removeJiraAction(jiraIndex) {
        let proceed = confirm("Do you really want to remove this jira ticket?");
        if (proceed) {
            $("#jirasdiv_" + jiraIndex).remove();
            validate_jira(null,null,jiraIndex);
        }
        jiraSum = jiraSum - 1;
        let index = jiraIndexes.indexOf(jiraIndex);
        jiraIndexes.splice(index,1);
    }

    function removeENMDGAction(dgIndex) {
        let proceed = confirm("Do you really want to remove this Impacted Delivery Group?");
        if (proceed) {
            $("#enmdgdiv_" + dgIndex).remove();
            validateENMDGField(null, dgIndex);
        }
        enmdgSum = enmdgSum - 1;
        let index = enmdgIndexes.indexOf(dgIndex);
        enmdgIndexes.splice(index,1);
    }

    function validate_jira(jiraNum, warning_jira_section, formNumJira) {
        $('#edit_delivery_group').attr('disabled', true);
        $('#add_jira').attr('disabled', true);
        if ($('#jirasdiv_' + formNumJira + ' .delivery_form_jira').length === 0) {
            $('#edit_delivery_group').attr('disabled', false);
            $('#add_jira').attr('disabled', false);
            return;
        }
        jiraNum = jiraNum.replace("[", "");
        jiraNum = jiraNum.replace("]", "");
        jiraNum = jiraNum.trim();
        $.ajax({
            url: "/api/tools/jiravalidation/issue/" + jiraNum + "/",
            dataType: "json",
            success: function(json) {
                var warnings = [];
                warning_jira_section.text("");
                $.each(json, function(i, item) {
                    if (item['warning'] != null){
                        warning_jira_section.text(item['warning']);
                        warning_jira_section.show();
                        $("#jirasdiv_" + formNumJira).addClass('jiraWarning');
                        warnings.push(item);
                        $('#add_jira').attr('disabled', true);
                        $('#edit_delivery_group').attr('disabled', true);
                    } else {
                        $("#jirasdiv_" + formNumJira).removeClass('jiraWarning');
                        warning_jira_section.hide();
                        $('#add_jira').attr('disabled', false);
                        $('#edit_delivery_group').attr('disabled', false);
                    }
                });
            },
            error: function(xhr, textStatus, errorThrown) {
                let proceed_jira = "";
                if (errorThrown === "NOT FOUND") {
                    alert("JIRA Ticket: " + jiraNum + " is invalid. Please enter in a valid JIRA Ticket. (Example: CIS-11807 or https://jira-oss.seli.wh.rnd.internal.ericsson.com/browse/CIS-11807)");
                } else {
                    message = "Issue retrieving data from JIRA, would you like to proceed anyway?";
                    proceed_jira = confirm(message);
                }
                if (proceed_jira){
                    $('#add_jira').attr('disabled', false);
                    $('#edit_delivery_group').attr('disabled', false);
                } else {
                    $('#jiras_input_' + formNumJira).val("");
                    $('#add_jira').attr('disabled', true);
                    $('#edit_delivery_group').attr('disabled', true);
                }
            }
        });
    }

    function wrapArtifactData(){
        integrationChart_afterEdit["integrationCharts"] = [];
        serviceGroupData_afterEdit["serviceGroups"] = [];
        integrationValue_afterEdit["integrationValues"] = [];
        pipeline_afterEdit["pipelines"] = [];
        for (let i = 0; i < artifactFormList.length; i++){
            let index = artifactFormList[i];
            let currArtifact = $(document).find('#div_'+index);
            let gerritLinkList = currArtifact.find(".artifact_input_form_gerrit_input");
            let gerritResultList = [];
            let artifactName = currArtifact.find("#input_"+index).val();
            let gerritLinkSum = gerritLinkList.length;
            let result;
            for (let j = 0; j < gerritLinkSum ; j++) {
                if (gerritLinkList[j].value.length != 0) {
                    gerritResultList.push(gerritLinkList[j].value);
                }
            }
            if (currArtifact.find('#input_hidden_'+index).val() === "service_group" || currArtifact.find('#category_'+index).val() === "service_group"){
                result = {'serviceGroupName': artifactName, 'gerritLinks': gerritResultList};
                serviceGroupData_afterEdit["serviceGroups"].push(result);
            }
            if (currArtifact.find('#input_hidden_'+index).val() === "integration_chart" || currArtifact.find('#category_'+index).val() === "integration_chart"){
                result = {'integrationChartName': artifactName, 'gerritLinks': gerritResultList};
                integrationChart_afterEdit["integrationCharts"].push(result);
            }
            if (currArtifact.find('#input_hidden_'+index).val() === "integration_value" || currArtifact.find('#category_'+index).val() === "integration_value"){
                result = {'integrationValueName': artifactName, 'gerritLinks': gerritResultList};
                integrationValue_afterEdit["integrationValues"].push(result);
            }
            if (currArtifact.find('#input_hidden_'+index).val() === "pipeline" || currArtifact.find('#category_'+index).val() === "pipeline"){
                result = {'pipelineName': artifactName, 'gerritLinks': gerritResultList};
                pipeline_afterEdit["pipelines"].push(result);
            }
        }
    }

    function wrapImpactedDGNumber() {
        dg_afterEdit["impactedDeliveryGroupNumberList"] = []
        for (let i = 0; i < enmdgSum; i++) {
            let enmDgElement = $("#enmdg_" + enmdgIndexes[i]);
            if (enmDgElement.length === 0) {
                continue;
            }
            dg_afterEdit["impactedDeliveryGroupNumberList"].push(Number(enmDgElement.val().trim()));
        }
    }

    function wrapJira() {
        jira_afterEdit["jiraList"] = []
        for (let i = 0; i < jiraSum; i++) {
            let jiraElement = $("#jiras_input_" + jiraIndexes[i]);
            if (jiraElement.length === 0) {
                continue;
            }
            jira_afterEdit["jiraList"].push(jiraElement.val().trim());
        }
    }

    function submit_dg_edits(is_service_group_edited, is_integration_chart_edited, is_integration_value_edited, is_pipeline_edited, is_impacted_dg_edited, is_jira_edited){
        let message = '';
        let params = {
            'is_service_group_edited': is_service_group_edited,
            'is_integration_chart_edited': is_integration_chart_edited,
            'is_integration_value_edited': is_integration_value_edited,
            'is_pipeline_edited': is_pipeline_edited,
            'is_impacted_dg_edited': is_impacted_dg_edited,
            'is_jira_edited': is_jira_edited,
            'serviceGroupBeforeEdit': serviceGroupData_beforeEdit,
            'serviceGroupAfterEdit': serviceGroupData_afterEdit,
            'integrationChartBeforeEdit': integrationChart_beforeEdit,
            'integrationChartAfterEdit': integrationChart_afterEdit,
            'integrationValueBeforeEdit': integrationValue_beforeEdit,
            'integrationValueAfterEdit': integrationValue_afterEdit,
            'pipelineBeforeEdit': pipeline_beforeEdit,
            'pipelineAfterEdit': pipeline_afterEdit,
            'impactedDGBeforeEdit': dg_beforeEdit,
            'impactedDGAfterEdit': dg_afterEdit,
            'jiraBeforeEdit': jira_beforeEdit,
            'jiraAfterEdit': jira_afterEdit,
        };
        $.ajax({
            type: "PUT",
            url: "api/cloudNative/deliveryQueue/editCNDeliveryGroup/" + deliveryGroupNumber + "/",
            dataType: "json",
            headers: { "X-CSRFToken": getCookie("csrftoken") },
            data: JSON.stringify(params),
            success: function(result) {
                message = "Successfully updated CN Delivery Group.";
                $("body").removeClass('loading');
                alert(message);
                window.location.href = '/cloudNative/Cloud Native ENM/deliveryQueue/' + dropName + '/' + deliveryGroupNumber + '/?section=queued';
            },
            error: function(xhr, textStatus, errorThrown) {
                message = "Issue updating CN Delivery Group: " + xhr.responseText;
                $("body").removeClass('loading');
                confirm(message);
            }
        });
    }

    function edit_delivery_group() {
        if (validateArtifactbyContainer() === true){
            alert("Please resolve all warnings!");
        } else {
            let team_query = $('.delivery_form_creator');
            let team_email_query = $('.delivery_form_team_email');
            let proceed = confirm("Do you want to edit delivery group " + deliveryGroupNumber + " for these data?");
            if (proceed) {
                $('body').addClass('loading');
                wrapImpactedDGNumber();
                serviceGroupData_afterEdit["teamEmail"] = team_email_query.val().trim();
                serviceGroupData_afterEdit["drop"] = serviceGroupData_beforeEdit.drop;
                wrapArtifactData();
                wrapJira();
                serviceGroupData_afterEdit["team"] = team_query.val().trim();
                if(JSON.stringify(serviceGroupData_afterEdit) !== JSON.stringify(serviceGroupData_beforeEdit)){
                    is_service_group_edited = true;
                }

                if(JSON.stringify(integrationChart_afterEdit["integrationCharts"]) != JSON.stringify(integrationChart_beforeEdit["integrationCharts"])){
                    is_integration_chart_edited = true;
                }

                if(JSON.stringify(integrationValue_afterEdit["integrationValues"]) != JSON.stringify(integrationValue_beforeEdit["integrationValues"])){
                    is_integration_value_edited = true;
                }

                if(JSON.stringify(pipeline_afterEdit["pipelines"]) != JSON.stringify(pipeline_beforeEdit["pipelines"])){
                    is_pipeline_edited = true;
                }

                if (JSON.stringify(dg_beforeEdit["impactedDeliveryGroupNumberList"]) != JSON.stringify(dg_afterEdit["impactedDeliveryGroupNumberList"])){
                    is_impacted_dg_edited = true;
                }

                if(JSON.stringify(jira_beforeEdit["jiraList"]) != JSON.stringify(jira_afterEdit["jiraList"])){
                    is_jira_edited = true;
                }
                let edit_flags = [is_service_group_edited, is_impacted_dg_edited, is_integration_chart_edited, is_integration_value_edited, is_jira_edited, is_pipeline_edited];
                for (i = 0; i < edit_flags.length; i++){
                    if(edit_flags[i] === true){
                        submit_dg_edits(is_service_group_edited, is_integration_chart_edited, is_integration_value_edited, is_pipeline_edited, is_impacted_dg_edited, is_jira_edited);
                        break
                    }
                    if (i+1 === edit_flags.length){
                        alert("No changes detected");
                        $('body').removeClass('loading');
                    }
                }
            }
        }
    }

    function getCookie(c_name) {
        if (document.cookie.length > 0) {
            c_start = document.cookie.indexOf(c_name + "=");
            if (c_start != -1)
            {
                c_start = c_start + c_name.length + 1;
                c_end = document.cookie.indexOf(";", c_start);
                if (c_end === -1) c_end = document.cookie.length;
                return unescape(document.cookie.substring(c_start,c_end));
            }
        }
        return "";
    }
});

