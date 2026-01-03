import React from 'react'
import { View, StyleSheet, ViewStyle } from 'react-native'

interface CardProps {
    children: React.ReactNode
    style?: ViewStyle
    padding?: number
}

export const Card: React.FC<CardProps> = ({ children, style, padding = 16 }) => {
    return (
        <View style={[styles.card, { padding }, style]}>
            {children}
        </View>
    )
}

const styles = StyleSheet.create({
    card: {
        backgroundColor: 'white',
        borderRadius: 12,
        elevation: 2, // Android shadow
        shadowColor: '#000', // iOS shadow
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.1,
        shadowRadius: 3,
        marginBottom: 12,
    },
})
