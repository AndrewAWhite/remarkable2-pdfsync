DIR = /mnt/c/Andrew/Documents/remarkable/rmsync/xochitl
METADATA =  $(wildcard $(DIR)/*.metadata)
CONTENT = $(wildcard $(DIR)/*.content)

all : metadata.txt content.txt

metadata.txt : $(METADATA)
	# refresh the metadata.txt file
	cat $^ > metadata.txt
	# edit the file so that it's valid json by wrapping in '[]' and adding ',' between objects
	sed -i '1s/^/[/;:a;N;$$!ba;s/}\n{/},\n{/g;$$a]' metadata.txt
	# for each .metadata file that has changed since the last sync, regenerate pdf
	for notebook_id in $(basename $(notdir $?)); \
	do                                           \
		echo $$notebook_id;                      \
		echo "one two three" $$notebook_id;      \
	done
	

content.txt : $(CONTENT)
	cat $^ > content.txt