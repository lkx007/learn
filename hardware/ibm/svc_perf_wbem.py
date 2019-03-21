#!/usr/bin/python
# -*- coding: utf-8 -*- # coding: utf-8


import pywbem
import getopt, sys, datetime, time, calendar, json,os,math


def usage():
  print >> sys.stderr, "Usage: svc_perf_wbem.py --cluster <cluster1> [--cluster <cluster2>...] --user <username> --password <pwd>  --hostname <hostname> --proxy <proxy> --fun <fun>[msg,performance]"

##############################################################

RAW_COUNTERS = ['timestamp', 'KBytesRead', 'KBytesWritten', 'KBytesTransferred', 'ReadIOs', 'WriteIOs', 'TotalIOs', 'IOTimeCounter', 'ReadIOTimeCounter', 'WriteIOTimeCounter','ReadHitIOs','WriteHitIOs']
COUNTERS = ['ReadRateKB', 'WriteRateKB', 'TotalRateKB', 'ReadIORate', 'WriteIORate', 'TotalIORate', 'ReadIOTime', 'WriteIOTime', 'ReadIOPct']

FC_COUNTERS=['BytesReceived','BytesTransmitted','CRCErrors','DataTransmissionDelayCount','DataTransmissionDelayTime']


##############################################################
def enumNames(cimClass):
  ''' Enum storage objects and return dict{id:name} '''
  names = {}
  for obj in conn.ExecQuery( 'WQL', 'SELECT DeviceID, ElementName FROM %s' % (cimClass) ):
    deviceID = obj.properties['DeviceID'].value
    if deviceID:
      names[str(deviceID)] = obj.properties['ElementName'].value
  return names

##############################################################
def calculateStats(old_counters, new_counters,lun=''):
  ''' Calculate perf statistic values from raw counters '''
  stats = {}
  ''' check that we have timestamp in cached sample '''
  if 'timestamp' in old_counters:
    timespan = new_counters['timestamp'] - old_counters['timestamp']

    if timespan:
      deltaReadKB  = float(new_counters['KBytesRead'] - old_counters['KBytesRead'])
      deltaWriteKB = float(new_counters['KBytesWritten'] - old_counters['KBytesWritten'])
      deltaTotalKB = float(new_counters['KBytesTransferred'] - old_counters['KBytesTransferred'])
      deltaReadIO  = float(new_counters['ReadIOs'] - old_counters['ReadIOs'])
      deltaWriteIO = float(new_counters['WriteIOs'] - old_counters['WriteIOs'])
      deltaTotalIO = float(new_counters['TotalIOs'] - old_counters['TotalIOs'])
      deltaReadIOTimeCounter = float(new_counters['ReadIOTimeCounter'] - old_counters['ReadIOTimeCounter'])
      deltaWriteIOTimeCounter = float(new_counters['WriteIOTimeCounter'] - old_counters['WriteIOTimeCounter'])

      stats['ReadRateKB']  = math.ceil ( deltaReadKB  / timespan )
      stats['WriteRateKB'] = math.ceil ( deltaWriteKB / timespan )
      stats['TotalRateKB'] = math.ceil ( deltaTotalKB / timespan )
      stats['ReadIORate']  = math.ceil ( deltaReadIO  / timespan )
      stats['WriteIORate'] = math.ceil ( deltaWriteIO / timespan )
      stats['TotalIORate'] = math.ceil ( deltaTotalIO / timespan )

      #lun 加多两个指标 缓存名中率
      if lun:
        deltaReadHit  = float(new_counters['ReadHitIOs'] - old_counters['ReadHitIOs'])
        deltaWriteHit = float(new_counters['WriteHitIOs'] - old_counters['WriteHitIOs'])
        readHitIOs = math.ceil ( deltaReadHit / timespan )
        writeHitIOs = math.ceil ( deltaWriteHit / timespan )
        if stats['ReadIORate'] > 0:
          stats['ReadHitIOs'] =  readHitIOs /  stats['ReadIORate'] * 100
        else:
          stats['ReadHitIOs'] = 0 

        if stats['WriteIORate'] > 0:
          stats['WriteHitIOs'] =  writeHitIOs /  stats['WriteIORate'] * 100
        else:
          stats['WriteHitIOs'] = 0



      if (deltaReadIO > 0) and (deltaReadIOTimeCounter > 0):
        stats['ReadIOTime'] = math.ceil ( deltaReadIOTimeCounter / deltaReadIO )

      if (deltaWriteIO > 0) and (deltaWriteIOTimeCounter > 0):
        stats['WriteIOTime'] = math.ceil ( deltaWriteIOTimeCounter / deltaWriteIO )

      #不知什么意思，先不要
      #if (deltaTotalIO > 0) and (deltaReadIO > 0):
      #  stats['ReadIOPct'] = deltaReadIO / deltaTotalIO * 100

    else:
      print >> sys.stderr, 'timespan between samples is 0, skipping'

  else:
      print >> sys.stderr, 'no timestamp in previous sample, skipping'
  return stats

