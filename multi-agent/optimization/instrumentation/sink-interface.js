function assertEventSink(sink) {
  if (!sink || typeof sink.write !== 'function') {
    throw new Error('invalid sink: must implement write(event)');
  }
  if (sink.close && typeof sink.close !== 'function') {
    throw new Error('invalid sink: close must be function when provided');
  }
}

async function safeSinkWrite(sink, event, onError) {
  try {
    await sink.write(event);
  } catch (err) {
    if (typeof onError === 'function') onError(err, sink, event);
  }
}

module.exports = {
  assertEventSink,
  safeSinkWrite
};
