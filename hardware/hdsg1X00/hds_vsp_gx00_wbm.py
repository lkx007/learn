#!/usr/bin/env python 
import getopt, sys, datetime, time, calendar, json,os,math
from Vsp import Vsp

def usage():
  print >> sys.stderr, "Usage: hw_6800v3_wbem.py --cluster <cluster1> [--cluster <cluster2>...] --user <username> --password <pwd>  --hostname <hostname> --proxy <proxy> --smis_port 5989 --fun <fun>[msg,performance] "

try:
  opts, args = getopt.gnu_getopt(sys.argv[1:], "-h", ["help", "cluster=", "user=", "password=", "hostname=","proxy=","fun=","smis_port="])
except getopt.GetoptError, err:
  print >> sys.stderr, str(err) # will print something like "option -a not recognized"
  usage()
  sys.exit(2)

port  = 10051
cluster = None
user = None
password = None
hostname = None
proxy = None
fun = None
smis_port = None
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
  elif o == "--smis_port":
    fun = a;
  elif o in ("-h", "--help"):
    usage()
    sys.exit()


Vsp(cluster,user,password,hostname,port,proxy,fun,smis_port)

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