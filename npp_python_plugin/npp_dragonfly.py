import subprocess;
import threading;
from threading import Thread;
import time;
import sys;
import os;
import re;
import jellyfish;
import lxml;
from lxml import etree;
import sqlite3;

import traceback;

import socket

from fuzzy_string_comparison import get_closest_match;

import win32clipboard;

try:
	import tinycss;
except:
	pass;

def set_cb(t):
	win32clipboard.OpenClipboard();
	win32clipboard.EmptyClipboard();
	win32clipboard.SetClipboardData(1,t);
	win32clipboard.CloseClipboard();

def get_cb():
	win32clipboard.OpenClipboard();
	r = win32clipboard.GetClipboardData();
	win32clipboard.CloseClipboard();
	return r;

def get_dirname(fn):
	tf = fn.rfind("/");
	tf2 = fn.rfind("\\");
	if(tf2 > tf):
		tf = tf2;
	if(tf == -1):
		return "";
	dir = fn[0:tf];
	return dir;

current_lang = "python";
dm = {};

icb_max = 5;
cb_buff = 0;
cb_page_default = "default";
cb_page = cb_page_default;
cb_page_auto_detect = True;
cb_page_map = {};
cb_page_bmap = {};
cb_list_flag = -1;
internal_cb = [""] * icb_max;

paste_port = 36555;
cmd_port = 36556;
paste_send_port = 35555;
cmd_send_port = 35556;

rcv_port_list = [paste_port,cmd_port];
global dsep;
dsep = "###<<<>>>###";

global serv_path;
serv_path = "";
try:
	serv_path = os.environ["NPP_DRAGON"];
except:
	print "NPP_DRAGON ENVIRONMENTAL VARIABLE ISN'T SETUP";
	exit();

raw = "python";
try:
	
	with open(serv_path+"\\grammar\\context.txt","r+") as f:
		raw = f.read();
	raw.replace("\n","").replace("\r","").replace("\t","").replace(" ","").lower();
except:
	pass;
current_lang = raw;

global ed;
ed = editor;

global mark_time;
mark_time = int(time.time());

global is_running;
is_running = True;

global esep;
esep = "###!!||!!###";


auto_lang = True;
# r = re.compile(r'[0-9_]*[a-zA-Z]+[0-9_]*');

global action_map;
action_map = {};

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

def backspace(x=1):
	global ed;
	for i in range(0,x):
		ed.deleteBack();

action_map["backspace"] = backspace;
	
def move_left(x=1):
	global ed;
	tpos = int(ed.getCurrentPos());
	tpos -= x;
	if(tpos < 0):
		tpos = 0;
	ed.gotoPos(tpos);

action_map["left"] = move_left;

def move_right(x=1):
	global ed;
	tpos = int(ed.getCurrentPos());
	tpos += x;
	ed.gotoPos(tpos);

action_map["right"] = move_right;
	
def move_up(x=1):
	global ed;
	for i in range(0,x):
		ed.lineUp();

action_map["up"] = move_up;

def move_down(x=1):
	global ed;
	for i in range(0,x):
		ed.lineDown();

action_map["down"] = move_down;

def doc_top(x=1):
	global ed;
	ed.documentStart();
	
action_map["doc_top"] = doc_top;

def doc_bot(x=1):
	global ed;
	ed.documentEnd();

action_map["doc_bot"] = doc_bot;

def line_start(x=1):
	global ed;
	cln = cur_line_num(ed);
	cln -= 1;
	tpos = 0;
	if(cln > 0):
		tpos = ed.getLineEndPosition(cln) + 2;
	ed.gotoPos(tpos);
action_map["line_start"] = line_start;

def line_end(x=1):
	global ed;
	ed.lineEnd();

action_map["line_end"] = line_end;

def container_nav(x=1,type=0,direction=0,targ="(",targ2=")"):
	global ed;
	tlen = int(Editor.getTextLength(ed));
	tpos = int(ed.getCurrentPos());
	txt = "";
	p = -1;
	if(direction == 1): # Right
		txt = Editor.getTextRange(editor,tpos,tlen);
		y = 0
		#Console.write(console,"LEN: "+str(len(txt))+"\n");
		for i in range(0,x):
			y = txt.find(targ,y);
			if(y != -1):
				p = y;
				y += len(targ);
		p += tpos;
		#Console.write(console,"pos: "+str(p)+"\n\n");
	elif(direction == 0): # Left
		txt = Editor.getTextRange(editor,0,tpos);
		y = len(txt);
		for i in range(0,x):
			y = txt[:y].rfind(targ);
			if(y != -1):
				p = y;
	#Console.write(console,"type: "+str(type)+"\n\n");
	cstack = []; # container stack
	wdw_size = 500; # window size
	wdw = "";
	wdw_i = 0;
	cpos = p;
	if(p != -1):
		if(type == 0):
			# Move cursor to just inside the container.
			ed.gotoPos(p+1);
		elif(type == 1):
			nlf = False;
			# Move cursor to first line after bracket...
			cpos = p+1
			while(cpos < tlen):
				if(wdw_i >= len(wdw)):
					rem = tlen - cpos;
					tws = wdw_size;
					if(rem < tws):
						tws = rem;
					wdw = Editor.getTextRange(editor,cpos,cpos+tws);
					wdw_i = 0;
				c = wdw[wdw_i];
				wdw_i += 1;
				if((nlf) and not((c == " ")or(c == "\t"))):
					#Console.write(console,"nlf: [pos: "+str(cpos)+"] ("+str(ord(c))+") "+str(c)+"\n\n");
					break;
				if(c == "\n"):
					nlf = True;
				if(c == targ):
					cstack.append(targ);
				elif(c == targ2):
					if targ in cstack:
						cstack.remove(targ);
					else:
						break;
				cpos += 1;
			if((cpos == tlen) or nlf):
				#Console.write(console,"goto: [pos: "+str(cpos)+"]\n\n");
				ed.gotoPos(cpos);
			
		elif(type == 2):
			# Find last line after open container.
			cpos = p+1
			tln = p+1;
			#Console.write(console,"targs: "+targ+" "+targ2+"\n\n");
			while(cpos < tlen):
				if(wdw_i >= len(wdw)):
					rem = tlen - cpos;
					tws = wdw_size;
					if(rem < tws):
						tws = rem;
					wdw = Editor.getTextRange(editor,cpos,cpos+tws);
					wdw_i = 0;
				c = wdw[wdw_i];
				wdw_i += 1;
				if(c == "\n"):
					tln = cpos;
					#Console.write(console,"tln: [pos: "+str(cpos)+"] ("+str(ord(c))+") "+str(c)+"\n\n");
				if(c == targ):
					cstack.append(targ);
				elif(c == targ2):
					if targ in cstack:
						cstack.remove(targ);
					else:
						break;
				cpos += 1;
			if(cpos != tlen):
				#Console.write(console,"goto: [pos: "+str(cpos)+"]\n\n");
				ed.gotoPos(tln);
		elif(type == 3):
			# Goto just inside closing container symbol.
			cpos = p+1
			while(cpos < tlen):
				if(wdw_i >= len(wdw)):
					rem = tlen - cpos;
					tws = wdw_size;
					if(rem < tws):
						tws = rem;
					wdw = Editor.getTextRange(editor,cpos,cpos+tws);
					wdw_i = 0;
				c = wdw[wdw_i];
				wdw_i += 1;
				if(c == targ):
					cstack.append(targ);
				elif(c == targ2):
					if targ in cstack:
						cstack.remove(targ);
					else:
						break;
				cpos += 1;
			if(cpos != tlen):
				ed.gotoPos(cpos);

def paren_nav_left(x=1,type=0):
	container_nav(x,type,0,"(",")");
	
action_map["paren_nav_left"] = paren_nav_left;

def paren_nav_right(x=1,type=0):
	container_nav(x,type,1,"(",")");

action_map["paren_nav_right"] = paren_nav_right;

def square_nav_left(x=1,type=0):
	container_nav(x,type,0,"[","]");
	
action_map["square_nav_left"] = square_nav_left;

def square_nav_right(x=1,type=0):
	container_nav(x,type,1,"[","]");

action_map["square_nav_right"] = square_nav_right;

def curly_nav_left(x=1,type=0):
	container_nav(x,type,0,"{","}");
	
action_map["curly_nav_left"] = curly_nav_left;

def curly_nav_right(x=1,type=0):
	container_nav(x,type,1,"{","}");

action_map["curly_nav_right"] = curly_nav_right;

def angle_nav_left(x=1,type=0):
	container_nav(x,type,0,"<",">");
	
action_map["angle_nav_left"] = angle_nav_left;

def angle_nav_right(x=1,type=0):
	container_nav(x,type,1,"<",">");

action_map["angle_nav_right"] = angle_nav_right;


def save_source_file(x=1):
	global ed;
	Notepad.menuCommand(notepad,41006);

action_map["save_source_file"] = save_source_file;

def s_cut(x=1):
	global ed;
	global icb_max;
	global cb_buff;
	global cb_page;
	global cb_list_flag;
	global internal_cb;
	global serv_path;
	ss = Editor.getSelectionStart(editor);
	se = Editor.getSelectionEnd(editor);
	txt = Editor.getTextRange(editor,ss,se);
	internal_cb[cb_buff] = txt;
	set_cb(internal_cb[cb_buff]);
	# Save to sqlite3 db.
	try:
		with open(serv_path+"\\clipboard\\buffer.data","w+") as f:
			f.write(txt);
			f.flush();
	except:
		pass;
	sub = subprocess.Popen(["python","-u",serv_path+"\\clipboard\\cb_client.py",":copy",str(cb_page),":buffer",str(cb_buff+1)],shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);
	try:
		raw = sub.communicate()[0];
		Console.write(console,"copy: [page: "+str(cb_page)+" buffer: "+str(cb_buff+1)+"] "+raw+"\n");
	except:
		pass;
	clipboard_list(cb_list_flag,1);
	sss = ed.getSelectionStart();
	sse = ed.getSelectionEnd();
	if(sss != sse):
		ed.deleteBack();

action_map["cut"] = s_cut;

def s_copy(x=1):
	global ed;
	global icb_max;
	global cb_buff;
	global cb_page;
	global cb_list_flag;
	global internal_cb;
	global serv_path;
	ss = Editor.getSelectionStart(editor);
	se = Editor.getSelectionEnd(editor);
	txt = Editor.getTextRange(editor,ss,se);
	internal_cb[cb_buff] = txt;
	set_cb(internal_cb[cb_buff]);
	# Save to sqlite3 db.
	try:
		with open(serv_path+"\\clipboard\\buffer.data","w+") as f:
			f.write(txt);
			f.flush();
	except:
		pass;
	sub = subprocess.Popen(["python","-u",serv_path+"\\clipboard\\cb_client.py",":copy",str(cb_page),":buffer",str(cb_buff+1)],shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);
	try:
		raw = sub.communicate()[0];
		Console.write(console,"copy: [page: "+str(cb_page)+" buffer: "+str(cb_buff+1)+"] "+raw+"\n");
	except:
		pass;
	clipboard_list(cb_list_flag,1);

action_map["copy"] = s_copy;

def s_paste(x=1):
	global ed;
	global icb_max;
	global cb_buff;
	global internal_cb;
	sss = ed.getSelectionStart();
	sse = ed.getSelectionEnd();
	if(sss != sse):
		ed.deleteBack();
	ed.addText(internal_cb[cb_buff]);

