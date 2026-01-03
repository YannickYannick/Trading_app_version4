import React from 'react'
import { View, Text, StyleSheet, ScrollView, RefreshControl, TouchableOpacity } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { useStrategies } from '../hooks/useStrategies'
import { Card } from '../components/common/Card'
import type { Strategy } from '@trading-app/shared'
import { Ionicons } from '@expo/vector-icons'

const StrategyItem = ({ strategy, onPress, onToggle }: { strategy: Strategy, onPress: (s: Strategy) => void, onToggle: (id: number, active: boolean) => void }) => {
    return (
        <TouchableOpacity style={styles.strategyItem} onPress={() => onPress(strategy)}>
            <View style={styles.strategyHeader}>
                <View style={{ flex: 1 }}>
                    <Text style={styles.strategyName}>{strategy.name}</Text>
                    <Text style={styles.strategyAsset}>{strategy.all_asset_symbol || 'No Asset'}</Text>
                </View>
                <TouchableOpacity
                    onPress={() => onToggle(strategy.id, !strategy.is_active)}
                    style={[styles.statusBadge, { backgroundColor: strategy.is_active ? '#E8F5E9' : '#FFEBEE' }]}
                >
                    <Text style={[styles.statusText, { color: strategy.is_active ? '#4CAF50' : '#F44336' }]}>
                        {strategy.is_active ? 'ACTIF' : 'INACTIF'}
                    </Text>
                </TouchableOpacity>
            </View>

            <Text style={styles.description} numberOfLines={2}>
                {strategy.description || 'Aucune description'}
            </Text>

            <View style={styles.parametersContainer}>
                <View style={styles.paramTag}>
                    <Text style={styles.paramLabel}>Risque: {strategy.risk_level || 'N/A'}</Text>
                </View>
                <View style={styles.paramTag}>
                    <Text style={styles.paramLabel}>Budget: {strategy.budget || 0} €</Text>
                </View>
            </View>
        </TouchableOpacity>
    )
}

export const StrategiesScreen = (props: any) => {
    const { strategies, isLoading, refresh, toggleStrategy } = useStrategies()

    const handlePress = (strategy: Strategy) => {
        (props.navigation as any).navigate('StrategyEdit', { strategy })
    }

    return (
        <SafeAreaView style={styles.container}>
            <View style={styles.header}>
                <Text style={styles.title}>Stratégies</Text>
                <TouchableOpacity
                    onPress={() => (props.navigation as any).navigate('CreateStrategy')}
                    style={styles.addButton}
                >
                    <Ionicons name="add" size={24} color="#000" />
                </TouchableOpacity>
            </View>

            <ScrollView
                contentContainerStyle={styles.scrollContent}
                refreshControl={
                    <RefreshControl refreshing={isLoading} onRefresh={refresh} />
                }
            >
                {strategies.length > 0 ? (
                    strategies.map(strategy => (
                        <Card key={strategy.id} style={styles.card} padding={16}>
                            <StrategyItem strategy={strategy} onPress={handlePress} onToggle={toggleStrategy} />
                        </Card>
                    ))
                ) : (
                    <View style={styles.emptyState}>
                        <Ionicons name="bulb-outline" size={48} color="#9E9E9E" />
                        <Text style={styles.emptyText}>Aucune stratégie configurée</Text>
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
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    addButton: {
        padding: 8,
        backgroundColor: '#F5F5F5',
        borderRadius: 20,
    },
    title: {
        fontSize: 24,
        fontWeight: 'bold',
        color: '#333',
    },
    scrollContent: {
        padding: 16,
        paddingBottom: 100,
    },
    card: {
        marginBottom: 16,
    },
    strategyItem: {
        gap: 12,
    },
    strategyHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
    },
    strategyName: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#333',
        marginBottom: 4,
    },
    strategyAsset: {
        fontSize: 14,
        color: '#666',
        fontWeight: '600',
    },
    statusBadge: {
        paddingHorizontal: 8,
        paddingVertical: 4,
        borderRadius: 12,
    },
    statusText: {
        fontSize: 12,
        fontWeight: 'bold',
    },
    description: {
        fontSize: 14,
        color: '#757575',
        lineHeight: 20,
    },
    parametersContainer: {
        flexDirection: 'row',
        gap: 8,
        marginTop: 4,
    },
    paramTag: {
        backgroundColor: '#F5F5F5',
        paddingHorizontal: 8,
        paddingVertical: 4,
        borderRadius: 4,
    },
    paramLabel: {
        fontSize: 12,
        color: '#616161',
    },
    emptyState: {
        alignItems: 'center',
        justifyContent: 'center',
        padding: 40,
    },
    emptyText: {
        marginTop: 16,
        color: '#9E9E9E',
        fontSize: 16,
    }
})
