from dragonfly.grammar.grammar     import Grammar
from dragonfly.grammar.context     import AppContext
from dragonfly.grammar.rule_mapping import MappingRule
from dragonfly.grammar.elements    import Dictation
from dragonfly.actions.actions     import Key, Text
from dragonfly import (Grammar, AppContext, CompoundRule, MappingRule, Choice, Dictation, Key, Text,IntegerRef,NumberRef)

import sys;
import os;
import os.path;
import time;
import socket;
import select;
import lxml;
from lxml import etree;
import re;
import num2word;

#
def text2int(textnum, numwords={}):
	if not numwords:
		units = [
				"zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
				"nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
				"sixteen", "seventeen", "eighteen", "nineteen",
			]
		
		tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
		
		scales = ["hundred", "thousand", "million", "billion", "trillion"]
		
		numwords["and"] = (1, 0)
		for idx, word in enumerate(units):
			numwords[word] = (1, idx)
		for idx, word in enumerate(tens):
			numwords[word] = (1, idx * 10)
		for idx, word in enumerate(scales):
			numwords[word] = (10 ** (idx * 3 or 2), 0)
	
	ordinal_words = {'first':1, 'second':2, 'third':3, 'fifth':5, 'eighth':8, 'ninth':9, 'twelfth':12}
	ordinal_endings = [('ieth', 'y'), ('th', '')]
	
	textnum = textnum.replace('-', ' ')
	
	current = result = 0
	for word in textnum.split():
		if word in ordinal_words:
			scale, increment = (1, ordinal_words[word])
		else:
			for ending, replacement in ordinal_endings:
				if word.endswith(ending):
					word = "%s%s" % (word[:-len(ending)], replacement)
			
			if word not in numwords:
				raise Exception("Illegal word: " + word)
			
			scale, increment = numwords[word]
		
		current = current * scale + increment
		if scale > 100:
			result += current
			current = 0
	
	if(((result + current) == 0) and (scale >= 100)):
		result = scale;

	return result + current


def clean_fd_name(s):
	d = "\\";
	d2 = "/";
	sl = len(s);
	for i in range(0,sl):
		j = sl - (i + 1);
		if(j < 0):
			break;
		x = s[j];
		if((x == d) or (x == d2)):
			return s[(j+1):];
	return s;

global orig_path;
orig_path = os.getcwd();

global dragon_path;
dragon_path = "";
try:
	dragon_path = os.environ["NPP_DRAGON"];
except:
	print "[ERROR] Environmental variable 'NPP_DRAGON' is not setup.  Did you run setup.bat in the nppserve directory?";
	exit();

#---------------------------------------------------------------------------
# Create this module's grammar and the context under which it'll be active.
global grammar;
grammar_context = AppContext(executable="notepad++")
grammar = Grammar("notepad++_example", context=grammar_context)

global _gcontext;
global _gcontext_list;
global _gcontext_map;
_gcontext_list = [];
_gcontext_map = {};
_gcontext = "php";

mrule_list = [];

# 
os.chdir(dragon_path + "\\grammar\\context\\");

d = ".";
_gcontext_list = [os.path.join(d,o) for o in os.listdir(d) if os.path.isdir(os.path.join(d,o))];

_gll = len(_gcontext_list);
for i in range(0,_gll):
	_gcontext_list[i] = clean_fd_name(_gcontext_list[i]);

os.chdir(orig_path);

f = open(dragon_path+"\\grammar\\context.txt","r+");
line = f.readline();
f.close();

line = line.replace("\r","").replace("\n","");
if line in _gcontext_list:
	_gcontext = line;

class G_Rule:

	def __init__(self, name, spec, extra,ph_list):
		self.name = name;
		self.spec = spec;
		self.extra = extra;
		self.ph_list = ph_list;

