$(document).ready(function () {
    let productName = "Cloud Native ENM";
    let dropName = $('#hidden_drop_div').html();
    let userPerm = $('#hidden_userPerms_div').html();
    let adminPerm = $('#hidden_adminPerms_div').html();
    let dropStatus = $('#hidden_cnDropStatus_div').html();
    let groupId = $('#hidden_group_div').html();
    var deliveryGroupSubscriptions;
    var subscriptionStatus;
    var displaySubscriptionStatus;
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
    deliveryGroupSubscriptions = [];

    function loadSubscriptions() {
        $.ajax({
            type: 'GET',
            url: "/api/cloudNative/deliveryQueue/subscriptions/",
            dataType: 'json',
            cache: false,
            success: function (json, textStatus) {
                for (data in json){
                deliveryGroupSubscriptions.push((json[data]['fields'].cnDeliveryGroup));}
            },
            error: function (xhr, textStatus, errorThrown) {
                deliveryGroupSubscriptions.push('No User')
            }
        });
    }
    loadSubscriptions();

    function buildQueueResults() {
        $('body').addClass('loading');
        $.ajax({
            type: 'GET',
            url: "/api/cloudNative/" + productName + "/getCNDeliveryQueue/" + dropName + "/",
            dataType: 'json',
            cache: false,
            success: function (json, textStatus) {
                let deliveryGroups = json.cnDeliveryGroups;
                let html_content = {
                    'queued': '',
                    'delivered': '',
                    'obsoleted': '',
                    'deleted': ''
                };
                let groupStatus = "queued"
                // generate expansion section
                for (let key in html_content) {
                    html_content[key] += '<div style="float:right;"><a href="javascript:void(0)" class="expand' + key + '">Expand All</a> | <a href="javascript:void(0)" class="collapse' + key + '">Collapse All</a></div><br>';
                    html_content[key] += '<div class="accordion groupaccordion" id="accordion' + key + '">';
                };
                // get dg data
                for (let i = 0; i < deliveryGroups.length; i++) {
                    let deliveryGroup = deliveryGroups[i];
                    let serviceGroupList = deliveryGroup.serviceGroups;
                    let integrationChartList = deliveryGroup.integrationCharts;
                    let integrationValueList = deliveryGroup.integrationValues;
                    let commentList = deliveryGroup.comments;
                    let jiraIssueList = deliveryGroup.jiraIssue;
                    let pipelineList = deliveryGroup.pipelines;
                    let impactedDGList = deliveryGroup.impactedENMDeliveryGroups;
                    // update groupStatus
                    if(deliveryGroup.queued) {
                        groupStatus = "queued";
                    }
                    if (deliveryGroup.delivered) {
                        groupStatus = "delivered";
                    }
                    if (deliveryGroup.obsoleted) {
                        groupStatus = "obsoleted";
                    }
                    if (deliveryGroup.deleted) {
                        groupStatus = "deleted";
                    }
                    if (deliveryGroupSubscriptions.indexOf('No User') > -1) {
                        displaySubscriptionStatus = false;
                        subscriptionStatus = '';
                    } else if (deliveryGroupSubscriptions.indexOf(deliveryGroup.id) > -1) {
                        displaySubscriptionStatus = true;
                        subscriptionStatus = '<a class="img" href="javascript:void(0);" onClick="checkSubscription(\'Are you sure you want to stop watching Group ' + deliveryGroup.id + '?\', ' + deliveryGroup.id + ')"><img src="/static/images/watched.png" title="Stop Watching Delivery Group: ' + deliveryGroup.id + '" /></a>';
                    }else {
                        displaySubscriptionStatus = false;
                        subscriptionStatus = '<a class="img" href="javascript:void(0);" onClick="checkSubscription(\'Are you sure you want to watch Group ' + deliveryGroup.id + '?\', ' + deliveryGroup.id + ')"><img src="/static/images/unwatched.png" title="Start Watching Delivery Group: ' + deliveryGroup.id + '" /></a>';
                    }
                    html_content[groupStatus] += '<h2 id="group' + deliveryGroup.id + '" class="productware_group">'
                    html_content[groupStatus] += 'Group:' + deliveryGroup.id;

                    if (displaySubscriptionStatus) {
                        html_content[groupStatus] += '<img src="/static/images/watched.png" style="float: right" title="Watcher for Group: ' + deliveryGroup.id + '" />';
                    }
                    if (deliveryGroup.impactedENMDeliveryGroups.length > 0) {
                        html_content[groupStatus] += ' <img src="/static/images/impactedDgFlag.svg" alt="EnmDependency" title="ENM Dependency" class="delivery_group_flag_img" />';
                    }
                    // missingdep
                    if (deliveryGroup.missingDependencies) {
                        html_content[groupStatus] += ' <img src="/static/images/missingDepFlag.svg" alt="MissingDependencies" title="Missing Dependencies" class="delivery_group_flag_img" />';
                    }
                    //  bug or TR
                    if (deliveryGroup.bugOrTR){
                        html_content[groupStatus] += ' <img src="/static/images/bug.png" alt="Bug or Tr" title="Group Contains Bug Or TR Jira" class="delivery_group_flag_img" />';
                    }
                    if (jiraIssueList.length == 0) {
                        html_content[groupStatus] += ' - No JIRA Ticket(s) associated';
                    }
                    html_content[groupStatus] += '</h2>';
                    if (deliveryGroup.cnProductSetVersion__product_set_version) {
                        includedInPsHtml = '<a href="/cloudnative/getCloudNativeProductSetContent/' + dropName + '/'+ deliveryGroup.cnProductSetVersion__product_set_version + '"/">' + deliveryGroup.cnProductSetVersion__product_set_version + '</a>';
                        if (groupStatus == 'delivered') {
                            includedInPsString = ' | Included in: ' + includedInPsHtml;
                        }
                        else if (groupStatus == 'obsoleted') {
                            includedInPsString = ' | Removed from: ' + includedInPsHtml;
                        }
                    } else {
                        includedInPsString = "";
                    }
                    // team info
                    if (deliveryGroup.component__element) {
                        createdByTeamString = ' | Created by Team: ' + deliveryGroup.component__element + ' ' + deliveryGroup.component__parent__label__name +': ' + deliveryGroup.component__parent__element;
                    } else {
                        createdByTeamString = "";
                    }
                    html_content[groupStatus] += '<div>' +
                        '<table class="general-table" width="100%">' +
                        '<tr>' +
                        '<th class="delivery_group_banner" colspan=9>' +
                        '<div class="table-title">Delivery Group: ' + deliveryGroup.id + includedInPsString + createdByTeamString + " " + ' </div>';
                    //. rendering edition and deletion button
                    if (groupStatus == "queued") {
                        html_content[groupStatus] += '<div class="table-actions">' +
                            subscriptionStatus +
                            '<a class="img" href="/cloudNative/deliveryQueue/editDeliveryGroup/' + deliveryGroup.id + '/"><img src="/static/images/edit.png" title="Edit Delivery Group: ' + deliveryGroup.id + '" /></a>' +
                            '</div>';
                    }
                    //rendering impacted non-cn delivery group
                    html_content[groupStatus] += renderImpactedENMDeliveryGroupSection(deliveryGroup, impactedDGList, groupStatus, productName, dropName);
                    // rendering header of sg table
                    if (groupStatus == 'obsoleted') {
                        html_content[groupStatus] += '</th>' +
                            '</tr>' +
                            '<tr>' +
                            '<th>Repository</th>' +
                            '<th>Gerrit Link</th>' +
                            '<th>Category</th>' +
                            '<th>Change id</th>';
                    }
                    else{
                        html_content[groupStatus] += '</th>' +
                            '</tr>' +
                            '<tr>' +
                            '<th>Repository</th>' +
                            '<th>Gerrit Link</th>' +
                            '<th>Category</th>';
                        if (groupStatus == 'queued') {
                            html_content[groupStatus] += '<th>Action</th>';
                        }
                    }
                    html_content[groupStatus] += '</tr>';
                    // putting service group info into the table
                    for(let j = 0; j < serviceGroupList.length; j++) {
                        let serviceGroupName = (Object.getOwnPropertyNames(serviceGroupList[j]))[0];
                        html_content[groupStatus] += '<tr class="productware_artifact_in_group">';
                        html_content[groupStatus] += '<td>' + serviceGroupName + '</td>';
                        html_content[groupStatus] += '<td>';
                        let gerritList = (serviceGroupList[j])[serviceGroupName];
                        let gerritDataList = [];
                        for(let k = 0; k < Object.keys(gerritList).length; k++) {
                            let tmpGerritLink = String(gerritList[k].cnGerrit__gerrit_link);
                            html_content[groupStatus] += '<p><a href="' + tmpGerritLink + '">' + tmpGerritLink + '</a></p>';
                            gerritDataList.push(tmpGerritLink);
                        }
                        html_content[groupStatus] += '</td><td>Service Group</td>';
                        if (groupStatus == 'queued') {
                            html_content[groupStatus] += '<td><p align="center"><a class="img" href="javascript:void(null);" onClick="removeServiceGroupAction(\''+ deliveryGroup.id + '\',\'' + serviceGroupName + '\',\'' + gerritDataList + '\',\'' + productName + '\',\'' + dropName + '\',\'' + groupStatus + '\')"><img src="/static/images/delete.png" width="25" height="25" title="Delete ' + serviceGroupName + ' from group: ' + deliveryGroup.id + '" /></a></p></td>';
                        }
                        else if (groupStatus == 'obsoleted') {
                            html_content[groupStatus] += '<td>';
                            let changeIdList = (serviceGroupList[j])[serviceGroupName];
                            for(let k = 0; k < Object.keys(changeIdList).length; k++) {
                                let tmpRevertChangeId = String(changeIdList[k].revert_change_id);
                                html_content[groupStatus] += '<p><a href="https://gerrit-gamma.gic.ericsson.se/#/q/' + tmpRevertChangeId + '" target="_blank">' + "Reverted Gerrit Link" + '</a></p>';
                                }
                                html_content[groupStatus] += '</td>';
                            }
                        html_content[groupStatus] += '</tr>';
                    }
                    // rendering integration charts
                    html_content[groupStatus] += renderIntegrationChartSection(deliveryGroup, integrationChartList, groupStatus, productName, dropName);
                    // rendering integration values
                    html_content[groupStatus] += renderIntegrationValueSection(deliveryGroup, integrationValueList, groupStatus, productName, dropName);
                    // rendering pipeline table
                    html_content[groupStatus] += renderPipelineSection(deliveryGroup, pipelineList, groupStatus, productName, dropName);
                    html_content[groupStatus] += '</table>';
                    // rendering jira accordin
                    html_content[groupStatus] += renderJiraSection(deliveryGroup, jiraIssueList, groupStatus, productName, dropName)
                    // rendering dg comment seciton
                    // add dg comment section to be done.
                    html_content[groupStatus] += renderCommentSection(deliveryGroup, commentList, groupStatus, productName, dropName)
                    // putting all the contents to the right section: 'queued', 'delivered', 'obsoleted', 'deleted'
                    if (groupStatus == 'queued') {
                        html_content[groupStatus] += renderQueuedSection(deliveryGroup, groupStatus, productName, dropName, userPerm, adminPerm, dropStatus);
                    }
                    if (groupStatus == 'delivered') {
                        html_content[groupStatus] += renderDeliveredSection(deliveryGroup, groupStatus, productName, dropName);
                    }
                    if (groupStatus == 'obsoleted' || groupStatus == 'deleted') {
                        html_content[groupStatus] += renderObsoletedOrDeletedSection(deliveryGroup, groupStatus, productName, dropName);
                    }
                    html_content[groupStatus] += '</div>';
                }
                for (key in html_content) {
                    html_content[key] += '</div>';
                    $('#' + key).html(html_content[key]);
                }
                $(".accordion").accordion({
                    active: false,
                    collapsible: true,
                    heightStyle: "content",
                    animate: {
                        duration: 50
                   }
                });

                $(".groupaccordion").accordion({
                    active: 0
                });
                // nativating group
                if (groupId != 'None')
                {
                    var groupAlreadySelected = false;
                    $(".groupaccordion > h2:first-child").each(function(index) {
                        if ($(this).attr('id') === 'group' + groupId)
                        {
                            groupAlreadySelected = true;
                            return;
                        }
                    });
                    if (!groupAlreadySelected)
                    {
                        $('#group' + groupId).click();
                        theOffset = $('#group' + groupId).offset();
                        $(window).scrollTop(theOffset.top -900);
                    }
                }
                $('.expandqueued').click(function () {
                    $('#accordionqueued > .ui-widget-content').show();
                    $('#accordionjira > .ui-widget-content').show();
                    $('#accordioncomment > .ui-widget-content').show();
                });
                $('.collapsequeued').click(function () {
                    $('#accordionqueued > .ui-widget-content').hide();
                    $('#accordionjira > .ui-widget-content').hide();
                    $('#accordioncomment > .ui-widget-content').hide();
                });

                $('.expanddelivered').click(function () {
                    $('#accordiondelivered > .ui-widget-content').show();
                    $('#accordionjira > .ui-widget-content').show();
                    $('#accordioncomment > .ui-widget-content').show();
                });
                $('.collapsedelivered').click(function () {
                    $('#accordiondelivered > .ui-widget-content').hide();
                    $('#accordionjira > .ui-widget-content').hide();
                    $('#accordioncomment > .ui-widget-content').hide();
                });

                $('.expandobsoleted').click(function () {
                    $('#accordionobsoleted > .ui-widget-content').show();
                    $('#accordionjira > .ui-widget-content').show();
                    $('#accordioncomment > .ui-widget-content').show();
                });
                $('.collapseobsoleted').click(function () {
                    $('#accordionobsoleted > .ui-widget-content').hide();
                    $('#accordionjira > .ui-widget-content').hide();
                    $('#accordioncomment > .ui-widget-content').hide();
                });

                $('.expanddeleted').click(function () {
                    $('#accordiondeleted > .ui-widget-content').show();
                    $('#accordionjira > .ui-widget-content').show();
                    $('#accordioncomment > .ui-widget-content').show();
                });
                $('.collapsedeleted').click(function () {
                    $('#accordiondeleted > .ui-widget-content').hide();
                    $('#accordionjira > .ui-widget-content').hide();
                    $('#accordioncomment > .ui-widget-content').hide();
                });

                var tabSection = document.getElementById("tabSection").getAttribute("data-tabSection");
                if (typeof tabSection === "undefined" ) {
                    var tabSection = 'queued';
                }
                openItem(tabSection);
                $('body').removeClass('loading');
            }
        });
    }
    buildQueueResults();
});