action_map["paste"] = s_paste;

def clone(x=1):
	global ed;
	global icb_max;
	global cb_buff;
	global internal_cb;
	ss = Editor.getSelectionStart(editor);
	se = Editor.getSelectionEnd(editor);
	txt = Editor.getTextRange(editor,ss,se);
	ed.lineEnd();
	ed.addText("\n%s" % txt);

action_map["clone"] = clone;

def clipboard_list(x=-1,y=0):
	global ed;
	global icb_max;
	global cb_buff;
	global internal_cb;
	global serv_path;
	global cb_list_flag;
	cb_list_flag = x;
	tfn = serv_path+"\\clipboard\\clipboard.ini"
	txt = "";
	if(x == -1):
		for i in range(0,icb_max):
			p = "        ";
			if(i == cb_buff):
				p = "[ACTIVE]";
			txt = "%s%s" % (txt,"\n# ======================================");
			txt = "%s%s%s%s%s" % (txt,"\n#   ",p,"    BUFFER ",str(i+1));
			txt = "%s%s" % (txt,"\n# ======================================\n");
			txt = "%s%s\n" % (txt,internal_cb[i]);
	else:
		i = cb_buff;
		y = -1;
		try:
			y = int(x) - 1;
		except:
			pass;
		if((y >= 0) and (y < icb_max)):
			i = y;
		txt = "%s%s" % (txt,"\n# ======================================");
		txt = "%s%s%s%s" % (txt,"\n#   ","    BUFFER ",str(i+1));
		txt = "%s%s" % (txt,"\n# ======================================\n");
		txt = "%s%s\n" % (txt,internal_cb[i]);
	try:
		with open(tfn,"w+") as f:
			f.write(txt.replace("\r", ""));
			f.flush();
	except:
		pass;
	
	# Notepad.menuCommand(notepad,44072); # switch views.
	#Console.write(console,txt);
	#print tfn;
	fl = Notepad.getFiles(notepad);
	efl = [];
	efd = {};
	if(x == 0):
		for f in fl:
			efl.append(f[0]);
			efd[f[0]] = f[1];
		if(tfn in efl):
			cbid = Notepad.getCurrentBufferID(notepad);
			Notepad.activateBufferID(notepad,efd[tfn]);
			Notepad.close(notepad);
			Notepad.activateBufferID(notepad,cbid);
			try:
				with open(tfn,"w+") as f:
					f.write("");
					f.flush();
			except:
				pass;
			time.sleep(0.1);
	else:
		cbid = Notepad.getCurrentBufferID(notepad);
		vbid = None;
		fl = Notepad.getFiles(notepad);
		efl = [];
		efd = {};
		for f in fl:
			efl.append(f[0]);
			efd[f[0]] = f[1];
		if(tfn not in efl):
			if(y == 0):
				Notepad.open(notepad,tfn);
				Notepad.menuCommand(notepad,10001);
				Notepad.activateBufferID(notepad,cbid);
		else:
			if(y != 0):
				Notepad.menuCommand(notepad,44072); # switch views.
				vbid = Notepad.getCurrentBufferID(notepad);
				if(vbid != efd[tfn]):
					Notepad.activateBufferID(notepad,efd[tfn]);
			else:
				Notepad.activateBufferID(notepad,efd[tfn]);
			ed.setText(txt);
			Notepad.menuCommand(notepad,41006);
			if(y != 0):
				if(vbid != efd[tfn]):
					Notepad.activateBufferID(notepad,vbid);
			Notepad.activateBufferID(notepad,cbid);

action_map["clipboard_list"] = clipboard_list;

def clipboard_up(x=1):
	global ed;
	global icb_max;
	global cb_buff;
	global cb_page;
	global cb_page_bmap;
	global cb_list_flag;
	global internal_cb;
	if((cb_buff - 1) < 0):
		if((icb_max - 1) < 0):
			cb_buff = 0;
			set_cb(internal_cb[cb_buff]);
		else:
			cb_buff = icb_max - 1;
			set_cb(internal_cb[cb_buff]);
	else:
		cb_buff -= 1;
		set_cb(internal_cb[cb_buff]);
	# Save updated position to sqlite3 db.
	cb_page_bmap[cb_page][3] = cb_buff + 1;
	sub = subprocess.Popen(["python","-u",serv_path+"\\clipboard\\cb_client.py",":activebuffid",str(cb_page),":buffer",str(cb_buff+1)],shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);
	try:
		raw = sub.communicate()[0];
		Console.write(console,"buffer position update: [page: "+str(cb_page)+" buffer: "+str(cb_buff+1)+"] "+raw+"\n");
	except:
		pass;
	clipboard_list(cb_list_flag,1);

action_map["clipboard_up"] = clipboard_up;

def clipboard_down(x=1):
	global ed;
	global icb_max;
	global cb_buff;
	global cb_page;
	global cb_page_bmap;
	global cb_list_flag;
	global internal_cb;
	if((cb_buff + 1) >= icb_max):
		cb_buff = 0;
		set_cb(internal_cb[cb_buff]);
	else:
		cb_buff += 1;
		set_cb(internal_cb[cb_buff]);
	# Save updated position to sqlite3 db.
	cb_page_bmap[cb_page][3] = cb_buff + 1;
	sub = subprocess.Popen(["python","-u",serv_path+"\\clipboard\\cb_client.py",":activebuffid",str(cb_page),":buffer",str(cb_buff+1)],shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);
	try:
		raw = sub.communicate()[0];
		Console.write(console,"buffer position update: [page: "+str(cb_page)+" buffer: "+str(cb_buff+1)+"] "+raw+"\n");
	except:
		pass;
	clipboard_list(cb_list_flag,1);

action_map["clipboard_down"] = clipboard_down;

def clipboard_select(x=1):
	global ed;
	global icb_max;
	global cb_buff;
	global cb_page;
	global cb_page_bmap;
	global cb_list_flag;
	global internal_cb;
	try:
		y = int(x) - 1;
		if((y > 0) and (y < icb_max)):
			cb_buff = y;
			set_cb(internal_cb[cb_buff]);
	except:
		pass;
	# Save updated position to sqlite3 db.
	cb_page_bmap[cb_page][3] = cb_buff + 1;
	sub = subprocess.Popen(["python","-u",serv_path+"\\clipboard\\cb_client.py",":activebuffid",str(cb_page),":buffer",str(cb_buff+1)],shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);
	try:
		raw = sub.communicate()[0];
		Console.write(console,"buffer position update: [page: "+str(cb_page)+" buffer: "+str(cb_buff+1)+"] "+raw+"\n");
	except:
		pass;
	clipboard_list(cb_list_flag,1);

action_map["clipboard_select"] = clipboard_select;

def clipboard_auto(x=-1):
	global ed;
	global icb_max;
	global cb_buff;
	global internal_cb;
	global cb_page_auto_detect;
	if(x == 1):
		cb_page_auto_detect = True;
		with open(serv_path+"\\clipboard\\autopage.ini","w+") as f:
			f.write("1");
			f.flush();
	elif(x == 0):
		cb_page_auto_detect = False;
		with open(serv_path+"\\clipboard\\autopage.ini","w+") as f:
			f.write("0");
			f.flush();
	

action_map["clipboard_auto"] = clipboard_auto;

def clipboard_page_list(x=1,y=0):
	global ed;
	global icb_max;
	global cb_buff;
	global internal_cb;
	global serv_path;
	global cb_page_bmap;
	tfn = serv_path+"\\clipboard\\clipboard_page.ini"
	txt = "";
	for k,v in cb_page_bmap.iteritems():
		p = "        ";
		if(k == cb_page):
			p = "[ACTIVE]";
		
		txt = "%s%s%s = %s\n" % (txt,p,k,v[2]);
	
	try:
		with open(tfn,"w+") as f:
			f.write(txt.replace("\r", ""));
			f.flush();
	except:
		pass;
	
	#Console.write(console,txt);
	#print tfn;
	if(x != 1):
		fl = Notepad.getFiles(notepad);
		efl = [];
		efd = {};
		for f in fl:
			efl.append(f[0]);
			efd[f[0]] = f[1];
		if(tfn in efl):
			cbid = Notepad.getCurrentBufferID(notepad);
			Notepad.activateBufferID(notepad,efd[tfn]);
			Notepad.close(notepad);
			Notepad.activateBufferID(notepad,cbid);
			try:
				with open(tfn,"w+") as f:
					f.write("");
					f.flush();
			except:
				pass;
			time.sleep(0.1);
	else:
		cbid = Notepad.getCurrentBufferID(notepad);
		vbid = None;
		fl = Notepad.getFiles(notepad);
		efl = [];
		efd = {};
		for f in fl:
			efl.append(f[0]);
			efd[f[0]] = f[1];
		if(tfn not in efl):
			if(y == 0):
				Notepad.open(notepad,tfn);
				Notepad.menuCommand(notepad,10001);
				Notepad.activateBufferID(notepad,cbid);
		else:
			if(y != 0):
				Notepad.menuCommand(notepad,44072); # switch views.
				vbid = Notepad.getCurrentBufferID(notepad);
				if(vbid != efd[tfn]):
					Notepad.activateBufferID(notepad,efd[tfn]);
			else:
				Notepad.activateBufferID(notepad,efd[tfn]);
			ed.setText(txt);
			Notepad.menuCommand(notepad,41006);
			if(y != 0):
				if(vbid != efd[tfn]):
					Notepad.activateBufferID(notepad,vbid);
			Notepad.activateBufferID(notepad,cbid);

action_map["clipboard_page_list"] = clipboard_page_list;



def inject_doctype(x=-1):
	global ed;
	if(x == 1):
		ed.addText('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">');
	elif(x == 2):
		ed.addText('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">');
	

action_map["inject_doctype"] = inject_doctype;

# ACTIONS END HERE
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

def snippet_display_name_list(txt):
	global ed;
	global serv_path;
	
	filename = serv_path+"\\snippets\\snippet_page.ini"
	with open(filename,"w+") as file_stream:
		file_stream.write(txt);
		file_stream.flush();
	
	filelist = Notepad.getFiles(notepad);
	temp_filelist = [];
	temp_filemap = {};
	for file_object in filelist:
		temp_filelist.append(file_object[0]);
		temp_filemap[file_object[0]] = file_object[1];
	
	if(filename in temp_filelist):
		cbid = Notepad.getCurrentBufferID(notepad);
		Notepad.activateBufferID(notepad,temp_filemap[filename]);
		Notepad.close(notepad);
		Notepad.activateBufferID(notepad,cbid);
		time.sleep(0.1);
	else:
		cbid = Notepad.getCurrentBufferID(notepad);
		Notepad.open(notepad,filename);
		Notepad.menuCommand(notepad,10001);
		Notepad.activateBufferID(notepad,cbid);

def navigate(nav_path):
	global ed;
	global action_map;
	
	ns = nav_path.split(",");
	for x in ns:
		m = x.split(":");
		an = m[0];
		rp = 1;
		if(len(m) > 1):
			try:
				rp = int(m[1]);
			except:
				rp = 1;
		if(an in action_map):
			action_map[an](rp);

def cleaner(_raw):
	global esep;
	ssep = "###)))(((###";
	rez = (False,None);
	raw = "";
	rrr = _raw.split(esep);
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

def format_props(p_raw):
	psep = "###>>><<<###";
	ksep = "###((()))###";
	ps = p_raw.split(psep);
	d = {};
	for p in ps:
		kv = p.split(ksep);
		if((len(kv) < 2) or (kv[0] == "")):
			continue;
		d[kv[0]] = kv[1];
	return d;

