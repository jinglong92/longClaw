const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const {
  TelemetryRuntime,
  EVENT_TYPES,
  ACTOR_TYPES,
  MemoryEventSink,
  JsonlEventSink,
  loadEventsFromJsonl,
  validateEvent
} = require('../../optimization/instrumentation');

test('runtime emits and serializes structured events', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'longclaw-events-'));
  const file = path.join(dir, 'events.jsonl');

  const memorySink = new MemoryEventSink();
  const jsonlSink = new JsonlEventSink(file);
  const runtime = new TelemetryRuntime({
    sinks: [memorySink, jsonlSink],
    versionResolver: () => ({
      router_version: 'router_policy_test',
      prompt_version: 'prompt_test',
      memory_policy_version: 'memory_test',
      evaluator_version: 'eval_test',
      hidden_policy_version: 'hidden_test'
    })
  });

  const event = runtime.emit({
    run_id: 'run_test_1',
    session_id: 'sess_test_1',
    request_id: 'req_test_1',
    event_type: EVENT_TYPES.MESSAGE_RECEIVED,
    actor_type: ACTOR_TYPES.INGRESS,
    actor_id: 'web_console',
    parent_event_id: null,
    payload: { text: 'hello' },
    metrics: { text_length: 5 }
  });

  assert.ok(event);
  await runtime.flushNow();

  const inMemory = memorySink.getEvents();
  assert.equal(inMemory.length, 1);
  assert.equal(inMemory[0].event_type, EVENT_TYPES.MESSAGE_RECEIVED);

  const fromJsonl = loadEventsFromJsonl(file);
  assert.equal(fromJsonl.length, 1);

  const check = validateEvent(fromJsonl[0]);
  assert.equal(check.ok, true);

  await runtime.close();
});