function renderQueuedSection(deliveryGroup, groupStatus, productName, dropName, userPerm, adminPerm, dropStatus) {
    let html_content = "";
    html_content += '<div style="position: relative;">';
    html_content += '<span style="float: left; clear: right;">';
    html_content += renderMissingDepSection(deliveryGroup, productName, dropName, groupStatus);
    html_content += '</span><br>';
    html_content += '<span style="right: 0px; position: absolute; top: 0px;"';
    // rendering deliver button
    if (adminPerm == 'True') {
        if (deliveryGroup.missingDependencies && (dropStatus == 'open' || dropStatus == 'reopen')) {
            html_content += '><a class="btn btn-default" id="link_' + deliveryGroup.id + '" href="javascript:void(0);"  onClick="checkUserActionDeletion(\''+ deliveryGroup.id + '\',\'' + productName + '\',\'' + dropName + '\')">Delete This Group</a>';
            html_content += '<a class="btn btn-default button-disabled" title="Missing Dependencies Cannot Deliver" disabled>Deliver This Group</a>';
        } else if (dropStatus == 'open' || dropStatus == 'reopen') {
            html_content += '><a class="btn btn-default" id="link_' + deliveryGroup.id + '" href="javascript:void(0);"  onClick="checkUserActionDeletion(\''+ deliveryGroup.id + '\',\'' + productName + '\',\'' + dropName + '\')">Delete This Group</a>';
            html_content += '<a class="btn btn-default" id="link_' + deliveryGroup.id + '" href="' + "/cloudNative/deliveryQueue/deliveryConfirmation/" + dropName + "/" + deliveryGroup.id + "/" + '">Deliver This Group</a>';
        } else {
            let permsSummary = "Drop is frozen. You can't either deliver or delete a delivery group.";
            html_content += '><a class="btn btn-default button-disabled" id="link_' + deliveryGroup.id + '"  title="' + permsSummary + '" disabled>Delete This Group</a>';
            html_content += '<a class="btn btn-default button-disabled" id="link_' + deliveryGroup.id + '"  title="' + permsSummary + '" disabled>Deliver This Group</a>';
        }
    } else {
        if (dropStatus == 'frozen' || dropStatus == 'error' || dropStatus == 'not exist') {
            let permsSummary = "Drop is frozen. You can't either deliver or delete a delivery group.";
            html_content += '><a class="btn btn-default button-disabled" id="link_' + deliveryGroup.id + '"  title="' + permsSummary + '" disabled>Delete This Group</a>';
            html_content += '<a class="btn btn-default button-disabled" id="link_' + deliveryGroup.id + '"  title="' + permsSummary + '" disabled>Deliver This Group</a>';
        } else {
            let permsSummary = "No permission to deliver or delete this group."
            html_content += '><a class="btn btn-default button-disabled" id="link_' + deliveryGroup.id + '"  title="' + permsSummary + '" disabled>Delete This Group</a>';
            html_content += '<a class="btn btn-default button-disabled" id="link_' + deliveryGroup.id + '"  title="' + permsSummary + '" disabled>Deliver This Group</a>';
        }
    }
    html_content += '</span></div>';
    return html_content;
}

