import argparse
import json

from app.core.db import Base, SessionLocal, engine
from app.workers.jobs import run_collection_pipeline, run_daily_summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Trend Radar maintenance CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db", help="Create database tables")
    subparsers.add_parser("collect-now", help="Run the collection pipeline immediately")
    subparsers.add_parser("send-summary", help="Send the daily summary immediately")

    args = parser.parse_args()

    if args.command == "init-db":
        Base.metadata.create_all(bind=engine)
        print("database_initialized")
        return

    with SessionLocal() as db:
        if args.command == "collect-now":
            result = run_collection_pipeline(db)
            print(json.dumps(result, default=str))
            return
        if args.command == "send-summary":
            result = {"sent": run_daily_summary(db)}
            print(json.dumps(result))
            return


if __name__ == "__main__":
    main()
