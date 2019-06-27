#!/bin/sh


echo "修改代理mysql密码"
/usr/local/mysql/bin/mysql -u'root' -p'p@ssw0rd' -e "SET PASSWORD FOR 'zabbix_proxy'@'%' = PASSWORD('Ccssoft_2019@)(')"

echo "修改代理配置文件"

sed -i  's/^DBPassword.*/DBPassword=Ccssoft_2019@)(/g'   /usr/local/zabbix_proxy/etc/zabbix_proxy.conf


echo "重启代理和agent"
/etc/init.d/zabbix_proxy restart
/etc/init.d/zabbix_agentd restart

echo "删除文件/tmp/a.sh"
rm -rf /tmp/a.sh

echo  "完成"



==================

#!/bin/sh

function proxy(){
	ip=$1
	pass='Ky3!KGwB\n'

	expect -c "
		spawn scp -r /usr/local/src/test/pm.sh  root@$ip:/tmp/a.sh
		expect {
			\"*assword\" {set timeout 300; send ""\"$pass\r\""";exp_continue;}
			\"yes/no\" {send \"yes\r\";}
			}
	expect eof"
}

function run(){
ip=$1
ssh root@$1 > /dev/null 2>&1 << eeooff
/tmp/a.sh
rm -rf /tmp/a.sh
exit
eeooff
}


for i in {161..174}
do
	a="10.142.88.$i"
    proxy $a
    #run $a
done

for i in {161..174}
do
	a="10.142.88.$i"
    run $a
done


echo "完成";