def fcCalculate(old_counters, new_counters):
  stats = {}
  ''' check that we have timestamp in cached sample '''
  if 'timestamp' in old_counters:
    timespan = new_counters['timestamp'] - old_counters['timestamp']
    if timespan:
      BytesReceived  = float(new_counters['BytesReceived'] - old_counters['BytesReceived'])
      BytesTransmitted = float(new_counters['BytesTransmitted'] - old_counters['BytesTransmitted'])
      CRCErrors = float(new_counters['CRCErrors'] - old_counters['CRCErrors'])
      DataTransmissionDelayCount  = float(new_counters['DataTransmissionDelayCount'] - old_counters['DataTransmissionDelayCount'])
      DataTransmissionDelayTime = float(new_counters['DataTransmissionDelayTime'] - old_counters['DataTransmissionDelayTime'])
      
      stats['BytesReceived']  = math.ceil ( BytesReceived  / timespan ) #接收字节
      stats['BytesTransmitted'] = math.ceil ( BytesTransmitted / timespan ) #发送字节
      stats['CRCErrors'] = math.ceil ( CRCErrors / timespan ) #冗余校验错误
      stats['DataTransmissionDelayCount']  = math.ceil ( DataTransmissionDelayCount  / timespan ) #数据传输延迟计数
      stats['DataTransmissionDelayTime'] = math.ceil ( DataTransmissionDelayTime / timespan ) #数据传输延迟时间

    else:
      print >> sys.stderr, 'timespan between samples is 0, skipping'

  else:
      print >> sys.stderr, 'no timestamp in previous sample, skipping'
  return stats



##############################################################
def collectStats(connection, elementType, elementClass, statisticsClass):
  ##enumerate element names
  names = enumNames(elementClass)
  ##get volume stats
  stats = conn.EnumerateInstances(statisticsClass)
  for stat in stats:
    ''' parse property InstanceID = "StorageVolumeStats 46" to get element ID '''
    elementID = stat.properties['InstanceID'].value.split()[1]
    elementName = names[elementID]
    ps = stat.properties
    timestamp = calendar.timegm(ps['StatisticTime'].value.datetime.timetuple())
    ''' get previous samples '''
    cached_raw_counters = {}
    cache_key = '%s.%s.%s' % (cluster, elementType, elementName)
    if (cache_key in cache):
      cached_raw_counters = cache[cache_key]
    if cached_raw_counters is None:
      cached_raw_counters = {}
    ''' don't proceed samples with same timestamp to prevent speed calculation errors '''
    if ('timestamp' in cached_raw_counters) and (timestamp == cached_raw_counters['timestamp']):
      print >> sys.stderr, 'same sample: %s = %s, skipping' % (cache_key, ps['StatisticTime'].value.datetime)
      continue
    ''' get current samples '''
    new_raw_counters = {}
    new_raw_counters['timestamp'] = timestamp
    for k in RAW_COUNTERS:
      if k in ps and ps[k].value is not None:
        new_raw_counters[k] = ps[k].value
    ''' save current samples to cache '''
    cache[cache_key] = new_raw_counters
    ''' calculate statistics for Zabbix '''
    stat_values = calculateStats(cached_raw_counters, new_raw_counters)

    for s in elementCounters:
      if s in stat_values:
        print '%s svc.%s[%s,%s] %d %s' % (cluster, s, elementType, elementID, timestamp, stat_values[s])

