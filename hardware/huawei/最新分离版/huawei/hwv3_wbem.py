#!/usr/bin/env python3
import getopt, sys, datetime, time, calendar, json,os,math
from Hwv3 import Hwv3


#/usr/bin/python3 /usr/local/zabbix/huawei/hwv3_wbem.py  --cluster "10.142.88.7" --user "smis_admin" --password "Admin@12" --hostname "NM-XX-A5403-F05-01U_46U-HW-6800V3-B01"  --proxy "127.0.0.1"  --fun "fcportMsg"


def usage():
  print ( sys.stderr, "Usage: hwv3_wbem.py --cluster <cluster1> [--cluster <cluster2>...] --user <username> --password <pwd>  --hostname <hostname> --proxy <proxy>  --fun <fun>[msg,performance]" )

try:
  opts, args = getopt.gnu_getopt(sys.argv[1:], "-h", ["help", "cluster=", "user=", "password=", "hostname=","proxy=","fun="])
except getopt.GetoptError as err:
  print ( sys.stderr, str(err)) # will print something like "option -a not recognized"
  usage()
  sys.exit(2)

port  = 10051
cluster = None
user = None
password = None
hostname = None
proxy = '127.0.0.1'
fun = None
for o, a in opts:
  if o == "--cluster": 
    cluster = a; 
  elif o == "--user":
    user = a;
  elif o == "--password":
    password = a;
  elif o == "--hostname":
    hostname = a;
  elif o == "--proxy":
    proxy = a;
  elif o == "--fun":
    fun = a;
  elif o in ("-h", "--help"):
    usage()
    sys.exit()


Hwv3(cluster,user,password,hostname,port,proxy,fun)

"""
#ip = '10.242.48.81'
cluster = '192.168.8.22'
user = 'maintenance'
password = 'raid-maintenance'
port = '10051'
#host = 'NM-XX-A5403-B14-03U_18U-HIT-HDS_VSP_G-B01'
hostname = 'test_hds'
proxy = '10.142.88.7''msg'
#fun = 
fun = 'performance'

/usr/bin/python /usr/local/zabbix/hdsgx00/hds_vsp_gx00_wbm.py  --cluster '192.168.8.22' --user 'maintenance' --password 'raid-maintenance' --hostname 'test_hds'  --proxy '10.142.88.7' --fun 'msg'

Vsp(cluster,user,password,hostname,port,proxy,fun)
"""
