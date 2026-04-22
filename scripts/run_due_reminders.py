#!/usr/bin/env python3
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

WS = Path(__file__).resolve().parents[1]
STATE = WS / 'memory' / 'reminders.json'
OUT = WS / 'memory' / 'due-reminders.json'
TZ = ZoneInfo('Asia/Shanghai')


def load_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


state = load_json(STATE, {"timezone": "Asia/Shanghai", "items": []})
now = datetime.now(TZ)
due = []
changed = False
for item in state.get('items', []):
    status = item.get('status', 'pending')
    if status == 'done' or status == 'sent':
        continue
    due_at = item.get('due_at')
    if not due_at:
        continue
    try:
        due_dt = datetime.fromisoformat(due_at)
        if due_dt.tzinfo is None:
            due_dt = due_dt.replace(tzinfo=TZ)
    except Exception:
        continue
    if due_dt <= now:
        due.append({
            'id': item.get('id'),
            'title': item.get('title'),
            'content': item.get('content'),
            'due_at': item.get('due_at'),
            'chat_id': item.get('chat_id'),
            'reply_tag': item.get('reply_tag', '[[reply_to_current]]'),
            'status': status,
        })
        if status == 'pending':
            item['status'] = 'due'
            item['due_detected_at'] = now.isoformat()
            changed = True

save_json(OUT, {
    'generated_at': now.isoformat(),
    'count': len(due),
    'items': due,
})
if changed:
    save_json(STATE, state)
print(json.dumps({'generated_at': now.isoformat(), 'count': len(due), 'out': str(OUT)}, ensure_ascii=False))
