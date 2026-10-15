import unittest,sys,pathlib,copy,json
P=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(P/'skills/tqsi-calculate/scripts'))
from calculate_batch import calculate_batch
class CalculationTests(unittest.TestCase):
    def batch(self,codes,extra=0):
        items=[];rows=[]
        for n,c in enumerate(codes+[None]*extra):
            fs=[{'test':c,'verified':True}] if c else []
            score=0 if c in ['E1','E2','E3','E4','E5'] else 75 if c in ['E7','E8'] else 95 if c=='E9' else 100
            items.append({'item_id':str(n),'lang':'hi'});rows.append({'item_id':str(n),'error_score':score,'findings':fs})
        return {'items':rows,'discarded_findings':[]},items
    def calc(self,codes,extra=0):
        r,i=self.batch(codes,extra);return calculate_batch(r,i)['overall']
    def test_major_cannot_hide_in_large_clean_set(self):
        self.assertEqual(self.calc(['E7'],999)['overall_decision_score'],59)
    def test_critical_cannot_hide(self):
        self.assertEqual(self.calc(['E4'],9)['overall_decision_score'],59)
    def test_cap_never_raises_low_score(self):
        self.assertEqual(self.calc(['E3'])['overall_decision_score'],0)
    def test_minor_only_no_cap(self):
        d=self.calc(['E9'],9);self.assertEqual(d['overall_decision_score'],99.5);self.assertEqual(d['decision'],'REVIEW REQUIRED')
    def test_no_automatic_pass(self):self.assertFalse(self.calc([None])['automatic_pass'])
    def test_missing_kept_visible(self):
        r,i=self.batch([None]);i.append({'item_id':'missing','lang':'hi'});d=calculate_batch(r,i)['overall'];self.assertFalse(d['coverage_complete']);self.assertIn('INCOMPLETE',d['decision'])
    def test_no_numeric_no_mean(self):self.assertIsNone(calculate_batch({'items':[]},[{'item_id':'x'}])['overall']['overall_decision_score'])
    def test_unverified_rejected(self):
        r,i=self.batch(['E7']);r['items'][0]['findings'][0]['verified']=False
        with self.assertRaises(ValueError):calculate_batch(r,i)
    def test_wrong_score_rejected(self):
        r,i=self.batch(['E7']);r['items'][0]['error_score']=100
        with self.assertRaises(ValueError):calculate_batch(r,i)
    def test_disabled_e6_rejected(self):
        r,i=self.batch([None]);r['items'][0]['findings']=[{'test':'E6','verified':True}]
        with self.assertRaises(ValueError):calculate_batch(r,i)
    def test_duplicate_ids_rejected(self):
        r,i=self.batch([None]);i.append(i[0])
        with self.assertRaises(ValueError):calculate_batch(r,i)
    def test_language_isolation_and_global_cap(self):
        r,i=self.batch(['E7',None]);i[1]['lang']='te';d=calculate_batch(r,i);self.assertEqual(d['overall']['overall_decision_score'],59);self.assertEqual(d['by_language']['te']['overall_decision_score'],100)
    def test_known_workbook(self):
        e=P/'examples';d=calculate_batch(json.loads((e/'report.json').read_text(encoding='utf-8')),json.loads((e/'items.json').read_text(encoding='utf-8')))['overall'];self.assertEqual(d['overall_decision_score'],44);self.assertEqual(d['severity_counts'],{'Critical':5,'Major':2,'Minor':2})
    def test_exact_sixty_review_and_below_sixty_no_go(self):
        r,i=self.batch([None]);r['items'][0]['findings']=[{'test':'E9','verified':True}]*8;r['items'][0]['error_score']=60;self.assertEqual(calculate_batch(r,i)['overall']['decision'],'REVIEW REQUIRED');r['items'][0]['findings'].append({'test':'E9','verified':True});r['items'][0]['error_score']=55;self.assertEqual(calculate_batch(r,i)['overall']['decision'],'NO GO')
if __name__=='__main__':unittest.main()
