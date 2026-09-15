# TC-FENCE-001 — enclosing fence with isolated and non-isolated modules

## Purpose

Verify how Quartus Prime Pro Chip Planner draws an enclosing fence around:

- `u_isolated`: exclusive Logic Lock placement and a bounded route region.
- `u_non_isolated`: non-exclusive Logic Lock placement and a bounded route
  region.
- an unassigned fence: no associated design hierarchy, zero route-region
  expansion, and geometry that fully encloses both modules.

This is primarily a Chip Planner geometry/rendering test. The exact requested
outer fence is also a negative Fitter-legality test because a reserved outer
placement region cannot contain logic belonging to other hierarchies.

## Quartus terminology used by this test

| Requested term | Quartus Prime Pro setting |
|---|---|
| Exclusive Logic Lock Region | `Reserved = On` / `RESERVE_PLACE_REGION ON` |
| Non-exclusive Logic Lock Region | `Reserved = Off` |
| Exclusive Route Region | No direct Quartus setting. Use a bounded `ROUTE_REGION`; validate exclusivity from Fitter results. |
| Fence RR width = 0 | Routing Region uses the same boundary as the fence placement region (expansion `0`) |

Quartus documentation explicitly states that routing regions cannot be
reserved. Therefore, do not record a visual outline alone as proof of
exclusive routing.

## Files

- `top.v` — synthesizable Verilog-2001 design containing the two module
  hierarchies.
- `regions.qsf.template` — portable assignment template. Device coordinates
  are placeholders because legal resource coordinates depend on the selected
  FPGA.

## Preconditions

1. Quartus Prime Pro with a device that supports Logic Lock routing regions.
2. A new project with `top` as the top-level entity and `top.v` included.
3. Complete Analysis & Synthesis before assigning hierarchy members.
4. Select coordinates containing only legal core resources. Keep each module
   region large enough for its logic.
5. Enable preservation of hierarchy if synthesis flattens either instance.

## Suggested geometry

Use equivalent legal coordinates on the selected device:

```text
+--------------------------------------------------------------+
|                     unassigned fence                         |
|                                                              |
|    +------------------+        +------------------+           |
|    | u_isolated       |        | u_non_isolated   |           |
|    | Reserved = On    |        | Reserved = Off   |           |
|    | RR expansion = 0 |        | RR expansion = 0 |           |
|    +------------------+        +------------------+           |
|                                                              |
+--------------------------------------------------------------+
```

The fence placement and routing outlines must form one closed rectangle. The
module rectangles must be strictly inside the fence boundary.

## Setup

### 1. Create the design module regions

1. Run **Processing > Start > Start Analysis & Synthesis**.
2. Open **Assignments > Logic Lock Regions Window**.
3. In Project Navigator, right-click `u_isolated`, then select
   **Logic Lock Region > Create New Logic Lock Region**.
4. Set the isolated region:
   - Size/State: **Fixed/Locked**
   - Reserved: **On**
   - Core-Only: **On**
   - Routing Region: **Custom**, with its boundary equal to the placement
     boundary (expansion zero).
5. Create a region for `u_non_isolated`.
6. Set the non-isolated region:
   - Size/State: **Fixed/Locked**
   - Reserved: **Off**
   - Core-Only: **On**
   - Routing Region: **Custom**, with its boundary equal to the placement
     boundary.
7. Save the project. Compare the generated `.qsf` assignments with
   `regions.qsf.template`.

### 2. Create the requested fence

1. Open **Tools > Chip Planner**.
2. Create a fixed Logic Lock region that encloses both module regions.
3. Leave the fence region's design-hierarchy/member field empty.
4. Set **Reserved = On** to model the requested exclusive placement.
5. Select **Custom** Routing Region and make its outline exactly equal to the
   fence placement outline. This represents route-region expansion `0`.
6. Ensure the outer outline is one closed shape with no gaps, holes, uncovered
   routing tiles, or partially selected routing resources.
7. Save screenshots before running the Fitter. Record the Quartus version,
   device, revision, and exact coordinates.

## Checks in Chip Planner

Use **View > Layers Settings** and enable Logic Lock placement regions, routing
regions, routing resources, and region labels.

| ID | Check | Expected result |
|---|---|---|
| CP-01 | Isolated module placement | `u_isolated` is Fixed/Locked and Reserved |
| CP-02 | Isolated module routing | Its routing outline equals its placement outline |
| CP-03 | Non-isolated placement | `u_non_isolated` is Fixed/Locked and not Reserved |
| CP-04 | Non-isolated routing | Its routing outline equals its placement outline |
| CP-05 | Fence membership | Fence has no hierarchy/member |
| CP-06 | Fence exclusivity | Fence placement is Reserved |
| CP-07 | Fence RR width | Routing and placement outlines coincide (expansion `0`) |
| CP-08 | Enclosure | Fence strictly encloses both module regions |
| CP-09 | Continuity | Fence outline has no gaps or holes |
| CP-10 | Routing-tile coverage | No routing tile on the fence outline is uncovered |
| CP-11 | Partial overlap | No routing resource is only partially covered at a fence edge |
| CP-12 | RR overlap | In the requested geometry, the fence routing region geometrically covers the complete routing regions of both modules |

For CP-10 and CP-11, zoom to routing-resource level and inspect all four
corners and each change in device-resource type; a device-level overview is
not sufficient.

## Fitter result and expected negative behavior

Run **Processing > Start Compilation**.

The exact requested geometry is expected to be rejected or made unsatisfiable:
`RESERVE_PLACE_REGION ON` reserves the outer fence for its own assigned
hierarchy, but the fence has no hierarchy and encloses `u_isolated` and
`u_non_isolated`. Their placement is therefore foreign to the reserved fence.

Pass the negative portion of this test when:

1. Chip Planner preserves and draws the requested geometry before fitting; and
2. Fitter reports the reservation/placement conflict instead of silently
   producing a successful fit that violates the reservation.

Capture the full Fitter message and `<revision>.fit.rpt`.

## Compilable control variant

Repeat the test with the fence **Reserved = Off**. Keep its hierarchy empty,
route-region expansion at zero, and all geometry unchanged.

Expected:

1. The design can fit if the selected device coordinates have enough
   resources.
2. Both hierarchy regions remain within their placement constraints.
3. The route-region outlines remain visible in Chip Planner.
4. A successful fit does **not** prove the fence route region is exclusive,
   because Quartus does not provide a reserved/exclusive route-region setting.

## Pass/fail summary

- **Visualization PASS:** CP-01 through CP-12 match the requested geometry.
- **Negative legality PASS:** Fitter diagnoses the exclusive outer placement
  conflict.
- **Control PASS:** the same geometry fits after only the fence placement
  reservation is disabled.
- **FAIL:** Chip Planner leaves a gap/hole, partially covers a routing resource,
  loses an overlap after reload, associates the fence with a hierarchy, or the
  Fitter silently accepts contradictory exclusive placement.
