"""Build the static website with trees rendered from current mapping JSON."""
import json
from pathlib import Path
import shutil

from print_mapping_tree import render_tree

ROOT = Path(__file__).resolve().parents[1]


def main():
    output = ROOT / '_site'
    output.mkdir(exist_ok=True)
    # Copy page assets; the tree bundle is regenerated below.
    for name in ('index.html', 'styles.css', 'app.js'):
        shutil.copyfile(ROOT / 'website' / name, output / name)
    assignment = json.loads((ROOT / 'archetypes/sic_to_archetype.json').read_text())
    profiles = []
    tree_texts = {}
    count = 0
    for profile, info in assignment['archetypes'].items():
        statements = {}
        for statement, relative in info['statements'].items():
            document = json.loads((ROOT / relative).read_text())
            filename = f'{profile}_{statement.lower()}.txt'
            text = render_tree(document)
            tree_texts[f'trees/{filename}'] = text
            statements[statement] = f'trees/{filename}'
            count += 1
        profiles.append({'id': profile, 'label': profile.replace('_', ' ').title(), 'statements': statements})
    bundle = 'window.mappingTrees = ' + json.dumps({'profiles': profiles, 'texts': tree_texts}, ensure_ascii=False) + ';\n'
    (ROOT / 'website/mapping-trees.js').write_text(bundle, encoding='utf-8')
    (output / 'mapping-trees.js').write_text(bundle, encoding='utf-8')
    print(f'Built {output}: {count} mapping trees from current JSON.')


if __name__ == '__main__':
    main()
