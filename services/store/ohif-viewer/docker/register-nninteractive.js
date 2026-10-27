// Registers the Kaapana nnInteractive extension and mode in OHIF's pluginConfig.json.
// Run from the OHIF source root after the packages are copied into extensions/ and modes/.
const fs = require('fs');

const path = 'platform/app/pluginConfig.json';
const config = JSON.parse(fs.readFileSync(path, 'utf8'));

const register = (list, packageName, { first = false } = {}) => {
  if (!list.some(entry => entry.packageName === packageName)) {
    first ? list.unshift({ packageName }) : list.push({ packageName });
  }
};

// Last: the extension uses services (segmentation, cornerstone viewport) that OHIF's own
// extensions register first.
register(config.extensions, '@kaapana/extension-nninteractive');
// First: the mode serves the `viewer` route, which OHIF's longitudinal mode also declares, and
// the first registered mode wins the route.
register(config.modes, '@kaapana/mode-nninteractive', { first: true });

fs.writeFileSync(path, JSON.stringify(config, null, 2) + '\n');