def format_msg(data):
	global esep;
	rez = (None,None);
	dsep = "###<<<>>>###";
	ssep = "###)))(((###";
	r = data.split(dsep);
	msg = r[0];
	rl = len(r);
	if((rl < 2)or(r[1] == "")):
		return (msg,{});
	p_raw = r[1];
	"""
	d = {};
	ps = p_raw.split(psep);
	for p in ps:
		kv = p.split(ksep);
		if((len(kv) < 2) or (kv[0] == "")):
			continue;
		d[kv[0]] = kv[1];
	"""
	rez = (msg,format_props(p_raw));
	return rez;

def check_dt_dups():
	now = int(time.time());
	max_diff = 2; # 2 seconds.
	fn = "E:\\usr\\nppserve\\npp_check.txt";
	f = open(fn,"r+");
	x = 0;
	xs = f.readline();
	if(xs != ""):
		x = int(xs);
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

msg_queue = [];

def dragon_thread():
	global ed;
	global is_running;
	global esep;
	global action_map;
	global msg_queue;
	global atom_list;
	global atom_map;
	global bm;
	global auto_lang;
	global serv_path;
	global esep;
	global icb_max;
	global cb_buff;
	global internal_cb;
	global cb_page_map;
	global cb_page_bmap;
	global cb_page_default;
	global cb_page;
	global cb_list_flag;
	global current_lang;
	global dm;
	if(not check_dt_dups()):
		is_running = False;
		return False;
	
	mem_re = re.compile("\|[^|]*\|");
	connav_re = re.compile("\:rp[0-9]+");
	#print "test point 2";
	tmp = "";
	ssep = "###)))(((###";
	Thread(target=dragon_guard_thread).start();
	while(is_running):
		time.sleep(0.05);
		mm = None;
		if(len(msg_queue) > 0):
			mm = msg_queue.pop(0)
		else:
			continue;
		msg = mm[0].replace(ssep,"");
		props = mm[1];
		for k,v in props.iteritems():
			props[k] = v.replace(esep,"");
		
		#print msg, props;
		cln = cur_line_num(ed);
		if(("type" not in props) or (props["type"] == "add_text")):
			indent = "inherit";
			if("indent" in props):
				indent = props["indent"];
			lines = msg.replace("\r","").split("\n");
			prep = "";
			tc = int(ed.getLineIndentation(cln)/4);
			if(indent != "inherit"):
				tc = 0;
			m = "";
			tabs = "\t" * tc;
			sep = "\n%s" % tabs;
			for x in lines:
				m += prep + x;
				prep = sep;
			# Pre-navigation
			if("pre_nav" in props):
				navigate(props["pre_nav"]);
			ed.addText(m);
			# Post-navigation
			if("post_nav" in props):
				navigate(props["post_nav"]);
		elif("type" in props):
			mtype = props["type"];
			if(mtype == "action"):
				m = msg.split(":");
				an = m[0];
				rp = 1;
				if(len(m) > 1):
					try:
						rp = int(m[1]);
					except:
						rp = 1;
				if(an in action_map):
					action_map[an](rp);
			elif(mtype == "memcomplete"):
				try:
					c_lang = current_lang;
					if(c_lang in dm):
						c_lang = dm[c_lang];
					
					indent = "inherit";
					if("indent" in props):
						indent = props["indent"];
					lines = msg.replace("\r","").split("\n");
					prep = "";
					tc = int(ed.getLineIndentation(cln)/4);
					if(indent != "inherit"):
						tc = 0;
					m = "";
					for x in lines:
						m += prep + x;
						prep = "\n" + ("\t" * tc);
					msg = m;
					
					#print msg;
					#Console.write(console,str(bm)+"\n\n\n\n---------\n\n\n");
					buff_id = Notepad.getCurrentBufferID(notepad);
					memtype = [["var"]];
					pre = msg[0];
					if("memtype" in props):
						try:
							mtl = props["memtype"].split("|");
							memtype = [];
							for mt in mtl:
								mtc = mt.split(",");
								mtsl = [];
								memtype.append(mtsl);
								for ms in mtc:
									try:
										n = ms.replace("\n","").replace("\r","").replace("\t","").replace(" ","");
										mtsl.append(n);
									except:
										pass;
							pass;
						except:
							memtype = [["var"]];
					t = msg;
					result = msg;
					tf = mem_re.search(t);
					tfl = [];
					while(tf != None):
						tfl.append(t[(tf.start()+1):(tf.end()-1)]);
						tf = mem_re.search(t,tf.end()+1);
					tfc = len(tfl);
					tmp = None;
					for mt in memtype:
						if(len(mt) == tfc):
							tmp = mt;
							break;
					memtype = tmp;
					
					if((memtype != None) and (tfc > 0)):
						for i in range(0,tfc):
							mt = memtype[i];
							#Console.write(console,str(c_lang)+"\n\n\n-----\n\n");
							#Console.write(console,str(bm[buff_id][c_lang])+"\n====\n\n");
							al = [];
							bl = [];
							try:
								for ax in bm[buff_id][c_lang]["alias"][mt].iterkeys():
									al.append(ax);
									bl.append(ax);
							except:
								pass;
							for ax in bm[buff_id][c_lang][mt]:
								if(ax not in bl):
									bl.append(ax);
							
							tm = tfl;
							m = tm[0];
							z = get_closest_match(m,bl);
							if(z in al):
								z = bm[buff_id][c_lang]["alias"][mt][z];
							tf = mem_re.search(result);
							result = "%s%s%s" % (result[0:tf.start()],z,result[tf.end():]);
							del al;
							del bl;
					else:
						result = get_closest_match(msg,bm[buff_id][c_lang][memtype[0]]);
					"""
					ts = t.split("|");
					result = "";
					if(len(ts) > 2):
						m = ts[1];
						z = get_closest_match(m,bm[buff_id][atom_list[memtype]]);
						result = "%s%s%s" % (ts[0],z,ts[2]);
						#print "TESTING: ", result,"\n\n";
						pre = "";
					else:
						result = get_closest_match(msg,bm[buff_id][atom_list[memtype]]);
					"""
					#result = get_closest_match(msg,bm[buff_id][atom_list[memtype]]);
					#if((memtype == 0) and (pre == "$")):
					#	result = "%s%s" % (pre,result);
					ed.addText(result);
				except:
					pass;
			elif(mtype == "run_program"):
				try:
					nosave = False;
					fn = serv_path + "\\run_code.bat";
					cfn = Notepad.getCurrentFilename(notepad);
					plist = ["start", fn];
					msg = msg.replace(":filename",cfn);
					if(msg.find(":nosave") != -1):
						nosave = True;
						msg = msg.replace(":nosave","");
					if(not nosave):
						Notepad.menuCommand(notepad,41006);
					ms = msg.split(" ");
					for m in ms:
						if((m == None) or (m == "")):
							continue;
						plist.append(m);
					subprocess.Popen(plist, shell = True)
				except:
					pass;
			elif(mtype == "auto_language_detect"):
				try:
					res = -1;
					t = int(msg);
					#print "Auto lang: "+str(t);
					if(t == 1):
						res = t;
						auto_lang = True;
					elif(t == 0):
						rest = t
						auto_lang = False;
					if(t != -1):
						try:
							with open(serv_path+"\\grammar\\autolang.txt","w+") as f:
								f.write(str(res));
								f.flush();
						except:
							pass;
				except:
					pass;
			elif(mtype == "grammar_def"):
				#print "testing\n";
				#tfn = serv_path+"\\__code_utility__";
				tfn = serv_path+"\\grammar\\grammar.ini"
				#print tfn;
				fl = Notepad.getFiles(notepad);
				efl = [];
				efd = {};
				for f in fl:
					efl.append(f[0]);
					efd[f[0]] = f[1];
				if(tfn in efl):
					Notepad.activateBufferID(notepad,efd[tfn]);
					Notepad.close(notepad);
					time.sleep(0.1);
				else:
					cbid = Notepad.getCurrentBufferID(notepad);
					Notepad.open(notepad,tfn);
					Notepad.menuCommand(notepad,10001);
					Notepad.activateBufferID(notepad,cbid);
			elif(mtype == "container_navigation"):
				#print "testing\n";
				#tfn = serv_path+"\\__code_utility__";
				dir = 0;
				x = 1;
				cntype = 0;
				tf = msg.find(":right");
				if(tf != -1):
					dir = 1;
				
				ts = msg.split(" ");
				#Console.write(console,"msg: "+str(msg)+"\n\n");
				try:
					tstype = int(ts[len(ts)-2]);
					cntype = tstype;
				except:
					pass;
				#Console.write(console,"cntype: "+str(cntype)+" : "+str(ts)+"\n\n");
				
				tf = msg.find(":paren");
				if(tf != -1):
					if(dir == 0):
						paren_nav_left(x,cntype);
					else:
						paren_nav_right(x,cntype);
					continue;
				tf = msg.find(":square");
				if(tf != -1):
					if(dir == 0):
						square_nav_left(x,cntype);
					else:
						square_nav_right(x,cntype);
					continue;
				tf = msg.find(":curly");
				tf2 = msg.find(":bracket");
				if((tf != -1)or(tf2 != -1)):
					if(dir == 0):
						curly_nav_left(x,cntype);
					else:
						curly_nav_right(x,cntype);
					continue;
				tf = msg.find(":angle");
				if(tf != -1):
					if(dir == 0):
						angle_nav_left(x,cntype);
					else:
						angle_nav_right(x,cntype);
					continue;
			elif(mtype == "container_navigation_short"):
				#print "testing\n";
				#tfn = serv_path+"\\__code_utility__";
				
				st = "paren";
				if ("subtype" in props):
					st = props["subtype"];
				
				dir = 0;
				if ("direction" in props):
					try:
						nn = int(props["direction"]);
						dir = nn;
					except:
						pass;
				
				x = 1;
				cntype = 0;
				
				xl = connav_re.findall(msg);
				for y in xl:
					try:
						nn = int(y[3:]);
						x = nn;
					except:
						pass;
					break;
				
				ts = msg.split(" ");
				#Console.write(console,"ts: "+str(ts)+"\n\n");
				try:
					tstype = int(ts[len(ts)-2]);
					cntype = tstype;
				except:
					try:
						tstype = int(ts[len(ts)-1]);
						cntype = tstype;
					except:
						pass;
				#Console.write(console,"msg: "+msg+" cntype: "+str(cntype)+" : "+str(st)+" x:"+str(x)+"\n\n");
				
				
				if(st == "paren"):
					if(dir == 0):
						paren_nav_left(x,cntype);
					else:
						paren_nav_right(x,cntype);
					continue;
				if(st == "square"):
					if(dir == 0):
						square_nav_left(x,cntype);
					else:
						square_nav_right(x,cntype);
					continue;
				if(st == "curly"):
					if(dir == 0):
						curly_nav_left(x,cntype);
					else:
						curly_nav_right(x,cntype);
					continue;
				if(st == "angle"):
					if(dir == 0):
						angle_nav_left(x,cntype);
					else:
						angle_nav_right(x,cntype);
					continue;
			elif(mtype == "clipboard_page_manage"):
				#print "testing\n";
				#tfn = serv_path+"\\__code_utility__";
				#tfn = serv_path+"\\clipboard\\clipboard_page.ini"
				#print tfn;
				
				fn = Notepad.getCurrentFilename(notepad);
				tfn = "";
				ms = msg.replace("\r","").replace("\n","").split(" ");
				try:
					m = ms[len(ms)-1];
					if(m == ""):
						m = ms[len(ms)-2];
						if((m[0] == ":") or (m == "")):
							continue;
					tfn = m;
				except:
					pass;
				
				tf = msg.find(":add");
				if(tf != -1):
					try:
						kl = [];
						for k in cb_page_bmap.iterkeys():
							kl.append(k);
						res = get_closest_match(tfn,kl);
						if(res != None):
							mstr = jellyfish.jaro_distance(tfn,res);
							if(mstr >= 0.7):
								Console.write(console,"Clipboard-Page NOT ADDED: "+tfn+"   Match strength ["+str(mstr)+"] too strong to existing page: "+res+"\n");
								continue;
						
						tdir = get_dirname(fn);
						if(tdir == ""):
							Console.write(console,"Clipboard-Page NOT ADDED. No directory??? -- "+fn+":"+tdir+"\n");
							continue;
						tdf = None;
						for k,v in cb_page_bmap.iteritems():
							if(v[2] == tdir):
								tdf = k;
								break;
						if(tdf != None):
							Console.write(console,"Clipboard-Page ["+str(tfn)+"] NOT ADDED. Directory already has a page: -- "+k+":"+tdir+"\n");
							continue;
						# Issue add command to the database via the client script.
						sub = subprocess.Popen(["python","-u",serv_path+"\\clipboard\\cb_client.py",":add",str(tfn),":dir",str(tdir)],shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);
						try:
							sr = sub.communicate()[0];
							if(sr.replace("\n","").replace("\r","") != "Done."):
								Console.write(console,"Clipboard-Page NOT ADDED: -- CB_CLIENT.PY SCRIPT ERROR --\n"+sr);
								continue;
						except:
							Console.write(console,"Clipboard-Page NOT ADDED: == CB_CLIENT.PY SCRIPT ERROR ==");
							continue;
						Console.write(console,"Clipboard-Page Added: "+tfn+"\n");
						cb_page = tfn;
						cb_page_bmap[tfn] = [None,icb_max,tdir,1];
						cb_page_map[tfn] = [""] * icb_max;
						m = cb_page_bmap[tfn];
						internal_cb = cb_page_map[m[0]];
						cb_page = m[0];
						cb_buff = m[3] - 1;
						clipboard_list(cb_list_flag,1);
						clipboard_page_list(1,1);
					except:
						pass;
				
				tf = msg.find(":delete");
				if(tf != -1):
					try:
						kl = [];
						for k in cb_page_bmap.iterkeys():
							kl.append(k);
						res = get_closest_match(tfn,kl);
						if((res == None) or (res == "default")):
							Console.write(console,"No match.\n");
							continue;
						Console.write(console,"Clipboard-Page Deleted: "+res+"\n");
						if(cb_page == res):
							m = cb_page_bmap[cb_page_default];
							internal_cb = cb_page_map[m[0]];
							cb_page = m[0];
							cb_buff = m[3] - 1;
						m = cb_page_bmap[res];
						# Delete local data for the page.
						cb_page_bmap.pop(res);
						cb_page_map.pop(res);
						# Issue delete command to the database via the client script.
						sub = subprocess.Popen(["python","-u",serv_path+"\\clipboard\\cb_client.py",":delete",str(res)],shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);
						try:
							raw = sub.communicate()[0];
							Console.write(console,"Raw: "+str(raw)+"\n");
						except:
							pass;
						clipboard_list(cb_list_flag,1);
						clipboard_page_list(1,1);
					except:
						pass;
				
				tf = msg.find(":goto");
				if(tf != -1):
					try:
						kl = [];
						for k in cb_page_bmap.iterkeys():
							kl.append(k);
						res = get_closest_match(tfn,kl);
						if(res == None):
							Console.write(console,"No match.");
							continue;
						Console.write(console,"Clipboard-Page Selected: "+res+"\n");
						m = cb_page_bmap[res];
						internal_cb = cb_page_map[res];
						cb_page = res;
						cb_buff = m[3] - 1;
						clipboard_list(cb_list_flag,1);
						clipboard_page_list(1,1);
					except:
						pass;

			elif(mtype == "add_snippet"):
				selection_start = ed.getSelectionStart();
				selection_end = ed.getSelectionEnd();
				if(selection_start == selection_end):
					continue; # makes no sense to add an empty snippet.
				
				txt = Editor.getTextRange(editor, selection_start, selection_end);
				txt = txt.replace("'","''");
				
				snippet_db_path = "%s\\snippets\\db\\snippets.sqlite3" % serv_path;
				connection = sqlite3.connect(snippet_db_path);
				cursor = connection.cursor();
				
				snippet_context = current_lang;
				msg_split = msg.split("~~~");
				snippet_name = msg_split[0].replace("_"," ").replace("/","").replace("\\","").replace(":","");
				has_snippet_context = (len(msg_split) > 1) and (msg_split[1].replace(" ","").replace("\t","").replace("\n","") != "");
				
				possible_context_list = ["wildcard"];
				for context in dm.iterkeys():
					possible_context_list.append(context);
				
				if(has_snippet_context):
					snippet_context = msg_split[1];
					# match it to one of the context options.
					closest_context = get_closest_match(snippet_context, possible_context_list);
				
				# ensure this snippet name isn't taken for this context
				sql = "select name from snippet where (context = '%s' or '%s' = 'wildcard') and name = '%s'" % (snippet_context, snippet_context, snippet_name);
				cursor.execute(sql);
				rows = cursor.fetchall();
				snippet_names = []
				for fetched_snippet_name in rows:
					if((fetched_snippet_name[0] != None) and (fetched_snippet_name[0] != "")):
						snippet_names.append(fetched_snippet_name[0].lower());
				
				if(len(snippet_names) > 0):
					continue;
				
				# insert the snippet.
				sql = "insert into snippet (name, content, context) values ('%s', '%s', '%s')" % (snippet_name, txt, snippet_context);
				cursor.execute(sql);
				connection.commit();
				connection.close();
				Console.write(console,"ADD-SNIPPET: %s\n" % snippet_name);
				
			elif(mtype == "inject_snippet"):
				selection_start = ed.getSelectionStart();
				selection_end = ed.getSelectionEnd();
				if(selection_start != selection_end):
					ed.deleteBack();
				
				snippet_db_path = "%s\\snippets\\db\\snippets.sqlite3" % serv_path;
				connection = sqlite3.connect(snippet_db_path);
				cursor = connection.cursor();
				
				msg_split = msg.split("~~~");
				snippet_name = msg_split[0].replace("_"," ").replace("/","").replace("\\","").replace(":","");
				snippet_context = current_lang;
				has_snippet_context = (len(msg_split) > 1) and (msg_split[1].replace(" ","").replace("\t","").replace("\n","") != "");
				
				possible_context_list = ["wildcard"];
				for context in dm.iterkeys():
					possible_context_list.append(context);
				
				if(has_snippet_context):
					snippet_context = msg_split[1];
					# match it to one of the context options.
					closest_context = get_closest_match(snippet_context, possible_context_list);
				
				if(snippet_context == None):
					snippet_context = current_lang;
				
				sql = "select name from snippet where (context = '%s' or '%s' = 'wildcard')" % (snippet_context, snippet_context);
				cursor.execute(sql);
				rows = cursor.fetchall();
				snippet_names = [];
				for fetched_snippet_name in rows:
					if((fetched_snippet_name[0] != None) and (fetched_snippet_name[0] != "")):
						snippet_names.append(str(fetched_snippet_name[0]).lower());
				
				snippet_name = get_closest_match(snippet_name, snippet_names);
				if((snippet_name == None) or (snippet_name == "")):
					continue;
				
				sql = "select content from snippet where (context = '%s' or '%s' = 'wildcard') and name = '%s' limit 1" % (snippet_context, snippet_context, snippet_name);
				
				cursor.execute(sql);
				snippet = "";
				try:
					snippet = cursor.fetchone()[0];
				except:
					continue;
				connection.close();
				Console.write(console,"INJECT-SNIPPET: %s\n" % snippet_name);
				
				if(snippet == None):
					continue;
				
				cln = cur_line_num(ed);
				lines = snippet.replace("\r","").split("\n");
				prep = "";
				tc = int(ed.getLineIndentation(cln)/4);
				m = "";
				tabs = "\t" * tc
				sep = "\n%s" % tabs
				for x in lines:
					m += prep + x;
					prep = sep;
				
				snippet = m;
				ed.addText(snippet);
			
			elif(mtype == "display_snippets"):
				snippet_db_path = "%s\\snippets\\db\\snippets.sqlite3" % serv_path;
				connection = sqlite3.connect(snippet_db_path);
				cursor = connection.cursor();
				
				snippet_context = current_lang;
				has_snippet_context = msg.replace(" ","").replace("\t","").replace("\n","") != "";
				
				possible_context_list = ["wildcard"];
				for context in dm.iterkeys():
					possible_context_list.append(context);
				
				if(has_snippet_context):
					snippet_context = msg;
					# match it to one of the context options.
					closest_context = get_closest_match(snippet_context, possible_context_list);
				
				if(snippet_context == None):
					snippet_context = current_lang;
				
				sql = "select name from snippet where (context = '%s' or '%s' = 'wildcard')" % (snippet_context, snippet_context);
				cursor.execute(sql);
				rows = cursor.fetchall();
				snippet_names = [];
				for fetched_snippet_name in rows:
					if((fetched_snippet_name[0] != None) and (fetched_snippet_name[0] != "")):
						snippet_names.append(str(fetched_snippet_name[0]).lower());
				
				snippet_names.sort();
				
				Console.write(console,"DISPLAY-SNIPPETS: %s\n" % snippet_context);
				
				snippet_display_string = "\n".join(snippet_names);
				snippet_display_name_list(snippet_display_string);
				
				connection.close();
				
	"""
	# Roll out a subprocess for the client process.
	sub = subprocess.Popen(["python","-u","E:\\usr\\nppserve\\npp_client_ka.py"],shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);
	while(is_running):
		time.sleep(0.05);
		#print "Awaiting input...";
		raw = sub.stdout.readline();
		#print "\n---------\n\ninput read: "+str(raw)+"\n\n";
		is_valid, data = cleaner(raw);
		#print str(data);
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
			if("indent" in props):
				indent = props["indent"];
			lines = msg.replace("\r","").split("\n");
			prep = "";
			tc = int(ed.getLineIndentation(cln)/4);
			m = "";
			for x in lines:
				m += prep + x;
				prep = "\n" + ("\t" * tc);
			ed.addText(m);
		elif("type" in props):
			mtype = props["type"];
			if(mtype == "action"):
				m = msg.split(":");
				an = m[0];
				rp = 1;
				if(len(m) > 1):
					try:
						rp = int(m[1]);
					except:
						rp = 1;
				if(an in action_map):
					action_map[an](rp);
		else:
			pass;
	"""
	#print "Exited loop...\n";


