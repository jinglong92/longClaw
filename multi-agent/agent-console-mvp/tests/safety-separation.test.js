const test = require('node:test');
const assert = require('node:assert/strict');

const {
  validateVisibleRoute,
  sanitizePatchSuggestions
} = require('../../hidden-agents/safety_agent');

test('visible route rejects hidden agent labels', () => {
  const valid = validateVisibleRoute(['WORK']);
  assert.equal(valid.ok, true);

  const invalid = validateVisibleRoute(['ROUTER_AGENT']);
  assert.equal(invalid.ok, false);
  assert.ok(String(invalid.reason).includes('invalid visible label'));
});

test('patch sanitizer blocks visible routing protocol mutation', () => {
  const input = [
    {
      patch_id: 'p1',
      target: 'visible_route_protocol',
      kind: 'rewrite'
    },
    {
      patch_id: 'p2',
      target: 'memory_policy',
      kind: 'threshold'
    }
  ];

  const { safePatches, rejected } = sanitizePatchSuggestions(input);
  assert.equal(safePatches.length, 1);
  assert.equal(rejected.length, 1);
  assert.equal(safePatches[0].auto_apply_allowed, false);
});
