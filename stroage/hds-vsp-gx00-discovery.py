#!/usr/bin/python

#coding=utf-8



import pywbem,getopt, sys,logging
from zbxsend import Metric, send_to_zabbix



def usage():
  print >> sys.stderr, "Usage: svc_perf_discovery_sender_zabbix.py [--debug] --clusters <svc1>[,<svc2>...] --user <username> --password <pwd> --hostname  <hostname> --discovery-types <type1>,[type2]"
  print >> sys.stderr, "Discovery types: 'volume-mdisk','volume','mdisk','pool'"


try:
  opts, args = getopt.gnu_getopt(sys.argv[1:], "-h", ["help", "clusters=", "user=", "password=","hostname=", "debug", "discovery-types="])
except getopt.GetoptError, err:
  print >> sys.stderr, str(err)
  usage()
  sys.exit(2)

debug = False
clusters = []
DISCOVERY_TYPES = []
user = None
password = None
hostname = None


for o, a in opts:
  if o == "--clusters" and not a.startswith('--'):
    clusters.extend( a.split(','))    
  elif o == "--user" and not a.startswith('--'):
    user = a
  elif o == "--hostname":
    hostname = a
  elif o == "--password" and not a.startswith('--'):
    password = a
  elif o == "--debug":
    debug = True
  elif o == "--discovery-types":
    DISCOVERY_TYPES.extend( a.split(','))
  elif o in ("-h", "--help"):
    usage()
    sys.exit()


if not clusters:
  print >> sys.stderr, '--clusters option must be set'
  usage()
  sys.exit(2)

if not DISCOVERY_TYPES:
  print >> sys.stderr, '--discovery-types option must be set'
  usage()
  sys.exit(2)

if not user or not password:
  print >> sys.stderr, '--user and --password options must be set'
  usage()
  sys.exit(2)   
  


if not hostname:
  print >> sys.stderr, '--hostname options must be set'
  usage()
  sys.exit(2)

def debug_print(message):
  if debug:
    print message 



def getRaidName(data,type):
  output = []
  if len(data):
    for  x in data:
      arr = x['ElementName'].split('.')
      name = '-'.join( arr) 
      output.append('{ "{#TYPE}":"%s","{#NAME}":"%s","{#ID}":"%s" }' % (type,name,x['DeviceID']) )
  return output

def getPoolName(data,type):
  output = []
  if len(data):
    for  x in data:
      arr = x['PoolID'].split('.')
      id = arr[-1]      
      output.append('{ "{#TYPE}":"%s","{#NAME}":"%s","{#ID}":"%s" }' % (type,x['ElementName'],id) )
  return output

def getLunName(data,type):
  output = []
  if len(data):
    for  x in data:
      arr = x['Caption'].split('.') 
      name = arr[-1]      
      output.append('{ "{#TYPE}":"%s","{#NAME}":"%s","{#ID}":"%s" }' % (type,name,x['DeviceID']) )
  return output


def getFcName(data,type):
  output = []
  if len(data):
    for  x in data:
      output.append('{ "{#TYPE}":"%s","{#NAME}":"%s","{#ID}":"%s" }' % (type,x['ElementName'],x['DeviceID']) )
  return output  


def getHostGroupName(data,type):
  output = []
  if len(data):
    for  x in data:
      output.append('{ "{#TYPE}":"%s","{#NAME}":"%s","{#ID}":"%s" }' % (type,x['ElementName'],x['DeviceID']) )
  return output   

def getHostName(data,type):
  output = []
  if len(data):
    for  x in data:
      arr = x['InstanceID'].split(' ')
      id = arr[-1]
      output.append('{ "{#TYPE}":"%s","{#NAME}":"%s","{#ID}":"%s" }' % (type,x['ElementName'],id) )
  return output  


def getDiskName(data,type):
  output = []
  if len(data):
    for  x in data:
      name = x['ElementName'] . replace('.','-')   
      output.append('{ "{#TYPE}":"%s","{#NAME}":"%s","{#ID}":"%s" }' % (type,name,x['DeviceID']) )
  return output 


for cluster in clusters:
  debug_print('Connecting to: %s' % cluster)
  conn = pywbem.WBEMConnection('https://'+cluster, (user, password), 'root/hitachi/smis',None,None,None,True)
  conn.debug = True

  for discovery in DISCOVERY_TYPES:
    output = []

    
    if discovery == 'raid':
      data = conn.EnumerateInstances('HITACHI_ArrayGroup')
      data = getRaidName(data,'raid')
      output = output + data

    if discovery == 'pool':
      data = conn.EnumerateInstances('HITACHI_ThinProvisioningPool')
      data = getPoolName(data,'pool')
      output = output + data

    if discovery == 'lun':
      data = conn.EnumerateInstances('HITACHI_StorageVolume')
      data = getLunName(data,'lun')
      output = output + data

    if discovery == 'disk':
      data = conn.EnumerateInstances('HITACHI_DiskDrive')
      data = getDiskName(data,'disk')
      output = output + data

    if discovery == 'fcport':
      data = conn.EnumerateInstances('HITACHI_FCPort')
      data = getFcName(data,'fcport')
      output = output + data 

    if discovery == 'host_group':
      data = conn.EnumerateInstances('HITACHI_SCSIProtocolController')
      data = getHostGroupName(data,'host_group')
      output = output + data 


    if discovery == 'host':
      data = conn.EnumerateInstances('HITACHI_AuthorizedPrivilege')
      data = getHostName(data,'host')
      output = output + data 




    json = []
    json.append('{"data":[')

    for i, v in enumerate( output ):
      if i < len(output)-1:
        json.append(v+',')
      else:
        json.append(v)
    json.append(']}')

    json_string = ''.join(json)
    print(json_string) 

    trapper_key = 'svc.discovery.%s' % discovery
    debug_print('Sending to host=%s, key=%s' % (hostname, trapper_key))

    #send json to LLD trapper item with zbxsend module
    if debug:
      logging.basicConfig(level=logging.INFO)
    else:
      logging.basicConfig(level=logging.WARNING)     
    send_to_zabbix([Metric(hostname, trapper_key, json_string)], 'localhost', 10051)