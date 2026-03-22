const { VISIBLE_ROUTE_LABELS } = require('../../shared/types/visible-routing');

const ROUTER_POLICY_VERSION = 'router_policy_v2';
const DUAL_ROUTE_MIN_CONFIDENCE = 0.66;
const DUAL_ROUTE_MIN_SECOND_SCORE = 1;
const DUAL_ROUTE_MAX_SCORE_GAP = 1;

const RULES = [
  {
    role: 'LIFE',
    keywords: [
      { token: '日程', weight: 1.0 },
      { token: '出行', weight: 1.0 },
      { token: '家务', weight: 1.0 },
      { token: '安排', weight: 0.35 },
      { token: '健康', weight: 0.9 }
    ]
  },
  {
    role: 'JOB',
    keywords: [
      { token: '求职', weight: 1.0 },
      { token: '简历', weight: 1.0 },
      { token: '面试', weight: 1.3 },
      { token: 'offer', weight: 1.1 },
      { token: '投递', weight: 1.0 }
    ]
  },
  {
    role: 'WORK',
    keywords: [
      { token: '晋升', weight: 1.1 },
      { token: '职场', weight: 1.0 },
      { token: '团队', weight: 1.0 },
      { token: '管理', weight: 1.0 },
      { token: '沟通', weight: 0.9 }
    ]
  },
  {
    role: 'PARENT',
    keywords: [
      { token: '孩子', weight: 1.0 },
      { token: '育儿', weight: 1.0 },
      { token: '亲子', weight: 1.0 },
      { token: '学校', weight: 0.9 },
      { token: '接娃', weight: 1.3 }
    ]
  },
  {
    role: 'LEARN',
    keywords: [
      { token: '学习', weight: 1.0 },
      { token: '论文', weight: 1.1 },
      { token: '复盘', weight: 1.0 },
      { token: '课程', weight: 1.0 },
      { token: '备考', weight: 1.0 }
    ]
  },
  {
    role: 'MONEY',
    keywords: [
      { token: '理财', weight: 1.0 },
      { token: '预算', weight: 0.9 },
      { token: '投资', weight: 1.1 },
      { token: '保险', weight: 1.0 },
      { token: '税务', weight: 1.0 }
    ]
  },
  {
    role: 'BRO',
    keywords: [
      { token: '闲聊', weight: 1.0 },
      { token: '吐槽', weight: 1.0 },
      { token: '放松', weight: 0.9 },
      { token: '段子', weight: 1.0 },
      { token: '打气', weight: 0.9 }
    ]
  },
  {
    role: 'SIS',
    keywords: [
      { token: '女性视角', weight: 1.2 },
      { token: '关系', weight: 1.0 },
      { token: '恋爱', weight: 1.0 },
      { token: '约会', weight: 1.0 },
      { token: '边界', weight: 1.0 }
    ]
  }
];

const ROLE_PRIORITY = {
  JOB: 1,
  PARENT: 2,
  WORK: 3,
  LEARN: 4,
  MONEY: 5,
  LIFE: 6,
  SIS: 7,
  BRO: 8
};

function scoreRole(text, rule) {
  let score = 0;
  for (const keyword of rule.keywords) {
    const token = typeof keyword === 'string' ? keyword : keyword.token;
    const weight = typeof keyword === 'string' ? 1 : Number(keyword.weight || 1);
    if (text.includes(token)) score += weight;
  }
  return score;
}

function selectVisibleRoute(input, { maxParallel = 2 } = {}) {
  const text = String(input || '').trim();
  const rows = RULES.map(rule => ({ role: rule.role, score: scoreRole(text, rule) }))
    .filter(row => row.score > 0)
    .sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score;
      return (ROLE_PRIORITY[a.role] || 99) - (ROLE_PRIORITY[b.role] || 99);
    });

  const topScore = rows[0]?.score || 0;
  const secondScore = rows[1]?.score || 0;
  const scoreGap = topScore - secondScore;

  let selected;
  if (rows.length === 0) {
    selected = ['LIFE'];
  } else {
    const confidence = Math.min(0.98, 0.55 + topScore * 0.1);
    const wantsParallel = Math.max(1, Math.min(maxParallel, 2)) > 1;
    const allowDualRoute =
      wantsParallel &&
      rows.length > 1 &&
      confidence >= DUAL_ROUTE_MIN_CONFIDENCE &&
      secondScore >= DUAL_ROUTE_MIN_SECOND_SCORE &&
      scoreGap <= DUAL_ROUTE_MAX_SCORE_GAP;

    selected = allowDualRoute
      ? rows.slice(0, 2).map(row => row.role)
      : [rows[0].role];
  }

  const confidence = rows.length === 0 ? 0.4 : Math.min(0.98, 0.55 + rows[0].score * 0.1);
  const routeMode = selected.length === 2 ? 'dual' : 'single';

  return {
    visible_route: selected,
    confidence,
    policy_version: ROUTER_POLICY_VERSION,
    rationale: rows.length
      ? `mode=${routeMode}; dual_threshold=${DUAL_ROUTE_MIN_CONFIDENCE}; matched=${rows.map(row => `${row.role}:${row.score}`).join(',')}`
      : 'fallback to LIFE due to missing keyword match'
  };
}

function candidateRouteFromTrace(trace, { maxParallel = 2 } = {}) {
  const text = trace.user_input || '';
  return selectVisibleRoute(text, { maxParallel });
}

function isValidVisibleRoute(route) {
  if (!Array.isArray(route) || route.length === 0 || route.length > 2) return false;
  return route.every(role => VISIBLE_ROUTE_LABELS.includes(role));
}

module.exports = {
  ROUTER_POLICY_VERSION,
  DUAL_ROUTE_MIN_CONFIDENCE,
  DUAL_ROUTE_MIN_SECOND_SCORE,
  DUAL_ROUTE_MAX_SCORE_GAP,
  RULES,
  selectVisibleRoute,
  candidateRouteFromTrace,
  isValidVisibleRoute
};
