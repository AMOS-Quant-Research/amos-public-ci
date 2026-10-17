from __future__ import annotations

import argparse
import json

from .compiler import MeshCompiler


def main() -> None:
    parser = argparse.ArgumentParser(description="AMOS Free Cloud Mesh")
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan = subparsers.add_parser("plan", help="compile an approval-first tenant plan")
    plan.add_argument("tenant_file")
    route = subparsers.add_parser("route", help="resolve an AMOS capability to an enabled backend")
    route.add_argument("tenant_file")
    route.add_argument("--capability", required=True)
    route.add_argument("--continuous", action="store_true")
    args = parser.parse_args()

    if args.command == "plan":
        compiler = MeshCompiler()
        print(json.dumps(compiler.plan(compiler.load(args.tenant_file)), ensure_ascii=False, indent=2))
    if args.command == "route":
        compiler = MeshCompiler()
        tenant = compiler.load(args.tenant_file)
        print(json.dumps(compiler.route(tenant, args.capability, continuous=args.continuous), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
