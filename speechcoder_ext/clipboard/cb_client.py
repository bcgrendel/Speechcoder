import time;
import sqlite3
import sys;
import os;

ndp = None;
raw_path = "";
db_path = "\\clipboard\\db\\cb.sqlite3";
buff_path = "\\clipboard\\buffer.data";
try:
	ndp = None;
	ndp = os.environ["NPP_DRAGON"];
	db_path = str(ndp) + str(db_path);
	buff_path = str(ndp) + str(buff_path);
except:
	print "[ERROR] Environmental variable 'NPP_DRAGON' is not setup.  Did you run setup.bat in the nppserve directory?";
	exit();

"""
mtype = None;
sql = "select id,data,props,mtype,client_ip,client_port,tstamp from npp_cmd order by tstamp asc limit 1";
if(len(sys.argv) > 1):
	mtype = int(sys.argv[1]);
	sql = "select id,data,props,mtype,client_ip,client_port,tstamp from npp_cmd mtype = '"+str(mtype)+"' order by tstamp asc limit 1";
"""

conn = None;
cur = None;

try:
	conn = sqlite3.connect(db_path);
	cur = conn.cursor();
except:
	print "[ERROR] Unable to connect to the db: "+db_path;
	exit();

# Ensure tables exist.
sql = "SELECT name FROM sqlite_master WHERE type='table' AND name='cb_page'";
sql2 = "SELECT name FROM sqlite_master WHERE type='table' AND name='cb_buffer'";
cur.execute(sql);
r = cur.fetchall();
rf = (len(r) < 1);
cur.execute(sql2);
r = cur.fetchall();
rf2 = (len(r) < 1);

def_buff_size = 5;

if(rf or rf2):
	# create tables!
	# drop either that might already exist.
	sql = "drop table if exists 'cb_page'";
	cur.execute(sql);
	sql = "drop table if exists 'cb_buffer'";
	cur.execute(sql);
	# create
	sql = "create table cb_page(id integer primary key autoincrement,name varchar(256),directory varchar(512),size integer not null default "+str(def_buff_size)+",current_buff_id integer not null default 1)";
	cur.execute(sql);
	sql = "create table cb_buffer(id integer primary key autoincrement,name varchar(256),buff_id integer not null default 1,page_id integer,buffer text)";
	cur.execute(sql);
	conn.commit();


# Check if the db needs initialization...
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
sql = "select name from cb_page where name = 'default'";
cur.execute(sql);
ff = False;
try:
	pgn = cur.fetchone()[0];
	if(pgn != "default"):
		ff = True;
except:
	ff = True;

if(ff):
	sql = "insert into cb_page (name) values ('default')";
	cur.execute(sql);
	conn.commit();
	pgid = 1;
	sql = "select last_insert_rowid()";
	cur.execute(sql);
	
	try:
		pgid = int(cur.fetchone()[0]);
	except:
		print "DB ERROR. Failed to create clipboard paging tables.";
		exit();

	for i in range(0,def_buff_size):
		sql = "insert into cb_buffer (buff_id,page_id,buffer) values ('"+str(i+1)+"','"+str(pgid)+"','')";
		cur.execute(sql);
	conn.commit();

# Perform actions:
# ---------------------------------------------------------

if(len(sys.argv) > 1):
	mtype = sys.argv[1];
	if(mtype == ":pagelist"):
		sql = "select id,name,size,directory,current_buff_id from cb_page";
		cur.execute(sql);
		r = cur.fetchall();
		for v,w,x,y,z in r:
			sys.stdout.write("%s,%s,%s,%s,%s\n" % (v,w,x,y,z));
			sys.stdout.flush();
	elif(mtype == ":page"):
		if(len(sys.argv) > 4):
			try:
				page_name = sys.argv[2];
				buff_id = int(sys.argv[4]);
				sql = "select b.buffer from cb_buffer b inner join cb_page p on p.id = b.page_id where b.buff_id = '"+str(buff_id)+"' and p.name= '"+str(page_name)+"'";
				cur.execute(sql);
				r = cur.fetchone()[0];
				sys.stdout.write(r);
				sys.stdout.flush();
			except:
				pass;
	elif(mtype == ":copy"):
		if(len(sys.argv) > 4):
			try:
				page_name = sys.argv[2];
				buff_id = int(sys.argv[4]);
				txt = "";
				with open(buff_path,"r+") as f:
					txt = f.read().replace("\r","");
				if((len(txt) > 0) and (txt[len(txt)-1] == "\n")):
					txt = txt[0:len(txt)-1];
				sql = "update cb_buffer set buffer = ? where id in (select b.id from cb_buffer b inner join cb_page p on p.id = b.page_id where b.buff_id = ? and p.name= ?)";
				cur.execute(sql,(txt,buff_id,str(page_name)));
				conn.commit();
				sys.stdout.write("Done.");
				sys.stdout.flush();
				with open(buff_path,"w+") as f:
					f.write("");
					f.flush();
			except:
				pass;
	elif(mtype == ":delete"):
		if(len(sys.argv) > 2):
			try:
				page_name = sys.argv[2];
				if(page_name.lower() != "default"):
					sql = "delete from cb_buffer where page_id in (select id from cb_page where name = ?)";
					cur.execute(sql,(page_name,));
					sql = "delete from cb_page where name = ?";
					cur.execute(sql,(page_name,));
					conn.commit();
					sys.stdout.write("Done.");
					sys.stdout.flush();
			except:
				pass;
	elif(mtype == ":add"):
		if(len(sys.argv) > 4):
			try:
				page_name = sys.argv[2];
				page_dir = sys.argv[4];
				sql = "insert into cb_page (name,directory) values (?,?)";
				cur.execute(sql,(str(page_name),str(page_dir)));
				conn.commit();
				pgid = 0;
				sql = "select last_insert_rowid()";
				cur.execute(sql);
				
				try:
					pgid = int(cur.fetchone()[0]);
				except:
					print "DB ERROR. Failed to create clipboard page.";
					exit();
				
				for i in range(0,def_buff_size):
					sql = "insert into cb_buffer (buff_id,page_id,buffer) values ('"+str(i+1)+"','"+str(pgid)+"','')";
					cur.execute(sql);
				conn.commit();
				sys.stdout.write("Done.");
				sys.stdout.flush();
			except:
				pass;
	elif(mtype == ":activebuffid"):
		if(len(sys.argv) > 4):
			try:
				page_name = sys.argv[2];
				buffid = sys.argv[4];
				sql = "update cb_page set current_buff_id = ? where name = ?";
				cur.execute(sql,(int(buffid),str(page_name)));
				conn.commit();
				sys.stdout.write("Done.");
				sys.stdout.flush();
			except:
				pass;



try:
	conn.disconnect();
except:
	pass;
