import React from 'react'
import { View, Text, StyleSheet, ScrollView, RefreshControl } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { usePositions } from '../hooks/usePositions'
import { Card } from '../components/common/Card'
import type { Position } from '@trading-app/shared'
import { Ionicons } from '@expo/vector-icons'

const PositionItem = ({ position }: { position: Position }) => {
    // Ensure pnl is a number
    const rawPnl = position.pnl;
    const pnl = typeof rawPnl === 'string' ? parseFloat(rawPnl) : (Number(rawPnl) || 0)
    const pnlColor = pnl >= 0 ? '#4CAF50' : '#F44336'

    // Fallbacks for display
    const symbol = position.all_asset_symbol || position.asset?.symbol || `Asset #${position.asset?.id || position.id}`
    const qty = Number(position.size) || 0
    const entryPrice = Number(position.entry_price) || 0
    const currentPrice = Number(position.current_price || position.yahoo_current_price) || entryPrice

    return (
        <View style={styles.positionItem}>
            <View style={styles.topRow}>
                <View>
                    <Text style={styles.symbol}>{symbol}</Text>
                    <Text style={[styles.side, { color: position.side === 'BUY' ? '#2196F3' : '#FF9800' }]}>
                        {position.side}
                    </Text>
                </View>
                <View style={styles.rightAlign}>
                    <Text style={[styles.pnl, { color: pnlColor }]}>
                        {pnl >= 0 ? '+' : ''}{pnl.toFixed(2)} €
                    </Text>
                    {(() => {
                        const rawPercent = position.pnl_percent;
                        const percentage = typeof rawPercent === 'string' ? parseFloat(rawPercent) : (Number(rawPercent) || 0);
                        return (
                            <Text style={[styles.pnlPercent, { color: pnlColor }]}>
                                {percentage ? `${percentage > 0 ? '+' : ''}${percentage.toFixed(2)}%` : '0.00%'}
                            </Text>
                        );
                    })()}
                </View>
            </View>

            <View style={styles.detailsRow}>
                <View style={styles.detailItem}>
                    <Text style={styles.detailLabel}>Qté</Text>
                    <Text style={styles.detailValue}>{qty}</Text>
                </View>
                <View style={styles.detailItem}>
                    <Text style={styles.detailLabel}>Entrée</Text>
                    <Text style={styles.detailValue}>{entryPrice.toFixed(2)}</Text>
                </View>
                <View style={styles.detailItem}>
                    <Text style={styles.detailLabel}>Actuel</Text>
                    <Text style={styles.detailValue}>{currentPrice.toFixed(2)}</Text>
                </View>
            </View>
        </View>
    )
}

export const PositionsScreen = () => {
    const { positions, isLoading, refresh } = usePositions()

    return (
        <SafeAreaView style={styles.container}>
            <View style={styles.header}>
                <Text style={styles.title}>Positions Ouvertes</Text>
            </View>

            <ScrollView
                contentContainerStyle={styles.scrollContent}
                refreshControl={
                    <RefreshControl refreshing={isLoading} onRefresh={refresh} />
                }
            >
                {positions.length > 0 ? (
                    positions.map(position => (
                        <Card key={position.id} style={styles.card} padding={16}>
                            <PositionItem position={position} />
                        </Card>
                    ))
                ) : (
                    <View style={styles.emptyState}>
                        <Ionicons name="briefcase-outline" size={48} color="#9E9E9E" />
                        <Text style={styles.emptyText}>Aucune position ouverte</Text>
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
    positionItem: {
        gap: 12,
    },
    topRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
    },
    symbol: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#333',
    },
    side: {
        fontSize: 12,
        fontWeight: 'bold',
        marginTop: 2,
    },
    rightAlign: {
        alignItems: 'flex-end',
    },
    pnl: {
        fontSize: 18,
        fontWeight: 'bold',
    },
    pnlPercent: {
        fontSize: 12,
        marginTop: 2,
    },
    detailsRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        paddingTop: 12,
        borderTopWidth: 1,
        borderTopColor: '#f0f0f0',
    },
    detailItem: {
        alignItems: 'center',
    },
    detailLabel: {
        fontSize: 11,
        color: '#757575',
        marginBottom: 2,
        textTransform: 'uppercase',
    },
    detailValue: {
        fontSize: 14,
        fontWeight: '600',
        color: '#333',
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
