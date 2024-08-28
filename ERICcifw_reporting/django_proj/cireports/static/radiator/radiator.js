
// maroon, red, amber, green
//var colors = ["#aa2222", "#e32119", "#fabb00", "#89ba17" ,"#ffffff"];
//var colors = ["#7b0663", "#e32119", "#90b9b6", "#00625f"];
var colors = ["#00625f", "#90b9b6", "#e32119", "#7b0663"];

function timeAgo(time, local) {
    (!local) && (local = Date.now());
    if (typeof time !== 'number' || typeof local !== 'number') {
        return;
    }

    var offset = Math.abs((local - time)/1000),
        span = [],
        MINUTE = 60,
        HOUR = 3600,
        DAY = 86400,
        WEEK = 604800,
        MONTH = 2629744,
        YEAR = 31556926,
        DECADE = 315569260;

    if (offset <= MINUTE) span = [ '', 'moments' ];
    else if (offset < (MINUTE * 60)) span = [ Math.round(Math.abs(offset / MINUTE)), 'min' ];
    else if (offset < (HOUR * 24)) span = [ Math.round(Math.abs(offset / HOUR)), 'hr' ];
    else if (offset < (DAY * 7)) span = [ Math.round(Math.abs(offset / DAY)), 'day' ];
    else if (offset < (WEEK * 52)) span = [ Math.round(Math.abs(offset / WEEK)), 'week' ];
    else if (offset < (YEAR * 10)) span = [ Math.round(Math.abs(offset / YEAR)), 'year' ];
    else if (offset < (DECADE * 100)) span = [ Math.round(Math.abs(offset / DECADE)), 'decade' ];
    else span = [ '', 'a long time' ];
    span[1] += (span[0] === 0 || span[0] > 1) ? 's' : '';
    span = span.join(' ');
    return (time <= local) ? span + ' ago' : 'in ' + span;
}

function clearAndSetTitle(target, title) {
    title = title.replace("%20", " ");

    d3.select("#text-container")
        .transition()
        .duration(1000)
        .style("color", "#fff");
    target.transition().duration(1000).style("opacity", "0");
    target.selectAll(new Array("svg", "table", "h1")).remove();
    d3.select("#text-container").text(title);
    d3.select("#text-container")
        .transition()
        .duration(1000)
        .style("color", "#333");
    //target.append("h1").text(title);
    target.transition().duration(1000).style("opacity", "1");
}

function drawPieChart(json, target, config) {
   clearAndSetTitle(target, "Jobs Status: " + config["view"]);
      keyColor = function(d, i) {return colors[i];};
   var margin = {top: 15, right: 80, bottom: 150, left: 80},
        width = 1400 - margin.left - margin.right,
        height = 1000 - margin.top - margin.bottom;


   var total = json[0]["value"] + json[1]["value"] + json[2]["value"] + json[3]["value"]; 
   var chart = nv.models.pieChart()
        .x(function(d) { var fmt = d3.format("%"); return fmt((d.value / total)) })
        .y(function(d) { return (d.value/total) })
        .values(function(d) { return d })
        .width(width)
        .height(height)
        .labelThreshold(.05)
        .valueFormat(d3.format("%"))
        .donutLabelsOutside(true)
        .donut(true)
        .color(keyColor);

    var svg = target.append('svg')
        .datum([json])
        .transition()
        .duration(1200)
        .call(chart);



}

function drawStackedBarChart(json, target, config, granularity) {
    clearAndSetTitle(target, "Jobs Trend Bar Chart: " + config["view"]);

    var keyColor = function(d, i) {return colors[i];};
    var margin = {top: 15, right: 80, bottom: 150, left: 80},
        width = 1450 - margin.left - margin.right,
        height = 800 - margin.top - margin.bottom;


    var chart = nv.models.multiBarChart()
        .width(width)
        .height(height)
        .x(function(d) { return d[0] })
        .y(function(d) { return d[1] })
        .color(keyColor)
        .clipEdge(true);


    var x;

    if(granularity != "" ){
     // x = d3.time.scale()
       //   .domain([new Date(start), new Date(end)])
         // .range([0, width]);

      chart.xAxis
         .axisLabel(granularity + "s")
         .tickFormat(timeFormat(granularity));
    }else{
        chart.xAxis
          .tickFormat(function(d) { return d3.time.format('%d/%m/%y')(new Date(d)) });
        }


    chart.yAxis
         .axisLabel('Jobs')
         .tickFormat(d3.format('s'));

    var svg = target.append('svg')
        .datum(json)
        .transition()
        .duration(500)
        .call(chart);

    nv.utils.windowResize(chart.update);


}