function renderDeliveredSection(deliveryGroup, groupStatus, productName, dropName) {
    let userPerm = $('#hidden_userPerms_div').html();
    let adminPerm = $('#hidden_adminPerms_div').html();
    let dropStatus = $('#hidden_cnDropStatus_div').html();
    let html_content = "";
    html_content += '<div align="right">';
    // render update ps btn
    if (adminPerm == 'True' && (dropStatus == 'open' || dropStatus == 'reopen')) {
        // link to be changed
        html_content += '<a class="btn btn-default" id="update_ps_link_' + deliveryGroup.id + '" href="/cloudNative/deliveryQueue/updateProductSetVersion/'+ dropName + '/' + deliveryGroup.id + '/">Update Product Set Version</a>';
    } else {
        html_content += '<span class="btn btn-default button-disabled" title="';
        if (dropStatus == 'frozen' || dropStatus == 'error' || dropStatus == 'not exist') {
            let permsSummary = "Drop is frozen";
            html_content += permsSummary;
        } else {
            html_content += 'No Permissions to update';
        }
        html_content += '" disabled>Update Product Set Version</span>';
    }
    // render obsolete btn
    if (adminPerm == 'True' && (dropStatus == 'open' || dropStatus == 'reopen')) {
        // link to be changed
        html_content += '<a class="btn btn-default" id="link_' + deliveryGroup.id + '" href="javascript:void(0);"  onClick="checkUserActionObsoletion(\''+ deliveryGroup.id + '\',\'' + productName + '\',\'' + dropName + '\')">Obsolete This Group</a>';
    } else {
        html_content += '<span class="btn btn-default button-disabled" title="';
        if (dropStatus == 'frozen' || dropStatus == 'error' || dropStatus == 'not exist') {
            let permsSummary = "Drop is frozen";
            html_content += permsSummary;
        } else {
            html_content += 'No Permissions to Obsolete';
        }
        html_content += '" disabled>Obsolete This Group</span>';
    }
    html_content += '</div>';
    return html_content
}

