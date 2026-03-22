const { randomUUID } = require('crypto');
const { assertEventSink, safeSinkWrite } = require('./sink-interface');
const { validateEvent } = require('./validator');
const { EVENT_TYPES, ACTOR_TYPES } = require('./event-types');

function defaultVersionResolver() {
  return {
    router_version: 'router_policy_v0',
    prompt_version: 'prompt_bundle_v0',
    memory_policy_version: 'memory_policy_v0',
    evaluator_version: 'evaluator_v0',
    hidden_policy_version: 'hidden_policy_v0'
  };
}

class TelemetryRuntime {
  constructor({
    sinks = [],
    versionResolver = defaultVersionResolver,
    strictValidation = true,
    onError = null
  } = {}) {
    this.sinks = sinks;
    this.versionResolver = versionResolver;
    this.strictValidation = strictValidation;
    this.onError = typeof onError === 'function' ? onError : null;
    this.queue = [];
    this.flushScheduled = false;
    this.flushing = false;
    this.sequence = Math.floor(Date.now() * 1000);

    for (const sink of this.sinks) {
      assertEventSink(sink);
    }
  }

  emit(partialEvent) {
    const event = {
      event_id: randomUUID(),
      run_id: partialEvent.run_id,
      session_id: partialEvent.session_id,
      request_id: partialEvent.request_id,
      timestamp: partialEvent.timestamp || new Date().toISOString(),
      sequence: ++this.sequence,
      event_type: partialEvent.event_type,
      actor_type: partialEvent.actor_type,
      actor_id: partialEvent.actor_id,
      parent_event_id: partialEvent.parent_event_id ?? null,
      payload: partialEvent.payload || {},
      metrics: partialEvent.metrics || {},
      version_metadata: {
        ...this.versionResolver(),
        ...(partialEvent.version_metadata || {})
      }
    };

    const check = validateEvent(event);
    if (!check.ok) {
      const err = new Error(`invalid telemetry event: ${check.reason}`);
      if (this.onError) this.onError(err, event);
      if (this.strictValidation) return null;
    }

    this.queue.push(event);
    this._scheduleFlush();
    return event;
  }

  _scheduleFlush() {
    if (this.flushScheduled) return;
    this.flushScheduled = true;
    setImmediate(() => {
      this.flushScheduled = false;
      this.flush().catch(err => {
        if (this.onError) this.onError(err);
      });
    });
  }

  async flush() {
    if (this.flushing) return;
    this.flushing = true;
    try {
      while (this.queue.length > 0) {
        const event = this.queue.shift();
        await Promise.all(
          this.sinks.map(sink =>
            safeSinkWrite(sink, event, err => {
              if (this.onError) this.onError(err, event);
            })
          )
        );
      }
    } finally {
      this.flushing = false;
    }
  }

  async flushNow() {
    await this.flush();
  }

  pendingCount() {
    return this.queue.length;
  }

  async close() {
    await this.flush();
    await Promise.all(
      this.sinks.map(async sink => {
        if (typeof sink.close === 'function') {
          try {
            await sink.close();
          } catch (err) {
            if (this.onError) this.onError(err);
          }
        }
      })
    );
  }
}

module.exports = {
  TelemetryRuntime,
  defaultVersionResolver,
  EVENT_TYPES,
  ACTOR_TYPES
};
