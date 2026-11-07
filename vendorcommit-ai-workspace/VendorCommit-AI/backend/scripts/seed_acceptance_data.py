"""Non-destructive fixture loader. Run from backend/: python scripts/seed_acceptance_data.py"""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.acceptance_fixtures import seed_acceptance_story
from app.database import SessionLocal

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--simulate-failure', action='store_true', help='Reset only the labelled QA retry fixture to a simulated failed state.')
    arguments = parser.parse_args()
    with SessionLocal() as db:
        result = seed_acceptance_story(db, simulate_failure=arguments.simulate_failure)
        print('Fictional QA fixtures are present (idempotent counts):', result)
        if arguments.simulate_failure:
            print('The QA-RETRY-RECOVERY fixture is now failed; use its Retry action or the live verifier to recover it.')
