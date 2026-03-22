const fs = require('fs');
const path = require('path');

class JsonlEventSink {
  constructor(filePath) {
    if (!filePath || typeof filePath !== 'string') {
      throw new Error('JsonlEventSink requires file path');
    }
    this.filePath = filePath;
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    this.stream = fs.createWriteStream(filePath, {
      flags: 'a',
      encoding: 'utf8'
    });
  }

  async write(event) {
    const line = `${JSON.stringify(event)}\n`;
    return new Promise((resolve, reject) => {
      this.stream.write(line, err => {
        if (err) {
          reject(err);
          return;
        }
        resolve();
      });
    });
  }

  async close() {
    return new Promise((resolve, reject) => {
      this.stream.end(err => {
        if (err) {
          reject(err);
          return;
        }
        resolve();
      });
    });
  }
}

function loadEventsFromJsonl(filePath) {
  if (!fs.existsSync(filePath)) return [];
  const content = fs.readFileSync(filePath, 'utf8');
  if (!content.trim()) return [];
  const lines = content.split('\n').filter(Boolean);
  const events = [];
  for (const line of lines) {
    try {
      events.push(JSON.parse(line));
    } catch (_err) {
      // skip malformed lines to keep replay resilient
    }
  }
  return events;
}

module.exports = {
  JsonlEventSink,
  loadEventsFromJsonl
};