##############################################################

''' main script body '''





def comFun(ps,cache_key,COUNTERS):
  timestamp = calendar.timegm(ps['StatisticTime'].value.datetime.timetuple())
  cached_raw_counters = {}
  if (cache_key in cache):
    cached_raw_counters = cache[cache_key]
  if cached_raw_counters is None:
    cached_raw_counters = {}
  ''' don't proceed samples with same timestamp to prevent speed calculation errors '''
  if ('timestamp' in cached_raw_counters) and (timestamp == cached_raw_counters['timestamp']):
    print >> sys.stderr, 'same sample: %s = %s, skipping' % (cache_key, ps['StatisticTime'].value.datetime)
    return []

  else:
    new_raw_counters = {}
    new_raw_counters['timestamp'] = timestamp
    for k in COUNTERS:
      if k in ps and ps[k].value is not None:
        new_raw_counters[k] = ps[k].value
    ''' save current samples to cache '''
    cache[cache_key] = new_raw_counters
    return [cached_raw_counters, new_raw_counters]




### 硬盘 性能 数据 ####
def diskPerformance(connection, elementType, elementClass, statisticsClass):
  print "采集硬盘 性能 数据"
  #names = enumNames(elementClass)
  stats = conn.EnumerateInstances(statisticsClass)
  for stat in stats:
    elementID = stat.properties['InstanceID'].value.split()[1]
    #elementName = names[elementID]
    ps = stat.properties
    cache_key = '%s.%s.%s' % (cluster, elementType, elementID)
    raws = comFun(ps,cache_key,RAW_COUNTERS)

    if len(raws):
      stat_values = calculateStats(raws[0], raws[1])
      if stat_values:
        id = 'disk' + elementID
        componseContent('disk.read.rate[{id}]'.format(id=id), stat_values['ReadRateKB'] ) 
        componseContent('disk.write.rate[{id}]'.format(id=id), stat_values['WriteRateKB'] ) 
        componseContent('disk.rw.rate[{id}]'.format(id=id), stat_values['TotalRateKB'] ) 
        componseContent('disk.read.io.rate[{id}]'.format(id=id), stat_values['ReadIORate'] ) 
        componseContent('disk.write.io.rate[{id}]'.format(id=id), stat_values['WriteIORate'] ) 
        componseContent('disk.rw.io.rate[{id}]'.format(id=id), stat_values['TotalIORate'] )
        if  stat_values.has_key('ReadIOTime'):
          componseContent('disk.read.io.time[{id}]'.format(id=id), stat_values['ReadIOTime'] ) 
        if stat_values.has_key('WriteIOTime'):
          componseContent('disk.write.io.time[{id}]'.format(id=id), stat_values['WriteIOTime'] ) 


 ### 阵列 性能 数据 ####
