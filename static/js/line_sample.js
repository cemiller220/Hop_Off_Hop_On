queue()
    .defer(d3.json, "/get_data_sample")
    .await(makeSamplePlot);

function makeSamplePlot(error, recordsJson) {
    var records = recordsJson;
    var dateFormat = d3.time.format("%H:%M:%S");
    
    records.forEach(function(d) {
                    d["time"] = dateFormat.parse(d["time"]);
                    d["time"].setSeconds(0);
                    d["adjusted_value"] = +d["adjusted_value"]
                    });
    
    var ndx = crossfilter(records);
    
    var crowd_dim = ndx.dimension(function(d) {return [d.stop_name, d3.time.hour(d.time)]; })
    var crowd_group = crowd_dim.group().reduceSum(function(d) { return d.adjusted_value; });
    
    var sampleCrowdChart = dc.seriesChart("#sample-crowd-chart");
    
    sampleCrowdChart
        .width(450)
        .height(350)
        .chart(function(c) {return dc.lineChart(c).interpolate('basis'); })
        .x(d3.time.scale().domain([dateFormat.parse('00:00:00'),dateFormat.parse('23:00:00')]))
        .xUnits(d3.time.minute)
        .brushOn(false)
        .yAxisLabel('Crowdedness')
        .xAxisLabel('Time')
        .clipPadding(10)
        .elasticY(true)
        .mouseZoomable(false)
        .dimension(crowd_dim)
        .group(crowd_group)
        .seriesAccessor(function(d) {return d.key[0];})
        .keyAccessor(function(d) {return d.key[1];})
        .valueAccessor(function(d) {return d.value;})
        .legend(dc.legend().x(60).y(0).itemHeight(13).gap(5).horizontal(0));
    
    sampleCrowdChart.margins().left += 10;
    
    dc.renderAll();
}