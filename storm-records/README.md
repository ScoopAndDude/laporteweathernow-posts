# Storm records (TEST, branch storm-records)

A test of per-lot storm records for Hard Hat Weather, built Oct. 19, 2026 after Scoop OK'd it
("ok", 8:53 AM). Nothing here touches the live sender, the website or any customer.

The idea: after every storm, each plow customer's lot gets a record of what happened there: snow total
(checked against the lot's plow amount), hour-by-hour snow, ice and temperature, and whether it refroze.
Other trades get radar-measured rain at the job site. All from free NOAA data.

- `scripts/storm_records/` - the code; `run.py probe` checks which archives answer.
- `storm-records/out/` - results written by the "Storm records (test)" job.
