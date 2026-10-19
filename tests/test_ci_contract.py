import hashlib,json,tempfile,unittest
from pathlib import Path
from ci_contract import emit,validate

class PublicSafeContractTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.fixture=self.root/"fixture.txt"
        self.fixture.write_text("PUBLIC SYNTHETIC TEST FIXTURE ONLY\n")
        self.report=emit("stdlib_smoke",self.fixture,self.root/"evidence.json")

    def test_synthetic_handoff(self):
        self.assertEqual(validate(self.report)["status"],"PUBLIC_SYNTHETIC_TEST_PASS")
        self.assertEqual(self.report["artifact_sha256"],
                         hashlib.sha256(self.fixture.read_bytes()).hexdigest())
        self.assertEqual(json.loads((self.root/"evidence.json").read_text()),self.report)

    def test_no_private_fields(self):
        for key in ("api_key","private_strategy","market_ticks","broker_token"):
            x=dict(self.report);x[key]="secret"
            with self.assertRaisesRegex(ValueError,"unexpected keys"):
                validate(x)

    def test_no_live_orders(self):
        x=dict(self.report);x["orders_sent"]=1
        with self.assertRaisesRegex(ValueError,"no trading"):
            validate(x)

    def test_no_false_real_data_claim(self):
        x=dict(self.report);x["source"]="DUKASCOPY_REAL"
        with self.assertRaisesRegex(ValueError,"private source"):
            validate(x)

    def test_no_false_success(self):
        x=dict(self.report);x["tests_failed"]=1
        with self.assertRaisesRegex(ValueError,"tests must pass"):
            validate(x)

    def test_bad_hash(self):
        x=dict(self.report);x["artifact_sha256"]="bad"
        with self.assertRaisesRegex(ValueError,"hash invalid"):
            validate(x)

if __name__=="__main__":unittest.main()
