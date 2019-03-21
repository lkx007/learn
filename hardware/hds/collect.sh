#!/bin/bash
# 'Hostname' of the host which will collect data

#日立存储数据采集


nohup /usr/bin/python /usr/local/zabbix/hdsgx00/hds_vsp_gx00_wbm.py  --cluster "$1" --user "$2" --password "$3" --hostname "$4"  --proxy "$5"   --smis_port "%6" --fun "$7"  >  /dev/null 2>&1 &






/usr/bin/python /usr/local/zabbix/hdsgx00/hds_vsp_gx00_wbm.py  --cluster "192.168.8.22" --user "maintenance" --password "raid-maintenance" --hostname "test_hds"  --proxy "10.142.88.7" --fun "msg"


/usr/bin/python /usr/local/zabbix/hdsgx00/hds_vsp_gx00_wbm.py  --cluster "192.168.8.22" --user "maintenance" --password "raid-maintenance" --hostname "test_hds"  --proxy "10.142.88.7" --fun "msg"


/usr/bin/python /usr/local/zabbix/hdsgx00/hds_vsp_gx00_discovery.py  --cluster "192.168.8.22" --user "maintenance" --password "raid-maintenance" --hostname "test_hds"  --discovery-types "disk"


