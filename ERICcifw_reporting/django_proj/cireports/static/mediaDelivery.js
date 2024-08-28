$(document).ready(function() {
    var product_list = [];
    var drop_select_box = $('#drop');
    var product_set = $('#product_set_input').val();
    populate_drop_select();
    var optionNum = 0;

    function populate_drop_select() {
        var frozen = 0;
        var closed = 0;
        $.ajax({
            url: "/api/productSet/" + product_set + "/activeDrops/",
            dataType: "json",
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
                drop_select_box.val(drop_items[0]);
                buildMappingContenttable();
            },

            error: function(xhr, textStatus, errorThrown) {
                alert("Issue retrieving the list of Drops: " + (errorThrown ? errorThrown : xhr.status));
            }
        });
        $('#drop').change(function() {
           buildMappingContenttable();
        });

    }

    function buildMappingContenttable() {
        $(".deploy_options").empty();
        optionNum = 0;
        $.ajax({
            type: 'GET',
            url: "/api/productSet/" + product_set + "/drop/" + $('#drop').val().split(':').pop() + "/mappings/",
            dataType: 'json',
            cache: false,
            success: function(json) {
                 $.each(json.ps_media_drop_products, function(i, item) {
                      if (item.mapping == true) {
                             $(".deploy_options").append("<div><input id='option-" + optionNum + "' type='checkbox' class='mapped' name='product' value='" + item.product + "' checked><label for='option-" + optionNum + "'><span><span></span></span>" + item.product + "</label></div>");
                       } else {
                             $(".deploy_options").append("<div><input id='option-" + optionNum + "' type='checkbox' class='mapped' name='product' value='" + item.product + "' ><label for='option-" + optionNum+ "'><span><span></span></span>" + item.product + "</label></div>");
                       }
                       optionNum = optionNum + 1;
                  });
           },
           error: function(xhr, textStatus, errorThrown) {
               alert("Issue retrieving the list of Products for Drop: " + (errorThrown ? errorThrown : xhr.status));
           }
        });
    }

    function validateEmail(email) {
        var re = /^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
        return re.test(String(email).toLowerCase());
    }

    $('#add_to_psdrop').click(add_psdrop_stage);
    function add_psdrop_stage() {
        $('#add_to_psdrop').attr('disabled', true);
        var dropData = $('#drop').val();
        var product = $('#product_input').val();
        var media_artifact = $('#media_artifact_input').val();
        var version = $('#media_artifact_version_input').val();
        var email = $('#email_input').val();

        if (!validateEmail(email)) {
            window.alert("Please provide a valid email address.");
            $('#add_to_psdrop').attr('disabled', false);
            return
        }
        var signum = $('#signum_input').val();

        if (dropData.indexOf('Closed') > -1) {
            if (group_info) {
                window.alert("This Drop is Closed. You cannot Edit this Group for a Closed Drop");
            } else {
                window.alert(dropData);
            }
            $('#add_to_psdrop').attr('disabled', false);
            return
        }
        $(".mapped:checked").each(function() {
             product_list.push($(this).val());
        });
        var form_data = {
            'drop': $('#drop').val().split(':').pop(),
            'product': product,
            'mediaArtifact': media_artifact,
            'version':version,
            'productSet': product_set,
            'signum': signum,
            'email': email,
            'deployProductList': product_list.toString(),
        };

        var msg = "Please Confirm Media Delivery. \nAuto Deployment Mappings selected:\n" + product_list.join('\n') + "\nNote: you must provide correct mappings required for an ENM Auto Deployment.";
        if (product_list.length == 0) {
            msg = "Please Confirm Media Delivery. \nWarning: No Auto Deployment Mappings were selected, default mappings will be used for an ENM Auto Deployment.";
        }
        proceed = confirm(msg);
        if (proceed) {
            $('body').addClass('loading');
            $('#add_to_psdrop').attr('disabled', true);
            $.ajax({
                type: "POST",
                url: "/mediaDeliveryToDrop/",
                data: form_data,
                success: function() {
                    window.location.href = "/ENM/dropMedia/" + $('#drop').val().split(':').pop();
                },
                error: function(xhr, textStatus, errorThrown) {
                    $('body').removeClass('loading');
                    alert("Issue adding group: " + (errorThrown ? errorThrown : xhr.status));
                    $('#add_to_psdrop').attr('disabled', false);
                }
            });
        } else {
            $('#add_to_psdrop').attr('disabled', false);
            product_list = [];
        }
    }

});
