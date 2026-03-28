# Trace Schema

Canonical trace record is implemented by `TraceRecord` in `openclaw_substrate/schemas.py`.

## Required fields

- `trace_id`
- `session_id`
- `turn_id`
- `policy_version`
- `request_text`
- `response_text`
- `route`
- `model`
- `created_at`

## Optional quality and diagnostics fields

- `retries`
- `explicit_correction`
- `tool_success`
- `wrong_route`
- `sideline_reason`
- `metadata`

## Mainline vs sideline

- Mainline: `sideline_reason == ""`
- Sideline: `sideline_reason != ""`

`TracePlane.split_mainline_sideline()` provides deterministic split for replay and training filters.

## Next-state assembly

`TracePlane.assemble_next_state(session_id)` builds:

- bounded history window
- stats: retries, correction rate, tool success rate
- `policy_version`

This supports route/judge context and downstream training.

## Eligibility filter

`TracePlane.training_eligible_filter()` currently uses:

- mainline only
- `metadata.quality_score >= eligibility_min_quality`

This keeps low-quality sideline noise out of early training sets.
