# Recorded UI Versions

Current version: **1.2.1**. Recorded 24 October 2026.

- **1.2.1**: five modules; Team and Calibration removed from navigation, routing
  and screen initialization. Dashboard, Courses and Assignments, Grading Standards,
  Review Analytics, Settings and Activity retain the accepted 1.2 styling.
- **1.2.2**: six modules; includes the existing demonstration Team and Calibration
  screen and browser-local notes. It does not imply a real multi-user service.

Each directory retains its frontend source files, VERSION and SHA-256 manifest.
The root application currently serves 1.2.1. Version directories are reference
snapshots, not separate published routes. Backend and user data remain shared and
are intentionally excluded. Existing calibration notes were not deleted.

The active 1.2.1 now includes the editable real-data implementation described in
[the demo record](../docs/14_VERSION_1_2_1_EDITABLE_DEMO.md). Its former static UI
is retained separately in 1.2.1-static-baseline/. Version 1.2.2 is unchanged.
