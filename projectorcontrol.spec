a = Analysis([os.path.join(HOMEPATH,'support\\_mountzlib.py'), os.path.join(HOMEPATH,'support\\useTK.py'), os.path.join(HOMEPATH,'support\\useUnicode.py'), 'projectorcontrol.py'],
             pathex=['pyinstaller-1.3'])
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name='buildprojectorcontrol/projectorcontrol.exe',
          debug=False,
          strip=False,
          upx=False,
          console=False , icon='Projector.ico')
coll = COLLECT(TkTree(), exe,
               a.binaries,
               strip=False,
               upx=False,
               name='distprojectorcontrol')

