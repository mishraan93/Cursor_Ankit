# Dump every placed node with its device location as CSV.
#
#   quartus_cdb -t scripts/dump_isolated_nodes.tcl <project> [<revision>] > nodes.csv
#
# Use this when the Chip Planner cannot show the floorplan: the CSV tells you
# which cells sit inside an isolated region's coordinate window, so you can
# confirm that nothing foreign was placed there before looking at routing.

package require ::quartus::project
package require ::quartus::chip_planner

if {[llength $quartus(args)] < 1} {
    puts stderr "usage: quartus_cdb -t dump_isolated_nodes.tcl <project> \[<revision>\]"
    exit 2
}

set project [lindex $quartus(args) 0]
set revision [expr {[llength $quartus(args)] > 1 ? [lindex $quartus(args) 1] : ""}]

if {$revision eq ""} {
    project_open $project
} else {
    project_open $project -revision $revision
}

read_netlist

# The set of queryable properties differs between device families, so ask the
# netlist which ones exist rather than assuming a fixed list.
set location_key ""
if {![catch {get_info_parameters -node} params]} {
    foreach candidate {location loc position} {
        if {[lsearch -exact $params $candidate] >= 0} {
            set location_key $candidate
            break
        }
    }
}
if {$location_key eq ""} {
    set location_key "location"
}

puts "name,type,location"
foreach_in_collection node [get_nodes -type all] {
    set name ""
    set type ""
    set location ""
    catch {set name [get_node_info -node $node -info name]}
    catch {set type [get_node_info -node $node -info type]}
    catch {set location [get_node_info -node $node -info $location_key]}
    puts "\"$name\",\"$type\",\"$location\""
}

project_close
