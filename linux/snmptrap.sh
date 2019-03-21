#!/bin/bash

echo "安装Snmp相关服务 yum install -y net-snmp"
yum install -y net-snmp*

zabbix_trap_receiver="zabbix_trap_receiver.pl"
a=$(find / -name $zabbix_trap_receiver)
if [ "$a" ]
then
	$(cp $a /usr/bin/$zabbix_trap_receiver)
else
	echo "找不到文件"
	exit 1
fi

echo "/usr/bin/$zabbix_trap_receiver赋执行权限a+x"
$(chmod a+x /usr/bin/$zabbix_trap_receiver)


trapName="public"
echo "修改snmptrap配置文件"
snmptrapConf="/etc/snmp/snmptrapd.conf"
read -p "请输入团体名：" name
if [ -n "$name" ]
then 
	trapName=$name
else
	echo "没有输入团体名，将使用默认团体名public"
fi


echo "查找团体名是否已配置"
nameRaw=$(grep "^[^#].*execute.*$trapName" $snmptrapConf)
if [ -n  "$nameRaw" ]
then 
	newRaw=$(echo $nameRaw | tr -d "#")
        $(sed -i 's/$nameRaw/$newRaw/g' $snmptrapConf)
else
	echo "新增一个团体名"
	tmp=$(grep "^authCommunity" $snmptrapConf)
	if [ -n  "$tmp" ]
	then
        	$(sed -i  "/^authCommunity/authCommunity execute $trapName" $snmptrapConf)
	else
		#$(sed -i  "$ a authCommunity execute $trapName" $snmptrapConf)
		$(tac $snmptrapConf | sed '0,/authCommunity/{//s/.*/authCommunity execute $trapName\n&/}' | tac > $snmptrapConf )
	fi
	#echo "authCommunity execute $trapName" >>  $snmptrapConf
fi  


perl=$(grep perl $snmptrapConf)
if [ -n "$perl" ]
then
	echo "perl 已配置过"
else
	sed -i '$ a perl do "/usr/bin/zabbix_trap_receiver.pl"' $snmptrapConf
fi

echo "snmptrapd.conf 配置完成!"


zabbix_config="/usr/local/zabbix_proxy/etc/zabbix_proxy.conf"
echo "修改zabbix配置，暂时只修改$zabbix_config配置"

$(sed -i 's/.*StartSNMPTrapper=.*/StartSNMPTrapper=1/g' $zabbix_config)
$(sed -i 's/.*SNMPTrapperFile=.*/SNMPTrapperFile=\/tmp\/zabbix_traps.tmp/g' $zabbix_config)

$(touch /tmp/zabbix_traps.tmp && chmod 0777 /tmp/zabbix_traps.tmp )
$(chown zabbix:zabbix /tmp/zabbix_traps.tmp )
echo "所有修改完毕"
echo "重启zabbix_proxy服务 /etc/init.d/zabbix_proxy restart"
/etc/init.d/zabbix_proxy restart
echo "重启zabbix_agentd服务 /etc/init.d/zabbix_agentd restart"
/etc/init.d/zabbix_agentd restart
echo "杀死snmptrapd服务 killall snmptrapd"
killall snmptrapd
echo "启动snmptrapd服务 "
snmptrapd -C -c $snmptrapConf
