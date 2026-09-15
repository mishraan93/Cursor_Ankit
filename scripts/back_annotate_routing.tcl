# Back-annotate the fitted routing to a Routing Constraints File (.rcf).
#
#   quartus_cdb -t scripts/back_annotate_routing.tcl <project> [<revision>]
#
# The .rcf is the text form of what the Chip Planner draws, so it is the input
# for scripts/check_isolated_routing.py when the Chip Planner display is not
# usable. Routing back-annotation is a Quartus Prime Standard Edition feature;
# in Pro Edition use the Fitter Security Report instead.

package require ::quartus::project
package require ::quartus::backannotate

if {[llength $quartus(args)] < 1} {
    puts stderr "usage: quartus_cdb -t back_annotate_routing.tcl <project> \[<revision>\]"
    exit 2
}

set project [lindex $quartus(args) 0]
set revision [expr {[llength $quartus(args)] > 1 ? [lindex $quartus(args) 1] : ""}]

if {$revision eq ""} {
    project_open $project
} else {
    project_open $project -revision $revision
}

# Logic Cell Insertion and register duplication must be off, otherwise the
# Fitter refuses to back-annotate routing.
foreach {name value} {
    LOGIC_CELL_INSERTION_LOGIC_DUPLICATION OFF
    AUTO_REGISTER_DUPLICATION OFF
} {
    if {[get_global_assignment -name $name] ne $value} {
        puts "note: $name is not $value; routing back-annotation may be refused"
    }
}

if {[catch {logiclock_back_annotate -routing} err]} {
    puts stderr "routing back-annotation failed: $err"
    puts stderr "try the command line form: quartus_cdb $project --back_annotate=routing"
    project_close
    exit 1
}

puts "wrote routing constraints for project '$project'"
project_close
