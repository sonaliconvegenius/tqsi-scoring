"""Render current Claude T-QSI reports without recalculating their scores."""
import argparse,collections,hashlib,html,json,pathlib

def read(p):return json.loads(pathlib.Path(p).read_text(encoding='utf-8-sig'))
def fingerprint(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest()

def prepare(report,items,metadata,suggestions=None,previous=None,previous_items=None):
    inputs={i['item_id']:i for i in items}
    if len(inputs)!=len(items):raise ValueError('Duplicate input IDs; use unique IDs for each target language')
    results={r['item_id']:r for r in report['items']}
    if len(results)!=len(report['items']):raise ValueError('Duplicate report IDs')
    if results.keys()-inputs.keys():raise ValueError('Report contains unmatched items')
    output=[];suggestions=suggestions or {}
    for iid,item in inputs.items():
        row=results.get(iid,{'item_id':iid,'error_score':'n/a','rating':'n/a','flags':['UND'],'findings':[]})
        matches=suggestions.get(iid,[])
        fs=[]
        for f in row['findings']:
            matched=next((s for s in matches if s['test']==f['test'] and s.get('field','question')==f['field']),{})
            fs.append({**f,'suggested_correction':f.get('rewrite') or matched.get('suggested_correction')})
        action='Correct the affected translation and upload Document Version 2.' if fs else 'No findings detected within the completed checks.'
        if row['error_score']=='n/a':action='Resolve the reported uncertainty or missing assessment, then reassess.'
        if 'SEN' in row['flags']:action+=' Content Governance must review the sensitivity flag.'
        if 'IMG' in row['flags']:action+=' Review image content separately.'
        output.append({**row,'lang':item.get('lang'),'source':item['source'],'target':item['target'],'findings':fs,'next_action':action,'assessment_missing':iid not in results})
    comparison=None
    if previous:
        old={r['item_id']:r for r in previous['items']};old_inputs={i['item_id']:i for i in previous_items or []}
        comparison={'added':sorted(inputs.keys()-old.keys()),'removed':sorted(old.keys()-inputs.keys()),'items':[]}
        changed_settings=previous.get('run_record',{}).get('ai_model')!=report.get('run_record',{}).get('ai_model') or previous.get('run_record',{}).get('ai_instructions_version')!=report.get('run_record',{}).get('ai_instructions_version') or previous.get('run_record',{}).get('r1_version')!=report.get('run_record',{}).get('r1_version')
        for row in output:
            iid=row['item_id']
            if iid not in old:continue
            identity=lambda f:f.get('finding_id') or fingerprint({k:f.get(k) for k in ('test','field','source_excerpt','target_excerpt','defect')})
            a={identity(f):f for f in old[iid]['findings']};b={identity(f):f for f in row['findings']}
            limited=changed_settings or row['error_score']=='n/a' or row['rating']=='n/a' or iid not in old_inputs or old_inputs[iid]['source']!=inputs[iid]['source'] or old_inputs[iid].get('grade')!=inputs[iid].get('grade') or bool(previous.get('discarded_findings')) or bool(report.get('discarded_findings'))
            gone=len(a.keys()-b.keys())
            comparison['items'].append({'item_id':iid,'lang':row['lang'],'previous':[old[iid]['error_score'],old[iid]['rating']],'latest':[row['error_score'],row['rating']],'resolved':0 if limited else gone,'uncertain':gone if limited else 0,'remaining':len(a.keys()&b.keys()),'new_candidates':len(b.keys()-a.keys()),'limited':limited})
        comparison['assessment_settings_changed']=changed_settings
    groups={}
    for lang in sorted({r['lang'] for r in output}):
        rows=[r for r in output if r['lang']==lang];nums=[r['error_score'] for r in rows if isinstance(r['error_score'],(int,float))]
        groups[lang]={'total':len(rows),'scored':len(nums),'unresolved':len(rows)-len(nums),'mean':round(sum(nums)/len(nums),2) if nums else None,'ratings':dict(collections.Counter(r['rating'] for r in rows)),'bands':dict(collections.Counter(r.get('band') for r in rows if isinstance(r['error_score'],(int,float)))),'flags':dict(collections.Counter(f for r in rows for f in r['flags']))}
    return {'output_version':'2.0','metadata':metadata,'validation_status':'Section 8 validation pending; deferred to team. Not an automatic scoring gate.','not_evaluated':['E6','N4','P1','R2','R3','REF','R3 additions'],'r1_status':'Used as supplied in scorer run record','items':output,'by_language':groups,'comparison':comparison,'discarded_findings':report.get('discarded_findings',[]),'run_record':report.get('run_record',{}),'release_decision':'Programme owner responsibility'}

def render(data):
    e=lambda v:html.escape(str(v));m=data['metadata']
    overview=''.join('<tr><td>'+e(lang)+'</td><td>'+e(s['scored'])+'</td><td>'+e(s['unresolved'])+'</td><td>'+e(s['mean'] if s['mean'] is not None else 'n/a')+'</td><td>'+e(', '.join(f'{k}: {v}' for k,v in s['ratings'].items()))+'</td></tr>' for lang,s in data['by_language'].items())
    rows='';cards=''
    for r in data['items']:
        issue='; '.join(f['test']+': '+f['defect'] for f in r['findings']) or 'No finding within completed checks' if not r['assessment_missing'] else 'Assessment missing'
        rows+='<tr><td><a href="#item-'+e(r['item_id'])+'">'+e(r['item_id'])+'</a></td><td>'+e(r['lang'])+'</td><td>'+e(r['error_score'])+'</td><td>'+e(r['rating'])+'</td><td>'+e(issue)+'</td><td>'+e(r['next_action'])+'</td></tr>'
        evidence=''
        for f in r['findings']:
            evidence+='<article><p><strong>'+e(f['test'])+' · '+e(f['field'])+'</strong></p><p>'+e(f['defect'])+'</p><div class="pair"><div><small>English evidence</small><p>'+e(f['source_excerpt'])+'</p></div><div><small>Translated evidence</small><p>'+e(f['target_excerpt'])+'</p></div></div><p><strong>Suggested correction:</strong> '+e(f.get('suggested_correction') or 'A replacement has not been supplied; revise this field against the source.')+'</p></article>'
        cards+='<details id="item-'+e(r['item_id'])+'"><summary>'+e(r['item_id'])+' · '+e(r['error_score'])+' · '+e(r['rating'])+'</summary><p><strong>Source:</strong> '+e(r['source'].get('question',''))+'</p><p><strong>Current translation:</strong> '+e(r['target'].get('question',''))+'</p>'+evidence+'<p><strong>Next:</strong> '+e(r['next_action'])+'</p></details>'
    rev=''
    if data['comparison']:
        c=data['comparison'];trs=''.join('<tr>'+''.join('<td>'+e(x[k])+'</td>' for k in ('item_id','lang','previous','latest','resolved','remaining','new_candidates','uncertain'))+'</tr>' for x in c['items'])
        rev='<section><h2>Revision comparison</h2><p>Added: '+e(c['added'])+' · Removed: '+e(c['removed'])+' · Settings changed: '+e(c['assessment_settings_changed'])+'</p><div class="scroll"><table><tr><th>Item</th><th>Language</th><th>Previous</th><th>Latest</th><th>Resolved</th><th>Remaining</th><th>New candidates</th><th>Uncertain</th></tr>'+trs+'</table></div><p>Unmatched finding text requires review. Uncertainty, changed source/settings, or discarded evidence cannot establish resolution.</p></section>'
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"><title>T-QSI V2 evaluator output</title><style>body{font:16px/1.6 system-ui,sans-serif;background:#f2f6f7;color:#203346;margin:0}main{max-width:1180px;margin:auto;padding:24px}section,header{background:white;padding:24px;border:1px solid #d9e3e8;border-radius:12px;margin:16px 0}.notice{padding:14px;background:#fff1cf;border-radius:8px}h1{line-height:1.2}h2{font-size:21px}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:12px 9px;text-align:left;border-bottom:1px solid #d9e3e8;vertical-align:top}.scroll{overflow:auto}details{padding:16px 0;border-bottom:1px solid #d9e3e8}summary{cursor:pointer;font-weight:600}.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}.pair>div{background:#f1f5f6;padding:12px;border-radius:8px}button,input,select{font:inherit;max-width:100%;padding:10px;margin:8px 0}button{background:#225c61;color:white;border:0;border-radius:6px;cursor:pointer}label{display:block}p,li,summary{overflow-wrap:anywhere}small{color:#536b7a}@media(max-width:600px){main{padding:12px}header,section{padding:16px}.pair{grid-template-columns:1fr}}</style><main>'''
    page+='<header><small>T-QSI · Output V2.0 · Claude plugin v0.2.0</small><h1>'+e(m.get('assessment_name','Translation evaluation'))+'</h1><p>'+e(' · '.join(f'{k}: {m.get(k,"Not recorded")}' for k in ('program_name','pod_name','subject','grade','document_version')))+'</p><div class="notice">'+e(data['validation_status'])+' Results are provisional; release is decided by the programme owner.</div></header>'
    page+='<section><h2>1. Assessment overview</h2><div class="scroll"><table><tr><th>Target</th><th>Scored</th><th>Unresolved</th><th>Mean error score</th><th>Quality</th></tr>'+overview+'</table></div><p><strong>Error score:</strong> translation fidelity. <strong>Quality rating:</strong> wording quality. Good wording does not mean error-free translation.</p><p>'+e(m.get('coverage','Scope follows the supplied scorer input; missing source, options, keys and image coverage must be disclosed.'))+'</p></section>'
    page+='<section><h2>2. Findings and next actions</h2><div class="scroll"><table><tr><th>Item</th><th>Language</th><th>Error score</th><th>Quality</th><th>What was found</th><th>What to do next</th></tr>'+rows+'</table></div></section><section><h2>3. Evidence and suggested corrections</h2>'+cards+'</section>'+rev
    page+='<section><h2>4. Upload a corrected document</h2><label>Revision<select id="round"><option>Document Version 2</option><option>Document Version 3</option><option>Final submitted version</option></select></label><label>Upload file<input id="file" type="file" accept=".docx,.pdf,.xlsx,.json" multiple></label><button id="handoff-button">Prepare reassessment request</button><p id="handoff" role="status">Attach the corrected file in the plugin chat to start reassessment. Selecting a file here does not upload or evaluate it.</p><p>Keep the same item IDs. Each target language receives separate results. A final submitted version can still contain unresolved findings; it is not release approval.</p></section>'
    page+='<section><h2>5. Current tool coverage</h2><p><strong>Retained:</strong> E1–E5, E7–E9, N1–N3, C1–C3; R1/Annex C; IMG, SEN and UND.</p><p><strong>Not evaluated in V2:</strong> E6, N4, P1, R2, R3, REF and proposed R3 additions. Their absence does not reduce scores or add NC. Pending §8 validation does not change scores.</p><p>IMG: inspect images separately. SEN: Content Governance review. UND: resolve uncertainty and reassess. Unassessed input items are shown separately.</p><details><summary>Scorer record, score bands and discarded evidence</summary><pre style="white-space:pre-wrap;overflow-wrap:anywhere">'+e(json.dumps({'by_language':data['by_language'],'run_record':data['run_record'],'discarded_findings':data['discarded_findings']},ensure_ascii=False,indent=2))+'</pre></details></section>'
    page+='''<script>document.getElementById('handoff-button').onclick=()=>{const files=Array.from(document.getElementById('file').files).map(f=>f.name);document.getElementById('handoff').textContent=files.length?'Attach '+files.join(', ')+' in the plugin chat and request: Reassess '+document.getElementById('round').value+' and compare with the previous T-QSI report. No file was uploaded here.':'Choose the corrected document, then attach it in the plugin chat.';};</script></main></html>'''
    return page

def main():
    p=argparse.ArgumentParser();p.add_argument('report');p.add_argument('items');p.add_argument('--metadata',required=True);p.add_argument('--suggestions');p.add_argument('--previous-report');p.add_argument('--previous-items');p.add_argument('--out',required=True);p.add_argument('--json-out');a=p.parse_args()
    data=prepare(read(a.report),read(a.items),read(a.metadata),read(a.suggestions) if a.suggestions else None,read(a.previous_report) if a.previous_report else None,read(a.previous_items) if a.previous_items else None)
    out=pathlib.Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(render(data),encoding='utf-8')
    if a.json_out:pathlib.Path(a.json_out).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(str(out.resolve()))
if __name__=='__main__':main()
