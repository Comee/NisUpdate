'''
Created on 2014年11月19日

@author: Leo
'''

from distutils.core import setup
import py2exe
import sys
import os
import os.path
sys.argv.append ('py2exe')

options = {"py2exe":  
           {
                "compressed": False ,  # (boolean) create a compressed zipfile
                "unbuffered" :False ,  # if true, use unbuffered binary stdout and stderr
                "optimize": 2,
                
                'packages': 'encodings, pubsub, tkinter, lxml',
                "bundle_files": 2,
                "dll_excludes": [],
                "includes": [],
                "excludes": [],
                
            }  
          }  

setup(
    version="0.1.0",
    description="update nis application",
    name="update nis",
    options=options,
    zipfile=None,
#     data_files=[   os.path.join (sys.prefix, "DLLs", f) 
#                    for f in os.listdir (os.path.join (sys.prefix, "DLLs")) 
#                    if  (f.lower ().startswith (("tcl", "tk")) 
#                        and f.lower ().endswith ((".dll",))
#                        )
#                     ] ,
    windows=[{"script": "NisUpdate.py", "icon_resources": [(1, "favicon.ico")] }],
      
    ) 


