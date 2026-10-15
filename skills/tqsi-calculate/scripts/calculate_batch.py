"""User-approved T-QSI batch decision rule, version 1.0.0; stdlib only."""
import argparse,collections,json,math
SEVERITY={**{f'E{i}':'Critical' for i in range(1,6)},'E7':'Major','E8':'Major','E9':'Minor'}
QUALITY={'N1','N2','N3','C1','C2','C3'}
def calculate_batch(report,inputs):
    ids=[i['item_id'] for i in inputs]
    if len(set(ids))!=len(ids):raise ValueError('Duplicate input item IDs')
    results=report['items'];rids=[r['item_id'] for r in results]
    if len(set(rids))!=len(rids) or set(rids)-set(ids):raise ValueError('Duplicate or unmatched result IDs')
    source={i['item_id']:i for i in inputs}
    for r in results:
        counts=collections.Counter()
        for f in r.get('findings',[]):
            code=f['test']
            if code not in SEVERITY and code not in QUALITY:raise ValueError('Unsupported or disabled rule: '+code)
            if f.get('verified') is not True:raise ValueError('Unverified finding: '+r['item_id'])
            if code in SEVERITY:counts[SEVERITY[code]]+=1
        if any(f['test']=='E1' for f in r.get('findings',[])) and any(f['test']!='E1' for f in r['findings']):raise ValueError('E1 must stop other checks')
        score=r['error_score']
        if score!='n/a':
            if isinstance(score,bool) or not isinstance(score,(int,float)) or not math.isfinite(score) or not 0<=score<=100:raise ValueError('Invalid score')
            expected=0 if counts['Critical'] else max(0,100-25*counts['Major']-5*counts['Minor'])
            if score!=expected:raise ValueError('Item score does not reconcile with verified findings: '+r['item_id'])
    def group(ins,rows):
        counts=collections.Counter(SEVERITY[f['test']] for r in rows for f in r.get('findings',[]) if f['test'] in SEVERITY)
        numeric=[r['error_score'] for r in rows if isinstance(r['error_score'],(int,float))]
        missing=[i['item_id'] for i in ins if i['item_id'] not in {r['item_id'] for r in rows}]
        unresolved=[r['item_id'] for r in rows if r['error_score']=='n/a']
        severe=bool(counts['Critical'] or counts['Major'])
        mean=sum(numeric)/len(numeric) if numeric else None
        final=min(mean,59) if mean is not None and severe else mean
        incomplete=bool(missing or unresolved or report.get('discarded_findings'))
        decision='NO GO' if severe or (final is not None and final<60) else 'INCOMPLETE — REVIEW REQUIRED' if incomplete or final is None else 'REVIEW REQUIRED'
        return {'total_units':len(ins),'scored_units':len(numeric),'missing_item_ids':missing,'unresolved_item_ids':unresolved,'severity_counts':{k:counts[k] for k in ['Critical','Major','Minor']},'raw_mean_score':round(mean,2) if mean is not None else None,'overall_decision_score':round(final,2) if final is not None else None,'serious_error_cap':59 if severe else None,'cap_reduced_score':mean is not None and severe and mean>59,'coverage_complete':not incomplete,'decision':decision,'automatic_pass':False}
    overall=group(inputs,results)
    langs=sorted({i.get('lang','unknown') for i in inputs})
    return {'calculation_version':'1.0.0','policy_origin':'T-QSI item rules plus direct user-approved overall decision rule, 15 October 2026','overall':overall,'by_language':{lang:group([i for i in inputs if i.get('lang','unknown')==lang],[r for r in results if source[r['item_id']].get('lang','unknown')==lang]) for lang in langs},'formula':'Item: Critical => 0; otherwise max(0,100-25*Major-5*Minor). Raw mean: sum of scored items / scored count. Overall: min(raw mean,59) if any confirmed Major/Critical, otherwise raw mean. Missing/n-a excluded and disclosed. No automatic pass.'}
def main():
    p=argparse.ArgumentParser();p.add_argument('report');p.add_argument('items');p.add_argument('--out',required=True);a=p.parse_args()
    with open(a.report,encoding='utf-8-sig') as f:r=json.load(f)
    with open(a.items,encoding='utf-8-sig') as f:i=json.load(f)
    r['batch_calculation']=calculate_batch(r,i)
    with open(a.out,'w',encoding='utf-8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
if __name__=='__main__':main()
