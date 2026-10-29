import tempfile
import unittest
from pathlib import Path
from research.ai_trader.signal_hub import normalize,research_preflight,ResearchQueue

def sample(source="AMOS_AI_TRADER"):
    return normalize({"action":"BUY","symbol":"XAUUSD","observed_at_ns":1234567890000000000,
                      "evidence_ref":"sha256:abc","entry":2600.0,"sl":2590.0,"tp":2620.0},source)
def risk():
    return {"locked":False,"unknown":False,"journal_corrupt":False,"busy":False,
            "source_verified":True,"daily_sends":0,"daily_losses":0,
            "daily_loss_amount":0,"worst_case_next_loss":10}
def limits():
    return {"max_daily_sends":5,"max_daily_losses":2,"max_daily_loss_amount":100}
class HorizontalIntegrationTests(unittest.TestCase):
    def test_source_mapping_and_dedup_key(self):
        self.assertEqual(sample(),sample())
        self.assertEqual(sample("DAGRAM_OBSERVATION")["source"],"DAGRAM_OBSERVATION")
        self.assertEqual(normalize({"action":"STAY","observed_at_ns":123,"evidence_ref":"e"},
                                   "DAGRAM_OBSERVATION")["action"],"WAIT")
    def test_no_backdating_without_observation(self):
        with self.assertRaises(ValueError):
            normalize({"action":"BUY","entry":1,"sl":.9,"tp":1.1,"evidence_ref":"e"},"DAGRAM_OBSERVATION")
    def test_invalid_prices(self):
        with self.assertRaises(ValueError):
            normalize({"action":"SELL","observed_at_ns":123,"evidence_ref":"e",
                       "entry":10,"sl":9,"tp":8},"AMOS_AI_TRADER")
    def test_three_risk_guards(self):
        s=sample()
        for field,value,expected in (("daily_sends",5,"DAILY_SEND_LIMIT"),
                                     ("daily_losses",2,"DAILY_LOSS_COUNT_LIMIT"),
                                     ("daily_loss_amount",95,"DAILY_LOSS_AMOUNT_LIMIT")):
            r=risk();r[field]=value
            self.assertEqual(research_preflight(s,r,limits()),expected)
    def test_unknown_blocks_and_duplicate(self):
        with tempfile.TemporaryDirectory() as d:
            q=ResearchQueue(Path(d)/"journal.jsonl")
            self.assertEqual(q.admit(sample(),risk(),limits())["status"],"QUEUED_FOR_RESEARCH")
            self.assertEqual(q.admit(sample(),risk(),limits())["status"],"DUPLICATE")
            q.mark_unknown()
            self.assertEqual(q.admit(sample(),risk(),limits())["status"],"LOCKED")
    def test_wait_never_queued(self):
        s=normalize({"action":"STAY","observed_at_ns":123,"evidence_ref":"e"},"DAGRAM_OBSERVATION")
        self.assertEqual(research_preflight(s,risk(),limits()),"NO_TRADE")
    def test_source_unverified(self):
        r=risk();r["source_verified"]=False
        self.assertEqual(research_preflight(sample(),r,limits()),"SOURCE_UNVERIFIED")
    def test_journal_corrupt_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            q=ResearchQueue(Path(d)/"journal.jsonl")
            q.state_path.write_text("{bad")
            with self.assertRaisesRegex(RuntimeError,"JOURNAL_CORRUPT_LOCKED"):
                q.admit(sample(),risk(),limits())
