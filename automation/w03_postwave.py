#!/usr/bin/env python3
"""Offline W03 snapshot, technical QC, registered comparison and first draft.

Production runs are bound to the exact frozen Core source, inputs, private PI
policy and URL-analysis implementation. This process never submits a prompt.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
import csv
from datetime import datetime, timezone
import fcntl
import hashlib
import html
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tarfile
import uuid

import w03_response_text
import w03_manuscript

WAVE='MIBO2-W03'
SITE='JP01'
CORE_COMMIT='d970efab834f193b7f3d12ecded20be6f0e8f445'
ENGINE_SHA='914b61672d66ca0dd21f3bd4a89e70dd5d7589d4322f3106e95b9f32535216a6'
START='2026-12-01T00:00:00Z'
CLOSE='2026-12-03T00:00:00Z'
LINEAGES=[f'MIBO-SL-{i:03d}' for i in range(1,5)]


class PipelineError(ValueError):
    pass


class BusyError(PipelineError):
    pass


def utc(): return datetime.now(timezone.utc)
def iso(t): return t.astimezone(timezone.utc).isoformat().replace('+00:00','Z')
def instant(value): return datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(timezone.utc)
def encoded(value): return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()


def regular(path):
    p=Path(path)
    if not p.is_absolute() or not p.is_file() or any(q.is_symlink() for q in (p,*p.parents)):
        raise PipelineError('Expected an absolute regular non-symlink input')
    return p


def read_json(path):
    with Path(path).open(encoding='utf-8') as f: return json.load(f)


def write(path,value):
    p=Path(path)
    p.parent.mkdir(parents=True,exist_ok=True)
    data=value if isinstance(value,bytes) else encoded(value)
    with p.open('xb') as f:
        f.write(data);f.flush();os.fsync(f.fileno())
    os.chmod(p,0o600)
    return sha(p)


@contextmanager
def job_lock(output_root):
    p=Path(output_root)/'.postwave.lock'
    if p.is_symlink(): raise PipelineError('Postwave lock must not be a symlink')
    fd=os.open(p,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc: raise BusyError('Another postwave process holds the lock') from exc
        yield
    finally: os.close(fd)


def tree_hashes(root):
    root=Path(root)
    if not root.exists(): return {}
    if root.is_symlink() or not root.is_dir(): raise PipelineError('Source tree is not a real directory')
    result={}
    for p in sorted(root.rglob('*')):
        info=p.lstat()
        rel=p.relative_to(root).as_posix()
        if p.is_symlink() or not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
            raise PipelineError('Snapshot rejects symlinks and special files')
        if any(ord(c)<32 or c=='\\' for c in rel): raise PipelineError('Unsafe snapshot filename')
        if stat.S_ISREG(info.st_mode):
            if info.st_nlink!=1: raise PipelineError('Snapshot rejects hard-linked source files')
            result[rel]=sha(p)
    return result


def copy_snapshot(source,destination):
    source,destination=Path(source),Path(destination)
    before=tree_hashes(source)
    destination.mkdir(parents=True,exist_ok=False)
    for name,digest in before.items():
        p=destination/name
        p.parent.mkdir(parents=True,exist_ok=True)
        with (source/name).open('rb') as src,p.open('xb') as dst:
            shutil.copyfileobj(src,dst,1024*1024);dst.flush();os.fsync(dst.fileno())
        os.chmod(p,0o600)
        if sha(p)!=digest: raise PipelineError('Snapshot copy hash mismatch')
    if before!=tree_hashes(source): raise PipelineError('Raw source changed during snapshot')
    if not (destination/'SHA256SUMS.txt').exists():
        write(destination/'SHA256SUMS.txt',''.join(f'{d}  {name}\n' for name,d in sorted(before.items())).encode())
    receipt={'source_existed':source.exists(),'source_file_count':len(before),'source_file_sha256':before,
             'copied_tree_sha256':tree_hashes(destination),'snapshot_kind':'automatic_derivative_copy_not_human_signed_native_closure',
             'original_response_bytes_modified':False}
    return receipt


def require_qc_integrity(qc):
    if qc.get('wave_id')!=WAVE or qc['totals']['planned']!=960:
        raise PipelineError('Technical QC has a wrong design or wave')
    if len(qc.get('observations',[]))!=960:
        raise PipelineError('Technical QC must account for all 960 logical slots')
    if any(ns.get('issues') or ns.get('malformed_evidence_records') or ns.get('unlinked_raw_sha256') for ns in qc['namespaces']):
        raise PipelineError('Namespace integrity or malformed evidence prevents analysis')
    if any(obs.get('issues') for obs in qc['observations']):
        raise PipelineError('Capture integrity or retry-evidence anomaly prevents analysis')


def normalize_i03(rows,qc,snapshot,freeze,qc_sha):
    observations={o['initial_attempt_id']:o for o in qc['observations']}
    output=[]; returned=Counter()
    for row in rows:
        if row['item_id']!='MIBO-I03': continue
        slot=observations[row['attempt_id']]
        cfg=freeze['core_api'][row['service_lineage_id']]
        profile=hashlib.sha256(json.dumps(cfg['request_profile'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        result={'wave_id':WAVE,'site_id':SITE,'service_lineage_id':row['service_lineage_id'],'item_id':'MIBO-I03','language':row['language'],
            'query_sha256':row['query_sha256'],'condition':'ACI','window_id':row['window_id'],'replication':int(row['replication']),
            'model_id':row['model_id'],'request_profile_sha256':profile,'technical_status':'technical_missing','text':None,'citations':None,
            'technical_state':slot['status'],'initial_attempt_id':row['attempt_id'],'technical_audit_sha256':qc_sha}
        if slot['status']=='verified_capture':
            valid=[e for e in slot['attempt_evidence'] if e.get('verified_capture') is True]
            if len(valid)!=1: raise PipelineError('A logical slot has no unique verified response')
            capture=valid[0]
            aid=capture['attempt_id']
            if '/' in aid or '\\' in aid or aid in ('.','..'): raise PipelineError('Unsafe capture identifier')
            raw=Path(snapshot)/'api_raw'/(aid+'.json')
            if sha(regular(raw))!=capture['raw_sha256']: raise PipelineError('Audited response bytes changed')
            envelope=read_json(raw)
            if envelope['attempt_id']!=aid or envelope['item_id']!='MIBO-I03' or envelope['model_id_requested']!=row['model_id']:
                raise PipelineError('Normalized response identity mismatch')
            text,citations,safety=w03_response_text.response_for_review(envelope['raw_response'])
            result.update(technical_status='valid',text=text,citations=citations,selected_attempt_id=aid,
                raw_response_sha256=capture['raw_sha256'],provider_safety_signal=safety)
            returned[(row['service_lineage_id'],row['language'],str(envelope.get('model_id_returned')))]+=1
        output.append(result)
    if len(output)!=80: raise PipelineError('The normalized I03 subset must preserve 80 planned slots')
    return {'schema':'mibo-i03-url-input-1.0','wave_id':WAVE,'technical_audit_sha256':qc_sha,'rows':output,
        'returned_identifier_counts':[{'service_lineage_id':a,'language':b,'returned_identifier':c,'n':n} for (a,b,c),n in sorted(returned.items())]}


def secondary_overlap(engine,baseline,prospective):
    output=[]
    for sid in LINEAGES:
        for lang in ['EN','JA']:
            collections=[]
            for wave in [baseline,prospective]:
                sets={frozenset(engine.extract_urls(r['text'],r['citations'])) for r in wave['rows']
                    if r['service_lineage_id']==sid and r['language']==lang and r['technical_status']=='valid'}
                sets.discard(frozenset())
                collections.append(sets)
            old,new=collections
            union=old|new
            output.append({'service_lineage_id':sid,'language':lang,'shared_distinct_sets':len(old&new),
                'W02_nonempty_distinct_sets':len(old),'W03_nonempty_distinct_sets':len(new),
                'distinct_set_jaccard':len(old&new)/len(union) if union else None,
                'url_free_response_sets_excluded':True,'analysis_status':'exploratory'})
    return output


def write_csv(path,records,fields):
    with Path(path).open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for row in records: w.writerow({key:row.get(key) for key in fields})


def write_comparison_csv(analysis,path):
    cells={(r['wave_id'],r['service_lineage_id'],r['language']):r for r in analysis['cells']}
    rows=[]
    for c in analysis['contrasts']:
        old,new=(cells[w,c['service_lineage_id'],c['language']] for w in ['MIBO2-W02','MIBO2-W03'])
        loo=c['leave_one_response_out'] or {}
        rows.append({'service_lineage_id':c['service_lineage_id'],'language':c['language'],'W02_n':old['valid_n'],'W03_n':new['valid_n'],
            'W02_J':old['exact_url_jaccard']['mean'],'W03_J':new['exact_url_jaccard']['mean'],'W03_minus_W02':c['W03_minus_W02'],
            'numerical_contrast_defined':c['numerical_contrast_defined'],'sensitivity_min':loo.get('min'),'sensitivity_max':loo.get('max'),
            'undefined_omission_combinations':loo.get('undefined_combinations'),'deployment_disclosure':c['deployment_disclosure']})
    write_csv(path,rows,list(rows[0]))


def ready_reason(now,start,close,collector_active,complete):
    if now<start: return 'WAITING_FOR_REGISTERED_START'
    if collector_active: return 'WAITING_FOR_COLLECTOR_TO_STOP'
    if complete: return 'READY_COMPLETE_MATRIX'
    if now<close: return 'WAITING_FOR_REGISTERED_CLOSE_WITH_MISSING_SLOTS'
    return 'READY_CLOSED_WINDOW_WITH_RETAINED_MISSINGNESS'


def unit_state(unit):
    if unit!='mibo-core-v2-w03.service': raise PipelineError('Unexpected collector unit')
    out=subprocess.run(['systemctl','show',unit,'--property=ActiveState,SubState,MainPID'],capture_output=True,text=True,check=True)
    return dict(line.split('=',1) for line in out.stdout.strip().splitlines())


def require_single_namespace(data_root):
    for root in Path(data_root).glob('v*/'+SITE+'/'+WAVE):
        if root.parent.parent.name=='v2.0.1': continue
        if any(list((root/folder).glob('*.json')) for folder in ['api_raw','failures','dispatch','dispatches']):
            raise PipelineError('Another protocol namespace contains W03 attempts; automatic pooling is forbidden')


def load_dependencies(config):
    core=Path(config['core_source_root'])
    sys.path.insert(0,str(core/'automation'))
    import runtime_health
    import core_v2_runner
    import core_v2_status
    import core_v2_wave_audit
    import core_v2_execution_state
    state=runtime_health.provenance_state(core)
    if state.get('snapshot_integrity_pass') is not True or state.get('commit_sha')!=CORE_COMMIT:
        raise PipelineError('Frozen collector source integrity failed')
    extension=Path(__file__).resolve().parents[1]
    code=runtime_health.provenance_state(extension)
    if code.get('snapshot_integrity_pass') is not True or code.get('commit_sha')!=config['postwave_source_commit']:
        raise PipelineError('Postwave installed source integrity failed')
    path=regular(config['paths']['analysis_engine'])
    if sha(path)!=ENGINE_SHA: raise PipelineError('Registered analysis implementation changed')
    spec=importlib.util.spec_from_file_location('_mibo_w03_registered_url_engine',path)
    engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)
    return core_v2_runner,core_v2_status,core_v2_wave_audit,core_v2_execution_state,engine


def load_config(path,expected_sha):
    if sha(regular(path))!=expected_sha: raise PipelineError('Installed configuration hash mismatch')
    cfg=read_json(path)
    if cfg.get('schema')!='mibo-w03-postwave-config-1' or cfg.get('wave_id')!=WAVE or cfg.get('site_id')!=SITE:
        raise PipelineError('Wrong postwave configuration identity')
    if cfg.get('additional_human_case_grading')!=0 or cfg.get('provider_model_calls_authorized') is not False:
        raise PipelineError('Postwave scope must remain offline with zero added case grading')
    for name,digest in cfg['input_sha256'].items():
        if sha(regular(cfg['paths'][name]))!=digest: raise PipelineError('A frozen postwave input changed: '+name)
    auth=read_json(cfg['paths']['postwave_authorization'])
    if auth.get('authorized') is not True or auth.get('wave_id')!=WAVE or auth.get('additional_human_case_grading')!=0:
        raise PipelineError('Actual private postwave policy authorization is missing')
    return cfg


def verify_completed(root,marker):
    for rel,digest in marker['artifact_sha256'].items():
        p=Path(root)/rel
        if not p.resolve().is_relative_to(Path(root).resolve()) or p.is_symlink() or sha(p)!=digest:
            raise PipelineError('Completed output changed; do not regenerate silently')


def generate_outputs(cfg,run,snapshot,qc,rows,freeze,engine,baseline,source_snapshot):
    qc_sha=write(run/'TECHNICAL_QC.json',qc)
    write_csv(run/'TECHNICAL_QC_STATUS.csv',qc['observations'],['initial_attempt_id','service_lineage_id','query_form_id','language','window_id','status','submitted_confirmed'])
    require_qc_integrity(qc)
    prospective=normalize_i03(rows,qc,snapshot,freeze,qc_sha)
    normalized_sha=write(run/'W03-I03-normalized.private.json',prospective)
    engine.validate_rows(prospective['rows'],WAVE)
    analysis=engine.analyze(baseline,prospective)
    baseline_identifiers=read_json(cfg['paths']['baseline_returned_identifiers'])['rows'] if cfg.get('paths',{}).get('baseline_returned_identifiers') else []
    analysis['returned_identifier_metadata']={'W02':baseline_identifiers,'W03':prospective['returned_identifier_counts'],
        'interpretation':'Literal returned identifier metadata; unchanged identifiers do not establish unchanged hosted weights'}
    analysis['exploratory_cross_wave_set_overlap']=secondary_overlap(engine,baseline,prospective)
    analysis['input_sha256']={'baseline':cfg['input_sha256']['baseline'],'prospective':normalized_sha,'technical_qc':qc_sha,'analysis_engine':ENGINE_SHA}
    analysis_sha=write(run/'W02-W03-URL-COMPARISON.json',analysis)
    write_comparison_csv(analysis,run/'W02-W03-URL-COMPARISON.csv')
    write(run/'DERIVATIVE_SNAPSHOT_RECEIPT.json',source_snapshot)
    provenance={'analysis_registration_commit':'d7438c82552b71d9837de5aac90fc4c1b5d14623','registered_analysis_sha256':ENGINE_SHA,
        'W03_manifest_sha256':cfg['input_sha256']['manifest'],'W03_freeze_sha256':cfg['input_sha256']['freeze'],
        'W03_collector_authorization_sha256':cfg['input_sha256']['collector_authorization'],
        'W03_snapshot_seal_sha256':sha(Path(snapshot)/'SHA256SUMS.txt'),'technical_QC_sha256':qc_sha,'URL_comparison_sha256':analysis_sha,
        'postwave_source_commit':cfg['postwave_source_commit'],'draft_generated_at_utc':iso(utc()),
        'model_ids':{sid:freeze['core_api'][sid]['model_id'] for sid in LINEAGES}}
    w03_manuscript.write_manuscript(analysis,qc,provenance,run/'paper')
    pdf=run/'paper/MIBO-W02-W03-manuscript.pdf'
    pdfinfo=subprocess.run(['pdfinfo',str(pdf)],check=True,capture_output=True,text=True).stdout
    page_line=next(line for line in pdfinfo.splitlines() if line.startswith('Pages:'))
    pages=int(page_line.split(':',1)[1])
    if not 4<=pages<=12: raise PipelineError('Unexpected manuscript page count')
    qa=run/'paper-layout';qa.mkdir()
    subprocess.run(['pdftoppm','-r','100','-png',str(pdf),str(qa/'page')],check=True,capture_output=True)
    rendered=list(qa.glob('page-*.png'))
    if len(rendered)!=pages or any(p.stat().st_size<10000 for p in rendered):
        raise PipelineError('Manuscript page rendering failed')
    write(run/'PAPER_LAYOUT_RENDER_REPORT.json',{'pdf_pages':pages,'pages_rendered':len(rendered),'template_visually_verified_before_W03':True,
        'future_actual_pages_generated_for_PI_final_review':True,'automatic_rendering_does_not_claim_human_review':True})
    valid=sum(c['valid_n'] for c in analysis['cells'] if c['wave_id']==WAVE)
    contrasts=sum(c['numerical_contrast_defined'] for c in analysis['contrasts'])
    summary=(f'<!doctype html><html lang="ja"><meta charset="utf-8"><title>MIBO W03 完成稿確認</title><style>body{{font:18px/1.8 sans-serif;max-width:820px;margin:50px auto;padding:0 25px}}a{{color:#126956}}</style><h1>MIBO W03 完成稿確認</h1>'
        f'<p>技術QCで確認した取得は{qc["totals"]["verified_capture"]}件／960件です。論文の主解析I03は{valid}件／80件、数値比較できるセルは{contrasts}／8です。追加の人手採点は0件です。</p>'
        '<p><a href="paper/MIBO-W02-W03-manuscript.pdf">論文初稿 PDF</a>　<a href="paper/MIBO-W02-W03-manuscript.html">編集用 HTML</a></p>'
        '<p><a href="W02-W03-URL-COMPARISON.csv">比較表 CSV</a>　<a href="TECHNICAL_QC.json">技術QC記録</a></p>'
        '<p>既存W02の判定不能9件は元の判定を保持しています。未定義の類似度や比較できないセルを0に置き換えていません。URLの一致は出典の正確性や事業施策の効果を意味しません。</p>'
        '<p>ご確認いただくのは完成稿です。倫理・機関手続、利益相反、資金および著者情報は投稿前の完成稿確認に含めています。外部への投稿・公開は行っていません。</p></html>')
    write(run/'REVIEW_START_HERE.html',summary.encode())
    with tarfile.open(run/'DERIVATIVE_INPUT_SNAPSHOT.tar.gz','x:gz') as tar:
        tar.add(snapshot,arcname='W03-derivative-snapshot',recursive=True)
    files=tree_hashes(run)
    manifest={'schema':'mibo-w03-postwave-run-manifest-1','completed_at_utc':iso(utc()),'wave_id':WAVE,'site_id':SITE,
        'status':'FIRST_DRAFT_READY_FOR_PI_REVIEW','full_wave_verified_captures':qc['totals']['verified_capture'],'planned_full_wave_slots':960,
        'I03_retained_responses':valid,'I03_planned_slots':80,'defined_primary_contrasts':contrasts,'paper_pages':pages,
        'additional_human_case_grading':0,'provider_calls_made':0,'raw_source_modified':False,'artifact_sha256':files,
        'input_sha256':cfg['input_sha256'],'postwave_source_commit':cfg['postwave_source_commit']}
    write(run/'RUN_MANIFEST.json',manifest)
    return manifest


def run_pipeline(cfg):
    runner,status,auditor,execution,engine=load_dependencies(cfg)
    paths={k:Path(v) for k,v in cfg['paths'].items()}
    protocol,_=runner.load_protocol(paths['protocol'])
    wave=runner.wave(protocol,WAVE)
    if wave['start_utc']!=START or wave['close_utc']!=CLOSE:
        raise PipelineError('Frozen field window changed')
    root=Path(cfg['output_root'])
    if root.is_symlink() or not root.is_dir(): raise PipelineError('Private output root is not prepared')
    with job_lock(root):
        if (root/'COMPLETED.json').exists():
            marker=read_json(root/'COMPLETED.json');verify_completed(root,marker)
            return {'status':'ALREADY_COMPLETE','run_directory':marker['run_directory']}
        current=utc()
        if current<instant(START): return {'status':'WAITING_FOR_REGISTERED_START','provider_calls':0}
        state=unit_state('mibo-core-v2-w03.service')
        active=state.get('ActiveState') not in {'inactive','failed'} or state.get('MainPID') not in ('0','',None)
        if active:
            if current>=instant(CLOSE): raise BusyError('Collector remains active after the registered close')
            return {'status':'WAITING_FOR_COLLECTOR_TO_STOP','provider_calls':0}
        require_single_namespace(cfg['data_root'])
        completion=status.build_report(protocol_path=paths['protocol'],manifest_path=paths['manifest'],freeze_path=paths['freeze'],
            authorization_path=paths['collector_authorization'],data_root=Path(cfg['data_root']),expected_wave=WAVE,expected_site=SITE)
        if completion.get('integrity_pass') is not True:
            raise PipelineError('Retained execution-state integrity failed before snapshot')
        decision=ready_reason(current,instant(START),instant(CLOSE),False,completion['scientific_collection_complete'])
        if decision.startswith('WAITING_'): return {'status':decision,'provider_calls':0}
        baseline=read_json(paths['baseline']);engine.validate_rows(baseline['rows'],'MIBO2-W02')
        rows=runner.read_csv(paths['manifest'])
        freeze,_=runner.load_freeze(paths['freeze'],protocol=protocol,wave_id=WAVE,site_id=SITE)
        raw_root=Path(cfg['data_root'])/'v2.0.1'/SITE/WAVE
        run=root/'runs'/(current.strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8])
        run.mkdir(parents=True,exist_ok=False)
        try:
            with execution.lineage_locks(Path(cfg['data_root']),SITE,WAVE,set(LINEAGES)):
                state=unit_state('mibo-core-v2-w03.service')
                if state.get('ActiveState') not in {'inactive','failed'} or state.get('MainPID') not in ('0','',None):
                    raise BusyError('Collector restarted before the snapshot lock')
                require_single_namespace(cfg['data_root'])
                snapshot=run/'snapshot'
                snapshot_receipt=copy_snapshot(raw_root,snapshot)
                specs=[{'version':'2.0.1','raw_root':str(snapshot),'manifest':str(paths['manifest']),'protocol':str(paths['protocol']),
                    'freeze':str(paths['freeze']),'lineages':LINEAGES}]
                qc=auditor.audit_wave(baseline_manifest=paths['manifest'],namespaces=specs,wave_id=WAVE)
                manifest=generate_outputs(cfg,run,snapshot,qc,rows,freeze,engine,baseline,snapshot_receipt)
                if tree_hashes(raw_root)!=snapshot_receipt['source_file_sha256']:
                    raise PipelineError('Original source changed while outputs were generated')
            artifact_sha={str((run/rel).relative_to(root)):digest for rel,digest in manifest['artifact_sha256'].items()}
            artifact_sha[str((run/'RUN_MANIFEST.json').relative_to(root))]=sha(run/'RUN_MANIFEST.json')
            marker={'schema':'mibo-w03-postwave-completion-1','completed_at_utc':iso(utc()),'run_directory':str(run),'artifact_sha256':artifact_sha,
                'status':'FIRST_DRAFT_READY_FOR_PI_REVIEW','additional_human_case_grading':0,'provider_calls':0}
            write(root/'COMPLETED.json',marker)
            return {'status':marker['status'],'run_directory':str(run),'paper':str(run/'paper/MIBO-W02-W03-manuscript.pdf'),
                'technical_QC_verified_captures':manifest['full_wave_verified_captures'],'primary_subset_retained':manifest['I03_retained_responses'],
                'completion_sha256':sha(root/'COMPLETED.json'),'additional_human_case_grading':0,'provider_calls':0}
        except BaseException as exc:
            if not (run/'FAILURE.json').exists():
                write(run/'FAILURE.json',{'status':'NO_FINAL_RESULT_PUBLISHED','error_type':type(exc).__name__,
                    'recorded_at_utc':iso(utc()),'original_response_bytes_modified':False,'provider_calls':0})
            raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--config-sha256',required=True)
    parser.add_argument('--validate-only',action='store_true')
    args=parser.parse_args()
    try:
        cfg=load_config(args.config,args.config_sha256)
        if args.validate_only:
            runner,status,auditor,execution,engine=load_dependencies(cfg)
            engine.validate_rows(read_json(cfg['paths']['baseline'])['rows'],'MIBO2-W02')
            result={'status':'POSTWAVE_CONFIGURATION_VALIDATED','additional_human_case_grading':0,'provider_calls':0}
        else: result=run_pipeline(cfg)
        print(json.dumps(result,sort_keys=True))
        return 0
    except BusyError:
        print(json.dumps({'status':'WAITING_FOR_QUIESCENT_ARCHIVE','provider_calls':0}))
        return 75
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError):
        print(json.dumps({'status':'POSTWAVE_FAILED_SAFE','message':'Inspect the private failure record; raw inputs are preserved and no final result is published','provider_calls':0}))
        return 1


if __name__=='__main__':
    raise SystemExit(main())
