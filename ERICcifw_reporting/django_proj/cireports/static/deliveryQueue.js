var packagestable;
var testwaretable;
var product_name;
var drop_name;
var groupid;
var userPerms;
var editPerms;
var permsSummary;
var frozen;
var deliveryGroupSubscriptions;
var subscriptionStatus;
var displaySubscriptionStatus;
var impactedCNDeliveryGroupIds = [];

$(document).ready(function () {
    packagestable = $('table#drop-package-revisions');
    testwaretable = $('table#drop-testware-revisions');
    product_name = $('#hidden_product_div').html();
    drop_name = $('#hidden_drop_div').html();
    groupid = $('#hidden_group_div').html();
    userPerms = ($('#hidden_userPerms_div').html() == 'True');
    editPerms = ($('#hidden_editPerms_div').html() == 'True');
    permsSummary = $('#hidden_permsSummary_div').html();
    frozen = ($('#hidden_frozen_div').html() != 'False');
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
    $('#dialog-alert').dialog({
        'autoOpen': false
    });

    function loadSubscriptions() {
        $.ajax({
            type: 'GET',
            url: "/api/deliverygroup/subscriptions/",
            dataType: 'json',
            cache: false,
            success: function (json, textStatus) {
                for (data in json)
                    deliveryGroupSubscriptions.push((json[data]['fields'].deliveryGroup));
            },
            error: function (xhr, textStatus, errorThrown) {
                deliveryGroupSubscriptions.push('No User')
            }
        });
    }
    loadSubscriptions();

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

    function buildQueueResults() {
        $('body').addClass('loading');
        $.ajax({
            type: 'GET',
            url: "/" + product_name + "/queue/" + drop_name + "/" + 'json/',
            dataType: 'json',
            cache: false,
            success: function (json, textStatus) {
                var x = 0;
                jiraUrl = json.jiraUrl;
                deliveryGroups = json.deliveryGroups;
                html_content = {
                    'queued': '',
                        'delivered': '',
                        'obsoleted': '',
                        'deleted': '',
                };
                for (key in html_content) {
                    html_content[key] += '<div style="float:right;"><a href="javascript:void(0)" class="expand' + key + '">Expand All</a> | <a href="javascript:void(0)" class="collapse' + key + '">Collapse All</a></div><br>';
                    html_content[key] += '<div class="accordion groupaccordion" id="accordion' + key + '">';

                }
                deliveryGroupCount = deliveryGroups.length;
                for (deliveryGroupKey in deliveryGroups) {
                    deliveryGroup = deliveryGroups[deliveryGroupKey];
                    artifacts = deliveryGroup.artifacts;
                    jiras = deliveryGroup.jiras;
                    comments = deliveryGroup.comments;
                    testware = deliveryGroup.testware;
                    includedInPriorityTestSuite = deliveryGroup.includedInPriorityTestSuite
                    testwareTypes = deliveryGroup.testwareTypes
                    iso = deliveryGroup.iso;
                    consolidate =  deliveryGroup.consolidatedGroup;
                    bugOrTR  = deliveryGroup.bugOrTR;
                    newartifact =  deliveryGroup.newArtifact;
                    impactedCNDeliveryGroup = deliveryGroup.impactedCNDeliveryGroup;
                    groupStatus = "queued";
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
                    if (testware.length != 0) {
                         if (includedInPriorityTestSuite.length != 0) {
                              html_content[groupStatus] += '<h2 id="group' + deliveryGroup.id + '" class="priority_testware_group">'
                         } else {
                             html_content[groupStatus] += '<h2 id="group' + deliveryGroup.id + '" class="testware_group">'
                         }
                    }else{
                         html_content[groupStatus] += '<h2 id="group' + deliveryGroup.id + '" class="productware_group">'
                    }
                    html_content[groupStatus] += 'Group:' + deliveryGroup.id;
                    if (displaySubscriptionStatus) {
                        html_content[groupStatus] += '<img src="/static/images/watched.png" style="float: right" title="Watcher for Group: ' + deliveryGroup.id + '" />';
                    }
                    if (deliveryGroup.warning) {
                        html_content[groupStatus] += '<img src="/static/images/warning.png" alt="warning" title="Warning: Issue with Delivery Group" class="delivery_group_flag_img"/>';
                    }
                    if (deliveryGroup.autoCreated) {
                        html_content[groupStatus] += ' <img src="/static/images/autoCreatedFlag.svg" alt="autoCreated" title="Auto Created Delivery Group" class="delivery_group_flag_img" /> ';
                    }
                    if (deliveryGroup.missingDependencies) {
                        html_content[groupStatus] += ' <img src="/static/images/missingDepFlag.svg" alt="missingDependencies" title="Missing Dependencies" class="delivery_group_flag_img" />';
                    }
                    if (deliveryGroup.consolidatedGroup){
                        html_content[groupStatus] += ' <img src="/static/images/consolidatedFlag.svg" alt="ConsolidatedGroup" title="Services Linked To Consolidated Group" class="delivery_group_flag_img" />';
                    }
                    if (deliveryGroup.ccbApproved){
                        html_content[groupStatus] += ' <img src="/static/images/ccbApprovedFlag.svg" alt="CCBApproved" title="CCB Approved Delivery Group" class="delivery_group_flag_img" />';
                    }
                    if (deliveryGroup.newArtifact){
                        html_content[groupStatus] += ' <img src="/static/images/newartifactFlag.svg" alt="newArtifact" title="New Artifact to Baseline" class="delivery_group_flag_img" />';
                    }
                    if (deliveryGroup.bugOrTR){
                        html_content[groupStatus] += ' <img src="/static/images/bug.png" alt="Bug or Tr" title="Group Contains Bug Or TR Jira" class="delivery_group_flag_img" />';
                    }
                    if (impactedCNDeliveryGroup.length > 0){
                        html_content[groupStatus] += ' <img src="/static/images/impactedDgFlag.svg" alt="cENM Dg Aligned" title="Group Aligned with cENM DG" class="delivery_group_flag_img" />';
                    }
                    if (testware.length != 0) {
                        if (includedInPriorityTestSuite.length != 0) {
                             html_content[groupStatus] += ' - Contains ' + testwareTypes.toString() + ' Testware';
                        } else {
                            html_content[groupStatus] += ' - Contains Testware';
                        }
                    }
                    if (jiras.length == 0) {
                        html_content[groupStatus] += ' - No JIRA Ticket(s) associated';
                    }
                    html_content[groupStatus] += '</h2>';
                    if (iso) {
                        if (iso['deliveryGroup_status'] == 'delivered') {
                            isoString = ' | Included in <a href="/' + product_name + '/' + drop_name + '/mediaContent/' + iso["iso__mediaArtifact__name"] + '/' + iso["iso__version"] + '">' + iso["iso__version"] + '</a>';
                        } else {
                            isoString = ' | Removed from  <a href="/' + product_name + '/' + drop_name + '/mediaContent/' + iso["iso__mediaArtifact__name"] + '/' + iso["iso__version"] + '">' + iso["iso__version"] + '</a>'
                        }
                    } else {
                        isoString = "";
                    }
                    if (deliveryGroup.component__element) {
                        createdByTeamString = ' | Created by Team: ' + deliveryGroup.component__element + ' ' + deliveryGroup.component__parent__label__name +': ' + deliveryGroup.component__parent__element;
                    } else {
                        createdByTeamString = "";
                    }
                    html_content[groupStatus] += '<div>' +
                        '<table class="general-table" width="100%">' +
                        '<tr>' +
                        '<th class="delivery_group_banner" colspan=9>' +
                        '<div class="table-title">Delivery Group: ' + deliveryGroup.id + isoString + createdByTeamString + " " + ' </div>';
                    if (groupStatus == "queued") {
                        html_content[groupStatus] += '<div class="table-actions">' +
                            subscriptionStatus +
                            '<a class="img" href="/' + product_name + '/multipleDeliveries/?groupid=' + deliveryGroup.id + '"><img src="/static/images/edit.png" title="Edit Delivery Group: ' + deliveryGroup.id + '" /></a>' +
                            '<a class="img" href="javascript:void(0);" onClick="checkAction(\'Do you really want to delete Delivery Group ' + deliveryGroup.id + '?\', \'/' + product_name + '/updateDeliveryGroup/' + drop_name + '/' + deliveryGroup.id + '/True/\')"><img src="/static/images/delete.png" title="Delete Delivery Group: ' + deliveryGroup.id + '" /></a>' +
                            '</div>';
                    }
                    html_content[groupStatus] += '</th></tr>'
                    if (impactedCNDeliveryGroup.length > 0) {
                        html_content[groupStatus] += renderImpactedCNDeliveryGroupSection(deliveryGroup, impactedCNDeliveryGroup, groupStatus, drop_name);
                    }
                    html_content[groupStatus] += '<th>Artifact Name</th>' +
                        '<th>Version</th>' +
                        '<th>Date Created</th>' +
                        '<th>Size(MB)</th>' +
                        '<th>Services</th>' +
                        '<th>Category</th>' +
                        '<th>KGB</th>' +
                        '<th>Team(s)</th>';
                    if (groupStatus == 'queued') {

                        html_content[groupStatus] += '<th>Action</th>';
                    }
                    html_content[groupStatus] += '</tr>';
                    for (artifactKey in artifacts) {
                        artifact = artifacts[artifactKey]['artifact'];
                        nexusUrl = artifacts[artifactKey]['nexusUrl'];
                        kgbResult = artifacts[artifactKey]['frozenKGBresult'];
                        teamsWithLineBreak = artifact.team.replace(/,/g, '<br>');
                        if(artifact.packageRevision__category__name === "testware"){
                            if(artifact.priorityTestware){
                                 html_content[groupStatus] += '<tr class="priority_testware_artifact_in_group">';
                            } else {
                                html_content[groupStatus] += '<tr class="testware_artifact_in_group">';
                            }
                        } else {
                            html_content[groupStatus] += '<tr class="productware_artifact_in_group">';
                        }
                        html_content[groupStatus] += '<td> <a href="/'+ product_name +'/packages/'+ artifact.packageRevision__package__name +'">' + artifact.packageRevision__package__name + '</a></td><td><a href="'+ nexusUrl +'">' + artifact.packageRevision__version + '</a></td><td>' + artifact.packageRevision__date_created.replace('T', ' ') + '</td>';
                        var artifactSize = artifact.packageRevision__size;
                        if (artifactSize == 0) {
                            artifactSize == "--";
                        }else{
                            artifactSize = Math.round((artifactSize/(1024*1024))*1000)/1000;
                        }
                        html_content[groupStatus] += '<td>' + artifactSize + '</td>';
                        if (artifact.services != "None") {
                        serviceHtml = createList(artifact.services);
                        html_content[groupStatus] += '<td>' + '<div class="dropdown">'+
                                                    '<button class="dropbtn">Services</button>'+
                                                    '<div class="dropdown-content">'+
                                                    serviceHtml+
                                                    '</div>' +
                                                    '</div>' +
                        '</td>';
                        }else{
                            serviceHtml = " No Services"
                            html_content[groupStatus] += '<td>' + serviceHtml+ '</td>';
                        }
                        if(artifact.packageRevision__category__name === "testware"){
                            if(artifact.priorityTestware){
                                html_content[groupStatus] += '<td>' + artifact.testwareTypes.toString() + ' ' + artifact.packageRevision__category__name + '</td>'
                            } else {
                                html_content[groupStatus] += '<td>' + artifact.packageRevision__category__name + '</td>'
                            }
                        } else {
                                html_content[groupStatus] += '<td>' + artifact.packageRevision__category__name + '</td>'
                        }
                        html_content[groupStatus] += '<td><p align="center">'

                        if (kgbResult == "True") {
                            if(artifact.kgb_test == 'not_started' || artifact.testReport == "" || artifact.kgb_test == 'in_progress'){
                                html_content[groupStatus] += '<img src="/static/images/';
                                if (artifact.kgb_snapshot_report == true) {
                                     html_content[groupStatus] += 'snapshot_' + artifact.kgb_test + '.png" title="Snapshot(s) Used in KGB Testing" alt="snapshot_';
                                } else{
                                     html_content[groupStatus] += artifact.kgb_test + '.png" alt="';
                                }
                                html_content[groupStatus] +=  artifact.kgb_test + '" width="30" height="30"><span style="display:none">' + artifact.kgb_test;
                            } else{
                               html_content[groupStatus] += '<a class="img" href="'+artifact.testReport+'"> <img src="/static/images/';
                               if (artifact.kgb_snapshot_report == true) {
                                   html_content[groupStatus] += 'snapshot_' + artifact.kgb_test + '.png" title="Snapshot(s) Used in KGB Testing" alt="snapshot_';
                               } else{
                                   html_content[groupStatus] += artifact.kgb_test + '.png" alt="';
                               }
                               html_content[groupStatus] += artifact.kgb_test + '" width="30" height="30"><span style="display:none">' + artifact.kgb_test +'</a>';
                            }
                        } else {
                            if(artifact.packageRevision__kgb_test == 'not_started' ||  artifact.packageRevision__kgb_test == 'in_progress'){
                                html_content[groupStatus] += '<img src="/static/images/';
                                if (artifact.kgb_snapshot_report == true) {
                                    html_content[groupStatus] += 'snapshot_' + artifact.kgb_test + '.png" title="Snapshot(s) Used in KGB Testing" alt="snapshot_';
                                } else {
                                    html_content[groupStatus] +=  artifact.packageRevision__kgb_test + '.png" alt="';
                                }
                                html_content[groupStatus] += artifact.packageRevision__kgb_test + '" width="30" height="30"><span style="display:none">' + artifact.packageRevision__kgb_test
                            }else{
                                html_content[groupStatus] += '<a class="img" href="'+ product_name +'/returnresults/'+ artifact.packageRevision__package__name +'/'+ artifact.packageRevision__version +'/kgb/rpm/"><img src="/static/images/';
                                if (artifact.kgb_snapshot_report == true) {
                                     html_content[groupStatus] += 'snapshot_' + artifact.packageRevision__kgb_test + '.png" title="Snapshot(s) Used in KGB Testing" alt="snapshot_';
                                } else{
                                    html_content[groupStatus] += artifact.packageRevision__kgb_test + '.png" alt="';
                                }
                                html_content[groupStatus] += artifact.packageRevision__kgb_test + '" width="30" height="30"><span style="display:none">' + artifact.packageRevision__kgb_test +'</a>'
                            }
                        }
                        html_content[groupStatus] += '</span></p></td>' + '<td>' + teamsWithLineBreak + '</td>';
                        if (groupStatus == 'queued') {
                            html_content[groupStatus] += '<td><p align="center"><a class="img" href="javascript:void(null);" onClick="checkAction(\'Do you really want to delete ' + artifact.packageRevision__package__name + ' from the group?\', \'/' + product_name + '/deleteFromGroup/' + drop_name + '/' + artifact.id + '/\')"><img src="/static/images/delete.png" width="25" height="25" title="Delete ' + artifact.packageRevision__package__name + ' from group: ' + deliveryGroup.id + '" /></a></p></td>';
                        }
                        html_content[groupStatus] += '</tr>';
                    }
                    html_content[groupStatus] += '</table>';
                    if (jiras.length > 0) {
                        html_content[groupStatus] += '<div class="accordion" id="accordionjira">' +
                            '<h2 id="' + groupStatus + '">Jiras</h2>' +
                            '<div>' +
                            '<table class="general-table" width="100%">' +
                            '<tr>' +
                            '<th class="title" colspan=5>' +
                            '<div class="table-title">Delivery Group: ' + deliveryGroup.id + '</div>' +
                            '<div class="table-actions">' +
                            '<a class="img" href="/' + product_name + '/addjira/' + drop_name + '/' + deliveryGroup.id + '/queued"><img src="/static/images/create.png" title="Add Jira to ' + deliveryGroup.id + '" /></a>' +
                            '</div>' +
                            '</th>' +
                            '</tr>' +
                            '<tr>' +
                            '<th>Issue</th>' +
                            '<th>Type</th>' +
                            '<th>Label</th>' +
                            '<th>TR Classification Group (TCG)</th>' +
                            '<th></th>' +
                            '</tr>';
                        for (jiraKey in jiras) {
                            jira = jiras[jiraKey];
                            jiraLabels = '';
                            for (labelKey in jira.labels) {
                                jiraLabels += jira.labels[labelKey] + '<br>';
                            }
                            jiraTCGs = '';
                            for (tcgKey in jira.tcgs) {
                                jiraTCGs += jira.tcgs[tcgKey] + '<br>';
                            }
                            html_content[groupStatus] += '<tr>' +
                                '<td><a href="' + jira.jiraLink + '" target="_blank">' + jira.jira.jiraIssue__jiraNumber + '</a></td>' +
                                '<td>' + jira.jira.jiraIssue__issueType + '</td>' +
                                '<td>' + jiraLabels + '</td>' +
                                '<td>' + jiraTCGs + '</td>' +
                                '<td><p align="center"><a class="img" href="javascript:void(0);" onClick="checkAction(\'Do you really want to delete ' + jira.jira.jiraIssue__jiraNumber + ' from the group?\', \'/' + product_name + '/deleteJiraFromGroup/' + drop_name + '/' + jira.jira.id + '\')"><img src="/static/images/delete.png" width="25" height="25" title="Delete ' + jira.jira.jiraIssue__jiraNumber + ' from group: ' + deliveryGroup.id + '" /></a></p></td>' +
                                '</tr>';
                        }

                        html_content[groupStatus] += '</table>' +
                            '</div>' +
                            '</div>';
                    }

                    html_content[groupStatus] += '<div class="accordion" id="accordioncomment">' +
                        '<h2 id="' + groupStatus + 'Comments">Comments</h2>' +
                        '<div>' +
                        '<table class="general-table" width="100%">' +
                        '<tr>' +
                        '<th class="title" colspan=2>' +
                        '<div class="table-title">Delivery Group: ' + deliveryGroup.id + '</div>' +
                        '<div class="table-actions">' +
                        '<a class="img" href="/' + product_name + '/addcomment/' + drop_name + '/' + deliveryGroup.id + '/queued"><img src="/static/images/create.png" title="Add Comment to ' + deliveryGroup.id + '" /></a>' +
                        '</div>' +
                        '</th>' +
                        '</tr>';
                    for (commentKey in comments) {
                        comment = comments[commentKey];
                        if (comment.date) {
                            commentDateString = comment.date.replace('T', ' ');
                        } else {
                            commentDateString = '-';
                        }
                        if (comment.comment){
                            comment = comment.comment;
                            if(comment.indexOf('https') !== -1 && comment.indexOf('Auto created') !== -1) {
                                let urls = comment.match(/\bhttps?:\/\/\S+/gi);
                                comment = comment.replace(urls[0],'') + '<a href="' + urls[0] + '">' + urls[0] + '</a>'
                            }
                        } else {
                            comment = ""
                        }
                        html_content[groupStatus] += '<tr>' +
                            '<td>' + comment + '</td>' +
                            '<td>' + commentDateString + '</td>' +
                            '</tr>';
                    }
                    html_content[groupStatus] += '</table>' +
                        '</div>' +
                        '</div>';

                    html_content[groupStatus] += '<div class="accordion" id="accordionservice">' +
                        '<h2 id="' + groupStatus + 'Comments">DeliveryGroup To Services</h2>' +
                        '<div>' +
                        '<table class="general-table" >' +
                        '<tr>' +
                        '<th class="title" colspan=2>' +
                        '<div class="table-title">Delivery Group: ' + deliveryGroup.id + '</div>' +
                        '<div class="table-actions">' +
                        '</div>' +
                        '</th>' +
                        '</tr>' +
                        '<tr>' +
                        '<th>Services</th>' +
                        '</tr>';

                    serviceArray = [];
                    for (artifactKey in artifacts) {
                        artifact = artifacts[artifactKey]['artifact'];
                        if (artifact.services != "None") {
                            for (var i = 0; i < artifact.services.length; i++){
                                if (serviceArray.indexOf(artifact.services[i]) > -1) {
                                    continue;
                                }
                                serviceArray.push(artifact.services[i]);
                            }
                        }
                    }
                    deliveryGroupToServiceHtml = createList(serviceArray);
                    html_content[groupStatus] += '<tr>' +
                        '<td class = "general-table-column">' + deliveryGroupToServiceHtml + '</td>'
                        '</tr>';
                    html_content[groupStatus] += '</table>' +
                        '</div>' +
                        '</div>';

                    if (groupStatus == 'queued') {
                        html_content[groupStatus] += '<div style="position: relative;">' +
                            '<form enctype="multipart/form-data" id="missingDepsForm_' + deliveryGroup.id + '" method="post" action="/' + product_name + '/missingDependencies/' + drop_name + '/' + deliveryGroup.id + '/">' +
                            '<span style="float: left; clear: right;">';
                        if (deliveryGroup.missingDependencies) {
                            if (includedInPriorityTestSuite.length != 0) {
                                html_content[groupStatus] += '<input id="missingDeps_' + deliveryGroup.id + '" type="checkbox" onclick="checkBoxAction(\'Do you really want to unflag this Delivery Group ' + deliveryGroup.id + ' as having missing dependencies? \\n \',\'' + deliveryGroup.id + '\', \'' + deliveryGroup.missingDependencies + '\',\'missingDeps\')"  name="missingDeps_' + deliveryGroup.id + '" checked> This Group has missing dependencies';
                            } else {
                                html_content[groupStatus] += '<input id="missingDeps_' + deliveryGroup.id + '" type="checkbox" onclick="checkBoxAction(\'Do you really want to unflag this Delivery Group ' + deliveryGroup.id + ' as having missing dependencies? \\n **Note: if this Group contains only non Priority Testware, it will be automatically delivered into drop '+ drop_name + '**\',\'' + deliveryGroup.id + '\', \'' + deliveryGroup.missingDependencies + '\',\'missingDeps\')"  name="missingDeps_' + deliveryGroup.id + '" checked> This Group has missing dependencies';
                            }
                        } else {
                            html_content[groupStatus] += '<input id="missingDeps_' + deliveryGroup.id + '" type="checkbox" onclick="checkBoxAction(\'Do you really want to flag this Delivery Group ' + deliveryGroup.id + ' as having missing dependencies?\',\'' + deliveryGroup.id + '\', \'' + deliveryGroup.missingDependencies + '\',\'missingDeps\')"  name="missingDeps_' + deliveryGroup.id + '"> This Group has missing dependencies';
                        }
                        html_content[groupStatus] += '</span><br></form>';
                        html_content[groupStatus] += '<form enctype="multipart/form-data" id="ccbApprovedForm_' + deliveryGroup.id + '" method="post" action="/' + product_name + '/ccbApproved/' + drop_name + '/' + deliveryGroup.id + '/">' +
                            '<span style="float: left; clear: right;">';
                        if (deliveryGroup.ccbApproved) {
                             html_content[groupStatus] += '<input id="ccbApproved_'+ deliveryGroup.id + '" type="checkbox" onclick="checkBoxAction(\'Do you really want to remove CCB Approved flag from Delivery Group ' + deliveryGroup.id + '?\',\'' + deliveryGroup.id + '\', \'' + deliveryGroup.ccbApproved + '\',\'ccbApproved\')"  name="ccbApproved_' + deliveryGroup.id + '" checked> This Group is CCB Approved';
                        } else {
                             html_content[groupStatus] += '<input id="ccbApproved_' + deliveryGroup.id + '" type="checkbox" onclick="checkBoxAction(\'Do you really want to flag this Delivery Group ' + deliveryGroup.id + ' as CCB Approved?\',\'' + deliveryGroup.id + '\', \'' + deliveryGroup.ccbApproved + '\',\'ccbApproved\')"  name="ccbApproved_' + deliveryGroup.id + '" > This Group is CCB Approved';
                        }
                        html_content[groupStatus] += '</span></form><span style="right: 0px; position: absolute; top: 0px;"';
                        if (userPerms && editPerms) {
                            if (deliveryGroup.missingDependencies && !frozen) {
                                html_content[groupStatus] += 'class="btn btn-default button-disabled" title="Missing Dependencies Cannot Deliver" disabled>Deliver This Group';
                            } else if (!frozen) {
                                html_content[groupStatus] += '><a class="btn btn-default" id="link_' + deliveryGroup.id + '" href="javascript:void(0);"  onClick="checkUserActionDelivery(\'Do you really want to deliver Delivery Group ' + deliveryGroup.id + ' to ' + drop_name + '?\',\'/' + product_name + '/deliverGroup/' + drop_name + '/' + deliveryGroup.id + '/\',\'' + deliveryGroup.id + '\')">Deliver This Group</a>';
                            } else {
                                html_content[groupStatus] += 'class="btn btn-default button-disabled" title="' + permsSummary + '" disabled>Deliver This Group';
                            }
                        } else {
                            html_content[groupStatus] += 'class="btn btn-default button-disabled" style="pointer-events: auto !important;"';
                            if (editPerms && !frozen) {
                                html_content[groupStatus] += 'title="No Permissions to Deliver"';
                            } else {
                                html_content[groupStatus] += 'title="' + permsSummary + '"';
                            }
                            html_content[groupStatus] += ' disabled>Deliver This Group';
                        }
                        html_content[groupStatus] += '</span></div>';
                    }

                    if (groupStatus == 'delivered') {
                         html_content[groupStatus] += '<div align="right">';
                        if (userPerms && !frozen) {
                            html_content[groupStatus] += '<a class="btn btn-default" id="link_' + deliveryGroup.id + '" href="javascript:void(0);"  onClick="checkUserAction(\'Do you really want to obsolete Delivery Group ' + deliveryGroup.id + ' from ' + drop_name + '?\',\'/' + product_name + '/obsoleteGroup/' + drop_name + '/' + deliveryGroup.id + '/\',\'' + deliveryGroup.id + '\')">Obsolete This Group</a>';
                        } else {
                            html_content[groupStatus] += '<span class="btn btn-default button-disabled" title="';
                            if (frozen) {
                                html_content[groupStatus] += permsSummary;
                            } else {
                                html_content[groupStatus] += 'No Permissions to Obsolete';
                            }
                            html_content[groupStatus] += '" disabled>Obsolete This Group</span>';
                        }
                        html_content[groupStatus] += '</div>';
                    }

                    if (groupStatus == 'obsoleted' || groupStatus == 'deleted') {
                        if (userPerms && !frozen) {
                            if (groupStatus == 'obsoleted') {
                                action = 'unobsolete';
                            } else {
                                action = 'False';
                            }
                            html_content[groupStatus] += '<div align="right"><a href="javascript:void(0);" class="btn btn-default"  onClick="checkAction(\'Do you really want to restore Delivery Group ' + deliveryGroup.id + ' to the Queue?\', \'/' + product_name + '/updateDeliveryGroup/' + drop_name + '/' + deliveryGroup.id + '/' + action + '/\')">Restore Delivery Group</a></div>';
                        } else {
                            html_content[groupStatus] += '<div align="right"><span class="btn btn-default button-disabled" title="';
                            if (frozen) {
                                html_content[groupStatus] += permsSummary;
                            } else {
                                html_content[groupStatus] += 'No Permissions to Restore';
                            }
                            html_content[groupStatus] += '" disabled>Restore Delivery Group</span></div>';
                        }
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

                if (groupid != 'None')
                {
                    var groupAlreadySelected = false;
                    $(".groupaccordion > h2:first-child").each(function(index) {
                        if ($(this).attr('id') === 'group' + groupid)
                        {
                            groupAlreadySelected = true;
                            return;
                        }
                    });
                    if (!groupAlreadySelected)
                    {
                        $('#group' + groupid).click();
                        theOffset = $('#group' + groupid).offset();
                        $(window).scrollTop(theOffset.top -900);
                    }
                }
                $('.expandqueued').click(function () {
                    $('#accordionqueued > .ui-widget-content').show();
                    $('#accordionjira > .ui-widget-content').show();
                    $('#accordioncomment > .ui-widget-content').show();
                    $('#accordionservice > .ui-widget-content').show();
                });
                $('.collapsequeued').click(function () {
                    $('#accordionqueued > .ui-widget-content').hide();
                    $('#accordionjira > .ui-widget-content').hide();
                    $('#accordioncomment > .ui-widget-content').hide();
                    $('#accordionservice > .ui-widget-content').hide();
                });
                $('.expanddelivered').click(function () {
                    $('#accordiondelivered > .ui-widget-content').show();
                    $('#accordionjira > .ui-widget-content').show();
                    $('#accordioncomment > .ui-widget-content').show();
                    $('#accordionservice > .ui-widget-content').show();
                });
                $('.collapsedelivered').click(function () {
                    $('#accordiondelivered > .ui-widget-content').hide();
                    $('#accordionjira > .ui-widget-content').hide();
                    $('#accordioncomment > .ui-widget-content').hide();
                    $('#accordionservice > .ui-widget-content').hide();
                });
                $('.expandobsoleted').click(function () {
                    $('#accordionobsoleted > .ui-widget-content').show();
                    $('#accordionjira > .ui-widget-content').show();
                    $('#accordioncomment > .ui-widget-content').show();
                    $('#accordionservice > .ui-widget-content').show();
                });
                $('.collapseobsoleted').click(function () {
                    $('#accordionobsoleted > .ui-widget-content').hide();
                    $('#accordionjira > .ui-widget-content').hide();
                    $('#accordioncomment > .ui-widget-content').hide();
                    $('#accordionservice > .ui-widget-content').hide();
                });
                $('.expanddeleted').click(function () {
                    $('#accordiondeleted > .ui-widget-content').show();
                    $('#accordionjira > .ui-widget-content').show();
                    $('#accordioncomment > .ui-widget-content').show();
                    $('#accordionservice > .ui-widget-content').show();
                });
                $('.collapsedeleted').click(function () {
                    $('#accordiondeleted > .ui-widget-content').hide();
                    $('#accordionjira > .ui-widget-content').hide();
                    $('#accordioncomment > .ui-widget-content').hide();
                    $('#accordionservice > .ui-widget-content').hide();
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

function stopAutoDelivery(dropId, newAutoDeliveryState) {
     $.ajax({
            type: 'PUT',
            url: "/drops/"+dropId+"/",
            data: JSON.stringify({dropId:dropId, autoDeliveryStatus: newAutoDeliveryState}),
            headers: { "X-CSRFToken": getCookie("csrftoken") },
            contentType: "application/json",
            success: function (json, textStatus) {
                location.reload();
                console.log(json)
                console.log(textStatus)
            },
            error: function (xhr, textStatus, errorThrown) {
                console.log('failed with '+textStatus)
            }
        });

}

function greetMsg(msg) {
    alert(msg);
}

function renderImpactedCNDeliveryGroupSection(deliveryGroup, impactedCNDGList, groupStatus, dropName) {
    let htmlContent = '';
    let section = 'queued';
    let colSpan = 8;
    if (impactedCNDGList.length > 0) {
        impactedCNDGList.forEach(function (impactedcndgs) {
            let removeSection = '<a class="img" href="javascript:void(0);" onClick="removeImpactedCNDeliveryGroupAction(\''+ impactedcndgs.cnDeliveryGroup__id + '\',\'' + deliveryGroup.id + '\',\'' + dropName + '\',\'' + groupStatus + '\')"><img src="/static/images/delete.png" width="25" height="25" title="Delete ' + deliveryGroup.id + ' from group: ' + impactedcndgs.cnDeliveryGroup__id + '" /></a>';
            impactedCNDeliveryGroupIds.push([deliveryGroup.id,impactedcndgs.cnDeliveryGroup__id]);
            if (groupStatus != 'queued') {
                removeSection = ''
                colSpan = 7;
            }
            if (impactedcndgs.cnDeliveryGroup__delivered){
                section = 'delivered';
            }
            else if (impactedcndgs.cnDeliveryGroup__obsoleted){
                section = 'obsoleted';
            }
            else if (impactedcndgs.cnDeliveryGroup__deleted){
                section = 'deleted';
            }
            htmlContent += '<tr>' +
                '<th colspan='+colSpan+'>Impacted Cloud Native Delivery Group: <a href="/cloudNative/CloudNativeENM/deliveryQueue/'+drop_name+'/'+impactedcndgs.cnDeliveryGroup__id+'/?section='+section+'">' + impactedcndgs.cnDeliveryGroup__id + '</a>' + ' </th>' +
                '<td><p align="center">' + removeSection + '</p></td>' +
                '</tr>';
        });
    }
    htmlContent += '</div></div>';
    return htmlContent;
}

function removeImpactedCNDeliveryGroupAction(cnDeliveryGroupId, enmDeliveryGroupId, dropName, groupStatus) {
    let proceed = "";
    proceed = confirm("Do you really want to remove Cloud Native delivery group: "+ cnDeliveryGroupId + " from Delivery group: " + enmDeliveryGroupId + " ? ");
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
                window.location.href = "/ENM/queue/" + dropName + "/" + enmDeliveryGroupId + "/?section=" + groupStatus;
            },
            error: function (xhr, textStatus, errorThrown) {
                alert("Issue removing service group: " + xhr.responseText);
            }
        });
        $('body').removeClass('loading');
    }
}

function createList(artifact){
    var returnString = "<ul id='newList'>"
    for (cnt = 0; cnt < artifact.length; cnt++) {
       returnString += "<li>"+artifact[cnt]+"</li>";
    }
    returnString += "</ul>"
    return returnString
}

function checkSubscription(msg, id) {
    var json_data = '{"deliveryGroup": ' + id + '}';
    var proceed = confirm(msg);
    if (proceed) {
        $('body').addClass('loading');
        $.ajax({
            type: 'POST',
            url: "/api/deliverygroup/subscriptions/",
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

function checkAction(msg, link) {
    var proceed = confirm(msg);
    if (proceed) {
        $('body').addClass('loading');
        window.location = link;
    }
}

function checkUserActionDelivery(msg, link, id) {
    var proceed = "";
    for (index in impactedCNDeliveryGroupIds){
        let cnDeliveryGroupId = impactedCNDeliveryGroupIds[index][1]
        let deliveryGroupId = impactedCNDeliveryGroupIds[index][0]
        if (deliveryGroupId == id){
            msg += "\nWARNING: Delivery Group is aligned with CN Delivery Group: " + cnDeliveryGroupId;
        }
    }
    msg += "\n";
    $.ajax({
        url: "/api/tools/grouppackageversionvalidation/ENM/" + drop_name + "/" + id + "/",
        dataType: "json",
        success: function (json) {
            $.each(json, function (i, item) {
                if (item != "") {
                    msg =  msg + "" + item;
                }
            });
            proceed = confirm(msg);
            if (proceed) {
                $('body').addClass('loading');
                window.location = link;
                $("#link_" + id).hide();
            }
        },
        error: function (xhr, textStatus, errorThrown) {
            alert("Issue Checking Group: " + (errorThrown ? errorThrown : xhr.status));
        }
    });
}

function checkUserAction(msg, link, id) {
    var proceed = confirm(msg);
    if (proceed) {
        window.location = link;
        $('body').addClass('loading');
        $("#link_" + id).hide();
    }
}

function checkBoxAction(msg, id, value, checkboxType) {
    var proceed = confirm(msg);
    if (proceed) {
        $('body').addClass('loading');
        $('#'+checkboxType+'Form_'+id).submit();
    } else {
        $('#'+checkboxType+'_'+id).prop('checked', value == 'true');
    }
}

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
