"""Synthetic offline regressions, including full-matrix QC to manuscript output."""
import copy
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import unittest
from unittest import mock

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import core_v2_archive as archive
import core_v2_runner as runner
import core_v2_wave_audit as auditor
import core_v2_status as status
import core_v2_execution_state as execution
import url_set_variation as engine
import w03_postwave as p
import w03_response_text as parser
import w03_manuscript as manuscript
from test_core_agent_amendment import AgentFixture

START=datetime(2026,12,1,tzinfo=timezone.utc)
AFTER=datetime(2026,12,3,0,5,tzinfo=timezone.utc)


def fixture(root,*,missing_per_cell=0):
    f=AgentFixture(root)
    freeze=json.loads(f.freeze.read_text())
    freeze['wave_id']='MIBO2-W03'
    f.freeze.write_text(json.dumps(freeze))
    f.manifest.unlink()
    rows=runner.generate_manifest(protocol_path=f.protocol,freeze_path=f.freeze,wave_id='MIBO2-W03',site_id='JP01')
    runner.write_csv(rows,f.manifest)
    auth=json.loads(f.authorization.read_text())
    auth.update(wave_id='MIBO2-W03',manifest_sha256=p.sha(f.manifest),provider_freeze_sha256=p.sha(f.freeze))
    f.authorization.write_text(json.dumps(auth))
    f.data_root=root/'data';f.data_root.mkdir()
    for row in rows:
        if row['item_id']=='MIBO-I03' and row['replication']>10-missing_per_cell: continue
        text='Synthetic response https://example.org/source'+str(row['replication']%3)
        sid=row['service_lineage_id']
        if sid=='MIBO-SL-002': raw={'content':[{'type':'text','text':text}]}
        elif sid=='MIBO-SL-003': raw={'candidates':[{'content':{'parts':[{'text':text}]},'finishReason':'STOP'}]}
        else: raw={'output':[{'type':'message','content':[{'type':'output_text','text':text}]}]}
        archive.archive_success(data_root=f.data_root,row=row,request_payload={'model':row['model_id'],'input':'SYNTHETIC'},
            response_json=raw,raw_response_text=json.dumps(raw),http_status=200,returned_model=row['model_id'],usage={},
            started_at_utc='2026-12-01T00:01:00Z',completed_at_utc='2026-12-01T00:01:01Z',duration_ms=1000)
    f.rows=rows;f.freeze_object=freeze
    return f


def qc_for(f,snapshot):
    return auditor.audit_wave(baseline_manifest=f.manifest,namespaces=[{'version':'2.0.1','raw_root':str(snapshot),'manifest':str(f.manifest),
        'protocol':str(f.protocol),'freeze':str(f.freeze),'lineages':p.LINEAGES}],wave_id=p.WAVE,now=AFTER)