function renderObsoletedOrDeletedSection(deliveryGroup, groupStatus, productName, dropName) {
    let userPerm = $('#hidden_userPerms_div').html();
    let adminPerm = $('#hidden_adminPerms_div').html();
    let dropStatus = $('#hidden_cnDropStatus_div').html();
    let html_content = "";
    if (adminPerm == 'True' && (dropStatus == 'open' || dropStatus == 'reopen')) {
        // link to be changed
        html_content += '<div align="right"><a href="javascript:void(0);" class="btn btn-default"  onClick="checkUserActionRestoration(\''+ deliveryGroup.id + '\',\'' + productName + '\',\'' + dropName + '\')">Restore Delivery Group</a></div>';
    } else {
        html_content += '<div align="right"><span class="btn btn-default button-disabled" title="';
        if (dropStatus == 'frozen' || dropStatus == 'error' || dropStatus == 'not exist') {
            let permsSummary = "Drop is frozen";
            html_content += permsSummary;
        } else {
            html_content += 'No Permissions to Restore';
        }
        html_content += '" disabled>Restore Delivery Group</span></div>';
    }
    return html_content
}

function renderCommentSection(deliveryGroup, commentList, groupStatus, productName, dropName) {
    let htmlContent = "";
    if (commentList.length > 0) {
        htmlContent += '<div class="accordion" id="accordioncomment">' +
        '<h2 id="' + groupStatus + 'Comments">Comments</h2>' +
        '<div>' +
        '<table class="general-table" width="100%">' +
        '<tr>' +
        '<th class="title" colspan=2>' +
        '<div class="table-title">Delivery Group: ' + deliveryGroup.id + '</div>' +
        '<div class="table-actions">' +
        '<a class="img" href="cloudNative/deliveryQueue/addComment/' + productName + '/' + dropName + '/' + deliveryGroup.id + '/' + groupStatus + '/"><img src="/static/images/create.png" title="Add Comment to ' + deliveryGroup.id + '" /></a>' +
        '</div>' +
        '</th>' +
        '</tr>';
        commentList.forEach(function (comment, index) {
            if (comment.date) {
                commentDateString = comment.date.replace('T', ' ');
            } else {
                commentDateString = '-';
            }
            htmlContent += '<tr>' +
            '<td>' + comment.comment + '</td>' +
            '<td>' + commentDateString + '</td>' +
            '</tr>';
        });
    } else {
        htmlContent += '<div class="accordion" id="accordioncomment">' +
        '<h2 id="' + groupStatus + 'Comments">Comments</h2>' +
        '<div>' +
        '<table class="general-table" width="100%">' +
        '<tr>' +
        '<th class="title" colspan=2>' +
        '<div class="table-title">Delivery Group: ' + deliveryGroup.id + '</div>' +
        '<div class="table-actions">' +
        '<a class="img" href="cloudNative/deliveryQueue/addComment/' + productName + '/' + dropName + '/' + deliveryGroup.id + '/' + groupStatus + '/"><img src="/static/images/create.png" title="Add Comment to ' + deliveryGroup.id + '" /></a>' +
        '</div>' +
        '</th>' +
        '</tr>';
    }
    htmlContent += '</table>' +
        '</div>' +
        '</div>';
    return htmlContent;
}

