class PgEventSink {
  constructor(pool) {
    this.pool = pool;
  }

  async write(event) {
    if (!this.pool) return;
    await this.pool.query(
      `INSERT INTO events (
         run_id,
         session_id,
         request_id,
         node_id,
         event_id,
         actor_type,
         agent_id,
         parent_event_id,
         seq,
         event_type,
         metrics_json,
         version_json,
         payload_json
       )
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb, $12::jsonb, $13::jsonb)
       ON CONFLICT (run_id, seq) DO UPDATE SET
         event_type = EXCLUDED.event_type,
         metrics_json = EXCLUDED.metrics_json,
         version_json = EXCLUDED.version_json,
         payload_json = EXCLUDED.payload_json`,
      [
        event.run_id,
        event.session_id,
        event.request_id,
        event.payload?.node_id || null,
        event.event_id,
        event.actor_type,
        event.actor_id,
        event.parent_event_id,
        event.sequence,
        event.event_type,
        JSON.stringify(event.metrics || {}),
        JSON.stringify(event.version_metadata || {}),
        JSON.stringify(event)
      ]
    );
  }

  async close() {
    return undefined;
  }
}

module.exports = {
  PgEventSink
};
