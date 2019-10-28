Highcharts.setOptions({
    lang: {
        thousandsSep: ','
    },
    chart: {
        style: {
            fontFamily: '"Roboto", sans-serif'
        }
    }
});

var ChartHelper = ChartHelper || {};
var ChartHelper = {
    make_column_chart: function(el,
        categories,
        series_data,
        title_text,
        historical_average,
        bar_color) {
      $(el).highcharts({
        chart: {
            type: 'column'
        },
        title: {
            text: title_text
        },
        xAxis: {
            categories: categories,
            title: {
                text: 'Congress'
            }
        },
        yAxis: {
            min: 0,
            title: {
                text: null,
                align: 'high'
            },
            labels: {
                overflow: 'justify'
            },
            stackLabels: {
              enabled: false,
            },
            allowDecimals: false,
            plotLines: [{
                value: historical_average,
                color: '#c2682a',
                dashStyle: 'shortdash',
                width: 2,
            }]
        },
        tooltip: {
          enabled: false,
        },
        plotOptions: {
            series: {
                dataLabels: {
                    enabled: true,
                },
                borderRadius: 2,
            }
        },
        credits: {
            enabled: false
        },
        series: [{
            data: series_data,
            color: bar_color,
        }],
        legend: {
          enabled: false,
        },
      });

    }
}