class G_Symbol:

	def __init__(self,name,mtype,pos=0,ch_num=0):
		self.name = name;
		self.mtype = mtype;
		self.pos = pos;
		self.ch_list = None;
		ph_name = "autoplaceholder"+str(ch_num);
		if(mtype == 2):
			self.ch_list = name;
			self.name = ph_name;
	
	def render_extra(self):
		if(self.mtype == 1): # Symbol
			return "Dictation(\""+str(self.name)+"\")";
		elif(self.mtype == 2): # Flag
			cls = "";
			for c in self.ch_list:
				cls += "\""+str(c)+"\":\""+str(c)+"\",";
			res = "Choice(\""+str(self.name)+"\",{"+cls+"})";
			return res;
		elif(self.mtype == 3): # Integer
			return "IntegerRef(\""+str(self.name)+"\",1,100)";
		return None;

	def render_spec(self):
		if(self.mtype == 1): # Normal
			return "<"+self.name+">";
		elif(self.mtype == 2): # Flag
			return "[<"+self.name+">]";
		elif(self.mtype == 3): # Integer
			return "<"+self.name+">";
		return self.name;


def asc_ins_obj(ls,item):
	ln = len(ls);
	for i in range(0,ln):
		x = ls[i];
		if(x.pos >= item.pos):
			ls.insert(i,item);
			return;
	ls.append(item);

def asc_ins(ls,item):
	ln = len(ls);
	for i in range(0,ln):
		x = ls[i];
		if(x >= item):
			ls.insert(i,item);
			return;
	ls.append(item);

class G_Out:

	# ctype 0 -> require, 1 -> require_not
	def __init__(self,out,cond=None):
		self.raw = out;
		try:
			if(self.raw != None):
				self.raw = self.raw.replace('"','\\"').replace("'","\\'");
		except:
			pass;
		self.parts = [];
		self.cond = cond;
		
		pos = [];
		pos2 = [];

		ph_list = [];
		
		mtype = -1;
		st = "%";
		se = "%";
		
		spec = out;
		
		if(spec == None):
			return;

		i = 0;
		j = 0;
		i = spec.find(st);
		j = spec.find(se,i+1);
		while ((i != -1)and(j != -1)):
			if i not in pos:
				name = spec[(i+len(st)):j];
				asc_ins_obj(ph_list,G_Symbol(name,mtype,i));
				asc_ins(pos,i);
				asc_ins(pos2,j + (len(se) - 1));
			i = spec.find(st,j + 1);
			j = spec.find(se,i + 1);

		# Grab all the non-placeholder sections.
		i = 0;
		j = 0;
		sn = len(spec);
		pn = len(pos);
		for k in range(0,pn):
			j = pos[k];
			n = pos2[k];
			sc = spec[i:j];
			asc_ins_obj(ph_list,G_Symbol(sc,0,i));
			i = n + 1;
		
		if(i < sn):
			j = sn;
			sc = spec[i:j];
			asc_ins_obj(ph_list,G_Symbol(sc,0,i));

		self.parts = ph_list;
	
	def render_parts(self):
		for x in self.parts:
			if(x.mtype == -1):
				pass;
			elif(x.mtype == 0):
				pass;
			pass;
		

