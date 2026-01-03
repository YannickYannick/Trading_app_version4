import React, { useState } from 'react'
import {
    View,
    Text,
    StyleSheet,
    KeyboardAvoidingView,
    Platform,
    TouchableWithoutFeedback,
    Keyboard,
    Image,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { useAuth } from '../../hooks/useAuth'
import { Button } from '../../components/common/Button'
import { Input } from '../../components/common/Input'

export const LoginScreen = () => {
    const { login, isLoading } = useAuth()

    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')

    const handleLogin = async () => {
        if (!username || !password) {
            setError('Veuillez remplir tous les champs')
            return
        }

        try {
            setError('')
            await login({ username, password })
        } catch (e: any) {
            console.error(e)
            setError('Identifiants incorrects ou problème de connexion')
        }
    }

    return (
        <SafeAreaView style={styles.container}>
            <KeyboardAvoidingView
                behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
                style={styles.keyboardView}
            >
                <TouchableWithoutFeedback onPress={Keyboard.dismiss}>
                    <View style={styles.content}>
                        <View style={styles.header}>
                            <Text style={styles.title}>Trading App</Text>
                            <Text style={styles.subtitle}>Connectez-vous pour continuer</Text>
                        </View>

                        <View style={styles.form}>
                            <Input
                                label="Nom d'utilisateur"
                                value={username}
                                onChangeText={setUsername}
                                autoCapitalize="none"
                                autoCorrect={false}
                                placeholder="Ex: trader123"
                            />

                            <Input
                                label="Mot de passe"
                                value={password}
                                onChangeText={setPassword}
                                secureTextEntry
                                placeholder="••••••••"
                                onSubmitEditing={handleLogin}
                            />

                            {error ? <Text style={styles.errorText}>{error}</Text> : null}

                            <Button
                                title="Se connecter"
                                onPress={handleLogin}
                                loading={isLoading}
                                style={styles.button}
                                size="lg"
                            />
                        </View>
                    </View>
                </TouchableWithoutFeedback>
            </KeyboardAvoidingView>
        </SafeAreaView>
    )
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#fff',
    },
    keyboardView: {
        flex: 1,
    },
    content: {
        flex: 1,
        padding: 24,
        justifyContent: 'center',
    },
    header: {
        alignItems: 'center',
        marginBottom: 48,
    },
    title: {
        fontSize: 32,
        fontWeight: 'bold',
        color: '#2196F3',
        marginBottom: 8,
    },
    subtitle: {
        fontSize: 16,
        color: '#666',
    },
    form: {
        width: '100%',
    },
    button: {
        marginTop: 16,
    },
    errorText: {
        color: '#F44336',
        marginBottom: 16,
        textAlign: 'center',
    },
})
