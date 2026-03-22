const { HIDDEN_AGENT_SET } = require('../../shared/types/hidden-agents');
const { VISIBLE_ROUTE_SET } = require('../../shared/types/visible-routing');

const ID = 'SAFETY_AGENT';
const VERSION = 'safety_agent_v0.1';

function validateVisibleRoute(route) {
  if (!Array.isArray(route)) {
    return { ok: false, reason: 'visible route must be array' };
  }
  if (route.length === 0 || route.length > 2) {
    return { ok: false, reason: 'visible route must contain 1..2 labels' };
  }
  for (const label of route) {
    if (!VISIBLE_ROUTE_SET.has(label)) {
      return { ok: false, reason: `invalid visible label: ${label}` };
    }
    if (HIDDEN_AGENT_SET.has(label)) {
      return { ok: false, reason: `hidden label leaked into visible route: ${label}` };
    }
  }
  return { ok: true };
}

function sanitizePatchSuggestions(patches) {
  const safePatches = [];
  const rejected = [];

  for (const patch of patches || []) {
    const target = String(patch.target || '');
    if (target.includes('visible_route') || target.includes('routing_protocol')) {
      rejected.push({
        patch,
        reason: 'cannot auto-mutate visible routing protocol'
      });
      continue;
    }
    safePatches.push({
      ...patch,
      auto_apply_allowed: false,
      safety_review_required: true
    });
  }

  return { safePatches, rejected };
}

function analyze({ route, patchSuggestions }) {
  const routeCheck = validateVisibleRoute(route || []);
  const { safePatches, rejected } = sanitizePatchSuggestions(patchSuggestions || []);

  return {
    agent_id: ID,
    version: VERSION,
    summary: routeCheck.ok
      ? `route contract valid; patch suggestions safe=${safePatches.length} rejected=${rejected.length}`
      : `route contract violation: ${routeCheck.reason}`,
    route_check: routeCheck,
    safe_patch_suggestions: safePatches,
    rejected_patch_suggestions: rejected
  };
}

module.exports = {
  ID,
  VERSION,
  validateVisibleRoute,
  sanitizePatchSuggestions,
  analyze
};