def parse_symbols(spec):
	res = [None,None,None];
	pos = [];
	pos2 = [];

	_spec = "";
	extra = "[";
	ph_list = [];

	mt = [3,2,1];
	stl = ["<%","{","<"];
	sel = [">","}",">"];

	# Get the IntegerRefs, Flags/Choices, and Dications (in that order).
	for k in range(0,3):
		mtype = mt[k];
		st = stl[k];
		se = sel[k];

		i = 0;
		j = 0;
		i = spec.find(st);
		j = spec.find(se);
		while ((i != -1)and(j != -1)):
			if i not in pos:
				tn = len(ph_list)+1;
				name = spec[(i+len(st)):j];
				if(mtype == 2):
					tmp = name.split("|");
					name = [];
					for t in tmp:
						name.append(trim_lead(trim_trail(t," ")," "));
				asc_ins_obj(ph_list,G_Symbol(name,mtype,i,tn));
				asc_ins(pos,i);
				asc_ins(pos2,j + (len(se) - 1));
			j = spec.find(se,j + 1);
			i = spec.find(st,i + 1);
	
	# Grab all the non-placeholder sections.
	i = 0;
	j = 0;
	sn = len(spec);
	pn = len(pos);
	for k in range(0,pn):
		j = pos[k];
		n = pos2[k];
		sc = spec[i:j];
		asc_ins_obj(ph_list,G_Symbol(sc,0,i));
		i = n + 1;
	
	if(i < sn):
		j = sn;
		sc = spec[i:j];
		asc_ins_obj(ph_list,G_Symbol(sc,0,i));

	sep = "";
	# put it all together.
	for x in ph_list:
		_ts = x.render_spec();
		_te = x.render_extra();
		if(_ts == None):
			continue;
		_spec += x.render_spec();
		if(_te != None):
			extra += sep + x.render_extra();
			sep = ",";
	
	extra += "]";

	res = [_spec,extra,ph_list];
	return res;

def get_ext(s):
	d = "\\";
	d2 = "/";
	d3 = ".";
	sl = len(s);
	for i in range(0,sl):
		j = sl - (i + 1);
		if(j < 0):
			break;
		x = s[j];
		if((x == d) or (x == d2)):
			return "";
		elif(x == d3):
			return s[(j+1):];
	return "";

def filter_files(fl,ext):
	res = [];
	for x in fl:
		if(get_ext(x) == ext):
			res.append(clean_fd_name(x));
	return res;

global fct_temp;
fct_temp = None;

global target_ip;
global target_port;
target_ip = "127.0.0.1";
target_port = 36555;

