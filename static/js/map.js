// Current problem: need to reset selected stop/line on time change

queue()
    .defer(d3.json, "/get_data_map")
    .await(makeGraphs);

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



function makeGraphs(error, recordsJson) {
    var records = recordsJson;
    var dateFormat = d3.time.format("%H:%M:%S");
    
    records.forEach(function(d) {
                    d["time"] = dateFormat.parse(d["time"]);
                    d["time"].setMinutes(0);
                    d["time"].setSeconds(0);
                    d["adjusted_value"] = +d["adjusted_value"];
                    d["seconds"] = +d["seconds"];
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
    
    //Create Crossfilter instance
    var ndx = crossfilter(records);
    
    //var current_time_dim = time_from_slider();
    //current_time_dim.filter('yes');
    
    timeFormat = d3.time.format("%H:%M")
    
    //Define dimensions
    var stop_name_dim = ndx.dimension(function(d) { return d.stop_name; });
    var day_dim = ndx.dimension(function(d) { return d.day; });
    var lines_dim = ndx.dimension(function(d) { return d.lines; });
    var time_dim = ndx.dimension(function(d) { return timeFormat(d.time); });
    var stop_day_hour_dim = ndx.dimension(function(d) {return d.stop_id + " " + d.day + " " + d.time; } );
    var allDim = ndx.dimension(function(d) {return d;});

    
    //Group data
    var stop_name_group = stop_name_dim.group();
    var day_group = day_dim.group();
    var lines_group = lines_dim.groupAll().reduce(reduceAdd, reduceRemove, reduceInitial).value();
    var time_group = time_dim.group();
    var stop_day_hour_group = stop_day_hour_dim.group();
    var all = ndx.groupAll();
    
    var value_sum = stop_day_hour_group.reduceSum(function(d) { return Math.log10(d.adjusted_value); });
    var max_value = value_sum.top(1)[0].value;
    
    console.log(max_value);
    
    
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
    
    var timeDropdown = dc.selectMenu("#time-dropdown");
    var stopidSelector = dc.selectMenu("#stop-id-selector");
    var dayDropdown = dc.selectMenu("#day-dropdown");
    var linesSelector = dc.selectMenu("#lines-selector");

    
    timeDropdown
        .dimension(time_dim)
        .group(time_group)
        .controlsUseVisibility(true);
    
    linesSelector
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
        .dimension(stop_name_dim)
        .group(stop_name_group)
        .multiple(true)
        .numberVisible(30)
        .controlsUseVisibility(true);
    
    dayDropdown
        .dimension(day_dim)
        .group(day_group)
        .controlsUseVisibility(true);
    
    var map = L.map('map');
    
    var drawMap = function(){
        
        map.setView([40.76, -73.95], 12);
        mapLink = '<a href="http://openstreetmap.org">OpenStreetMap</a>';
        L.tileLayer(
                    'http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: '&copy; ' + mapLink + ' Contributors',
                    maxZoom: 20,
                    }).addTo(map);
        
        var geoData = []
        _.each(allDim.top(Infinity), function(d) {
               geoData.push([d["stop_lat"], d["stop_lon"], Math.log10(d["adjusted_value"])]);
               });
        var heat = L.heatLayer(geoData, {
                               radius: 10,
                               blue: 20,
                               maxZoom: 1,
                               max: max_value
                               }).addTo(map);
    };
    
    drawMap()
    
    dcCharts = [stopidSelector, dayDropdown, linesSelector, timeDropdown];
    
    _.each(dcCharts, function(dcChart) {
           dcChart.on("filtered", function(chart, filter) {
                      map.eachLayer(function (layer) {
                                    map.removeLayer(layer)
                                    });
                      drawMap();
                      });
           });
    
    dc.renderAll();
    
};