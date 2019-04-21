#!/bin/sh

echo "修改镜像地址"
dir='/etc/yum.repos.d/http.repo'
media='baseurl=http://10.142.88.150/centos7'
#sed -i "s/baseurl=.*/#&/g;" $dir 
#sed -i "/baseurl=.*/a${media}/" $dir 
sed -i "s/baseurl=.*/#&/g;/baseurl=.*/a${media}" $dir #跟上面两个效果一样

echo "清除yum源缓存"
yum clean all
rm -rf /var/cache/yum
echo "建立yum源"
mkdir  /media/CentOS-7.5_1804/
yum makecache
yum -y install net-snmp*

echo "修改snmptrapd.conf"
echo "disableAuthorization yes" >> /etc/snmp/snmptrapd.conf
echo 'perl do "/usr/bin/zabbix_trap_receiver.pl"'  >> /etc/snmp/snmptrapd.conf

killall snmptrapd
snmptrapd -C -c /etc/snmp/snmptrapd.conf

rm -rf /tmp/a