def raidPerformance(connection, elementType, elementClass, statisticsClass):
  print "采集阵列 性能 数据"
  names = enumNames(elementClass)
  stats = conn.EnumerateInstances(statisticsClass)
  for stat in stats:
    elementID = stat.properties['InstanceID'].value.split()[1]
    elementName = names[elementID]
    ps = stat.properties
    cache_key = '%s.%s.%s' % (cluster, elementType, elementName)
    raws = comFun(ps,cache_key,RAW_COUNTERS)
    if len(raws):
      stat_values = calculateStats(raws[0], raws[1])
      if stat_values:
        id = elementName
        componseContent('raid.read.rate[{id}]'.format(id=id), stat_values['ReadRateKB'] ) 
        componseContent('raid.write.rate[{id}]'.format(id=id), stat_values['WriteRateKB'] ) 
        componseContent('raid.rw.rate[{id}]'.format(id=id), stat_values['TotalRateKB'] ) 
        componseContent('raid.read.io.rate[{id}]'.format(id=id), stat_values['ReadIORate'] ) 
        componseContent('raid.write.io.rate[{id}]'.format(id=id), stat_values['WriteIORate'] ) 
        componseContent('raid.rw.io.rate[{id}]'.format(id=id), stat_values['TotalIORate'] )
        if  stat_values.has_key('ReadIOTime'):
          componseContent('raid.read.io.time[{id}]'.format(id=id), stat_values['ReadIOTime'] ) 
        if stat_values.has_key('WriteIOTime'):
          componseContent('raid.write.io.time[{id}]'.format(id=id), stat_values['WriteIOTime'] ) 
      
 
  ### 卷 性能 数据 ####
def lunPerformance(connection, elementType, elementClass, statisticsClass):
  print "采集 卷 性能 数据"	
  names = enumNames(elementClass)
  stats = conn.EnumerateInstances(statisticsClass)
  for stat in stats:
    elementID = stat.properties['InstanceID'].value.split()[1]
    elementName = names[elementID]
    ps = stat.properties
    cache_key = '%s.%s.%s' % (cluster, elementType, elementName)
    raws = comFun(ps,cache_key,RAW_COUNTERS)
    if len(raws):
      stat_values = calculateStats(raws[0], raws[1],True)
      if stat_values:
        id = elementName
        componseContent('lun.read.rate[{id}]'.format(id=id), stat_values['ReadRateKB'] ) 
        componseContent('lun.write.rate[{id}]'.format(id=id), stat_values['WriteRateKB'] ) 
        componseContent('lun.rw.rate[{id}]'.format(id=id), stat_values['TotalRateKB'] ) 
        componseContent('lun.read.io.rate[{id}]'.format(id=id), stat_values['ReadIORate'] ) 
        componseContent('lun.write.io.rate[{id}]'.format(id=id), stat_values['WriteIORate'] ) 
        componseContent('lun.rw.io.rate[{id}]'.format(id=id), stat_values['TotalIORate'] )

        componseContent('lun.read.io.hit[{id}]'.format(id=id), stat_values['ReadHitIOs'] ) 
        componseContent('lun.write.io.hit[{id}]'.format(id=id), stat_values['WriteHitIOs'] )

        if  stat_values.has_key('ReadIOTime'):
          componseContent('lun.read.io.time[{id}]'.format(id=id), stat_values['ReadIOTime'] ) 
        if stat_values.has_key('WriteIOTime'):
          componseContent('lun.write.io.time[{id}]'.format(id=id), stat_values['WriteIOTime'] )      


#FC
def fcPerformance(connection, elementType, elementClass, statisticsClass):
  print "采集 fc 性能 数据"		
  names = enumNames(elementClass)
  stats = conn.EnumerateInstances(statisticsClass)
  for stat in stats:
    elementID = stat.properties['InstanceID'].value.split()[1]
    elementName = names[elementID]
    ps = stat.properties
    cache_key = '%s.%s.%s' % (cluster, elementType, elementName)
    raws = comFun(ps,cache_key,FC_COUNTERS)
    if len(raws):
      stat_values = fcCalculate(raws[0], raws[1]) 
      if stat_values:
        id = 'wwpn_' + elementName
        componseContent('ifHCInOctetsPersecond[{id}]'.format(id=id), stat_values['BytesReceived'] ) #接收字节
        componseContent('ifHCOutOctetsPersecond[{id}]'.format(id=id), stat_values['BytesTransmitted'] )#发送字节
        componseContent('fc.crc.errors[{id}]'.format(id=id), stat_values['CRCErrors'] )#冗余校验错误
        componseContent('fc.delay.count[{id}]'.format(id=id), stat_values['DataTransmissionDelayCount'] )#数据传输延迟计数
        componseContent('fc.delay.time[{id}]'.format(id=id), stat_values['DataTransmissionDelayTime'] )#数据传输延迟时间


