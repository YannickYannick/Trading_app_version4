import React, { useState } from 'react'
import {
    View,
    Text,
    StyleSheet,
    Modal,
    TouchableOpacity,
    TextInput,
    Linking,
    ScrollView,
    ActivityIndicator,
    Alert,
} from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { Button } from './common/Button'
import { brokersService } from '../services/api'
import type { BrokerAccount } from '@trading-app/shared'

interface SaxoOAuthModalProps {
    visible: boolean
    account: BrokerAccount
    onSuccess: () => void
    onClose: () => void
}

type Step = 'start' | 'code' | 'success'

export const SaxoOAuthModal: React.FC<SaxoOAuthModalProps> = ({
    visible,
    account,
    onSuccess,
    onClose,
}) => {
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [step, setStep] = useState<Step>('start')
    const [authUrl, setAuthUrl] = useState<string | null>(null)
    const [code, setCode] = useState('')
    const [state, setState] = useState<string | null>(null)

    const handleGetAuthUrl = async () => {
        setLoading(true)
        setError(null)

        try {
            const response = await brokersService.getSaxoAuthUrl(account.id)
            if (response.auth_url) {
                setAuthUrl(response.auth_url)
                setState(response.state || null)
                setStep('code')
                // Open URL in external browser
                await Linking.openURL(response.auth_url)
            } else {
                setError("Impossible d'obtenir l'URL d'authentification")
            }
        } catch (err: any) {
            setError(err.error || err.message || "Erreur lors de la récupération de l'URL")
        } finally {
            setLoading(false)
        }
    }

    const handleExchangeCode = async () => {
        if (!code.trim()) {
            setError("Veuillez entrer le code d'autorisation")
            return
        }

        setLoading(true)
        setError(null)

        try {
            // Extract code from URL if necessary
            let authCode = code.trim()
            try {
                const url = new URL(authCode)
                const codeParam = url.searchParams.get('code')
                if (codeParam) {
                    authCode = codeParam
                }
            } catch {
                // Not a URL, use code as-is
            }

            await brokersService.exchangeSaxoAuthCode(account.id, authCode, state || undefined)
            setStep('success')
            setTimeout(() => {
                onSuccess()
                handleClose()
            }, 2000)
        } catch (err: any) {
            setError(err.error || err.message || "Erreur lors de l'échange du code")
        } finally {
            setLoading(false)
        }
    }

    const handleClose = () => {
        setStep('start')
        setCode('')
        setAuthUrl(null)
        setState(null)
        setError(null)
        onClose()
    }

    const hasTokens = account.saxo_access_token || account.saxo_refresh_token
    const tokenExpiresAt = account.saxo_token_expires_at
        ? new Date(account.saxo_token_expires_at)
        : null
    const isTokenExpired = tokenExpiresAt ? tokenExpiresAt < new Date() : false

    return (
        <Modal
            visible={visible}
            animationType="slide"
            presentationStyle="pageSheet"
            onRequestClose={handleClose}
        >
            <View style={styles.container}>
                {/* Header */}
                <View style={styles.header}>
                    <TouchableOpacity onPress={handleClose} style={styles.closeButton}>
                        <Ionicons name="close" size={24} color="#333" />
                    </TouchableOpacity>
                    <View style={styles.headerContent}>
                        <Ionicons name="shield-checkmark" size={24} color="#2196F3" />
                        <Text style={styles.headerTitle}>Authentification Saxo</Text>
                    </View>
                    {hasTokens && (
                        <View
                            style={[
                                styles.badge,
                                { backgroundColor: isTokenExpired ? '#FFF3CD' : '#D4EDDA' },
                            ]}
                        >
                            <Text
                                style={{
                                    color: isTokenExpired ? '#856404' : '#155724',
                                    fontSize: 10,
                                    fontWeight: 'bold',
                                }}
                            >
                                {isTokenExpired ? 'EXPIRÉ' : 'ACTIF'}
                            </Text>
                        </View>
                    )}
                </View>

                {/* Progress Steps */}
                <View style={styles.steps}>
                    <View style={styles.stepItem}>
                        <View
                            style={[
                                styles.stepCircle,
                                step === 'start' && styles.stepCircleActive,
                                step !== 'start' && styles.stepCircleCompleted,
                            ]}
                        >
                            <Text style={styles.stepNumber}>1</Text>
                        </View>
                        <Text style={styles.stepLabel}>Obtenir URL</Text>
                    </View>
                    <View
                        style={[
                            styles.stepConnector,
                            (step === 'code' || step === 'success') && styles.stepConnectorActive,
                        ]}
                    />
                    <View style={styles.stepItem}>
                        <View
                            style={[
                                styles.stepCircle,
                                step === 'code' && styles.stepCircleActive,
                                step === 'success' && styles.stepCircleCompleted,
                            ]}
                        >
                            <Text style={styles.stepNumber}>2</Text>
                        </View>
                        <Text style={styles.stepLabel}>Échanger code</Text>
                    </View>
                    <View
                        style={[
                            styles.stepConnector,
                            step === 'success' && styles.stepConnectorActive,
                        ]}
                    />
                    <View style={styles.stepItem}>
                        <View
                            style={[
                                styles.stepCircle,
                                step === 'success' && styles.stepCircleActive,
                            ]}
                        >
                            <Text style={styles.stepNumber}>3</Text>
                        </View>
                        <Text style={styles.stepLabel}>Terminé</Text>
                    </View>
                </View>

                <ScrollView style={styles.content} contentContainerStyle={styles.contentContainer}>
                    {/* Step 1: Get Auth URL */}
                    {step === 'start' && (
                        <View style={styles.stepContent}>
                            <View style={styles.infoCard}>
                                <Ionicons name="link" size={32} color="#2196F3" />
                                <Text style={styles.infoTitle}>
                                    Étape 1 : Obtenir l'URL d'authentification
                                </Text>
                                <Text style={styles.infoText}>
                                    Cliquez sur le bouton ci-dessous pour générer l'URL
                                    d'authentification Saxo Bank. Votre navigateur s'ouvrira
                                    automatiquement.
                                </Text>
                            </View>

                            {error && (
                                <View style={styles.errorCard}>
                                    <Ionicons name="alert-circle" size={20} color="#D32F2F" />
                                    <Text style={styles.errorText}>{error}</Text>
                                </View>
                            )}

                            <Button
                                title={loading ? "Génération..." : "Obtenir l'URL d'authentification"}
                                onPress={handleGetAuthUrl}
                                loading={loading}
                                icon={<Ionicons name="open-outline" size={18} color="#FFF" />}
                                style={{ marginTop: 16 }}
                            />

                            {hasTokens && (
                                <View style={styles.tokensInfo}>
                                    <View style={styles.tokensHeader}>
                                        <Ionicons name="key" size={18} color="#666" />
                                        <Text style={styles.tokensTitle}>Tokens actuels</Text>
                                    </View>
                                    <View style={styles.tokensList}>
                                        <View style={styles.tokenItem}>
                                            <Text style={styles.tokenLabel}>Access Token:</Text>
                                            <Text
                                                style={[
                                                    styles.tokenValue,
                                                    { color: account.saxo_access_token ? '#4CAF50' : '#999' },
                                                ]}
                                            >
                                                {account.saxo_access_token ? 'Présent' : 'Absent'}
                                            </Text>
                                        </View>
                                        <View style={styles.tokenItem}>
                                            <Text style={styles.tokenLabel}>Refresh Token:</Text>
                                            <Text
                                                style={[
                                                    styles.tokenValue,
                                                    { color: account.saxo_refresh_token ? '#4CAF50' : '#999' },
                                                ]}
                                            >
                                                {account.saxo_refresh_token ? 'Présent' : 'Absent'}
                                            </Text>
                                        </View>
                                        {tokenExpiresAt && (
                                            <View style={styles.tokenItem}>
                                                <Text style={styles.tokenLabel}>
                                                    <Ionicons name="time" size={12} /> Expiration:
                                                </Text>
                                                <Text
                                                    style={[
                                                        styles.tokenValue,
                                                        { color: isTokenExpired ? '#F44336' : '#666' },
                                                    ]}
                                                >
                                                    {tokenExpiresAt.toLocaleString('fr-FR', {
                                                        day: '2-digit',
                                                        month: '2-digit',
                                                        year: 'numeric',
                                                        hour: '2-digit',
                                                        minute: '2-digit',
                                                    })}
                                                </Text>
                                            </View>
                                        )}
                                    </View>
                                </View>
                            )}
                        </View>
                    )}

                    {/* Step 2: Exchange Code */}
                    {step === 'code' && (
                        <View style={styles.stepContent}>
                            <View style={styles.infoCard}>
                                <Ionicons name="key" size={32} color="#2196F3" />
                                <Text style={styles.infoTitle}>
                                    Étape 2 : Échanger le code d'autorisation
                                </Text>
                                <Text style={styles.infoText}>
                                    Après vous être connecté sur Saxo Bank, copiez le code
                                    d'autorisation depuis l'URL de redirection et collez-le
                                    ci-dessous.
                                </Text>
                            </View>

                            {error && (
                                <View style={styles.errorCard}>
                                    <Ionicons name="alert-circle" size={20} color="#D32F2F" />
                                    <Text style={styles.errorText}>{error}</Text>
                                </View>
                            )}

                            <View style={styles.inputContainer}>
                                <Text style={styles.inputLabel}>Code d'autorisation</Text>
                                <TextInput
                                    style={styles.input}
                                    value={code}
                                    onChangeText={(text) => {
                                        setCode(text)
                                        setError(null)
                                    }}
                                    placeholder="Collez le code ou l'URL complète"
                                    placeholderTextColor="#999"
                                    multiline
                                    numberOfLines={3}
                                    autoCapitalize="none"
                                    autoCorrect={false}
                                />
                                <Text style={styles.inputHint}>
                                    💡 Vous pouvez coller l'URL complète, le code sera extrait
                                    automatiquement
                                </Text>
                            </View>

                            <View style={styles.buttonRow}>
                                <Button
                                    title="Retour"
                                    onPress={() => {
                                        setStep('start')
                                        setCode('')
                                        setError(null)
                                    }}
                                    variant="outline"
                                    style={{ flex: 1, marginRight: 8 }}
                                    icon={<Ionicons name="arrow-back" size={18} color="#2196F3" />}
                                />
                                <Button
                                    title={loading ? "Échange..." : "Échanger le code"}
                                    onPress={handleExchangeCode}
                                    loading={loading}
                                    disabled={!code.trim()}
                                    style={{ flex: 1, marginLeft: 8 }}
                                    icon={<Ionicons name="refresh" size={18} color="#FFF" />}
                                />
                            </View>
                        </View>
                    )}

                    {/* Step 3: Success */}
                    {step === 'success' && (
                        <View style={styles.stepContent}>
                            <View style={styles.successCard}>
                                <Ionicons name="checkmark-circle" size={64} color="#4CAF50" />
                                <Text style={styles.successTitle}>Authentification réussie !</Text>
                                <Text style={styles.successText}>
                                    Les tokens d'authentification ont été sauvegardés avec succès.
                                </Text>
                                <Text style={styles.successHint}>
                                    La fenêtre se fermera automatiquement...
                                </Text>
                            </View>
                        </View>
                    )}
                </ScrollView>
            </View>
        </Modal>
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
    },
    closeButton: {
        padding: 4,
    },
    headerContent: {
        flex: 1,
        flexDirection: 'row',
        alignItems: 'center',
        marginLeft: 12,
    },
    headerTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#333',
        marginLeft: 8,
    },
    badge: {
        paddingHorizontal: 8,
        paddingVertical: 4,
        borderRadius: 4,
    },
    steps: {
        flexDirection: 'row',
        alignItems: 'center',
        padding: 16,
        backgroundColor: '#FFF',
        borderBottomWidth: 1,
        borderBottomColor: '#EEE',
    },
    stepItem: {
        alignItems: 'center',
    },
    stepCircle: {
        width: 32,
        height: 32,
        borderRadius: 16,
        backgroundColor: '#E0E0E0',
        justifyContent: 'center',
        alignItems: 'center',
        marginBottom: 4,
    },
    stepCircleActive: {
        backgroundColor: '#2196F3',
    },
    stepCircleCompleted: {
        backgroundColor: '#4CAF50',
    },
    stepNumber: {
        color: '#FFF',
        fontSize: 14,
        fontWeight: 'bold',
    },
    stepLabel: {
        fontSize: 10,
        color: '#666',
    },
    stepConnector: {
        flex: 1,
        height: 2,
        backgroundColor: '#E0E0E0',
        marginHorizontal: 8,
    },
    stepConnectorActive: {
        backgroundColor: '#4CAF50',
    },
    content: {
        flex: 1,
    },
    contentContainer: {
        padding: 16,
    },
    stepContent: {
        flex: 1,
    },
    infoCard: {
        backgroundColor: '#E3F2FD',
        borderRadius: 8,
        padding: 16,
        alignItems: 'center',
    },
    infoTitle: {
        fontSize: 16,
        fontWeight: 'bold',
        color: '#333',
        marginTop: 12,
        textAlign: 'center',
    },
    infoText: {
        fontSize: 14,
        color: '#666',
        marginTop: 8,
        textAlign: 'center',
        lineHeight: 20,
    },
    errorCard: {
        backgroundColor: '#FFEBEE',
        borderRadius: 8,
        padding: 12,
        flexDirection: 'row',
        alignItems: 'center',
        marginTop: 16,
    },
    errorText: {
        fontSize: 14,
        color: '#D32F2F',
        marginLeft: 8,
        flex: 1,
    },
    tokensInfo: {
        marginTop: 24,
        backgroundColor: '#FFF',
        borderRadius: 8,
        padding: 16,
    },
    tokensHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 12,
    },
    tokensTitle: {
        fontSize: 14,
        fontWeight: 'bold',
        color: '#666',
        marginLeft: 8,
    },
    tokensList: {
        gap: 8,
    },
    tokenItem: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: 4,
    },
    tokenLabel: {
        fontSize: 14,
        color: '#666',
    },
    tokenValue: {
        fontSize: 14,
        fontWeight: 'bold',
    },
    inputContainer: {
        marginTop: 16,
    },
    inputLabel: {
        fontSize: 14,
        fontWeight: 'bold',
        color: '#333',
        marginBottom: 8,
    },
    input: {
        backgroundColor: '#FFF',
        borderWidth: 1,
        borderColor: '#DDD',
        borderRadius: 8,
        padding: 12,
        fontSize: 14,
        color: '#333',
        textAlignVertical: 'top',
    },
    inputHint: {
        fontSize: 12,
        color: '#999',
        marginTop: 8,
    },
    buttonRow: {
        flexDirection: 'row',
        marginTop: 24,
    },
    successCard: {
        backgroundColor: '#FFF',
        borderRadius: 8,
        padding: 32,
        alignItems: 'center',
    },
    successTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#4CAF50',
        marginTop: 16,
    },
    successText: {
        fontSize: 14,
        color: '#666',
        marginTop: 8,
        textAlign: 'center',
    },
    successHint: {
        fontSize: 12,
        color: '#999',
        marginTop: 16,
    },
})
