class MemoryEventSink {
  constructor({ maxItems = 5000 } = {}) {
    this.maxItems = maxItems;
    this.events = [];
  }

  async write(event) {
    this.events.push(event);
    if (this.events.length > this.maxItems) {
      const overflow = this.events.length - this.maxItems;
      this.events.splice(0, overflow);
    }
  }

  getEvents() {
    return [...this.events];
  }

  clear() {
    this.events.length = 0;
  }

  async close() {
    return undefined;
  }
}

module.exports = {
  MemoryEventSink
};
