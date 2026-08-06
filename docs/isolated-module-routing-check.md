# Checking routing in an isolated module without the Chip Planner

The Chip Planner route/route-matrix display is often unusable: it needs a full
Fitter run with routing kept in the database, it is limited to certain device
families, and several routing layers only exist in Quartus Prime Standard
Edition. These methods answer the same question — *does any routing show up in
or across the isolated module?* — from reports and files instead.

## Method 1: Fitter Security Report (fastest, no scripting)

When a design compiles with secured regions, the Fitter writes a Security
Report into `Compilation Report > Fitter`, and the same tables land in
`<revision>.fit.rpt`:

| Panel | What it proves |
|---|---|
| Secured LogicLock Region Summary | the region really was treated as secured |
| Security Routing Interfaces | which interfaces abut which regions |
| Secured LogicLock Region Inputs and Outputs | every signal that legally enters or leaves |
| Security I/O Bank Usage | which I/O banks the region owns |

Read it as: any signal crossing the boundary must appear in the inputs/outputs
panel *and* be carried by a security routing interface. Anything else is a
route that should not be there. If the panels are missing altogether, the
separation constraints were not applied, which is also why the Chip Planner had
nothing to draw.

```bash
grep -n -A40 "Secured LogicLock Region Summary" <revision>.fit.rpt
grep -n -A40 "Security Routing Interfaces"      <revision>.fit.rpt
```

## Method 2: back-annotated routing file (definitive, scriptable)

The `.rcf` is the text form of the routing the Chip Planner would draw. Each
entry names a signal and lists the routing elements it uses with their device
coordinates:

```
signal_name = crypto_core:u_crypto|done {
	LOCAL_LINE:X16Y13S0I2;
	R4:X20Y13S0I11;
	dest = (monitor:u_monitor|done_r, DATAA), route_port = DATAA;
}
```

Generate it, then compare every coordinate against the region window:

```bash
quartus_cdb <project> -c <revision> --back_annotate=routing
# or: quartus_cdb -t scripts/back_annotate_routing.tcl <project> <revision>

python3 scripts/check_isolated_routing.py \
    --qsf <project>.qsf \
    --rcf <revision>.rcf \
    --fit-rpt <revision>.fit.rpt
```

`scripts/check_isolated_routing.py` reads the LogicLock and security
assignments (`LL_ORIGIN`, `LL_WIDTH`, `LL_HEIGHT`,
`LL_REGION_SECURITY_LEVEL`, `LL_SECURITY_ROUTING_INTERFACE`, `LL_MEMBER_OF`,
`LL_MEMBER_OF_SECURITY_ROUTING_INTERFACE`) and reports three kinds of failure:

- routing belonging to another module that passes through the isolated region,
- routing inside the fence that surrounds the isolated region,
- routing that leaves the isolated region without a security routing interface.

It exits non-zero on failure, so it can run in a regression script. Try it on
the bundled example, which contains one deliberate violation:

```bash
python3 scripts/check_isolated_routing.py \
    --qsf scripts/examples/isolation_demo.qsf \
    --rcf scripts/examples/isolation_demo.rcf
```

Routing back-annotation requires Standard Edition, and it is refused unless
`LOGIC_CELL_INSERTION_LOGIC_DUPLICATION` and `AUTO_REGISTER_DUPLICATION` are
off. In Pro Edition, fall back to method 1 or 3.

## Method 3: placement cross-check from the netlist

Before chasing routing, confirm no foreign cell was placed in the region. This
dumps every node with its device location so you can filter by the region
window:

```bash
quartus_cdb -t scripts/dump_isolated_nodes.tcl <project> <revision> > nodes.csv
```

A cell from another hierarchy inside the region window explains routing through
the region, and is a placement problem rather than a router problem.

## Method 4: connectivity check in the Timing Analyzer

`quartus_sta` can prove there is no timing path between the isolated module and
the rest of the design, which is a useful independent signal when routing data
is unavailable:

```tcl
project_open <project> -revision <revision>
create_timing_netlist
# any path reported here crosses the isolation boundary
report_timing -from [get_registers {crypto_core:u_crypto|*}] \
              -to   [get_registers {*}] -npaths 100 -detail full_path
delete_timing_netlist
```

Exclude the signals that are legitimately assigned to a security routing
interface; anything left over is a connection the isolation was supposed to
prevent.

## If you still want the graphical view to work

- Run a full compile; a Fitter-only or rapid-recompile run leaves no routing to
  display.
- `View > Layers Settings`, pick the Detailed preset and enable the device
  routing resource layers; the Basic and Floorplan Editing presets hide them.
- Routing appears only after you select something: use `Expand Connections` on
  a selected node, or `Show Physical Routing` / `Highlight Routing` from the
  Locate History window.
- Check edition and device family support before concluding the display is
  broken.