def build_context_funct(cn,context,name,out_list,opt_map,config,tformat={}):
	global fct_temp;
	global _gcontext_map;
	global _gcontext;
	
	itb = "             ";
	itt = "    ";
	
	res = "global "+str(cn)+";\n";
	res += "global _gcontext_map;\n";
	res += "def "+cn+"(_v_,_vt_):\n";
	res += itb + "global _gcontext;\n";
	res += itb + "def_conf = {};\n";
	for k,v in config.iteritems():
		res += itb + "def_conf[\""+str(k)+"\"] = \""+str(v)+"\";\n";
	
	res += itb + "t_form = {};\n";
	res += itb + "cform = 0;\n";
	for k,v in tformat.iteritems():
		res += itb + "t_form[\""+str(k)+"\"] = \""+str(v)+"\";\n";

	res += itb + "def_format = 0;\n";
	res += itb + "if(\"format\" in def_conf):\n";
	res += itb + itt + "def_format = int(def_conf[\"format\"]);\n";
	ld = "_v_";

	#res += itb + "if \"x\" in _v_:\n";
	#res += itb + itt + "print str(_v_[\"x\"]);\n";
	
	res +=  itb + "m = \"\";\n";
	res += itb+"props = None;\n";
	gs = "";
	for go in out_list:
		cond = go.cond;
		gcc = "";
		ts = "";
		gs = "";
		if(cond != None):
			for gco in cond:
				tcc = "";
				ts = "";
				if(gco[0] == 0): # require
					#print "req: "+str(gco[1]);
					for gcss in gco[1]:
						tcc = "(";
						ts = "";
						#print str(gcss);
						for gcs in gcss:
							tcc += ts+"((\""+gcs+"\" in "+ld+")and("+ld+"[\""+gcs+"\"] != None))";
							ts = "or"
						tcc += ")";
						gcc += gs + tcc;
						gs = "and";
				elif(gco[0] == 1): # require_not
					#print "req_not: "+str(gco[1]);
					for gcss in gco[1]:
						tcc = "(";
						ts = "";
						#print "______: "+str(gcss);
						for gcs in gcss:
							tcc += ts+"((\""+gcs+"\" in "+ld+")and("+ld+"[\""+gcs+"\"] == None))";
							ts = "or";
						tcc += ")";
						#print "         >>> "+tcc;
						gcc += gs + tcc;
						gs = "and";
				else:
					pass;
		if(gcc != ""):
			res += itb+"if("+gcc+"):\n";
			for gcp in go.parts:
				gn = gcp.name.replace("\r","").replace("\n","");
				if(gcp.mtype == -1):
					gn = gcp.name.replace("\r","").replace("\n","");
					res += itb+itt+"cform = def_format;\n";
					res += itb+itt+"if((\""+gn+"\" in _vt_)and(_vt_[\""+gn+"\"] == 1)):\n";
					res += itb+itt+itt+"if(\""+gn+"\" in t_form):\n";
					res += itb+itt+itt+itt+"cform = int(t_form[\""+gn+"\"]);\n";
					res += itb+itt+"if(\""+gn+"\" in "+ld+"):\n";
					res += itb+itt+itt+"m += format_text("+ld+"[\""+gn+"\"],cform);\n";
				else:
					if(gcp.name != ""):
						gnnn = gcp.name;
						try:
							if(gnnn != None):
								gnnn = gnnn.replace('"','\\"').replace("'","\\'");
						except:
							pass;
						res += itb+itt+"m += \"\"\""+gnnn+"\"\"\";\n";
					else:
						res += itb+itt+"m += \"\";\n";
			if(len(go.parts) < 1):
				res += itb+itt+"pass;\n";
		else:
			for gcp in go.parts:
				if(gcp.mtype == -1):
					gn = gcp.name.replace("\r","").replace("\n","");
					res += itb+"cform = def_format;\n";
					res += itb+"if((\""+gn+"\" in _vt_)and(_vt_[\""+gn+"\"] == 1)):\n";
					res += itb+itt+"if(\""+gn+"\" in t_form):\n";
					res += itb+itt+itt+"cform = int(t_form[\""+gn+"\"]);\n";
					res += itb+"if(\""+gcp.name+"\" in "+ld+"):\n";
					res += itb+itt+"m += format_text("+ld+"[\""+gcp.name+"\"],cform);\n";
				else:
					if(gcp.name != ""):
						gnnn = gcp.name;
						try:
							if(gnnn != None):
								gnnn = gnnn.replace('"','\\"').replace("'","\\'");
						except:
							pass;
						res += itb+"m += \"\"\""+gnnn+"\"\"\";\n";
					else:
						res += itb+"m += \"\";\n";
	
	dpl = itb+"props = [";
	sep = "";
	for k,v in opt_map.iteritems():
		dpl += sep + "d_prop(\""+str(k)+"\",\""+str(v)+"\")";
		sep = ",";
	dpl += "];\n";
	res += dpl;
	res += itb+"return (m,props);\n";
	#print "\n\n#>>>>>>>>>>>\n\n"+res+"\n\n"+"global "+str(cn)+"; global _gcontext_map; _gcontext_map[\""+context+"_"+name+"\"] = "+str(cn)+";\n";
	exec res;
	exec "global "+str(cn)+"; global _gcontext_map; _gcontext_map[\""+context+"_"+name+"\"] = "+str(cn)+";\n";
	
	return fct_temp;

"""
def build_context_funct(cn,context):
	global fct_temp;

	itb = "             ";
	itt = "    ";

	res = "global "+str(cn)+";\n";
	res += "def "+cn+"(self):\n";
	res += itb + "global _gcontext;\n";
	res += itb + "if(_gcontext != self.rcontext):\n"+itb+itt+"return True;";
	res += itb + "return False;\n";
	exec res;
	exec "global "+str(cn)+"; global fct_temp; fct_temp = "+str(cn)+";\n";
	return fct_temp;
"""

_gcontext_date = os.path.getmtime(dragon_path+"\\grammar\\context.txt");

