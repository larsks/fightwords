#!/bin/sh

# Convert any files on the command line into PBM P4 files
# in the pbms/ directory.

for file in "$@"; do
  basename=${file##*/}
  gm convert -negate "$file" pbms/"${basename%.*}.pbm"
done
