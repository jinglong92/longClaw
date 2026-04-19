#!/usr/bin/env python3
"""
Query the sidecar session ledger.

This tool performs a simple text search across tables in the sidecar
database.  It supports limiting results and selecting a specific table
kind.  Note that this is a minimal implementation using LIKE queries;
future versions may add full‑text search.
"""

import argparse
import json
import sys
from typing import Dict, List

from runtime_sidecar.state import readers, writers, db


def main() -> int:
    parser = argparse.ArgumentParser(description="Search the session ledger")
    parser.add_argument("--query", required=True, help="Search term (substring match)")
    parser.add_argument("--kind", choices=["sessions", "route_decisions", "tool_events", "notes"], help="Table to search")
    parser.add_argument("--limit", type=int, default=100, help="Maximum number of rows to return")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()
    # Ensure database exists
    conn = db.get_connection()
    writers.initialise_schema(conn)
    kinds = [args.kind] if args.kind else ["sessions", "route_decisions", "tool_events", "notes"]
    all_results: Dict[str, List[Dict[str, str]]] = {}
    for kind in kinds:
        results = readers.search_records(kind, args.query, limit=args.limit)
        all_results[kind] = results
    if args.json:
        print(json.dumps(all_results, indent=2, default=str))
    else:
        for kind, results in all_results.items():
            print(f"== {kind} ==")
            if not results:
                print("(no results)")
                continue
            # Print column names
            columns = results[0].keys()
            header = " | ".join(columns)
            print(header)
            print("-" * len(header))
            for row in results:
                values = [str(row.get(col, "")) for col in columns]
                print(" | ".join(values))
            print()
    return 0


if __name__ == "__main__":
    sys.exit(main())