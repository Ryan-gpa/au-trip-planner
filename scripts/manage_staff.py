"""
Staff travel profile manager — Phase 2 connector for au-trip-planner.

Reads and writes `settings.local.json` next to the trip-research skill
(skills/trip-research/settings.local.json), specifically the
`travel_policy.staff` list the SKILL.md reads to resolve a traveler's
tier, frequent flyer numbers, and hotel loyalty numbers.

Zero extra dependencies (stdlib only). Never touches anything outside
that one local file — no network calls, nothing sent anywhere. Frequent
flyer / hotel loyalty numbers are stored so they can be read back and
quoted at booking time for points and record keeping; this script does
not submit them to any airline, hotel, or booking API itself.

Usage:
    python manage_staff.py list
    python manage_staff.py show "Jane Ngo"
    python manage_staff.py add --name "Jane Ngo" --role CEO --tier executive
        [--home-city Sydney]
        [--ff "Qantas Frequent Flyer:1234567"]   (repeatable)
        [--hotel "Accor Live Limitless:998877"]  (repeatable)
        [--note "aisle seat only"]
    python manage_staff.py update --name "Jane Ngo" --tier senior
        (same optional flags as add; only given fields change,
         --ff/--hotel replace that person's full list when passed)
    python manage_staff.py remove --name "Jane Ngo"

Tiers: executive, senior, standard (see references/travel-policy.default.json
for what each tier controls).
"""

import argparse
import json
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent / "skills" / "trip-research"
SETTINGS_PATH = SKILL_DIR / "settings.local.json"
VALID_TIERS = ("executive", "senior", "standard")


def _load_settings():
    if not SETTINGS_PATH.exists():
        return {}
    return json.loads(SETTINGS_PATH.read_text())


def _save_settings(settings):
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2) + "\n")


def _staff_list(settings):
    return settings.setdefault("travel_policy", {}).setdefault("staff", [])


def _find(staff, name):
    name_lower = name.strip().lower()
    for person in staff:
        if person.get("name", "").strip().lower() == name_lower:
            return person
    return None


def _parse_pairs(pairs):
    """Turn ["Program:Number", ...] into [{"program": ..., "number": ...}, ...]."""
    out = []
    for pair in pairs or []:
        if ":" not in pair:
            raise SystemExit(f"Expected 'Program:Number', got: {pair}")
        program, _, number = pair.partition(":")
        out.append({"program": program.strip(), "number": number.strip()})
    return out


def cmd_list(args, settings):
    staff = _staff_list(settings)
    if not staff:
        print("No staff profiles yet. Add one with: manage_staff.py add --name ... --role ... --tier ...")
        return
    for person in staff:
        ff_count = len(person.get("frequent_flyer", []))
        hotel_count = len(person.get("hotel_loyalty", []))
        print(f"{person.get('name')} — {person.get('role', 'no role set')} — tier: {person.get('tier')} "
              f"({ff_count} frequent flyer, {hotel_count} hotel loyalty)")


def cmd_show(args, settings):
    staff = _staff_list(settings)
    person = _find(staff, args.name)
    if not person:
        raise SystemExit(f"No profile found for '{args.name}'. Run 'list' to see who's on file.")
    print(json.dumps(person, indent=2))


def cmd_add(args, settings):
    staff = _staff_list(settings)
    if _find(staff, args.name):
        raise SystemExit(f"'{args.name}' already exists. Use 'update' instead.")
    if args.tier not in VALID_TIERS:
        raise SystemExit(f"--tier must be one of {VALID_TIERS}, got: {args.tier}")

    person = {"name": args.name, "role": args.role or "", "tier": args.tier}
    if args.home_city:
        person["home_city"] = args.home_city
    if args.ff:
        person["frequent_flyer"] = _parse_pairs(args.ff)
    if args.hotel:
        person["hotel_loyalty"] = _parse_pairs(args.hotel)
    if args.note:
        person["notes"] = args.note

    staff.append(person)
    _save_settings(settings)
    print(f"Added {args.name} ({args.tier}) to {SETTINGS_PATH}")


def cmd_update(args, settings):
    staff = _staff_list(settings)
    person = _find(staff, args.name)
    if not person:
        raise SystemExit(f"No profile found for '{args.name}'. Use 'add' instead.")

    if args.role is not None:
        person["role"] = args.role
    if args.tier is not None:
        if args.tier not in VALID_TIERS:
            raise SystemExit(f"--tier must be one of {VALID_TIERS}, got: {args.tier}")
        person["tier"] = args.tier
    if args.home_city is not None:
        person["home_city"] = args.home_city
    if args.ff is not None:
        person["frequent_flyer"] = _parse_pairs(args.ff)
    if args.hotel is not None:
        person["hotel_loyalty"] = _parse_pairs(args.hotel)
    if args.note is not None:
        person["notes"] = args.note

    _save_settings(settings)
    print(f"Updated {args.name} in {SETTINGS_PATH}")


def cmd_remove(args, settings):
    staff = _staff_list(settings)
    person = _find(staff, args.name)
    if not person:
        raise SystemExit(f"No profile found for '{args.name}'.")
    staff.remove(person)
    _save_settings(settings)
    print(f"Removed {args.name} from {SETTINGS_PATH}")


def build_parser():
    parser = argparse.ArgumentParser(description="Manage traveler profiles for au-trip-planner.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List all staff profiles").set_defaults(func=cmd_list)

    p_show = sub.add_parser("show", help="Show one staff profile")
    p_show.add_argument("name")
    p_show.set_defaults(func=cmd_show)

    p_add = sub.add_parser("add", help="Add a new staff profile")
    p_add.add_argument("--name", required=True)
    p_add.add_argument("--role")
    p_add.add_argument("--tier", required=True, choices=VALID_TIERS)
    p_add.add_argument("--home-city")
    p_add.add_argument("--ff", action="append", metavar="Program:Number",
                        help="Frequent flyer program and number, repeatable")
    p_add.add_argument("--hotel", action="append", metavar="Program:Number",
                        help="Hotel loyalty program and number, repeatable")
    p_add.add_argument("--note")
    p_add.set_defaults(func=cmd_add)

    p_update = sub.add_parser("update", help="Update an existing staff profile")
    p_update.add_argument("--name", required=True)
    p_update.add_argument("--role")
    p_update.add_argument("--tier", choices=VALID_TIERS)
    p_update.add_argument("--home-city")
    p_update.add_argument("--ff", action="append", metavar="Program:Number")
    p_update.add_argument("--hotel", action="append", metavar="Program:Number")
    p_update.add_argument("--note")
    p_update.set_defaults(func=cmd_update)

    p_remove = sub.add_parser("remove", help="Remove a staff profile")
    p_remove.add_argument("name")
    p_remove.set_defaults(func=cmd_remove)

    return parser


if __name__ == "__main__":
    parsed = build_parser().parse_args()
    settings = _load_settings()
    parsed.func(parsed, settings)
