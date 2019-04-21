#!/bin/sh

#yum install expect

function ip(){
	ip=$1
	pass='Ky3!KGwB\n'
	expect -c "
	    spawn scp -r /usr/local/zabbix_proxy/share/zabbix/externalscripts/dev.ping.result  root@$ip:/usr/local/zabbix_proxy/share/zabbix/externalscripts/
	    expect {
	        \"*assword\" {set timeout 300; send ""\"$pass\r\"""; exp_continue;}
	        \"yes/no\" {send \"yes\r\";}
	    }
	expect eof"

	expect -c "
	    spawn scp -r /usr/bin/zabbix_trap_receiver.pl  root@$ip:/usr/bin/
	    expect {
	        \"*assword\" {set timeout 300; send ""\"$pass\r\"""; exp_continue;}
	        \"yes/no\" {send \"yes\r\";}
	    }
	expect eof"

	expect -c "
	    spawn scp -r /usr/bin/zabbix_trap_receiver.pl  root@$ip:/usr/bin/
	    expect {
	        \"*assword\" {set timeout 300; send ""\"$pass\r\"""; exp_continue;}
	        \"yes/no\" {send \"yes\r\";}
	    }
	expect eof"

}




for i in {73..82}
do
	a="10.142.88.$i"
    ip $a
done

echo "完成\n";
