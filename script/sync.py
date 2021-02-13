import socket, sqlite3, os, json
from datetime import datetime
import paramiko
from config.ssh_config import ssh_passphrase, RM_IP

XOCHITL_PATH = '/home/root/.local/share/remarkable/xochitl/'
DB_FILE = './remarkable_sync.db'
TIMESTAMP_FMT = '%Y-%m-%d %H:%M:%S'

def is_rm_online():
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.settimeout(1)
	try:
		s.connect((RM_IP, 22))
		s.shutdown(socket.SHUT_RDWR)
		return True
	except:
		return False
	finally:
		s.close()

def get_client():
	client = paramiko.SSHClient()
	client.load_system_host_keys()
	client.connect(hostname=RM_IP, port=22, username='root', passphrase=ssh_passphrase)
	return client

def get_modified(client, obj):
	# use stat to get file attributes, and awk to extract modified time
	stdin, stdout, stderr = client.exec_command(f""" 
		stat {obj} |
		awk '/Modify/ {{ print $2, $3 }}'
		""")
	# Remove trailing \n and .0000..
	modified = [l[:-11] for l in stdout]
	if len(modified) != 1:
		return
	# Convert to datetime
	modified = datetime.strptime(modified[0], TIMESTAMP_FMT)
	return modified

def list_notebook_ids(client):
	stdin, stdout, stderr = client.exec_command(f"""
		ls -l {XOCHITL_PATH} |
		awk '/\.content/ {{ print $9 }}'
	""")
	files = [n[:-9] for n in stdout]
	return files

def get_notebook_pages(client, notebook_id):
	# read .content file, extract fileType row
	stdin, stdout, stderr = client.exec_command(f"""
		awk '/fileType/ {{ print $0 }}' {XOCHITL_PATH}{notebook_id}.content
	""")
	# if we don't get anything, or the filetype isn't 'notebook',
	# return []
	info = [n[:-1] for n in stdout]
	if len(info) != 1:
		return []
	if '"notebook"' not in info[0]:
		return []
	# load .content as json and return pages
	info = {}
	stdin, stdout, stderr = client.exec_command(f"""
		cat {XOCHITL_PATH}{notebook_id}.content
	""")
	content = json.loads('\n'.join(stdout))
	return content['pages']

def get_db_con():
	return sqlite3.connect(DB_FILE)

def db_setup():
	if os.path.isfile(DB_FILE):
		return
	con = get_db_con()
	cur = con.cursor()
	cur.execute("""
		CREATE TABLE base_modified (
			modified text
		);
	""")
	cur.execute("""
		CREATE TABLE notebooks (
			id text,
			name text,
			modified text
		);
	""")
	cur.execute("""
		CREATE TABLE pages (
			id text,
			notebook_id text,
			page_number integer,
			modified text
		);
	""")
	cur.close()
	con.commit()
	con.close()

def main():
	db_setup()
	if not is_rm_online():
		print('remarkable could not be reached.')
		exit(0)
	client = get_client()
	for notebook_id in list_notebook_ids(client):
		pages = get_notebook_pages(client, notebook_id)
		if not pages:
			continue
		for page_id in pages:
			print(get_modified(client, f'{XOCHITL_PATH}{notebook_id}/{page_id}.rm'))
		
	client.close()

if __name__ == '__main__':
	main()
	# db_setup()
	# con = get_db_con()
	# cur = con.cursor()
	# cur.execute("""
	# 	INSERT INTO base_modified (modified)
	# 	VALUES ('this is sa value');
	# """)
	# cur.close()
	# cur = con.cursor()
	# for r in cur.execute("""
	# 		SELECT * FROM base_modified;
	# 		"""):
	# 	print(r)
	# con.commit()
	# con.close()


	