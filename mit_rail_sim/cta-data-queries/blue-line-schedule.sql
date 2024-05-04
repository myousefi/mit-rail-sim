WITH schd AS (
    SELECT *
    FROM schedule_dimension.schd_rail_timepoint_times srtt
    WHERE version = :version
        AND runid IS NOT NULL
        AND TRIM(runid) != 'None'
    AND ctadaytype = 1
)
SELECT
    REPLACE(runid, 'R', 'B') AS runid,
    timepoint_time,
    'Forest Park' AS terminal
FROM schd
WHERE timepointid = 'FstPkN'
ORDER BY timepoint_time ASC;
