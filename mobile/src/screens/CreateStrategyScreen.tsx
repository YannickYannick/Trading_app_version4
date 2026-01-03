import React, { useState, useEffect } from 'react'
import { View, Text, StyleSheet, ScrollView, Alert, TouchableOpacity, Modal, FlatList, Switch } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Input } from '../components/common/Input'
import { Button } from '../components/common/Button'
import { strategiesService, assetsService } from '../services/api'
import { Ionicons } from '@expo/vector-icons'
import { useNavigation } from '@react-navigation/native'
import type { AllAsset } from '@trading-app/shared'

const RISK_LEVELS = ['LOW', 'MEDIUM', 'HIGH']
const ALGO_TYPES = ['ma_crossover', 'macd', 'rsi', 'bollinger', 'threshold', 'grid']

export const CreateStrategyScreen = () => {
    const navigation = useNavigation()
    const [name, setName] = useState('')
    const [description, setDescription] = useState('')
    const [riskLevel, setRiskLevel] = useState('MEDIUM')
    const [algoType, setAlgoType] = useState('ma_crossover')
    const [isActive, setIsActive] = useState(false)
    const [maxPositionSize, setMaxPositionSize] = useState('1000')
    const [selectedAsset, setSelectedAsset] = useState<AllAsset | null>(null)

    // Asset Search State
    const [isAssetModalVisible, setAssetModalVisible] = useState(false)
    const [assetSearchQuery, setAssetSearchQuery] = useState('')
    const [searchResults, setSearchResults] = useState<AllAsset[]>([])
    const [isSearching, setIsSearching] = useState(false)

    const [isLoading, setIsLoading] = useState(false)

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

    const handleCreate = async () => {
        if (!name.trim()) {
            Alert.alert('Erreur', 'Le nom est obligatoire')
            return
        }
        if (!selectedAsset) {
            Alert.alert('Erreur', 'Vous devez sélectionner un actif')
            return
        }

        try {
            setIsLoading(true)
            await strategiesService.create({
                name,
                description,
                risk_level: riskLevel as any,
                is_active: isActive,
                all_asset_id: selectedAsset.id,
                strategy_type: 'TECHNICAL', // Default
                algorithm_type: algoType,
                parameters: {
                    max_position_size: Number(maxPositionSize)
                }
            })
            Alert.alert('Succès', 'Stratégie créée avec succès', [
                { text: 'OK', onPress: () => navigation.goBack() }
            ])
        } catch (error: any) {
            console.error(error)
            const msg = error.response?.data?.error || error.response?.data?.detail || 'Impossible de créer la stratégie'
            Alert.alert('Erreur', typeof msg === 'string' ? msg : JSON.stringify(msg))
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <SafeAreaView style={styles.container}>
            <View style={styles.header}>
                <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backButton}>
                    <Ionicons name="close" size={24} color="#333" />
                </TouchableOpacity>
                <Text style={styles.title}>Nouvelle Stratégie</Text>
            </View>

            <ScrollView contentContainerStyle={styles.content}>
                {/* Section Informations Générales */}
                <Text style={styles.sectionHeader}>Informations</Text>
                <Input
                    label="Nom"
                    value={name}
                    onChangeText={setName}
                    placeholder="Ex: Apple Moving Average"
                />
                <Input
                    label="Description"
                    value={description}
                    onChangeText={setDescription}
                    placeholder="Description courte..."
                    multiline
                    numberOfLines={2}
                />

                {/* Section Actif */}
                <Text style={[styles.sectionHeader, { marginTop: 20 }]}>Actif Cible</Text>
                <TouchableOpacity
                    style={styles.assetSelector}
                    onPress={() => {
                        setAssetModalVisible(true)
                        searchAssets() // Load initial list
                    }}
                >
                    {selectedAsset ? (
                        <View>
                            <Text style={styles.assetSelectorSymbol}>{selectedAsset.symbol}</Text>
                            <Text style={styles.assetSelectorName}>{selectedAsset.name}</Text>
                        </View>
                    ) : (
                        <Text style={styles.assetSelectorPlaceholder}>Sélectionner un actif...</Text>
                    )}
                    <Ionicons name="chevron-forward" size={20} color="#999" />
                </TouchableOpacity>

                {/* Section Paramètres */}
                <Text style={[styles.sectionHeader, { marginTop: 20 }]}>Paramètres</Text>

                <Text style={styles.label}>Algorithme</Text>
                <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipsScroll}>
                    {ALGO_TYPES.map(algo => (
                        <TouchableOpacity
                            key={algo}
                            style={[
                                styles.chip,
                                algoType === algo && styles.chipActive
                            ]}
                            onPress={() => setAlgoType(algo)}
                        >
                            <Text style={[styles.chipText, algoType === algo && styles.chipTextActive]}>
                                {algo.toUpperCase().replace('_', ' ')}
                            </Text>
                        </TouchableOpacity>
                    ))}
                </ScrollView>

                <Text style={styles.label}>Niveau de risque</Text>
                <View style={styles.riskContainer}>
                    {RISK_LEVELS.map((level) => (
                        <TouchableOpacity
                            key={level}
                            style={[
                                styles.riskButton,
                                riskLevel === level && styles.riskButtonActive,
                                { borderColor: getRiskColor(level) }
                            ]}
                            onPress={() => setRiskLevel(level)}
                        >
                            <Text style={[
                                styles.riskText,
                                riskLevel === level && styles.riskTextActive,
                                { color: riskLevel === level ? '#fff' : getRiskColor(level) }
                            ]}>
                                {level}
                            </Text>
                        </TouchableOpacity>
                    ))}
                </View>

                <Input
                    label="Taille Pos. Max (€)"
                    value={maxPositionSize}
                    onChangeText={setMaxPositionSize}
                    keyboardType="numeric"
                    placeholder="1000"
                />

                <View style={styles.switchRow}>
                    <Text style={styles.switchLabel}>Activer immédiatement</Text>
                    <Switch value={isActive} onValueChange={setIsActive} />
                </View>

                <View style={styles.spacer} />

                <Button
                    title="Créer la stratégie"
                    onPress={handleCreate}
                    loading={isLoading}
                />
            </ScrollView>

            {/* Modal de sélection d'actif */}
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
                            style={{ flex: 1, marginBottom: 0 }} // Override marginBottom
                        />
                    </View>
                    <FlatList
                        data={searchResults}
                        keyExtractor={(item) => item.id.toString()}
                        renderItem={({ item }) => (
                            <TouchableOpacity
                                style={styles.modalItem}
                                onPress={() => {
                                    setSelectedAsset(item)
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
        </SafeAreaView>
    )
}

const getRiskColor = (level: string) => {
    switch (level) {
        case 'LOW': return '#4CAF50'
        case 'MEDIUM': return '#FF9800'
        case 'HIGH': return '#F44336'
        default: return '#9E9E9E'
    }
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#fff',
    },
    header: {
        flexDirection: 'row',
        alignItems: 'center',
        padding: 16,
        borderBottomWidth: 1,
        borderBottomColor: '#eee',
    },
    backButton: {
        marginRight: 16,
    },
    title: {
        fontSize: 20,
        fontWeight: 'bold',
        color: '#333',
    },
    content: {
        padding: 16,
    },
    sectionHeader: {
        fontSize: 18,
        fontWeight: 'bold',
        marginTop: 8,
        marginBottom: 12,
        color: '#333',
    },
    label: {
        fontSize: 14,
        fontWeight: '500',
        color: '#333',
        marginBottom: 8,
        marginTop: 8,
    },
    riskContainer: {
        flexDirection: 'row',
        gap: 12,
        marginBottom: 16,
    },
    riskButton: {
        flex: 1,
        paddingVertical: 10,
        borderWidth: 1,
        borderRadius: 8,
        alignItems: 'center',
        justifyContent: 'center',
    },
    riskButtonActive: {
        backgroundColor: '#333',
        borderWidth: 0,
    },
    riskText: {
        fontWeight: 'bold',
        fontSize: 12,
    },
    riskTextActive: {
        color: '#fff',
    },
    spacer: {
        height: 32,
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
    chipsScroll: {
        flexDirection: 'row',
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
    switchRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginTop: 8,
        marginBottom: 16,
    },
    switchLabel: {
        fontSize: 16,
        color: '#333',
    }
})
