$(document).ready(function () {

    var product_names = [];
    var product_select_box = $("#products");
    var drop_names = [];
    var drops_select_box = $("#drops");
    var previous_drop_names = [];
    var previous_drops_select_box = $("#previous_drops");

    $("#products").change(function() {
        populate_drops($(this).val());
    });

    $("#drops").change(function() {
        populate_ps_versions($(this).val(), 0);
    });

    $("#previous_drops").change(function() {
        populate_ps_versions($(this).val(), 1);
    });

    $("#get_diff").click(get_ps_diff);

    var resultsHtml = document.getElementById("previous_drops").innerHTML;


    if ($("input:hidden[name=productSetVersion]").val() !== "None" && (typeof externalCall == "undefined")){
    $("#product_set").append("<option value='"+$("input:hidden[name=productSetVersion]").val()+"'>"+$("input:hidden[name=productSetVersion]").val()+"</option>");
    $("#product_set").each(function() { this.selected = (this.text == $("input:hidden[name=productSetVersion]").val()); });
    $("#drops").append("<option value='"+$("input:hidden[name=drop]").val()+"'>"+$("input:hidden[name=drop]").val()+"</option>");
    $("#drops").each(function() { this.selected = (this.text == $("input:hidden[name=drop]").val()); });
    $("#products").append("<option value='"+$("input:hidden[name=product]").val()+"'>"+$("input:hidden[name=product]").val()+"</option>");
    $("#products").each(function() { this.selected = (this.text == $("input:hidden[name=product]").val()); });
    if ($("input:hidden[name=previous_product_set]").val() !== "None" && (typeof externalCall == "undefined")){
        $("#previous_product_set").append("<option value='"+$("input:hidden[name=previous_product_set]").val()+"'>"+$("input:hidden[name=previous_product_set]").val()+"</option>");
        $("#previous_product_set").each(function() { this.selected = (this.text == $("input:hidden[name=previous_product_set]").val()); });
        }
        externalCall = 1;
        get_ps_diff();
        externalCall = 0;
        populate_products_select();
        var populateInitialVals = setInterval(initial_val_populator, 1000);
    }else{
        externalCall = 0;
        populate_products_select();
    }

    function initial_val_populator(){
        if (resultsHtml !== document.getElementById("previous_drops").innerHTML) {

            $("#drops option[value='"+$("input:hidden[name=drop]").val()+"']").prop("selected", "selected");
            var promises1 = [];
            var promises2 = [];
            promises1.push(populate_ps_versions($("input:hidden[name=drop]").val(), 0));
            $.when.apply($,promises1).then(function(json) {
                $("#product_set option[value='"+$("input:hidden[name=productSetVersion]").val()+"']").prop("selected", "selected");
            });
            $("#previous_drops option[value='"+$("input:hidden[name=previousDrop]").val()+"']").prop("selected", "selected");
            promises2.push(populate_ps_versions($("input:hidden[name=previousDrop]").val(), 1));
            $.when.apply($,promises2).then(function(json) {
                $("#previous_product_set option[value='"+$("input:hidden[name=previousPS]").val()+"']").prop("selected", "selected");
            });
            clearInterval(populateInitialVals);
        }
    }

    function runAccordionScript() {
        $( "#accordionUpdated" ).accordion({
            active:true,
            collapsible: true,
            heightStyle: "content"
        });
        $( "#accordionAdded" ).accordion({
            active:false,
            collapsible: true,
            heightStyle: "content"
        });
        $( "#accordionObsoleted" ).accordion({
            active:false,
            collapsible: true,
            heightStyle: "content"
        });
        $("#accordionUpdated > .ui-widget-content").show();
        $("#accordionAdded > .ui-widget-content").show();
        $("#accordionObsoleted > .ui-widget-content").show();

        $(".expandResults").click(function() {
            $("#accordionUpdated > .ui-widget-content").show();
            $("#accordionAdded > .ui-widget-content").show();
            $("#accordionObsoleted > .ui-widget-content").show();
        });
        $(".collapseResults").click(function() {
            $("#accordionUpdated > .ui-widget-content").hide();
            $("#accordionAdded > .ui-widget-content").hide();
            $("#accordionObsoleted > .ui-widget-content").hide();
        });
    }

    function populate_products_select() {
        return $.ajax({
            url: "/api/productSet/list/",
            dataType: "json",
            success: function (json) {
                product_select_box.empty();
                $.each(json.productSets, function (i, item) {
                    product_select_box.append("<option value='" + item.product + "' id='" + item.product + "'>" + item.name + "</option>");
                    product_names.push(item.name);
                });
                product_select_box.prop("disabled", false);
                product_select_box.val("ENM");
                product_select_box.change();
            },
            error: function (xhr, textStatus, errorThrown) {
                alert("Issue retrieving the product list: " + (errorThrown ? errorThrown : xhr.status));
            }
        });
    }

    function populate_drops(product){
        $("#previous_product_set").empty();
        $("#product_set").empty();
        drops_select_box.empty();
        previous_drops_select_box.empty();
        return $.ajax({
            url: "/dropsInProduct/.json/",
            dataType: "json",
            data: {"products": product},
            success: function (json) {
                drop_names = [];
                previous_drop_names = [];
                $.each(json.Drops, function (i, item) {
                    item = item.split(":").pop();
                    drops_select_box.append("<option class='" + product + "' value='" + item + "' id='" + item + "'>" + item + "</option>");
                    drop_names.push(item);
                    previous_drops_select_box.append("<option class='prev" + product + "' value='" + item + "' id='prev" + item + "'>" + item + "</option>");
                    previous_drop_names.push(item);
                });
                populate_ps_versions($("#drops").val(), 0);
                populate_ps_versions($("#previous_drops").val(), 1);
            },
            error: function (xhr, textStatus, errorThrown) {
                alert("Issue retrieving drops from "+product+": " + (errorThrown ? errorThrown : xhr.status));
            }
        });
    }

    function populate_ps_versions(drop, previous){
        product=$("#products").val();
        if (previous){
            var id = "#previous_product_set";
        } else {
            var id = "#product_set";
        }
        getUrl = "/api/productSet/"+product+"/drop/"+drop+"/versions/";

        $(id).empty()
        return $.ajax({
            url: getUrl,
            dataType: "json",
            success: function (json) {
                if (previous){
                    previous_product_set_names = []
                } else {
                    product_set_names = []
                }
                $.each(json, function (i,item) {
                    version = item.version
                    $(id).append("<option class='" + drop + "' value='" + version + "' id='" + version + "'>" + version + "</option>");
                    if (previous){
                        previous_product_set_names.push(version)
                    } else {
                        product_set_names.push(version)
                    }
                });
            }
        });
    }

    function get_ps_diff() {
        $("body").addClass("loading");
        $("#get_diff").attr("disabled", "disabled");
        if (externalCall && $("#previous_product_set").val()) {
            queryData = {
                "previous": $("#previous_product_set").val(),
                "externalCall": externalCall,
                "current": $("#product_set").val(),
                "drop": $("#drops").val(),
                "product": $("#products").val()
            }
        }else if (externalCall) {
            queryData = {
                "externalCall": externalCall,
                "current": $("#product_set").val(),
                "drop": $("#drops").val(),
                "product": $("#products").val()
            }
        }else{
            queryData = {
                "externalCall": externalCall,
                "current": $("#product_set").val(),
                "previous": $("#previous_product_set").val(),
                "drop": $("#drops").val(),
                "preDrop": $("#previous_drops").val(),
                "product": $("#products").val()
            }
        }
        getUrl = "/compareProductSets/";
        $.ajax({
            type: "GET",
            url: getUrl,
            dataType: "html",
            data: queryData,
            success: function (html) {
                $("div#results").html(html);
                $("#get_diff").attr("disabled", false);
                runAccordionScript();
                $("body").removeClass("loading");
            },
            error: function (xhr, textStatus, errorThrown) {
                if (xhr.status !== 0) {
                    alert("Unable to load Results table: " + (errorThrown ? errorThrown : xhr.status));
                    $("body").removeClass("loading");
                }
            }
        });
    }
});

