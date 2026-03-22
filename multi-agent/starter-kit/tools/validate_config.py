#!/usr/bin/env python3
"""Validate longClaw multi-agent config v0.1 (JSON only).

Dependency-free validator for starter-kit configs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ALLOWED_ROLES = {"LIFE", "JOB", "WORK", "PARENT", "LEARN", "MONEY", "BRO", "SIS"}

REQUIRED_TOP_LEVEL = {
    "version",
    "profile_name",
    "compatibility_mode",
    "controller",
    "specialists",
    "routing",
    "risk_audit",
    "output_visibility",
}

KNOWN_CONTROLLER_KEYS = {"id", "default_mode", "max_parallel_specialists", "must_finalize"}
KNOWN_SPECIALIST_KEYS = {"id", "enabled", "domain"}
KNOWN_ROUTING_KEYS = {"parallel_limit", "triggers"}
KNOWN_TRIGGER_KEYS = {"name", "keywords", "route"}
KNOWN_RISK_KEYS = {"enabled", "required_fields"}
KNOWN_VISIBILITY_KEYS = {"show_routing", "routing_format"}


def _issue(
    issues: list[dict[str, str]],
    code: str,
    path: str,
    message: str,
    hint: str,
) -> None:
    issues.append(
        {
            "code": code,
            "path": path,
            "message": message,
            "hint": hint,
        }
    )


def _unknown_keys(
    obj: Any,
    known_keys: set[str],
    path_prefix: str,
    issues: list[dict[str, str]],
    strict: bool,
) -> None:
    if not strict or not isinstance(obj, dict):
        return
    for key in sorted(set(obj.keys()) - known_keys):
        _issue(
            issues,
            "MA008",
            f"{path_prefix}.{key}",
            f"unknown field in strict mode: {key}",
            "remove the field or disable --strict",
        )


def load_json_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"file not found: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON ({exc})") from exc

    if not isinstance(data, dict):
        raise ValueError("root must be a JSON object")

    return data


def validate_config(data: dict[str, Any], strict: bool = False) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []

    missing = sorted(REQUIRED_TOP_LEVEL - set(data.keys()))
    for key in missing:
        _issue(
            issues,
            "MA001",
            f"$.{key}",
            f"missing required field: {key}",
            "add the required field to config root",
        )

    _unknown_keys(data, REQUIRED_TOP_LEVEL, "$", issues, strict)

    if missing:
        return issues

    if data["version"] != "0.1":
        _issue(
            issues,
            "MA002",
            "$.version",
            "version must be '0.1'",
            "set version to 0.1 or run a migration step",
        )

    if data["compatibility_mode"] != "openclaw_v1":
        _issue(
            issues,
            "MA002",
            "$.compatibility_mode",
            "compatibility_mode must be 'openclaw_v1'",
            "set compatibility_mode to openclaw_v1",
        )

    controller = data.get("controller", {})
    _unknown_keys(controller, KNOWN_CONTROLLER_KEYS, "$.controller", issues, strict)

    if controller.get("id") != "CTRL":
        _issue(
            issues,
            "MA003",
            "$.controller.id",
            "controller.id must be CTRL",
            "set controller.id to CTRL",
        )

    default_mode = controller.get("default_mode")
    if default_mode not in {"single_specialist", "auto_route"}:
        _issue(
            issues,
            "MA003",
            "$.controller.default_mode",
            "default_mode must be single_specialist or auto_route",
            "choose one allowed value",
        )

    mp = controller.get("max_parallel_specialists")
    if not isinstance(mp, int) or mp < 1 or mp > 2:
        _issue(
            issues,
            "MA003",
            "$.controller.max_parallel_specialists",
            "max_parallel_specialists must be integer in [1, 2]",
            "set value to 1 or 2",
        )

    if controller.get("must_finalize") is not True:
        _issue(
            issues,
            "MA003",
            "$.controller.must_finalize",
            "must_finalize must be true",
            "set must_finalize to true",
        )

    specialists = data.get("specialists", [])
    if not isinstance(specialists, list) or len(specialists) == 0:
        _issue(
            issues,
            "MA004",
            "$.specialists",
            "specialists must be a non-empty array",
            "add at least one specialist object",
        )
        return issues

    seen_roles: set[str] = set()
    enabled_roles: set[str] = set()

    for idx, specialist in enumerate(specialists):
        base = f"$.specialists[{idx}]"
        _unknown_keys(specialist, KNOWN_SPECIALIST_KEYS, base, issues, strict)

        role = specialist.get("id")
        if role not in ALLOWED_ROLES:
            _issue(
                issues,
                "MA004",
                f"{base}.id",
                f"unsupported role: {role}",
                "use one of LIFE/JOB/WORK/PARENT/LEARN/MONEY/BRO/SIS",
            )
            continue

        if role in seen_roles:
            _issue(
                issues,
                "MA004",
                f"{base}.id",
                f"duplicate specialist role: {role}",
                "keep each role unique",
            )
        seen_roles.add(role)

        if specialist.get("enabled") is True:
            enabled_roles.add(role)

        domain = specialist.get("domain")
        if not isinstance(domain, str) or not domain.strip():
            _issue(
                issues,
                "MA004",
                f"{base}.domain",
                "domain must be non-empty string",
                "set a concise domain description",
            )

    if not enabled_roles:
        _issue(
            issues,
            "MA004",
            "$.specialists",
            "at least one specialist must be enabled",
            "set one specialist enabled=true",
        )

    routing = data.get("routing", {})
    _unknown_keys(routing, KNOWN_ROUTING_KEYS, "$.routing", issues, strict)

    parallel_limit = routing.get("parallel_limit")
    if not isinstance(parallel_limit, int) or parallel_limit < 1 or parallel_limit > 2:
        _issue(
            issues,
            "MA005",
            "$.routing.parallel_limit",
            "parallel_limit must be integer in [1, 2]",
            "set routing.parallel_limit to 1 or 2",
        )
    elif isinstance(mp, int) and parallel_limit > mp:
        _issue(
            issues,
            "MA005",
            "$.routing.parallel_limit",
            "parallel_limit cannot exceed controller.max_parallel_specialists",
            "lower parallel_limit or raise controller.max_parallel_specialists",
        )

    triggers = routing.get("triggers")
    if not isinstance(triggers, list) or len(triggers) == 0:
        _issue(
            issues,
            "MA005",
            "$.routing.triggers",
            "triggers must be a non-empty array",
            "add at least one routing trigger",
        )
        return issues

    for idx, trigger in enumerate(triggers):
        base = f"$.routing.triggers[{idx}]"
        _unknown_keys(trigger, KNOWN_TRIGGER_KEYS, base, issues, strict)

        name = trigger.get("name")
        if not isinstance(name, str) or not name.strip():
            _issue(
                issues,
                "MA005",
                f"{base}.name",
                "name must be non-empty string",
                "set a readable trigger name",
            )

        keywords = trigger.get("keywords")
        if not isinstance(keywords, list) or len(keywords) == 0:
            _issue(
                issues,
                "MA005",
                f"{base}.keywords",
                "keywords must be non-empty array",
                "add one or more matching keywords",
            )

        route = trigger.get("route")
        if not isinstance(route, list) or len(route) == 0 or len(route) > 2:
            _issue(
                issues,
                "MA005",
                f"{base}.route",
                "route must contain 1 or 2 roles",
                "set route to one role or two parallel roles",
            )
            continue

        for role in route:
            if role not in ALLOWED_ROLES:
                _issue(
                    issues,
                    "MA005",
                    f"{base}.route",
                    f"unsupported role in route: {role}",
                    "use one of LIFE/JOB/WORK/PARENT/LEARN/MONEY/BRO/SIS",
                )
            elif role not in enabled_roles:
                _issue(
                    issues,
                    "MA006",
                    f"{base}.route",
                    f"route references disabled role: {role}",
                    "enable the role or remove it from trigger route",
                )

    risk = data.get("risk_audit", {})
    _unknown_keys(risk, KNOWN_RISK_KEYS, "$.risk_audit", issues, strict)

    if risk.get("enabled") is not True:
        _issue(
            issues,
            "MA003",
            "$.risk_audit.enabled",
            "risk_audit.enabled must be true in starter-kit v0.1",
            "set risk_audit.enabled to true",
        )

    required_fields = risk.get("required_fields")
    if not isinstance(required_fields, list) or len(required_fields) < 2:
        _issue(
            issues,
            "MA003",
            "$.risk_audit.required_fields",
            "required_fields must contain at least 2 entries",
            "include at least core_gap and tail_risk",
        )

    visibility = data.get("output_visibility", {})
    _unknown_keys(visibility, KNOWN_VISIBILITY_KEYS, "$.output_visibility", issues, strict)

    if visibility.get("show_routing") is not True:
        _issue(
            issues,
            "MA007",
            "$.output_visibility.show_routing",
            "show_routing must be true",
            "set output_visibility.show_routing to true",
        )

    fmt = visibility.get("routing_format")
    if fmt != "User -> CTRL -> [ROLE] -> CTRL -> User":
        _issue(
            issues,
            "MA007",
            "$.output_visibility.routing_format",
            "routing_format must match required contract",
            "set required routing format string exactly",
        )

    return issues


def print_validation_report(data: dict[str, Any], issues: list[dict[str, str]]) -> None:
    if issues:
        print("INVALID CONFIG")
        for idx, issue in enumerate(issues, start=1):
            print(
                f"{idx}. [{issue['code']}] {issue['path']}: {issue['message']} "
                f"| fix: {issue['hint']}"
            )
        return

    print("VALID CONFIG")
    print(f"profile_name: {data.get('profile_name')}")
    enabled = [s["id"] for s in data.get("specialists", []) if s.get("enabled") is True]
    print("enabled_roles: " + ", ".join(enabled))


def run_validation(config_path: Path, strict: bool = False) -> int:
    try:
        data = load_json_config(config_path)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    issues = validate_config(data, strict=strict)
    print_validation_report(data, issues)
    return 1 if issues else 0


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate multi-agent config v0.1",
    )
    parser.add_argument(
        "positional_config",
        nargs="?",
        help="Path to config JSON (legacy positional mode)",
    )
    parser.add_argument("--config", help="Path to config JSON")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on unknown fields",
    )
    return parser


def main() -> int:
    parser = _build_arg_parser()
    args = parser.parse_args()

    config_arg = args.config or args.positional_config
    if not config_arg:
        parser.print_usage()
        return 2

    path = Path(config_arg).expanduser().resolve()
    return run_validation(path, strict=args.strict)


if __name__ == "__main__":
    raise SystemExit(main())
