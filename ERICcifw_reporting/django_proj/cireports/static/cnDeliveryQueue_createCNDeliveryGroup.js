$(document).ready(function() {
    let globalArtifactIndex = 1;
    let globalArtifactSum = 0;
    let jiraSum = 0;
    let jiraIndex = 1;
    let enmdgSum = 0;
    let enmdgIndex = 1;
    let artifactFormDict={
        // 'form_1': {'gerrit_sum': 1, 'gerrit_index': 1}
    };
    let jiraForms = {};
    let enmdgForms = {};
    let team_items = [];
    let service_group_items = [];
    let integration_chart_items = [];
    let integration_value_items = [];
    let impacted_dg_items = [];
    let artifact_autocomplete_items = [];
    let productName = $('#hidden_product_div').html();
    let dropName = $('#hidden_drop_div').html();

    drop_select_box = $('#drop');
    populate_drop_select();
    populate_integration_value();
    populate_integration_chart();
    populate_service_group_select();
    team_input_box = $('#team');
    populate_team_select();
    dg_input_box = $('#enm_dg_input');
    populate_enm_dg_select(dropName);
    missing_dep_comment = $('#missing_dep_comment')
    missing_dep_comment.hide();
    initMissingDepFields();

    $('#add_jira').click(add_jira_selector);
    $('#add_artifact').click(add_artifact_form);
    $('#add_enmdg').click(add_enmdg_selector);
    $('#add_to_queue').click(add_to_queue);
    add_jira_selector();

    function initMissingDepFields() {
        $(document).on("click", "#set_missingDep", function() {
            checkMissingDepValue();
        });
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
            url: "/api/cloudNative/getDeliveryGroupsByDrop/ENM/",
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

    function populate_drop_select() {
        let result = productName + " " + dropName;
        drop_select_box.append('<option value="' + result + '" id="' + result + '">' + result + '</option>');
    }

    function populate_team_select() {
        $.ajax({
            url: "/api/cireports/component/ENM/Team/",
            dataType: "json",
            success: function(json) {
                team_input_box.append('<option value="" id=""></option>');
                $.each(json, function(i, item) {
                    team_input_box.append('<option value="' + item.element + '" id="' + item.element + '">' + item.element + '</option>');
                    team_items.push(item.element);
                });
                team_input_box.autocomplete({
                    source: team_items
                });
            },
            error: function(xhr, textStatus, errorThrown) {
                alert("Issue retrieving the list of Teams: " + xhr.responseText);
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
        team_input_box.after($team_form_warning);
    }

    function removeArtifactAction(formNum) {
        $("#div_" + formNum).remove();
        validateArtifactbyContainer();
        delete artifactFormDict['form_' + formNum];
        globalArtifactSum = globalArtifactSum - 1;
    }

    function removeJiraAction(jiraFormNum) {
        let proceed = confirm("Do you really want to remove this jira ticket?");
        if (proceed) {
            $("#jirasdiv_" + jiraFormNum).remove();
            delete jiraForms[jiraFormNum];
            jiraSum = jiraSum - 1;
        }
        if (jiraSum === 0){
            $('#add_jira').attr('disabled',false);
            $('#add_to_queue').attr('disabled',false);
        }
    }

    function removeENMDGAction(linkNum) {
        let proceed = confirm("Do you really want to remove this jira ticket?");
        if (proceed) {
            $("#enmdgdiv_" + linkNum).remove();
            delete enmdgForms[linkNum];
            enmdgSum = enmdgSum - 1;
        }
    }

    function validate_jira(jiraNum, warning_jira_section, formNumJira) {
        $('#add_jira').attr('disabled',true);
        $('#add_to_queue').attr('disabled',true);
        jiraNum = jiraNum.replace("[", "");
        jiraNum = jiraNum.replace("]", "");
        jiraNum = jiraNum.trim();
        $.ajax({
            url: "/api/cloudNative/jiravalidation/issue/" + jiraNum + "/",
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
                        $('#add_to_queue').attr('disabled', true);
                    } else {
                        $("#jirasdiv_" + formNumJira).removeClass('jiraWarning');
                        warning_jira_section.hide();
                        $('#add_to_queue').attr('disabled', false);
                        $('#add_jira').attr('disabled',false);
                    }
                });
            },
            error: function(xhr, textStatus, errorThrown) {
                let proceed_jira = "";
                if (errorThrown === "NOT FOUND") {
                    alert("JIRA Ticket: " + jiraNum + " is invalid. Please enter in a valid JIRA Ticket. (Example: TORF-417819)");
                } else {
                    message = "Issue retrieving data from JIRA, would you like to proceed anyway?";
                    proceed_jira = confirm(message);
                }
                if (proceed_jira){
                    $('#add_to_queue').attr('disabled', false);
                    $('#add_jira').attr('disabled',false);
                } else {
                    $('#jiras_input_' + formNumJira).val("");
                    $('#add_to_queue').attr('disabled', true);
                }
            }
        });
    }

    function validateArtifactbyContainer() {
        let artifactInputList = [];
        if ($('.artifact_input_form').length === 0) {
            $('#add_to_queue').attr('disabled', false);
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
                $('#add_to_queue').attr('disabled', true);
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
                    $('#add_to_queue').attr('disabled', true);
                    break;
                } else if (currValue === nextValue) {
                    errFlag = true;
                    $('#' + currWarningId).text('Duplicate Artifact found. Please modify.');
                    $('#' + currWarningId).show();
                    $('#' + nextWarningId).text('Duplicate Artifact found. Please modify.');
                    $('#' + nextWarningId).show();
                    $('#add_to_queue').attr('disabled', true);
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
            $('#add_to_queue').attr('disabled', false);
        }
        return errFlag;
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
                $('#add_to_queue').attr('disabled', true);
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
                    $('#add_to_queue').attr('disabled', true);
                    continue;
                } else if (currValue === nextValue) {
                    errFlag = true;
                    $('#' + currWarningId).text('Duplicate gerrit value found. Please modify.');
                    $('#' + currWarningId).show();
                    $('#' + nextWarningId).text('Duplicate gerrit value found. Please modify.');
                    $('#' + nextWarningId).show();
                    $('#add_to_queue').attr('disabled', true);
                    continue;
                }
            }
        }
        if (errFlag === false) {
            $('#add_to_queue').attr('disabled', false);
        }
    }

    function validate_team(teamValue, team_warning_section) {
        if (teamValue.trim().length === 0) {
            let warningText = "ERROR: Team name can not be empty";
            team_warning_section.text(warningText);
            team_warning_section.show();
            $('#add_to_queue').attr('disabled', true);
        } else {
            team_warning_section.text("");
            team_warning_section.hide();
            $('#add_to_queue').attr('disabled', false);
        }
    }

    function validateENMDGField(warning_section, formNum) {
        let enmDgValue = $('#enmdgdiv_' + formNum + ' .delivery_form_enm_dg').val();
        for(let index = 1; index <= enmdgSum; index++) {
            let divId = '#enmdgdiv_' + index;
            let enmDgQuery = $('.delivery_form_enm_dg');
            let currentENMDGName = $(divId).find(enmDgQuery).val();
            if (currentENMDGName === enmDgValue && formNum != index && currentENMDGName.trim().length != 0) {
                let warningText = "ERROR: Duplicate Impacted ENM delivery group number found for " + currentENMDGName;
                warning_section.text(warningText);
                warning_section.show();
                $('#add_to_queue').attr('disabled', true);
                break;
            } else {
                warning_section.text("");
                warning_section.hide();
                $('#add_to_queue').attr('disabled', false);
            }
        }
    }

    function check_jira_inputs() {
        return wrapJiraData().length === jiraSum && jiraSum > 0;
    }

    function add_artifact_form(){
        let formNum = globalArtifactIndex;
        let $category_select= $('<label>Category:</label><select id="category_'+formNum+'"><option value="none" selected>...</option><option value="service_group" id="service_group">Service Group</option><option value="integration_chart" id="integration_chart">Integration Chart</option><option value="integration_value" id="integration_value">Integration Value</option><option value="pipeline" id="pipeline">Pipeline Code</option></select>');
        artifactFormDict['form_'+formNum]={'gerrit_sum':0,'gerrit_index':1};
        let linkNum = artifactFormDict['form_'+formNum].gerrit_index;
        let $artifact_form_container =$("<div id='div_"+formNum+"' class='artifact_div' style='border-style: groove'></div>");
        let $artifact_form_label =$("<br><label for='input_"+formNum+"'>Repository:</label>");
        let $artifact_form_input =$("<input id='input_"+formNum+"' class='artifact_input_form'>" );
        let $artifact_form_removal=$("<a id='remove_"+formNum+"' class='img'><img src='/static/images/delete.png' class='artifact_input_form_delete_img' title='Remove Package Input' /></a><br>");
        let $artifact_form_warning=$("<br><p id='warning_" + formNum + "' class='artifact_input_form_warning'></p><br>");
        let $artifact_form_gerrit_container=$("<div id='gerrit_div_" + formNum + "_" + linkNum + "' class='gerrit_container'></div>");
        let $artifact_form_gerrit_label=$("<label for='gerrit_label_" + formNum + "'>Gerrit Link:</label>");
        let $artifact_form_gerrit_input=$("<input id='gerrit_input_" + formNum + "_" + linkNum + "' class='artifact_input_form_gerrit_input'>");
        let $artifact_form_gerrit_warning=$("<p id='gerrit_warning_" + formNum + "_" + linkNum +"' class='artifact_input_form_warning'></p><br>");

        $(document).on("change", "#category_"+formNum, function() {
            autoCompleteHandler($artifact_form_container,formNum);
        });
        $(document).on("click", "#remove_" + formNum, function() {
            removeArtifactAction(formNum);
        });
        $(document).on("blur", "#gerrit_input_" + formNum + "_" + linkNum, function() {
            validateGerritLinkbyContainer();
        });
        $(document).on("blur", '#input_' + formNum, function() {
            validateArtifactbyContainer();
        });

        $('#add_artifact').before($artifact_form_container);
        $artifact_form_warning.hide();
        $artifact_form_gerrit_warning.hide();
        $artifact_form_gerrit_container.prepend($artifact_form_gerrit_label, [$artifact_form_gerrit_input, $artifact_form_gerrit_warning]);
        $artifact_form_container.prepend($category_select,$artifact_form_label, [$artifact_form_input, $artifact_form_removal, $artifact_form_warning, $artifact_form_gerrit_container]);
        globalArtifactIndex+=1;
        globalArtifactSum+=1;
        artifactFormDict['form_'+formNum].gerrit_index+=1;
        artifactFormDict['form_'+formNum].gerrit_sum+=1;
    }

    function add_jira_selector() {
        let formNumJira = jiraIndex;
        jiraForms[formNumJira] = formNumJira;
        let $jira_container = $("<div id='jirasdiv_" + formNumJira  + "' class='jiradiv'></div>")
        let $jira_label = $("<label for='jiras_" + formNumJira + "' id='jiraslabel_" + formNumJira + "'>JIRA Ticket:</label>")
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
        jiraIndex += 1;
        jiraSum += 1;
    }

    function add_enmdg_selector() {
        let formNum = enmdgIndex
        enmdgForms[formNum] = formNum;
        let $enmdg_container = $("<div id='enmdgdiv_" + formNum  + "' class='enmdgdiv'></div>")
        let $enmdg_label = $("<label for='enmdg_" + formNum + "' id='enmdglabel_" + formNum + "'>Impacted ENM Delivery Group:</label>")
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
        enmdgIndex += 1;
        enmdgSum += 1;
    }

    function checkMissingDepValue() {
        let missingDepBox = document.getElementById('set_missingDep');
        if (missingDepBox.checked) {
            missing_dep_comment.show();
        } else {
            missing_dep_comment.hide();
            $('#missing_dep_comment').val("");
        }
    }

    function autoCompleteHandler(artifactForm,formNum){
        if (artifactForm.find('#category_'+formNum).val()==="integration_chart"){
            artifact_autocomplete_items=integration_chart_items;
        }else if (artifactForm.find('#category_'+formNum).val()==="integration_value"){
            artifact_autocomplete_items=integration_value_items;
        }else if (artifactForm.find('#category_'+formNum).val()==="service_group"){
            artifact_autocomplete_items=service_group_items;
        }else{
            artifact_autocomplete_items=[];
        }
        artifactForm.find("#input_"+formNum).autocomplete({
            source: artifact_autocomplete_items
        });
    }

    function wrapArtifactData(){
        let integrationChartData = [];
        let serviceGroupData = [];
        let integrationValueData= [];
        let pipelineData= [];
        for (let i = 1; i<= Object.keys(artifactFormDict).length; i++){
            let currArtifact=$(document).find('#div_'+i);
            let gerritLinkList = $('#div_'+i).find(".artifact_input_form_gerrit_input");
            let gerritResultList =[];
            let artifactName = $('#div_'+i).find("#input_"+i).val();
            let gerritLinkSum = gerritLinkList.length;
            let result;
            for (let j = 0; j < gerritLinkSum ; j++) {
                if (gerritLinkList[j].value.length != 0) {
                    gerritResultList.push(gerritLinkList[j].value);
                }
            }
            if (artifactName.trim().length === 0) {
                continue;
            }
            if (currArtifact.find('#category_'+i).val() === "service_group"){
                result = {'imageName': artifactName, 'gerritList': gerritResultList};
                serviceGroupData.push(result);
            }
            if (currArtifact.find('#category_'+i).val() === "integration_chart"){
                result = {'integrationChartName': artifactName, 'gerritList': gerritResultList};
                integrationChartData.push(result);
            }
            if (currArtifact.find('#category_'+i).val()==="integration_value"){
                result = {'integrationValueName': artifactName, 'gerritList': gerritResultList};
                integrationValueData.push(result);
            }
            if (currArtifact.find('#category_'+i).val()==="pipeline"){
                result = {'pipelineName': artifactName, 'gerritList': gerritResultList};
                pipelineData.push(result);
            }
        }
        return {integrationChart:integrationChartData,serviceGroup:serviceGroupData,integrationValue:integrationValueData,pipeline:pipelineData};
    }

    function wrapJiraData() {
        let jiraData = [];
        Object.keys(jiraForms).forEach(key => {
            let jiraElement = $("#jiras_input_" + key);
            if (jiraElement.val().trim().length > 0) {
                jiraData.push(jiraElement.val());
            }
        });
        return jiraData;
    }

    function wrapENMDeliveryGroupData() {
        let enmDgData = []
        Object.keys(enmdgForms).forEach(key => {
            let enmDgElement = $("#enmdg_" + key);
            if (enmDgElement.val().trim().length > 0) {
                enmDgData.push(enmDgElement.val());
            }
        });
        return enmDgData;
    }

    function wrapMissingDepReasonData(missingDepReason) {
        let missingDepData = "";
        if (missingDepReason.trim().length > 0) {
            missingDepData = missingDepReason
        }
        return missingDepData;
    }

    async function add_to_queue() {
        if (validateArtifactbyContainer() === true){
            alert("Please resolve all warnings!");
        } else {
            let productName = "Cloud Native ENM";
            let team_query = $('.delivery_form_creator');
            let team_email_query = $('.delivery_form_team_email');
            let delivery_queue_dict = {};
            let pipelineList = [];
            let enmDgList = [];
            let missingDep = $('#set_missingDep').prop('checked');
            let missingDepReason =  $('#missing_dep_comment').val();
            let userId = $('#hidden_user_div').html();
            let data = wrapArtifactData();
            delivery_queue_dict['serviceGroupList'] = [];
            delivery_queue_dict['integrationChartList'] = [];
            delivery_queue_dict['integrationValueList'] = [];
            delivery_queue_dict['pipelineList'] = [];
            delivery_queue_dict["jiraTickets"] = [];
            delivery_queue_dict["teamName"] = "";
            delivery_queue_dict["teamEmail"] = "";
            delivery_queue_dict["dropName"] = "";
            delivery_queue_dict["missingDepReason"] = "";
            delivery_queue_dict["missingDep"] = false;
            if (check_jira_inputs()){
                let proceed = confirm("Do you want create a new delivery group with these data?");
                if (proceed) {
                    $('body').addClass('loading');
                    delivery_queue_dict['integrationChartList'] = data['integrationChart'];
                    delivery_queue_dict['serviceGroupList'] = data['serviceGroup'];
                    delivery_queue_dict['integrationValueList'] = data['integrationValue'];
                    delivery_queue_dict['pipelineList'] = data['pipeline'];
                    delivery_queue_dict["jiraTickets"] = wrapJiraData();
                    enmDgList = wrapENMDeliveryGroupData();
                    delivery_queue_dict["missingDepReason"] = wrapMissingDepReasonData(missingDepReason);
                    delivery_queue_dict["pipelines"] = pipelineList;
                    delivery_queue_dict["teamName"] = team_query.val().trim();
                    delivery_queue_dict["teamEmail"] = team_email_query.val().trim();
                    delivery_queue_dict["dropName"] = dropName;
                    delivery_queue_dict["missingDep"] = missingDep;
                    let params = {
                        'cnImageList':delivery_queue_dict["serviceGroupList"],
                        'integrationChartList': delivery_queue_dict["integrationChartList"],
                        'integrationValueList': delivery_queue_dict["integrationValueList"],
                        'pipelineList': delivery_queue_dict["pipelineList"],
                        'jiraTickets':delivery_queue_dict["jiraTickets"],
                        'dropName': delivery_queue_dict["dropName"],
                        'teamName':delivery_queue_dict["teamName"],
                        'teamEmail':delivery_queue_dict["teamEmail"],
                        'missingDep':delivery_queue_dict["missingDep"],
                        'missingDepReason': delivery_queue_dict["missingDepReason"],
                        'impacted_delivery_group': enmDgList,
                        'userName': userId,
                        'productName': productName
                    }
                    $.ajax({
                        type: "POST",
                        url: "/api/cloudNative/deliveryQueue/addCNDeliveryGroup/",
                        dataType: "json",
                        headers: { "X-CSRFToken": getCookie("csrftoken") },
                        data: JSON.stringify(params),
                        success: function(result) {
                            alert("new delivery group successfully created. New DG Number: " + result);
                            window.location.href = "/cloudNative/" + productName + "/deliveryQueue/" + delivery_queue_dict["dropName"] + "/" + result + "/?section=queued"
                            $('body').removeClass('loading');
                        },
                        error: function(xhr, textStatus, errorThrown) {
                            alert("Issue creating CN Delivery Group: " + xhr.responseText);
                            $('body').removeClass('loading');
                        }
                    });
                }
            }else{
                window.alert("Please fill in JIRA ticket(s) associated with this Delivery Group.")
        }
        }
    }
});

function getCookie(c_name)
{
    if (document.cookie.length > 0)
    {
        c_start = document.cookie.indexOf(c_name + "=");
        if (c_start != -1)
        {
            c_start = c_start + c_name.length + 1;
            c_end = document.cookie.indexOf(";", c_start);
            if (c_end == -1) c_end = document.cookie.length;
            return unescape(document.cookie.substring(c_start,c_end));
        }
    }
    return "";
 }

