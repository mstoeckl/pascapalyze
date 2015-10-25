
# PASCAPALYZE

This is a script that reads in a .cap experiment file created by Pasco Capstone,
extracts the raw data from that file, and writes it out in a modified TSV format
that the programs XMGR/XVGR can use in a graph.

## How it works
The .cap files are actually zip files, containing the index `main.xml` and 
a directory full of data files. The data files contain a single array with
elements 12 bytes long; the last 8 bytes of those elements can be interpreted
as a 64-bit-long double. `main.xml` is sufficiently self-documenting that these
data files can be mapped to values.

## Limitations
Have only run this program on three different files; may not handle everything.