def paste_server():
	global end_proc;
	global paste_port;
	global paste_send_port;
	global end_msg;
	global dsep;
	global msg_queue;
	global ksep;
	send_port = paste_send_port;
	UDP_IP = "127.0.0.1"
	UDP_PORT = paste_port;

	r_addr = "";
	r_port = 0;

	sock = socket.socket(socket.AF_INET, # Internet
			     socket.SOCK_DGRAM) # UDP
	sock.bind((UDP_IP, UDP_PORT))

	while True:
		data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
		r_addr = addr[0];
		r_port = addr[1];
		#if(end_proc):
		#	break;
		#if(data == end_msg):
		#	break;
		send_msg("ack",send_port);
		#conn = sqlite3.connect("db\\npp_serve.sqlite3");
		#cur = conn.cursor();
		d_raw = data.split(dsep);
		dat = d_raw[0];
		props = "";
		if(len(d_raw) > 1):
			props = d_raw[1];
		
		#msg_queue.append([dat,props,0]);
		try:
			msg_queue.append([dat,format_props(props),0]);
		except:
			pass;
		#sql = "insert into npp_cmd (data,props,mtype,client_port,client_ip) values (?,?,?,?,?)";
		#prep = [dat,props,0,str(r_port),str(r_addr)];
		#cur.execute(sql,prep);
		#conn.commit();
		#try:
		#	conn.close();
		#except:
		#	pass;
		#sys.stdout.write("PASTE received message:", data, " : ", addr[0], ":",addr[1])
		#sys.stdout.flush()
		#print "PASTE received message:", data, " : ", addr[0], ":",addr[1]

