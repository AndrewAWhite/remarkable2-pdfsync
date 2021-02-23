METADATA =  $(wildcard $(SYNC_DIR)/*.metadata)
CONTENT = $(wildcard $(SYNC_DIR)/*.content)
NOTEBOOKS = $(wildcard $(SYNC_DIR)/*/*.rm)

all : metadata.txt content.txt notebooks

metadata.txt : $(METADATA)
	# clear metadata.txt
	echo '' > metadata.txt
	# for each .metadata file, add {<file id>: <contents of .metadata file>}
	$(foreach md,$^,echo {\"$(basename $(notdir $(md)))\": >> metadata.txt && cat $(md) >> metadata.txt && echo \} >> metadata.txt &&) echo "done"
	# edit the file so that it's valid json by wrapping in '[]' and adding ',' between objects
	sed -i '1s/^/[/;:a;N;$$!ba;s/}\n{/},\n{/g;$$a]' metadata.txt

content.txt : $(CONTENT)
	# clear content.txt
	echo '' > content.txt
	# for each .content file, add {<file id>: <contents of .content file>}
	$(foreach md,$^,echo {\"$(basename $(notdir $(md)))\": >> content.txt && cat $(md) >> content.txt && echo \} >> content.txt &&) echo "done"
	# edit the file so that it's valid json by wrapping in '[]' and adding ',' between objects
	sed -i '1s/^/[/;:a;N;$$!ba;s/}\n{/},\n{/g;$$a]' content.txt

notebooks : $(NOTEBOOKS)  
	# for each .rm file that has changed since the last sync, regenerate pdf
	mkdir -p $(BACKUP_DIR)
	($(foreach rm_file,$?,./lines-are-rusty/target/debug/lines-are-rusty -o $(BACKUP_DIR)/$(basename $(notdir $(rm_file))).pdf $(rm_file) &> /dev/null &) wait) && echo "done"
	touch notebooks