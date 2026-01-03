import React from 'react'
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, Alert } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { useAuth } from '../hooks/useAuth'
import { Ionicons } from '@expo/vector-icons'

export const SettingsScreen = ({ navigation }: any) => {
    const { user, logout } = useAuth()

    const handleLogout = () => {
        Alert.alert(
            'Déconnexion',
            'Êtes-vous sûr de vouloir vous déconnecter ?',
            [
                { text: 'Annuler', style: 'cancel' },
                { text: 'Déconnexion', style: 'destructive', onPress: logout }
            ]
        )
    }

    const MenuItem = ({ icon, label, onPress, color = '#333' }: any) => (
        <TouchableOpacity style={styles.menuItem} onPress={onPress}>
            <View style={styles.menuItemLeft}>
                <Ionicons name={icon} size={24} color={color} style={styles.menuIcon} />
                <Text style={[styles.menuLabel, { color }]}>{label}</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color="#CCC" />
        </TouchableOpacity>
    )

    return (
        <SafeAreaView style={styles.container} edges={['top']}>
            <View style={styles.header}>
                <Text style={styles.headerTitle}>Réglages</Text>
            </View>

            <ScrollView contentContainerStyle={styles.content}>
                <View style={styles.profileSection}>
                    <View style={styles.avatar}>
                        <Text style={styles.avatarText}>{user?.username?.charAt(0).toUpperCase() || 'U'}</Text>
                    </View>
                    <Text style={styles.username}>{user?.username || 'Utilisateur'}</Text>
                    <Text style={styles.email}>{user?.email || 'email@example.com'}</Text>
                </View>

                <View style={styles.section}>
                    <Text style={styles.sectionHeader}>Compte</Text>
                    <MenuItem
                        icon="card-outline"
                        label="Gérer les Courtiers"
                        onPress={() => navigation.navigate('BrokerManage')}
                    />
                    <MenuItem
                        icon="person-outline"
                        label="Profil"
                        onPress={() => Alert.alert('Info', 'Fonctionnalité à venir')}
                    />
                </View>

                <View style={styles.section}>
                    <Text style={styles.sectionHeader}>Application</Text>
                    <MenuItem
                        icon="notifications-outline"
                        label="Notifications"
                        onPress={() => Alert.alert('Info', 'Fonctionnalité à venir')}
                    />
                    <MenuItem
                        icon="help-circle-outline"
                        label="Aide & Support"
                        onPress={() => Alert.alert('Info', 'Fonctionnalité à venir')}
                    />
                </View>

                <View style={[styles.section, { marginTop: 24, borderTopWidth: 0 }]}>
                    <MenuItem
                        icon="log-out-outline"
                        label="Se déconnecter"
                        onPress={handleLogout}
                        color="#F44336"
                    />
                </View>
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
        backgroundColor: '#FFF',
        borderBottomWidth: 1,
        borderBottomColor: '#EEE',
    },
    headerTitle: {
        fontSize: 24,
        fontWeight: 'bold',
        color: '#333',
    },
    content: {
        paddingBottom: 40,
    },
    profileSection: {
        backgroundColor: '#FFF',
        padding: 24,
        alignItems: 'center',
        marginBottom: 24,
    },
    avatar: {
        width: 80,
        height: 80,
        borderRadius: 40,
        backgroundColor: '#E3F2FD',
        justifyContent: 'center',
        alignItems: 'center',
        marginBottom: 12,
    },
    avatarText: {
        fontSize: 32,
        fontWeight: 'bold',
        color: '#2196F3',
    },
    username: {
        fontSize: 20,
        fontWeight: 'bold',
        color: '#333',
        marginBottom: 4,
    },
    email: {
        fontSize: 14,
        color: '#757575',
    },
    section: {
        backgroundColor: '#FFF',
        paddingVertical: 8,
        borderTopWidth: 1,
        borderBottomWidth: 1,
        borderColor: '#EEE',
        marginBottom: 24,
    },
    sectionHeader: {
        fontSize: 14,
        fontWeight: 'bold',
        color: '#999',
        marginLeft: 16,
        marginBottom: 8,
        marginTop: 8,
        textTransform: 'uppercase',
    },
    menuItem: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingVertical: 12,
        paddingHorizontal: 16,
    },
    menuItemLeft: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    menuIcon: {
        marginRight: 16,
    },
    menuLabel: {
        fontSize: 16,
        color: '#333',
    },
})
