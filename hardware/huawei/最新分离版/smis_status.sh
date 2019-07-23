#!/bin/sh
#


if [ ! `pidof cimserver` ];then
nohup  /usr/local/src/smisprovider/conf/start_agent.sh > /dev/null  2>1&
fi

if [ ! `pidof slpd` ];then
nohup  /usr/local/src/smisprovider/conf/start_slp.sh  > /dev/null  2>1&
fi



crond 

#check smis tatus   add by allen
* * * * * /usr/local/src/smis_status.sh


#add by allen
export LD_LIBRARY_PATH=/usr/local/src/smisprovider/lib
