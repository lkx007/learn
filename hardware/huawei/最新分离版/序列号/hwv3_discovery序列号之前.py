#!/usr/bin/python3

#coding=utf-8

import pywbem,getopt,sys,os,logging
#from zbxsend import Metric,send_to_zabbix   #此插件不支持3.5，所以不要他了



def usage():
  print (sys.stderr, "Usage: hwv3_discovery.py  --clusters <svc1>[,<svc2>...] --user <username> --password <pwd> --hostname  <hostname> --serial <serial> --discovery-types <type1>,[type2]")
#python ./hwv3_discovery.py  --clusters '10.142.88.7' --user 'smis_admin' --password 'Admin@12' --hostname  'test' --discovery-types 'pool'

try:
  opts, args = getopt.gnu_getopt(sys.argv[1:], "-h", ["help", "clusters=", "user=", "password=","hostname=", "debug", "serial=","discovery-types="])
except(getopt.GetoptError, err):
  print(sys.stderr,str(err))
  usage()
  sys.exit(2)

debug = False
clusters = []
DISCOVERY_TYPES = []
user = None
password = None
hostname = None
serial = None

send = '/usr/local/zabbix_proxy/bin/zabbix_sender'

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
  elif o == "--serial":
    serial = a
  elif o == "--discovery-types":
    DISCOVERY_TYPES.extend( a.split(','))
  elif o in ("-h", "--help"):
    usage()
    sys.exit()


if not clusters:
  print(sys.stderr,'--clusters option must be set')
  usage()
  sys.exit(2)

if not DISCOVERY_TYPES:
  print(sys.stderr, '--discovery-types option must be set')
  usage()
  sys.exit(2)

if not user or not password or  not serial:
  print(sys.stderr, '--user , --password , --serial options must be set')
  usage()
  sys.exit(2)


if not hostname:
  print(sys.stderr, '--hostname options must be set')
  usage()
  sys.exit(2)

def debug_print(message):
  if debug:
    print(message)


for cluster in clusters:
  debug_print('Connecting to: %s' % cluster)
  conn = pywbem.WBEMConnection('https://'+cluster, (user, password), 'root/huawei',None,None,None,True)
  conn.debug = True

  for discovery in DISCOVERY_TYPES:
    output = []

    if discovery == 'fcport':
      data = conn.EnumerateInstances('HuaSy_FrontEndFCPort')
      for  x in data:
        if x['DeviceID'].startswith(serial):
          output.append('{ "{#TYPE}":"%s","{#NAME}":"%s","{#ID}":"%s" }' % (discovery,x['ElementName'],x['DeviceID']) )

    if discovery == 'pool':
      data = conn.EnumerateInstances('HuaSy_ConcreteStoragePool')
      for  x in data:
        if x['InstanceID'].startswith(serial):
          output.append('{ "{#TYPE}":"%s","{#NAME}":"%s","{#ID}":"%s" }' % (discovery,x['ElementName'],x['InstanceID']) )

    if discovery == 'enclosure':
      data = conn.EnumerateInstances('HuaSy_EnclosureChassis')
      for  x in data:
        if x['Tag'].startswith(serial):
          output.append('{ "{#TYPE}":"%s","{#NAME}":"%s","{#ID}":"%s" }' % (discovery,x['ElementName'],x['Tag']) )

    if discovery == 'raid':
      data = conn.EnumerateInstances('HuaSy_DiskStoragePool')
      for  x in data:
        if x['InstanceID'].startswith(serial):
          output.append('{ "{#TYPE}":"%s","{#NAME}":"%s","{#ID}":"%s" }' % (discovery,x['ElementName'],x['InstanceID']) )

    if discovery == 'disk':
      data = conn.EnumerateInstances('HuaSy_DiskDrive')
      for  x in data:
        if x['DeviceID'].startswith(serial):
          output.append('{ "{#TYPE}":"%s","{#NAME}":"%s","{#ID}":"%s" }' % (discovery,x['ElementName'],x['DeviceID']) )

    if discovery == 'host':
      data = conn.EnumerateInstances('HuaSy_StorageHardwareID')
      names = []
      ids = {}
      for  x in data:
        if x['InstanceID'].startswith(serial):
          name = x['ElementName']
          id = x['InstanceID']
          if name not in names and name:  # 
            names.append(name)
            ids[id] = name
      for x in ids:
        output.append('{ "{#TYPE}":"%s","{#NAME}":"%s","{#ID}":"%s" }' % (discovery,ids[x],x) )


    if discovery == 'host_group':
      data = conn.EnumerateInstances('HuaSy_InitiatorMaskingGroup')
      for  x in data:
        if x['InstanceID'].startswith(serial):
          output.append('{ "{#TYPE}":"%s","{#NAME}":"%s","{#ID}":"%s" }' % (discovery,x['ElementName'],x['InstanceID']) )

    if discovery == 'lun':
      data = conn.EnumerateInstances('HuaSy_StorageVolume')
      for  x in data:
        if x['DeviceID'].startswith(serial):
          output.append('{ "{#TYPE}":"%s","{#NAME}":"%s","{#ID}":"%s" }' % (discovery,x['ElementName'],x['DeviceID']) )


    if discovery == 'lun_group':
      data = conn.EnumerateInstances('HuaSy_DeviceMaskingGroup')
      for  x in data:
        if x['InstanceID'].startswith(serial):
          output.append('{ "{#TYPE}":"%s","{#NAME}":"%s","{#ID}":"%s" }' % (discovery,x['ElementName'],x['InstanceID']) )



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


    #send json to LLD trapper item with zbxsend module
    if debug:
      logging.basicConfig(level=logging.INFO)
    else:
      logging.basicConfig(level=logging.WARNING)	   
    #send_to_zabbix([Metric(hostname, trapper_key, json_string)], 'localhost', 10051)
    command = "{zabbix_sender} -z 127.0.0.1 -s {host} -k {key} -o '{value}'" . format(zabbix_sender=send,host=hostname,key=discovery,value=json_string)
    os.popen(command)