def check_context_state():
	global _gcontext;
	global _gcontext_date;
	td = os.path.getmtime(dragon_path+"\\grammar\\context.txt");
	if(td != _gcontext_date):
		_gcontext_date = td;
		f = open(dragon_path+"\\grammar\\context.txt","r+");
		line = f.readline();
		f.close();

		line = line.replace("\r","").replace("\n","");
		if line in _gcontext_list:
			_gcontext = line;


def build_proc_funct(fn,ph_list): # out_list,opt_map
	global fct_temp;
	global target_ip;
	global target_port;
	"""
	def _process_recognition(self, node, extras):
	global dsep;
	global ssep;
	global esep;
        fname = extras["fname"];
	ip = "127.0.0.1";
	port = 36555;
	props = [d_prop("indent","inherit"),d_prop("type","add_text")];
	m = "def "+str(fname).replace(" ","_").lower()+"():\n";
	send_udp(str(ssep)+m+str(dsep)+prep_props(props)+str(esep),ip,port);
	"""
	itb = "             ";
	itt = "    ";

	res = "global "+str(fn)+";\n";
	res += "def "+fn+"(self, node, extras):\n";
	res += itb+"global dsep; global ssep; global esep; \n";
	res += itb+"global target_ip;\n";
	res += itb+"global target_port;\n";
	res += itb+"ip = target_ip;\n"+itb+"port = target_port;\n";
	res += itb+"check_context_state();\n";
	#res += itb+"if(not self."+cn+"()): return;\n"; # not in proper context for this grammar.
	ld = "_v_";
	res += itb+ld + " = {};\n";
	ldt = "_vt_";
	res += itb+ldt + " = {};\n";
	
	for p in ph_list:
		if(p.mtype == 0):
			continue;
		n = p.name;
		m = p.mtype;
		res += itb+ld+"[\""+str(n)+"\"] = None;\n"+itb+"if \""+str(n)+"\" in extras:\n"+itb+itt+ld+"[\""+str(n)+"\"] = str(extras[\""+str(n)+"\"]);\n";
		res += itb+ldt+"[\""+str(n)+"\"] = "+str(m)+";\n";
		if(m == 2):
			for ps in p.ch_list:
				res += itb+ld+"[\""+str(ps)+"\"] = None;\n"+itb+"if ("+ld+"[\""+str(n)+"\"] == \""+str(ps)+"\"):\n"+itb+itt+ld+"[\""+str(ps)+"\"] = "+ld+"[\""+str(n)+"\"];\n";
	#res += itb+"print str(_v_)\n\n\n";
	#res += itb+"print str(_vt_)\n\n\n";
	# Message should be constructed here from the output/action tag of this concept.
	res += itb+"m,props = _gcontext_map[str(_gcontext)+\"_\"+self.rname]("+ld+","+ldt+");\n";

	res += itb+"send_udp(str(ssep)+m+str(dsep)+prep_props(props)+str(esep),ip,port);\n\n";
	#print "\n\n#============\n\n"+res+"\n\n"+"global "+str(fn)+"; global fct_temp; fct_temp = "+str(fn)+";\n";
	exec res;
	exec "global "+str(fn)+"; global fct_temp; fct_temp = "+str(fn)+";\n";
	return fct_temp;

def get_reqs(ch):
	pat = [];
	for k,v in ch.attrib.iteritems():
		vl = v.split(",");
		vv = [];
		for vli in vl:
			ovl = vli.split("|");
			tv = [];
			for vvv in ovl:
				tv.append(trim_lead(trim_trail(vvv," ")," "));
			vv.append(tv);
		if(k == "require"):
			pat.append((0,vv));
		elif(k == "require_not"):
			pat.append((1,vv));
	return pat;
	