### disk 静态信息 其它没有翻译的不清楚的没有加进来 
def  diskMsg(conn):
  print "采集 disk 静态信息"	
  res = conn.ExecQuery('WQL', 'select * from IBMTSSVC_DiskDrive')
  for x in res:
    id = 'disk' + x.properties['DeviceID'].value
    componseContent('disk.mfc[{id}]'.format(id=id), x.properties['VendorID'].value ) #厂商 
    componseContent('disk.size.total[{id}]'.format(id=id), x.properties['Capacity'].value ) #硬盘大小
    componseContent('disk.blocks.size[{id}]'.format(id=id), x.properties['BlockSize'].value ) #硬盘块大小 
    componseContent('disk.model[{id}]'.format(id=id), x.properties['ProductID'].value ) #产品型号 
    componseContent('disk.fru[{id}]'.format(id=id), x.properties['FRUPartNum'].value ) #硬盘部件号 
    componseContent('disk.speed[{id}]'.format(id=id), x.properties['RPM'].value ) #硬盘转速 
    componseContent('disk.fru.id[{id}]'.format(id=id), x.properties['FRUIdentity'].value ) #部件标识 
    componseContent('disk.firmware.level[{id}]'.format(id=id), x.properties['FirmwareLevel'].value ) #固件级别  
    componseContent('disk.raid.name[{id}]'.format(id=id), x.properties['MdiskName'].value ) #硬盘所在RAID名称 
    componseContent('enclosure.id[{id}]'.format(id=id), x.properties['EnclosureID'].value ) #机柜id 
    componseContent('slot.id[{id}]'.format(id=id), x.properties['SlotID'].value ) #插槽标识 
    status  = 1
    if x.properties['ErrorSequenceNumber'].value :
      status = 0
    componseContent('disk.status[{id}]'.format(id=id), x.properties['EnabledState'].value ) #硬盘状态 
    componseContent('disk.tech.type[{id}]'.format(id=id), x.properties['TechType'].value ) #技术类型  


#存储池的静态信息
def poolMsg(conn):
  print "采集 存储池 静态信息"
  res = conn.ExecQuery('WQL', 'select * from IBMTSSVC_ConcreteStoragePool')
  for x in res:
    id = x.properties['ElementName'].value 
    componseContent('pool.status[{id}]'.format(id=id), x.properties['NativeStatus'].value ) # 状态
    componseContent('pool.name[{id}]'.format(id=id), x.properties['ElementName'].value ) #名称
    componseContent('pool.capacity.size.free[{id}]'.format(id=id), x.properties['RemainingManagedSpace'].value ) # 池剩余容量大小
    componseContent('pool.capacity.size.used[{id}]'.format(id=id), x.properties['UsedCapacity'].value ) #池已用容量大小
    componseContent('pool.lun.number[{id}]'.format(id=id), x.properties['NumberOfStorageVolumes'].value ) #池LUN数量
    componseContent('pool.lun.size.total[{id}]'.format(id=id), x.properties['VirtualCapacity'].value ) #池LUN容量大小
    componseContent('pool.raid.number[{id}]'.format(id=id), x.properties['NumberOfBackendVolumes'].value ) #池RAID数量
    componseContent('pool.capacity.size.total[{id}]'.format(id=id), x.properties['TotalManagedSpace'].value ) #池总容量大小
    componseContent('pool.ext.blocks.size[{id}]'.format(id=id), x.properties['ExtentSize'].value ) #池扩展数据块大小

