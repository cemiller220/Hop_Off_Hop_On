//current problems: update legend with selection

queue()
    .defer(d3.json, "/get_data_map")
    .await(makePlot);

function reduceAdd(p, v) {
    v.lines.forEach (function(val, idx) {
                     if (val == '6X') {
                     val = '6';
                     } else if (val == '7X') {
                     val = '7';
                     } else if (val == 'A1' || val == 'A2') {
                     val = 'A';
                     }
                     p[val] = (p[val] || 0) + 1; //increment counts
                     });
    return p;
}

function reduceRemove(p, v) {
    v.lines.forEach (function(val, idx) {
                     if (val == '6X') {
                     val = '6';
                     } else if (val == '7X') {
                     val = '7';
                     } else if (val == 'A1' || val == 'A2') {
                     val = 'A';
                     }
                     p[val] = (p[val] || 0) - 1; //decrement counts
                     });
    return p;
    
}

function reduceInitial() {
    return {};
}


function makePlot(error, recordsJson) {
    var records = recordsJson;
    var dateFormat = d3.time.format("%H:%M:%S");
    
    records.forEach(function(d) {
                    d["time"] = dateFormat.parse(d["time"]);
                    d["time"].setMinutes(0);
                    d["time"].setSeconds(0);
                    d["adjusted_value"] = +d["adjusted_value"];
                    d["stop_lat"] = +d["stop_lat"];
                    d["stop_lon"] = +d["stop_lon"];
                    lines = [];
                    for (i=0; i<d["lines"].length; i++){
                    if (d["lines"][i] == 'A1' || d["lines"][i] == 'A2') {
                    if (lines.indexOf('A') < 0){
                    lines.push('A');
                    }
                    } else if (d["lines"][i] == '6X') {
                    if (lines.indexOf('6') < 0){
                    lines.push('6');
                    }
                    } else if (d["lines"][i] == '7X') {
                    if (lines.indexOf('7') < 0){
                    lines.push('7');
                    }
                    } else {
                    lines.push(d["lines"][i]);
                    }
                    }
                    
                    d["lines"] = lines;
                    });
    
    var ndx = crossfilter(records);
    
    var stop_name_dim = ndx.dimension(function(d) { return d.stop_name; });
    var day_dim = ndx.dimension(function(d) { return d.day; });
    var lines_dim = ndx.dimension(function(d) { return d.lines; });
    var crowd_dim = ndx.dimension(function(d) {return [d.stop_name, d.time]; })
    var allDim = ndx.dimension(function(d) {return d;});
    
    //Group data
    var stop_name_group = stop_name_dim.group();
    var day_group = day_dim.group();
    var lines_group = lines_dim.groupAll().reduce(reduceAdd, reduceRemove, reduceInitial).value();
    var crowd_group = crowd_dim.group().reduceSum(function(d) { return d.adjusted_value; });
    var filtered_crowd = remove_empty_bins(crowd_group)
    var all = ndx.groupAll();
    
    lines_group.all = function() {
        var newObject = [];
        for (var key in this) {
            if (this.hasOwnProperty(key) && key != "all") {
                newObject.push({
                               key: key,
                               value: this[key]
                               });
            }
        }
        return newObject;
    }
    
    var stopidSelector = dc.selectMenu("#stop-id-selector2","group1");
    var dayDropdown = dc.selectMenu("#day-dropdown2", "group1");
    var linesSelector = dc.selectMenu("#lines-selector2", "group1");
    var crowdChart = dc.seriesChart("#crowd-chart", "plot");
    
    linesSelector
        .width(200)
        .dimension(lines_dim)
        .group(lines_group)
        .multiple(true)
        .numberVisible(10)
        .controlsUseVisibility(true)
        .filterHandler (function (dimension, filters) {
                        dimension.filter(null);
                        if (filters.length === 0)
                        dimension.filter(null);
                        else
                        dimension.filterFunction(function (d) {
                                                 for (var i=0; i < d.length; i++) {
                                                 if (filters.indexOf(d[i]) >= 0) return true;
                                                 }
                                                 return false;
                                                 });
                        return filters;
                        });
    
    stopidSelector
        .width(100)
        .dimension(stop_name_dim)
        .group(stop_name_group)
        .multiple(true)
        .numberVisible(30)
        .controlsUseVisibility(true);
    
    dayDropdown
        .dimension(day_dim)
        .group(day_group)
        .controlsUseVisibility(true);
    
    var drawPlot = function() {
        crowdChart
        .width(590)
        .height(400)
        .chart(function(c) {return dc.lineChart(c).interpolate('basis'); })
        .x(d3.time.scale().domain([dateFormat.parse('00:00:00'),dateFormat.parse('23:00:00')]))
        .xUnits(d3.time.hour)
        .brushOn(false)
        .yAxisLabel('Crowdedness')
        .xAxisLabel('Time')
        .clipPadding(10)
        .elasticY(true)
        .mouseZoomable(false)
        .dimension(crowd_dim)
        .group(filtered_crowd)
        .seriesAccessor(function(d) {return d.key[0];})
        .keyAccessor(function(d) {return d.key[1];})
        .valueAccessor(function(d) {return d.value;})
        .legend(dc.legend().x(60).y(0).itemHeight(13).gap(5).horizontal(0));
        
    dc.renderAll("plot");
    }
    dc.renderAll("group1");
    
    //drawPlot();
    crowdChart.margins().left += 10;
    
    
    
    function remove_empty_bins(source_group) {
        return {
        all:function () {
            return source_group.all().filter(function(d) {
                                             return d.value != 0;
                                             });
        }
        };
    }
    
    
    var submitButton = document.getElementById("make_plot");
    submitButton.addEventListener("click", function(){
                                  crowd_group = crowd_dim.group().reduceSum(function(d) { return d.adjusted_value; });
                                  filtered_crowd = remove_empty_bins(crowd_group);
                                  drawPlot();
                                  });
    
    
    
    
}