def cmd_server():
	global end_proc;
	global cmd_port;
	global cmd_send_port;
	global end_msg;
	global dsep;
	global ksep;
	send_port = cmd_send_port;
	UDP_IP = "127.0.0.1"
	UDP_PORT = cmd_port;

	r_addr = "";
	r_port = 0;

	sock = socket.socket(socket.AF_INET, # Internet
			     socket.SOCK_DGRAM) # UDP
	sock.bind((UDP_IP, UDP_PORT))

	while True:
		data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
		r_addr = addr[0];
		r_port = addr[1];
		#if(end_proc):
		#	break;
		#if(data == end_msg):
		#	break;
		send_msg("ack",send_port);
		#conn = sqlite3.connect("db\\npp_serve.sqlite3");
		#cur = conn.cursor();
		d_raw = data.split(dsep);
		dat = d_raw[0];
		props = "";
		if(len(d_raw) > 1):
			props = d_raw[1];
		try:
			msg_queue.append([dat,format_props(props),1]);
		except:
			pass;
		#sql = "insert into npp_cmd (data,props,mtype,client_port,client_ip) values (?,?,?,?,?)";
		#prep = [dat,props,1,str(r_port),str(r_addr)];
		#cur.execute(sql,prep);
		#conn.commit();
		#try:
		#	conn.close();
		#except:
		#	pass;
		#print "CMD received message:", data, " : ", addr[0], ":",addr[1]

def send_msg(msg,port):
	UDP_IP = "127.0.0.1"
	UDP_PORT = port
	MESSAGE = msg;

	sock = socket.socket(socket.AF_INET, # Internet
			     socket.SOCK_DGRAM) # UDP
	sock.sendto(MESSAGE, (UDP_IP, UDP_PORT))

def check_eligible_word(w):
	if(len(w) < 1):
		return False;
	"""
	if(len(w) < 2):
		return False;
	"""
	try:
		v = int(w);
		if(str(v) == w):
			return False;
	except:
		pass;

	return True;

def string_remover(txt,rr):
	tmp = txt;
	tmp2 = "";
	for x in rr:
		r = x[0];
		g = r.search(tmp);
		if(g == None):
			continue;
		os = -1;
		oe = -1;
		ns = 0;
		try:
			ns = g.start();
			ne = g.end();
			tmp2 = tmp[0:ns];
			#print tmp[ns:ne];
		except:
			pass;
		while((g != None) and (os != ns)):
			os = ns;
			oe = ne;
			g = r.search(tmp,ne + 1);
			if(g == None):
				break;
			try:
				ns = g.start();
				ne = g.end();
				tmp2 = "%s%s" % (tmp2,tmp[oe:ns]);
				#print tmp[ns:ne];
				#print "  ***>>>"
			except:
				pass;
		tmp2 = "%s%s" % (tmp2,tmp[oe:]);
		tmp = tmp2;
	return tmp;

bm = {};

atom_list = ["var","function","class","token"];
atom_map = {};
lang_list = ["py","php"];

# 'r' | 'u' | 'ur' | 'R' | 'U' | 'UR' | 'Ur' | 'uR'
sr = [['[uUrR]*"""[^"\\\\]*(?:(?:\\\\.|"{1,2}(?!"))[^"\\\\]*)*"""','[uUrR]*"""','"""'],
      ["[uUrR]*'''[^'\\\\]*(?:(?:\\\\.|'{1,2}(?!'))[^'\\\\]*)*'''","[uUrR]*'''","'''"],
      ['[uUrR]*"([^"\\\\]*(?:\\\\.[^"\\\\]*)*)"','[uUrR]*"','"'],
      ["[uUrR]*'([^'\\\\]*(?:\\\\.[^'\\\\]*)*)'","[uUrR]*'","'"]];

ssr = r"""#[.]*""";
py_rr = [];
for x in sr:
	py_rr.append([re.compile(x[0]),re.compile(x[1]),re.compile(x[2])]);
py_rr.append([re.compile(ssr,re.VERBOSE),re.compile(ssr,re.VERBOSE),re.compile(r"""[^.]""",re.VERBOSE)]);

reg_rr = {};
reg_rr["python"] = py_rr;

atom_map["py"] = ["var","function","class","token"];