function renderJiraSection(deliveryGroup, jiraIssueList, groupStatus, productName, dropName) {
    let htmlContent = "";
    if(jiraIssueList.length > 0) {
        // api for adding jira to be added
        htmlContent += '<div class="accordion" id="accordionjira">' +
            '<h2 id="' + groupStatus + '">Jiras</h2>' +
            '<div>' +
            '<table class="general-table" width="100%">' +
            '<tr>' +
            '<th class="title" colspan=5>' +
            '<div class="table-title">Delivery Group: ' + deliveryGroup.id + '</div>' +
            '<div class="table-actions">' +
            '<a class="img" href="/cloudNative/deliveryQueue/editJira/' + deliveryGroup.id + '/"><img src="/static/images/edit.png" title="Edit Jira tickets for Delivery Group: ' + deliveryGroup.id + '" /></a>' +
            '</div>' +
            '</th>' +
            '</tr>' +
            '<tr>' +
            '<th>Issue</th>' +
            '<th>Type</th>' +
            '<th></th>' +
            '</tr>';
        jiraIssueList.forEach(function (jira, index) {
            // jira link to be added
            htmlContent += '<tr>' +
                '<td><a href="' + jira.jiraLink + '" target="_blank">' + jira.cnJiraIssue__jiraNumber + '</a></td>' +
                '<td>' + jira.cnJiraIssue__issueType + '</td>' +
                '<td><p align="center"><a class="img" href="javascript:void(0);" onClick="removeJiraAction(\''+ deliveryGroup.id + '\',\'' + jira.cnJiraIssue__jiraNumber + '\',\'' + productName + '\',\'' + dropName + '\',\'' + groupStatus + '\')"><img src="/static/images/delete.png" width="25" height="25" title="Delete ' + jira.cnJiraIssue__jiraNumber + ' from group: ' + deliveryGroup.id + '" /></a></p></td>' +
                '</tr>';
            })
    } else {
        htmlContent += '<div class="accordion" id="accordionjira">' +
            '<h2 id="' + groupStatus + '">Jiras</h2>' +
            '<div>' +
            '<table class="general-table" width="100%">' +
            '<tr>' +
            '<th class="title" colspan=5>' +
            '<div class="table-title">Delivery Group: ' + deliveryGroup.id + '</div>' +
            '<div class="table-actions">' +
            '<a class="img" href="/cloudNative/deliveryQueue/editJira/' + deliveryGroup.id + '/"><img src="/static/images/create.png" title="Create Jira tickets for Delivery Group: ' + deliveryGroup.id + '" /></a>' +
            '</div>' +
            '</th>' +
            '</tr>' +
            '<tr>' +
            '<th>Issue</th>' +
            '<th>Type</th>' +
            '<th></th>' +
            '</tr>';
    }
    htmlContent += '</table>' +
            '</div>' +
            '</div>';
    return htmlContent;
}

function renderImpactedENMDeliveryGroupSection(deliveryGroup, impactedDGList, groupStatus, productName, dropName) {
    let htmlContent = '';
    let section = 'queued';
    let colSpan = 3;
    if (impactedDGList.length > 0) {
        impactedDGList.forEach(function (enmDeliveryGroup, index) {
            let removeSection = '<a class="img" href="javascript:void(0);" onClick="removeImpactedENMDeliveryGroupAction(\''+ deliveryGroup.id + '\',\'' + enmDeliveryGroup.deliveryGroup__id + '\',\'' + productName + '\',\'' + dropName + '\',\'' + groupStatus + '\')"><img src="/static/images/delete.png" width="25" height="25" title="Delete ' + enmDeliveryGroup.deliveryGroup__id + ' from group: ' + deliveryGroup.id + '" /></a>';
            if (groupStatus != 'queued') {
                removeSection = ''
            }
            if (groupStatus == 'delivered' || groupStatus == 'deleted'){
                colSpan = 2
            }
            if (enmDeliveryGroup.deliveryGroup__delivered){
                section = 'delivered';
            }
            else if (enmDeliveryGroup.deliveryGroup__obsoleted){
                section = 'obsoleted';
            }
            else if (enmDeliveryGroup.deliveryGroup__deleted){
                section = 'deleted';
            }
            htmlContent += '<tr>' +
                '<th colspan='+colSpan+'>Impacted Integrated Delivery Group: <a href="/ENM/queue/'+dropName+'/'+enmDeliveryGroup.deliveryGroup__id+'/?section='+section+'">' + enmDeliveryGroup.deliveryGroup__id + '</th>' +
                '<td><p align="center">' + removeSection + '</p></td>' +
                '</tr>';
        });
    }
    htmlContent += '</div></div>';
    return htmlContent;
}

function renderPipelineSection(deliveryGroup, pipelineList, groupStatus, productName, dropName) {
    let htmlContent = "";
    if (pipelineList.length > 0) {
        pipelineList.forEach(function (pipeline, index) {
            let pipelineName = (Object.getOwnPropertyNames(pipeline))[0];
            let gerritList = pipeline[pipelineName];
            let gerritDataList = [];
            htmlContent += '<tr>' +
                '<td>' + pipelineName + '</td>';
            gerritList.forEach(function (gerrit, index) {
                let tmpGerritLink = gerrit.cnGerrit__gerrit_link
                htmlContent += '<td><a href="' + tmpGerritLink + '">' + tmpGerritLink + '</a></td>';
                gerritDataList.push(tmpGerritLink);
            });
            htmlContent += '<td>Pipeline</td>';
            let removeSection = '<a class="img" href="javascript:void(0);" onClick="removePipelineAction(\''+ deliveryGroup.id + '\',\'' + pipelineName + '\',\'' + gerritDataList + '\',\'' + productName + '\',\'' + dropName + '\',\'' + groupStatus + '\')"><img src="/static/images/delete.png" width="25" height="25" title="Delete ' + pipelineName + ' from group: ' + deliveryGroup.id + '" /></a>';
            if (groupStatus == 'obsoleted') {
                htmlContent += '<td>';
                let changeIdList = pipeline[pipelineName];
                changeIdList.forEach(function (changeId, index) {
                    let tmpRevertChangeId = changeId.revert_change_id;
                    htmlContent += '<p><a href="https://gerrit-gamma.gic.ericsson.se/#/q/' + tmpRevertChangeId + '" target="_blank">' + "Reverted Gerrit Link" + '</a></p>';
                    });
                    htmlContent += '</td>';
                }
            else if (groupStatus == 'queued') {
                htmlContent += '<td><p align="center">' + removeSection + '</p></td>'
            }
            htmlContent += '</tr>';
        });
    }
    htmlContent += '</div></div>';
    return htmlContent;
}

