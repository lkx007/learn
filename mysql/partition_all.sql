DELIMITER $$
CREATE PROCEDURE `partition_maintenance_all`(SCHEMA_NAME VARCHAR(32))
BEGIN
       CALL partition_maintenance(SCHEMA_NAME, 'history', 3, 24, 7);
       CALL partition_maintenance(SCHEMA_NAME, 'history_log', 3, 24, 7);
       CALL partition_maintenance(SCHEMA_NAME, 'history_str', 3, 24, 7);
       CALL partition_maintenance(SCHEMA_NAME, 'history_text', 3, 24, 7);
       CALL partition_maintenance(SCHEMA_NAME, 'history_uint', 3, 24, 7);
       CALL partition_maintenance(SCHEMA_NAME, 'trends', 365, 24, 14);
       CALL partition_maintenance(SCHEMA_NAME, 'trends_uint', 365, 24, 14);
END$$
DELIMITER ;



SELECT * FROM history as h 
LEFT JOIN items  as i on i.itemid = h.itemid
LEFT JOIN `hosts` as  hs on hs.hostid = i.hostid
GROUP BY hs.proxy_hostid
limit 30


select  *,count(eventid),   FROM_UNIXTIME(clock,'%Y%m%d %H:%i')  as t   
from events group by t  order by clock desc  limit mit 20;

SELECT r.*,h1.`host` from 
(
SELECT e.clock,FROM_UNIXTIME(e.clock,'%Y%m%d %H')  as time_h,
COUNT(e.eventid),h.proxy_hostid
from `events` as e 
LEFT JOIN `triggers` as t on t.triggerid = e.objectid
LEFT JOIN functions as f on f.functionid = t.triggerid
LEFT JOIN items as i on i.itemid = f.itemid
LEFT JOIN `hosts` as h on h.hostid = i.hostid


where  
h.proxy_hostid = 10278  # 5-proxy
and
e.clock > ( UNIX_TIMESTAMP() - 3600 * 24 )

GROUP BY h.proxy_hostid,time_h
order by e.clock desc
) as r
LEFT JOIN `hosts` as h1 on h1.hostid = r.proxy_hostid 
