PyGRF
#####

A Python package for dealing with Ragnarok Online data files.

List of Goals
=============

- provide a simple and easy to use API
- open, read and unpack GRF and GPF archives
- open, read and parse various game files, such as GAT, SPR, etc.
- no external dependencies
- well tested using pytest

API
===

The API isn't complete, but I can start working it out here.

Entry Points
------------

pygrf.open_grf(filename)
    open a grf archive, returning the handler

GRF Archive
-----------

GRF.open(filename)
    open the given filename, returning a streamable object
GRF.extract(filename, dest='')
    extract the given file to the given destination directory
GRF.close()
    close teh archive
