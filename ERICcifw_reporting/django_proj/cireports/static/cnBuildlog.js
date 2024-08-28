var buildLogId = "";
var commentId = "";
var beforeEdit = "";
$(document).ready(function () {
    $("#cnbuildlog-dialog").dialog({
        closeOnEscape: false,
        modal: true,
        width: "500",
        height: "270",
        resizable: true,
        autoOpen: false,
        open: function (event, ui) {
            $(".ui-dialog-titlebar-close").hide();
        }
    });

    $("#cnbuildlog-comment-edit-dialog").dialog({
        closeOnEscape: false,
        modal: true,
        width: "500",
        height: "270",
        resizable: true,
        autoOpen: false,
        open: function (event, ui) {
            $(".ui-dialog-titlebar-close").hide();
        }
    });

    $("#cnbuildlog-jira-edit-dialog").dialog({
        closeOnEscape: false,
        modal: true,
        width: "500",
        height: "270",
        resizable: true,
        autoOpen: false,
        open: function (event, ui) {
            $(".ui-dialog-titlebar-close").hide();
        }
    });

    $(".cancel").click(function (e) {
        $("#cnbuildlog-dialog").dialog("close");
        $("#cnbuildlog-comment-edit-dialog").dialog("close");
        $("#cnbuildlog-jira-edit-dialog").dialog("close");
    });
});

function displayPopup(id) {
    buildLogId = id;
    $("#cnbuildlog-dialog").dialog("open");
}

function displayEditPopup(id,value) {
    commentId = id;
    beforeEdit = value;
    $('#cnbuildlog_edit_comment').val(value);
    $("#cnbuildlog-comment-edit-dialog").dialog("open");
}

function addCommentData() {
    const commentMessage = $('#cnbuildlog_comment').val();
    const jiraMessage = $('#cnbuildlog_jira').val();
    let proceed = true;
    if (commentMessage == "" && jiraMessage == "") {
        proceed = false;
    }
    let params = {
        "buildLogId": buildLogId,
        "comment": commentMessage,
        "jira": jiraMessage
    }
    if (proceed) {
        $.ajax({
            type: 'POST',
            url: "/api/cloudNative/addCNBuildLogComment/",
            headers: { "X-CSRFToken": getCookie("csrftoken") },
            dataType: "json",
            data: JSON.stringify(params),
            success: function (json) {
                $('body').addClass('loading');
                alert("Comment Added Successfully");
                window.location.reload();
            },
            error: function (xhr, textStatus, errorThrown) {
                alert("Failed to add comment " + xhr.responseText);
            }
        })
    }
    $("#cnbuildlog-dialog").dialog("close");
}

function deleteEntry(cnBuildlogId) {
    let proceed = "";
    proceed = confirm("Are you sure you want to delete this buildlog entry?");
    if(proceed){
        let params = {
            "build_log_id": cnBuildlogId,
        }
        $.ajax({
            type: 'PATCH',
            url: "/api/cloudNative/deleteCNBuildLog/",
            headers: { "X-CSRFToken": getCookie("csrftoken") },
            data: JSON.stringify(params),
            success: function (json) {
                $('body').addClass('loading');
                alert("Buildlog entry deleted successfully");
                window.location.reload();
            },
            error: function (xhr, textStatus, errorThrown) {
                alert("Failed to delete buildlog entry " + xhr.responseText);
            }
        })
    }
}

function editCommentData() {
    const commentMessage = $('#cnbuildlog_edit_comment').val();
    let proceed = beforeEdit !== commentMessage && commentMessage !== "";
    let params = {
        "commentId": commentId,
        "editComment": commentMessage,
    }
    if (proceed) {
        $.ajax({
            type: 'POST',
            url: "/api/cloudNative/editCNBuildLogComment/",
            headers: { "X-CSRFToken": getCookie("csrftoken") },
            dataType: "json",
            data: JSON.stringify(params),
            success: function (json) {
                $('body').addClass('loading');
                alert("Comment edited Successfully");
                window.location.reload();
            },
            error: function (xhr, textStatus, errorThrown) {
                alert("Failed to edit comment " + xhr.responseText);
            }
        })
    } else {
        alert("No edition has been made: No changes detected!");
    }
    $("#cnbuildlog-comment-edit-dialog").dialog("close");
}

function deleteCommentData() {
    let params = {
        "commentId": commentId,
    }
    $.ajax({
        type: 'DELETE',
        url: "/api/cloudNative/deleteCNBuildLogComment/",
        headers: { "X-CSRFToken": getCookie("csrftoken") },
        dataType: "json",
        data: JSON.stringify(params),
        success: function (json) {
            $('body').addClass('loading');
            alert("Comment deleted Successfully");
            window.location.reload();
        },
        error: function (xhr, textStatus, errorThrown) {
            alert("Failed to delete comment " + xhr.responseText);
        }
    })
    $("#cnbuildlog-comment-edit-dialog").dialog("close");
}

function deleteJiraData(commentId) {
    let proceed = "";
    proceed = confirm("Are you sure you want to delete this Jira Issue?");
    if(proceed){
        let params = {
            "commentId": commentId,
        }
        $.ajax({
            type: 'DELETE',
            url: "/api/cloudNative/deleteCNBuildLogJira/",
            headers: { "X-CSRFToken": getCookie("csrftoken") },
            dataType: "json",
            data: JSON.stringify(params),
            success: function (json) {
                $('body').addClass('loading');
                alert("Jira deleted Successfully");
                window.location.reload();
            },
            error: function (xhr, textStatus, errorThrown) {
                alert("Failed to delete jira " + xhr.responseText);
            }
        })
    }
    $("#cnbuildlog-jira-edit-dialog").dialog("close");
}

function getSearchData() {
    const dropValue = document.getElementById("search").value;
    location.href = "/cloudnative/buildlog/" + dropValue + "/";
}

function getCookie(c_name) {
    if (document.cookie.length > 0) {
        c_start = document.cookie.indexOf(c_name + "=");
        if (c_start != -1) {
            c_start = c_start + c_name.length + 1;
            c_end = document.cookie.indexOf(";", c_start);
            if (c_end == -1) c_end = document.cookie.length;
            return unescape(document.cookie.substring(c_start, c_end));
        }
    }
    return "";
}