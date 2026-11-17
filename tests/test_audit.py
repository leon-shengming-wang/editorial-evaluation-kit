import copy
import sqlite3
import unittest
from reviewbench.audit import AuditStore
from test_core import example

class AuditTests(unittest.TestCase):
    def setUp(self):
        self.store=AuditStore(':memory:'); self.addCleanup(self.store.close); self.store.import_cases([example()])
    def test_import_idempotent(self):
        self.store.import_cases([example()]); self.assertEqual(self.store.connection.execute('SELECT COUNT(*) FROM cases').fetchone()[0],1)
    def test_rejects_changed_case(self):
        record=example(); record['prompt']='Changed prompt'
        with self.assertRaises(ValueError): self.store.import_cases([record])
    def test_import_atomic(self):
        new=example(); new['id']='new-case'; changed=example(); changed['prompt']='Changed'
        with self.assertRaises(ValueError): self.store.import_cases([new,changed])
        self.assertEqual(self.store.connection.execute('SELECT COUNT(*) FROM cases').fetchone()[0],1)
    def test_history_preserved(self):
        first=self.store.add_review('test-001','practice-reviewer','B','Initial illustrative judgment.')
        second=self.store.add_review('test-001','practice-reviewer','A','Correction: source date is May 4.')
        self.assertGreater(second,first); self.assertEqual(len(self.store.history('test-001')),2); self.assertEqual(self.store.disagreements(),[])
    def test_disagreement_not_accuracy(self):
        self.store.add_review('test-001','practice-reviewer','B','Demonstrate review queue only.')
        self.assertEqual(self.store.disagreements()[0][2:4],('A','B'))
    def test_each_reviewers_latest(self):
        self.store.add_review('test-001','reviewer-one','B','First')
        self.store.add_review('test-001','reviewer-two','tie','Second')
        self.assertEqual(len(self.store.disagreements()),2)
    def test_unknown_case(self):
        with self.assertRaises(sqlite3.IntegrityError): self.store.add_review('missing','reviewer','A','Reason')
    def test_invalid_winner(self):
        with self.assertRaises(ValueError): self.store.add_review('test-001','reviewer','C','Reason')
    def test_empty_fields(self):
        with self.assertRaises(ValueError): self.store.add_review('test-001','','A','Reason')
        with self.assertRaises(ValueError): self.store.add_review('test-001','reviewer','A',' ')
    def test_parameterized_sql(self):
        name="x'); DROP TABLE cases; --"
        self.store.add_review('test-001',name,'A','Literal text, not SQL.')
        self.assertEqual(self.store.history('test-001')[0][1],name)
        self.assertEqual(self.store.connection.execute('SELECT COUNT(*) FROM cases').fetchone()[0],1)

class CalibrationCliTests(unittest.TestCase):
    def test_import_no_fake_reviews(self):
        import tempfile
        from pathlib import Path
        from reviewbench.calibrate import main
        with tempfile.TemporaryDirectory() as directory:
            db=str(Path(directory)/'reviews.sqlite3')
            source=str(Path(__file__).resolve().parents[1]/'data/cases.jsonl')
            self.assertEqual(main(['--database',db,'import',source]),0)
            with AuditStore(db) as store:
                self.assertEqual(store.connection.execute('SELECT COUNT(*) FROM reviews').fetchone()[0],0)
                from reviewbench.core import load
                self.assertEqual(store.connection.execute('SELECT COUNT(*) FROM cases').fetchone()[0],len(load(source)))
    def test_review_and_history(self):
        import tempfile
        from pathlib import Path
        from reviewbench.calibrate import main
        with tempfile.TemporaryDirectory() as directory:
            db=str(Path(directory)/'reviews.sqlite3')
            with AuditStore(db) as store: store.import_cases([example()])
            self.assertEqual(main(['--database',db,'review','test-001','--reviewer','test-fixture','--winner','A','--reason','Test fixture, not a real review.']),0)
            self.assertEqual(main(['--database',db,'history','test-001']),0)
            self.assertEqual(main(['--database',db,'disagreements']),0)
    def test_unknown_case_returns_error(self):
        from reviewbench.calibrate import main
        self.assertEqual(main(['--database',':memory:','review','missing','--reviewer','fixture','--winner','A','--reason','Test']),1)
