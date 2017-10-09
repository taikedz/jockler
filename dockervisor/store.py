import pathlib
import os
from dockervisor import files

# Store dir structure -------------------------
#
# images folder:
# each image should have a corresponding folder
# each folder contains
# * stable - the last item marked stable
# * last - the last instance that was run

homedir = str(pathlib.Path.home())
a_store_dir = [homedir, "dcv-data"]

def write_store_file(a_storefile, filedata):
    ''' Ensures the store exists and writes the image data

    Raises IOError if file could not be written or directory could not be created
    '''
    files.ensure_dir(a_storefile[:-1])
    files.write_file(a_storefile, filedata)

def write_data(filename, imagename, filedata):
    ''' Writes text data to file, overwriting existing data
    '''
    write_store_file(a_store_dir + [imagename, filename] , filedata )

def append_data(filename, imagename, filedata):
    ''' Writes new text data to the end of the file, after a new line
    '''
    olddata = read_data(filename, imagename)
    if olddata:
        filedata = os.linesep.join([olddata,filedata])

    write_data(filename, imagename, filedata )

def read_store_file(a_storefile):
    ''' Returns the file's data, or None if the file is not found
    '''
    return files.read_file(a_storefile)

def read_data(filename, imagename):
    ''' Read text data from file; returns string data, or None if file was not found
    '''
    return read_store_file(a_store_dir + [imagename, filename])
    

