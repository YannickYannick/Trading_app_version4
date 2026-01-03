import React from 'react'
import { TouchableOpacity, Text, StyleSheet, ActivityIndicator, ViewStyle, TextStyle } from 'react-native'

interface ButtonProps {
    title: string
    onPress: () => void
    variant?: 'primary' | 'secondary' | 'outline' | 'danger'
    size?: 'sm' | 'md' | 'lg'
    loading?: boolean
    disabled?: boolean
    style?: ViewStyle
}

export const Button: React.FC<ButtonProps> = ({
    title,
    onPress,
    variant = 'primary',
    size = 'md',
    loading = false,
    disabled = false,
    style,
}) => {
    const getBackgroundColor = () => {
        if (disabled) return '#E0E0E0'
        switch (variant) {
            case 'primary': return '#2196F3'
            case 'secondary': return '#757575'
            case 'danger': return '#F44336'
            case 'outline': return 'transparent'
            default: return '#2196F3'
        }
    }

    const getTextColor = () => {
        if (disabled) return '#9E9E9E'
        if (variant === 'outline') return '#2196F3'
        return '#FFFFFF'
    }

    const getPadding = () => {
        switch (size) {
            case 'sm': return { paddingVertical: 6, paddingHorizontal: 12 }
            case 'lg': return { paddingVertical: 14, paddingHorizontal: 24 }
            default: return { paddingVertical: 10, paddingHorizontal: 16 }
        }
    }

    return (
        <TouchableOpacity
            style={[
                styles.button,
                {
                    backgroundColor: getBackgroundColor(),
                    borderColor: variant === 'outline' ? '#2196F3' : 'transparent',
                    borderWidth: variant === 'outline' ? 1 : 0,
                    ...getPadding(),
                },
                style,
            ]}
            onPress={onPress}
            disabled={disabled || loading}
            activeOpacity={0.8}
        >
            {loading ? (
                <ActivityIndicator color={getTextColor()} size="small" />
            ) : (
                <Text style={[styles.text, { color: getTextColor(), fontSize: size === 'lg' ? 16 : 14 }]}>
                    {title}
                </Text>
            )}
        </TouchableOpacity>
    )
}

const styles = StyleSheet.create({
    button: {
        borderRadius: 8,
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'row',
    },
    text: {
        fontWeight: '600',
        textAlign: 'center',
    },
})
