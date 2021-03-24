import os
import sys


class FatalError( RuntimeError ):
    pass

app = os.path.basename(sys.argv[0])

files = [ "test.lua" ]

verbose = 0
