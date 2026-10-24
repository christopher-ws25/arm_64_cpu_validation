"""Reject incomplete or contradictory guest reports without booting a VM."""
import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import payload

NONCE = "a" * 32


def valid_records(injected=False):
    records = []
    for name in payload.CASE_NAMES:
        failed = injected and name == payload.CASE_NAMES[-1]
        records.append(("ARM64_CASE", {"nonce": NONCE, "name": name,
                        "actual": "0x3", "expected": "0x4" if failed else "0x3",
                        "nzcv": "0x0", "expected_nzcv": "0x0", "passed": not failed}))
    rc = int(injected)
    records.append(("ARM64_PAYLOAD_RESULT", {"nonce": NONCE, "test": "isa_add_flags",
                    "cases": 6, "failures": rc, "injected_failure": injected, "exit_code": rc}))
    records.append(("ARM64_PAYLOAD_EXIT", {"nonce": NONCE, "exit_code": rc}))
    return records


def text(records):
    return "\n".join(marker + " " + json.dumps(value) for marker, value in records)


class PayloadProtocolTests(unittest.TestCase):
    def test_normal_and_injected_reports(self):
        for injected in (False, True):
            with self.subTest(injected=injected):
                self.assertEqual(payload.verify(text(valid_records(injected)), NONCE, injected)["exit_code"], int(injected))

    def test_missing_case_and_duplicate_summary(self):
        records = valid_records()
        for bad in (records[1:], records + [records[-2]]):
            with self.assertRaises(ValueError):
                payload.verify(text(bad), NONCE, False)

    def test_claimed_pass_cannot_hide_bad_measurement(self):
        records = copy.deepcopy(valid_records())
        records[0][1]["actual"] = "0x4"
        with self.assertRaisesRegex(ValueError, "verdict"):
            payload.verify(text(records), NONCE, False)

    def test_summary_cannot_hide_nonzero_guest_exit(self):
        records = copy.deepcopy(valid_records())
        records[-1][1]["exit_code"] = 1
        with self.assertRaisesRegex(ValueError, "summary/exit"):
            payload.verify(text(records), NONCE, False)

    def test_wrong_nonce_and_malformed_json_do_not_count(self):
        with self.assertRaises(ValueError):
            payload.verify(text(valid_records()), "b" * 32, False)
        noise = 'ARM64_CASE {bad json}\nARM64_CASE [1,2]\n'
        self.assertEqual(payload.verify(noise + text(valid_records()), NONCE, False)["exit_code"], 0)

    def test_injection_must_be_explicit_in_summary(self):
        with self.assertRaises(ValueError):
            payload.verify(text(valid_records(True)), NONCE, False)


if __name__ == "__main__":
    unittest.main()
