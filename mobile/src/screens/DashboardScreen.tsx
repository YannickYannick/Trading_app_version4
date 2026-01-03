import React from 'react'
import { View, Text, StyleSheet, ScrollView, RefreshControl } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { useFocusEffect } from '@react-navigation/native'
import { useDashboardData } from '../hooks/useDashboardData'
import { Card } from '../components/common/Card'
import { useAuth } from '../hooks/useAuth'

// Composant pour un widget de stat
const StatWidget = ({ label, value, color }: { label: string, value: string, color?: string }) => (
    <View style={styles.statWidget}>
        <Text style={styles.statLabel}>{label}</Text>
        <Text style={[styles.statValue, color ? { color } : null]}>{value}</Text>
    </View>
)

// Composant pour un trade de la liste
const TradeItem = ({ trade }: { trade: any }) => {
    const isProfit = trade.pnl && trade.pnl > 0
    const pnlColor = isProfit ? '#4CAF50' : (trade.pnl < 0 ? '#F44336' : '#757575')

    return (
        <View style={styles.tradeItem}>
            <View>
                <Text style={styles.tradeSymbol}>{trade.symbol || trade.all_asset_symbol || trade.asset?.symbol || `Asset #${trade.id}`}</Text>
                <Text style={styles.tradeDate}>{trade.timestamp ? new Date(trade.timestamp).toLocaleDateString() : 'Date N/A'}</Text>
            </View>
            <View style={{ alignItems: 'flex-end' }}>
                <Text style={[styles.tradeSide, { color: trade.side === 'BUY' ? '#2196F3' : '#FF9800' }]}>
                    {trade.side}
                </Text>
                {trade.pnl !== undefined && (
                    <Text style={[styles.tradePnl, { color: pnlColor }]}>
                        {Number(trade.pnl) > 0 ? '+' : ''}{Number(trade.pnl).toFixed(2)} €
                    </Text>
                )}
            </View>
        </View>
    )
}

export const DashboardScreen = ({ navigation }: any) => {
    const { user } = useAuth()
    const { data, isLoading, error, refresh } = useDashboardData()

    useFocusEffect(
        React.useCallback(() => {
            refresh()
        }, [refresh])
    )

    return (
        <SafeAreaView style={styles.container}>
            <ScrollView
                contentContainerStyle={styles.scrollContent}
                refreshControl={
                    <RefreshControl refreshing={isLoading} onRefresh={refresh} />
                }
            >
                <View style={styles.header}>
                    <Text style={styles.greeting}>Bonjour, {user?.username || 'Trader'}</Text>
                    <Text style={styles.date}>{new Date().toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' })}</Text>
                </View>

                {/* Cartes de statistiques Principales */}
                <View style={[styles.statsRow, { marginBottom: 12 }]}>
                    <Card style={styles.statCard}>
                        <StatWidget
                            label="Mon Capital"
                            value={data ? `${Number(data.summary.total_capital || 0).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}` : '...'}
                            color="#2196F3"
                        />
                    </Card>
                    <Card style={styles.statCard}>
                        <StatWidget
                            label="PnL Total"
                            value={data ? `${Number(data.summary.total_pnl).toFixed(2) || '0.00'} €` : '...'}
                            color={data?.summary.total_pnl && data.summary.total_pnl >= 0 ? '#4CAF50' : '#F44336'}
                        />
                    </Card>
                </View>

                {/* Broker Breakdown - Horizontal Scroll */}
                {data?.brokerAccounts && data.brokerAccounts.length > 0 && (
                    <View style={{ marginBottom: 16 }}>
                        <Text style={styles.sectionTitle}>Mes Courtiers</Text>
                        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingRight: 16 }}>
                            {data.brokerAccounts.map((account: any, index: number) => (
                                <Card key={account.id || index} style={{ marginRight: 12, minWidth: 150 }} padding={16}>
                                    <View>
                                        <Text style={{ fontWeight: 'bold', fontSize: 16, marginBottom: 4, color: '#333' }}>{account.broker_type}</Text>
                                        <Text style={{ color: '#757575', fontSize: 12, marginBottom: 8 }}>{account.name}</Text>
                                        <Text style={{ fontSize: 18, fontWeight: 'bold', color: '#2196F3' }}>
                                            {Number(account.balance_eur || 0).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
                                        </Text>
                                    </View>
                                </Card>
                            ))}
                        </ScrollView>
                    </View>
                )}

                {/* Statistiques Secondaires */}
                <View style={styles.statsRow}>
                    <Card style={styles.statCard}>
                        <StatWidget
                            label="Win Rate"
                            value={data ? `${Number(data.summary.win_rate).toFixed(0)}%` : '...'}
                        />
                    </Card>
                    <Card style={styles.statCard}>
                        <StatWidget
                            label="Positions"
                            value={data ? (data.summary.open_positions_count?.toString() || '0') : '...'}
                        />
                    </Card>
                </View>

                <View style={styles.statsRow}>
                    <Card style={styles.statCard}>
                        <StatWidget
                            label="Total Trades"
                            value={data ? (data.summary.total_trades?.toString() || '0') : '...'}
                        />
                    </Card>
                    <View style={styles.statCard} />
                </View>

                {/* Trades récents */}
                <Text style={styles.sectionTitle}>Trades Récents</Text>
                <Card style={styles.recentTradesCard} padding={0}>
                    {data?.recentTrades && data.recentTrades.length > 0 ? (
                        data.recentTrades.map((trade, index) => (
                            <View key={trade.id || index}>
                                <View style={{ padding: 16 }}>
                                    <TradeItem trade={trade} />
                                </View>
                                {index < data.recentTrades.length - 1 && <View style={styles.divider} />}
                            </View>
                        ))
                    ) : (
                        <View style={{ padding: 16, alignItems: 'center' }}>
                            <Text style={{ color: '#999' }}>Aucun trade récent</Text>
                        </View>
                    )}
                </Card>
            </ScrollView>
        </SafeAreaView>
    )
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#F5F5F5',
    },
    scrollContent: {
        padding: 16,
    },
    header: {
        marginBottom: 24,
    },
    greeting: {
        fontSize: 24,
        fontWeight: 'bold',
        color: '#333',
    },
    date: {
        fontSize: 16,
        color: '#757575',
        textTransform: 'capitalize',
    },
    statsRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        marginBottom: 8,
    },
    statCard: {
        flex: 0.48,
        alignItems: 'center',
        paddingVertical: 20,
    },
    statWidget: {
        alignItems: 'center',
    },
    statLabel: {
        fontSize: 14,
        color: '#757575',
        marginBottom: 4,
    },
    statValue: {
        fontSize: 20,
        fontWeight: 'bold',
        color: '#333',
    },
    sectionTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#333',
        marginTop: 12,
        marginBottom: 12,
    },
    recentTradesCard: {
        overflow: 'hidden',
    },
    tradeItem: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    tradeSymbol: {
        fontWeight: 'bold',
        fontSize: 16,
        color: '#333',
    },
    tradeDate: {
        fontSize: 12,
        color: '#999',
        marginTop: 2,
    },
    tradeSide: {
        fontSize: 12,
        fontWeight: 'bold',
        textTransform: 'uppercase',
    },
    tradePnl: {
        fontWeight: 'bold',
        marginTop: 2,
    },
    divider: {
        height: 1,
        backgroundColor: '#EEEEEE',
    },
})
