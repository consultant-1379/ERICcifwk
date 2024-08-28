$(document).ready(function() {
    let deliveryGroupNumber = $('#hidden_dg_div').html();
    let dropNumber = $('#hidden_drop_div').html();
    let ps_select_box = $('#cn_ps_ver');
    let ps_select_container = $('.dg_confirm_ps_version');
    let has_ps_ver_radioBtn = $('#has_cn_ps_ver');
    let no_ps_ver_radioBtn = $('#no_cn_ps_ver')
    let dg_confirm_btn = $('#dg_confirm_btn');
    let ps_items = [""];

    populate_ps_select();
    has_ps_ver_radioBtn.click(hasCNProductSetVersionCheck);
    no_ps_ver_radioBtn.click(hasCNProductSetVersionCheck);
    dg_confirm_btn.click(deliverCNDeliveryGroup);

    function populate_ps_select() {
        $.ajax({
            type: "GET",
            url: "/api/cenm/drop/" + dropNumber + "/productSetVersions/",
            success: function(result) {
                $.each(result["ProductSetVersion"], function(i, item) {
                    console.log(item);
                    ps_select_box.append('<option value="' + item.product_set_version + '" id="' + item.product_set_version + '">' + item.product_set_version + '</option>');
                    ps_items.push(item.product_set_version);
                });
                ps_select_box.autocomplete({
                    source: ps_items
                });
            },
            error: function(xhr, textStatus, errorThrown) {
                alert("Issue retrieving the list of cn product set versions: " + xhr.responseText);
            }
        })
    }

    function hasCNProductSetVersionCheck() {
        if (has_ps_ver_radioBtn.is(':checked')) {
            ps_select_container.show();
        } else {
            ps_select_container.hide();
        }
        if(no_ps_ver_radioBtn.is(':checked')){
            ps_select_box.val("");
        }
    }

    function deliverCNDeliveryGroup() {
        // To-Do combine update dg delivery rest call with the rest call for updating cn ps
        let proceed = "";
        let productSetVersion = "";
        if (has_ps_ver_radioBtn.val()) {
            productSetVersion = ps_select_box.val().trim();
            if(productSetVersion.length == 0 && has_ps_ver_radioBtn.is(':checked')) {
                alert("Product set version can't be empty.");
                return;
            }
            proceed = confirm("Do you really want to deliver delivery group " + deliveryGroupNumber + " with product set version " + ps_select_box.val() + " ? ");
        } else {
            productSetVersion = false;
            proceed = confirm("Do you really want to deliver delivery group " + deliveryGroupId + " without updating product set version? ");
        }
        if(proceed) {
            $('body').addClass('loading');
            dg_confirm_btn.attr('disabled', true);
            $.ajax({
                type: 'POST',
                url: '/api/cloudNative/deliveryQueue/deliverCNDeliveryGroup/',
                headers: { "X-CSRFToken": getCookie("csrftoken") },
                dataType: 'json',
                data: {
                    "deliveryGroupNumber": deliveryGroupNumber,
                    "productSetVersion": productSetVersion
                },
                success: function(result) {
                    let productName = "Cloud Native ENM"
                    if(result == "SUCCESS") {
                        alert("Group Successfully delivered. ");
                        window.location = "/cloudNative/" + productName + "/deliveryQueue/" + dropNumber + "/" + deliveryGroupNumber + "?section=delivered";
                    }
                    $('body').removeClass('loading');
                },
                error: function (xhr, textStatus, errorThrown) {
                    let productName = "Cloud Native ENM"
                    alert("Issue delivering delivery group: " + xhr.responseText);
                    window.location = "/cloudNative/" + productName + "/deliveryQueue/" + dropNumber + "/" + deliveryGroupNumber + "?section=queued";
                    $('body').removeClass('loading');
                    dg_confirm_btn.attr('disabled', false);
                }
            });
            dg_confirm_btn.attr('disabled', false);
        }
    }
})

function getCookie(c_name) {
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