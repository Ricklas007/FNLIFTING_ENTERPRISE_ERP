from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ops.readiness import build_readiness_report  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="FNLIFTING ERP production readiness preflight")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--fail-on-warn", action="store_true", help="return non-zero when warnings exist")
    args = parser.parse_args()

    report = build_readiness_report()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        summary = report["summary"]
        print(f"FNLIFTING ERP {report['version']} · ambiente: {report['environment']}")
        print(f"Estado: {report['status']} · OK={summary['pass']} · Avisos={summary['warn']} · Falhas={summary['fail']}")
        print()
        for item in report["checks"]:
            marker = {"pass": "OK", "warn": "AVISO", "fail": "FALHA"}.get(item["status"], item["status"].upper())
            print(f"[{marker}] {item['label']}: {item['message']}")
            if item.get("recommendation"):
                print(f"  -> {item['recommendation']}")

    if report["summary"]["fail"] > 0:
        return 2
    if args.fail_on_warn and report["summary"]["warn"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

