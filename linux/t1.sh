#!/bin/sh

cp /usr/local/share/snmp/snmp_perl_trapd.pl /usr/share/snmp/

echo "修改snmptrap配置文件"
snmptrapConf="/etc/snmp/snmptrapd.conf"




disableAuthorization yes
perl do "/usr/bin/zabbix_trap_receiver.pl"