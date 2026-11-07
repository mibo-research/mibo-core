"""Synthetic checks of scientific edge cases, with no provider calls."""
import copy
import itertools
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import url_set_variation as u


def dataset(wave='MIBO2-W02', n=10):
    rows=[]
    for lineage, language, rep in itertools.product(sorted(u.LINEAGES), ['EN','JA'], range(1,11)):
        rows.append({'wave_id':wave, 'site_id':'JP01','service_lineage_id':lineage,
            'item_id':'MIBO-I03','language':language,'query_sha256':('a' if language=='EN' else 'b')*64,
            'condition':'ACI','window_id':'STD','replication':rep,
            'model_id':'synthetic','request_profile_sha256':'c'*64,
            'technical_status':'valid' if rep<=n else 'technical_missing',
            'text':'https://example.org/a' if rep<=n else None,
            'citations':[] if rep<=n else None})
    return {'rows':rows}


class URLSetVariationTests(unittest.TestCase):
    def test_w02_extraction_order_trim_deduplicate_cap(self):
        cites=[{'url':'https://e.test/a;'}, {'url':'https://e.test/a'}]
        text='https://e.test/b). https://e.test/c, https://e.test/d; https://e.test/e https://e.test/f'
        self.assertEqual(u.extract_urls(text,cites),['https://e.test/'+x for x in 'abcde'])

    def test_exact_string_parameters_and_case_are_not_normalized(self):
        self.assertEqual(len(u.extract_urls('https://E.test/x?a=1 https://e.test/x?a=2',[])),2)
        self.assertEqual(u.pair_jaccard({'https://E.test/x'},{'https://e.test/x'}),0)

    def test_empty_pair_definitions(self):
        self.assertIsNone(u.pair_jaccard(set(),set()))
        self.assertEqual(u.pair_jaccard(set(),{'a'}),0)
        self.assertIsNone(u.mean_pair_jaccard([set(),set()])['mean'])
        self.assertEqual(u.mean_pair_jaccard([set(),set(),{'a'}]),{'mean':0.0,'all_pair_count':3,'eligible_pair_count':2,'both_empty_pair_count':1})

    def test_hostname_preserves_subdomains_and_counts_bad_parse(self):
        hosts, errors=u.hostname_set(['https://A.Example.org/x','https://example.org/y','https://[bad'])
        self.assertEqual(hosts,{'a.example.org','example.org'})
        self.assertEqual(errors,1)

    def test_complete_design_and_zero_difference(self):
        r=u.analyze(dataset(),dataset('MIBO2-W03'))
        self.assertEqual(len(r['cells']),16)
        self.assertEqual(len(r['contrasts']),8)
        for cell in r['contrasts']:
            self.assertEqual(cell['W03_minus_W02'],0)
            self.assertEqual(cell['leave_one_response_out']['defined_combinations'],100)

    def test_missingness_min8_is_held_fixed_during_omissions(self):
        r=u.analyze(dataset(n=8),dataset('MIBO2-W03',n=8))
        self.assertTrue(r['contrasts'][0]['contrast_eligible'])
        self.assertEqual(r['contrasts'][0]['leave_one_response_out']['defined_combinations'],64)
        r=u.analyze(dataset(n=7),dataset('MIBO2-W03'))
        self.assertFalse(r['contrasts'][0]['contrast_eligible'])
        self.assertIsNone(r['contrasts'][0]['W03_minus_W02'])

    def test_refusals_remain_valid_url_free(self):
        d=dataset()
        for r in d['rows']:
            r['text']='I cannot answer this request.'
        out=u.analyze(d)
        self.assertEqual(out['cells'][0]['valid_n'],10)
        self.assertEqual(out['cells'][0]['url_free_n'],10)
        self.assertIsNone(out['cells'][0]['exact_url_jaccard']['mean'])

    def test_undefined_omission_combinations_are_counted(self):
        r=u.leave_one_out_contrast([set(),set(),{'a'}],[{'a'},{'a'},{'a'}])
        self.assertEqual(r['undefined_combinations'],3)
        self.assertEqual(r['defined_combinations'],6)

    def test_profile_change_is_not_silently_compared(self):
        after=dataset('MIBO2-W03')
        for row in after['rows']:
            row['request_profile_sha256']='d'*64
        r=u.analyze(dataset(),after)
        self.assertFalse(r['contrasts'][0]['contrast_eligible'])
        self.assertIsNone(r['contrasts'][0]['W03_minus_W02'])

    def test_model_change_is_disclosed(self):
        after=dataset('MIBO2-W03')
        for row in after['rows']:
            row['model_id']='different-synthetic'
        c=u.analyze(dataset(),after)['contrasts'][0]
        self.assertFalse(c['requested_model_id_equal'])
        self.assertTrue(c['contrast_eligible'])
        self.assertIn('changed_deployment',c['deployment_disclosure'])

    def test_query_mismatch_prevents_contrast(self):
        after=dataset('MIBO2-W03')
        for row in after['rows']:
            row['query_sha256']='d'*64
        self.assertFalse(u.analyze(dataset(),after)['contrasts'][0]['contrast_eligible'])

    def test_duplicate_retry_missing_slot_and_within_cell_pool_rejected(self):
        for change in ['duplicate','missing','mixed_model']:
            d=dataset()
            if change=='duplicate':
                d['rows'].append(copy.deepcopy(d['rows'][0]))
            elif change=='missing':
                d['rows'].pop()
            else:
                d['rows'][0]['model_id']='mixed'
            with self.assertRaises(ValueError):
                u.analyze(d)

    def test_unequal_n_distinct_counts_not_directly_compared(self):
        c=u.analyze(dataset(n=9),dataset('MIBO2-W03'))['contrasts'][0]
        self.assertFalse(c['distinct_set_counts_directly_comparable'])

    def test_reordering_responses_does_not_make_replication_paired(self):
        a, b=dataset(), dataset('MIBO2-W03')
        b['rows'].reverse()
        self.assertTrue(all(c['W03_minus_W02']==0 for c in u.analyze(a,b)['contrasts']))


if __name__=='__main__':
    unittest.main()