def build_context_map(rlist):
	global orig_path;
	global dragon_path;
	global grammar;
	global mrule_list;
	tb = "  ";

	_cn = "tcname";
	_pn = "tpname";
	_cnn = 1;
	
	c_list = "CompoundRule,object,";

	os.chdir(dragon_path + "\\grammar\\context\\");

	d = ".";
	dl = [os.path.join(d,o) for o in os.listdir(d) if os.path.isdir(os.path.join(d,o))];

	for y in dl:
		found_rule_list = [];
		x = clean_fd_name(y);
		os.chdir(dragon_path + "\\grammar\\context\\"+x);
		fl = filter_files([os.path.join(d,o) for o in os.listdir(d) if not os.path.isdir(os.path.join(d,o))],"xml");
		context = x;
		config = {};
		for z in fl:
			# parse the xml file
			os.chdir(dragon_path + "\\grammar\\context\\"+x);
			props = {};
			xml = etree.parse(z);
			
			cci = xml.getiterator("config");
			for c in cci:
				for ch in c.iterchildren():
					config[str(ch.tag)] = ch.text;
				break;
		
			cci = xml.getiterator("concept");
			for c in cci:
				name = "";
				output = "";
				options = {};
				tform = {};
				glm = [];
				g = None;
				for ch in c.iterchildren():
					if(ch == None):
						continue;
					tag = ch.tag;
					if(tag == "name"):
						name = ch.text;
					elif(tag == "format"):
						pat = get_reqs(ch);
						ky = None;
						vl = None;
						for p in ch.iterchildren():
							if(p.tag.lower() == "name"):
								ky = p.text;
							if(p.tag.lower() == "value"):
								vl = p.text;
						if((ky != None)and(vl != None)):
							tform[ky] = vl;
					elif(tag == "option"):
						pat = get_reqs(ch);
						ky = None;
						vl = None;
						for p in ch.iterchildren():
							if(p.tag.lower() == "name"):
								ky = p.text;
							if(p.tag.lower() == "value"):
								vl = p.text;
						if((ky != None)and(vl != None)):
							options[ky] = vl;
					elif(tag == "action"):
						gsep = G_Out(":");
						gl = [];
						nm = None;
						rp = None;
						for p in ch.iterchildren():
							ptag = p.tag;
							if(ptag.lower() == "name"):
								pat = get_reqs(p);
								g = None;
								if(pat == None):
									g = G_Out(p.text);
								else:
									g = G_Out(p.text,pat);
								nm = g;
								gl.append(g);
							elif(ptag.lower() == "repeat"):
								#rp = g;
								gl.append(gsep);
								for pch in p.iterchildren():
									pat = get_reqs(pch);
									if(pat == None):
										g = G_Out(pch.text);
									else:
										g = G_Out(pch.text,pat);
									gl.append(g);
								continue;
						glm = gl;
					elif(tag == "output"):
						gl = [];
						for p in ch.iterchildren():
							ptag = p.tag;
							if(ptag == "br"):
								g = G_Out("\n");
								gl.append(g);
								continue;
							elif(ptag == "tab"):
								g = G_Out("\t");
								gl.append(g);
								continue;
							pat = get_reqs(p);
							g = None;
							if(pat == None):
								g = G_Out(p.text);
							else:
								g = G_Out(p.text,pat);
							gl.append(g);
						glm = gl;
				# Get the matching rule from the rule_list
				rule = None;
				for rx in rlist:
					if(rx.name == name):
						rule = rx;
						break;
				# no matching rule? skip it.
				if(rule == None):
					continue;
				if(rule.name not in found_rule_list):
					found_rule_list.append(rule.name);
				# put it altogether 
				# build_proc_funct(fn,cn,ph_list,out_list,opt_map):
				t_cn = _cn + str(_cnn);
				build_context_funct(t_cn,context,name,glm,options,config,tform);
				#build_proc_funct(t_pn,t_cn,rule.ph_list,glm,options);
				_cnn += 1;
			os.chdir(orig_path);
		nflist = [];
		for rx in mrule_list:
			if(rx not in found_rule_list):
				nflist.append(rx);
		for rx in nflist:
			t_cn = _cn + str(_cnn);
			#print "[lang: "+str(context)+" name: "+str(rx)+"]:"+t_cn+"\n";
			build_context_funct(t_cn,context,rx,[],{},config,{});
			_cnn += 1;
			pass;

