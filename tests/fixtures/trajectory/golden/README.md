Golden trajectory fixtures live in this directory.

Required files when a golden run is committed:

- `manifest.json`
- `presence_episode_df.pkl`
- `transition_units_df.pkl`
- `transition_nodes_df.pkl`
- `global_units_df.pkl`
- `global_presence_episode_df.pkl`
- `hourly_metric_summary_df.pkl`
- `route_family_df.pkl`

Current policy:

- tests may skip when `manifest.json` is absent
- once `manifest.json` exists, listed artifacts must exist and match the declared contract
