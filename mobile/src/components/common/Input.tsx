import React from 'react'
import { View, TextInput, Text, StyleSheet, TextInputProps, ViewStyle } from 'react-native'

interface InputProps extends TextInputProps {
    label?: string
    error?: string
    containerStyle?: ViewStyle
}

export const Input: React.FC<InputProps> = ({
    label,
    error,
    containerStyle,
    style,
    ...props
}) => {
    return (
        <View style={[styles.container, containerStyle]}>
            {label && <Text style={styles.label}>{label}</Text>}
            <TextInput
                style={[
                    styles.input,
                    error ? styles.inputError : null,
                    props.editable === false ? styles.inputDisabled : null,
                    style,
                ]}
                placeholderTextColor="#9E9E9E"
                {...props}
            />
            {error && <Text style={styles.error}>{error}</Text>}
        </View>
    )
}

const styles = StyleSheet.create({
    container: {
        marginBottom: 16,
    },
    label: {
        marginBottom: 6,
        fontSize: 14,
        color: '#333',
        fontWeight: '500',
    },
    input: {
        height: 48,
        borderWidth: 1,
        borderColor: '#E0E0E0',
        borderRadius: 8,
        paddingHorizontal: 16,
        fontSize: 16,
        color: '#000',
        backgroundColor: '#FAFAFA',
    },
    inputError: {
        borderColor: '#F44336',
    },
    inputDisabled: {
        backgroundColor: '#F5F5F5',
        color: '#9E9E9E',
    },
    error: {
        marginTop: 4,
        fontSize: 12,
        color: '#F44336',
    },
})
