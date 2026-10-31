#!/usr/bin/env python3
"""Native dynamic-interposition tests, with a fake KWin ABI and real Unix socket."""
from pathlib import Path
import argparse
import json
import os
import socket
import subprocess
import tempfile
p=argparse.ArgumentParser(description=__doc__);p.add_argument('build',type=Path);p.add_argument('--mock-transport',action='store_true');a=p.parse_args();out=a.build.resolve()
mock=r'''
#include "kwin-api.hpp"
#include <cstdint>
static int calls;
static int layer_calls;
static long long value;
static bool valid;
static KWin::RenderLoop loop;
extern "C" int mock_calls() { return calls; }
extern "C" int mock_layer_calls() { return layer_calls; }
extern "C" long long mock_value() { return value; }
extern "C" bool mock_valid() { return valid; }
void KWin::RenderLoop::scheduleRepaint(Item *, OutputLayer *, Deadline deadline) {
    calls++; valid=deadline.has_value(); value=deadline ? deadline->time_since_epoch().count() : 0;
}
void KWin::OutputLayer::scheduleRepaint(Item *item, Deadline deadline) {
    layer_calls++; loop.scheduleRepaint(item,this,deadline);
}
'''
driver=r'''
#include "kwin-api.hpp"
#include <cstdio>
#include <cstring>
extern "C" int mock_calls();
extern "C" int mock_layer_calls();
extern "C" long long mock_value();
extern "C" bool mock_valid();
extern "C" int transport_hints() __attribute__((weak));
int main(int argc,char **argv) {
    if(argc!=2) return 2;
    KWin::RenderLoop loop; KWin::OutputLayer layer;
    auto item=reinterpret_cast<KWin::Item *>(&layer);
    auto time=std::chrono::steady_clock::time_point(std::chrono::nanoseconds(42));
    KWin::Deadline deadline=time;
    auto start=std::chrono::steady_clock::now();
    if(!std::strcmp(argv[1],"driver")) loop.scheduleRepaint(nullptr,nullptr,deadline);
    else if(!std::strcmp(argv[1],"content")) loop.scheduleRepaint(item,&layer,deadline);
    else if(!std::strcmp(argv[1],"damage")) loop.scheduleRepaint(nullptr,&layer,deadline);
    else if(!std::strcmp(argv[1],"catchup")) for(int i=0;i<1000;i++) layer.scheduleRepaint(nullptr,deadline);
    else if(!std::strcmp(argv[1],"layer-content")) layer.scheduleRepaint(item,deadline);
    else if(!std::strcmp(argv[1],"empty-deadline")) loop.scheduleRepaint(item,&layer,std::nullopt);
    else if(!std::strcmp(argv[1],"burst")) for(int i=0;i<1000;i++) loop.scheduleRepaint(item,&layer,deadline);
    else return 2;
    auto ns=std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now()-start).count();
    std::printf("{\"calls\":%d,\"layers\":%d,\"valid\":%s,\"time\":%lld,\"ns\":%lld,\"mock_hints\":%d}\n",mock_calls(),mock_layer_calls(),mock_valid()?"true":"false",mock_value(),(long long)ns,transport_hints?transport_hints():0);
}
'''
(out/'mock.cpp').write_text(mock);(out/'driver.cpp').write_text(driver)
cxx=os.environ.get('CXX','g++')
subprocess.run([cxx,'-std=c++20','-O0','-fPIC','-shared',str(out/'mock.cpp'),'-o',str(out/'libmockkwin.so')],check=True)
subprocess.run([cxx,'-std=c++20','-O0',str(out/'driver.cpp'),'-L'+str(out),'-lmockkwin','-Wl,-rpath,'+str(out),'-o',str(out/'driver')],check=True)
if a.mock_transport:
    (out/'transport.cpp').write_text(r'''#include <sys/socket.h>
#include <dlfcn.h>
#include <cerrno>
#include <cstdlib>
#include <cstddef>
static int hints;
extern "C" int transport_hints() { return hints; }
extern "C" int socket(int,int,int) { return 50000; }
extern "C" int connect(int,const sockaddr *,socklen_t) { if(std::getenv("MOCK_NO_LISTENER")) { errno=ENOENT; return -1; } return 0; }
extern "C" ssize_t send(int,const void *,size_t size,int) { hints++; return size; }
extern "C" int close(int fd) { if(fd==50000) return 0; using Fn=int(*)(int); static Fn real=(Fn)dlsym(RTLD_NEXT,"close");return real(fd); }
''')
    subprocess.run([cxx,'-shared','-fPIC',str(out/'transport.cpp'),'-ldl','-o',str(out/'libtransport.so')],check=True)
with tempfile.TemporaryDirectory(prefix='damage-test-') as temporary:
    sock=None
    address=str(Path(temporary)/'damage.sock')
    if not a.mock_transport:
        sock=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM)
        sock.bind(address);sock.setblocking(False)
    cases=[('driver',0,1,0),('content',1,1,0),('damage',1,1,0),('catchup',0,1000,1000),('layer-content',1,1,1),('empty-deadline',1,1,0),('burst',None,1000,0)]
    for name,expected,calls,layers in cases:
        env={**os.environ,'LD_PRELOAD':str(out/'anland-damage-68.so')+(':'+str(out/'libtransport.so') if a.mock_transport else ''),'ANLAND_DAMAGE_SOCKET':address}
        result=subprocess.run([str(out/'driver'),name],env=env,capture_output=True,text=True,timeout=5,check=True)
        data=json.loads(result.stdout)
        hints=data['mock_hints'] if a.mock_transport else 0
        while sock is not None:
            try:
                assert sock.recv(10)==b'\x01';hints+=1
            except BlockingIOError:break
        assert data['calls']==calls and data['layers']==layers,(name,data)
        assert data['valid']==(name!='empty-deadline'),(name,data)
        assert data['time']==(0 if name=='empty-deadline' else 42),(name,data)
        if expected is not None:assert hints==expected,(name,hints)
        else:assert 1<=hints<=data['ns']//2000000+1,(name,hints,data)
        print(f'{name}: original calls={calls}, hints={hints}: PASS')
    if sock is not None:sock.close()
    # No listener must not block or suppress the original KWin method.
    env['ANLAND_DAMAGE_SOCKET']=address
    if a.mock_transport:env['MOCK_NO_LISTENER']='1'
    result=subprocess.run([str(out/'driver'),'content'],env=env,capture_output=True,text=True,timeout=5,check=True)
    assert json.loads(result.stdout)['calls']==1
    print('absent listener: original method preserved: PASS')
print('8 native interposition/argument tests: PASS; transport='+('mocked (sandbox forbids AF_UNIX)' if a.mock_transport else 'real Unix datagrams'))
