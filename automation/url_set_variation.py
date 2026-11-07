#!/usr/bin/env python3
"""Offline, descriptive I03 URL-string analysis; never fetches or grades a source.

Input is a hash-archived, technically audited JSON object with `rows`. Each of
the eight planned lineage/language cells must have its ten logical slots,
including technical missingness. A retry is not an additional observation.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
from itertools import combinations, product
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

URL_RE = re.compile(r'https?://[^\s<>"\]\)]+')
LINEAGES = {f'MIBO-SL-{i:03d}' for i in range(1, 5)}
CELL_FIELDS = ('site_id', 'service_lineage_id', 'item_id', 'language',
               'query_sha256', 'condition', 'window_id')


def extract_urls(text, citations):
    """Exact W02 selection: citation URLs, then text regex; trim, dedup, cap 5."""
    if not isinstance(text, str) or not isinstance(citations, list):
        raise ValueError('Text/citation container type mismatch')
    links = []
    for citation in citations:
        if not isinstance(citation, dict):
            raise ValueError('Citation must be an object')
        value = citation.get('url', '')
        if value and not isinstance(value, str):
            raise ValueError('Citation URL must be a string')
        links.append(value)
    links += URL_RE.findall(text)
    return list(dict.fromkeys(u.rstrip('.,;') for u in links if u))[:5]


def pair_jaccard(a, b):
    a, b = set(a), set(b)
    union = a | b
    return len(a & b) / len(union) if union else None


def mean_pair_jaccard(sets):
    values = [pair_jaccard(a, b) for a, b in combinations(sets, 2)]
    eligible = [v for v in values if v is not None]
    return {'mean': sum(eligible) / len(eligible) if eligible else None,
            'all_pair_count': len(values), 'eligible_pair_count': len(eligible),
            'both_empty_pair_count': len(values) - len(eligible)}


def hostname_set(urls):
    """Lowercase exact hosts; count parse failures without changing URL strings."""
    hosts, errors = set(), 0
    for url in urls:
        try:
            host = urlsplit(url).hostname
        except ValueError:
            host = None
        if host:
            hosts.add(host.lower())
        else:
            errors += 1
    return hosts, errors


def summarize(rows):
    valid = [r for r in rows if r['technical_status'] == 'valid']
    sets = [frozenset(extract_urls(r['text'], r['citations'])) for r in valid]
    hosts = [hostname_set(s) for s in sets]
    n = len(valid)
    return {'planned_n': len(rows), 'valid_n': n, 'technical_missing_n': len(rows)-n,
            'distinct_first_five_url_sets': len(set(sets)),
            'url_free_n': sum(not s for s in sets),
            'url_free_proportion': sum(not s for s in sets)/n if n else None,
            'exact_url_jaccard': mean_pair_jaccard(sets),
            'hostname_jaccard': mean_pair_jaccard([h[0] for h in hosts]),
            'hostname_parse_failure_occurrences': sum(h[1] for h in hosts)}, sets


def leave_one_out_contrast(baseline, prospective):
    """All whole-response omissions; original eligibility is checked by caller."""
    values, undefined = [], 0
    for i, j in product(range(len(baseline)), range(len(prospective))):
        old = mean_pair_jaccard(baseline[:i] + baseline[i+1:])['mean']
        new = mean_pair_jaccard(prospective[:j] + prospective[j+1:])['mean']
        if old is None or new is None:
            undefined += 1
        else:
            values.append(new - old)
    return {'defined_combinations': len(values), 'undefined_combinations': undefined,
            'min': min(values) if values else None, 'max': max(values) if values else None,
            'interpretation': 'descriptive sensitivity range; not a confidence interval'}


def validate_rows(rows, wave):
    if wave not in {'MIBO2-W02', 'MIBO2-W03'} or not isinstance(rows, list):
        raise ValueError('Expected the prespecified wave and row list')
    groups = defaultdict(list)
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or row.get('wave_id') != wave:
            raise ValueError('Wrong wave identity')
        if (row.get('site_id') != 'JP01' or row.get('item_id') != 'MIBO-I03'
                or row.get('condition') != 'ACI' or row.get('window_id') != 'STD'
                or row.get('service_lineage_id') not in LINEAGES
                or row.get('language') not in {'EN','JA'}):
            raise ValueError('Row is outside the fixed primary subset')
        for field in ('query_sha256', 'request_profile_sha256'):
            if not isinstance(row.get(field), str) or not re.fullmatch('[a-f0-9]{64}', row[field]):
                raise ValueError('Missing or invalid configuration digest')
        if not isinstance(row.get('model_id'), str) or not row['model_id']:
            raise ValueError('Missing model identifier')
        rep = row.get('replication')
        if type(rep) is not int or not 1 <= rep <= 10:
            raise ValueError('Replication is not a planned logical slot')
        logical = (row['service_lineage_id'], row['language'], rep)
        if logical in seen:
            raise ValueError('Duplicate logical slot; retries cannot increase n')
        seen.add(logical)
        if row.get('technical_status') not in {'valid','technical_missing'}:
            raise ValueError('Only technical missingness may remove a response')
        if row['technical_status'] == 'valid':
            extract_urls(row.get('text'), row.get('citations'))
        elif row.get('text') not in (None, '') or row.get('citations') not in (None, []):
            raise ValueError('Technical missingness must not carry retained response content')
        groups[(row['service_lineage_id'], row['language'])].append(row)
    if set(groups) != set(product(LINEAGES, ['EN','JA'])) or len(rows) != 80:
        raise ValueError('Include all 80 planned I03 slots, including missing slots')
    for members in groups.values():
        if len(members) != 10 or len({tuple(r[f] for f in CELL_FIELDS) for r in members}) != 1:
            raise ValueError('Cell changes its design identity')
        if len({(r['model_id'],r['request_profile_sha256']) for r in members}) != 1:
            raise ValueError('Do not pool deployments within a cell')
    return groups


def analyze(baseline, prospective=None):
    waves = {'MIBO2-W02': validate_rows(baseline['rows'], 'MIBO2-W02')}
    if prospective is not None:
        waves['MIBO2-W03'] = validate_rows(prospective['rows'], 'MIBO2-W03')
    result = {'schema':'mibo-url-set-variation-1.0', 'additional_human_case_grading':0,
              'hypothesis_tests':None, 'cells':[], 'contrasts':[]}
    summaries, sets = {}, {}
    for wave, groups in waves.items():
        for key, rows in sorted(groups.items()):
            summary, urls = summarize(rows)
            summaries[wave,key], sets[wave,key] = summary, urls
            result['cells'].append({'wave_id':wave, 'service_lineage_id':key[0],
                'language':key[1], 'model_id':rows[0]['model_id'],
                'request_profile_sha256':rows[0]['request_profile_sha256'], **summary})
    if prospective is None:
        result['status'] = 'exploratory_W02_baseline_only_no_W03_contrast'
        return result
    for key, before in sorted(waves['MIBO2-W02'].items()):
        after = waves['MIBO2-W03'][key]
        same_design = all(before[0][f] == after[0][f] for f in CELL_FIELDS)
        same_profile = before[0]['request_profile_sha256'] == after[0]['request_profile_sha256']
        same_model = before[0]['model_id'] == after[0]['model_id']
        old, new = summaries['MIBO2-W02',key], summaries['MIBO2-W03',key]
        eligible = same_design and same_profile and min(old['valid_n'],new['valid_n']) >= 8
        defined = eligible and old['exact_url_jaccard']['mean'] is not None and new['exact_url_jaccard']['mean'] is not None
        result['contrasts'].append({'service_lineage_id':key[0], 'language':key[1],
            'same_design':same_design, 'material_request_profile_equal':same_profile,
            'requested_model_id_equal':same_model,
            'deployment_disclosure':'same_requested_identifier_no_immutable_weight_claim' if same_model and same_profile else 'changed_deployment_or_profile_no_causal_model_update_interpretation',
            'minimum_n_rule_satisfied':min(old['valid_n'],new['valid_n']) >= 8,
            'contrast_eligible':eligible, 'numerical_contrast_defined':defined,
            'W03_minus_W02':new['exact_url_jaccard']['mean']-old['exact_url_jaccard']['mean'] if defined else None,
            'distinct_set_counts_directly_comparable':old['valid_n']==new['valid_n'],
            'leave_one_response_out':leave_one_out_contrast(sets['MIBO2-W02',key],sets['MIBO2-W03',key]) if defined else None})
    result['status'] = 'prospectively_specified_W03_descriptive_comparison'
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--prospective', type=Path)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    baseline_bytes = args.baseline.read_bytes()
    prospective_bytes = args.prospective.read_bytes() if args.prospective else None
    result = analyze(json.loads(baseline_bytes), json.loads(prospective_bytes) if prospective_bytes else None)
    result['input_sha256'] = {'baseline':hashlib.sha256(baseline_bytes).hexdigest(),
        'prospective':hashlib.sha256(prospective_bytes).hexdigest() if prospective_bytes else None}
    with args.out.open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        f.write('\n')
    print(json.dumps({'output':str(args.out),'sha256':hashlib.sha256(args.out.read_bytes()).hexdigest(),'status':result['status']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