def trim_lead(s,delim):
	d = delim;
	sl = len(s);
	for i in range(0,sl):
		x = s[i];
		if(x != delim):
			return s[i:];
	return None;

def trim_trail(s,delim):
	d = delim;
	sl = len(s);
	for i in range(0,sl):
		j = sl - (i + 1);
		if(j < 0):
			break;
		x = s[j];
		if(x != delim):
			return s[:sl-i];
	return None;

# get the grammar file.
npp_grammar = {};
f = open(dragon_path+"\\grammar\\grammar.ini");
raw = f.readlines();
f.close();

rx = [];
for y in raw:
	x = trim_lead(trim_trail(y," ")," ");
	if (len(x) < 1):
		continue;
	if(x[0] == "#"):
		continue;
	if(x.replace(" ","").replace("\t","").replace("\r","").replace("\n","") == ""):
		continue;
	rx.append(y);
raw = rx;



# ftype 0 - under_score lower, ftype 1 = - under_score upper, ftype 2 = under_score CAPS, ftype 3 - camel lower, ftype 4 = - camel upper, ftype 5 = CAPS               format_text("whaT a BiG var",1);
def format_text(txt,ftype):

	if((txt == None)or(txt.replace(" ","").replace("\n","").replace("\r","").replace("\t","") == "")):
		if(txt == None):
			txt = "";
		return txt;
	res = trim_lead(trim_trail(txt.replace("\n","").replace("\r","").replace("\t","")," ")," ");
	res = res.replace("\\","\\\\").replace("'","\\'").replace('"','\\"');
	# Deal with verbose numbers.
	tl = re.split("[^a-zA-Z0-9_]{1}",res);

	m = None;
	try:
		#print "Attempting: %s\n" % (res);
		m = text2int(res);
	except:
		pass;
	if(m != None):
		res = str(m);
		#print "Test: "+res+"\n";
	else:
		y = [];
		yd = {};
		for x in tl:
			try:
				tx = x;
				k = None;
				try:
					k = int(x);
				except:
					pass;
				if(isinstance(k, (int, long))):
					tx = num2word.to_card(k);
				n = text2int(tx);
				p = res.find(x);
				if(x in yd):
					tmp = yd[x];
					p = res.find(x,tmp+1);
					yd[x] = p;
				else:
					yd[x] = p;
				y.append([tx,p,n,len(x)]);
				#res = "%s%s%s" % (res[0:p],str(n),res[(p+len(x)):]);
				#m = text2int(res);
				#res = 
			except:
				try:
					if(len(y) > 0):
						t = "";
						sp = None;
						ep = None;
						for z in y:
							t = "%s %s" % (t,z[0]);
							if(sp == None):
								sp = z[1];
							et = z[1] + z[3];
							if((ep == None)or(et > ep)):
								ep = z[1] + z[3];
						n = str(text2int(t));
						res = "%s%s%s" % (res[0:sp],n,res[ep:]);
						y = None;
					pass;
				except:
					pass;
		try:
			if(len(y) > 0):
				t = "";
				sp = None;
				ep = None;
				for z in y:
					t = "%s %s" % (t,z[0]);
					if(sp == None):
						sp = z[1];
					ep = z[1] + len(z[0]);
				n = str(text2int(t));
				res = "%s%s%s" % (res[0:sp],n,res[ep:]);
				pass;
			pass;
		except:
			pass;
		#print "Test2: "+res+"\n";

	if(ftype == 0):
		return res.lower().replace(" ","_");
	elif(ftype == 1):
		rr = res.lower().split(" ");
		sep = "";
		tmp = "";
		for r in rr:
			tmp += sep + str(r[0]).upper() + r[1:len(r)];
			sep = " ";
		res = tmp.replace(" ","_");
		return res;
	elif(ftype == 2):
		return res.upper().replace(" ","_");
	elif(ftype == 3):
		rr = res.lower().split(" ");
		sep = "";
		tmp = "";
		for r in rr:
			if(sep == ""):
				tmp += sep + r[0].lower() + r[1:len(r)];
			else:
				tmp += sep + r[0].upper() + r[1:len(r)];
			sep = " ";
		res = tmp.replace(" ","");
		return res;
	elif(ftype == 4):
		rr = res.lower().split(" ");
		sep = "";
		tmp = "";
		for r in rr:
			tmp += sep + r[0].upper() + r[1:len(r)];
			sep = " ";
		res = tmp.replace(" ","");
		return res;
	elif(ftype == 5):
		return res.upper().replace(" ","");
	return txt;

