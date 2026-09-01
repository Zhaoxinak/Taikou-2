# -*- coding: utf-8 -*-
import os, sys, struct
sys.path.insert(0,'.')
import savedata_loadflow_emu_ref as M
sav=open(M.SAV_PATH,'rb').read()
import time
t=time.time()
r=M.run(0,0,sav)
print('elapsed %.1fs'%(time.time()-t))
for k,v in r.items(): print('  %-9s %s'%(k,v))