def parse_py(txt,buff_id):
	global py_rr;
	global atom_list;
	global atom_map;
	global bm;
	lang = "py";
	if(lang not in bm[buff_id]):
		bm[buff_id][lang] = {};
		bm[buff_id][lang]["alias"] = {}
	kw = ['and', 'as', 'assert', 'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except', 'exec', 'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'not', 'or', 'pass', 'print', 'raise', 'return', 'try', 'while', 'with', 'yield'];
	c = "class";
	f = "def";
	

	vd = ["None","True","False"];
	fd = [];
	cd = [];
	tl = [];

	tmp = string_remover(txt,py_rr);
	ss = tmp.split("\n");
	pt = None;
	for x in ss:
		y = re.split("[^a-zA-Z0-9_]{1}",x);
		t = [];
		pt = None;
		for z in y:
			if z != "":
				t.append(z);
				if(pt != None):
					if((pt == f) and (z not in fd)):
						fd.append(z);
					elif((pt == c) and (z not in cd)):
						cd.append(z);
				if((z not in tl) and (z not in kw)):
					tl.append(z);
				pt = z;
	for x in tl:
		if((x not in fd) and (x not in cd) and (x not in vd) and check_eligible_word(x)):
			vd.append(x);
	
	cm = {"var":vd,"function":fd,"class":cd,"token":tl};
	if(lang in atom_map):
		for x in atom_map[lang]:
			if(x in cm):
				bm[buff_id][lang][x] = cm[x];


php_sr = [['"([^"\\\\]*(?:\\\\.[^"\\\\]*)*)"','[uUrR]*"','"'],
	  ["'([^'\\\\]*(?:\\\\.[^'\\\\]*)*)'","[uUrR]*'","'"]];
ssr = r"""/ \*(([^*])|(\* [^/]))*\* /""";
ssr2 = r"""//[.]*""";
php_rr = [];
for x in php_sr:
	php_rr.append([re.compile(x[0]),re.compile(x[1]),re.compile(x[2])]);
php_rr.append([re.compile(ssr,re.VERBOSE),re.compile(r"""/ \*""",re.VERBOSE),re.compile(r"""\* /""",re.VERBOSE)]);
php_rr.append([re.compile(ssr2,re.VERBOSE),re.compile(ssr2,re.VERBOSE),re.compile(r"""[^.]""",re.VERBOSE)]);
reg_rr["php"] = php_rr;

atom_map["php"] = ["var","function","class","token"];

def parse_php(txt,buff_id):
	global php_rr;
	global atom_list;
	global atom_map;
	global bm;
	lang = "php";
	if(lang not in bm[buff_id]):
		bm[buff_id][lang] = {};
		bm[buff_id][lang]["alias"] = {}
	kw = ['__halt_compiler', 'abstract', 'and', 'array', 'as', 'break', 'callable', 'case', 'catch', 'class', 'clone', 'const', 'continue', 'declare', 'default', 'die', 'do', 'echo', 'else', 'elseif', 'empty', 'enddeclare', 'endfor', 'endforeach', 'endif', 'endswitch', 'endwhile', 'eval', 'exit', 'extends', 'final', 'for', 'foreach', 'function', 'global', 'goto', 'if', 'implements', 'include', 'include_once', 'instanceof', 'insteadof', 'interface', 'isset', 'list', 'namespace', 'new', 'or', 'print', 'private', 'protected', 'public', 'require', 'require_once', 'return', 'static', 'switch', 'throw', 'trait', 'try', 'unset', 'use', 'var', 'while', 'xor'];
	c = "class";
	f = "function";
	# 'r' | 'u' | 'ur' | 'R' | 'U' | 'UR' | 'Ur' | 'uR'
	
	vd = ["null","true","false"];
	fd = [];
	cd = [];
	tl = [];
	
	tmp = string_remover(txt,php_rr);
	ss = tmp.split("\n");
	pt = None;
	for x in ss:
		y = re.split("[^a-zA-Z0-9_]{1}",x);
		t = [];
		pt = None;
		for z in y:
			if z != "":
				t.append(z);
				if(pt != None):
					if((pt == f) and (z not in fd)):
						fd.append(z);
					elif((pt == c) and (z not in cd)):
						cd.append(z);
				if((z not in tl) and (z not in kw)):
					tl.append(z);
				pt = z;
	for x in tl:
		if((x not in fd) and (x not in cd) and (x not in vd) and check_eligible_word(x)):
			vd.append(x);
	cm = {"var":vd,"function":fd,"class":cd,"token":tl};
	#Console.write(console,"php parse:\n------\n\n"+str(tmp)+"\n\n\n");
	if(lang in atom_map):
		for x in atom_map[lang]:
			if(x in cm):
				bm[buff_id][lang][x] = cm[x];
	#for x in atom_list:
	#	bm[buff_id][lang][x] = cm[x];
	"""
	print "Vars:\n-------\n","\n".join(vd),"\n\n\nFunctions:\n-------\n","\n".join(fd),"\n\n\nClasses:\n---------\n","\n".join(cd);
	"""

# how many memtypes for html? 
#    4 
# What are they?
# 0)tag 1)attr 2)class 3)id
id_r = "%s|%s" % ('(id="([^"\\\\]*(?:\\\\.[^"\\\\]*)*)")',"(id='([^'\\\\]*(?:\\\\.[^'\\\\]*)*)')");
name_r = "%s|%s" % ('(name="([^"\\\\]*(?:\\\\.[^"\\\\]*)*)")',"(name='([^'\\\\]*(?:\\\\.[^'\\\\]*)*)')");
class_r = "%s|%s" % ('(class="([^"\\\\]*(?:\\\\.[^"\\\\]*)*)")',"(class='([^'\\\\]*(?:\\\\.[^'\\\\]*)*)')");
html_sr = [
	  [id_r,'.','.'],
	  [name_r,'.','.'],
      [class_r,".","."],
];
html_rr = [];
for x in html_sr:
	html_rr.append([re.compile(x[0]),re.compile(x[1]),re.compile(x[2])]);

reg_rr["html"] = html_rr;

atom_map["html"] = ["tagname","attribute","css_class","id","name"];

def parse_html(txt,buff_id):
	global html_rr;
	global atom_list;
	global atom_map;
	global bm;
	lang = "html";
	if(lang not in bm[buff_id]):
		bm[buff_id][lang] = {};
		bm[buff_id][lang]["alias"] = {}
	
	va = {"anchor":"a","unordered":"ul","ordered":"ol","listitem":"li","image":"img","panel":"div","row":"tr","column":"td","tablerow":"tr"};
	vd = ["div","a","li","html","body","head","title","table","tr","td","input","textarea","button","iframe","ul","li","img","meta","script","span","label"]; # tag name
	
	fa = {"linkref":"href","reference":"href","relative":"rel","source":"src"};
	fd = ["width","height","style","onclick","href","rel","class","id","src","type"]; # attribute
	cd = []; # css class
	tl = []; # id
	nl = []; # name
	
	id_r = html_rr[0][0];
	name_r = html_rr[1][0];
	class_r = html_rr[2][0];
	
	tmp = id_r.search(txt);
	while(tmp != None):
		ss = tmp.start();
		se = tmp.end();
		raw = txt[ss+4:se-1];
		if(raw not in tl):
			tl.append(raw);
		tmp = id_r.search(txt,se+1);
	
	tmp = name_r.search(txt);
	while(tmp != None):
		ss = tmp.start();
		se = tmp.end();
		raw = txt[ss+6:se-1];
		if(raw not in nl):
			nl.append(raw);
		tmp = name_r.search(txt,se+1);
	
	tmp = class_r.search(txt);
	while(tmp != None):
		ss = tmp.start();
		se = tmp.end();
		raw = txt[ss+7:se-1];
		y = re.split("[^a-zA-Z0-9_]{1}",raw);
		for x in y:
			if((x != "") and (x not in cd)):
				cd.append(x);
		tmp = class_r.search(txt,se+1);
	cm = {"tagname":vd,"attribute":fd,"css_class":cd,"id":tl,"name":nl};
	ca = {"tagname":va,"attribute":fa,"css_class":{},"id":{},"name":{}};
	#for x in atom_list:
	#	bm[buff_id][lang][x] = cm[x];
	#	bm[buff_id][lang]["alias"][x] = ca[x];
	
	if(lang in atom_map):
		for x in atom_map[lang]:
			if(x in cm):
				bm[buff_id][lang][x] = cm[x];
				bm[buff_id][lang]["alias"][x] = ca[x];

xml_sr = [
	  [id_r,'.','.'],
	  [name_r,'.','.'],
      [class_r,".","."],
];
xml_rr = [];
for x in xml_sr:
	xml_rr.append([re.compile(x[0]),re.compile(x[1]),re.compile(x[2])]);

reg_rr["xml"] = xml_rr;

atom_map["xml"] = ["tagname","attribute","css_class","id","name"];

def parse_xml(txt,buff_id):
	global xml_rr;
	global atom_list;
	global atom_map;
	global bm;
	lang = "xml";
	if(lang not in bm[buff_id]):
		bm[buff_id][lang] = {};
		bm[buff_id][lang]["alias"] = {}
	
	va = {};
	vd = []; # tag name
	
	fa = {"linkref":"href","reference":"href","relative":"rel","source":"src"};
	fd = ["width","height","style","href","rel","class","id","src","type"]; # attribute
	cd = []; # css class
	tl = []; # id
	nl = []; # name
	
	id_r = html_rr[0][0];
	name_r = html_rr[1][0];
	class_r = html_rr[2][0];
	
	tmp = id_r.search(txt);
	while(tmp != None):
		ss = tmp.start();
		se = tmp.end();
		raw = txt[ss+4:se-1];
		if(raw not in tl):
			tl.append(raw);
		tmp = id_r.search(txt,se+1);
	
	tmp = name_r.search(txt);
	while(tmp != None):
		ss = tmp.start();
		se = tmp.end();
		raw = txt[ss+6:se-1];
		if(raw not in nl):
			nl.append(raw);
		tmp = name_r.search(txt,se+1);
	
	tmp = class_r.search(txt);
	while(tmp != None):
		ss = tmp.start();
		se = tmp.end();
		raw = txt[ss+7:se-1];
		y = re.split("[^a-zA-Z0-9_]{1}",raw);
		for x in y:
			if((x != "") and (x not in cd)):
				cd.append(x);
		tmp = class_r.search(txt,se+1);
	
	try:
		xml = etree.XML(txt);
		for c in xml.xpath("//*"):
			if(c.tag not in vd):
				vd.append(c.tag);
	except:
		pass;
	
	cm = {"tagname":vd,"attribute":fd,"css_class":cd,"id":tl,"name":nl};
	ca = {"tagname":va,"attribute":fa,"css_class":{},"id":{},"name":{}};
	#for x in atom_list:
	#	bm[buff_id][lang][x] = cm[x];
	#	bm[buff_id][lang]["alias"][x] = ca[x];
	
	if(lang in atom_map):
		for x in atom_map[lang]:
			if(x in cm):
				bm[buff_id][lang][x] = cm[x];
				bm[buff_id][lang]["alias"][x] = ca[x];

css_sr = [
	  ["",'.','.'],
      ["",".","."],
];
css_rr = [];
for x in css_sr:
	html_rr.append([re.compile(x[0]),re.compile(x[1]),re.compile(x[2])]);

reg_rr["css"] = css_rr;

atom_map["css"] = ["tagname","property","value","css_class","id","pseudo"];
tcss_parser = tinycss.make_parser("page3");

def parse_css(txt,buff_id):
	global css_rr;
	global atom_list;
	global bm;
	global tcss_parser;
	lang = "css";
	if(lang not in bm[buff_id]):
		bm[buff_id][lang] = {};
		bm[buff_id][lang]["alias"] = {}
	
	ta = {"anchor":"a","unordered":"ul","ordered":"ol","listitem":"li","image":"img","panel":"div","row":"tr","column":"td","tablerow":"tr"};
	td = ["div","a","li","html","body","head","title","table","tr","td","input","textarea","button","iframe","ul","li","img","meta","script","span","label"]; # tag name
	
	aa = {};
	ad = ["width","height","min-width","min-height","float","clear","position","background","background-color","background-repeat","background-position","border","border-top","border-right","border-bottom","border-left","margin","margin-top","margin-right","margin-bottom","margin-left","padding","padding-top","padding-right","padding-bottom","padding-left","line-height","font","font-family","font-style","font-size","font-weight","text-decoration","color","cursor","text-shadow","display","vertical-align","display","list-style-type"]; # style property
	va = {};
	vd = ["Arial", "Helvetica", "sans-serif", "left", "center", "right", "auto", "bold", "none", "no-repeat","repeat-x","repeat-y","repeat","top","url()","solid","!important","block","disc","inline","underline","italic","both","relative","absolute","decimal","pointer"]; # property value
	cd = []; # css class
	tl = []; # id
	pl = ["active","visited","hover","focus","first-letter","first-line","first-child","before","after"]; # pseudo
	
	#parse out all the rules, collecting IDs and class names along the way.
	p = tcss_parser.parse_stylesheet(txt);
	mod = None;
	for x in p.rules:
		for y in x.selector:
			try:
				if((y.type.lower() == "ident")and(mod != None)):
					mod = None;
					v = y.value;
					if(mod == 0):
						if(v not in tl):
							tl.append(v);
					elif(mod == 1):
						if(v not in cd):
							cd.append(v);
				elif(y.value == "#"):
					mod = 0;
				elif(y.value == "."):
					mod = 1;
				else:
					mod = None;
			except:
				pass;
		
	
	cm = {"tagname":td,"property":ad,"value":vd,"css_class":cd,"id":tl,"pseudo":pl};
	ca = {"tagname":ta,"property":aa,"value":va,"css_class":{},"id":{},"pseudo":{}};
	#for x in atom_list:
	#	bm[buff_id][lang][x] = cm[x];
	#	bm[buff_id][lang]["alias"][x] = ca[x];
	
	if(lang in atom_map):
		for x in atom_map[lang]:
			if(x in cm):
				bm[buff_id][lang][x] = cm[x];
				bm[buff_id][lang]["alias"][x] = ca[x];

js_sr = [['"([^"\\\\]*(?:\\\\.[^"\\\\]*)*)"','',''],
	  ["'([^'\\\\]*(?:\\\\.[^'\\\\]*)*)'","",""]];
ssr = r"""/ \*(([^*])|(\* [^/]))*\* /""";
ssr2 = r"""//[.]*""";
js_rr = [];
for x in js_sr:
	js_rr.append([re.compile(x[0]),re.compile(x[1]),re.compile(x[2])]);
js_rr.append([re.compile(ssr,re.VERBOSE),re.compile(r"""/ \*""",re.VERBOSE),re.compile(r"""\* /""",re.VERBOSE)]);
js_rr.append([re.compile(ssr2,re.VERBOSE),re.compile(ssr2,re.VERBOSE),re.compile(r"""[^.]""",re.VERBOSE)]);
reg_rr["javascript"] = js_rr;

atom_map["js"] = ["var","function","class","token"];

def parse_js(txt,buff_id):
	global js_rr;
	global atom_list;
	global atom_map;
	global bm;
	lang = "js";
	if(lang not in bm[buff_id]):
		bm[buff_id][lang] = {};
	
	kw = ["break","case","catch","continue","debugger","default","delete","do","else","finally","for","function","if","in","instanceof","new","return","switch","this","throw","try","typeof","var","void","while","with"];
	f = "function";
	
	vd = ["null","true","false"];
	fd = [];
	cd = [];
	tl = [];
	
	tmp = string_remover(txt,js_rr);
	ss = tmp.split("\n");
	pt = None;
	for x in ss:
		y = re.split("[^a-zA-Z0-9_]{1}",x);
		t = [];
		pt = None;
		for z in y:
			if z != "":
				t.append(z);
				if(pt != None):
					if((pt == f) and (z not in fd)):
						fd.append(z);
				if((z not in tl) and (z not in kw)):
					tl.append(z);
				pt = z;
	for x in tl:
		if((x not in fd) and (x not in cd) and (x not in vd) and check_eligible_word(x)):
			vd.append(x);
	cm = {"var":vd,"function":fd,"class":cd,"token":tl};
	
	#Console.write(console,str(cm)+"\n\n\n~~~~~~\n"+str(buff_id)+"\n~~~~~~\n\n");
	if(lang in atom_map):
		for x in atom_map[lang]:
			if(x in cm):
				bm[buff_id][lang][x] = cm[x];

cpp_sr = [['"([^"\\\\]*(?:\\\\.[^"\\\\]*)*)"','[uUrR]*"','"'],
	  ["'([^'\\\\]*(?:\\\\.[^'\\\\]*)*)'","[uUrR]*'","'"]];
ssr = r"""/ \*(([^*])|(\* [^/]))*\* /""";
ssr2 = r"""//[.]*""";
cpp_rr = [];
for x in cpp_sr:
	cpp_rr.append([re.compile(x[0]),re.compile(x[1]),re.compile(x[2])]);
cpp_rr.append([re.compile(ssr,re.VERBOSE),re.compile(r"""/ \*""",re.VERBOSE),re.compile(r"""\* /""",re.VERBOSE)]);
cpp_rr.append([re.compile(ssr2,re.VERBOSE),re.compile(ssr2,re.VERBOSE),re.compile(r"""[^.]""",re.VERBOSE)]);
reg_rr["c"] = php_rr;

atom_map["c"] = ["var","function","class","token"];

def parse_cpp(txt,buff_id):
	global cpp_rr;
	global atom_list;
	global atom_map;
	global bm;
	lang = "c";
	if(lang not in bm[buff_id]):
		bm[buff_id][lang] = {};
		bm[buff_id][lang]["alias"] = {}
	kw = ['alignas', 'alignof', 'and', 'and_eq', 'asm', 'auto', 'bitand', 'bitor', 'bool', 'break', 'catch', 'char', 'char16_t', 'char32_t', 'class', 'compl', 'const', 'constexpr', 'const_cast', 'continue', 'decltype', 'default', 'delete', 'do', 'double', 'dynamic_cast', 'else', 'enum', 'explicit', 'export', 'extern', 'float', 'for', 'friend', 'goto', 'if', 'int', 'long', 'mutable', 'namespace', 'new', 'noexcept', 'not', 'not_eq', 'nullptr', 'namespace', 'new', 'operator', 'or', 'or_eq', 'private', 'protected', 'public', 'register', 'reinterpret_cast', 'return', 'short', 'signed', 'sizeof', 'static', 'static_assert', 'static_cast', 'struct', 'switch', 'template', 'this', 'thread_local', 'throw', 'true', 'try', 'typedef', 'typeid', 'typename', 'union', 'unsigned', 'using', 'virtual', 'void', 'volatile', 'wchar_t', 'while', 'xor', 'xor_eq'];
	c = "class";
	f = "";
	# 'r' | 'u' | 'ur' | 'R' | 'U' | 'UR' | 'Ur' | 'uR'
	
	vd = ["null","true","false"];
	fd = [];
	cd = [];
	tl = [];
	
	tmp = string_remover(txt,php_rr);
	ss = tmp.split("\n");
	pt = None;
	for x in ss:
		y = re.split("[^a-zA-Z0-9_]{1}",x);
		t = [];
		pt = None;
		for z in y:
			if z != "":
				t.append(z);
				if(pt != None):
					#if((pt == f) and (z not in fd)):
					#	fd.append(z);
					if((pt == c) and (z not in cd)):
						cd.append(z);
				if((z not in tl) and (z not in kw)):
					tl.append(z);
				pt = z;
	for x in tl:
		if((x not in fd) and (x not in cd) and (x not in vd) and check_eligible_word(x)):
			vd.append(x);
	cm = {"var":vd,"function":fd,"class":cd,"token":tl};
	#Console.write(console,"php parse:\n------\n\n"+str(tmp)+"\n\n\n");
	if(lang in atom_map):
		for x in atom_map[lang]:
			if(x in cm):
				bm[buff_id][lang][x] = cm[x];

def in_range(range_list,start,end):
	for r in range_list:
		if(((r[0] <= start)and(r[1] >= start)) or ((start <= r[0])and(end >= r[0])) or (start == r[0]) or (end == r[1])):
			return True;
	return False;

def isolate_source(src,ttype,targ_rr,tag_list=[["<?php","?>"]],cpos=0):
	result = "";
	range_list = [];
	type = ttype;
	# Get ranges at which excluded elements (regexes in targ_rr) occur
	for r in targ_rr:
		tr = [];
		st = 0;
		os = -1;
		while((os != st)):
			os = st;
			s = r[0].search(src,st);
			if(s == None):
				break;
			st = s.end()+1;
			tr.append([s.start(),s.end()]);
		# merge the ranges.
		tx = [];
		for x in tr:
			found = False;
			for y in range_list:
				# if ranges overlap, combine them.
				if(((x[0] <= y[0])and(x[1] >= y[0])) or ((y[0] <= x[0])and(y[1] >= x[0])) or (y[0] == x[0]) or (y[1] == x[1])):
					xs = x[0];
					if(y[0] < x[0]):
						xs = y[0];
					xe = x[1];
					if(y[1] > x[1]):
						xe = y[1];
					y[0] = xs;
					y[1] = xe;
					found = True;
					break;
			if(not found):
				tx.append(x);
		for x in tx:
			range_list.append(x);
	tg_range = [];
	src_len = len(src);
	for tg in tag_list:
		ts = 0;
		tgm = 0;
		tgl = [len(tg[0]),len(tg[1])];
		tmp = src.find(tg[tgm]);
		while(tmp != -1):
			# check if tmp falls within the range of excluded elements (e.g. strings and comments).
			if(not in_range(range_list,tmp,tmp+tgl[tgm])):
				if(tgm == 0):
					tgm = 1;
					ts = tmp;
				else:
					tgm = 0;
					tg_range.append([ts,tmp + tgl[1]]);
			tmp = src.find(tg[tgm],tmp+tgl[tgm]);
		if((tgm == 1) and (ts != src_len)):
			tg_range.append([ts,src_len]);
			
	# Sort the script region occurrences. Assuming no overlap, as there should be none.
	t_range = [];
	for t in tg_range:
		pos = len(t_range);
		for i in range(0,pos):
			y = t_range[i];
			if(y[0] >= t[0]):
				pos = i;
				break;
		t_range.insert(pos,t);
	# If type == 0, then remove the script regions. else, remove the external regions.
	#    Remove without affecting char/line count
	if(type == 2):
		type = 0;
		for x in t_range:
			if((cpos >= x[0]) and (cpos < x[1])):
				type = 1;
				break;
	if(type == 0):
		result = src;
		while(len(t_range) > 0):
			t = t_range[0];
			t_range.pop(0);
			tl = t[1] - t[0];
			# re.sub(r"[^\n]{1}",r"-",s);
			result = "%s%s%s" % (result[0:t[0]],re.sub(r"[^\n]{1}",r" ",result[t[0]:t[1]]),result[t[1]:]);
			#result = "%s%s" % (result[0:t[0]],result[t[1]:]);
			#for x in t_range:
			#	x[0] -= tl;
			#	x[1] -= tl;
	else:
		# Reverse the ranges.
		x_range = [];
		ts = 0;
		sl = len(src);
		for t in t_range:
			if(ts < (t[0]-1)):
				x_range.append([ts,t[0]-1]);
			ts = t[1];
		if(ts < sl):
			x_range.append([ts,sl]);
		result = src;
		while(len(x_range) > 0):
			t = x_range[0];
			x_range.pop(0);
			tl = t[1] - t[0];
			result = "%s%s%s" % (result[0:t[0]],re.sub(r"[^\n]{1}",r" ",result[t[0]:t[1]]),result[t[1]:]);
			#result = "%s%s" % (result[0:t[0]],result[t[1]:]);
			#for x in x_range:
			#	x[0] -= tl;
			#	x[1] -= tl;
		pass;
	return (type,result.replace("\r"," "));

def trim_lead(s,delim):
	d = delim;
	sl = len(s);
	for i in range(0,sl):
		x = s[i];
		if(x not in delim):
			return s[i:];
	return None;
	
global err_msg;
err_msg = "";
def get_tag_range_list(src,type=0,cpos=0):
	global err_msg;
	xml = None;
	# HTML
	ttype = 0; # xml
	tags = ["script","style"];
	html_range = ["html","div","p","span","tr","td","table"];
	tsrc = src;
	try:
		#Console.write(console,src);
		tsrc = src.replace("<?php","     ").replace("?>","  ").replace("&nbsp;","      ");
		xml = etree.XML(tsrc);
	except Exception as e:
		err_msg = "%s\n" % e;
		#Console.write(console,"ERROR:"+err_msg+"\n");
		success = False;
		try:
			xml = etree.HTML(tsrc);
			success = True;
		except:
			pass;
		if(not success):
			try:
				tsrc = trim_lead(tsrc,[" ","\t","\n","\r"]);
				xml = etree.XML(tsrc);
				if(xml.tag.lower() not in html_range):
					return 0;
				else:
					return -1;
			except:
				return -1;
			return -1; # failure
	try:
		if(xml.tag.lower() in html_range):
			ttype = 1; # html
		else:
			return 0;
	except:
		return 0;
	range_list = [];
	try:
		for tagname in tags:
			x_range = [];
			range_list.append(x_range);
			ti = xml.getiterator(tagname);
			ssp = src.split("\n");
			for t in ti:
				sl = t.sourceline;
				# Now find where the tag ends...
				#   Pattern: iterate siblings, move up to parent, repeat until found or docroot (use end of file).
				tmp = t.getparent();
				ln = None;
				lns = 0;
				x = 0;
				for i in range(0,sl-1):
					if(i >= len(ssp)):
						x = len(src);
						break;
					x += len(ssp[i]) + 1;
				ln2 = x;
				ssf = src.find(tagname,ln2);
				ssf = src.find(">",ssf);
				if(type == 1):
					if(ssf > cpos):
						break; # Not in range. Try the next tag.
				while(tmp != None):
					si = t.itersiblings();
					for x in si:
						ln = x.sourceline;
						break;
					if(ln != None):
						break;
					tmp = tmp.getparent();
				if(ln == None):
					ln = len(src);
				else:
					x = 0;
					for i in range(0,ln-1):
						if(i >= len(ssp)):
							x = len(src);
							break;
						if(len(tmp) > i):
							x += len(tmp[i]) + 1;
					ln = x;
				loc = ssf+(src[ssf:ln].rfind(tagname) - 1);
				if(type == 1):
					if((cpos >= ssf) and (cpos < loc)):
						return tagname;
				x_range.append([ssf,loc]);
		if(type == 1):
			return None;
	except Exception as e:
		err_msg = "[Line #%s]: %s\n" % (str(traceback.tb_lineno(sys.exc_traceback)),e);
		if(type == 1):
			return None;
		return -1;
	return range_list;

current_buffid = None; #Notepad.getCurrentBufferID(notepad);
try:
	f = open(serv_path+"\\grammar\\autolang.txt","r+");
	line = f.readline();
	f.close();

	line = line.replace("\r","").replace("\n","");
	if int(line) != 1:
		auto_lang = False;
except:
	try:
		f = open(serv_path+"\\grammar\\autolang.txt","r+");
		f.write("1");
		f.flush();
		f.close();
	except:
		pass;

def auto_lang_detect():
	global current_buffid;
	global auto_lang;
	global lang_list;
	global reg_rr;
	global current_lang;
	global serv_path;
	global err_msg;
	default_lang = "python";
	cbid = Notepad.getCurrentBufferID(notepad);
	ext = None;
	d = {"python":["py"],"php":["php"],"html":["html","htm"],"css":["css"],"javascript":["js"],"xml":["xml"],"c":["cpp","c","h","hpp"]};
	ml = {"php":[["<?php","?>"],["<?","?>"]]};
	cur_lang = default_lang;
	
	first_time = (current_buffid != cbid);
	fn = Notepad.getCurrentFilename(notepad);
	fns = fn.split(".");
	fnsl = len(fns);
	current_buffid = cbid;
	if(fnsl < 2):
		ext = default_lang;
	else:
		ext = fns[fnsl-1];
		found = False;
		for k in d:
			if(ext in d[k]):
				found = True;
				ext = k;
				break;
		if(not found):
			ext = default_lang;
	
	src_lt = [];
	# Check the caret position for mixed language files (e.g. PHP files often contain html)
	if((ext in ml) and (ext in reg_rr)):
		cpos = ed.getCurrentPos();
		src = editor.getText();
		type = 0;
		iso_src = "";
		type, iso_src = isolate_source(src,2,reg_rr[ext],ml[ext],cpos);
		#if(first_time):
		#	Console.write(console,str((type,iso_src)));
		if(type == 1): # Script [internal primary language]
			src_lt.append([ext,iso_src]);
			# Get external source.
			type, ext_src = isolate_source(src,0,reg_rr[ext],ml[ext]);
			# Dissect it for inline CSS and JavaScript if it's HTML.
			rng_lt = get_tag_range_list(ext_src);
			if(rng_lt == 0):
				src_lt.append(["xml",ext_src]);
			elif(rng_lt == -1):
				if(first_time):
					#Console.write(console,"[PHP] Not XML\n-----\n");
					with open(serv_path+"\\x1.xml","w+") as f:
						f.write(ext_src);
						f.flush();
					with open(serv_path+"\\x2.xml","w+") as f:
						f.write(iso_src);
						f.flush();
				pass; # nothing... neither xml nor html.
			else:
				ss = "";
				res_src = ext_src;
				
				for x in rng_lt[0]:
					ss = "%s\n%s" % (ss,ext_src[x[0]:x[1]]);
					res_src = "%s%s%s" % (res_src[0:x[0]], re.sub(r"[^\n]{1}",r" ",res_src[x[0]:x[1]]), res_src[x[1]:]);
				if(ss != ""):
					src_lt.append(["javascript",ss]);
				ss = "";
				for x in rng_lt[1]:
					ss = "%s\n%s" % (ss,ext_src[x[0]:x[1]]);
					res_src = "%s%s%s" % (res_src[0:x[0]], re.sub(r"[^\n]{1}",r" ",res_src[x[0]:x[1]]), res_src[x[1]:]);
				if(ss != ""):
					src_lt.append(["css",ss]);
				src_lt.append(["html",res_src]);
		else: # external language (e.g. html)
			# Get internal source.
			type, int_src = isolate_source(src,1,reg_rr[ext],ml[ext]);
			src_lt.append([ext,int_src]);
			ext_src = iso_src;
			rng_lt = get_tag_range_list(iso_src);
			t_ext = "html";
			#if(first_time):
			#	pass;
				#Console.write(console,"[EXTERNAL] XML CHECK:\n"+str(rng_lt)+"\n\n\n");#+str(iso_src);
				#etree.XML(trim_lead(iso_src," "));
			if(rng_lt == 0):
				src_lt.append(["xml",ext_src]);
				t_ext = "xml";
			elif(rng_lt == -1):
				if(first_time):
					Console.write(console,"[EXTERNAL] Not XML!\n"+err_msg);
					"""
					with open(serv_path+"\\x1.xml","w+") as f:
						f.write(iso_src.replace("<?php","     ").replace("?>","  ").replace("&nbsp;","      "));
						f.flush();
					with open(serv_path+"\\x1.xml","w+") as f:
						f.write(ext_src);
						f.flush();
					with open(serv_path+"\\x2.xml","w+") as f:
						f.write(int_src);
						f.flush();
					"""
					pass;
				pass; # nothing... neither xml nor html.
			else:
				ss = "";
				res_src = ext_src;
				for x in rng_lt[0]:
					ss = "%s\n%s" % (ss,ext_src[x[0]:x[1]]);
					res_src = "%s%s%s" % (res_src[0:x[0]], re.sub(r"[^\n]{1}",r" ",res_src[x[0]:x[1]]), res_src[x[1]:]);
				if(ss != ""):
					src_lt.append(["javascript",ss]);
				ss = "";
				for x in rng_lt[1]:
					ss = "%s\n%s" % (ss,ext_src[x[0]:x[1]]);
					res_src = "%s%s%s" % (res_src[0:x[0]], re.sub(r"[^\n]{1}",r" ",res_src[x[0]:x[1]]), res_src[x[1]:]);
				if(ss != ""):
					src_lt.append(["css",ss]);
				src_lt.append(["html",res_src]);
			
			# detect language.
			res = get_tag_range_list(iso_src,1,cpos);
			if(res == -1):
				#Console.write(console,"[EXTERNAL] CHECK: ["+str(res)+"] FOUND\n");
				pass;
			if(res == "script"):
				ext = "javascript";
				#Console.write(console,"[EXTERNAL] JAVASCRIPT FOUND\n");#+str(iso_src);
			elif(res == "style"):
				ext = "css";
			else:
				ext = "html";
				if(t_ext == "xml"):
					ext = "xml";
	elif(ext == "html"):
		# detect language.
		cpos = ed.getCurrentPos();
		txt = editor.getText();
		res = get_tag_range_list(txt,1,cpos);
		if(res == "script"):
			ext = "javascript";
		elif(res == "style"):
			ext = "css";
		else:
			ext = "html";
		src_lt.append([ext,txt]);
	else:
		src_lt.append([ext,editor.getText()]);
		pass;
	
	if(auto_lang):# and (current_buffid != cbid)):
		try:
			#Console.write(console,"Switch to: "+str(ext)+"\n");
			if(ext != current_lang):
				current_lang = ext;
				Console.write(console,"Switch to: "+str(ext)+"\n");
				with open(serv_path+"\\grammar\\context.txt","w+") as f:
					f.write(ext);
					f.flush();
		except:
			pass;
	return src_lt;

dm = {"python":"py","php":"php","html":"html","css":"css","javascript":"js","xml":"xml","c":"cpp"};
def memcomplete():
	global buffid_list;
	global lang_list;
	global atom_list;
	global atom_map;
	global m_vd;
	global m_fd;
	global m_cd;
	global m_tl;
	global dm;
	default_lang = "php";
	d = {"py":parse_py,"php":parse_php,"html":parse_html,"css":parse_css,"js":parse_js,"xml":parse_xml,"cpp":parse_cpp};
	ext = None;
	while(True):
		time.sleep(0.5);
		cbid = Notepad.getCurrentBufferID(notepad);
		src_lt = auto_lang_detect();
		fl = Notepad.getFiles(notepad);
		buff_list = [];
		
		for f in fl:
			fn = f[0];
			buff_id = f[1];
			if(buff_id not in buff_list):
				buff_list.append(buff_id);
			buff_index = f[2];
			buff_side = f[3];
			fns = fn.split(".");
			fnsl = len(fns);
			if(fnsl < 2):
				ext = default_lang;
			else:
				ext = fns[fnsl-1];
				if(ext not in d):
						ext = default_lang;
			if(buff_id not in bm):
				tm = {};
				tm[ext] = {};
				tm[ext]["alias"] = {};
				bm[buff_id] = tm;
				if(ext in atom_map):
					for a in atom_map[ext]:
						tm[ext][a] = [];
						tm[ext]["alias"][a] = {};
			if(cbid == buff_id):
				#txt = editor.getText();
				for x in src_lt:
					t_ext = x[0];
					if(t_ext in dm):
						t_ext = dm[t_ext];
					d[t_ext](x[1],buff_id);
		xl = [];
		for b in bm.keys():
			if(b not in buff_list):
				xl.append(b);
		for x in xl:
			bm.pop(x);

cd_re = re.compile("[\\\/]*");
def page_match(cdir,pgdir):
	global cd_re;
	da = cd_re.split(cdir);
	pa = cd_re.split(pgdir);
	# Pop unneeded leading element.
	da.pop(0);
	pa.pop(0);
	
	dal = len(da);
	pal = len(pa);
	if(dal < pal):
		return 0;
	
	for i in range(0,pal):
		if(da[i] != pa[i]):
			return 0;
	return (dal - pal) + 1;
	
def cbmanager():
	global ed;
	global icb_max;
	global cb_buff;
	global internal_cb;
	global cb_page_map;
	global cb_page_bmap;
	global cb_page_default;
	global cb_page;
	global serv_path;
	global cb_page_auto_detect;
	
	try:
		raw = "";
		with open(serv_path+"\\clipboard\\autopage.ini","r+") as f:
			raw = f.readline();
		r = raw.replace("\r","").replace("\t","").replace(" ","").replace("\n","");
		n = int(r);
		if(n != 1):
			cb_page_auto_detect = False;
		else:
			cb_page_auto_detect = True;
	except:
		pass;
	
	# Get page list.
	# Roll out a subprocess for the client process.
	sub = subprocess.Popen(["python","-u",serv_path+"\\clipboard\\cb_client.py",":pagelist"],shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);
	try:
		#print "Awaiting input...";
		raw = sub.communicate()[0];
		rl = raw.split("\n");
		for r in rl:
			rs = r.split(",");
			rl = len(rs);
			if(rl < 3):
				try:
					sub.terminate();
				except:
					pass;
				break;
			try:
				tmp = [rs[0],int(rs[2]),rs[3],int(rs[4])];
				cb_page_bmap[rs[1]] = tmp;
			except:
				pass;
	except:
		pass;
	cb_page_map[cb_page_default] = [""] * icb_max;
	cb_page = cb_page_default;
	cb_buff = cb_page_bmap[cb_page_default][3] - 1;
	for i in range(0,icb_max):
		# Load up the buffers from the database for the default page file.
		sub = subprocess.Popen(["python","-u",serv_path+"\\clipboard\\cb_client.py",":page",str(cb_page_default),":buffer",str(i+1)],shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);
		try:
			raw = sub.communicate()[0];
			cb_page_map[cb_page_default][i] = raw;
		except:
			pass;
		pass;
	internal_cb = cb_page_map[cb_page_default];
	while(True):
		time.sleep(0.1);
		fl = Notepad.getFiles(notepad);
		tpl = [];
		for f in fl:
			fn = f[0];
			cfn = False;
			if(fn == Notepad.getCurrentFilename(notepad)):
				cfn = True;
			dir = get_dirname(fn);
			m = None;
			for k,v in cb_page_bmap.iteritems():
				cbd = v[2];
				n = page_match(dir,cbd);
				# Matches and is stronger match than any previous matching page entry.
				if((n != 0) and ((m == None) or (m[1] > n))):
					m = [k,n];
			# Match found...
			if(m != None):
				if(m[0] not in cb_page_map):
					tpl.append(m[0]);
					t = cb_page_bmap[m[0]];
					cb_page_map[m[0]] = [""] * t[1];
					for i in range(0,t[1]):
						# Load up the buffers from the database for this page file.
						sub = subprocess.Popen(["python","-u",serv_path+"\\clipboard\\cb_client.py",":page",str(m[0]),":buffer",str(i+1)],shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);
						#print "Awaiting input...";
						try:
							raw = sub.communicate()[0];
							cb_page_map[m[0]][i] = raw;
						except:
							pass;
						pass;
				if(cfn and cb_page_auto_detect and (cb_page != m[0]) and (m[0] in cb_page_map)):
					#m = cb_page_bmap[m[0]];
					internal_cb = cb_page_map[m[0]];
					m2 = cb_page_bmap[m[0]];
					cb_page = m[0];
					cb_buff = m2[3] - 1;
					#icb_max = m[1];
			elif(cfn and cb_page_auto_detect and (cb_page != cb_page_default)):
				internal_cb = cb_page_map[cb_page_default];
				cb_page = cb_page_default;
				cb_buff = cb_page_bmap[cb_page_default][3] - 1;
		"""
		el = [];
		for x in cb_page_map.iterkeys():
			if(x not in tpl):
				el.append(x);
		for x in el:
			try:
				cb_page_map.pop(x);
			except:
				pass;
		"""

if __name__ == '__main__':
	#print "test point 1\n";
	Thread(target=cmd_server).start();
	Thread(target=paste_server).start();
	Thread(target=memcomplete).start();
	Thread(target=cbmanager).start();
	Thread(target=dragon_thread).start();