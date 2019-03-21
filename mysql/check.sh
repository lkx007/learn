#!/bin/sh

USER=''
PASSWORD=''
IP=''
while [ $# -ge 1 ] ; do
	case "$1" in
		-h) IP="$2";		shift 2 ;;
		-u) USER="$2";		shift 2 ;;
		-p) PASSWORD="$2";	shift 2 ;;
		*) echo "参数有误";shift 2 ;;
	esac
done

/usr/local/mysql/bin/mysql -h"$IP"   -u"$USER" -p"$PASSWORD"    -e "show databases"
#mysql_check[-h,{$IP}, -u,{$USER}, -p,{$PASSWORD}]