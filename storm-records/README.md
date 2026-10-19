# Storm records (TEST, branch storm-records)

A test of per-lot storm records for Hard Hat Weather, built Oct. 19, 2026 after Scoop OK'd it
("ok", 8:53 AM: build it on a test copy and try it on last winter's storms first). Nothing here touches
the live sender, the website or any customer.

## The idea
After every storm, each plow customer's lot gets a record of what happened there, kept automatically:
- snow total at the lot, checked against the lot's plow amount, and about when the plow amount was reached;
- hour by hour: snow, sleet, freezing rain or rain, and the temperature; ice; whether it thawed and refroze;
- in the live version, the PLOW / SALT / WATCH calls the company got and when (a dated warning record).

Other trades get rain measured by radar at the job site during work hours, next to the nearest airport.
Why: slip-and-fall claims and per-push billing arguments are won with records ("the side with the best
records often wins"); certified per-location snow totals cost $50-$140 per location (WeatherWorks CST).
This is not certified; it's a free, automatic daily record.

## Data (all free, public NOAA data)
- **Snow:** NOAA National Snowfall Analysis (NOHRSC sfav2), 6-hour and 24-hour grids (~4 km),
  `https://www.nohrsc.noaa.gov/snowfall_v2/data/YYYYMM/sfav2_CONUS_6h_YYYYMMDDHH.tif` (archive back
  through at least Nov. 2025).
- **When it fell:** NOAA MRMS MultiSensor QPE, 1-hour, 1 km (radar plus gauges), on AWS:
  `https://noaa-mrms-pds.s3.amazonaws.com/CONUS/MultiSensor_QPE_01H_Pass2_00.00/YYYYMMDD/...`
  (Pass1 when Pass2 is missing). Each 6-hour snow total is spread over its hours in proportion to the
  radar precipitation at the lot.
- **Type and temperature:** the nearest airport's hourly reports (IEM ASOS archive: MGC, PPO, VPZ, SBN).
  When radar shows precipitation at the lot but the airport reports none (lake-effect bands), the type
  comes from the temperature.
- **Checks:** NWS storm reports (IEM LSR) and CoCoRaHS observers (IEM daily API). The snowfall analysis
  uses many of the same reports, so the snow check is generous; the rain gauges are independent of the
  radar estimate.

## Results (run 39268159936, Oct. 19, 2026)
- Records for last winter's 5 big storms (Nov. 9-10, Nov. 29-30, Jan. 12-15, Jan. 25-26, Jan. 30-31) at 5 test
  lots, plus rain during work hours at 3 sites on 6 days. See `out/index.html`.
- **Snow vs 262 CoCoRaHS 24-hour reports:** typical miss 0.5 in., within 1 in. 75%, within 2 in. 91%, no bias.
  Generous: the analysis takes in many of these reports.
- **Snow vs 160 NWS storm reports (storm totals):** typical miss 1.5 in., within 2 in. 65%, about 1 in. low on
  average. Worst in narrow lake-effect bands: Fish Lake / Mill Creek's 20 in. (Jan. 15) showed as about 7.
  That's why each record lists the measured reports within 6 miles next to the estimate.
- **Radar rain vs 351 CoCoRaHS gauge-days:** typical miss 0.10 in., 98% within 1 in. (independent check).
- Example: Michigan City lot (Meijer, 5150 Franklin St), Jan. 30-31: 6.2 in.; two NWS reports 2.5 miles away
  measured 6.0. Plow amount (2 in.) reached about 11 PM Friday.
- MRMS radar water badly undercounts cold lake-effect snow (0.1-0.3 in. of water for 6-12 in. of snow), so it's
  used only to time the snow within each 6-hour quarter, together with the airport's reported snow rate.
- The Michigan City airport's rain gauge read 0.00 on every rainy day checked; rain comparisons use La Porte's
  or Valparaiso's gauge.
- Sample customer page: claude.ai artifact "Hard Hat Storm Record" (made by `scripts/storm_records/sample_page.py`).

## Files
- `scripts/storm_records/build.py` - the engine (`run.py probe` checks which archives answer).
- `storm-records/config.json` - test lots (public places only) and storm windows.
- `storm-records/out/` - results written by the "Storm records (test)" job: `records/<storm>/<lot>.html|json`,
  `rain/<site>-<day>.json`, `index.html`, `summary.json`, `summary.txt`.

## To switch it on (not done; needs Scoop's OK)
1. A GitHub job here saves a regional grid (snow analysis and hourly radar precipitation for NW Indiana and
   SW Michigan) after each storm to a data branch. No customer locations in this public repository.
2. The Hard Hat sender (Apps Script, private) reads that grid at each customer's lots, writes the record to
   the company's Weather log, and emails it the morning after the storm with the calls it sent.
3. Delay records and the rain-out guarantee check use radar at the site, with the station as a second line.
4. The Hard Hat page describes storm records (a website publish: check_site, credits, Scoop's OK).
