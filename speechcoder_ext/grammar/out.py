import subprocess;
import threading;
from threading import Thread;
import time;
import sys;
import os;

global serv_path;
serv_path = "";
try:
	serv_path = os.environ["NPP_DRAGON"];
except:
	print "NPP_DRAGON ENVIRONMENTAL VARIABLE ISN'T SETUP";
	exit();

global ed;
ed = editor;

global mark_time;
mark_time = int(time.time());

global is_running;
is_running = True;

global esep;
esep = "###!!||!!###";

def cur_line_num(ed):
	cpos = ed.getCurrentPos();
	lc = ed.getLineCount();
	ln = 0;
	for i in range(0,lc):
		le = ed.getLineEndPosition(i);
		ln = i;
		if(le >= cpos):
			return ln;
	return ln;

def cleaner(_raw):
	global esep;
	ssep = "###)))(((###";
	rez = (False,None);
	raw = "";
	rrr = raw.split(esep);
	rrrl = len(rrr);
	if(rrrl < 2):
		return rez;
	es = "";
	for i in range(0,rrrl - 1):
		x = rrr[i];
		raw += es + x;
		es = esep;
	r = raw.split(ssep);
	rl = len(r);
	if(rl < 2):
		return rez;
	res = "";
	sep = "";
	for i in range(1,rl):
		res += sep + str(r[i]);
		sep = ssep;
	rez = (True,res);
	return rez;

def format_msg(data):
	rez = (None,None);
	dsep = "###<<<>>>###";
	psep = "###>>><<<###";
	ksep = "###((()))###";
	r = data.split(dsep);
	msg = r[0];
	rl = len(r);
	if((rl < 2)or(r[1] == "")):
		return (msg,{});
	p_raw = r[1];
	d = {};
	ps = p_raw.split(psep);
	for p in ps:
		kv = p.split(ksep);
		if((len(kv) < 2) or (kv[0] == "")):
			continue;
		d[kv[0]] = kv[1];
	rez = (msg,d);
	return rez;

def check_dt_dups():
	now = int(time.time());
	max_diff = 2; # 2 seconds.
	fn = "E:\\usr\\nppserve\\npp_check.txt";
	f = open(fn,"r+");
	x = int(f.readline());
	f.close();
	if((now - x) > max_diff):
		return True;
	return False;

def mark_dt():
	now = int(time.time());
	fn = "E:\\usr\\nppserve\\npp_check.txt";
	f = open(fn,"w+");
	f.write(str(now)+"\n");
	f.flush();
	f.close();

def dragon_guard_thread():
	global is_running;
	while(is_running):
		mark_dt();
		time.sleep(0.5);

def dragon_thread():
	global ed;
	global is_running;
	global esep;
	if(not check_dt_dups()):
		is_running = False;
		return False;
	
	tmp = "";
	Thread(target=dragon_guard_thread).start();
	# Roll out a subprocess for the client process.
	sub = subprocess.Popen(["python","E:\\usr\\nppserve\\npp_client_ka.py"],shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);
	while(is_running):
		time.sleep(0.05);
		raw = sub.stdout.readline();
		is_valid, data = cleaner(raw);
		if(not is_valid):
			tmp += raw;
			is_valid, data = cleaner(tmp);
			if(not is_valid):
				continue;
		tmp = "";
		msg, props = format_msg(data);
		cln = cur_line_num(ed);
		if(("type" not in props) or (props["type"] == "add_text")):
			indent = "inherit";
			if("indent" not in props):
				indent = props["indent"];
			lines = msg.replace("\r","").split("\n");
			prep = "";
			tc = int(ed.getLineIndentation(cln)/4);
			m = "";
			for x in lines:
				m += prep + x;
				prep = "\n" + ("\t" * tc);
			ed.addText(m);
		else:
			mtype = props["type"];
			
	
if __name__ == '__main__':
	Thread(target=dragon_thread).start();
