"""Score and render one assessment; return success only with checked deliverables."""
import argparse,json,pathlib,subprocess,sys,hashlib
HERE=pathlib.Path(__file__).resolve().parent
def read(p):return json.loads(pathlib.Path(p).read_text(encoding='utf-8-sig'))
def main():
    p=argparse.ArgumentParser();p.add_argument('items');p.add_argument('judgements');p.add_argument('--metadata',required=True);p.add_argument('--suggestions');p.add_argument('--precheck');p.add_argument('--model',required=True);p.add_argument('--prompt-version',required=True);p.add_argument('--out-dir',required=True);a=p.parse_args()
    inputs=pathlib.Path(a.items).resolve();judges=pathlib.Path(a.judgements).resolve();out=pathlib.Path(a.out_dir).resolve();out.mkdir(parents=True,exist_ok=True)
    items=read(inputs);ids={i['item_id'] for i in items};js=read(judges);jids=[j['item_id'] for j in js]
    if len(ids)!=len(items) or len(set(jids))!=len(jids) or set(jids)-ids:raise ValueError('Duplicate or unmatched item/judgment IDs')
    pre=pathlib.Path(a.precheck).resolve() if a.precheck else out/'precheck.json'
    if not a.precheck:
        with pre.open('w',encoding='utf-8') as f:subprocess.run([sys.executable,str(HERE/'tqsi_tool.py'),'precheck',str(inputs)],stdout=f,check=True)
    raw=out/'scorer-report.json'
    with raw.open('w',encoding='utf-8') as f:subprocess.run([sys.executable,str(HERE/'tqsi_tool.py'),'score',str(inputs),str(judges),'--precheck',str(pre),'--model',a.model,'--prompt-version',a.prompt_version],stdout=f,check=True)
    args=[sys.executable,str(HERE/'render_output.py'),str(raw),str(inputs),'--metadata',str(pathlib.Path(a.metadata).resolve()),'--out',str(out/'evaluator-report.html'),'--json-out',str(out/'evaluator-results.json')]
    if a.suggestions:args+=['--suggestions',str(pathlib.Path(a.suggestions).resolve())]
    subprocess.run(args,check=True)
    d=read(out/'evaluator-results.json');page=(out/'evaluator-report.html').read_text(encoding='utf-8')
    for marker in ['Overall decision score','Critical:','Major:','Minor:','Calculated mean:','Findings and next actions','Evidence and suggested corrections','Upload a corrected document','Content-Security-Policy']:
        if marker not in page:raise ValueError('Required report section missing: '+marker)
    if {r['item_id'] for r in d['items']}!=ids:raise ValueError('Report omitted input entries')
    if d['batch_calculation']!=read(raw)['batch_calculation']:raise ValueError('Report and scorer calculations disagree')
    assets=[out/'evaluator-report.html',out/'evaluator-results.json']
    manifest={'plugin':'tqsi-calculation','plugin_version':'1.0.1','delivery_status':'ARTIFACTS VERIFIED','source_items_sha256':hashlib.sha256(inputs.read_bytes()).hexdigest(),'item_count':len(items),'overall':d['batch_calculation']['overall'],'required_artifacts':[{'path':str(f),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in assets],'host_installation_verified':False,'note':'Local output checks succeeded. Host installation, skill invocation and rendered preview must also be confirmed in the target Claude environment.'}
    (out/'delivery-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(manifest,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