#阵列的静态信息
def mdiskMsg(conn):
  print "采集 阵列的静态信息"
  res = conn.ExecQuery('WQL', 'select * from IBMTSSVC_BackendVolume')
  for x in res:
    id = x.properties['ElementName'].value  
    componseContent('raid.pool.name[{id}]'.format(id=id), x.properties['Poolname'].value ) #RAID所属池名称
    componseContent('raid.size.total[{id}]'.format(id=id), x.properties['Capacity'].value ) #RAID容量大小
    componseContent('raid.status[{id}]'.format(id=id), x.properties['NativeStatus'].value ) # RAID状态
    componseContent('raid.name[{id}]'.format(id=id), x.properties['ElementName'].value ) # RAID名称


#lun 静态信息
def lunMsg(conn):
  print "采集 卷的静态信息"
  res = conn.ExecQuery('WQL', 'select * from IBMTSSVC_StorageVolume')
  for x in res:
    id = x.properties['ElementName'].value  
    componseContent('lun.name[{id}]'.format(id=id), x.properties['VolumeName'].value ) #名称
    componseContent('lun.size.total[{id}]'.format(id=id), x.properties['NumberOfBlocks'].value ) #LUN容量大小
    componseContent('lun.size.total.real[{id}]'.format(id=id), x.properties['UncompressedUsedCapacity'].value ) #LUN实际容量大小
    componseContent('lun.pool.name[{id}]'.format(id=id), x.properties['Poolname'].value ) #LUN所在池名称
    componseContent('lun.status[{id}]'.format(id=id), x.properties['NativeStatus'].value ) #LUN状态
    componseContent('lun.id[{id}]'.format(id=id), x.properties['UniqueID'].value ) #LUN标识
    componseContent('lun.size.used[{id}]'.format(id=id), x.properties['ConsumableBlocks'].value ) #LUN已使用容量大小
    componseContent('lun.host.mapped[{id}]'.format(id=id), x.properties['IsFormatted'].value ) #LUN是否已映射主机



#FC 静态信息
def fcMsg(conn):
  print "采集 fc的静态信息"
  res = conn.ExecQuery('WQL', 'select * from IBMTSSVC_FCPort')
  for x in res:
    id = 'wwpn_' + x.properties['PermanentAddress'].value  
    #componseContent('fcfmac[{id}]'.format(id=id), x.properties['FcfMAC'].value ) #FcfMAC
    #componseContent('vlan.id[{id}]'.format(id=id), x.properties['VlanID'].value ) #VlanID
    componseContent('node.name[{id}]'.format(id=id), x.properties['NodeName'].value ) #节点名称
    status = 0 
    if x.properties['StatusDescriptions'].value == 'Port active':
      status = 1
    componseContent('fcif.status[{id}]'.format(id=id), status ) #Status
    componseContent('ifType[{id}]'.format(id=id), x.properties['PortType'].value ) #类型
    componseContent('ifSpeed[{id}]'.format(id=id), x.properties['Speed'].value ) #速度
    componseContent('if.max.speed[{id}]'.format(id=id), x.properties['MaxSpeed'].value ) #最大速度  
    componseContent('if.fc.wwpn[{id}]'.format(id=id), x.properties['PermanentAddress'].value ) #FC端口WWPN  
    componseContent('fc.io.port.id[{id}]'.format(id=id), x.properties['FCIOPortID'].value ) #FCIOPortID    
    componseContent('fc.switch.wwpn[{id}]'.format(id=id), x.properties['SwitchWWPN'].value )#switch wwpn
