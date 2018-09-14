#!/usr/bin/python
import os

os.popen('ps -eo pid,args,etime --sort start  | grep php > /tmp/d')

file = open("/tmp/d")
pid = ''
while 1:
    line = file.readline()
    if not line:
        break

    tmp = line.split()
    t = 0
    arr = tmp[3].split(':')

    for i in arr:
        if '-' not in i :
        t = t + int( i) * 60

    if t > 90 :
       pid = pid + ' ' + tmp[0]
file.close()

print 'kill -9' + pid
command = 'kill -9 '  + pid
os.system(command)

# 杀死php 进程进程
*/5 * * * * /usr/bin/python /usr/local/src/kill_php_script.py

chmod  a+x kill_php_script.py

service crond restart