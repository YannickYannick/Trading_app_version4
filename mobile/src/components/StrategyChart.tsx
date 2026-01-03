import React, { useRef, useEffect, useState } from 'react';
import { View, StyleSheet, ActivityIndicator } from 'react-native';
import { WebView } from 'react-native-webview';

interface ChartProps {
    priceHistory: { time: string; value: number }[];
    indicators?: {
        name: string;
        data: { time: string; value: number }[];
        color: string;
        lineWidth?: number;
        lineStyle?: number;
    }[];
    markers?: {
        time: string;
        position: 'aboveBar' | 'belowBar' | 'inBar';
        color: string;
        shape: 'circle' | 'square' | 'arrowUp' | 'arrowDown';
        text: string;
    }[];
    height?: number;
}

const HTML_CONTENT = `
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
    <script src="https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        body { margin: 0; padding: 0; background-color: #ffffff; overflow: hidden; }
        #chart-container { width: 100vw; height: 100vh; }
    </style>
</head>
<body>
    <div id="chart-container"></div>
    <script>
        let chart;
        let areaSeries;
        let indicatorSeriesMap = {};

        function log(msg) {
            window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'log', message: msg }));
        }

        function initChart() {
            try {
                const container = document.getElementById('chart-container');
                if (!container) return;

                if (typeof LightweightCharts === 'undefined') {
                    throw new Error('LightweightCharts library not loaded');
                }

                // Clean up existing chart if any
                if (chart) {
                    try { chart.remove(); } catch(e) {}
                    chart = null;
                }

                chart = LightweightCharts.createChart(container, {
                    width: container.clientWidth,
                    height: container.clientHeight,
                    layout: {
                        background: { color: '#ffffff' },
                        textColor: '#333',
                    },
                    grid: {
                        vertLines: { color: '#f0f0f0' },
                        horzLines: { color: '#f0f0f0' },
                    },
                    rightPriceScale: {
                        borderVisible: false,
                    },
                    timeScale: {
                        borderVisible: false,
                    },
                    crosshair: {
                        horzLine: {
                            visible: false,
                            labelVisible: false
                        },
                        vertLine: {
                            labelVisible: false,
                        }
                    },
                    handleScroll: {
                        mouseWheel: false,
                        pressedMouseMove: true,
                        horzTouchDrag: true,
                        vertTouchDrag: false,
                    },
                    handleScale: {
                        axisPressedMouseMove: true,
                        mouseWheel: false,
                        pinch: true,
                    },
                });

                areaSeries = chart.addAreaSeries({
                    topColor: 'rgba(33, 150, 243, 0.56)',
                    bottomColor: 'rgba(33, 150, 243, 0.04)',
                    lineColor: 'rgba(33, 150, 243, 1)',
                    lineWidth: 2,
                });

                window.addEventListener('resize', () => {
                   if (chart && container) {
                      chart.applyOptions({ width: container.clientWidth, height: container.clientHeight });
                   }
                });
                
                log('Chart initialized successfully');

            } catch (e) {
                log('Init error: ' + e.message);
                throw e; 
            }
        }

        function updateChart(data) {
            // Ensure chart and main series exist
            if (!chart || !areaSeries) {
                try {
                    initChart();
                } catch(e) {
                    return; // Init failed, cannot proceed
                }
            }

            try {
                if (data.priceHistory && areaSeries) {
                    areaSeries.setData(data.priceHistory);
                }

                // Update indicators
                if (data.indicators) {
                    // Remove old indicators
                    Object.keys(indicatorSeriesMap).forEach(key => {
                        try {
                            if (indicatorSeriesMap[key]) {
                                chart.removeSeries(indicatorSeriesMap[key]);
                            }
                        } catch(e) {
                            log('Error removing series: ' + e.message);
                        }
                    });
                    indicatorSeriesMap = {};

                    // Add new indicators
                    data.indicators.forEach((ind, index) => {
                        try {
                            const series = chart.addLineSeries({
                                color: ind.color || '#ff0000',
                                lineWidth: ind.lineWidth || 1,
                                lineStyle: ind.lineStyle || 0,
                                title: ind.name,
                                priceLineVisible: false,
                            });
                            series.setData(ind.data);
                            indicatorSeriesMap[ind.name + index] = series;
                        } catch(e) {
                            log('Error adding indicator ' + ind.name + ': ' + e.message);
                        }
                    });
                }

                // Update markers
                if (data.markers && areaSeries) {
                    areaSeries.setMarkers(data.markers);
                }
                
                if (chart) chart.timeScale().fitContent();
            } catch (e) {
                window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'error', message: 'Update error: ' + e.message }));
            }
        }

        // Initialize on load
        try {
            initChart();
        } catch(e) {
            // Already logged in initChart
        }
    </script>
</body>
</html>
`;

export const StrategyChart: React.FC<ChartProps> = ({ priceHistory, indicators, markers, height = 300 }) => {
    const webViewRef = useRef<WebView>(null);
    const [isLoaded, setIsLoaded] = useState(false);

    useEffect(() => {
        if (isLoaded && priceHistory.length > 0) {
            const data = {
                priceHistory,
                indicators,
                markers
            };
            const script = `updateChart(${JSON.stringify(data)});`;
            webViewRef.current?.injectJavaScript(script);
        }
    }, [priceHistory, indicators, markers, isLoaded]);

    return (
        <View style={{ height, backgroundColor: '#fff' }}>
            <WebView
                ref={webViewRef}
                originWhitelist={['*']}
                source={{ html: HTML_CONTENT }}
                style={{ flex: 1 }}
                onLoad={() => setIsLoaded(true)}
                scrollEnabled={false}
                bounces={false}
                onMessage={(event) => {
                    console.log('Chart Webview Log:', event.nativeEvent.data);
                }}
            />
            {!isLoaded && (
                <View style={StyleSheet.absoluteFillObject}>
                    <ActivityIndicator size="large" color="#2196F3" style={{ flex: 1 }} />
                </View>
            )}
        </View>
    );
};
