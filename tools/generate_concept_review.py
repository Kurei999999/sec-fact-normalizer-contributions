"""Generate paginated Markdown review queues, separating US-GAAP from other taxonomies."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
import html
import re
from urllib.parse import unquote
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
LINK = '{http://www.xbrl.org/2003/linkbase}'
XLINK = '{http://www.w3.org/1999/xlink}'
XML = '{http://www.w3.org/XML/1998/namespace}'
DOC_ROLE = 'http://www.xbrl.org/2003/role/documentation'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def load_descriptions(directory):
    """Follow XBRL locators and arcs; resource IDs need not match concept names."""
    paths = sorted(directory.rglob('*doc*.xml'))
    if not paths:
        raise ValueError(f'No taxonomy documentation XML found in {directory}')
    descriptions = {}
    for path in paths:
        tree = ET.parse(path)
        for link in tree.iter(LINK+'labelLink'):
            locators = {}
            resources = {}
            for element in link:
                if element.tag == LINK+'loc':
                    fragment = unquote(element.get(XLINK+'href', '').partition('#')[2])
                    taxonomy, separator, tag = fragment.partition('_')
                    if separator:
                        locators[element.get(XLINK+'label')] = taxonomy+':'+tag
                elif element.tag == LINK+'label' and element.get(XLINK+'role') == DOC_ROLE:
                    language = element.get(XML+'lang', '')
                    if language and not language.lower().startswith('en'):
                        continue
                    text = ' '.join(''.join(element.itertext()).split())
                    if text:
                        resources[element.get(XLINK+'label')] = text
            for arc in link.findall(LINK+'labelArc'):
                concept = locators.get(arc.get(XLINK+'from'))
                text = resources.get(arc.get(XLINK+'to'))
                if not concept or not text:
                    continue
                if concept in descriptions and descriptions[concept]['text'] != text:
                    raise ValueError(f'Conflicting definitions for {concept}; select one taxonomy-version directory')
                descriptions[concept] = {'text':text, 'file':path.relative_to(directory).as_posix()}
    if not descriptions:
        raise ValueError('Documentation files contained no usable English concept definitions')
    return descriptions, [p.relative_to(directory).as_posix() for p in paths]


def mapping_locations(repo, profile):
    locations = {}
    assignment = read(repo/'archetypes/sic_to_archetype.json')
    def walk(nodes, statement):
        for node in nodes:
            for concept in node.get('concepts', []):
                locations.setdefault(concept['name'], []).append(f'{statement} / {node["node_id"]}')
            walk(node.get('children', []), statement)
    for statement, relative in assignment['archetypes'][profile]['statements'].items():
        walk(read(repo/relative)['nodes'], statement)
    return locations


def markdown_text(value):
    """Render source labels/definitions as text, not executable HTML or Markdown."""
    text = html.escape(str(value), quote=False).replace("\\", "\\\\")
    return re.sub(r"([`*_\[\]|#])", r"\\\1", text)


def render_markdown(inventory, locations, descriptions, source_files, page_size=100):
    if page_size < 1:
        raise ValueError('Page size must be positive')
    items = sorted(inventory['concepts'], key=lambda item:item['concept'])
    if len({item['concept'] for item in items}) != len(items):
        raise ValueError('Input inventory contains duplicate concepts')
    groups = {'mapped':[], 'unmapped':[], 'other':[]}
    for item in items:
        name = item['concept']
        if not name.startswith('us-gaap:'):
            groups['other'].append(item)
        else:
            groups['mapped' if name in locations else 'unmapped'].append(item)
    profile = inventory['profile_id']
    title = profile.replace('_', ' ').title()
    files = {}
    counts = {key:len(group) for key,group in groups.items()}
    labels = {'mapped':'Mapped US-GAAP concepts', 'unmapped':'Unmapped US-GAAP concepts',
              'other':'Other taxonomies'}
    for kind, entries in groups.items():
        index_name = 'other_taxonomies.md' if kind == 'other' else kind+'_concepts.md'
        lines = [f'# {title}: {labels[kind]}', '',
                 'Source SICs: '+', '.join(inventory['research_scope']['source_sics']), '',
                 f'**{len(entries):,} concepts** · Alphabetical pages of up to {page_size} concepts.', '',
                 '[All industries](../README.md) · [Contribution guide](../../CONTRIBUTING.md)', '',
                 'Generated from the full JSON inventory and current mappings. Submit suggestions through issues; generated files are replaced on refresh.', '',
                 '## Pages', '']
        sections = {}
        if kind == 'other':
            for item in entries:
                sections.setdefault(item['concept'].split(':',1)[0], []).append(item)
            lines += ['These concepts are retained separately, not counted as US-GAAP mapping gaps. Namespace alone does not establish statement placement.', '']
        else:
            sections[kind] = entries
        if not entries:
            lines += ['No concepts in this category.', '']
        for section, section_items in sections.items():
            if kind == 'other':
                lines += ['### '+markdown_text(section), '']
            safe_section = re.sub(r'[^a-zA-Z0-9_-]', '_', section)
            for offset in range(0,len(section_items),page_size):
                number = offset//page_size+1
                chunk = section_items[offset:offset+page_size]
                relative = (f'pages/other-{safe_section}-{number:03d}.md' if kind == 'other'
                            else f'pages/{kind}-{number:03d}.md')
                range_label = markdown_text(chunk[0]['concept'])+' → '+markdown_text(chunk[-1]['concept'])
                lines.append(f'- [Page {number}: {range_label}]({relative}) ({len(chunk)} concepts)')
                body = [f'# {title}: {labels[kind]}', '',
                        f'[Back to index](../{index_name}) · [How to contribute](../../../CONTRIBUTING.md)', '',
                        'Taxonomy documentation: '+', '.join(markdown_text(f) for f in source_files)+'.', '',
                        'Definitions are reference-version documentation; historical concepts may differ. Missing definitions are never guessed. Original publisher notices apply.', '']
                for item in chunk:
                    name = item['concept']
                    body += ['### '+markdown_text(name), '',
                             '**Label:** '+markdown_text(item.get('label',name)), '']
                    definition = descriptions.get(name)
                    body += ['**Description:** '+markdown_text(definition['text'] if definition else 'No description found in the supplied taxonomy documentation.'), '']
                    mapped = locations.get(name)
                    if mapped:
                        body += ['**Mapped to:** '+markdown_text('; '.join(mapped)), '']
                    elif kind == 'unmapped':
                        body += ['**Review:** Suggest a statement/category, or explain why this belongs outside primary statements. Include your reasoning and filing evidence.', '']
                    else:
                        body += ['**Review:** Separate taxonomy review; not a US-GAAP mapping gap.', '']
                files[relative] = '\n'.join(body)+'\n'
            lines += ['']
        files[index_name] = '\n'.join(lines)+'\n'
    return files, counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--taxonomy-dir', type=Path, required=True, help='One taxonomy version, e.g. data/taxonomy/us-gaap/2026')
    parser.add_argument('--repo-root', type=Path, default=ROOT)
    parser.add_argument('--source', type=Path, help='Optional raw DB: refresh inventories from source_sics before rendering')
    parser.add_argument('--profiles', nargs='+', help='Default: all archetypes')
    parser.add_argument('--page-size', type=int, default=100)
    args = parser.parse_args()
    if args.page_size < 1: parser.error('--page-size must be positive')
    repo = args.repo_root.expanduser().resolve()
    taxonomy = args.taxonomy_dir.expanduser().resolve()
    descriptions, source_files = load_descriptions(taxonomy)
    profiles = list(read(repo/'archetypes/sic_to_archetype.json')['archetypes'])
    if args.profiles:
        if set(args.profiles)-set(profiles):parser.error('Unknown archetype')
        profiles = list(dict.fromkeys(args.profiles))
    if args.source:
        source = args.source.expanduser().resolve()
        if not source.is_file():parser.error('Source database does not exist')
        command = [sys.executable, str(Path(__file__).with_name('generate_concept_inventory.py')),
                   '--source', str(source), '--repo-root', str(repo), '--profiles', *profiles]
        subprocess.run(command, check=True)
    # Prepare all files first; never leave half a rendered file after a failure.
    outputs = []
    for profile in profiles:
        path = repo/'review'/profile/'all_concepts.json'
        if not path.is_file():
            parser.error(f'Missing inventory: {path}. Generate the source-SIC inventory first.')
        inventory = read(path)
        locations = mapping_locations(repo, profile)
        rendered, counts = render_markdown(inventory, locations, descriptions, source_files, args.page_size)
        outputs.append((path.parent, rendered))
        print(f'{profile}: {counts["mapped"]} mapped US-GAAP, {counts["unmapped"]} unmapped US-GAAP, {counts["other"]} other-taxonomy concepts')
    for directory, rendered in outputs:
        for relative, text in rendered.items():
            path = directory/relative
            path.parent.mkdir(exist_ok=True)
            temporary = path.with_suffix('.md.tmp')
            temporary.write_text(text,encoding='utf-8');temporary.replace(path)
        # Delete only obsolete pages owned by this generator and replaced text views.
        for path in (directory/'pages').glob('*.md'):
            if path.name.startswith(('mapped-', 'unmapped-', 'other-')) and str(path.relative_to(directory)) not in rendered:
                path.unlink()
        for name in ['concepts.txt','mapped_concepts.txt','unmapped_concepts.txt']:
            (directory/name).unlink(missing_ok=True)
    print('Created linked Markdown indexes and pages. JSON inventories and source data were preserved.')



if __name__=='__main__':main()