function renderIntegrationChartSection(deliveryGroup, integrationChartList, groupStatus, productName, dropName) {
    let htmlContent = "";
    if (integrationChartList.length > 0) {
        integrationChartList.forEach(function (chart, index) {
            let chartName = (Object.getOwnPropertyNames(chart))[0];
            let gerritList = chart[chartName];
            let gerritDataList = [];
            htmlContent += '<tr>' +
                '<td>' + chartName + '</td>';
            gerritList.forEach(function (gerrit, index) {
                let tmpGerritLink = gerrit.cnGerrit__gerrit_link
                htmlContent += '<td><a href="' + tmpGerritLink + '">' + tmpGerritLink + '</a></td>';
                gerritDataList.push(tmpGerritLink);
            });
            htmlContent += '<td>Integration Chart</td>';
            let removeSection = '<a class="img" href="javascript:void(0);" onClick="removeIntegrationChartAction(\''+ deliveryGroup.id + '\',\'' + chartName + '\',\'' + gerritDataList + '\',\'' + productName + '\',\'' + dropName + '\',\'' + groupStatus + '\')"><img src="/static/images/delete.png" width="25" height="25" title="Delete ' + chartName + ' from group: ' + deliveryGroup.id + '" /></a>';
            if (groupStatus == 'obsoleted') {
                htmlContent += '<td>';
                let changeIdList = chart[chartName];
                changeIdList.forEach(function (changeId, index) {
                    let tmpRevertChangeId = changeId.revert_change_id;
                    htmlContent += '<p><a href="https://gerrit-gamma.gic.ericsson.se/#/q/' + tmpRevertChangeId + '" target="_blank">' + "Reverted Gerrit Link" + '</a></p>';
                    });
                    htmlContent += '</td>';
                }
            else if (groupStatus == 'queued') {
                htmlContent += '<td><p align="center">' + removeSection + '</p></td>'
            }
            htmlContent += '</tr>';
        });
    }
    htmlContent += '</div></div>';
    return htmlContent
}

function renderIntegrationValueSection(deliveryGroup, integrationValueList, groupStatus, productName, dropName) {
    let htmlContent = "";
    if (integrationValueList.length > 0) {
        integrationValueList.forEach(function (integrationValue, index) {
            let integrationValueName = (Object.getOwnPropertyNames(integrationValue))[0];
            let gerritList = integrationValue[integrationValueName];
            let gerritDataList = [];
            htmlContent += '<tr>' +
                '<td>' + integrationValueName + '</td>' ;
            gerritList.forEach(function (gerrit, index) {
                let tmpGerritLink = gerrit.cnGerrit__gerrit_link
                htmlContent += '<td><a href="' + tmpGerritLink + '">' + tmpGerritLink + '</a></td>';
                gerritDataList.push(tmpGerritLink);
            });
            htmlContent += '<td>Integration Value</td>';
            let removeSection = '<a class="img" href="javascript:void(0);" onClick="removeIntegrationValueAction(\''+ deliveryGroup.id + '\',\'' + integrationValueName + '\',\'' + gerritDataList + '\',\'' + productName + '\',\'' + dropName + '\',\'' + groupStatus + '\')"><img src="/static/images/delete.png" width="25" height="25" title="Delete ' + integrationValueName + ' from group: ' + deliveryGroup.id + '" /></a>';
            if (groupStatus == 'obsoleted') {
                htmlContent += '<td>';
                let changeIdList = integrationValue[integrationValueName];
                changeIdList.forEach(function (changeId, index) {
                    let tmpRevertChangeId = changeId.revert_change_id;
                    htmlContent += '<p><a href="https://gerrit-gamma.gic.ericsson.se/#/q/' + tmpRevertChangeId + '" target="_blank">' + "Reverted Gerrit Link" + '</a></p>';
                    });
                    htmlContent += '</td>';
                }
            else if (groupStatus == 'queued') {
                htmlContent += '<td><p align="center">' + removeSection + '</p></td>'
            }
            htmlContent += '</tr>';
        });
    }
    htmlContent += '</div></div>';
    return htmlContent
}

function renderMissingDepSection(deliveryGroup, productName, dropName, groupStatus) {
    let htmlContent = "";
    if (deliveryGroup.missingDependencies) {
        htmlContent += '<input id="missing_' + deliveryGroup.id + '" type="checkbox" onchange="updateMissingDepAction(\''+ true + '\',\'' + deliveryGroup.id + '\',\'' + productName + '\',\'' + dropName + '\',\'' + groupStatus + '\')"  name="missingDeps_' + deliveryGroup.id + '" checked> This Group has missing dependencies';    
    } else {
        htmlContent += '<input id="missing_' + deliveryGroup.id + '" type="checkbox" onchange="updateMissingDepAction(\''+ false + '\',\'' + deliveryGroup.id + '\',\'' + productName + '\',\'' + dropName + '\',\'' + groupStatus + '\')"  name="missingDeps_' + deliveryGroup.id + '"> This Group has missing dependencies';    
    }
    htmlContent += '<br><br>';
    return htmlContent;
}

function removeServiceGroupAction(deliveryGroupId, serviceGroupName, gerritList, productName, dropName, groupStatus) {
    let proceed = "";
    proceed = confirm("Do you really want to remove "+ serviceGroupName + " from " + deliveryGroupId + " ? ");
    if (proceed) {
        let data = {
            'imageName': serviceGroupName,
            'gerritList': gerritList
        };
        $.ajax({
            type: 'DELETE',
            url: '/api/cloudNative/deliveryQueue/editServiceGroup/' + deliveryGroupId + '/',
            headers: { "X-CSRFToken": getCookie("csrftoken") },
            dataType: "json",
            data: data,
            success: function (json) {
                $('body').addClass('loading');
                alert("Service group successfully deleted.");
                window.location.href = "/cloudNative/" + productName + "/deliveryQueue/" + dropName + "/" + deliveryGroupId + "/?section=" + groupStatus;
            },
            error: function (xhr, textStatus, errorThrown) {
                alert("Issue removing service group: " + xhr.responseText);
            }
        });
        $('body').removeClass('loading');
    }
}

