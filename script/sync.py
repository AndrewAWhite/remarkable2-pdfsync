import socket, sqlite3, os, json
from datetime import datetime
import paramiko
from config.ssh_config import ssh_passphrase, RM_IP

XOCHITL_PATH = '/home/root/.local/share/remarkable/xochitl/'
BACKUP_PATH = '/mnt/c/Andrew/Documents/remarkable/backup/'
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

def get_notebook_name(client, notebook_id):
	stdin, stdout, stderr = client.exec_command(f"""
		cat {XOCHITL_PATH}{notebook_id}.metadata
	""")
	metadata = json.loads('\n'.join(stdout))
	return metadata['visibleName']

def get_db_con():
	return sqlite3.connect(DB_FILE)

def db_setup(client, reset=False):
	if os.path.isfile(DB_FILE) and not reset:
		return
	con = get_db_con()
	cur = con.cursor()
	create_tables(cur)
	fill_db(client, cur)
	cur.close()
	con.commit()
	con.close()

def create_tables(cur):
	cur.execute("""
		DROP TABLE IF EXISTS base_modified;
	""")
	cur.execute("""
		DROP TABLE IF EXISTS notebooks;
	""")
	cur.execute("""
		DROP TABLE IF EXISTS pages;
	""")
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

def fill_db(client, cur):
	base_modified = get_modified(client, XOCHITL_PATH)
	cur.execute(f"""
		INSERT INTO base_modified (modified)
		VALUES ('{base_modified.strftime(TIMESTAMP_FMT)}');
	""")
	for notebook_id in list_notebook_ids(client):
		notebook_modified = get_modified(client, f'{XOCHITL_PATH}{notebook_id}')
		page_ids = get_notebook_pages(client, notebook_id)
		if not page_ids:
			continue
		notebook_name = get_notebook_name(client, notebook_id)
		# create notebook row
		cur.execute(f"""
			INSERT INTO notebooks (id, name, modified)
			VALUES ('{notebook_id}', '{notebook_name}', '{notebook_modified.strftime(TIMESTAMP_FMT)}');
		""")
		page_number = 1
		for page_id in page_ids:
			page_modified = get_modified(client, f'{XOCHITL_PATH}{notebook_id}/{page_id}.rm')
			# insert page row
			cur.execute(f"""
				INSERT INTO pages (id, notebook_id, page_number, modified)
				VALUES ('{page_id}', '{notebook_id}', {page_number}, '{page_modified.strftime(TIMESTAMP_FMT)}');
			""")
			page_number += 1



def main():
	if not is_rm_online():
		print('remarkable could not be reached.')
		exit(0)
	client = get_client()
	db_setup(client)
	client.close()

if __name__ == '__main__':
	main()
	


	