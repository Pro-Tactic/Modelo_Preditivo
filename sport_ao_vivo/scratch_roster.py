import json
from espn_api import get_summary

def main():
    summary = get_summary("401642230") # Current match ID
    rosters = summary.get("rosters") or []
    for roster in rosters:
        for player in roster.get("roster") or []:
            print(json.dumps(player, indent=2))
            return

if __name__ == "__main__":
    main()
