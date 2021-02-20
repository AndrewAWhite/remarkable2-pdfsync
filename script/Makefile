METADATA =  $(wildcard $(SYNC_SYNC_DIR)/*.metadata)
CONTENT = $(wildcard $(SYNC_DIR)/*.content)
NOTEBOOKS = $(wildcard $(SYNC_DIR)/*/*.rm)

all : metadata.txt content.txt notebooks

metadata.txt : $(METADATA)
	# concatenate all .metadata files into a single file
	cat $^ > metadata.txt
	# edit the file so that it's valid json by wrapping in '[]' and adding ',' between objects
	sed -i '1s/^/[/;:a;N;$$!ba;s/}\n{/},\n{/g;$$a]' metadata.txt

content.txt : $(CONTENT)
	# concatenate all .content files into a single file
	cat $^ > content.txt
	# edit the file so that it is valid json
	sed -i '1s/^/[/;:a;N;$$!ba;s/}\n{/},\n{/g;$$a]' content.txt

notebooks : $(NOTEBOOKS)  
	# for each .rm file that has changed since the last sync, regenerate pdf
	mkdir -p $(BACKUP_DIR)
	$(foreach rm_file,$?,../lines-are-rusty/target/debug/lines-are-rusty -o $(BACKUP_DIR)/$(basename $(notdir $(rm_file))).pdf $(rm_file) &)
	touch notebooks