function removeImpactedENMDeliveryGroupAction(cnDeliveryGroupId, enmDeliveryGroupId, productName, dropName, groupStatus) {
    let proceed = "";
    proceed = confirm("Do you really want to remove Delivery group: "+ enmDeliveryGroupId + " from  Cloud Native Delivery group: " + cnDeliveryGroupId + " ? ");
    if (proceed) {
        let data = {
            'impactedDeliveryGroupNumber': enmDeliveryGroupId,
        };
        $.ajax({
            type: 'DELETE',
            url: '/api/cloudNative/deliveryQueue/editImpactedDeliveryGroup/' + cnDeliveryGroupId + '/',
            headers: { "X-CSRFToken": getCookie("csrftoken") },
            dataType: "json",
            data: data,
            success: function (json) {
                $('body').addClass('loading');
                alert("Impacted Delivery Group successfully deleted.");
                window.location.href = "/cloudNative/" + productName + "/deliveryQueue/" + dropName + "/" + cnDeliveryGroupId + "/?section=" + groupStatus;
            },
            error: function (xhr, textStatus, errorThrown) {
                alert("Issue removing service group: " + xhr.responseText);
            }
        });
        $('body').removeClass('loading');
    }
}

function removeIntegrationChartAction(deliveryGroupId, integrationChartName, gerritList, productName, dropName, groupStatus) {
    let proceed = "";
    proceed = confirm("Do you really want to remove "+ integrationChartName + " from " + deliveryGroupId + " ? ");
    if (proceed) {
        let data = {
            'integrationChartName': integrationChartName,
            'gerritList': gerritList
        };
        $.ajax({
            type: 'DELETE',
            url: '/api/cloudNative/deliveryQueue/editIntegrationChart/' + deliveryGroupId + '/',
            headers: { "X-CSRFToken": getCookie("csrftoken") },
            dataType: "json",
            data: data,
            success: function (json) {
                $('body').addClass('loading');
                alert("Integration Chart successfully deleted.");
                window.location.href = "/cloudNative/" + productName + "/deliveryQueue/" + dropName + "/" + deliveryGroupId + "/?section=" + groupStatus;
            },
            error: function (xhr, textStatus, errorThrown) {
                alert("Issue removing integration chart: " + xhr.responseText);
            }
        });
        $('body').removeClass('loading');
    }
}

function removeIntegrationValueAction(deliveryGroupId, integrationValueName, gerritList, productName, dropName, groupStatus) {
    let proceed = "";
    proceed = confirm("Do you really want to remove "+ integrationValueName + " from " + deliveryGroupId + " ? ");
    if (proceed) {
        let data = {
            'integrationValueName': integrationValueName,
            'gerritList': gerritList
        };
        $.ajax({
            type: 'DELETE',
            url: '/api/cloudNative/deliveryQueue/editIntegrationValue/' + deliveryGroupId + '/',
            headers: { "X-CSRFToken": getCookie("csrftoken") },
            dataType: "json",
            data: data,
            success: function (json) {
                $('body').addClass('loading');
                alert("Integration Value successfully deleted.");
                window.location.href = "/cloudNative/" + productName + "/deliveryQueue/" + dropName + "/" + deliveryGroupId + "/?section=" + groupStatus;
            },
            error: function (xhr, textStatus, errorThrown) {
                alert("Issue removing integration value: " + xhr.responseText);
            }
        });
        $('body').removeClass('loading');
    }
}

function removePipelineAction(deliveryGroupId, pipelineName, gerritList, productName, dropName, groupStatus) {
    let proceed = "";
    proceed = confirm("Do you really want to remove "+ pipelineName + " from " + deliveryGroupId + " ? ");
    if (proceed) {
        let data = {
            'pipelineName': pipelineName,
            'gerritList': gerritList
        };
        $.ajax({
            type: 'DELETE',
            url: '/api/cloudNative/deliveryQueue/editPipeline/' + deliveryGroupId + '/',
            headers: { "X-CSRFToken": getCookie("csrftoken") },
            dataType: "json",
            data: data,
            success: function (json) {
                $('body').addClass('loading');
                alert("Pipeline successfully deleted.");
                window.location.href = "/cloudNative/" + productName + "/deliveryQueue/" + dropName + "/" + deliveryGroupId + "/?section=" + groupStatus;
            },
            error: function (xhr, textStatus, errorThrown) {
                alert("Issue removing pipeline: " + xhr.responseText);
            }
        });
        $('body').removeClass('loading');
    }
}

function removeJiraAction(deliveryGroupId, jiraNumber, productName, dropName, groupStatus) {
    let proceed = "";
    proceed = confirm("Do you really want to remove "+ jiraNumber + " from " + deliveryGroupId + " ? ");
    if (proceed) {
        let data = {
            'jiraNumber': jiraNumber
        };
        $.ajax({
            type: 'DELETE',
            url: '/api/cloudNative/deliveryQueue/editJira/' + deliveryGroupId + '/',
            headers: { "X-CSRFToken": getCookie("csrftoken") },
            dataType: "json",
            data: data,
            success: function (json) {
                $('body').addClass('loading');
                alert("Jira ticket successfully deleted.");
                window.location.href = "/cloudNative/" + productName + "/deliveryQueue/" + dropName + "/" + deliveryGroupId + "/?section=" + groupStatus;
            },
            error: function (xhr, textStatus, errorThrown) {
                alert("Issue removing jira tickets: " + xhr.responseText);
            }
        });
        $('body').removeClass('loading');
    }
}

