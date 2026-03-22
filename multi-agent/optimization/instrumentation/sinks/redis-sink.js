class RedisEventSink {
  constructor(redis, streamName = 'agent_events') {
    this.redis = redis;
    this.streamName = streamName;
  }

  async write(event) {
    if (!this.redis) return;
    await this.redis.xadd(this.streamName, '*', 'data', JSON.stringify(event));
  }

  async close() {
    return undefined;
  }
}

module.exports = {
  RedisEventSink
};