rule_list = [];

for r in raw:
	x = r.find("=");
	p1 = trim_trail(r[:int(x)]," ");
	p2 = trim_lead(r[int((x+1)):]," ");
	spec,extra,ph = parse_symbols(p2);
	rule = G_Rule(p1,spec,extra,ph);
	rule_list.append(rule);
	mrule_list.append(p1);

# Build the grammars
build_context_map(rule_list);
_tpn = "tfunct";
_cnn = 1;
_cn = "ggclass";
c_list = "CompoundRule,object,";
_itt = "     ";
for rr in rule_list:
	t_pn = _tpn + str(_cnn);
	build_proc_funct(t_pn,rr.ph_list);
	props = {};
	props["spec"] = "\""+rr.spec.replace("\r","").replace("\n","")+"\"";
	props["extras"] = rr.extra;
	props["rname"] = "\""+str(rr.name)+"\"";
	props["_process_recognition"] = t_pn;
	props["__init__"] = "CompoundRule.__init__";

	gss  = "global "+t_pn+";\n";
	gss += "class "+t_pn+"(CompoundRule):\n";

	sprop = "{";
	for k, v in props.iteritems():
		sprop += "\""+str(k)+"\":"+str(v)+",";
		gss += _itt+""+str(k)+" = "+str(v)+";\n";
	sprop += "}";
	gs = "global "+t_pn+";tcn = type(\""+(str(_cn)+str(_cnn))+"""\",("""+c_list+"""),"""+sprop+"""); grammar.add_rule(tcn());""";
	
	#print "\n\n------\n\n"+gss+"\n\n";
	
	exec gs;
	#print "\n\n#------------------\n\n";
	#print gs;
	_cnn += 1;

global dsep;
global psep;
global ksep;
global ssep;
global esep;
ssep = "###)))(((###";
dsep = "###<<<>>>###";
psep = "###>>><<<###";
ksep = "###((()))###";
esep = "###!!||!!###";

def d_prop(k,v):
	global ksep;
	return str(k) + str(ksep) + str(v);
def prep_props(p):
	global psep;
	return psep.join(p);

def send_udp(msg,addr,port):
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); # UDP
	sock.sendto(msg, (addr, int(port)));

cmap = {};
for cm in _gcontext_list:
	cmap[clean_fd_name(cm)] = clean_fd_name(cm);

class ContextSwitch(CompoundRule):

    spec = "language <cname>";
    cname = cmap;
    extras = [
              Choice("cname",cname),
             ]

    def _process_recognition(self, node, extras):
	global dsep;
	global ssep;
	global esep;
	global _gcontext;
	global dragon_path;
        cname = extras["cname"];
	_gcontext = cname;
	f = open(dragon_path+"\\grammar\\context.txt","w+");
	f.write(_gcontext);
	f.flush();
	f.close();

# Add the action rule to the grammar instance.
grammar.add_rule(ContextSwitch())
grammar.load()


# Unload function which will be called by natlink at unload time.
def unload():
    global grammar
    if grammar: grammar.unload()
    grammar = None
