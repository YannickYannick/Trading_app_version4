import React, { useState, useEffect, useCallback } from 'react'
import { View, Text, StyleSheet, ScrollView, RefreshControl, Alert, Modal, TouchableOpacity } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Card } from '../components/common/Card'
import { Button } from '../components/common/Button'
import { brokersService } from '../services/api'
import { Ionicons } from '@expo/vector-icons'
import type { BrokerAccount } from '@trading-app/shared'

export const BrokerManageScreen = ({ navigation }: any) => {
    const [accounts, setAccounts] = useState<BrokerAccount[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [actionLoading, setActionLoading] = useState<number | null>(null) // ID of account being processed

    const loadAccounts = useCallback(async () => {
        try {
            setIsLoading(true)
            const response = await brokersService.getAccounts()
            setAccounts(response.results || [])
        } catch (error) {
            console.error('Error loading accounts:', error)
            Alert.alert('Erreur', 'Impossible de charger les comptes brokers')
        } finally {
            setIsLoading(false)
        }
    }, [])

    useEffect(() => {
        loadAccounts()
    }, [loadAccounts])

    const handleSync = async (accountId: number, type: 'ASSETS' | 'POSITIONS' | 'TRADES') => {
        try {
            setActionLoading(accountId)
            await brokersService.sync(accountId, { sync_type: type, force: true })
            Alert.alert('Succès', `Synchronisation ${type} lancée`)
        } catch (error) {
            console.error(`Error syncing ${type}:`, error)
            Alert.alert('Erreur', `Échec de la synchronisation ${type}`)
        } finally {
            setActionLoading(null)
        }
    }

    const handleRefreshSaxo = async (accountId: number) => {
        try {
            setActionLoading(accountId)
            await brokersService.refreshSaxoToken(accountId)
            Alert.alert('Succès', 'Token Saxo rafraîchi')
            loadAccounts() // Reload to update status if needed
        } catch (error) {
            console.error('Error refreshing Saxo token:', error)
            Alert.alert('Erreur', 'Impossible de rafraîchir le token Saxo')
        } finally {
            setActionLoading(null)
        }
    }

    const handleConnectNew = () => {
        // TODO: Implement connection flow (e.g. navigation to a form or Saxo OAuth)
        Alert.alert('Information', 'La connexion de nouveaux comptes sera bientôt disponible.')
    }

    const renderAccountCard = (account: BrokerAccount) => {
        const isSaxo = account.broker_type === 'SAXO'
        const isBinance = account.broker_type === 'BINANCE'

        return (
            <Card key={account.id} style={styles.card}>
                <View style={styles.cardHeader}>
                    <View style={styles.brokerIcon}>
                        <Ionicons name="card-outline" size={24} color="#2196F3" />
                    </View>
                    <View style={{ flex: 1, marginLeft: 12 }}>
                        <Text style={styles.brokerName}>{account.name}</Text>
                        <Text style={styles.brokerType}>{account.broker_type} • {account.environment}</Text>
                    </View>
                    <View style={[styles.statusBadge, { backgroundColor: account.is_active ? '#E8F5E9' : '#FFEBEE' }]}>
                        <Text style={{ color: account.is_active ? '#4CAF50' : '#F44336', fontSize: 10, fontWeight: 'bold' }}>
                            {account.is_active ? 'ACTIF' : 'INACTIF'}
                        </Text>
                    </View>
                </View>

                <View style={styles.balanceRow}>
                    <Text style={styles.balanceLabel}>Solde Actuel:</Text>
                    <Text style={styles.balanceValue}>
                        {Number(account.balance_eur || 0).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
                    </Text>
                </View>

                <View style={styles.divider} />

                <Text style={styles.actionsLabel}>Actions de synchronisation</Text>
                <View style={styles.actionsRow}>
                    <Button
                        title="Assets"
                        onPress={() => handleSync(account.id, 'ASSETS')}
                        variant="outline"
                        size="sm"
                        loading={actionLoading === account.id}
                        style={styles.actionButton}
                    />
                    <Button
                        title="Positions"
                        onPress={() => handleSync(account.id, 'POSITIONS')}
                        variant="outline"
                        size="sm"
                        loading={actionLoading === account.id}
                        style={styles.actionButton}
                    />
                    <Button
                        title="Trades"
                        onPress={() => handleSync(account.id, 'TRADES')}
                        variant="outline"
                        size="sm"
                        loading={actionLoading === account.id}
                        style={styles.actionButton}
                    />
                </View>

                {isSaxo && (
                    <View style={{ marginTop: 12 }}>
                        <Text style={styles.actionsLabel}>Gestion Saxo</Text>
                        <View style={styles.actionsRow}>
                            <Button
                                title="Refresh Token"
                                onPress={() => handleRefreshSaxo(account.id)}
                                variant="secondary"
                                size="sm"
                                loading={actionLoading === account.id}
                                style={styles.actionButton}
                            />
                        </View>
                    </View>
                )}
            </Card>
        )
    }

    return (
        <SafeAreaView style={styles.container} edges={['top']}>
            <View style={styles.header}>
                <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backButton}>
                    <Ionicons name="arrow-back" size={24} color="#333" />
                </TouchableOpacity>
                <Text style={styles.title}>Gestion des Courtiers</Text>
                <TouchableOpacity onPress={handleConnectNew} style={styles.addButton}>
                    <Ionicons name="add" size={24} color="#2196F3" />
                </TouchableOpacity>
            </View>

            <ScrollView
                contentContainerStyle={styles.content}
                refreshControl={<RefreshControl refreshing={isLoading} onRefresh={loadAccounts} />}
            >
                {accounts.length > 0 ? (
                    accounts.map(renderAccountCard)
                ) : (
                    <View style={styles.emptyState}>
                        <Text style={styles.emptyText}>Aucun compte courtier connecté.</Text>
                        <Button title="Connecter un compte" onPress={handleConnectNew} style={{ marginTop: 16 }} />
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
        flexDirection: 'row',
        alignItems: 'center',
        padding: 16,
        backgroundColor: '#FFF',
        borderBottomWidth: 1,
        borderBottomColor: '#EEE',
        justifyContent: 'space-between',
    },
    backButton: {
        padding: 4,
    },
    title: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#333',
    },
    addButton: {
        padding: 4,
    },
    content: {
        padding: 16,
    },
    card: {
        marginBottom: 16,
    },
    cardHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 16,
    },
    brokerIcon: {
        width: 40,
        height: 40,
        borderRadius: 20,
        backgroundColor: '#E3F2FD',
        justifyContent: 'center',
        alignItems: 'center',
    },
    brokerName: {
        fontSize: 16,
        fontWeight: 'bold',
        color: '#333',
    },
    brokerType: {
        fontSize: 12,
        color: '#757575',
        marginTop: 2,
    },
    statusBadge: {
        paddingHorizontal: 8,
        paddingVertical: 4,
        borderRadius: 4,
    },
    balanceRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 16,
    },
    balanceLabel: {
        fontSize: 14,
        color: '#757575',
    },
    balanceValue: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#333',
    },
    divider: {
        height: 1,
        backgroundColor: '#EEEEEE',
        marginBottom: 16,
    },
    actionsLabel: {
        fontSize: 12,
        fontWeight: 'bold',
        color: '#999',
        marginBottom: 8,
        textTransform: 'uppercase',
    },
    actionsRow: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        gap: 8,
    },
    actionButton: {
        marginRight: 8,
        marginBottom: 8,
        minWidth: 80,
    },
    emptyState: {
        alignItems: 'center',
        padding: 32,
    },
    emptyText: {
        color: '#757575',
        fontSize: 16,
    },
})
