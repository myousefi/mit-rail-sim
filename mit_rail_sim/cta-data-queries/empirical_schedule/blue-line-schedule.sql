WITH schd AS (
    SELECT *
    FROM schedule_dimension.schd_rail_timepoint_times srtt
    WHERE version = :version
        AND runid IS NOT NULL
        AND TRIM(runid) != 'None'
        AND ctadaytype = 1
),
blue_line_runs AS (
    SELECT DISTINCT runid
    FROM schd
    WHERE timepointid SIMILAR TO '%%(MgnMTS|FstPk|UICH|OHARE)%%'
),
ohare_mgn_short_turned AS (
    SELECT
        o.*,
        CASE
            WHEN m.runid IS NOT NULL THEN true
            ELSE false
        END AS short_turned
    FROM schd o
    LEFT JOIN schd m ON o.runid = m.runid
        AND m.timepointid = 'MgnMTS'
        AND m.timepoint_time <= o.timepoint_time + 3600
        AND m.timepoint_time > o.timepoint_time
    WHERE o.timepointid = 'OHareS'
        AND o.runid IN (SELECT runid FROM blue_line_runs)
),
fstpk_fos_short_turned AS (
    SELECT
        f.*,
        CASE
            WHEN s.runid IS NOT NULL THEN true
            ELSE false
        END AS short_turned
    FROM schd f
    LEFT JOIN schd s ON f.runid = s.runid
        AND s.timepointid = 'FosMTN'
        AND s.timepoint_time <= f.timepoint_time + 3600
        AND s.timepoint_time > f.timepoint_time
    WHERE f.timepointid = 'FstPkN'
        AND f.runid IN (SELECT runid FROM blue_line_runs)
)
SELECT
    REPLACE(o.runid, 'R', 'B') AS runid,
    o.timepoint_time,
    'O-Hare' AS terminal,
    o.short_turned
FROM ohare_mgn_short_turned o
UNION ALL
SELECT
    REPLACE(f.runid, 'R', 'B') AS runid,
    f.timepoint_time,
    'Forest Park' AS terminal,
    f.short_turned
FROM fstpk_fos_short_turned f
ORDER BY timepoint_time ASC;