function drawFailedJobsTable(json, target, config) {
    clearAndSetTitle(target, "Failing Jobs: " + config["view"]);

    var table = target.append("table").style("opacity", 0);

    // sort the data by lastSuccess
    json = json.sort(function(a, b) {
        a = a['lastSuccess'] ; b = b['lastSuccess'] ;
        return a < b ? -1 : (a > b ? 1 : 0);
    });

    // add the rows
    var textSize = 2.8;
    var count = 0;
    var max = 12;
    row = table.append("tr").style("font-size", textSize + "em").style("color", "#000000");
    row.append("td").text("Job");
    row.append("td").text("Last Stable");
    row.append("td").text("Last Ran");
    json.forEach(function(d) {
        row = table.append("tr").style("font-size", textSize + "em").style("color", colors[2]);
        if (count <= max) { 
            if (d.failType == "failed") {
                textSize -= 0.1;
                count += 1;
                row.append("td").text(d.name);
                if (parseInt(d.lastSuccess) == 0) {
                    row.append("td").text("NEVER Stable");
                } else {
                    row.append("td").text("" + timeAgo(d.lastSuccess));
                }
                if (parseInt(d.lastFailure) == 0) {
                    row.append("td").text("NEVER");
                } else {
                    row.append("td").text("" + timeAgo(d.lastFailure));
                }
            }
        }
    });
     json = json.sort(function(a, b) {
        a = a['lastStable'] ; b = b['lastStable'] ;
        return a < b ? -1 : (a > b ? 1 : 0);
    });


    json.forEach(function(d) {
        row = table.append("tr").style("font-size", textSize + "em").style("color", colors[1]);
        if (count <= max) {
            if (d.failType == "unstable") {
                textSize -= 0.1;
                count += 1;
                row.append("td").text(d.name);
                if (parseInt(d.lastStable) == 0) {
                    row.append("td").text("NEVER Stable");
                } else {
                    row.append("td").text("" + timeAgo(d.lastStable));
                }
                if (parseInt(d.lastUnstable) == 0) {
                    row.append("td").text("NEVER");
                } else {
                    row.append("td").text("" + timeAgo(d.lastUnstable));
                }
            }
        }
    });

    table.transition()
        .duration(1000)
        .style("opacity", 1);
}

function drawAreaChart(json, target, config, granularity) {
    clearAndSetTitle(target, "Jobs Trend Area Chart: " + config["view"]);
    
    var keyColor = function(d, i) {return colors[i];};
    var margin = {top: 15, right: 80, bottom: 150, left: 80},
        width = 1410 - margin.left - margin.right,
        height = 800 - margin.top - margin.bottom;

    var chart = nv.models.stackedAreaChart()
        .width(width)
        .height(height)
        .x(function(d) { return d[0] })
        .y(function(d) { return d[1] })
        .color(keyColor)
        .clipEdge(true);


    var x;

    if(granularity != ""){
     // x = d3.time.scale()
       //   .domain([new Date(start), new Date(end)])
         // .range([0, width]);
      
       chart.xAxis
         .axisLabel(granularity + "s")
         .tickFormat(timeFormat(granularity));
    }else{
        chart.xAxis
          .tickFormat(function(d) { return d3.time.format('%d/%m')(new Date(d)) });
        }

    chart.yAxis
         .axisLabel('Jobs')
         .tickFormat(d3.format('s'));

    var svg = target.append('svg')
        .datum(json)
        .transition()
        .duration(500)
        .call(chart);

    nv.utils.windowResize(chart.update);

}

