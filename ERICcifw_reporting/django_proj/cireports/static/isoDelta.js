$(document).ready(function () {
    var product_names = [];
    var product_select_box = $('#products');
    var drop_names = [];
    var drops_select_box = $('#drops');
    var previous_drop_names = [];
    var previous_drops_select_box = $('#previous_drops');

    $('#products').change(function() {
        populate_drops($(this).val());
    });

    $('#drops').change(function() {
        populate_isos($(this).val(), 0);
    });

    $('#previous_drops').change(function() {
        populate_isos($(this).val(), 1);
    });

    $('#get_diff').click(get_iso_diff);

    var resultsHtml = document.getElementById("results").innerHTML

    if ($('input:hidden[name=isoVersion]').val() !== "None" && (typeof externalCall == 'undefined')){
        $("#iso").append('<option value="'+$('input:hidden[name=isoVersion]').val()+'">'+$('input:hidden[name=isoVersion]').val()+'</option>');
        $("#iso").each(function() { this.selected = (this.text == $('input:hidden[name=isoVersion]').val()); });
        $("#drops").append('<option value="'+$('input:hidden[name=drop]').val()+'">'+$('input:hidden[name=drop]').val()+'</option>');
        $("#drops").each(function() { this.selected = (this.text == $('input:hidden[name=drop]').val()); });
        if ($('input:hidden[name=preDrop]').val() !== "None"){
            $("#previous_drops").append('<option value="'+$('input:hidden[name=preDrop]').val()+'">'+$('input:hidden[name=preDrop]').val()+'</option>');
            $("#previous_drops").each(function() { this.selected = (this.text == $('input:hidden[name=preDrop]').val()); });
        }else{
            $("#previous_drops").append('<option value="'+$('input:hidden[name=drop]').val()+'">'+$('input:hidden[name=drop]').val()+'</option>');
            $("#previous_drops").each(function() { this.selected = (this.text == $('input:hidden[name=drop]').val()); });
        }
        $("#products").append('<option value="'+$('input:hidden[name=product]').val()+'">'+$('input:hidden[name=product]').val()+'</option>');
        $("#products").each(function() { this.selected = (this.text == $('input:hidden[name=product]').val()); });
        if ($('input:hidden[name=product]').val() !== "None"){
            $("#previous_iso").append('<option value="'+$('input:hidden[name=previousIsoVersion]').val()+'">'+$('input:hidden[name=previousIsoVersion]').val()+'</option>');
            $("#previous_iso").each(function() { this.selected = (this.text == $('input:hidden[name=previousIsoVersion]').val()); });
        }
        externalCall = 1;
        get_iso_diff();
        externalCall = 0;
        populate_products_select($('input:hidden[name=product]').val());
        var populateInitialVals = setInterval(initial_val_populator, 500);
    }else{
        externalCall = 0;
        populate_products_select($('input:hidden[name=product]').val());
    }

    function initial_val_populator(){
        if (resultsHtml !== document.getElementById("results").innerHTML) {

            $('#drops option[value="'+$('input:hidden[name=isoVersion]').val()+'"]').prop("selected", "selected");
            var promises1 = [];
            var promises2 = [];
            promises1.push(populate_isos($('input:hidden[name=drop]').val(), 0));
            $.when.apply($,promises1).then(function(json) {
                $('#iso option[value="'+$('input:hidden[name=isoVersion]').val()+'"]').prop("selected", "selected");
            });
            $('#previous_drops option[value="'+$('input:hidden[name=previousDrop]').val()+'"]').prop("selected", "selected");
            promises2.push(populate_isos($('input:hidden[name=previousDrop]').val(), 1));
            $.when.apply($,promises2).then(function(json) {
                $('#previous_iso option[value="'+$('input:hidden[name=previousIsoVer]').val()+'"]').prop("selected", "selected");
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
        $( "#accordionDeliveryGroup" ).accordion({
            active:false,
            collapsible: true,
            heightStyle: "content"
        });
        $('#accordionUpdated > .ui-widget-content').show();
        $('#accordionAdded > .ui-widget-content').show();
        $('#accordionObsoleted > .ui-widget-content').show();
        $('#accordionDeliveryGroup > .ui-widget-content').show();

        $('.expandResults').click(function() {
            $('#accordionUpdated > .ui-widget-content').show();
            $('#accordionAdded > .ui-widget-content').show();
            $('#accordionObsoleted > .ui-widget-content').show();
            $('#accordionDeliveryGroup > .ui-widget-content').show();
        });
        $('.collapseResults').click(function() {
            $('#accordionUpdated > .ui-widget-content').hide();
            $('#accordionAdded > .ui-widget-content').hide();
            $('#accordionObsoleted > .ui-widget-content').hide();
            $('#accordionDeliveryGroup > .ui-widget-content').hide();
        });
    }

    function populate_products_select(initialValue) {
        if (initialValue === "None") {
            initialValue = "ENM"
        }
        return $.ajax({
            url: "/metrics/allProducts/.json/",
            dataType: "json",
            success: function (json) {
                product_select_box.empty();
                $.each(json.Products, function (i, item) {
                    product_select_box.append('<option value="' + item.name + '" id="' + item.name + '">' + item.name + '</option>');
                    product_names.push(item.name);
                });
                product_select_box.prop("disabled", false);
                product_select_box.val(initialValue);
                product_select_box.change();
            },
            error: function (xhr, textStatus, errorThrown) {
                alert("Issue retrieving the product list: " + (errorThrown ? errorThrown : xhr.status));
            }
        });
    }

    function populate_drops(product){
        $('#previous_iso').empty();
        $('#iso').empty();
        drops_select_box.empty();
        previous_drops_select_box.empty();
        return $.ajax({
            url: "/dropsInProduct/.json/",
            dataType: "json",
            data: {"products": product},
            success: function (json) {
                drop_names = [];
                previous_drop_names = []
                $.each(json.Drops, function (i, item) {
                    item = item.split(':').pop()
                    drops_select_box.append('<option class="' + product + '" value="' + item + '" id="' + item + '">' + item + '</option>');
                    drop_names.push(item);
                    previous_drops_select_box.append('<option class="prev' + product + '" value="' + item + '" id="prev' + item + '">' + item + '</option>');
                    previous_drop_names.push(item);
                });
                populate_isos($('#drops').val(), 0);
                populate_isos($('#previous_drops').val(), 1);
            },
            error: function (xhr, textStatus, errorThrown) {
                alert("Issue retrieving drops from "+product+": " + (errorThrown ? errorThrown : xhr.status));
            }
        });
    }

    function populate_isos(drop, previous){
        product=$('#products').val();
        if (previous){
            var id = '#previous_iso';
        } else {
            var id = '#iso';
        }
        if ($('input:hidden[name=bom]').val() == "True") {
            getUrl = "/api/product/"+product+"/drop/"+drop+"/bom/versions/";
        }else {
            getUrl = "/api/product/"+product+"/drop/"+drop+"/iso/versions/";
        }
        $(id).empty()
        return $.ajax({
            url: getUrl,
            dataType: "json",
            success: function (json) {
                if (previous){
                    previous_iso_names = []
                } else {
                    iso_names = []
                }
                $.each(json, function (i,item) {
                    version = item.version
                    $(id).append('<option class="' + drop + '" value="' + version + '" id="' + version + '">' + version + '</option>');
                    if (previous){
                        previous_iso_names.push(version)
                    } else {
                        iso_names.push(version)
                    }
                });
            }
        });
    }

    function get_iso_diff() {
        $('body').addClass('loading');
        $('#get_diff').attr('disabled', 'disabled');
        if (externalCall) {
            queryData = {
                "externalCall": externalCall,
                "current": $('#iso').val(),
                "drop": $('#drops').val(),
                "product": $('#products').val()
            }
            if ($('#previous_iso').val() !== "None") {
                queryData["previous"] = $('#previous_iso').val();
            }
            if ($('#previous_drops').val() !== "None") {
                queryData["preDrop"] = $('#previous_drops').val();
            }
        }else{
            queryData = {
                "externalCall": externalCall,
                "current": $('#iso').val(),
                "previous": $('#previous_iso').val(),
                "drop": $('#drops').val(),
                "preDrop": $('#previous_drops').val(),
                "product": $('#products').val()
            }
        }
        if ($('input:hidden[name=bom]').val() == "True") {
            getUrl = "/compareBOMs/";
        }else {
            getUrl = "/compareISOs/";
        }
        $.ajax({
            type: 'GET',
            url: getUrl,
            dataType: "html",
            data: queryData,
            success: function (html) {
                $('div#results').html(html);
                $('#get_diff').attr('disabled', false);
                runAccordionScript();
                $('body').removeClass('loading');
            },
            error: function (xhr, textStatus, errorThrown) {
                if (xhr.status !== 0) {
                    alert("Unable to load Results table: " + (errorThrown ? errorThrown : xhr.status));
                    $('body').removeClass('loading');
                }
            }
        });
    }
});

