# Notes on creation of automatic remarkable 2 document sync


## Setup

Currently, the [lines-are-rusty](https://github.com/ax3l/lines-are-rusty.git) repository seems to have the best support for the latest lines file format, so this will be used.

A new git repository was created with 

```bash
git init
```

and lines-are-rusty added as a submodule:

```bash
git submodule add https://github.com/ax3l/lines-are-rusty.git
```

Since we'll use python for scripting, we set up a virtualenv with 

```bash
virtualenv venv
```

and add it to the .gitignore:

```
venv/
```

## Plan

All the hard work should be done on the raspberry pi, not on the remarkable.

The first step of the script can be to check if the remarkable is reachable, then on a file by file basis check whether it has been modified since the last sync, and resync the files if so.

So our first step is to write a function that checks whether the remarkable is on and has port 22 open:

```python
import socket

RM_IP = "192.168.0.229"

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

if __name__ == '__main__':
	print(f'remarkable online:  {is_rm_online()}')
```

Nice and simple, and works well.

Our next step is to write a function that connects to the remarkable, and checks the last modified date of each notebook.

We can use the package [paramiko](https://github.com/paramiko/paramiko) to connect via ssh.

Since this will contain some secret info, we'll put any secrets in a .gitignored config/ directory.

And since we'll use relative imports, we'll run the python file as a module like so:

```bash
# ensure you are currently at the root project directory, then:
python -m script.sync
```

After some playing around, the method for getting last modified ended up looking like this:

```python
import paramiko
from datetime import datetime
from config.ssh_config import ssh_passphrase, RM_IP

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
	modified = datetime.strptime(modified[0], '%Y-%m-%d %H:%M:%S')
	return modified
```

Now that we have a method for opening up an SSH connection, and a method for checking the last modified time for a given directory / file on the remarkable, we need to decide how we'll store our local copy of the last modified to compare against.

A basic sqlite database seems like a good fit.

## Notes on DB schema

The DB schema will naturally follow the file system structure of the remarkable.

Within the `xochitl` directory, for each notebook we have:

xochitl/
	- <notebook_id>/
		- <page_id>.rm
		- <page_id>-metadata.json
	- <notebook_id>.content
	- <notebook_id>.metadata
	- <notebook_id>.pagedata

the useful properties of each file are:

### `.content`

1. fileType
2. pages

### `.metadata`

1. visibleName

### `.pagedata`

none.

A possible db schema could be:

**base_modified**: (modified timestamp)

**notebooks**: (id, name, modified)

**pages**: (id, notebook_id, page_number, modified)

base_modified will keep track of the last time the xochitl directory itself has seen a change, so that we don't have to check each file individually.

notebooks will let us map the id to the notebook name, and let us know whether the notebook has been modified.

pages will let us track on the page by page level which pages have been modified and when.

