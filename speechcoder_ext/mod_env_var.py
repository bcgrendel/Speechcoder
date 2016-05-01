# Original source code found here: http://code.activestate.com/recipes/416087/history/4/
# Modified to change/add a specific env var instead of being specified via a command line argument.

try:
	from _winreg import *
	import os, sys, win32gui, win32con
except:
	print "[ERROR] You need to install python win32 libraries first!\n\nTry looking here:\nhttps://pypi.python.org/pypi/pywin32";
	exit();

def queryValue(key, name):
	value, type_id = QueryValueEx(key, name)
	return value

def show(key):
	for i in range(1024):
		try:
			n,v,t = EnumValue(key, i)
			print '%s=%s' % (n, v)
		except EnvironmentError:
			break

def main():
	try:
		path = r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment'
		reg = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
		key = OpenKey(reg, path, 0, KEY_ALL_ACCESS)
		name = "NPP_DRAGON";
		value = os.getcwd();
		#name, value = sys.argv[1].split('=')
		if name.upper() == 'PATH':
			value = queryValue(key, name) + ';' + value
		if value:
			SetValueEx(key, name, 0, REG_EXPAND_SZ, value)
		else:
			DeleteValue(key, name)
		win32gui.SendMessage(win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE, 0, 'Environment')
	except Exception, e:
		print e

	CloseKey(key)
	CloseKey(reg)
    
if __name__=='__main__':
	main()
