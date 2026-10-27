// SPDX-License-Identifier: MIT
// Temporary, opt-in glibc crash tracing inside the Arch guest; never Android.
#define _GNU_SOURCE
#include <execinfo.h>
#include <fcntl.h>
#include <signal.h>
#include <stdint.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <ucontext.h>
#include <unistd.h>

static int trace_fd = -1;
static volatile sig_atomic_t in_handler;

static void output(const char *s) {
    size_t n = 0;
    while (s[n]) ++n;
    while (n) {
        ssize_t written = write(trace_fd, s, n);
        if (written <= 0) break;
        s += written;
        n -= (size_t)written;
    }
}

static void hex_value(uintptr_t value) {
    char buf[2 + sizeof(uintptr_t) * 2 + 1];
    const char digits[] = "0123456789abcdef";
    buf[0]='0';buf[1]='x';
    for (size_t i=0; i<sizeof(uintptr_t)*2; ++i)
        buf[2+i]=digits[(value >> ((sizeof(uintptr_t)*2-1-i)*4)) & 15];
    buf[sizeof(buf)-1]=0;
    output(buf);
}

static void crash_handler(int sig, siginfo_t *info, void *context) {
    if (in_handler) _exit(128+sig);
    in_handler=1;
    output("\nAR client crash trace: signal=");hex_value((uintptr_t)sig);
    output(" fault_address=");hex_value((uintptr_t)info->si_addr);
    ucontext_t *uc=context;
    output("\nFAULT_PC=");
#if defined(__aarch64__)
    hex_value((uintptr_t)uc->uc_mcontext.pc);
    output("\nFAULT_LR=");hex_value((uintptr_t)uc->uc_mcontext.regs[30]);
#elif defined(__x86_64__)
    hex_value((uintptr_t)uc->uc_mcontext.gregs[REG_RIP]);
#endif
    output("\nBACKTRACE_BEGIN\n");
    // Best effort diagnostic unwinding; prewarmed in the constructor.
    void *frames[64];
    int count=backtrace(frames,64);
    backtrace_symbols_fd(frames,count,trace_fd);
    output("BACKTRACE_END\nMAPS_BEGIN\n");
    int maps=open("/proc/self/maps",O_RDONLY|O_CLOEXEC);
    if (maps>=0) {
        char buffer[4096];ssize_t n;
        while ((n=read(maps,buffer,sizeof(buffer)))>0) {
            ssize_t used=0;
            while (used<n) {ssize_t w=write(trace_fd,buffer+used,(size_t)(n-used));if(w<=0)break;used+=w;}
        }
        close(maps);
    }
    output("MAPS_END\n");
    _exit(128+sig);
}

// Prevent KCrash from replacing this diagnostic handler or starting DrKonqi.
// C spelling deliberately matches the exported C++ KCrash::initialize() symbol.
void _ZN6KCrash10initializeEv(void) {}

__attribute__((constructor)) static void initialize_trace(void) {
    const char *path=getenv("ARCHOHALL_TRACE_LOG");
    if (!path || !*path)path="/tmp/archohall-kwin-crash.log";
    trace_fd=open(path,O_WRONLY|O_APPEND|O_CREAT|O_CLOEXEC,0600);
    if (trace_fd<0)trace_fd=STDERR_FILENO;
    output("TRACE_READY pid=");hex_value((uintptr_t)getpid());output("\n");
    void *warmup[2];backtrace(warmup,2);
    stack_t alternate={0};alternate.ss_size=65536;
    alternate.ss_sp=mmap(NULL,alternate.ss_size,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    if(alternate.ss_sp!=MAP_FAILED)sigaltstack(&alternate,NULL);
    struct sigaction action={0};
    sigemptyset(&action.sa_mask);
    action.sa_sigaction=crash_handler;
    action.sa_flags=SA_SIGINFO|SA_ONSTACK;
    sigaction(SIGSEGV,&action,NULL);sigaction(SIGBUS,&action,NULL);sigaction(SIGABRT,&action,NULL);
}
