#!/usr/bin/python3
#coding=utf-8

import pywbem,getopt, sys, datetime, time, calendar, json,os,math,re,gc
import threading
from time import ctime,sleep



class Hwv3:
	"""docstring for Hwv3
		自己配置的都是5989
		存储用系统号区分，每一个指标都带有序列号，格式：序列号_指标
		6800v3 没有IO数据，只有状态，关键告警还要snmptrap
		
		190718 
		序列号 已取消
	"""
	conn = None
	namespace = 'root/huawei'
	zabbix_sender = '/usr/local/zabbix_proxy/bin/zabbix_sender'
	port = 10051 # zabbix 端口
	cache = {}
	cacheFile = None
	content = ''

	def __init__(self, ip,user,pwd,host,port,proxy,fun):
		self.ip = ip
		self.user = user
		self.pwd = pwd
		self.host = host
		self.proxy = proxy
		self.port = port
		self.fun = fun
		self.conn = self.connect()


		if not os.path.exists('/tmp/huawei'):
			os.mkdir('/tmp/huawei')

		self.cacheFile = '/tmp/huawei/hw' + self.ip
		if os.path.exists(self.cacheFile):
			self.cache = json.load( open(self.cacheFile, 'r') )
		else:
			f = open(self.cacheFile,'w')
			f.write('{}')
			f.close()

			
		

		item = 'self.' + fun
		eval(item)()
		self.send_to_zabbix()
		print("采集完成")


	#不再使用多线程，拆开
	def msg(self):
		arr2 = ['fcportMsg','poolMsg','enclosureMsg','raidMsg','diskBaseMsg','diskOtherMsg','hostMsg','hostGroupMsg','LunMsg','LunGroupMsg','baseMsg','baseSizeMsg','baseOtherMsg']
		t2 = []
		for i in arr2:
			fun = 'self.' + i
			t = threading.Thread(target=eval(fun))
			t2.append(t)

		for t in t2:
			t.setDaemon(True)
			t.start()

		for i in t2:
			i.join()

	def performance(self):
		arr = ['fcportMsg','poolMsg','enclosureMsg','raidMsg','diskMsg','LunMsg','baseOtherMsg']
		t2 = []
		for i in arr:
			fun = 'self.' + i
			t = threading.Thread(target=eval(fun))
			t2.append(t)
		for t in t2:
			t.setDaemon(True)
			t.start()
		for i in t2:
			i.join()

	def composeContent(self,key,value):
		value = str(value)
		if len(value) == 0:
			value = '--'
		self.content += self.host + "\t" + '"'+str(key)+'"' + "\t" + str(value) + "\n"


	def connect(self):
		 return pywbem.WBEMConnection('https://'+self.ip, (self.user, self.pwd), Hwv3.namespace,None,None,None,True)

	def saveCache(self):
		json.dumps(self.cache, open(self.cacheFile, 'w') )

	def send_to_zabbix(self):
		tempFile = '/tmp/' + self.ip + self.fun
		f = open(tempFile,'w')
		f.write(self.content)
		f.close()
		command = '{zabbix_sender} -z {proxy} -i {file}'.format(zabbix_sender=Hwv3.zabbix_sender,proxy=self.proxy,file=tempFile)
		os.popen(command)
		sleep(0.5)
		os.remove(tempFile)




	def fcportMsg(self):
		print("采集FC PORT信息")
		data = self.conn.EnumerateInstances('HuaSy_FrontEndFCPort')
		for x in data:
			id = x['ElementName']
			if self.fun != 'performance':
				self.composeContent('fcif.speed[{id}]'.format(id=id), x['Speed'])
				self.composeContent('fcif.wwpn[{id}]'.format(id=id), x['PermanentAddress'])
				self.composeContent('fcif.desc[{id}]'.format(id=id), x['ElementName'])
				#self.composeContent('fcif.type[{id}]'.format(id=id), x['PortType'])
				#self.composeContent('fcif.max.speed[{id}]'.format(id=id), x['MaxSpeed'])
			else:
				status = x['OperationalStatus']
				self.composeContent('fcif.status[{id}]'.format(id=id), status[0])
		del data
		gc.collect()

	def poolMsg(self):
		print("采集存储池信息")
		data = self.conn.EnumerateInstances('HuaSy_ConcreteStoragePool')
		newData = {} #组合成ID=>name 给下面使用，不用再关联一次
		for x in data:
			serial = x['InstanceID']
			id = x['ElementName']
			newData[serial] = id
			if self.fun != 'performance':
				self.composeContent('pool.desc[{id}]'.format(id=id), x['ElementName'])
				self.composeContent('pool.capacity.size.total[{id}]'.format(id=id), x['TotalManagedSpace']) #池总容量大小
				self.composeContent('pool.capacity.size.free[{id}]'.format(id=id), x['RemainingManagedSpace']) # 池剩余容量大小
				self.composeContent('pool.capacity.size.used[{id}]'.format(id=id), x['TotalManagedSpace']-x['RemainingManagedSpace']) #池已用容量大小
				#self.composeContent('pool.operational.status[{id}]'.format(id=id), x['OperationalStatus'])#运行状态
				self.composeContent('pool.id[{id}]'.format(id=id), x['PoolID'])#
			else:
				self.composeContent('pool.status[{id}]'.format(id=id), x['HealthState'])#健康状态

		if self.fun != 'performance':
			cs_paths = self.conn.EnumerateInstanceNames('HuaSy_ConcreteStoragePool')
			for k,cs_path in enumerate(cs_paths):
				serial  = cs_path['InstanceID']
				id = newData[serial]
				cs_inst = self.conn.GetInstance(cs_path)
				dmsg = self.conn.Associators(cs_inst.path,'HuaSy_AllocatedFromStoragePool','HuaSy_DiskStoragePool')
				if len(dmsg)>0:
					self.composeContent('pool.mapped.diskdm[{id}]'.format(id=id), dmsg[0]['ElementName']) # 存储池所在的磁盘域
			del cs_paths
		del newData
		del data
		gc.collect()

	# 控制框或硬盘框
	def enclosureMsg(self):
		print("采集控制框或硬盘框信息")
		data = self.conn.EnumerateInstances('HuaSy_EnclosureChassis')
		for x in data:
			if 'ElementName' in x:
				id = x['ElementName']
				if self.fun != 'performance':
					self.composeContent('diskencl.desc[{id}]'.format(id=id), x['ElementName']) # 控制器名
					self.composeContent('diskencl.mfc[{id}]'.format(id=id), x['Manufacturer']) # 厂家
					self.composeContent('diskencl.model[{id}]'.format(id=id), x['Model']) # 型号
					self.composeContent('diskencl.serial[{id}]'.format(id=id), x['SerialNumber']) # 序列号
					self.composeContent('diskencl.type[{id}]'.format(id=id), x['ChassisPackageType']) # 类型 17：控制框，18：硬盘框
				else:
					self.composeContent('diskencl.status[{id}]'.format(id=id), x['HealthState']) # 健康状态
		del data
		gc.collect()

	# 阵列信息 （磁盘域信息）
	def raidMsg(self):
		print("采集阵列信息")
		data = self.conn.EnumerateInstances('HuaSy_DiskStoragePool')
		for x in data:
			id = x['ElementName']
			if self.fun != 'performance':
				self.composeContent('diskdm.desc[{id}]'.format(id=id), x['ElementName']) # 名称
				self.composeContent('diskdm.size.total[{id}]'.format(id=id), x['TotalManagedSpace']) # 总容量
				self.composeContent('diskdm.size.used[{id}]'.format(id=id), x['RemainingManagedSpace']) #
				self.composeContent('diskdm.size.hotbackup[{id}]'.format(id=id), x['TotalManagedSpace'] - x['RemainingManagedSpace'] ) #
				self.composeContent('diskdm.size.free[{id}]'.format(id=id), x['HuaSyAvailableCapacity']) # 未分配的空闲容量
				#self.composeContent('raid.pool.id[{id}]'.format(id=id), x['PoolID'].split('_')[-1]) # 存储ID 这是一个字符PD_0,要处理下
			else:
				self.composeContent('diskdm.status[{id}]'.format(id=id), x['HealthState']) # 健康状态
		del data
		gc.collect()

	# 存储池所在的磁盘域
	# def poolInRaid(self):
	# 	cs_paths = self.conn.EnumerateInstanceNames('HuaSy_ConcreteStoragePool')
	# 	print data[0]
	# 	for cs_path in cs_paths:
	# 		serial  = cs_path['InstanceID']
	# 		id = ''
	# 		print cs_path
	# 		if serial.startswith(self.serial):
	# 			cs_inst = self.conn.GetInstance(cs_path)
	# 			dmsg = self.conn.Associators(cs_inst.path,'HuaSy_AllocatedFromStoragePool','HuaSy_DiskStoragePool')
	# 			if len(dmsg)>0:
	# 				self.composeContent('pool.mapped.diskdm[{id}]'.format(id=cs_path['InstanceID']), dmsg[0]['ElementName']) # 存储池所在的磁盘域

	#硬盘信息
	"""
		HuaSy_DiskDrive 基本信息
		HuaSy_DiskExtent 容量
		HuaSy_DiskPackag 物理信息
	"""
	def diskMsg(self):
		self.diskBaseMsg()
		self.diskOtherMsg()
	
	def diskBaseMsg(self):
		print("采集硬盘基本信息")
		data = self.conn.EnumerateInstances('HuaSy_DiskDrive')
		newData = {}
		for x in data:
			serial = x['DeviceID']
			id = x['ElementName']
			#newData[serial] = id
			newData[serial] = id
			if self.fun != 'performance':
				self.composeContent('disk.desc[{id}]'.format(id=id), x['ElementName']) # 名称
				self.composeContent('disk.type[{id}]'.format(id=id), x['Caption']) # 标题来当类型
				self.composeContent('disk.encryption.type[{id}]'.format(id=id), x['Encryption']) # 加密类型 0：未加密
			else:
				self.composeContent('disk.status[{id}]'.format(id=id), x['EnabledState']) # 状态 2：正常，其它 未知
				self.composeContent('disk.online[{id}]'.format(id=id), x['OperationalStatus'][0]) # 
			
		if self.fun != 'performance':
			source = self.conn.EnumerateInstanceNames('HuaSy_DiskDrive')
			for s in source:
				serial = s['DeviceID']
				id = newData[serial]				
				cs_inst = self.conn.GetInstance(s)
				dmsg = self.conn.Associators(cs_inst.path,'HuaSy_MediaPresent','HuaSy_DiskExtent')
				if dmsg:
					self.composeContent('disk.blocks.number[{id}]'.format(id=id), dmsg[0]['NumberOfBlocks']) #  块数
					self.composeContent('disk.blocks.size[{id}]'.format(id=id), dmsg[0]['BlockSize']) # 块大小 4K 
					self.composeContent('disk.size.total[{id}]'.format(id=id), dmsg[0]['NumberOfBlocks'] * dmsg[0]['BlockSize']) #  容量
			del source
		
		del data
		del newData
		gc.collect()


	def diskOtherMsg(self):
		print("采集硬盘扩展信息")
		data = self.conn.EnumerateInstances('HuaSy_DiskPackage')
		for x in data:
			id = x['ElementName']
			self.composeContent('disk.Version[{id}]'.format(id=id), x['Version']) #  版本
			self.composeContent('disk.serial[{id}]'.format(id=id), x['SerialNumber']) # 序列号
			self.composeContent('disk.model[{id}]'.format(id=id), x['Model']) # 型号
			self.composeContent('disk.mfc[{id}]'.format(id=id), x['Manufacturer']) #厂家 

		del data
		gc.collect()
	# 主机信息
	"""
	主机信息没有找到类，只找一个启动器，主机信息需要从启动器过去重拿出来
	启动器：主机关联端口的关联表，这里只取FC端口
	保留 InstanceID  用作关联主机类型时的过滤
	一台虚拟主机有一个或多个HBA卡

	"""
	def hostMsg(self):
		print("采集主机信息")
		data = self.conn.EnumerateInstances('HuaSy_StorageHardwareID')
		names = []
		ids = {}
		tmp = {} #映射的远程wwpn,即启动器
		source = self.conn.EnumerateInstanceNames('HuaSy_StorageHardwareID') #
		for x in data:
			name = x['ElementName']
			id = oid = x['InstanceID']
			id = name
			ids[id] = name
			if name not in names:  # 
				names.append(name)
				self.composeContent('storagehost.desc[{id}]'.format(id=id), name) #

				#操作系统,所属主机组,映射的LUN
				for s in source:
					if s['InstanceID'] == oid:
						cs_inst = self.conn.GetInstance(s)
						#操作系统
						dmsg = self.conn.Associators(cs_inst.path,'HuaSy_ElementSettingData','HuaSy_StorageClientSettingData')
						if dmsg:
							self.composeContent('storagehost.os.type[{id}]'.format(id=id), dmsg[0]['ElementName']) #操作系统

						#所属主机组
						dmsg = self.conn.Associators(cs_inst.path,'HuaSy_MemberOfCollection','HuaSy_InitiatorMasKingGroup')
						if dmsg:
							self.composeContent('storagehost.hostgroup.name[{id}]'.format(id=id), dmsg[0]['ElementName']) #所属主机组

						#映射的LUN
						t1 = self.conn.AssociatorNames(cs_inst.path,'HuaSy_AuthorizedSubject','HuaSy_AuthorizedPrivilege')
						if len(t1)>0:
							t2 = self.conn.AssociatorNames(t1[0],'HuaSy_AuthorizedTarget','HuaSy_MaskingSCSIProtocolController')
							if t2:
								t3 = self.conn.Associators(t2[0],'HuaSy_ProtocolControllerForUnit','HuaSy_StorageVolume')
								if t3:
									luns = set()
									for t in t3:
										luns.add(t['ElementName'])
									if luns:
										self.composeContent('storagehost.mapped.luns[{id}]'.format(id=id), json.dumps(list(luns))) #存储主机已映射卷列表
			#映射的远程wwpn,即启动器
			if name not in tmp:
				tmp[name] = set()
			tmp[name].add(x['StorageID'])
				
		for x in tmp:#映射的远程wwpn,即启动器（光纤端口）
			self.composeContent('storagehost.ports.wwpns[{id}]'.format(id=x), json.dumps(list(tmp[x]))) #存储主机WWPN列表

		del source
		del data
		gc.collect()



	# 主机组信息
	def hostGroupMsg(self):
		print("采集主机组信息")
		data = self.conn.EnumerateInstances('HuaSy_InitiatorMaskingGroup')
		source = self.conn.EnumerateInstanceNames('HuaSy_InitiatorMasKingGroup')
		names = {}
		for s in source:
			id  = s['InstanceID']
			cs_inst = self.conn.GetInstance(s)
			dmsg = self.conn.Associators(cs_inst.path,'HuaSy_MemberOfCollection','HuaSy_StorageHardwareID')
			tmp = set()
			for d in dmsg:
				tmp.add(d['ElementName'])
			names[id] = tmp
		for x in data:
			serial = x['InstanceID']
			id = name = x['ElementName']
			self.composeContent('storagehg.name[{id}]'.format(id=id), name) #  主机组名称
			#主机组下所有主机
			if serial in names:
				self.composeContent('storagehg.mapped.hosts[{id}]'.format(id=x['ElementName']), json.dumps(list(names[serial]))) #  主机组下所有主机

		del data
		del source
		gc.collect()

	def getLunInstance(self):
		self.lunInstance = self.conn.EnumerateInstanceNames('HuaSy_StorageVolume')
		data = self.conn.EnumerateInstances('HuaSy_StorageVolume')
		tmp = {}
		for x in data:
			serial = x['DeviceID'] 
			id = x['ElementName']
			tmp[serial] = id
		self.lun = data
		self.newData = tmp
		
			


	def LunMsg(self):
		self.getLunInstance()
		print("采集LUN信息")
		#data = self.conn.EnumerateInstances('HuaSy_StorageVolume')
		newData = {}
		for x in self.lun:
			#serial = x['DeviceID'] 
			id = x['ElementName']
			#newData[serial] = id
			if self.fun != 'performance':
				self.composeContent('lun.desc[{id}]'.format(id=id), x['ElementName']) # 名称
				self.composeContent('lun.size.total[{id}]'.format(id=id), x['NumberOfBlocks'] * x['BlockSize']) #
				self.composeContent('lun.blocks.number[{id}]'.format(id=id), x['NumberOfBlocks']) #
				self.composeContent('lun.blocks.size[{id}]'.format(id=id), x['BlockSize']) #
				self.composeContent('lun.thinly[{id}]'.format(id=id), x['ThinlyProvisioned']) # 是否是精简卷
				self.composeContent('lun.wwn[{id}]'.format(id=id), x['Name']) # lun wwn 
				self.composeContent('lun.nofailure[{id}]'.format(id=id), x['NoSinglePointOfFailure']) # 无单点故障
			else:
				self.composeContent('lun.status[{id}]'.format(id=id), x['OperationalStatus'][0]) # 
	
	# LUN 映射的主机
	def lunMappedHostMsgRun1(self):
		self.getLunInstance()
		cs_paths = self.lunInstance
		for cs_path in cs_paths:
			serial = cs_path['DeviceID']
			id = self.newData[serial]
			cs_inst = self.conn.GetInstance(cs_path)
			t1 = self.conn.AssociatorNames(cs_inst.path,'HuaSy_ProtocolControllerForUnit','HuaSy_MaskingSCSIProtocolController')
			if t1:
				t2 = self.conn.AssociatorNames(t1[0],'HuaSy_AuthorizedTarget','HuaSy_AuthorizedPrivilege') # 多个
				hosts = set()
				for o in t2:
					t3 = self.conn.Associators(o,'HuaSy_AuthorizedSubject','HuaSy_StorageHardwareID')
					hosts.add(t3[0]['ElementName'])
				if hosts:
					self.composeContent('lun.mapped.host[{id}]'.format(id=id), json.dumps(list(hosts)))# LUN 映射的主机
				else:
					self.composeContent('lun.mapped.host[{id}]'.format(id=id), '未映射')# LUN 映射的主机
					
	def lunMappedHostMsgRun(self,cs_paths):
		for cs_path in cs_paths:
			serial = cs_path['DeviceID']
			id = self.newData[serial]
			cs_inst = self.conn.GetInstance(cs_path)
			t1 = self.conn.AssociatorNames(cs_inst.path,'HuaSy_ProtocolControllerForUnit','HuaSy_MaskingSCSIProtocolController')
			if t1:
				t2 = self.conn.AssociatorNames(t1[0],'HuaSy_AuthorizedTarget','HuaSy_AuthorizedPrivilege') # 多个
				hosts = set()
				for o in t2:
					t3 = self.conn.Associators(o,'HuaSy_AuthorizedSubject','HuaSy_StorageHardwareID')
					hosts.add(t3[0]['ElementName'])
				if hosts:
					self.composeContent('lun.mapped.host[{id}]'.format(id=id), json.dumps(list(hosts)))# LUN 映射的主机
				else:
					self.composeContent('lun.mapped.host[{id}]'.format(id=id), '未映射')# LUN 映射的主机

		
	def lunMappedHostMsg(self):
		self.getLunInstance()
		cs_paths = self.lunInstance
		
		print("LUN 映射的主机")
		
		num = 10
		page  = math.ceil( len(cs_paths) / num )
		t2 = []
		
		for p in range(page):
			start = p * num
			end = start +  num
			arr = cs_paths[start:end]
			
			
			fun = 'self.lunMappedHostMsgRun'
			t = threading.Thread(target=eval(fun),args=(arr,))
			t2.append(t)
			
		for t in t2:
			t.setDaemon(True)
			t.start()
		for i in t2:
			i.join()
	
	
	
					
	#lun所在lun组
	def lunInGroupMsg(self):
		self.getLunInstance()
		print('lun所在lun组')
		for cs_path in self.lunInstance:
			serial = cs_path['DeviceID']
			id = self.newData[serial] # lun.name 
			cs_inst = self.conn.GetInstance(cs_path)
			#lun所在lun组
			dmsg = self.conn.Associators(cs_inst.path,'HuaSy_OrderedMemberOfCollection','HuaSy_DeviceMaskingGroup')
			if dmsg:
				self.composeContent('lun.mapped.lungroup[{id}]'.format(id=id), dmsg[0]['ElementName']) # lun 所在 lun组
			else:
				self.composeContent('lun.mapped.lungroup[{id}]'.format(id=id), '未映射') # lun 所在 lun组
	#lun所属存储池
	def lunInPoolMsg(self):
		print('lun所属存储池')
		self.getLunInstance()
		for cs_path in self.lunInstance :
			serial = cs_path['DeviceID']
			id = self.newData[serial]
			cs_inst = self.conn.GetInstance(cs_path)
			dmsg = self.conn.Associators(cs_inst.path,'HuaSy_AllocatedFromStoragePool','HuaSy_ConcreteStoragePool')
			if dmsg:
				self.composeContent('lun.pool.name[{id}]'.format(id=id), dmsg[0]['ElementName'])#lun所属存储池



	def LunGroupMsg(self):
		print("采集LUN信息")
		data = self.conn.EnumerateInstances('HuaSy_DeviceMaskingGroup')
		for x in data:
			id = x['ElementName']
			self.composeContent('lungroup.name[{id}]'.format(id=id), x['ElementName']) # 名称



	def baseOtherMsg(self):
		data = self.conn.EnumerateInstances('HuaSy_StorageSystem')
		if self.fun != 'performance':
			self.composeContent('dev.syslocation', str(data[0]['ElementName'])) #
			#增加一个wwn，可以直接用来关联交换机,wwn 就是控制框的序列号	
			self.composeContent('dev.wwn', str(data[0]['OtherIdentifyingInfo'][0]))
		else:
			self.composeContent('dev.status', data[0]['HealthState']) #

	
	def devMsg(self):
		self.baseMsg()
		self.baseSizeMsg()
		self.baseOtherMsg()
				
	def baseMsg(self):
		print("采集设备基本信息")
		data = self.conn.EnumerateInstances('HuaSy_ArrayProduct')
		self.composeContent('dev.serial', data[0]['IdentifyingNumber']) # 
		self.composeContent('dev.name', data[0]['ElementName']) # 
		self.composeContent('dev.version', data[0]['Version']) # 
		self.composeContent('dev.mfc', data[0]['Vendor']) #

	def baseSizeMsg(self):
		data = self.conn.EnumerateInstances('HuaSy_PrimordialStoragePool')
		self.composeContent('dev.storage.size.total', data[0]['TotalManagedSpace']) #总容量 
		self.composeContent('dev.storage.size.free', data[0]['RemainingManagedSpace']) # 剩余容量
		self.composeContent('dev.storage.size.used', data[0]['TotalManagedSpace']-data[0]['RemainingManagedSpace']) #使用容量


"""
ip = '10.142.88.2'
user = 'smis_admin'
pwd = 'Admin@12'
host = 'NM-XX-A5403-F03-01U_46U-HW-6800V3-B01'
port = 10051
proxy = '10.142.88.4'
fun = 'msg'
serial = '210235982610J1000002'
h = Hwv3(ip,user,pwd,host,port,proxy,fun,serial)
"""
