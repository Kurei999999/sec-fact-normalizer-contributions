"""Check canonical industry JSON formatting; use --write to apply it."""
import argparse
import json
from pathlib import Path
from archetype_format import canonical_statement, validate_format

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write',action='store_true')
    args=parser.parse_args()
    assignment=json.loads((ROOT/'archetypes/sic_to_archetype.json').read_text())
    changed=[]
    for profile in assignment['archetypes'].values():
        for relative in profile['statements'].values():
            path=ROOT/relative
            document=canonical_statement(json.loads(path.read_text()))
            errors=validate_format(document)
            if errors:raise ValueError(f'{relative}: {errors}')
            expected=json.dumps(document,ensure_ascii=False,indent=2)+'\n'
            if path.read_text()!=expected:
                changed.append(relative)
                if args.write:path.write_text(expected,encoding='utf-8')
    for relative in changed:print(('Formatted: ' if args.write else 'Needs formatting: ')+relative)
    print(f'{len(changed)} files '+('formatted.' if args.write else 'need formatting.'))
    return bool(changed) and not args.write


if __name__=='__main__':raise SystemExit(main())
