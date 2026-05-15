# Timefold Examples

This folder contains a minimal example of the Timefold adapter exchange format
used by the Python pipeline.

Files:

- `simple_round_robin_input.json`: example adapter input exported from a simple
  4-team single round-robin instance
- `simple_round_robin_output.json`: example feasible solution returned by an
  external Timefold adapter

Current adapter limitations:

- only teams, slots, and inferred round-robin matches are modeled directly
- declared RobinX / ITC2021 constraint families are exported as metadata only
- complex constraints such as capacity, break, venue, travel, fairness, and
  soft penalties are ignored by the baseline adapter
- slot meaning is approximated as an ordered round index, not a full temporal
  or venue-aware model
