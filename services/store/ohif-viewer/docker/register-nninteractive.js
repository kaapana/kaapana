// Registers the Kaapana nnInteractive extension and mode in OHIF's pluginConfig.json.
// Run from the OHIF source root after the packages are copied into extensions/ and modes/.
const fs = require('fs');

const path = 'platform/app/pluginConfig.json';
const config = JSON.parse(fs.readFileSync(path, 'utf8'));

const register = (list, packageName) => {
  if (!list.some(entry => entry.packageName === packageName)) {
    list.push({ packageName });
  }
};

register(config.extensions, '@kaapana/extension-nninteractive');
register(config.modes, '@kaapana/mode-nninteractive');

fs.writeFileSync(path, JSON.stringify(config, null, 2) + '\n');