##系统总概
def sysMsg(conn):
  print "采集 统总概的静态信息"
  res = conn.ExecQuery('WQL', 'select * from IBMTSSVC_Cluster')
  for x in res:
    componseContent('dev.cluster.id', x.properties['ID'].value )
    componseContent('product.version', x.properties['CodeLevel'].value )
    componseContent('product.name', x.properties['ElementName'].value )
    componseContent('dev.timezone', x.properties['TimeZone'].value )
    componseContent('dev.ip', x.properties['ConsoleIP'].value )
    componseContent('dev.storage.size.total', x.properties['BackendStorageCapacity'].value ) #总物理容量
    componseContent('dev.storage.size.free', x.properties['TotalUsedCapacity'].value ) #已使用存储容量
    componseContent('dev.storage.lun.size.total', x.properties['TotalVdiskCapacity'].value )#已配置的总容量
    componseContent('dev.storage.lun.size.write', x.properties['TotalVdiskCopyCapacity'].value )#已写入的总容量
    componseContent('dev.storage.size.used', x.properties['BackendStorageCapacity'].value - x.properties['TotalUsedCapacity'].value ) #可用容量


##主机信息采集
def hostMsg(conn):
  print "主机信息采集"
  res = conn.ExecQuery('WQL', 'select * from IBMTSSVC_ProtocolController')
  #主机字典
  hostDict = {}
  for x in res:
    hostDict.update({x.properties['HostClusterId'].value.encode('utf-8') : x.properties['ElementName'].value.encode('utf-8') })
    id =  x.properties['ElementName'].value
    componseContent('storagehost.name[{id}]'.format(id=id), x.properties['ElementName'].value ) #
    componseContent('storagehost.cluster.name[{id}]'.format(id=id), x.properties['HostClusterName'].value ) #

  #主机与端口的关系
  res1 = conn.ExecQuery('WQL', 'select * from IBMTSSVC_StorageHardwareID')
  portCount = {}
  wwpnArr = {}
  for x in res1:
    try:
      key  = x.properties['HostID'].value.encode('utf-8')
      k = None
      if hostDict.has_key(key):
        k = hostDict[key] # 主机名称 

      #主机端口数量
      if portCount.has_key(k):
        n = portCount[k] + 1
      else:
        n = 1
      portCount.update({k:n})
      #主机WWPN列表
      id = x.properties['StorageID'].value.encode('utf-8')
      if wwpnArr.has_key(k):
        n = wwpnArr[k]  
        n.append(id)
      else:
        n = [id]
      wwpnArr.update({k:n})
    except Exception as e:
      pass



  #端口数量发送给主机
  for x in portCount:
    componseContent('storagehost.fcport.number[{id}]'.format(id=x), portCount[x] ) #
  #端口wwpn 发送给主机
  for x in wwpnArr:
    componseContent('storagehost.ports.wwpns[{id}]'.format(id=x), json.dumps(wwpnArr[x]) ) #

  #主机跟LUN的关系
  print "主机与lun关系信息采集"
  lunHost = {} # lun集合与主机关系
  res = conn.ExecQuery('WQL', 'select * from IBMTSSVC_HardwareidStorageVolumeView')
  for x in res:
    #发到lun 就用集上
    try:
      id = x.properties['VolumeName'].value
      hostid = x.properties['HostOID'].value
      componseContent('lun.mapped.host[{id}]'.format(id=id), hostDict[hostid] ) # 主机
      componseContent('lun.mapped.host.port.wwpn[{id}]'.format(id=id), x.properties['VolumeWWPN'].value ) # 主机端口

      key  = hostid.encode('utf-8')
      k = hostDict[key] # 主机名称 
      VolumeName = x.properties['VolumeName'].value.encode('utf-8')
      if lunHost.has_key(k):
        n = lunHost[k]
        n.append(VolumeName) 
      else:
        n = [VolumeName]
      lunHost.update({k:n})

    except Exception as e:
      pass


  #lun集合发送给主机
  for x in lunHost:
    componseContent('storagehost.mapped.luns[{id}]'.format(id=x), json.dumps(lunHost[x]) ) #


    
