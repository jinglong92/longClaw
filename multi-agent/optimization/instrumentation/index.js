const { TelemetryRuntime, EVENT_TYPES, ACTOR_TYPES } = require('./runtime');
const { aggregateEventsToTraces } = require('./trace-aggregator');
const { validateEvent, validateTrace } = require('./validator');
const { MemoryEventSink } = require('./sinks/memory-sink');
const { JsonlEventSink, loadEventsFromJsonl } = require('./sinks/jsonl-sink');
const { PgEventSink } = require('./sinks/pg-sink');
const { RedisEventSink } = require('./sinks/redis-sink');

module.exports = {
  TelemetryRuntime,
  EVENT_TYPES,
  ACTOR_TYPES,
  aggregateEventsToTraces,
  validateEvent,
  validateTrace,
  MemoryEventSink,
  JsonlEventSink,
  loadEventsFromJsonl,
  PgEventSink,
  RedisEventSink
};
