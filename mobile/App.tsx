import React from 'react'
import { SafeAreaProvider } from 'react-native-safe-area-context'
import { AuthProvider } from './src/hooks/AuthProvider'
import { AppNavigator } from './src/navigation/AppNavigator'

export default function App() {
  return (
    <SafeAreaProvider>
      <AuthProvider>
        <AppNavigator />
      </AuthProvider>
    </SafeAreaProvider>
  )
}
