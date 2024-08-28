$(document).ready(function() {
    let jiraSum = 0;
    let jiraIndex = 1;
    let deliveryGroupNumber = $('#hidden_deliveryGroupNumber_div').html();
    let jira_beforeEdit = [];
    let jira_afterEdit = {};
    initPage(deliveryGroupNumber);

    async function initPage(deliveryGroupNumber) {
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
        $('#drop').val(jira_beforeEdit.drop);
        jira_beforeEdit.jiraList.forEach(function(item, index) {
            add_jira_selector(item);
        });
        $(document).on("click", "#add_jira", function() {
            add_jira_selector("");
        });
        $(document).on("click", "#edit_jira", function() {
            edit_queue();
        });
    }

    function add_jira_selector(jiraValue) {
        let formNumJira = jiraIndex;
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
        jiraIndex = jiraIndex + 1;
        jiraSum = jiraSum + 1;
        if (jiraValue != "") {
            $('#jiras_input_' + formNumJira).val(jiraValue);
        }
    }

    function validate_jira(jiraNum, warning_jira_section, formNumJira) {
        $('#edit_jira').attr('disabled', true);
        $('#add_jira').attr('disabled', true);
        if ($('#jirasdiv_' + formNumJira + ' .delivery_form_jira').length == 0) {
            $('#edit_jira').attr('disabled', false);
            $('#add_jira').attr('disabled', false);
            return;
        }
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
                        $('#add_jira').attr('disabled', true);
                        $('#edit_jira').attr('disabled', true);
                    } else {
                        $("#jirasdiv_" + formNumJira).removeClass('jiraWarning');
                        warning_jira_section.hide();
                        $('#add_jira').attr('disabled', false);
                        $('#edit_jira').attr('disabled', false);
                    }
                });
            },
            error: function(xhr, textStatus, errorThrown) {
                let proceed_jira = "";
                if (errorThrown === "NOT FOUND") {
                    alert("JIRA Ticket: " + jiraNum + " is invalid. Please enter in a valid JIRA Ticket. (Example: TORF-417819)");
                } else {
                    message = "Issue retrieving data from JIRA, would you like to proceed anyway?"
                    proceed_jira = confirm(message)
                }
                if (proceed_jira){
                    $('#add_jira').attr('disabled', false);
                    $('#edit_jira').attr('disabled', false);
                } else {
                    $('#jiras_input_' + formNumJira).val("");
                    $('#add_jira').attr('disabled', false);
                    $('#edit_jira').attr('disabled', false);
                }
            }
        });
    }

    function removeJiraAction(jiraNum) {
        let proceed = confirm("Do you really want to remove this jira ticket?");
        if (proceed) {
            $("#jirasdiv_" + jiraNum).remove();
            validate_jira(jiraNum, $('#jira_warning_' + jiraNum, jiraIndex));
        }
        jiraSum = jiraSum - 1;
    }

    function edit_queue() {
        jira_afterEdit["jiraList"] = []
        let proceed = confirm("Do you want to edit delivery group " + deliveryGroupNumber + " for these jira data?");
        if (proceed) {
            for (let i = 1; i <= jiraSum; i++) {
                let jiraElement = $("#jiras_input_" + i);
                if (jiraElement.length == 0) {
                    continue;
                }
                jira_afterEdit["jiraList"].push(jiraElement.val().trim());
            }
            let params = {
                'data_beforeEdit': jira_beforeEdit,
                'data_afterEdit': jira_afterEdit
            }
            $.ajax({
                type: "PUT",
                url: "api/cloudNative/deliveryQueue/editJira/" + deliveryGroupNumber + "/",
                dataType: "json",
                headers: { "X-CSRFToken": getCookie("csrftoken") },
                data: JSON.stringify(params),
                success: function(result) {
                    let dropName = (jira_beforeEdit["drop"].split("Cloud Native ENM"))[1].trim();
                    alert("JIRA ticket successfully updated.");
                    window.location.href = "/cloudNative/Cloud Native ENM/deliveryQueue/" + dropName + "/" + deliveryGroupNumber + "/?section=queued";
                },
                error: function(xhr, textStatus, errorThrown) {
                    alert("Issue updating pipeline info for CN Delivery Group: " + xhr.responseText);
                }
            });
        }
    }
    function getCookie(c_name) {
        if (document.cookie.length > 0) {
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
});