function timeFormat(granularity) {
    var formats;
    if (granularity == "minute"){
        formats = [[d3.time.format("%H:%M"), function(d) { d = new Date(parseInt(d)); return d.getMinutes() != 1; }]];
    } else if (granularity == "hour"){
        formats = [  
        [d3.time.format("%H:%M"), function(d) { d = new Date(parseInt(d)); return d.getHours() != 1; }]
        ];
    } else if (granularity == "day"){
        formats = [
        [d3.time.format("%b %d"), function(d) { d = new Date(parseInt(d)); return d.getDate() != 1; }],
        [d3.time.format("%a %d"), function(d) { d = new Date(parseInt(d)); return d.getDay() != 1 && d.getDate() != 1; }]
        ];
    } else if (granularity == "week"){
        formats = [
        [d3.time.format("%W"), function(d) { d = new Date(parseInt(d)); return true; }]
        ];
    } else if (granularity == "day"){

        formats = [
        [d3.time.format("%b %d"), function(d) { d = new Date(parseInt(d)); return d.getDate() != 1; }],
        [d3.time.format("%a %d"), function(d) { d = new Date(parseInt(d)); return d.getDay() != 1 && d.getDate() != 1; }],
        ];
    } else if (granularity == "month"){
        formats = [
        [d3.time.format("%b %y"), function(d) { d = new Date(parseInt(d)); return d.getMonth() != 1;; }]
        ];
    } else if (granularity == "year"){
        formats = [
        [d3.time.format("%Y"), function() { return true; }]
        ];
    }

    return function(date) {
        var i = formats.length - 1, f = formats[i];
        while (!f[1](new Date(date))) {
            f = formats[--i];
        }
        return f[0](new Date(date));

  };
}


function drawWidget(divId, view, job, granularity, widgetType) {
    var options = { view: view };
    if (widgetType == "pie") {
        d3.json("/fem/jobStatus/view/" + view + "/api/json/?job=" + job, function(json) {
            drawPieChart(json, d3.select(divId), options);
        });
    } else if (widgetType == "jobs") {
        d3.json("/fem/failedJobs2/view/" + view + "/api/json/?job=" + job, function(json) {
            drawFailedJobsTable(json, d3.select(divId), options);
        });
    } else if (widgetType == "trendBar") {
        d3.json("/fem/jobTrend/?view=" + view + "&job=" + job + "&g=" + granularity, function(json) {
            drawStackedBarChart(json, d3.select(divId), options, granularity);
        });
    } else if (widgetType == "trendArea") {
        d3.json("/fem/jobTrend/?view=" + view + "&job=" + job + "&g=" + granularity, function(json) {
                drawAreaChart(json, d3.select(divId), options, granularity);
        });
    }     

}

function rotateWidgets(divId, view, job, start, end, granularity) {
    var radTypes = new Array("pie","trendBar","jobs","trendArea");
    //var radTypes = new Array("jobs");
    var radIdx = 0;

    drawWidget(divId, view, job, granularity, radTypes[radIdx]);
    setInterval(function() {
        radIdx = (radIdx + 1) % radTypes.length;
        drawWidget(divId, view, job, granularity, radTypes[radIdx]);
    }, 15000);
}

function showWidget(divId, view,type, job, granularity, url) {
    var options = { view: view };
        if (type == "PieChart") {
            d3.json(url + view + "/api/json/", function(json) {
                drawPieChart(json, d3.select(divId), options, view);
            });
        } else if (type == "Table") {
            d3.json(url + view + "/api/json/?job=" + job, function(json) {
                drawFailedJobsTable(json, d3.select(divId), options);
            });
        } else if (type == "TrendBarChart") {
            d3.json(url + "?view=" + view + "&job=" + '' + "&g=" + granularity, function(json) {
                drawStackedBarChart(json, d3.select(divId), options, granularity);

            });
        } else if (type == "TrendAreaChart") {
            d3.json(url + "?view=" + view + "&job=" + '' + "&g=" + granularity, function(json) {
                drawAreaChart(json, d3.select(divId), options, granularity);
            });
        }

}

function renderCustomWidgets(json, target, customView, firstCall) {
    var size = Object.keys(json).length
    var current = 0;                   
    var previous = size-1;
    var delay = 0;

    function renderLoop (delay,firstCall) { 

            if (firstCall !== "False") {
                delay = 0;
            }
            else {
                delay = json[previous].refresh * 1000;
            } 

        setTimeout(function () {    
            showWidget(target, json[current].view, json[current].type, json[current].job, json[current].granularity, json[current].url);
            previous = current;
            current++;                     
            if (current < size) {         
                renderLoop(delay, "False");  
            }                     
            else {
                rotateCustomWidgets(target, customView, "False")
            }
        }, delay)
    }   

    renderLoop(delay,firstCall); 
}

function rotateCustomWidgets(divId, customView, firstCall) {
    d3.json("/vis/" + customView + "/api/json/" , function(json) {
        renderCustomWidgets(json, divId, customView, firstCall);
    });
}

