# Baltic Exchange indices reference (public)


This folder contains reference tables derived from the public Baltic Exchange indices page:
- Source: https://www.balticexchange.com/en/data-services/market-information0/indices.html

Files:
- `indices.csv`: index codes + descriptions + frequency
- `routes.csv`: route codes / lane codes + short descriptions
- `index_components.csv`: index constituents where explicitly provided on the page
- `vessel_types.csv`: vessel class specs and investor-tool vessel types listed on the page
- `ports_world_port_index.csv`: major ports + coordinates (World Port Index / Pub 150, via a public mirror; see below)

Notes:
- `TD26` is referenced in the Aframax TCE basket on the page but is not listed in the dirty tanker route table.

Interactive routes map:
- The interactive map at https://www.balticexchange.com/en/data-services/routes.html may contain additional routes beyond `routes.csv`.
- To extract those routes, capture a HAR file in your browser (DevTools -> Network -> "Save all as HAR with content") and run:
  - `python3 real/scripts/update_exchange_routes_from_har.py --har /path/to/routes.har`
- Outputs:
  - `datasets/exchange_reference/routes_interactive_map.csv`
  - `datasets/exchange_reference/routes_merged.csv`

Ports dataset:
- `ports_world_port_index.csv` is built from "UpdatedPub150.csv" (World Port Index / Pub 150).
- Build script: `real/scripts/build_ports_world_port_index.py`
