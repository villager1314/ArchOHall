#!/usr/bin/env python3
"""Check all bundled ELF dependencies and archive link-parent consistency."""
import struct
from pathlib import PurePosixPath
import zipfile
from prepare_project import PROJECT

def main():
    with zipfile.ZipFile(PROJECT/'app/src/main/assets/bootstrap-relocated.zip') as archive:
        names=set(archive.namelist())
        links={line.split('←',1)[1].removeprefix('./'):line.split('←',1)[0] for line in archive.read('SYMLINKS.txt').decode().splitlines()}
        available={n.rsplit('/',1)[-1] for n in names|set(links)}
        system={'libc.so','libdl.so','libm.so','liblog.so','libandroid.so','libz.so','libEGL.so','libGLESv2.so','libGLESv1_CM.so','libOpenSLES.so','libmediandk.so','libvulkan.so','libaaudio.so','libbinder_ndk.so','libjnigraphics.so','libnativewindow.so','libcamera2ndk.so','libsync.so'}
        missing=set();count=0
        for name in names:
            for parent in PurePosixPath(name).parents:
                if str(parent) in links:
                    raise RuntimeError(f'Archive writes through a link: {name}')
            data=archive.read(name)
            if data[:6]!=b'\x7fELF\x02\x01':
                continue
            count+=1
            offset=struct.unpack_from('<Q',data,32)[0]
            size,num=struct.unpack_from('<HH',data,54)
            loads=[];dynamic=None
            for i in range(num):
                ph=struct.unpack_from('<IIQQQQQQ',data,offset+i*size)
                if ph[0]==1:loads.append((ph[3],ph[2],ph[5]))
                if ph[0]==2:dynamic=(ph[2],ph[5])
            if not dynamic:continue
            needed=[];strings=None
            for pos in range(dynamic[0],sum(dynamic),16):
                kind,value=struct.unpack_from('<qQ',data,pos)
                if kind==0:break
                if kind==1:needed.append(value)
                if kind==5:strings=value
            if strings is None:continue
            base=next((po+strings-va for va,po,length in loads if va<=strings<va+length),None)
            if base is None:raise RuntimeError(name)
            for index in needed:
                start=base+index
                lib=data[start:data.index(b'\0',start)].decode()
                if lib not in available|system:missing.add((name,lib))
        if missing:raise RuntimeError(f'Missing bundled ELF dependencies: {sorted(missing)}')
        print(f'Validated {count} ELF files and {len(links)} symlinks.')

if __name__=='__main__':main()
