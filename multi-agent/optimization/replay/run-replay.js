#!/usr/bin/env node
const path = require('path');
const { runReplayFromJsonl } = require('./replay-harness');
const { readRegistryFile } = require('../registry/registry');

function parseArgs(argv) {
  const args = {
    mode: 'dry-run',
    jsonl: path.resolve(__dirname, '..', 'traces', 'events.jsonl'),
    out: path.resolve(__dirname, '..', 'reports', `replay-${Date.now()}.json`)
  };

  for (let i = 2; i < argv.length; i += 1) {
    const token = argv[i];
    if (token === '--mode' && argv[i + 1]) {
      args.mode = argv[i + 1];
      i += 1;
      continue;
    }
    if (token === '--jsonl' && argv[i + 1]) {
      args.jsonl = path.resolve(argv[i + 1]);
      i += 1;
      continue;
    }
    if (token === '--out' && argv[i + 1]) {
      args.out = path.resolve(argv[i + 1]);
      i += 1;
      continue;
    }
  }
  return args;
}

function main() {
  const args = parseArgs(process.argv);
  const evaluatorConfig = readRegistryFile('evaluator.config.json');
  const report = runReplayFromJsonl({
    jsonlPath: args.jsonl,
    mode: args.mode,
    evaluatorConfig,
    reportPath: args.out
  });

  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
}

if (require.main === module) {
  main();
}
