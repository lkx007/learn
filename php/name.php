<?php

$url = '127.0.0.1';
$user = 'zabbix';
$password = 'zabbix';
$dbName ='zabbix';


$arr = $_SERVER['argv'];

if(!isset($arr[1])) exit();
$hostName = $arr[1];

//$hostName = 'test_host';

$con = mysql_connect($url,$user,$password);
if (!$con)
  {
  die('Could not connect: ' . mysql_error());
  }

mysql_select_db($dbName, $con);
$query = 'SELECT i.ip,h.ipmi_username,h.ipmi_password from `hosts` as h LEFT JOIN interface as i on i.hostid = h.hostid where h.name like "%'.$hostName.'%"  and  i.port= 161';
$result = mysql_query($query,$con);

if(!$result){
        mysql_close($con);
        exit();
}
while($row = mysql_fetch_array($result, MYSQL_ASSOC)){
        restart($row);
}
mysql_close($con);

function restart($row){
	$connection=ssh2_connect($row['ip'],22);
	ssh2_auth_password($connection,$row['ipmi_username'],$row['ipmi_password']);
	$cmd="reset /map1";
	ssh2_exec($connection,$cmd);
}