#主机端口和远程端口映射
def localRemotePort(conn):
  print "机端口和远程端口映射关系信息采集"
  res = conn.ExecQuery('WQL', 'select * from IBMTSSVC_FabricElementView')
  for x in res:
    id = x.properties['LocalWWPN'].value + '-' + x.properties['RemoteWWPN'].value
    componseContent('fccon.remote.host.name[{id}]'.format(id=id), x.properties['Name'].value ) #
    componseContent('fccon.remote.port.wwpn[{id}]'.format(id=id), x.properties['RemoteWWPN'].value ) #
    componseContent('fccon.remote.port.nport.id[{id}]'.format(id=id), x.properties['RemoteNPortID'].value ) #
    componseContent('fccon.local.port.wwpn[{id}]'.format(id=id), x.properties['LocalWWPN'].value ) #
    componseContent('fccon.local.port.nport.id[{id}]'.format(id=id), x.properties['LocalNPortID'].value ) #
    componseContent('fccon.type[{id}]'.format(id=id), x.properties['Type'].value ) # 
    componseContent('fccon.status[{id}]'.format(id=id), x.properties['State'].value ) # active



#静态数据 
def msg():
  diskMsg(conn)
  poolMsg(conn)
  mdiskMsg(conn) 
  lunMsg(conn) 
  fcMsg(conn)
  sysMsg(conn)  
  hostMsg(conn)
  localRemotePort(conn)

#动态性能 数据 
def performance(): 
  diskPerformance(conn, 'disk', 'IBMTSSVC_DiskDrive', 'IBMTSSVC_DiskDriveStatistics') 
  raidPerformance(conn, 'raid', 'IBMTSSVC_BackendVolume', 'IBMTSSVC_BackendVolumeStatistics') 
  lunPerformance(conn, 'volume', 'IBMTSSVC_StorageVolume', 'IBMTSSVC_StorageVolumeStatistics')
  fcPerformance(conn, 'fc', 'IBMTSSVC_FCPort', 'IBMTSSVC_FCPortStatistics') 


def componseContent(key,value):
  global content

  content += '"{hostname}"   "{key}"   {value}\n' .format(hostname=hostname,key=key,value=value)


def sendToZabbix():
  tmpFile = '/tmp/'+fun+cluster
  f = open(tmpFile,"w")
  f.write(content)
  f.close()
  command = "/usr/local/zabbix_proxy/bin/zabbix_sender  -z '{proxy}' -i {file}" . format(proxy=proxy,file=tmpFile)
  os.popen(command)
  os.remove(tmpFile)


try:
  opts, args = getopt.gnu_getopt(sys.argv[1:], "-h", ["help", "cluster=", "user=", "password=", "hostname=","proxy=","fun="  ])
except getopt.GetoptError, err:
  print >> sys.stderr, str(err) # will print something like "option -a not recognized"
  usage()
  sys.exit(2)


content = ''
port  = 10051
cluster = None
user = None
password = None
cachefile = None
hostname = None
proxy = None
fun = None
for o, a in opts:
  if o == "--cluster": 
    cluster = a; 
    cachefile = '/tmp/ibm/'+cluster
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




if not cluster or not user or not password:
  print >> sys.stderr, 'Required argument is not set'
  usage()
  sys.exit(2)

## Loading stats cache from file
cache = None
try:
  if 'none' != cachefile:
    cache = json.load( open(cachefile, 'r') )
except Exception, err:
  print >> sys.stderr, "Can't load cache:", str(err)

''' Initialize cache if neccesary '''
if cache is None:
  cache = {}





conn = pywbem.WBEMConnection('https://'+cluster, (user, password), 'root/ibm',None,None,None,True)
conn.debug = True





try:
  eval(fun)()
  sendToZabbix()
except Exception as e:
  raise
else:
  pass
finally:
  pass




try:
  if 'none' != cachefile:
    json.dump( cache, open(cachefile, 'w') )
except Exception, err:
  print >> sys.stderr, "Can't save cache:", str(err)

