"""Command-line interface for running the RV Winner Scout."""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

from rv_winner_scout.config.settings import get_settings
from rv_winner_scout.services.orchestrator import PipelineOrchestrator


def setup_logging(log_level: str = "INFO") -> None:
    """Configures structured console logging."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def async_main() -> int:
    parser = argparse.ArgumentParser(description="RV Winner Scout - Amazon RV Affiliate Discovery System")
    parser.add_argument(
        "--mode",
        choices=["smoke", "small", "full"],
        default=None,
        help="Run mode: smoke (5-10 items), small (15-30 items), or full (all accessible)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional path to save the generated Markdown report",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Ignore historical deduplication cache to re-evaluate products from scratch",
    )
    parser.add_argument(
        "--start-index",
        type=int,
        default=0,
        help="Optional 1-based or 0-based product index offset to resume search from (e.g. 2637)",
    )

    args = parser.parse_args()
    settings = get_settings()
    setup_logging(settings.log_level)

    orchestrator = PipelineOrchestrator(settings=settings)
    report_md, health = await orchestrator.run(
        mode=args.mode, fresh=args.fresh, start_index=args.start_index
    )

    # 1. Save report to data/reports
    reports_dir = os.path.join(settings.data_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    report_path = args.output or os.path.join(
        reports_dir, f"report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.md"
    )
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    # 2. Output report safely to console
    try:
        if sys.platform == "win32":
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    safe_report = report_md.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
    print("\n" + "=" * 80)
    try:
        print(safe_report)
    except Exception:
        print("Report generated successfully. Full details written to disk.")
    print("=" * 80 + "\n")

    print(f"Report saved to: {report_path}")
    print(f"Final Run Status: {health.status.value}")

    # Return exit code 0 for SUCCESS or PARTIAL; 1 for FAILED
    return 0 if health.status.value != "FAILED" else 1


def main() -> None:
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    exit_code = asyncio.run(async_main())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
