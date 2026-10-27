# Google Workspace Reports

## Version 1.0.4

First non RC release of the line that was tagged 1.0.2 through 1.0.4.RC.

- Added the Google Workspace Billing report: 28 columns, one row per charge
  for the selected billing period.
- Added the Consumption column to the Google Workspace report, taken from the
  latest usage record (52 to 53 columns).
- Moved the Google API client to `reports/http.py`, shared by both reports.
- Fixed the fixture paths in the tests, which could not find their files.

## Version 1.0.1

- Fixed issue getting parameter domain id

## Version 1.0.0

- Initial version