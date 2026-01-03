import React, { useState, useEffect, useMemo } from 'react'
import { View, Text, StyleSheet, ScrollView, Alert, TouchableOpacity, Switch, Modal, FlatList } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { useNavigation, useRoute } from '@react-navigation/native'
import { Ionicons } from '@expo/vector-icons'
import { strategiesService, assetsService } from '../services/api'
import { StrategyChart } from '../components/StrategyChart'
import { Input } from '../components/common/Input'
import { Button } from '../components/common/Button'
import type { AllAsset } from '@trading-app/shared'
import {
    calculateStrategySignals,
    simulateTradesFromSignals,
    calculatePerformanceMetrics,
    calculateRSI, calculateMA, calculateBollingerBands, calculateMACD
} from '@trading-app/shared'
import type { Strategy, TradeSimulation } from '@trading-app/shared'

const ALGO_TYPES = ['ma_crossover', 'macd', 'rsi', 'bollinger', 'threshold', 'grid']

export const StrategyEditScreen = () => {
    const navigation = useNavigation()
    const route = useRoute()
    const { strategy: initialStrategy } = route.params as { strategy: Strategy }

    const [strategy, setStrategy] = useState<Strategy>(initialStrategy)
    const [parameters, setParameters] = useState<Record<string, any>>({ ...initialStrategy.parameters, ...strategy.algorithm_parameters?.reduce((acc, p) => ({ ...acc, [p.key]: p.value }), {}) })
    const [priceHistory, setPriceHistory] = useState<any[]>([])
    const [isLoading, setIsLoading] = useState(false)
    const [isSaving, setIsSaving] = useState(false)
    const [isSyncing, setIsSyncing] = useState(false)

    // New editable fields
    const [minQuantity, setMinQuantity] = useState(String(strategy.min_quantity || ''))
    const [maxQuantity, setMaxQuantity] = useState(String(strategy.max_quantity || ''))

    // Asset Search State
    const [isAssetModalVisible, setAssetModalVisible] = useState(false)
    const [assetSearchQuery, setAssetSearchQuery] = useState('')
    const [searchResults, setSearchResults] = useState<AllAsset[]>([])
    const [isSearching, setIsSearching] = useState(false)

    // Debounce search
    useEffect(() => {
        const timer = setTimeout(() => {
            if (assetSearchQuery.length >= 2) {
                searchAssets()
            }
        }, 500)
        return () => clearTimeout(timer)
    }, [assetSearchQuery])

    const searchAssets = async () => {
        try {
            setIsSearching(true)
            const response = await assetsService.search(assetSearchQuery)
            setSearchResults(response.results)
        } catch (e) {
            console.error(e)
        } finally {
            setIsSearching(false)
        }
    }

    // Refresh strategy on mount to ensure latest parameters
    useEffect(() => {
        const fetchLatestStrategy = async () => {
            try {
                const freshStrategy = await strategiesService.getById(initialStrategy.id)
                setStrategy(freshStrategy)

                // Update parameters with fresh data
                const combinedParams = {
                    ...freshStrategy.parameters,
                    ...freshStrategy.algorithm_parameters?.reduce((acc: any, p: any) => ({ ...acc, [p.key]: p.value }), {})
                }
                setParameters(combinedParams)

                // Also update quantity fields
                setMinQuantity(String(freshStrategy.min_quantity || ''))
                setMaxQuantity(String(freshStrategy.max_quantity || ''))
            } catch (e) {
                console.error('Failed to refresh strategy', e)
            }
        }
        fetchLatestStrategy()
    }, [initialStrategy.id])

    // Load price history
    useEffect(() => {
        const loadData = async () => {
            if (!strategy.all_asset) return
            setIsLoading(true)
            try {
                const assetId = typeof strategy.all_asset === 'number' ? strategy.all_asset : strategy.all_asset.id
                console.log('Fetching prices for assetId:', assetId)
                const historyResponse = await assetsService.getPriceHistory(assetId, 365)

                const prices = (historyResponse.results || [])
                    .map((point: any) => ({
                        time: point.date?.split('T')[0] || point.date,
                        value: Number(point.close || 0),
                    }))
                    .filter((p: any) => p.value > 0 && p.time)
                    .sort((a: any, b: any) => a.time.localeCompare(b.time))

                setPriceHistory(prices)
            } catch (e) {
                console.error(e)
                Alert.alert('Erreur', 'Impossible de charger l\'historique des prix')
            } finally {
                setIsLoading(false)
            }
        }
        loadData()
    }, [strategy.all_asset])

    // Calculate indicators and signals
    const chartData = useMemo(() => {
        if (priceHistory.length === 0 || !strategy.algorithm_type) return null

        const prices = priceHistory.map(p => p.value)
        const dates = priceHistory.map(p => p.time)

        // Convert params to proper types
        const numericParams: any = {}
        Object.keys(parameters).forEach(key => {
            const val = parameters[key]
            numericParams[key] = !isNaN(Number(val)) ? Number(val) : val
        })

        // Calculate signals
        const signals = calculateStrategySignals(strategy.algorithm_type, prices, dates, numericParams)

        // Calculate performance
        const simulated = simulateTradesFromSignals(
            signals,
            prices,
            dates,
            numericParams.order_size || 1.0,
            numericParams.stop_loss,
            minQuantity ? Number(minQuantity) : 0,
            maxQuantity ? Number(maxQuantity) : undefined,
            numericParams.budget
        )
        const metrics = calculatePerformanceMetrics(simulated)

        // Prepare chart indicators
        const indicators: any[] = []

        try {
            switch (strategy.algorithm_type) {
                case 'ma_crossover':
                    const ma1 = calculateMA(prices, numericParams.ma1_period || 20)
                    const ma2 = calculateMA(prices, numericParams.ma2_period || 50)
                    indicators.push({
                        name: 'MA Fast',
                        data: dates.map((d, i) => ({ time: d, value: ma1[i] })).filter(p => !isNaN(p.value)),
                        color: '#2196F3',
                        lineWidth: 2
                    })
                    indicators.push({
                        name: 'MA Slow',
                        data: dates.map((d, i) => ({ time: d, value: ma2[i] })).filter(p => !isNaN(p.value)),
                        color: '#F44336',
                        lineWidth: 2
                    })
                    break

                case 'bollinger':
                    const bands = calculateBollingerBands(prices, numericParams.bb_period || 20, numericParams.bb_std || 2)
                    indicators.push({
                        name: 'Upper',
                        data: dates.map((d, i) => ({ time: d, value: bands.upper[i] })).filter(p => !isNaN(p.value)),
                        color: '#4CAF50',
                        lineWidth: 1
                    })
                    indicators.push({
                        name: 'Lower',
                        data: dates.map((d, i) => ({ time: d, value: bands.lower[i] })).filter(p => !isNaN(p.value)),
                        color: '#4CAF50',
                        lineWidth: 1
                    })
                    break
                case 'threshold':
                    if (numericParams.threshold_low) {
                        indicators.push({
                            name: 'Low',
                            data: dates.map(d => ({ time: d, value: numericParams.threshold_low })),
                            color: '#4CAF50',
                            lineWidth: 1
                        })
                    }
                    if (numericParams.threshold_high) {
                        indicators.push({
                            name: 'High',
                            data: dates.map(d => ({ time: d, value: numericParams.threshold_high })),
                            color: '#F44336',
                            lineWidth: 1
                        })
                    }
                    break
            }
        } catch (e) {
            console.error("Error calculating indicators", e)
        }

        // Prepare markers (buy/sell)
        const markers = simulated
            .filter(t => t.status === 'CLOSED' || t.status === 'OPEN')
            .map(t => ({
                time: t.entryTime,
                position: t.side === 'BUY' ? 'belowBar' : 'aboveBar',
                color: t.side === 'BUY' ? '#4CAF50' : '#F44336',
                shape: t.side === 'BUY' ? 'arrowUp' : 'arrowDown',
                text: t.side
            }))

        return { indicators, markers, metrics, simulated }
    }, [priceHistory, parameters, strategy.algorithm_type, minQuantity, maxQuantity])

    const simulatedTrades = chartData?.simulated || []

    const handleAssetSelect = async (asset: AllAsset) => {
        setStrategy(prev => ({
            ...prev,
            all_asset: asset,
            all_asset_symbol: asset.symbol,
            all_asset_name: asset.name
        }))
        setAssetModalVisible(false)

        // Auto-fetch sequence
        setIsSyncing(true)
        try {
            // 1. Validate Yahoo Symbol
            await assetsService.validateYahooSymbol(asset.id)

            // 2. Sync Price History (1 year)
            await assetsService.syncPriceHistory(asset.id, 365)

            // 3. Reload Chart (trigger useEffect)
            // Just modifying the object reference to trigger reload if ID didn't change (rare but possible)
            setStrategy(prev => ({ ...prev, all_asset: { ...asset } as any }))

            Alert.alert('Info', 'Données de marché mises à jour')
        } catch (e) {
            console.error(e)
            Alert.alert('Erreur', 'Impossible de récupérer les données marché')
        } finally {
            setIsSyncing(false)
        }
    }

    const handleManualYahooSearch = async () => {
        const assetId = typeof strategy.all_asset === 'object' ? strategy.all_asset?.id : strategy.all_asset
        if (!assetId) return

        setIsSyncing(true)
        try {
            const res = await assetsService.validateYahooSymbol(assetId)
            Alert.alert('Succès', res.message || 'Recherche terminée')
        } catch (e) {
            Alert.alert('Erreur', 'Recherche échouée')
        } finally {
            setIsSyncing(false)
        }
    }

    const handleManualPriceSync = async () => {
        const assetId = typeof strategy.all_asset === 'object' ? strategy.all_asset?.id : strategy.all_asset
        if (!assetId) return

        setIsSyncing(true)
        try {
            // Validate first to be sure
            await assetsService.validateYahooSymbol(assetId)
            // Then sync
            await assetsService.syncPriceHistory(assetId, 365)
            // Trigger chart reload
            const currentAsset = strategy.all_asset
            setStrategy(prev => ({ ...prev, all_asset: undefined }))
            setTimeout(() => {
                setStrategy(prev => ({ ...prev, all_asset: currentAsset }))
            }, 50)

            Alert.alert('Succès', 'Historique mis à jour sur 1 an')
        } catch (e) {
            Alert.alert('Erreur', 'Mise à jour échouée')
        } finally {
            setIsSyncing(false)
        }
    }

    const handleSave = async () => {
        setIsSaving(true)
        try {
            // Helper to determine param type
            const getParamType = (key: string, value: any): 'str' | 'int' | 'float' | 'bool' => {
                if (typeof value === 'boolean' || value === 'true' || value === 'false') return 'bool'
                if (!isNaN(Number(value))) {
                    return String(value).includes('.') ? 'float' : 'int'
                }
                return 'str'
            }

            // Convert parameters object to algorithm_parameters_data array format (WRITE ONLY field)
            const algorithmParamsCheck = Object.entries(parameters).map(([key, value]) => ({
                key,
                value: String(value),
                param_type: getParamType(key, value)
            }))

            await strategiesService.update(strategy.id, {
                algorithm_parameters_data: algorithmParamsCheck, // Use the correct write-only field
                algorithm_type: strategy.algorithm_type,
                name: strategy.name,
                all_asset: typeof strategy.all_asset === 'object' ? strategy.all_asset?.id : strategy.all_asset,
                min_quantity: minQuantity ? Number(minQuantity) : undefined,
                max_quantity: maxQuantity ? Number(maxQuantity) : undefined
            })
            Alert.alert('Succès', 'Stratégie mise à jour')
        } catch (e) {
            console.error('Save error:', e)
            Alert.alert('Erreur', 'Impossible de sauvegarder')
        } finally {
            setIsSaving(false)
        }
    }

    const renderParameterInput = (key: string, label: string, defaultValue: string) => (
        <Input
            label={label}
            value={String(parameters[key] !== undefined ? parameters[key] : defaultValue)}
            onChangeText={(text) => setParameters(prev => ({ ...prev, [key]: text }))}
            keyboardType="numeric"
            style={{ marginBottom: 12 }}
        />
    )

    return (
        <SafeAreaView style={styles.container}>
            <View style={styles.header}>
                <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backButton}>
                    <Ionicons name="arrow-back" size={24} color="#333" />
                </TouchableOpacity>
                <Text style={styles.title}>{strategy.name}</Text>
                <TouchableOpacity onPress={handleSave} disabled={isSaving}>
                    <Text style={{ color: '#2196F3', fontWeight: 'bold', fontSize: 16 }}>
                        {isSaving ? '...' : 'Sauvegarder'}
                    </Text>
                </TouchableOpacity>
            </View>

            <ScrollView contentContainerStyle={styles.content}>
                <View style={{ paddingHorizontal: 16, marginBottom: 12 }}>
                    <Text style={styles.label}>Nom de la stratégie</Text>
                    <Input
                        value={strategy.name}
                        onChangeText={(text) => setStrategy(prev => ({ ...prev, name: text }))}
                        placeholder="Nom de la stratégie"
                    />
                </View>

                <View style={styles.chartContainer}>
                    {priceHistory.length > 0 ? (
                        <StrategyChart
                            priceHistory={priceHistory}
                            indicators={chartData?.indicators}
                            markers={chartData?.markers as any}
                            height={300}
                        />
                    ) : (
                        <View style={[styles.chartContainer, { justifyContent: 'center', alignItems: 'center' }]}>
                            <Text>{isLoading ? 'Chargement...' : 'Pas de données'}</Text>
                        </View>
                    )}
                </View>

                {chartData?.metrics && (
                    <View style={styles.metricsContainer}>
                        <View style={styles.metricItem}>
                            <Text style={styles.metricLabel}>Win Rate</Text>
                            <Text style={[styles.metricValue, { color: chartData.metrics.winRate >= 50 ? '#4CAF50' : '#F44336' }]}>
                                {chartData.metrics.winRate.toFixed(1)}%
                            </Text>
                        </View>
                        <View style={styles.metricItem}>
                            <Text style={styles.metricLabel}>PnL</Text>
                            <Text style={[styles.metricValue, { color: chartData.metrics.totalPnL >= 0 ? '#4CAF50' : '#F44336' }]}>
                                {chartData.metrics.totalPnL.toFixed(2)}
                            </Text>
                        </View>
                        <View style={styles.metricItem}>
                            <Text style={styles.metricLabel}>Trades</Text>
                            <Text style={styles.metricValue}>{chartData.metrics.totalTrades}</Text>
                        </View>
                    </View>
                )}

                <Text style={styles.sectionTitle}>Configuration</Text>

                <Text style={styles.label}>Actif Cible</Text>
                <TouchableOpacity
                    style={styles.assetSelector}
                    onPress={() => {
                        setAssetModalVisible(true)
                        searchAssets()
                    }}
                >
                    {strategy.all_asset ? (
                        <View>
                            <Text style={styles.assetSelectorSymbol}>
                                {typeof strategy.all_asset === 'object' ? strategy.all_asset.symbol : strategy.all_asset_symbol}
                            </Text>
                            <Text style={styles.assetSelectorName}>
                                {typeof strategy.all_asset === 'object' ? strategy.all_asset.name : strategy.all_asset_name}
                            </Text>
                        </View>
                    ) : (
                        <Text style={styles.assetSelectorPlaceholder}>Sélectionner un actif...</Text>
                    )}
                    <Ionicons name="chevron-forward" size={20} color="#999" />
                </TouchableOpacity>



                {/* Manual Action Buttons */}
                <View style={{ flexDirection: 'row', gap: 12, marginBottom: 16, paddingHorizontal: 16 }}>
                    <Button
                        title="Rechercher Symbole"
                        onPress={handleManualYahooSearch}
                        loading={isSyncing}
                        variant="outline"
                        style={{ flex: 1 }}
                        size="sm"
                    />
                    <Button
                        title="MAJ Prix (1 an)"
                        onPress={handleManualPriceSync}
                        loading={isSyncing}
                        variant="outline"
                        style={{ flex: 1 }}
                        size="sm"
                    />
                </View>

                <Text style={styles.label}>Algorithme</Text>
                <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipsScroll}>
                    {ALGO_TYPES.map(algo => (
                        <TouchableOpacity
                            key={algo}
                            style={[
                                styles.chip,
                                strategy.algorithm_type === algo && styles.chipActive
                            ]}
                            onPress={() => setStrategy(prev => ({ ...prev, algorithm_type: algo }))}
                        >
                            <Text style={[styles.chipText, strategy.algorithm_type === algo && styles.chipTextActive]}>
                                {algo.toUpperCase().replace('_', ' ')}
                            </Text>
                        </TouchableOpacity>
                    ))}
                </ScrollView>

                <View style={{ flexDirection: 'row', gap: 12 }}>
                    <View style={{ flex: 1 }}>
                        <Input
                            label="Min Quantity"
                            value={minQuantity}
                            onChangeText={setMinQuantity}
                            keyboardType="numeric"
                            placeholder="0"
                        />
                    </View>
                    <View style={{ flex: 1 }}>
                        <Input
                            label="Max Quantity"
                            value={maxQuantity}
                            onChangeText={setMaxQuantity}
                            keyboardType="numeric"
                            placeholder="100"
                        />
                    </View>
                </View>

                <Text style={styles.sectionTitle}>Paramètres ({strategy.algorithm_type})</Text>

                <View style={styles.paramsContainer}>
                    {strategy.algorithm_type === 'ma_crossover' && (
                        <>
                            {renderParameterInput('ma1_period', 'Fast MA Period', '20')}
                            {renderParameterInput('ma2_period', 'Slow MA Period', '50')}
                        </>
                    )}
                    {strategy.algorithm_type === 'rsi' && (
                        <>
                            {renderParameterInput('rsi_period', 'RSI Period', '14')}
                            {renderParameterInput('rsi_low', 'Overbought (Low)', '30')}
                            {renderParameterInput('rsi_high', 'Oversold (High)', '70')}
                        </>
                    )}
                    {strategy.algorithm_type === 'bollinger' && (
                        <>
                            {renderParameterInput('bb_period', 'Period', '20')}
                            {renderParameterInput('bb_std', 'Std Dev', '2')}
                        </>
                    )}
                    {strategy.algorithm_type === 'macd' && (
                        <>
                            {renderParameterInput('macd_fast', 'Fast Period', '12')}
                            {renderParameterInput('macd_slow', 'Slow Period', '26')}
                            {renderParameterInput('macd_signal', 'Signal Period', '9')}
                        </>
                    )}
                    {strategy.algorithm_type === 'threshold' && (
                        <>
                            {renderParameterInput('threshold_low', 'Achat si <', '100')}
                            {renderParameterInput('threshold_high', 'Vente si >', '200')}
                        </>
                    )}
                    {strategy.algorithm_type === 'grid' && (
                        <>
                            {renderParameterInput('grid_min', 'Prix Min', '100')}
                            {renderParameterInput('grid_max', 'Prix Max', '200')}
                            {renderParameterInput('grid_levels', 'Niveaux', '10')}
                        </>
                    )}
                    {/* Common Params */}
                    {renderParameterInput('order_size', 'Taille Ordre', '1.0')}
                    {renderParameterInput('stop_loss', 'Stop Loss % (ex: 0.05)', '0.05')}
                </View>

                {/* Simulated Trades Table */}
                <Text style={styles.sectionTitle}>Trades Simulés ({chartData?.metrics?.totalTrades || 0})</Text>
                <View style={styles.tableContainer}>
                    <View style={styles.tableHeader}>
                        <Text style={[styles.tableHeaderText, { flex: 2 }]}>Date</Text>
                        <Text style={[styles.tableHeaderText, { flex: 0.8 }]}>Type</Text>
                        <Text style={[styles.tableHeaderText, { flex: 1, textAlign: 'right' }]}>Qté</Text>
                        <Text style={[styles.tableHeaderText, { flex: 1.5, textAlign: 'right' }]}>Prix</Text>
                        <Text style={[styles.tableHeaderText, { flex: 1.5, textAlign: 'right' }]}>PnL</Text>
                    </View>
                    {simulatedTrades.slice().reverse().slice(0, 50).map((trade, index) => (
                        <View key={index} style={styles.tableRow}>
                            <Text style={[styles.tableCell, { flex: 2 }]}>{trade.entryTime}</Text>
                            <Text style={[styles.tableCell, { flex: 0.8, color: trade.side === 'BUY' ? '#4CAF50' : '#F44336', fontWeight: 'bold' }]}>
                                {trade.side}
                            </Text>
                            <Text style={[styles.tableCell, { flex: 1, textAlign: 'right' }]}>
                                {trade.quantity ? trade.quantity.toFixed(4) : '-'}
                            </Text>
                            <Text style={[styles.tableCell, { flex: 1.5, textAlign: 'right' }]}>
                                {trade.entryPrice.toFixed(2)}
                            </Text>
                            <Text style={[styles.tableCell, { flex: 1.5, textAlign: 'right', color: (trade.pnl || 0) >= 0 ? '#4CAF50' : '#F44336' }]}>
                                {trade.pnl ? trade.pnl.toFixed(2) : '-'}
                            </Text>
                        </View>
                    ))}
                    {simulatedTrades.length === 0 && (
                        <Text style={{ textAlign: 'center', padding: 20, color: '#999' }}>Aucun trade simulé</Text>
                    )}
                </View>

            </ScrollView>

            {/* Asset Modal */}
            <Modal visible={isAssetModalVisible} animationType="slide" presentationStyle="pageSheet">
                <View style={styles.modalContainer}>
                    <View style={styles.modalHeader}>
                        <Text style={styles.modalTitle}>Sélectionner un actif</Text>
                        <TouchableOpacity onPress={() => setAssetModalVisible(false)}>
                            <Text style={styles.closeButton}>Fermer</Text>
                        </TouchableOpacity>
                    </View>
                    <View style={styles.searchContainer}>
                        <Ionicons name="search" size={20} color="#666" style={{ marginRight: 8 }} />
                        <Input
                            value={assetSearchQuery}
                            onChangeText={setAssetSearchQuery}
                            placeholder="Rechercher (ex: AAPL, BTC)..."
                            style={{ flex: 1, marginBottom: 0 }}
                        />
                    </View>
                    <FlatList
                        data={searchResults}
                        keyExtractor={(item) => item.id.toString()}
                        renderItem={({ item }) => (
                            <TouchableOpacity
                                style={styles.modalItem}
                                onPress={() => {
                                    setStrategy(prev => ({
                                        ...prev,
                                        all_asset: item,
                                        all_asset_symbol: item.symbol,
                                        all_asset_name: item.name
                                    }))
                                    setAssetModalVisible(false)
                                }}
                            >
                                <View>
                                    <Text style={styles.itemSymbol}>{item.symbol}</Text>
                                    <Text style={styles.itemName}>{item.name}</Text>
                                </View>
                                <Text style={styles.itemType}>{item.asset_type}</Text>
                            </TouchableOpacity>
                        )}
                        ListEmptyComponent={
                            <View style={styles.emptySearch}>
                                <Text style={{ color: '#999' }}>
                                    {isSearching ? 'Recherche...' : 'Aucun actif trouvé'}
                                </Text>
                            </View>
                        }
                    />
                </View>
            </Modal>
        </SafeAreaView >
    )
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#fff',
    },
    header: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: 16,
        borderBottomWidth: 1,
        borderBottomColor: '#eee',
    },
    backButton: {
        padding: 4,
    },
    title: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#333',
    },
    content: {
        paddingBottom: 40,
    },
    chartContainer: {
        height: 300,
        backgroundColor: '#f8f9fa',
        marginBottom: 16,
    },
    metricsContainer: {
        flexDirection: 'row',
        justifyContent: 'space-around',
        padding: 16,
        backgroundColor: '#f5f5f5',
        marginHorizontal: 16,
        borderRadius: 8,
        marginBottom: 20,
    },
    metricItem: {
        alignItems: 'center',
    },
    metricLabel: {
        fontSize: 12,
        color: '#666',
        marginBottom: 4,
    },
    metricValue: {
        fontSize: 16,
        fontWeight: 'bold',
        color: '#333',
    },
    sectionTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        marginLeft: 16,
        marginBottom: 12,
        color: '#333',
    },
    label: {
        fontSize: 14,
        fontWeight: '600',
        marginLeft: 16,
        marginBottom: 8,
        color: '#666',
        marginTop: 8,
    },
    paramsContainer: {
        paddingHorizontal: 16,
    },
    assetHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: 16,
        backgroundColor: '#f5f5f5',
        marginHorizontal: 16,
        marginBottom: 16,
        borderRadius: 8,
    },
    assetSymbol: {
        fontSize: 16,
        fontWeight: 'bold',
        color: '#333',
    },
    assetName: {
        fontSize: 12,
        color: '#666',
    },
    modalContainer: {
        flex: 1,
        backgroundColor: '#fff',
    },
    modalHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: 16,
        borderBottomWidth: 1,
        borderBottomColor: '#eee',
    },
    modalTitle: {
        fontSize: 18,
        fontWeight: 'bold',
    },
    closeButton: {
        color: '#2196F3',
        fontSize: 16,
    },
    searchContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        padding: 12,
        borderBottomWidth: 1,
        borderBottomColor: '#eee',
    },
    modalItem: {
        padding: 16,
        borderBottomWidth: 1,
        borderBottomColor: '#f0f0f0',
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    itemSymbol: {
        fontWeight: 'bold',
        fontSize: 16,
    },
    itemName: {
        color: '#666',
        fontSize: 12,
    },
    itemType: {
        fontSize: 12,
        color: '#999',
        backgroundColor: '#f5f5f5',
        paddingHorizontal: 8,
        paddingVertical: 4,
        borderRadius: 12,
    },
    emptySearch: {
        padding: 40,
        alignItems: 'center',
    },
    assetSelector: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: 16,
        borderWidth: 1,
        borderColor: '#ddd',
        borderRadius: 8,
        backgroundColor: '#FAFAFA',
        marginHorizontal: 16,
        marginBottom: 16,
    },
    assetSelectorSymbol: {
        fontWeight: 'bold',
        fontSize: 16,
    },
    assetSelectorName: {
        fontSize: 12,
        color: '#666',
    },
    assetSelectorPlaceholder: {
        color: '#999',
    },
    chipsScroll: {
        flexDirection: 'row',
        marginHorizontal: 16,
        marginBottom: 16,
    },
    chip: {
        paddingHorizontal: 16,
        paddingVertical: 8,
        borderRadius: 20,
        backgroundColor: '#f5f5f5',
        marginRight: 8,
        borderWidth: 1,
        borderColor: 'transparent',
    },
    chipActive: {
        backgroundColor: '#E3F2FD',
        borderColor: '#2196F3',
    },
    chipText: {
        fontSize: 12,
        color: '#666',
    },
    chipTextActive: {
        color: '#2196F3',
        fontWeight: 'bold',
    },
    tableContainer: {
        marginHorizontal: 16,
        marginBottom: 30,
        backgroundColor: '#fff',
        borderRadius: 8,
        borderWidth: 1,
        borderColor: '#eee',
        overflow: 'hidden',
    },
    tableHeader: {
        flexDirection: 'row',
        padding: 12,
        backgroundColor: '#f5f5f5',
        borderBottomWidth: 1,
        borderBottomColor: '#eee',
    },
    tableHeaderText: {
        fontWeight: 'bold',
        fontSize: 12,
        color: '#666',
    },
    tableRow: {
        flexDirection: 'row',
        padding: 12,
        borderBottomWidth: 1,
        borderBottomColor: '#f9f9f9',
    },
    tableCell: {
        fontSize: 12,
        color: '#333',
    },
})
