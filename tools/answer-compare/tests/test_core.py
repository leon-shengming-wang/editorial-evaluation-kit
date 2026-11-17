import copy
import json
import unittest
from comparekit.core import InputError, analyze, check, metrics, parse, validate

def case(**kw):
    c = dict(id='one', prompt='Be brief.', answer_a='Good.', answer_b='More words here.', constraints=[{'type':'max_words','value':2}]); c.update(kw); return c

class CoreTests(unittest.TestCase):
    def test_preference_is_rule_only(self):
        r = analyze([case()])['cases'][0]
        self.assertEqual(r['suggestion'], 'A')
        self.assertIn('not an overall', r['suggestion_reason'])
    def test_no_constraints_requires_review(self):
        self.assertEqual(analyze([case(constraints=[])])['cases'][0]['suggestion'],'review')
    def test_empty_answer_never_wins(self):
        self.assertEqual(analyze([case(answer_a='')])['cases'][0]['suggestion'],'review')
    def test_equal_checks_not_quality_tie(self):
        r = analyze([case(answer_b='Wrong.')])['cases'][0]
        self.assertEqual(r['suggestion'],'tie'); self.assertIn('not a quality tie',r['suggestion_reason'])
    def test_hash_changes_with_input(self):
        self.assertNotEqual(analyze([case()])['batch_id'],analyze([case(prompt='Other')])['batch_id'])
    def test_hash_stable_key_order(self):
        self.assertEqual(analyze([case()])['batch_id'],analyze([dict(reversed(list(case().items())))])['batch_id'])
    def test_hash_changes_with_constraints(self):
        self.assertNotEqual(analyze([case()])['batch_id'],analyze([case(constraints=[])])['batch_id'])
    def test_jsonl(self):
        self.assertEqual(len(parse(json.dumps(case())+'\n'+json.dumps(case(id='two')))),2)
    def test_wrapper(self):
        self.assertEqual(parse(json.dumps({'cases':[case()]}))[0]['id'],'one')
    def test_single(self):
        self.assertEqual(len(parse(json.dumps(case()))),1)
    def test_bom(self):
        self.assertEqual(len(parse('\ufeff'+json.dumps([case()]))),1)
    def test_errors(self):
        for text in ('','no json','[]','42','null'):
            with self.subTest(text=text), self.assertRaises(InputError): parse(text)
    def test_duplicate_ids(self):
        with self.assertRaises(InputError): validate([case(),case()])
    def test_bad_case_fields(self):
        for c in (case(id=''),case(prompt=' '),case(answer_a=None),case(extra='x'),case(constraints=None)):
            with self.subTest(c=c), self.assertRaises(InputError): validate([c])
    def test_case_limit(self):
        with self.assertRaises(InputError): validate([case(id=str(i)) for i in range(201)])
    def test_text_limit(self):
        with self.assertRaises(InputError): validate([case(answer_a='a'*50001)])
    def test_bad_constraints(self):
        for c in ({'type':'made_up'},{'type':'max_words','value':True},{'type':'max_words','value':-1},{'type':'required_terms','value':[]},{'type':'required_terms','value':['']},{'type':'json_object','value':1},{'type':'min_words','value':2.5}):
            with self.subTest(c=c), self.assertRaises(InputError): validate([case(constraints=[c])])
    def test_non_mutating(self):
        c = case(); before=copy.deepcopy(c); analyze([c]); self.assertEqual(c,before)
    def test_metrics(self):
        self.assertEqual(metrics("Well-known facts aren't guesses.\n\n## Notes")['words'],5)
        self.assertEqual(metrics('')['paragraphs'],0)
        self.assertEqual(metrics('# One\n## Two')['headings'],2)
    def test_all_rules(self):
        examples=[('max_words',1,'one','pass'),('min_words',2,'one','fail'),('exact_bullets',2,'- one\n* two','pass'),('max_headings',0,'# title','fail'),('required_terms',['ART'],'An artist.','fail'),('required_terms',['art'],'Art matters.','pass'),('forbidden_terms',['bad'],'badly done','pass'),('forbidden_terms',['bad'],'BAD idea','fail'),('json_object',None,'{}','pass'),('json_object',None,'[]','fail'),('json_object',None,'{"a":NaN}','fail'),('json_object',None,'{"a":1,"a":2}','fail'),('no_markdown',None,'# title','fail'),('no_markdown',None,'plain text','review')]
        for t,v,text,expected in examples:
            with self.subTest(t=t,text=text): self.assertEqual(check(text,{'type':t,'value':v})['status'],expected)
    def test_phrase_literal(self):
        self.assertEqual(check('C++ works',{'type':'required_terms','value':['C++']})['status'],'pass')
    def test_summary(self):
        self.assertEqual(analyze([case()])['summary'],{'cases':1,'checks':2,'failures':1})
    def test_html_is_data(self):
        self.assertEqual(analyze([case(answer_a='<script>alert(1)</script>')])['cases'][0]['answer_a'],'<script>alert(1)</script>')

if __name__=='__main__': unittest.main()
