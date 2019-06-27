#!/usr/bin/env python


import paramiko
ssh = paramiko.SSHClient()
key = paramiko.AutoAddPolicy()
ssh.set_missing_host_key_policy(key)
ssh.connect('127.0.0.1', 22, 'user', 'passwd' ,timeout=5)
ssh.connect('192.168.6.45', 22, 'admin', 'ITCloud123!')
stdin, stdout, stderr = ssh.exec_command('ls -l')
stdin, stdout, stderr = ssh.exec_command('reset /map1')