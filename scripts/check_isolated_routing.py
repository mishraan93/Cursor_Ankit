#!/usr/bin/env python3
"""Audit routing coordinates around an isolated (secured) region.

The check is text based: it reads the LogicLock/security assignments from the
Quartus Settings File and the back-annotated routing from the Routing
Constraints File, so it works from a shell without opening the Chip Planner.

Generate the .rcf first (Quartus Prime Standard Edition):

    quartus_cdb <project> -c <revision> --back_annotate=routing

Then:

    python3 scripts/check_isolated_routing.py --qsf <project>.qsf --rcf <revision>.rcf

This is a supplemental check, not a replacement for Quartus's Fitter Security
Report. An R4/C4/etc. coordinate identifies a routing-resource anchor and does
not fully describe the wire's span on every device family.

Exit status is 0 when no coordinate-level conflict is detected, 1 when a
conflict is found, and 2 when the inputs cannot establish a valid check.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# "LOCAL_LINE:X10Y20S0I3", "R4:X8Y13S1I27", "C16:X2Y40S0I5", ...
ROUTING_ELEMENT_RE = re.compile(
    r"\b(?P<kind>[A-Z][A-Z0-9_]*)\s*:\s*X(?P<x>-?\d+)Y(?P<y>-?\d+)(?P<rest>[SI]-?\d+)*"
)
SIGNAL_NAME_RE = re.compile(r"^\s*signal_name\s*=\s*(?P<name>.+?)\s*\{\s*$")
DEST_RE = re.compile(r"^\s*dest\s*=\s*\(\s*(?P<name>[^,]+?)\s*,")
ORIGIN_RE = re.compile(r"X(?P<x>-?\d+)[_\s]*Y(?P<y>-?\d+)", re.IGNORECASE)

QSF_GLOBAL_RE = re.compile(
    r"^\s*set_global_assignment\s+-name\s+(?P<name>\S+)\s+(?P<value>.*?)$", re.IGNORECASE
)
QSF_INSTANCE_RE = re.compile(
    r"^\s*set_instance_assignment\s+-name\s+(?P<name>\S+)\s+(?P<rest>.*?)$", re.IGNORECASE
)
SECTION_ID_RE = re.compile(r"-section_id\s+(?P<id>\"[^\"]+\"|\S+)", re.IGNORECASE)
TO_RE = re.compile(r"-to\s+(?P<to>\"[^\"]+\"|\S+)", re.IGNORECASE)


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value.strip()


@dataclass
class Region:
    """A LogicLock region, either a secured region or a security routing interface."""

    name: str
    origin_x: int | None = None
    origin_y: int | None = None
    width: int | None = None
    height: int | None = None
    security_level: str | None = None
    is_routing_interface: bool = False
    members: list[str] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)

    @property
    def is_secured(self) -> bool:
        return bool(self.security_level) and not self.is_routing_interface

    @property
    def placed(self) -> bool:
        return None not in (self.origin_x, self.origin_y, self.width, self.height)

    def contains(self, x: int, y: int, margin: int = 0) -> bool:
        if not self.placed:
            return False
        return (
            self.origin_x - margin <= x < self.origin_x + self.width + margin
            and self.origin_y - margin <= y < self.origin_y + self.height + margin
        )

    def owns_node(self, node: str) -> bool:
        return any(node == m or node.startswith(m + "|") for m in self.members)

    def bounds(self) -> str:
        if not self.placed:
            return "unplaced"
        return (
            f"X{self.origin_x}..X{self.origin_x + self.width - 1} "
            f"Y{self.origin_y}..Y{self.origin_y + self.height - 1}"
        )


@dataclass
class RoutingElement:
    kind: str
    x: int
    y: int
    signal: str
    dests: list[str]
    line_no: int


def parse_qsf(path: Path) -> dict[str, Region]:
    regions: dict[str, Region] = {}

    def region(name: str) -> Region:
        return regions.setdefault(name, Region(name=name))

    for raw in path.read_text(errors="replace").splitlines():
        line = raw.split("#", 1)[0]
        if not line.strip():
            continue

        section = SECTION_ID_RE.search(line)
        section_id = unquote(section.group("id")) if section else None

        m = QSF_GLOBAL_RE.match(line)
        if m and section_id:
            name = m.group("name").upper()
            value = unquote(SECTION_ID_RE.sub("", m.group("value")))
            reg = region(section_id)
            if name == "LL_ORIGIN":
                origin = ORIGIN_RE.search(value)
                if origin:
                    reg.origin_x = int(origin.group("x"))
                    reg.origin_y = int(origin.group("y"))
            elif name == "LL_WIDTH" and value.isdigit():
                reg.width = int(value)
            elif name == "LL_HEIGHT" and value.isdigit():
                reg.height = int(value)
            elif name in ("LL_REGION_SECURITY_LEVEL", "LL_SECURITY_LEVEL"):
                reg.security_level = value
            elif name == "LL_SECURITY_ROUTING_INTERFACE":
                reg.is_routing_interface = value.upper() == "ON"
            continue

        m = QSF_INSTANCE_RE.match(line)
        if m:
            name = m.group("name").upper()
            rest = m.group("rest")
            to = TO_RE.search(rest)
            if not to:
                continue
            target = unquote(to.group("to"))
            value = unquote(SECTION_ID_RE.sub("", TO_RE.sub("", rest)))
            if name == "LL_MEMBER_OF":
                region(section_id or value).members.append(target)
            elif name == "LL_MEMBER_OF_SECURITY_ROUTING_INTERFACE":
                reg = region(section_id or value)
                reg.is_routing_interface = True
                reg.signals.append(target)

    return regions


def parse_rcf(path: Path) -> list[RoutingElement]:
    elements: list[RoutingElement] = []
    signal = "<unknown>"
    dests: list[str] = []
    pending: list[RoutingElement] = []

    def flush() -> None:
        for element in pending:
            element.dests = list(dests)
            elements.append(element)
        pending.clear()

    for line_no, raw in enumerate(path.read_text(errors="replace").splitlines(), start=1):
        line = raw.split("#", 1)[0]
        if not line.strip():
            continue

        m = SIGNAL_NAME_RE.match(line)
        if m:
            flush()
            signal = unquote(m.group("name"))
            dests = []
            continue

        if line.strip().startswith("}"):
            flush()
            continue

        m = DEST_RE.match(line)
        if m:
            dests.append(unquote(m.group("name")))

        for element in ROUTING_ELEMENT_RE.finditer(line):
            pending.append(
                RoutingElement(
                    kind=element.group("kind"),
                    x=int(element.group("x")),
                    y=int(element.group("y")),
                    signal=signal,
                    dests=[],
                    line_no=line_no,
                )
            )

    flush()
    return elements


def signal_belongs_to(region: Region, element: RoutingElement) -> bool:
    if region.owns_node(element.signal):
        return True
    return any(region.owns_node(dest) for dest in element.dests)


def interfaces_for(regions: dict[str, Region], element: RoutingElement) -> list[Region]:
    return [
        r
        for r in regions.values()
        if r.is_routing_interface
        and any(
            sig == element.signal or element.signal.startswith(sig + "|") or sig in element.dests
            for sig in r.signals
        )
    ]


def check(
    regions: dict[str, Region], elements: list[RoutingElement], fence: int
) -> tuple[list[str], list[str]]:
    violations: list[str] = []
    notes: list[str] = []

    secured = [r for r in regions.values() if r.is_secured]
    if not secured:
        violations.append(
            "No secured LogicLock region found in the .qsf "
            "(expected LL_REGION_SECURITY_LEVEL on at least one region)."
        )
        return violations, notes

    for region in sorted(secured, key=lambda r: r.name):
        if not region.placed:
            violations.append(
                f"[{region.name}] region has no fixed origin/size; "
                "a secured region cannot be Auto or Floating."
            )
            continue

        notes.append(f"[{region.name}] {region.bounds()} ({len(region.members)} member(s))")

        for element in elements:
            inside = region.contains(element.x, element.y)
            in_fence = not inside and region.contains(element.x, element.y, margin=fence)
            owned = signal_belongs_to(region, element)
            via_interface = bool(interfaces_for(regions, element))

            if inside and not owned and not via_interface:
                violations.append(
                    f"[{region.name}] foreign routing inside the isolated region: "
                    f"{element.kind} at X{element.x}Y{element.y} carries '{element.signal}' "
                    f"(.rcf line {element.line_no})"
                )
            elif in_fence and not via_interface:
                violations.append(
                    f"[{region.name}] routing in the fence around the isolated region: "
                    f"{element.kind} at X{element.x}Y{element.y} carries '{element.signal}' "
                    f"(.rcf line {element.line_no})"
                )
            elif owned and not inside and not in_fence and not via_interface:
                violations.append(
                    f"[{region.name}] routing escapes the isolated region without a "
                    f"security routing interface: {element.kind} at X{element.x}Y{element.y} "
                    f"carries '{element.signal}' (.rcf line {element.line_no})"
                )

    return violations, notes


def summarise_fit_report(path: Path) -> list[str]:
    """Pull the Fitter Security Report panel titles out of <revision>.fit.rpt."""
    wanted = (
        "Secured LogicLock Region Summary",
        "Security Routing Interfaces",
        "Secured LogicLock Region Inputs and Outputs",
        "Security I/O Bank Usage",
    )
    found = []
    text = path.read_text(errors="replace")
    for title in wanted:
        found.append(f"{'found' if title in text else 'MISSING'}: {title}")
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--qsf", required=True, type=Path, help="Quartus Settings File")
    parser.add_argument("--rcf", required=True, type=Path, help="back-annotated Routing Constraints File")
    parser.add_argument("--fit-rpt", type=Path, help="Fitter report, checked for the Security Report panels")
    parser.add_argument(
        "--fence",
        type=int,
        default=1,
        help="width in LABs of the fence that must stay free of routing (default: 1)",
    )
    args = parser.parse_args()

    for path in (args.qsf, args.rcf):
        if not path.is_file():
            print(f"error: {path} not found", file=sys.stderr)
            return 2

    regions = parse_qsf(args.qsf)
    elements = parse_rcf(args.rcf)
    if not elements:
        print(
            "error: no routing elements were parsed from the .rcf; "
            "cannot establish isolation",
            file=sys.stderr,
        )
        return 2
    violations, notes = check(regions, elements, args.fence)

    print(f"regions:          {len(regions)}")
    print(f"routing elements: {len(elements)}")
    for note in notes:
        print(f"  {note}")

    if args.fit_rpt and args.fit_rpt.is_file():
        print("security report panels:")
        for line in summarise_fit_report(args.fit_rpt):
            print(f"  {line}")

    if violations:
        print(f"\nFAIL: {len(violations)} routing violation(s)")
        for violation in violations:
            print(f"  {violation}")
        return 1

    print("\nPASS: no coordinate-level routing conflict detected")
    print("Authoritative result: confirm the Quartus Fitter Security Report has no violations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
