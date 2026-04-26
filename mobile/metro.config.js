// Learn more https://docs.expo.io/guides/customizing-metro
const { getDefaultConfig } = require('expo/metro-config');
const fs = require('fs');
const path = require('path');

const projectRoot = __dirname;
const workspaceRoot = path.resolve(projectRoot, '..');
const isMonorepoWorkspace = fs.existsSync(
  path.join(workspaceRoot, 'shared', 'package.json'),
);

const config = getDefaultConfig(projectRoot);

// 1. Watch the monorepo root only when ../shared exists (real monorepo layout).
// If mobile lives alone under e.g. C:\TradingMobile, ../ is the drive root — do not watch it.
if (isMonorepoWorkspace) {
  config.watchFolders = [workspaceRoot];
  config.resolver.nodeModulesPaths = [
    path.resolve(projectRoot, 'node_modules'),
    path.resolve(workspaceRoot, 'node_modules'),
  ];
} else {
  config.watchFolders = [projectRoot];
  config.resolver.nodeModulesPaths = [path.resolve(projectRoot, 'node_modules')];
}

module.exports = config;
