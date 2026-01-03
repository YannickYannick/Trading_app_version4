module.exports = function (api) {
    api.cache(true);
    return {
        presets: ['babel-preset-expo'],
        plugins: [
            [
                'module-resolver',
                {
                    root: ['./'],
                    alias: {
                        '@trading-app/shared': '../shared/src',
                        '@shared': '../shared/src'
                    },
                    extensions: ['.ios.js', '.android.js', '.js', '.ts', '.tsx', '.json']
                }
            ]
        ]
    };
};
