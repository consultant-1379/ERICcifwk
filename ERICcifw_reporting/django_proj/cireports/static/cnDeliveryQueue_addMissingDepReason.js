$(document).ready(function() {
    let dropNumber = $('#hidden_drop_div').html();
    let deliveryGroupNumber = $('#hidden_dg_div').html();
    let missingDepBtn = $('#edit_queue');
    missingDepBtn.click(updateMissingDepReason);

    function updateMissingDepReason() {
        let reason = $('#add_missing_dep_comment').val();
        let proceed = confirm("Are you sure to flag missing dependencies for delivery group " + deliveryGroupNumber + "?" + "Reason: " + reason);
        let params = {
            "deliveryGroupNumber": deliveryGroupNumber,
            "missingDepValue": true,
            "missingDepReason": reason
        };
        if (proceed) {
            $.ajax({
                type: "PUT",
                url: "/api/cloudNative/deliveryQueue/updateMissingDependencies/" + deliveryGroupNumber + "/",
                dataType: "json",
                headers: { "X-CSRFToken": getCookie("csrftoken") },
                data: JSON.stringify(params),
                success: function(result) {
                    window.location.href = "/cloudNative/Cloud Native ENM/deliveryQueue/" + dropNumber + "/" + deliveryGroupNumber + "/?section=queued";
                },
                error: function(xhr, textStatus, errorThrown) {
                    alert("Issue updating missing dependencies reason for CN Delivery Group: " + xhr.responseText);
                }
            });
        }
    }
});

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