$(document).ready(function() {
    $body = $("body");
    var error_message = $("#error_message");
    error_message.hide();

    function set_error_message(input) {
        error_message.html(input);
        error_message.show();
    }

    function userAction(link, value) {
        $body.addClass('loading');

        $.ajax({
            url: link + value + '/',
            success: function() {
                window.location = link + value + '/';
            },
            error: function(jqXHR, status, er) {
                if (jqXHR.status === 404) {
                    set_error_message("Error: Not Found " + value);
                }
                $body.removeClass('loading');
            }
        });
    }

    drop_select_box = $('div.dropdown-content');
    populate_drop_select();

    function populate_drop_select() {
        $.ajax({
            url: "/dropsInProduct/.json/",
            dataType: "json",
            data: {
                "products": "ENM"
            },
            success: function(json) {
                var drop_items = [];
                var count = 0;
                $.each(json.Drops, function(i, item) {
                    if (count == 10) {
                        return false;
                    }
                    var item = String(item).split(':').pop();
                    var link = '/ENM/queue/' + item + '/';
                    drop_select_box.append('<li><a href="' + link + '">' + item + '</a></li>');
                    drop_items.push(item);
                    count++;
                });
            },

            error: function(xhr, textStatus, errorThrown) {
                alert("Issue retrieving the list of Drops: " + (errorThrown ? errorThrown : xhr.status));
            }
        });
    }

    function add_drop_selector() {
        $("#empty_drop_form").append("<div style='float: right;'> <input id='drops' style='margin-top:5px; width: 170px;' ><input class='submitButton' type='button' id='go_to_queue'></div>");
        drop_search_box = $('#drops');
        return populate_drops();
    }
    add_drop_selector();

    function populate_drops() {
        return $.ajax({
            url: "/dropsInProduct/.json/",
            dataType: "json",
            data: {
                "products": "ENM"
            },
            success: function(json) {
                drop_names = [""];
                $.each(json.Drops, function(i, item) {
                    var item = String(item).split(':').pop();
                    drop_names.push(item);
                });
                drop_search_box.autocomplete({
                    source: drop_names
                });
            },
            error: function(xhr, textStatus, errorThrown) {
                alert("Issue retrieving the All ENM Drops list: " + (errorThrown ? errorThrown : xhr.status));
            }
        });
    }

    cn_drop_select_box = $('div.cn-dropdown-content');
    populate_cnDrop_select();

    function populate_cnDrop_select() {
        let cnProductName = "Cloud Native ENM"
        $.ajax({
            url: "/api/cloudNative/getCNDropByProductName/" + cnProductName + "/",
            dataType: "json",
            success: function(json) {
                var drop_items = [];
                var count = 0
                $.each(json, function(i, item) {
                    if (count == 10) {
                        return false;
                    }
                    var link = '/cloudNative/Cloud Native ENM/deliveryQueue/' + item + '/';
                    cn_drop_select_box.append('<li><a href="' + link + '">' + item + '</a></li>');
                    drop_items.push(item);
                    count++;
                });
            },

            error: function(xhr, textStatus, errorThrown) {
                alert("Issue retrieving the list of cn Drops: " + (errorThrown ? errorThrown : xhr.status));
            }
        });
    }

    function add_cnDrop_selector() {
        $("#empty_cn_drop_form").append("<div style='float: right;'> <input id='cn_drops' style='margin-top:5px; width: 170px;' ><input class='submitButton' type='button' id='go_to_cn_queue'></div>");
        cn_drop_search_box = $('#cn_drops');
        return populate_cnDrops();
    }

    add_cnDrop_selector();

    function populate_cnDrops() {
        let cnProductName = "Cloud Native ENM"
        return $.ajax({
            url: "/api/cloudNative/getCNDropByProductName/" + cnProductName + "/",
            dataType: "json",
            success: function(json) {
                let drop_names = [""];
                $.each(json, function(i, item) {
                    drop_names.push(item);
                });
                cn_drop_search_box.autocomplete({
                    source: drop_names
                });
            },
            error: function(xhr, textStatus, errorThrown) {
                alert("Issue retrieving the All cENM Drops list: " + (errorThrown ? errorThrown : xhr.status));
            }
        });
    }

    product_select_box = $('div.products-dropdown-content');
    populate_product_select();

    function populate_product_select() {
        $.ajax({
            url: "/metrics/allProducts/.json/",
            dataType: "json",
            success: function(json) {
                var product_items = [];
                $.each(json.Products, function(i, item) {
                    var name = item['name'];
                    var link = '/' + name + '/packages/';
                    product_select_box.append('<li><a onclick=$body.addClass("loading"); href="' + link + '" title="Packages & Testware List for ' + name + '">' + name + '</a></li>');
                    product_items.push(item);
                });
            },

            error: function(xhr, textStatus, errorThrown) {
                alert("Issue retrieving the list of Products: " + (errorThrown ? errorThrown : xhr.status));
            }
        });
    }
    add_package_selector();

    function populate_packages() {
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
            },
            error: function(xhr, textStatus, errorThrown) {
                alert("Issue retrieving the All Package list: " + (errorThrown ? errorThrown : xhr.status));
            }
        });
    }

    function add_package_selector() {
        $("#empty_form").append("<div><input id='packages' style='margin-top:4px; width: 150px;' ><input class='submitButton' type='button' id='go_to_artifact'></div>");
        packages_select_box = $('#packages');
        return populate_packages();
    }
    add_deployment_selector();

    function populate_deployments() {
        return $.ajax({
            url: "/api/deployment/clusters/",
            dataType: "json",
            success: function(json) {
                deployment_ids = [""];
                $.each(json, function(i, item) {
                    deployment_ids.push(String(item.id));
                });
                deployment_box.autocomplete({
                    source: deployment_ids
                });
            },
            error: function(xhr, textStatus, errorThrown) {
                alert("Issue retrieving the All deployment IDs list: " + (errorThrown ? errorThrown : xhr.status));
            }
        });
    }

    function add_deployment_selector() {
        $("#empty_deployment_form").append("<div><label for='deployment'>ID </label> <input id='deployment_ids' style='width: 230px;' ><input class='submitButton' type='button' id='go_to_deployment'></div>");
        deployment_box = $('#deployment_ids');
        return populate_deployments();
    }
    $('#go_to_artifact').click(function() {
        userAction('/prototype/packages/', $('#packages').val());
    });
    $('#go_to_artifact').keyup(function(e) {
        if (e.keyCode == 13) {
            userAction('/prototype/packages/', $('#packages').val());
        }
    });
    $('#packages').keyup(function(e) {
        if (e.keyCode == 13) {
            userAction('/prototype/packages/', $('#packages').val());
        }
    });
    $('#go_to_queue').click(function() {
        userAction('/ENM/queue/', $('#drops').val());
    });
    $('#go_to_queue').keyup(function(e) {
        if (e.keyCode == 13) {
            userAction('/ENM/queue/', $('#drops').val());
        }
    });
    $('#go_to_cn_queue').click(function() {
        userAction('/cloudNative/Cloud Native ENM/deliveryQueue/', $('#cn_drops').val());
    });
    $('#go_to_cn_queue').keyup(function(e) {
        if (e.keyCode == 13) {
            userAction('/cloudNative/Cloud Native ENM/deliveryQueue/', $('#cn_drops').val());
        }
    });

    $('#drops').keyup(function(e) {
        if (e.keyCode == 13) {
            userAction('/ENM/queue/', $('#drops').val());
        }
    });
    $('#go_to_deployment').click(function() {
        userAction('/dmt/clusters/', $('#deployment_ids').val());
    });
    $('#go_to_deployment').keyup(function(e) {
        if (e.keyCode == 13) {
            userAction('/dmt/clusters/', $('#deployment_ids').val());
        }
    });
    $('#deployment_ids').keyup(function(e) {
        if (e.keyCode == 13) {
            userAction('/dmt/clusters/', $('#deployment_ids').val());
        }
    });
});
