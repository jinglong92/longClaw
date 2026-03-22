const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const {
  ensureRegistryFiles,
  readRegistryFile,
  writeRegistryFile,
  getActiveVersions
} = require('../../optimization/registry/registry');

test('registry read/write and active version lookup', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'longclaw-registry-'));
  ensureRegistryFiles(dir);

  const promptRegistry = readRegistryFile('prompt-registry.json', dir);
  assert.ok(promptRegistry.current);

  const next = {
    ...promptRegistry,
    current: 'prompt_bundle_v2',
    items: [...promptRegistry.items, { id: 'prompt_bundle_v2', description: 'test', created_at: new Date().toISOString() }]
  };
  writeRegistryFile('prompt-registry.json', next, dir);

  const versions = getActiveVersions(dir);
  assert.equal(versions.prompt_version, 'prompt_bundle_v2');
});
