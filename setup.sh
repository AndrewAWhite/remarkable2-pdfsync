#!/bin/bash

# First ensure rust is installed

curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Next build lines-are-rusty

cd lines-are-rusty && cargo build

# Next ensure sqlite is installed

sudo apt-get update && sudo apt-get install sqlite3