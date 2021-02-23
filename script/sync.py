import socket, json, subprocess, sys, os
import pexpect
from PyPDF2 import PdfFileMerger as pdf_merger, PdfFileReader as pdf_reader
from config.ssh_config import ssh_passphrase, RM_IP

XOCHITL_PATH = '/home/root/.local/share/remarkable/xochitl/'
BACKUP_PATH = '/mnt/c/Andrew/Documents/remarkable/rmsync/'

def rm_online():
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

def get_dict(file_name):
	data = None
	with open(f'{BACKUP_PATH}{file_name}.txt', 'r', encoding='utf-8') as file:
		data = json.loads(file.read())
	# rotate from [{k1: v1},{k2: v2},...,{kn: vn}] (easier to produce in makefile) to {kn: vn}
	d = {}
	for md in data:
		kv = next(iter(md.items()))
		d[kv[0]] = kv[1]
	return d

def get_notebook_data():
	metadata = get_dict('metadata')
	content = get_dict('content')
	parents = {k: v['visibleName'] for k, v in metadata.items() if v['type']=='CollectionType'}
	pages = {k: v['pages'] for k, v in content.items() if v.get('pages', [])}
	notebooks = {
		k: { 'name': v['visibleName'], 
			 'pages': pages.get(k, []), 
			 'parent': parents.get(v['parent'], ''),
			 'type': content[k].get('fileType', '')
			} for k, v in metadata.items() if v['type']=='DocumentType'
		}
	return notebooks

def build_notebooks():
	notebooks = get_notebook_data()
	dirs = set(v['parent'] for v in notebooks.values() if v['parent'])
	for dir in dirs:
		os.makedirs(f'{BACKUP_PATH}backup/{dir}', exist_ok=True)
	for notebook in notebooks.values():
		if notebook['type'] != 'notebook':
			continue
		basepath = f'{BACKUP_PATH}/backup/'
		parent = notebook['parent']
		if parent:
			basepath = f'{basepath}{parent}/'
		merger = pdf_merger()
		for page_id in notebook['pages']:
			merger.append(f'{BACKUP_PATH}pdf/{page_id}.pdf')
		merger.write(f'{basepath}{notebook["name"]}.pdf')
		print(f'built {notebook["name"]}')


def rsync():
	p = pexpect.spawn(
		f'rsync -avzh --rsync-path=/opt/bin/rsync root@{RM_IP}:/home/root/.local/share/remarkable/xochitl {BACKUP_PATH}'
		)
	p.expect('Enter passphrase for key')
	p.sendline(ssh_passphrase)
	print(p.read().decode(encoding='utf-8'))

def make():
	p = subprocess.Popen(
		['make', '-f', './script/Makefile', f'SYNC_DIR={BACKUP_PATH}xochitl', f'BACKUP_DIR={BACKUP_PATH}', 'all'],
		stdout = subprocess.PIPE
	)
	message = p.communicate()[0].decode('utf-8')
	return message
	


def main():
	# if remarkable is not reachable, exit
	if not rm_online():
		exit(0)
	# otherwise, sync local and remote xochitl directories
	rsync()
	# execute all rule in makefile
	result = make()
	# if nothing has changed, exit
	if 'Nothing to be done' in result:
		exit(0)
	# otherwise, rebuild pdf notebooks
	build_notebooks()


if __name__ == '__main__':
	main()
