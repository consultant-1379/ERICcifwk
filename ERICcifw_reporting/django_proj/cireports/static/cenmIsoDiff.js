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
        populate_productSets($(this).val(), 0);
    });

    $('#previous_drops').change(function() {
        populate_productSets($(this).val(), 1);
    });

    $('#get_diff').click(get_productSet_diff);

    // solve the loop problems??? previously it loops one more time
    if ($('input:hidden[name=productSetVersion]').val() !== "None"){
        $("#productSet").append('<option value="'+$('input:hidden[name=productSetVersion]').val()+'">'+$('input:hidden[name=productSetVersion]').val()+'</option>');
        $("#productSet").each(function() { this.selected = (this.text == $('input:hidden[name=productSetVersion]').val()); });
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
            $("#previous_productSet").append('<option value="'+$('input:hidden[name=previousProductSetVersion]').val()+'">'+$('input:hidden[name=previousProductSetVersion]').val()+'</option>');
            $("#previous_productSet").each(function() { this.selected = (this.text == $('input:hidden[name=previousProductSetVersion]').val()); });
        }
        populate_products_select($('input:hidden[name=product]').val());
    } else {
        populate_products_select($('input:hidden[name=product]').val());
    }

    function runAccordionScript() {
        $( "#accordionCsarChanges" ).accordion({
            active:false,
            collapsible: true,
            heightStyle: "content"
        });

        $( "#accordionIntegrationChartChanges" ).accordion({
            active:false,
            collapsible: true,
            heightStyle: "content"
        });

        $( "#accordionIntegrationChartChanges" ).accordion({
            active:false,
            collapsible: true,
            heightStyle: "content"
        });

        $( "#accordionImageChanges" ).accordion({
            active:false,
            collapsible: true,
            heightStyle: "content"
        });
    }

    function populate_products_select(initialValue) {
        if (initialValue === "None") {
            initialValue = "CENM"
        }
        product_select_box.prop("disabled", false);
        product_select_box.val(initialValue);
        product_select_box.change();
    }

    function populate_drops(product){
        $('#previous_productSet').empty();
        $('#productSet').empty();
        drops_select_box.empty();
        previous_drops_select_box.empty();
        return $.ajax({
            url: "api/cloudNative/dropsInProduct/.json/",
            dataType: "json",
            success: function (json) {
                drop_names = [];
                previous_drop_names = []
                $.each(json, function (i, item) {
                    item = item.drop_version
                    drops_select_box.append('<option class="' + "CENM" + '" value="' + item + '" id="' + item + '">' + item + '</option>');
                    drop_names.push(item);
                    previous_drops_select_box.append('<option class="prev' + "CENM" + '" value="' + item + '" id="prev' + item + '">' + item + '</option>');
                    previous_drop_names.push(item);
                });
                populate_productSets($('#drops').val(), 0);
                populate_productSets($('#previous_drops').val(), 1);
            },
            error: function (xhr, textStatus, errorThrown) {
                alert("Issue retrieving drops from "+product+": " + (errorThrown ? errorThrown : xhr.status));
            }
        });
    }

    function populate_productSets(drop, previous){
        product=$('#products').val();
        if (previous){
            var id = '#previous_productSet';
        } else {
            var id = '#productSet';
        }
        getUrl = "api/cenm/drop/" + drop + "/productSetVersions/";
        $(id).empty()
        return $.ajax({
            url: getUrl,
            dataType: "json",
            success: function (json) {
                console.log(json);
                if (previous){
                    previous_productSet_names = []
                } else {
                    productSet_names = []
                }
                $.each(json.ProductSetVersion, function (i,item) {
                    version = item.product_set_version
                    $(id).append('<option class="' + drop + '" value="' + version + '" id="' + version + '">' + version + '</option>');
                    if (previous){
                        previous_productSet_names.push(version)
                    } else {
                        productSet_names.push(version)
                    }
                });
            }
        });
    }

    function get_productSet_diff() {
        $('body').addClass('loading');
        $('#get_diff').attr('disabled', 'disabled');
        queryData = {
            "current": $('#productSet').val(),
            "previous": $('#previous_productSet').val(),
            "drop": $('#drops').val(),
            "preDrop": $('#previous_drops').val(),
        }
        getUrl = "/compareCENMISOsResult/";
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

