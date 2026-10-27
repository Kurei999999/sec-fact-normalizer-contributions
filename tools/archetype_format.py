"""Canonical industry-statement file layout; no accounting inference."""
from copy import deepcopy

VERSION = '1.4.0'
TOP_FIELDS = (
    'schema_version', 'profile_id', 'statement', 'status', 'validation_profile',
    'description', 'mapping_rules', 'classification_notes', 'metadata_contract',
    'taxonomy_reference', 'sources', 'metadata_notes', 'nodes', 'unmapped_placeholders',
)
NODE_FIELDS = (
    'node_id', 'metric_id', 'label', 'node_kind', 'aggregation_policy',
    'period_type', 'unit_type', 'contra', 'taxonomy_type', 'classification_note',
    'concepts', 'children',
)
CONCEPT_FIELDS = ('name', 'status', 'review_reason')


def canonical_node(node):
    unknown = set(node) - set(NODE_FIELDS)
    if unknown:
        raise ValueError(f'Unrecognized node fields: {sorted(unknown)}')
    defaults = dict(period_type=None, unit_type=None, contra=None, taxonomy_type=None,
                    classification_note='', concepts=[], children=[])
    values = {**defaults, **deepcopy(node)}
    concepts = []
    for concept in values['concepts']:
        if set(concept) - set(CONCEPT_FIELDS):
            raise ValueError('Unrecognized concept fields')
        concepts.append({k: concept.get(k) for k in CONCEPT_FIELDS})
    values['concepts'] = concepts
    values['children'] = [canonical_node(child) for child in values['children']]
    return {k: values[k] for k in NODE_FIELDS}


def canonical_statement(document):
    legacy = {'source_reference', 'presentation_reference'}
    if set(document) - set(TOP_FIELDS) - legacy:
        raise ValueError('Unrecognized statement metadata fields')
    defaults = dict(validation_profile='industry_statement', classification_notes=[],
                    metadata_contract={}, taxonomy_reference={}, sources=[],
                    metadata_notes={}, unmapped_placeholders=[])
    values = {**defaults, **deepcopy(document), 'schema_version': VERSION}
    for key in sorted(legacy):
        if key in document:
            values['sources'].append({'role': key, 'details': deepcopy(document[key])})
    values['mapping_rules'] = dict(sorted(values['mapping_rules'].items()))
    values['nodes'] = [canonical_node(n) for n in values['nodes']]
    values['unmapped_placeholders'] = [canonical_node(n) for n in values['unmapped_placeholders']]
    return {k: values[k] for k in TOP_FIELDS}


def validate_format(document):
    errors = []
    if tuple(document) != TOP_FIELDS:
        errors.append('Statement fields/order do not match schema 1.4.0')
    if document.get('schema_version') != VERSION:
        errors.append('Expected schema_version 1.4.0')
    for key in ['classification_notes', 'sources', 'nodes', 'unmapped_placeholders']:
        if not isinstance(document.get(key), list):errors.append(f'{key} must be an array')
    for key in ['mapping_rules','metadata_contract','taxonomy_reference','metadata_notes']:
        if not isinstance(document.get(key), dict):errors.append(f'{key} must be an object')
    if document.get('statement') not in {'IS','BS','CF'}:errors.append('Invalid statement')
    for key in ['profile_id','status','validation_profile','description']:
        if not isinstance(document.get(key),str) or not document[key].strip():errors.append(f'{key} must be nonempty text')
    if not document.get('nodes'):errors.append('nodes must not be empty')
    def walk(nodes, placeholder=False):
        if not isinstance(nodes,list):return
        for node in nodes:
            if not isinstance(node,dict):errors.append('Node must be an object');continue
            name=node.get('node_id','?')
            if tuple(node)!=NODE_FIELDS:errors.append(f'{name}: noncanonical node fields/order')
            kind=node.get('node_kind')
            if kind not in ({'group','total','line_item','analytical'} if placeholder else {'group','total','line_item'}):errors.append(f'{name}: invalid node_kind')
            if not isinstance(node.get('label'),str) or not node['label'].strip():errors.append(f'{name}: missing label')
            if kind=='group':
                if any(node.get(k) is not None for k in ['metric_id','period_type','unit_type','contra','taxonomy_type']):errors.append(f'{name}: group fact metadata must be null')
                if node.get('concepts'):errors.append(f'{name}: group must not hold concepts')
            elif not placeholder:
                if node.get('period_type') not in {'instant','duration'}:errors.append(f'{name}: invalid period_type')
                if node.get('unit_type') not in {'monetary','shares','per_share','percent','ratio'}:errors.append(f'{name}: invalid unit_type')
                if type(node.get('contra')) is not bool:errors.append(f'{name}: contra must be boolean')
                if not node.get('concepts'):errors.append(f'{name}: no concepts')
            if kind=='line_item' and node.get('children'):errors.append(f'{name}: line_item must be a leaf')
            if node.get('aggregation_policy')!='none':errors.append(f'{name}: aggregation_policy must be none')
            if node.get('taxonomy_type') is not None and not isinstance(node['taxonomy_type'],str):errors.append(f'{name}: invalid taxonomy_type')
            if not isinstance(node.get('classification_note'),str):errors.append(f'{name}: classification_note must be text')
            if not isinstance(node.get('concepts'),list):errors.append(f'{name}: concepts must be an array')
            else:
                for c in node['concepts']:
                    if not isinstance(c,dict) or tuple(c)!=CONCEPT_FIELDS:
                        errors.append(f'{name}: noncanonical concept fields/order');continue
                    if c.get('status') not in {'proposed','review'}:errors.append(f'{name}: invalid concept status')
                    reason=c.get('review_reason')
                    if reason is not None and not isinstance(reason,str):errors.append(f'{name}: review_reason must be text or null')
                    if c.get('status')=='review' and (not isinstance(reason,str) or not reason.strip()):errors.append(f'{name}: review requires a reason')
            if not isinstance(node.get('children'),list):errors.append(f'{name}: children must be an array')
            walk(node.get('children'),placeholder)
    walk(document.get('nodes'))
    walk(document.get('unmapped_placeholders'),True)
    return errors
