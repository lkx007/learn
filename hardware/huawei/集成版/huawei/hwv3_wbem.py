#!/usr/bin/env python 
import getopt, sys, datetime, time, calendar, json,os,math
from Hwv3 import Hwv3


def usage():
	print >> sys.stderr, "Usage: hwv3_wbem.py --cluster <cluster1> [--cluster <cluster2>...] --user <username> --password <pwd>  --hostname <hostname> --proxy <proxy> --fun <fun>[msg,performance]"

try:
	opts, args = getopt.gnu_getopt(sys.argv[1:], "-h", ["help", "cluster=", "user=", "password=", "hostname=","proxy=","fun="  ])
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

