import socket, sqlite3, os, json, subprocess, sys
from datetime import datetime
import paramiko
import pexpect
from scp import SCPClient
from config.ssh_config import ssh_passphrase, RM_IP

XOCHITL_PATH = '/home/root/.local/share/remarkable/xochitl/'
BACKUP_PATH = '/mnt/c/Andrew/Documents/remarkable/rmsync/'
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

def get_notebook_metadata(client, notebook_id):
	stdin, stdout, stderr = client.exec_command(f"""
		cat {XOCHITL_PATH}{notebook_id}.metadata
	""")
	metadata = json.loads('\n'.join(stdout))
	return metadata

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
			parent text,
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

def get_parent_name(client, parent_id):
	stdin, stdout, stderr = client.exec_command(f"""
		cat {XOCHITL_PATH}{parent_id}.metadata
	""")
	metadata = json.loads('\n'.join(stdout))
	return metadata['visibleName']

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
		notebook_metadata = get_notebook_metadata(client, notebook_id)
		parent = notebook_metadata['parent']
		if parent.strip() != '' and parent != 'trash':
			parent = get_parent_name(client, parent)
		# create notebook row
		cur.execute(f"""
			INSERT INTO notebooks (id, name, parent, modified)
			VALUES ('{notebook_id}', '{notebook_metadata['visibleName']}', '{parent}', '{notebook_modified.strftime(TIMESTAMP_FMT)}');
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

def create_backup_dir():
	con = get_db_con()
	cur = con.cursor()
	parent_results = cur.execute("""
		SELECT DISTINCT parent FROM notebooks;
	""")
	os.makedirs(f'{BACKUP_PATH}raw')
	for parent_row in parent_results:
		name = parent_row[0]
		path = f'{BACKUP_PATH}pdf/{name}'
		if not os.path.exists(path):
			os.makedirs(path)
	con.close()

def copy_file(client, remote, local):
	scp = SCPClient(client.get_transport())
	scp.get(remote, local)
	scp.close()

def copy_all(client):
	scp = SCPClient(client.get_transport())
	scp.get(XOCHITL_PATH, local_path=f'{BACKUP_PATH}/raw', recursive=True)
	scp.close()


def convert_page(page, destination):
	p2 = subprocess.Popen(
		['./lines-are-rusty/target/debug/lines-are-rusty', '-o', destination, page], 
		stdout = subprocess.PIPE)
	p2.communicate()

def rsync():
	p = pexpect.spawn(
		f'rsync -avzh --rsync-path=/opt/bin/rsync root@{RM_IP}:/home/root/.local/share/remarkable/xochitl {BACKUP_PATH}'
		)
	p.expect('Enter passphrase for key')
	p.sendline(ssh_passphrase)
	print(p.read().decode(encoding='utf-8'))

def make():
	p = subprocess.Popen(
		['make', '-f', './script/Makefile', f'SYNC_DIR={BACKUP_PATH}/xotchitl', f'BACKUP_DIR={BACKUP_PATH}/pdf', 'all'],
		stdout = sys.stdout
	)
	p.communicate()

def main():
	if not is_rm_online():
		print('remarkable could not be reached.')
		exit(0)
	client = get_client()
	db_setup(client)
	copy_all(client)
	client.close()

if __name__ == '__main__':
	# convert_page('/mnt/c/Andrew/Documents/remarkable/backup/raw/xochitl/5fbc7f03-b4ff-4dc7-b517-34a6ab901d6c/80917537-6b0a-4d33-bf38-a2d2594726a5.rm',
	# '/mnt/c/Andrew/Documents/remarkable/backup/test.pdf')
	make()
	#main()
	


	