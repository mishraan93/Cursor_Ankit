# Cursor_Ankit

## Isolated module routing checks

Command-line checks for whether any routing shows up in or across an isolated
(secured) region, for use when the Chip Planner routing display is not
available. See [docs/isolated-module-routing-check.md](docs/isolated-module-routing-check.md).

| File | Purpose |
|---|---|
| `scripts/check_isolated_routing.py` | performs a supplemental coordinate-level audit of back-annotated routing; the Fitter Security Report remains authoritative |
| `scripts/back_annotate_routing.tcl` | writes the routing constraints file the check reads |
| `scripts/dump_isolated_nodes.tcl` | dumps node placements as CSV to cross-check what sits inside the region |
| `scripts/examples/` | sample settings and routing files, containing one deliberate violation |

```bash
python3 scripts/check_isolated_routing.py \
    --qsf scripts/examples/isolation_demo.qsf \
    --rcf scripts/examples/isolation_demo.rcf
```

## Quartus Chip Planner fence test

[`tests/quartus/fence_region/TC-FENCE-001.md`](tests/quartus/fence_region/TC-FENCE-001.md)
defines a manual Quartus Prime Pro test for an unassigned, zero-expansion
fence enclosing isolated and non-isolated module regions. It includes
synthesizable Verilog-2001 RTL and a portable `.qsf` assignment template.
