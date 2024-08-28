WITH departures AS (
    SELECT
        event_time,
        EXTRACT(EPOCH FROM event_time - event_time::date) AS time_in_sec,
        run_id,
        headway * 60 AS headway,
        deviation * 60 AS deviation,
        CASE
            WHEN scada = 'nwd720t' THEN 'Southbound'
            WHEN scada = 'wc452t' THEN 'Northbound'
        END AS direction

    FROM
        avas_spectrum.qt2_trainevent
    WHERE
        scada IN ('nwd720t', 'wc452t')
        AND event_time::date BETWEEN :start_date AND :end_date
        AND EXTRACT(DOW FROM event_time) BETWEEN 1 AND 5
        AND run_id LIKE 'B%'
)
SELECT
    event_time,
    time_in_sec,
    run_id,
    headway,
    deviation,
    direction
FROM
    departures
ORDER BY
    event_time::time;
