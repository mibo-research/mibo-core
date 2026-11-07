"""Deterministic aggregate-only manuscript rendering, with no model/API call.

ReportLab is the sole extra dependency and is confined to document output.
Raw answers, individual citations and credential values never enter the draft.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

TITLE = 'Within and between wave variation in source URL strings in Japanese and English API responses'
PROVIDERS = {'MIBO-SL-001':'OpenAI','MIBO-SL-002':'Anthropic','MIBO-SL-003':'Google','MIBO-SL-004':'Perplexity'}
REFERENCES = [
 ('Sielinski R. 2026. Quantifying Uncertainty in AI Visibility: A Statistical Framework for Generative Search Measurement. arXiv:2603.08924v3. Preprint.', 'https://arxiv.org/abs/2603.08924v3'),
 ('Pykälä L, Kaski KK. 2026. Self-Consistency of Entity Sets and Citations in a Deep Research System under Repeated Prompting. arXiv:2610.26421v1. Preprint.', 'https://arxiv.org/abs/2610.26421v1'),
 ('Gao T, Yen H, Yu J, Chen D. 2023. Enabling Large Language Models to Generate Text with Citations. Proceedings of EMNLP, 6465–6488.', 'https://aclanthology.org/2023.emnlp-main.398/'),
 ('Liu NF, Zhang T, Liang P. 2023. Evaluating Verifiability in Generative Search Engines. arXiv:2304.09848v2.', 'https://arxiv.org/abs/2304.09848v2'),
 ('MIBO Core Protocol Package v2.0 and the prospectively registered v2.0.1 Agent amendment.', 'https://doi.org/10.5281/zenodo.22264635'),
 ('MIBO W03 derivative URL analysis registration v1.0. Registered 7 November 2026.', 'https://github.com/mibo-research/mibo-core/blob/30e48170f7387002e506baabd36884f12cc7a250/docs/analysis/W03-URL-variation-v1.0/REGISTRATION.md'),
]


def fmt(value, digits=3):
    return 'undefined' if value is None else f'{value:.{digits}f}'


def manuscript_data(analysis, qc, provenance, *, preview=False):
    cells = {(r['wave_id'], r['service_lineage_id'],r['language']):r for r in analysis['cells']}
    contrasts = analysis['contrasts']
    numerical = [c for c in contrasts if c['numerical_contrast_defined']]
    w03_n = sum(c['valid_n'] for c in analysis['cells'] if c['wave_id']=='MIBO2-W03')
    deltas = [c['W03_minus_W02'] for c in numerical]
    coverage = qc['totals']
    subset = f'{w03_n}/80 planned I03 responses were technically retained in W03.'
    result_sentence = (f'Numerical W03 minus W02 contrasts were defined in {len(numerical)}/8 cells. '
        + (f'The observed cell differences ranged from {fmt(min(deltas))} to {fmt(max(deltas))}.' if deltas else 'No numerical cross-wave contrast was available under the registered rules.'))
    abstract = ('Repeated answers can cite different URL strings even when prompts and requested API settings are held fixed. '
        'We describe within-wave and between-wave variation for one fixed sleep-deprivation question in English and Japanese, '
        'using four generative-AI service lineages at one Japanese site. W02 was an already-inspected exploratory baseline; '
        'the W03 derivative analysis was fixed before W03 collection. Each lineage-language cell planned ten responses per wave. '
        'The primary measure was mean pairwise Jaccard similarity of the first five extracted exact URL strings. '
        f'{subset} {result_sentence} '
        'Whole-response leave-one-out ranges describe sensitivity rather than confidence intervals. '
        'The study characterizes literal citation-output variability under these sampled conditions; it does not establish citation correctness, '
        'a service ranking, an intervention effect, or a causal effect of model updates.')
    design_table = [['Lineage','Requested model','Planned I03 per wave']]
    for sid in sorted(PROVIDERS):
        design_table.append([PROVIDERS[sid],provenance['model_ids'][sid],'20 (10 EN + 10 JA)'])
    qc_table = [['Lineage','Planned all items','Verified capture','Other technical states']]
    for r in qc['providers']:
        qc_table.append([PROVIDERS[r['service_lineage_id']],str(r['planned']),str(r['verified_capture']),str(r['planned']-r['verified_capture'])])
    primary = [['Lineage and language','W02 n / W03 n','W02 J','W03 J','Difference','Sensitivity range']]
    secondary = [['Lineage and language','Distinct sets W02 / W03','URL-free W02 / W03','Host J W02 / W03','Both-empty pairs W02 / W03']]
    overlap = [['Lineage and language','Shared distinct sets','Distinct-set Jaccard']]
    returned_table = [['Lineage and language','W02 returned identifiers','W03 returned identifiers']]
    returned_metadata=analysis.get('returned_identifier_metadata',{})
    for sid in sorted(PROVIDERS):
        for language in ['EN','JA']:
            values=[]
            for wave in ['W02','W03']:
                entries=[r for r in returned_metadata.get(wave,[]) if r['service_lineage_id']==sid and r['language']==language]
                values.append('; '.join(r['returned_identifier']+' (n='+str(r['n'])+')' for r in entries) or 'not available')
            returned_table.append([PROVIDERS[sid]+' '+language,*values])
    for c in contrasts:
        sid,lang = c['service_lineage_id'],c['language']
        old,new = cells['MIBO2-W02',sid,lang],cells['MIBO2-W03',sid,lang]
        loo = c['leave_one_response_out']
        interval = (fmt(loo['min'])+' to '+fmt(loo['max'])) if loo else 'not reported'
        label = PROVIDERS[sid]+' '+lang
        primary.append([label,f"{old['valid_n']} / {new['valid_n']}",fmt(old['exact_url_jaccard']['mean']),fmt(new['exact_url_jaccard']['mean']),fmt(c['W03_minus_W02']),interval])
        secondary.append([label,f"{old['distinct_first_five_url_sets']} / {new['distinct_first_five_url_sets']}",f"{old['url_free_n']} / {new['url_free_n']}",fmt(old['hostname_jaccard']['mean'])+' / '+fmt(new['hostname_jaccard']['mean']),f"{old['exact_url_jaccard']['both_empty_pair_count']} / {new['exact_url_jaccard']['both_empty_pair_count']}"])
    for r in analysis.get('exploratory_cross_wave_set_overlap',[]):
        overlap.append([PROVIDERS[r['service_lineage_id']]+' '+r['language'],str(r['shared_distinct_sets']),fmt(r['distinct_set_jaccard'])])
    eligibility = []
    for c in contrasts:
        reasons=[]
        if not c['same_design']: reasons.append('design identity differs')
        if not c['material_request_profile_equal']: reasons.append('material profile differs')
        if not c['minimum_n_rule_satisfied']: reasons.append('fewer than eight retained responses in a wave')
        if c['contrast_eligible'] and not c['numerical_contrast_defined']: reasons.append('a within-wave mean is undefined')
        if not c['requested_model_id_equal']: reasons.append('requested model identifier changed; deployment change disclosed')
        if reasons: eligibility.append(PROVIDERS[c['service_lineage_id']]+' '+c['language']+': '+ '; '.join(reasons)+'.')
    sections=[
      {'title':'Abstract','paragraphs':[abstract]},
      {'title':'Introduction','paragraphs':[
       'Citation-output consistency is distinct from citation accuracy. Work on verifiability and automatic citation evaluation examines whether sources support generated claims (Liu et al., 2023; Gao et al., 2023). A literal URL-overlap measure instead asks whether repeated answers surface the same strings. A stable set can still be wrong, and different strings can refer to equivalent evidence.',
       'Repeated-sampling studies have reported substantial variation in citation and visibility measures (Sielinski, 2026; Pykälä and Kaski, 2026). Their tasks and retrieval-enabled systems differ from this study. We use a small, fixed API-only panel with retrieval and tools disabled. The contribution is a transparent within-task repeated-observation description across two waves and two language forms, not a universal assessment of the services.',
       'The research question is how similar the first five source URL strings are across repeated responses within each sampled deployment-language cell, and how that similarity differs between W02 and W03. W02 summaries informed the choice of this question. That prior exposure is explicitly retained rather than represented as prospective W02 confirmation.']},
      {'title':'Methods','new_page':True,'paragraphs':[
       'The full JP01 ACI design comprises four lineages, 24 frozen query forms and ten replications, or 960 initial logical slots per wave. This paper uses only MIBO-I03: the main health effects of chronic sleep deprivation in adults, with an English form and a Japanese form. Each wave therefore plans 80 primary-subset responses in eight cells. The fixed query hashes, ordering seed, technical-only retry rules and observation windows remain those of the Core protocol and amendment.',
       'W03 was scheduled from 1 December 2026 00:00 UTC to 3 December 2026 00:00 UTC. W02 is an already-inspected baseline from the corresponding preceding registered wave. The derivative analysis was publicly fixed on 7 November 2026 before W03 outputs were available. Ordinary waves have no calibration Window A/B. Requested model strings and material profiles were carried forward from W02; a frozen identifier does not guarantee immutable hosted weights, alias resolution or provider defaults.',
       'The postwave process runs offline in the private research environment. After collection has stopped, it takes a hash-verified derivative snapshot while holding the existing lineage locks. It preserves original capture bytes and records the complete copied file set. This is an automatically sealed derivative snapshot, not a claim that a human reviewed and signed the future raw data. Technical QC verifies planned identities, response hashes, timing and retry evidence against frozen execution inputs.',
       'Retained observations are technical captures, not content-validity judgements. Refusals, safety responses and nonanswers remain observations. Technical missingness is tabulated separately; no response is replaced or imputed. A retry remains part of its original logical slot. The primary analysis neither adds human grading nor requires AI content grading. Existing W02 automated content codes remain exploratory and human_validation=false.',
       'Displayed answer text and literal citation fields use the unchanged W02 response-selection logic. Citation URLs are considered first, then regex URLs in displayed text. Trailing periods, commas and semicolons are stripped, first occurrences are deduplicated, and at most five are retained. Their exact strings form an order-insensitive set. No linked source is fetched, no redirect is resolved, and no query string is normalized. Bibliographic citations without URLs and semantic source identity are outside the metric.',
       'Within each cell, J is the mean pairwise set Jaccard similarity, |A intersect B| / |A union B|. A pair with one empty set has similarity zero. A pair with two empty sets is undefined, omitted from the mean and counted separately. A cell with no defined pairs has an undefined mean. The 45 possible pairs in a complete ten-response cell are dependent comparisons, not 45 independent observations.',
       'The primary difference is W03 J minus W02 J in each comparable lineage-language cell. At least eight technically retained responses are required in each wave. Site, item-form hash, language, lineage, ACI condition and ordinary window class must match. Different material-profile hashes are not automatically pooled. Requested-model changes are disclosed as deployment changes, without a causal model-update interpretation.',
       'Sensitivity analysis holds original eligibility fixed, omits one whole response from each wave and recalculates all cross-wave omission combinations. At ten retained responses in each wave there are 100 combinations. We report the minimum and maximum defined differences and the number of undefined combinations. These are descriptive sensitivity ranges, not confidence intervals. Replication numbers are not paired subjects. No significance tests or service rankings are produced.'], 'table':design_table,
       'table_caption':'Table 1. Requested deployments and planned primary-subset observations.'},
      {'title':'Technical QC and primary results','new_page':True,'paragraphs':[
       f"The full W03 matrix contained {coverage['planned']} planned logical slots. Technical QC verified {coverage['verified_capture']} captures; the other {coverage['planned']-coverage['verified_capture']} slots remained in separately reported technical states. {subset}",
       result_sentence,
       'Table 3 reports every prespecified cell, including unavailable contrasts. Literal URL-string differences do not alone identify changes in evidence quality or in the underlying model.'], 'table':qc_table,'table_caption':'Table 2. Full-wave technical accounting, without content grading.',
       'second_table':primary,'second_caption':'Table 3. Primary URL-set similarity and W03 minus W02 differences.',
       'notes':['J is mean pairwise exact-URL-set Jaccard. Undefined is not replaced by zero or one. Sensitivity ranges are not confidence intervals.']+eligibility},
      {'title':'Secondary descriptions','new_page':True,'paragraphs':[
       'Distinct first-five sets are reported with their actual retained-response denominator. Counts are directly comparable only where both waves have equal n. URL-free counts use retained observations; technical missingness is not a URL-free response. Exact lowercase hostname similarity uses the same five URLs, without merging subdomains into registrable domains. Unparseable or missing hostname occurrences are counted separately while literal URLs remain in the primary analysis.',
       'The exploratory cross-wave overlap uses the collections of distinct nonempty exact first-five URL sets in each cell: the number shared across waves and their set Jaccard. Empty response sets remain in the URL-free counts and are excluded from this secondary overlap; two empty collections give an undefined value. It is a description of observed distinct sets, not an independent-pair sample or an inferential test.'],
       'table':secondary,'table_caption':'Table 4. Secondary descriptions. URL-free entries are counts; denominators are in Table 3.',
       'second_table':overlap,'second_caption':'Table 5. Exploratory overlap of distinct exact first-five sets.',
       'notes':[f"Undefined leave-one-out combinations: {sum((c['leave_one_response_out'] or {}).get('undefined_combinations',0) for c in contrasts)} across cells with a defined primary contrast.",f"Hostname parse-failure occurrences across both waves: {sum(c['hostname_parse_failure_occurrences'] for c in analysis['cells'])}."]},
      {'title':'Discussion','new_page':True,'paragraphs':[
       'The cell-specific results describe the stability of literal URL strings under repeated fixed prompting. A positive W03 minus W02 difference means higher observed within-wave string overlap in that sampled cell; a negative difference means lower overlap. Neither direction is intrinsically a measure of answer quality. A null or unavailable contrast is not evidence of equivalence.',
       'The observations can motivate repeated measurement when organizations use generated citations as an operational signal. A single response need not characterize the distribution of repeated outputs. However, these data do not estimate citation market share, organic search visibility, the probability of a brand being recommended, or the effectiveness of an LLMO/AIO intervention. Such claims require a design that measures those outcomes and, for intervention effects, an appropriate causal comparison.',
       'The design has a deliberately narrow scope: one site, one I03 topic, two language forms, four requested deployments and two observation windows. Language differences are not isolated from wording, tokenization and deployment behavior. Cell differences do not generalize to all questions, users, models or dates. Repeated outputs can also share platform state and are not assumed to be independent draws from a universal population.',
       'A requested model identifier and unchanged payload profile do not guarantee unchanged hosted weights or provider defaults. We therefore retain exact configuration hashes and returned-model metadata and interpret differences as deployment- and time-specific observations. The design cannot isolate a causal model-update effect.',
       'The URL rule deliberately prioritizes reproducibility over semantic source matching. Redirects, tracking parameters, alternate editions, URL case and URL-free bibliography can reduce literal agreement without a substantive difference in evidence. Two empty URL sets provide no measurable source-string overlap and remain undefined pairs. Technical missingness can reduce the set of reportable contrasts; all such losses and unavailable cells are retained in the accounting.',
       'Nine pre-existing W02 I03 citation judgements were indeterminate in a separate automated coding exercise. They remain indeterminate. They are not relabelled as correct, and they do not by themselves remove technically retained responses from this URL-string analysis. Agreement among AI graders is not presented as human-validated accuracy.'],
       'conclusion':'The completed tables support a reproducible description of observed URL-string consistency within these cells. They provide a basis for further repeated observation, with the scope and technical missingness reported explicitly. They do not establish citation correctness, service superiority or a causal business effect.'},
      {'title':'Reproducibility and declarations','new_page':True,'paragraphs':[
       'The private execution record binds the original manifest, protocol, model/profile freeze, PI authorization, the derivative snapshot and the generated analysis to SHA-256 hashes. The registered URL-analysis implementation is reused at its frozen hash. Every derived result and manuscript file is listed in a run manifest. Original responses and credentials are not published by this automation.',
       'Research materials are provider-generated outputs from fixed prompts; no human participants were recruited or subjected to intervention. The PI authorized execution and this automated postwave processing. This draft does not claim institutional-body ethics approval or exemption. The applicable institutional determination and declarations require the author’s final manuscript review before submission.',
       'Competing interests: the author operates SASANO LAB. and has commercial interests in MIBO business reports. This relationship should be disclosed when the manuscript is submitted. No external funding source is asserted in this automated draft; the author should confirm the funding statement.',
       'AI and automation disclosure: Codex assisted software implementation and draft preparation. Primary and secondary numerical results are computed deterministically from retained technical captures. No additional human case grading or model/API-based semantic grading is performed by this postwave pipeline. The manuscript remains an internal first draft pending PI review; no journal submission or public publication is automated.'],
       'table':returned_table,'table_caption':'Table 6. Literal returned-model identifier metadata in the I03 captures. None denotes absent metadata, not a model name.',
       'provenance':provenance,'references':REFERENCES},
    ]
    return {'schema':'mibo-w02-w03-manuscript-1','title':TITLE,'subtitle':'MIBO2 W02 and W03 at JP01','author':'Kento Sasano','affiliation':'SASANO LAB.','status':'SIMULATION FOR LAYOUT TESTING — NOT OBSERVED W03 RESULTS' if preview else 'Internal first draft awaiting PI review','abstract':abstract,'sections':sections,'additional_human_case_grading':0,'preview':preview}


def render_html(data, path):
    parts=['<!doctype html><html lang="en"><meta charset="utf-8"><title>'+html.escape(data['title'])+'</title><style>body{font:17px/1.6 Georgia,serif;max-width:940px;margin:48px auto;padding:0 30px;color:#111}h1{font-size:30px;line-height:1.25}h2{font-size:23px;margin-top:34px}table{border-collapse:collapse;width:100%;margin:18px 0;font:14px/1.4 Arial,sans-serif}td,th{border:1px solid #bbb;padding:8px;text-align:left}th{background:#eee}small{color:#444}.status{font-weight:bold}@media print{body{font-size:11pt;margin:0}table{font-size:9pt}h2{break-after:avoid}}</style>']
    esc=html.escape
    parts += [f'<h1>{esc(data["title"])}</h1>',f'<p>{esc(data["author"])}<br>{esc(data["affiliation"])}</p>',f'<p class="status">{esc(data["status"])}</p>']
    for sec in data['sections']:
        parts.append('<section'+(' class="page"' if sec.get('new_page') else '')+'><h2>'+esc(sec['title'])+'</h2>')
        parts += ['<p>'+esc(p)+'</p>' for p in sec['paragraphs']]
        for table_key,caption_key in [('table','table_caption'),('second_table','second_caption')]:
            if table_key not in sec: continue
            parts.append('<p><b>'+esc(sec[caption_key])+'</b></p><table>')
            for index,row in enumerate(sec[table_key]):
                tag='th' if index==0 else 'td'
                parts.append('<tr>'+''.join('<'+tag+'>'+esc(str(x))+'</'+tag+'>' for x in row)+'</tr>')
            parts.append('</table>')
        parts += ['<p><small>'+esc(n)+'</small></p>' for n in sec.get('notes',[])]
        if sec.get('conclusion'): parts.append('<h2>Conclusion</h2><p>'+esc(sec['conclusion'])+'</p>')
        if sec.get('provenance'):
            parts.append('<h2>Provenance</h2>')
            parts += ['<p><small>'+esc(str(k))+': '+esc(str(v))+'</small></p>' for k,v in sec['provenance'].items() if k!='model_ids']
        if sec.get('references'):
            parts.append('<h2>References</h2><ol>')
            parts += ['<li>'+esc(text)+' <a href="'+esc(url,quote=True)+'">'+esc(url)+'</a></li>' for text,url in sec['references']]
            parts.append('</ol>')
        parts.append('</section>')
    parts.append('</html>')
    with Path(path).open('x',encoding='utf-8') as f: f.write('\n'.join(parts)+'\n')


def render_pdf(data, path):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
    styles={
      'title':ParagraphStyle('title',fontName='Times-Bold',fontSize=19,leading=23,spaceAfter=12),
      'heading':ParagraphStyle('heading',fontName='Times-Bold',fontSize=12,leading=16,spaceBefore=10,spaceAfter=8,keepWithNext=True),
      'body':ParagraphStyle('body',fontName='Times-Roman',fontSize=10.5,leading=14,spaceAfter=8),
      'small':ParagraphStyle('small',fontName='Times-Roman',fontSize=8.5,leading=11,spaceAfter=5),
      'cell':ParagraphStyle('cell',fontName='Times-Roman',fontSize=8.3,leading=10.7),
      'cellhead':ParagraphStyle('cellhead',fontName='Times-Bold',fontSize=8.3,leading=10.7),
      'hash':ParagraphStyle('hash',fontName='Courier',fontSize=7.1,leading=10,spaceAfter=5,wordWrap='CJK'),
    }
    def P(s,kind='body'): return Paragraph(html.escape(str(s)),styles[kind])
    story=[P(data['title'],'title'),P(data['author']+' | '+data['affiliation']),P(data['status'],'small')]
    width=174*mm
    for sec in data['sections']:
        if sec.get('new_page'): story.append(Spacer(1,3*mm))
        story.append(P(sec['title'],'heading'))
        story += [P(p) for p in sec['paragraphs']]
        for key,cap in [('table','table_caption'),('second_table','second_caption')]:
            if key not in sec: continue
            count=len(sec[key][0])
            ratios={3:[.25,.5,.25],4:[.28,.24,.24,.24],5:[.25,.23,.18,.2,.14],6:[.22,.14,.11,.11,.12,.30]}[count]
            if sec['title']=='Reproducibility and declarations' and count==3:
                ratios=[.22,.39,.39]
            rows=[[P(v,'cellhead' if i==0 else 'cell') for v in row] for i,row in enumerate(sec[key])]
            table=Table(rows,colWidths=[width*x for x in ratios],repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e9e9e9')),('GRID',(0,0),(-1,-1),.35,colors.HexColor('#bcbcbc')),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
            block=[Spacer(1,4*mm),P(sec[cap],'small'),table,Spacer(1,3*mm)]
            if key=='second_table' or 'second_table' not in sec:
                block += [P(n,'small') for n in sec.get('notes',[])]
            story.append(KeepTogether(block))
        if 'table' not in sec: story += [P(n,'small') for n in sec.get('notes',[])]
        if sec.get('conclusion'): story += [P('Conclusion','heading'),P(sec['conclusion'])]
        if sec.get('provenance'):
            story.append(P('Provenance','heading'))
            for k,v in sec['provenance'].items():
                if k=='model_ids': continue
                story.append(P(str(k)+': '+str(v),'hash' if 'sha256' in k or 'commit' in k else 'small'))
        if sec.get('references'):
            story.append(P('References','heading'))
            for index,(text,url) in enumerate(sec['references'],1): story.append(P(f'[{index}] {text} {url}','small'))
    def footer(c,doc):
        c.saveState(); c.setFont('Times-Roman',8)
        c.drawString(18*mm,10*mm,'MIBO W02 W03 | '+('LAYOUT SIMULATION' if data['preview'] else 'First draft for PI review'))
        c.drawRightString(192*mm,10*mm,str(doc.page)); c.restoreState()
    if Path(path).exists(): raise FileExistsError('Manuscript output is append-only')
    SimpleDocTemplate(str(path),pagesize=A4,leftMargin=18*mm,rightMargin=18*mm,topMargin=18*mm,bottomMargin=18*mm,title=data['title'],author=data['author']).build(story,onFirstPage=footer,onLaterPages=footer)


def write_manuscript(analysis,qc,provenance,out_dir,*,preview=False):
    out=Path(out_dir)
    out.mkdir(parents=True,exist_ok=False)
    data=manuscript_data(analysis,qc,provenance,preview=preview)
    with (out/'MANUSCRIPT_DATA.json').open('x',encoding='utf-8') as f:
        json.dump(data,f,ensure_ascii=False,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
    render_html(data,out/'MIBO-W02-W03-manuscript.html')
    render_pdf(data,out/'MIBO-W02-W03-manuscript.pdf')
    return data
