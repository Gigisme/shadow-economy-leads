"""Command-line entry point: `shadow-leads ingest [--source ...] [--run-id YYYY-MM-DD]`."""

import argparse
import logging
from datetime import date

from shadow_leads.ingest import registrucentras, sodra

INGESTERS = {
    registrucentras.SOURCE: registrucentras.fetch,
    sodra.SOURCE: sodra.fetch,
}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="shadow-leads")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="download raw data from official sources")
    ingest.add_argument("--source", choices=sorted(INGESTERS), action="append",
                        help="source to fetch (repeatable); default: all")
    ingest.add_argument("--run-id", default=date.today().isoformat(),
                        help="raw folder name for this run (default: today)")

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if args.command == "ingest":
        for name in args.source or sorted(INGESTERS):
            path = INGESTERS[name](args.run_id)
            logging.info("%s done: %s", name, path)


if __name__ == "__main__":
    main()
