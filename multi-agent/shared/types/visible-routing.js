const VISIBLE_ROUTE_LABELS = Object.freeze([
  'LIFE',
  'JOB',
  'WORK',
  'PARENT',
  'LEARN',
  'MONEY',
  'BRO',
  'SIS'
]);

const VISIBLE_ROUTE_SET = new Set(VISIBLE_ROUTE_LABELS);

function isVisibleRouteLabel(value) {
  return typeof value === 'string' && VISIBLE_ROUTE_SET.has(value);
}

function assertVisibleRouteLabels(route) {
  if (!Array.isArray(route)) {
    throw new Error('visible route must be an array');
  }
  for (const role of route) {
    if (!isVisibleRouteLabel(role)) {
      throw new Error(`invalid visible route label: ${role}`);
    }
  }
}

module.exports = {
  VISIBLE_ROUTE_LABELS,
  VISIBLE_ROUTE_SET,
  isVisibleRouteLabel,
  assertVisibleRouteLabels
};
