import React from 'react'
import { NavigationContainer } from '@react-navigation/native'
import { createNativeStackNavigator } from '@react-navigation/native-stack'
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import { useAuth } from '../hooks/useAuth'

// Screens
import { LoginScreen } from '../screens/auth/LoginScreen'
import { DashboardScreen } from '../screens/DashboardScreen'
import { StrategiesScreen } from '../screens/StrategiesScreen'
import { PositionsScreen } from '../screens/PositionsScreen'
import { TradesScreen } from '../screens/TradesScreen'
import { CreateStrategyScreen } from '../screens/CreateStrategyScreen'
import { StrategyEditScreen } from '../screens/StrategyEditScreen'
import { SettingsScreen } from '../screens/SettingsScreen'
import { BrokerManageScreen } from '../screens/BrokerManageScreen'
import { View, Text } from 'react-native'
import { Ionicons } from '@expo/vector-icons'

// Stack Types
export type AuthStackParamList = {
    Login: undefined
    Register: undefined
}

export type RootStackParamList = {
    MainTab: undefined
    CreateStrategy: undefined
    StrategyEdit: { strategy: any }
    BrokerManage: undefined
    Login: undefined
}

const Stack = createNativeStackNavigator<RootStackParamList>()
const AuthStack = createNativeStackNavigator<AuthStackParamList>()
const Tab = createBottomTabNavigator()

const AuthNavigator = () => {
    return (
        <AuthStack.Navigator screenOptions={{ headerShown: false }}>
            <AuthStack.Screen name="Login" component={LoginScreen} />
        </AuthStack.Navigator>
    )
}

const MainNavigator = () => {
    const insets = useSafeAreaInsets()

    return (
        <Tab.Navigator
            screenOptions={{
                tabBarActiveTintColor: '#2196F3',
                tabBarInactiveTintColor: 'gray',
                headerShown: false,
                tabBarStyle: {
                    paddingBottom: Math.max(insets.bottom, 15),
                    height: 60 + Math.max(insets.bottom, 15),
                    paddingTop: 10,
                },
                tabBarLabelStyle: {
                    fontSize: 12,
                    marginBottom: 5,
                }
            }}
        >
            <Tab.Screen
                name="Dashboard"
                component={DashboardScreen}
                options={{
                    tabBarIcon: ({ color, size }) => (
                        <Ionicons name="grid-outline" size={size} color={color} />
                    ),
                }}
            />
            <Tab.Screen
                name="Strategies"
                component={StrategiesScreen}
                options={{
                    tabBarIcon: ({ color, size }) => (
                        <Ionicons name="bulb-outline" size={size} color={color} />
                    ),
                    title: 'Stratégies'
                }}
            />
            <Tab.Screen
                name="Positions"
                component={PositionsScreen}
                options={{
                    tabBarIcon: ({ color, size }) => (
                        <Ionicons name="briefcase-outline" size={size} color={color} />
                    ),
                    title: 'Positions'
                }}
            />
            <Tab.Screen
                name="Trades"
                component={TradesScreen}
                options={{
                    tabBarIcon: ({ color, size }) => (
                        <Ionicons name="list-outline" size={size} color={color} />
                    ),
                    title: 'Historique'
                }}
            />
            <Tab.Screen
                name="Settings"
                component={SettingsScreen}
                options={{
                    tabBarIcon: ({ color, size }) => (
                        <Ionicons name="settings-outline" size={size} color={color} />
                    ),
                    title: 'Réglages'
                }}
            />
        </Tab.Navigator>
    )
}

export const AppNavigator = () => {
    const { isAuthenticated, isLoading } = useAuth()

    if (isLoading) {
        return (
            <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
                <Text>Chargement...</Text>
            </View>
        )
    }

    return (
        <NavigationContainer>
            <Stack.Navigator screenOptions={{ headerShown: false }}>
                {isAuthenticated ? (
                    <>
                        <Stack.Screen name="MainTab" component={MainNavigator} />
                        <Stack.Screen
                            name="CreateStrategy"
                            component={CreateStrategyScreen}
                            options={{ presentation: 'modal' }}
                        />
                        <Stack.Screen
                            name="StrategyEdit"
                            component={StrategyEditScreen}
                            options={{ headerShown: false }}
                        />
                        <Stack.Screen
                            name="BrokerManage"
                            component={BrokerManageScreen}
                            options={{ headerShown: false }}
                        />
                    </>
                ) : (
                    <Stack.Screen name="Login" component={LoginScreen} />
                )}
            </Stack.Navigator>
        </NavigationContainer>
    )
}