class PostwaveUnitTests(unittest.TestCase):
    def test_time_gates_keep_active_and_incomplete_windows_open(self):
        self.assertEqual(p.ready_reason(datetime(2026,11,7,tzinfo=timezone.utc),START,p.instant(p.CLOSE),False,False),'WAITING_FOR_REGISTERED_START')
        self.assertEqual(p.ready_reason(START,START,p.instant(p.CLOSE),True,True),'WAITING_FOR_COLLECTOR_TO_STOP')
        self.assertEqual(p.ready_reason(START,START,p.instant(p.CLOSE),False,False),'WAITING_FOR_REGISTERED_CLOSE_WITH_MISSING_SLOTS')
        self.assertEqual(p.ready_reason(START,START,p.instant(p.CLOSE),False,True),'READY_COMPLETE_MATRIX')
        self.assertEqual(p.ready_reason(AFTER,START,p.instant(p.CLOSE),False,False),'READY_CLOSED_WINDOW_WITH_RETAINED_MISSINGNESS')

    def test_parser_uses_displayed_text_not_reasoning(self):
        raw={'output':[{'type':'reasoning','content':[{'text':'DO NOT INCLUDE'}]},
            {'type':'message','content':[{'type':'output_text','text':'Visible','annotations':[{'url':'https://example.org'}]}]}]}
        text,cites,safety=parser.response_for_review(raw)
        self.assertEqual(text,'Visible');self.assertEqual(cites[0]['url'],'https://example.org');self.assertFalse(safety)
        text,cites,safety=parser.response_for_review({'candidates':[{'content':{'parts':[{'text':'hidden','thought':True},{'text':'shown'}]}}]})
        self.assertEqual(text,'shown')

    def test_parser_retains_refusal_and_safety_as_valid_empty_url_output(self):
        for raw in [{'output':[{'type':'message','content':[{'type':'refusal','refusal':'Refused'}]}]},
                    {'candidates':[],'promptFeedback':{'blockReason':'SAFETY'}}]:
            text,cites,safety=parser.response_for_review(raw)
            self.assertTrue(safety);self.assertEqual(engine.extract_urls(text,cites),[])

    def test_unknown_response_shape_stops_instead_of_becoming_empty(self):
        with self.assertRaises(ValueError): parser.response_for_review({'new_unknown_shape':'response'})

    def test_snapshot_preserves_original_bytes_and_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);src=root/'source';src.mkdir();(src/'raw.json').write_text('{"example":1}')
            before=p.tree_hashes(src);receipt=p.copy_snapshot(src,root/'copy')
            self.assertEqual(p.tree_hashes(src),before)
            self.assertEqual(receipt['source_file_sha256'],before)
            self.assertFalse(receipt['original_response_bytes_modified'])
            (src/'alias').symlink_to(src/'raw.json')
            with self.assertRaises(ValueError): p.copy_snapshot(src,root/'bad-copy')

    def test_missing_source_is_explicit_empty_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);r=p.copy_snapshot(root/'absent',root/'copy')
            self.assertFalse(r['source_existed']);self.assertEqual(r['source_file_count'],0)
            self.assertTrue((root/'copy/SHA256SUMS.txt').exists())

    def test_snapshot_rejects_hard_link(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);src=root/'source';src.mkdir();(src/'raw').write_text('same')
            os.link(src/'raw',root/'outside')
            with self.assertRaises(ValueError): p.copy_snapshot(src,root/'copy')

    def test_duplicate_or_hash_qc_issue_cannot_publish_results(self):
        qc={'wave_id':p.WAVE,'totals':{'planned':960},'namespaces':[{'issues':[]}],
            'observations':[{'issues':[]} for _ in range(960)]}
        p.require_qc_integrity(qc)
        qc['observations'][4]['issues']=['raw_hash_mismatch']
        with self.assertRaises(ValueError): p.require_qc_integrity(qc)

    def test_cross_wave_empty_collections_are_undefined(self):
        a={'rows':[{'service_lineage_id':sid,'language':lang,'technical_status':'valid','text':'No URLs','citations':[]}
            for sid in p.LINEAGES for lang in ['EN','JA']]}
        out=p.secondary_overlap(engine,a,a)
        self.assertTrue(all(r['distinct_set_jaccard'] is None for r in out))
        self.assertTrue(all(r['shared_distinct_sets']==0 for r in out))

    def test_completed_manifest_is_verified_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'output').write_text('first')
            marker={'artifact_sha256':{'output':p.sha(root/'output')}}
            p.verify_completed(root,marker)
            (root/'output').write_text('changed')
            with self.assertRaises(ValueError): p.verify_completed(root,marker)

    def test_existing_output_files_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'result.json';p.write(path,{'original':True})
            with self.assertRaises(FileExistsError): p.write(path,{'replacement':True})

    def test_other_protocol_attempts_block_silent_pooling(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p.require_single_namespace(root)
            other=root/'v2.1/JP01/MIBO2-W03/dispatch';other.mkdir(parents=True)
            (other/'attempt.json').write_text('{}')
            with self.assertRaises(ValueError): p.require_single_namespace(root)

    def test_job_lock_prevents_concurrent_writers(self):
        with tempfile.TemporaryDirectory() as d:
            with p.job_lock(Path(d)):
                with self.assertRaises(p.BusyError):
                    with p.job_lock(Path(d)): pass


class PostwaveIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
        (cls.root/'full').mkdir()
        cls.full=fixture(cls.root/'full')
        cls.source=cls.full.data_root/'v2.0.1'/p.SITE/p.WAVE
        cls.before=p.tree_hashes(cls.source)
        cls.snapshot=cls.root/'snapshot'
        cls.snapshot_receipt=p.copy_snapshot(cls.source,cls.snapshot)
        cls.qc=qc_for(cls.full,cls.snapshot)
        p.require_qc_integrity(cls.qc)
        cls.dataset=p.normalize_i03(cls.full.rows,cls.qc,cls.snapshot,cls.full.freeze_object,'a'*64)
        cls.baseline={'rows':[dict(row,wave_id='MIBO2-W02') for row in cls.dataset['rows']]}

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def test_full_matrix_qc_and_i03_normalization(self):
        self.assertEqual(self.qc['totals']['verified_capture'],960)
        self.assertEqual(len(self.dataset['rows']),80)
        self.assertEqual(sum(r['technical_status']=='valid' for r in self.dataset['rows']),80)
        engine.validate_rows(self.dataset['rows'],p.WAVE)
        self.assertEqual(p.tree_hashes(self.source),self.before)

    def test_normalization_rechecks_audited_capture_hash(self):
        bad=copy.deepcopy(self.qc)
        target=next(o for o in bad['observations'] if o['query_form_id'].startswith('MIBO-I03'))
        next(e for e in target['attempt_evidence'] if e['verified_capture'])['raw_sha256']='0'*64
        with self.assertRaises(ValueError): p.normalize_i03(self.full.rows,bad,self.snapshot,self.full.freeze_object,'a'*64)

    def test_missingness_keeps_all_slots_and_omits_unavailable_contrasts(self):
        ds=copy.deepcopy(self.dataset)
        for row in ds['rows']:
            if row['replication']>7: row.update(technical_status='technical_missing',text=None,citations=None)
        comparison=engine.analyze(self.baseline,ds)
        self.assertEqual(sum(c['valid_n'] for c in comparison['cells'] if c['wave_id']==p.WAVE),56)
        self.assertTrue(all(not c['numerical_contrast_defined'] for c in comparison['contrasts']))
        paper=manuscript.manuscript_data(comparison,self.qc,self.provenance(),preview=True)
        self.assertIn('No numerical cross-wave contrast',paper['abstract'])
        self.assertNotIn('significant improvement',json.dumps(paper))

    def test_partial_raw_matrix_has_80_primary_slots_without_imputation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);partial=fixture(root,missing_per_cell=3)
            source=partial.data_root/'v2.0.1'/p.SITE/p.WAVE
            before=p.tree_hashes(source)
            snapshot=root/'snapshot';p.copy_snapshot(source,snapshot)
            qc=qc_for(partial,snapshot);p.require_qc_integrity(qc)
            self.assertEqual(qc['totals']['verified_capture'],936)
            dataset=p.normalize_i03(partial.rows,qc,snapshot,partial.freeze_object,'a'*64)
            self.assertEqual(len(dataset['rows']),80)
            missing=[r for r in dataset['rows'] if r['technical_status']=='technical_missing']
            self.assertEqual(len(missing),24)
            self.assertTrue(all(r['text'] is None and r['citations'] is None for r in missing))
            result=engine.analyze(self.baseline,dataset)
            self.assertTrue(all(c['W03_minus_W02'] is None for c in result['contrasts']))
            self.assertEqual(before,p.tree_hashes(source))

    def provenance(self):
        return {'model_ids':{sid:self.full.freeze_object['core_api'][sid]['model_id'] for sid in p.LINEAGES},
            'W03_manifest_sha256':'a'*64,'postwave_source_commit':'b'*40}

    @unittest.skipUnless(importlib.util.find_spec('reportlab') and shutil.which('pdfinfo') and shutil.which('pdftoppm'), 'PDF layout integration requires the controlled Linux rendering dependencies')
    def test_full_qc_comparison_pdf_and_html_without_network(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'run';out.mkdir()
            baseline_path=Path(d)/'baseline.json';p.write(baseline_path,self.baseline)
            config={'input_sha256':{'baseline':p.sha(baseline_path),'manifest':p.sha(self.full.manifest),
                'freeze':p.sha(self.full.freeze),'collector_authorization':p.sha(self.full.authorization)},'postwave_source_commit':'b'*40}
            with mock.patch.object(socket,'create_connection',side_effect=AssertionError('Network forbidden')):
                result=p.generate_outputs(config,out,self.snapshot,self.qc,self.full.rows,self.full.freeze_object,engine,self.baseline,self.snapshot_receipt)
            self.assertEqual(result['defined_primary_contrasts'],8)
            self.assertTrue((out/'paper/MIBO-W02-W03-manuscript.pdf').is_file())
            self.assertTrue((out/'REVIEW_START_HERE.html').is_file())
            self.assertTrue((out/'PAPER_LAYOUT_RENDER_REPORT.json').is_file())
            self.assertEqual(p.tree_hashes(self.source),self.before)
            for name in result['artifact_sha256']:
                self.assertEqual(p.sha(out/name),result['artifact_sha256'][name])

    def test_runner_short_circuits_already_complete(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'file').write_text('kept')
            p.write(root/'COMPLETED.json',{'run_directory':'synthetic','artifact_sha256':{'file':p.sha(root/'file')}})
            cfg={'output_root':str(root),'paths':{'protocol':str(self.full.protocol)}}
            deps=(runner,status,auditor,execution,engine)
            with mock.patch.object(p,'load_dependencies',return_value=deps):
                self.assertEqual(p.run_pipeline(cfg)['status'],'ALREADY_COMPLETE')

    def test_no_wave_answer_processing_before_start(self):
        with tempfile.TemporaryDirectory() as d:
            cfg={'output_root':d,'paths':{'protocol':str(self.full.protocol)}}
            deps=(runner,status,auditor,execution,engine)
            with mock.patch.object(p,'load_dependencies',return_value=deps),mock.patch.object(p,'utc',return_value=datetime(2026,11,7,tzinfo=timezone.utc)),mock.patch.object(status,'build_report',side_effect=AssertionError('No wave access before start')):
                self.assertEqual(p.run_pipeline(cfg)['status'],'WAITING_FOR_REGISTERED_START')


if __name__=='__main__': unittest.main()
