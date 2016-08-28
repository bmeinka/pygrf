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

pygrf.open(filename, filetype=None)
    open a file of the given filetype. If no type is provided, it will be
    figured out
pygrf.open_grf(filename)
    open a grf archive, returning the handler

GRF Archive
-----------

archive.get(filename)
    retrieve the bytes of the given file
archive.extract(filename, dest='')
    extract the given file to the given destination directory
archive.close()
    close the archive (should be handled with a context)
