php -a
php > $cmd = 'ipmcget -t sensor -d list';    # 命令
php > $con = ssh2_connect('192.168.24.46',22);  #连接到SSH服务器
php > ssh2_auth_password($con, 'root', 'Huawei12#$');  #使用普通密码通过SSH进行身份验证
php > $shell = ssh2_shell($con);  #请求交互式shell
php > fwrite( $shell, $cmd.PHP_EOL);  #输入命令
php > $a=stream_get_contents($shell);  # 读取资源流到一个字符串
php > echo $a; 