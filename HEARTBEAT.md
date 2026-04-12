# HEARTBEAT.md

## Silent Heartbeat Policy

Heartbeat polling is an internal maintenance action, not a user-facing interaction.

Default behavior: **silence**.

---

## Core Rule

When heartbeat polling is triggered:

- Do **not** send any proactive outbound message to WeChat, email, SMS, Slack, or any other user-facing channel.
- Do **not** send placeholder texts such as `HEARTBEAT_OK`, `心跳正常`, `all good`, `still alive`, or any equivalent status ping.
- Do **not** acknowledge to the user that heartbeat polling occurred.
- If there is **no critical emergency**, produce **no outbound user-facing message**.

---

## Allowed Internal Actions

Heartbeat may still perform internal work, including:
- checking inbox / calendar / notifications
- reading or updating memory files
- reviewing workspace files
- recording internal logs or state
- preparing a future recommendation internally

These actions must remain silent unless a critical emergency exists.

---

## What Counts as a Critical Emergency

A user-facing alert is allowed **only** if immediate human action is required to prevent one of the following:

1. Security incident
2. Irreversible destructive failure
3. Production outage requiring human intervention
4. High-risk financial / operational failure
5. Safety-critical issue

If the issue is recoverable, transient, low-confidence, retryable, or can be handled automatically, it is **not** a critical emergency.

---

## Non-Emergencies (Must Stay Silent)

The following are **not** reasons to send a message:

- heartbeat succeeded normally
- no new events were found
- temporary timeout or retryable API failure
- one source failed but alternatives still exist
- minor warning or uncertainty
- “just keeping the user informed”
- “it has been a while since the last message”
- “something interesting was found”
- routine background polling result

All of the above must produce **no outbound message**.

---

## Output Contract

### If no critical emergency
- perform internal checks if needed
- optionally update internal files/logs
- send **nothing**
- return **empty / no-op / no outbound user-facing message**

### If critical emergency exists
Send exactly **one concise alert**, containing:
- what happened
- why it is critical
- what immediate action is required

---

## Enforcement Rule

If there is any ambiguity, choose **silence**.
