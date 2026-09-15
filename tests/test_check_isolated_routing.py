import tempfile
import unittest
from pathlib import Path

from scripts.check_isolated_routing import check, parse_qsf, parse_rcf


QSF = """\
set_global_assignment -name LL_ORIGIN X10_Y10 -section_id secure
set_global_assignment -name LL_WIDTH 8 -section_id secure
set_global_assignment -name LL_HEIGHT 8 -section_id secure
set_global_assignment -name LL_REGION_SECURITY_LEVEL 3 -section_id secure
set_instance_assignment -name LL_MEMBER_OF secure -to "core:u_core" -section_id secure
"""


class IsolationRoutingCheckTest(unittest.TestCase):
    def parse(self, qsf: str, rcf: str):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            qsf_path = root / "test.qsf"
            rcf_path = root / "test.rcf"
            qsf_path.write_text(qsf)
            rcf_path.write_text(rcf)
            return parse_qsf(qsf_path), parse_rcf(rcf_path)

    def test_foreign_route_inside_region_fails(self):
        regions, elements = self.parse(
            QSF,
            """\
signal_name = other:u_other|net {
    R4:X12Y12S0I1;
    dest = (other:u_other|reg, DATAA), route_port = DATAA;
}
""",
        )

        violations, _ = check(regions, elements, fence=1)

        self.assertEqual(1, len(violations))
        self.assertIn("foreign routing", violations[0])

    def test_owned_route_inside_region_passes(self):
        regions, elements = self.parse(
            QSF,
            """\
signal_name = core:u_core|net {
    LOCAL_LINE:X12Y12S0I1;
    dest = (core:u_core|reg, DATAA), route_port = DATAA;
}
""",
        )

        violations, _ = check(regions, elements, fence=1)

        self.assertEqual([], violations)

    def test_missing_security_assignment_fails(self):
        regions, elements = self.parse(
            "set_global_assignment -name TOP_LEVEL_ENTITY top\n",
            """\
signal_name = top|net {
    LOCAL_LINE:X1Y1S0I1;
}
""",
        )

        violations, _ = check(regions, elements, fence=1)

        self.assertEqual(1, len(violations))
        self.assertIn("No secured LogicLock region", violations[0])


if __name__ == "__main__":
    unittest.main()