function checkUserActionObsoletion(deliveryGroupId, productName, dropName) {
    let proceed = "";
    proceed = confirm("Do you really want to obsolete delivery group " + deliveryGroupId + " ? ");
    if(proceed) {
        $('body').addClass('loading');
        $.ajax({
            type: 'POST',
            url: "/api/cloudNative/deliveryQueue/obsoleteCNDeliveryGroup/" + deliveryGroupId + "/",
            headers: { "X-CSRFToken": getCookie("csrftoken") },
            dataType: "json",
            success: function (json) {
                if(json == 'obsoleted'){
                    alert("Group successfully obsoleted.");
                    window.location = "/cloudNative/" + productName + "/deliveryQueue/" + dropName + "/" + deliveryGroupId + "?section=" + json;
                }
                $('body').removeClass('loading');
            },
            error: function (xhr, textStatus, errorThrown) {
                alert("Issue obsoleting Group: " + xhr.responseText);
                window.location = "/cloudNative/" + productName + "/deliveryQueue/" + dropName + "/" + deliveryGroupId + "?section=delivered";
                $('body').removeClass('loading');
            }
        })
    }
}

function checkUserActionRestoration(deliveryGroupId, productName, dropName) {
    let proceed = "";
    proceed = confirm("Do you really want to deliver delivery group " + deliveryGroupId + " ? ");
    if(proceed) {
        $.ajax({
            type: 'POST',
            url: "/api/cloudNative/deliveryQueue/restoreCNDeliveryGroup/" + deliveryGroupId + "/",
            headers: { "X-CSRFToken": getCookie("csrftoken") },
            dataType: "json",
            success: function (json) {
                $('body').addClass('loading');
                alert("Group successfully restored.");
                window.location = "/cloudNative/" + productName + "/deliveryQueue/" + dropName + "/" + deliveryGroupId + "?section=queued";
            },
            error: function (xhr, textStatus, errorThrown) {
                alert("Issue restoring Group: " + xhr.responseText);
            }
        })
    }
}

function checkUserActionDeletion(deliveryGroupId, productName, dropName) {
    let proceed = "";
    proceed = confirm("Do you really want to delete delivery group " + deliveryGroupId + " ? ");
    if(proceed) {
        $.ajax({
            type: 'POST',
            url: "/api/cloudNative/deliveryQueue/deleteCNDeliveryGroup/" + deliveryGroupId + "/",
            headers: { "X-CSRFToken": getCookie("csrftoken") },
            dataType: "json",
            success: function (json) {
                $('body').addClass('loading');
                alert("Group successfully deleted.");
                window.location = "/cloudNative/" + productName + "/deliveryQueue/" + dropName + "/" + deliveryGroupId + "?section=deleted";
            },
            error: function (xhr, textStatus, errorThrown) {
                alert("Issue deleting Group: " + xhr.responseText);
            }
        })
    }
}

function updateMissingDepAction(currValue, deliveryGroupId, productName, dropName, groupStatus) {
    let params = {
        "deliveryGroupNumber": deliveryGroupId,
        "missingDepValue": !currValue,
        "missingDepReason": ""
    }
    if (currValue == 'true') {
        let proceed = confirm("Are you sure this delivery group does not have missing dependencies ?");
        if (proceed) {
            $('body').addClass('loading');
            $.ajax({
                type: 'PUT',
                url: "/api/cloudNative/deliveryQueue/updateMissingDependencies/" + deliveryGroupId + "/",
                headers: { "X-CSRFToken": getCookie("csrftoken") },
                dataType: "json",
                data: JSON.stringify(params),
                success: function (json) {
                    alert("Missing Dependencies successfully unchecked.");
                    window.location = "/cloudNative/" + productName + "/deliveryQueue/" + dropName + "/" + deliveryGroupId + "?section=" + groupStatus;
                },
                error: function (xhr, textStatus, errorThrown) {
                    alert("Issue unchecking missing dependencies: " + xhr.responseText);
                    window.location = "/cloudNative/" + productName + "/deliveryQueue/" + dropName + "/" + deliveryGroupId + "?section=" + groupStatus;
                }
            })
        } else {
            $('#missing_' + deliveryGroupId).prop('checked', currValue);
        }
    } 
    if (currValue == 'false') {
        let proceed = confirm("Are you sure this delivery group has missing dependencies ?");
        if (proceed) {
            window.location = "/cloudNative/deliveryQueue/addMissingDependenciesReason/" + dropName + "/" + deliveryGroupId;
        } else {
            $('#missing_' + deliveryGroupId).removeAttr('checked');
        }
    }
}

function checkSubscription(msg, id) {
    var json_data = '{"deliveryGroup": ' + id + '}';
    var proceed = confirm(msg);
    if (proceed) {
        $('body').addClass('loading');
        $.ajax({
            type: 'POST',
            url: "/api/cloudNative/deliveryQueue/subscriptions/",
            data: json_data,
            headers: { "X-CSRFToken": getCookie("csrftoken") },
            contentType: "application/json",
            success: function (json, textStatus) {
                location.reload();
            },
            error: function (xhr, textStatus, errorThrown) {
                alert("Issue Subscribing to Group: " + (errorThrown ? errorThrown : xhr.status));
            }
        });
    }
}


function checkBoxAction(msg, id, value, checkboxType) {
    var proceed = confirm(msg);
    if (proceed) {
        $('body').addClass('loading');
        if (checkboxType == "missingDeps"){
           $('#missingForm_' + id).submit();
        } else {
           $('#ccbApprovedForm_' + id).submit();
        }
    } else {
        if (checkboxType = "missingDep"){
           if (value == 'true') {
               $('#missing_' + id).prop('checked', true);
           } else {
               $('#missing_' + id).prop('checked', false);
           }
        } else{
          if (value == 'true') {
              $('#ccbApproved_' + id).prop('checked', true);
          } else {
              $('#ccbApproved_' + id).prop('checked', false);
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
            if (c_end == -1) c_end = document.cookie.length;
            return unescape(document.cookie.substring(c_start,c_end));
        }
    }
    return "";
}
