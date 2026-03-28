# Adapter Registry

Adapter registry is filesystem-based and append-only by default.

## Path

- default: `artifacts/adapters/registry.jsonl`

## Record fields

- `adapter_id`
- `backend` (`mlx-lm` or `llamafactory`)
- `base_model`
- `task_type`
- `metrics`
- `status` (`draft`, `shadow`, `canary`, `active`, `archived`)
- `path`
- `notes`
- `created_at`

## Lifecycle

1. create as `draft`
2. run shadow eval
3. promote to `canary`
4. promote to `active`
5. retire to `archived`

## API surface

Implemented in `openclaw_substrate/adapter_registry.py`:

- `register()`
- `list_adapters()`
- `update_status()`
- `get()`

## Operational rule

Do not activate adapters without a shadow report showing non-degraded metrics on:

- wrong-route rate
- retry rate
- explicit correction rate
- tool success proxy
- trainable sample yield
