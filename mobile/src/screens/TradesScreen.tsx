import React from 'react'
import { View, Text, StyleSheet, ScrollView, RefreshControl } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { useTrades } from '../hooks/useTrades'
import { Card } from '../components/common/Card'
import type { Trade } from '@trading-app/shared'
import { Ionicons } from '@expo/vector-icons'

const TradeListItem = ({ trade }: { trade: Trade }) => {
    const pnl = Number(trade.pnl) || 0
    const pnlColor = pnl >= 0 ? '#4CAF50' : '#F44336'

    // Fallbacks for display
    const symbol = trade.symbol || trade.all_asset_symbol || trade.asset?.symbol || `Asset #${trade.asset?.id || trade.id}`
    const price = Number(trade.price) || 0
    const size = Number(trade.size || trade.quantity) || 0
    const date = trade.timestamp || trade.executed_at

    return (
        <View style={styles.tradeItem}>
            <View style={styles.topRow}>
                <View>
                    <Text style={styles.symbol}>{symbol}</Text>
                    <Text style={styles.date}>
                        {date ? new Date(date).toLocaleString('fr-FR') : 'Date N/A'}
                    </Text>
                </View>
                <View style={styles.rightAlign}>
                    <Text style={[styles.pnl, { color: pnlColor }]}>
                        {pnl > 0 ? '+' : ''}{pnl.toFixed(2)} €
                    </Text>
                    <Text style={[styles.side, { color: trade.side === 'BUY' ? '#2196F3' : '#FF9800' }]}>
                        {trade.side}
                    </Text>
                </View>
            </View>

            <View style={styles.detailsRow}>
                <Text style={styles.detailText}>
                    <Text style={styles.detailLabel}>Prix: </Text>
                    {price.toFixed(2)}
                </Text>
                <Text style={styles.detailText}>
                    <Text style={styles.detailLabel}>Qté: </Text>
                    {size}
                </Text>
                <Text style={styles.detailText}>
                    <Text style={styles.detailLabel}>Frais: </Text>
                    {Number(trade.fees || 0).toFixed(2)}
                </Text>
            </View>
        </View>
    )
}

export const TradesScreen = () => {
    const { trades, isLoading, refresh } = useTrades()

    return (
        <SafeAreaView style={styles.container}>
            <View style={styles.header}>
                <Text style={styles.title}>Historique des Trades</Text>
            </View>

            <ScrollView
                contentContainerStyle={styles.scrollContent}
                refreshControl={
                    <RefreshControl refreshing={isLoading} onRefresh={refresh} />
                }
            >
                {trades.length > 0 ? (
                    trades.map(trade => (
                        <Card key={trade.id} style={styles.card} padding={16}>
                            <TradeListItem trade={trade} />
                        </Card>
                    ))
                ) : (
                    <View style={styles.emptyState}>
                        <Ionicons name="list-outline" size={48} color="#9E9E9E" />
                        <Text style={styles.emptyText}>Aucun trade récent</Text>
                    </View>
                )}
            </ScrollView>
        </SafeAreaView>
    )
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#F5F5F5',
    },
    header: {
        padding: 16,
        paddingBottom: 8,
        backgroundColor: '#fff',
        borderBottomWidth: 1,
        borderBottomColor: '#eee',
    },
    title: {
        fontSize: 24,
        fontWeight: 'bold',
        color: '#333',
    },
    scrollContent: {
        padding: 16,
    },
    card: {
        marginBottom: 12,
    },
    tradeItem: {
        gap: 8,
    },
    topRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
    },
    symbol: {
        fontSize: 16,
        fontWeight: 'bold',
        color: '#333',
    },
    date: {
        fontSize: 12,
        color: '#757575',
        marginTop: 2,
    },
    rightAlign: {
        alignItems: 'flex-end',
    },
    pnl: {
        fontSize: 16,
        fontWeight: 'bold',
    },
    side: {
        fontSize: 12,
        fontWeight: 'bold',
        marginTop: 2,
    },
    detailsRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        paddingTop: 8,
        marginTop: 4,
        borderTopWidth: 1,
        borderTopColor: '#f0f0f0',
    },
    detailText: {
        fontSize: 13,
        color: '#333',
    },
    detailLabel: {
        color: '#757575',
    },
    emptyState: {
        alignItems: 'center',
        justifyContent: 'center',
        padding: 40,
        marginTop: 40,
    },
    emptyText: {
        marginTop: 16,
        color: '#9E9E9E',
        fontSize: 16,
    }
})
