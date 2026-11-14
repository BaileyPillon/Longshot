"""Owned-item selection uses the game enum setter without granting inventory."""
import argparse
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RUN_ALL_ARGS = ["--cc", "gcc"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cc", default="gcc")
    args = parser.parse_args()
    code = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef struct { uint64_t x[32]; } Ctx;
typedef void (*A64Fn)(Ctx*);
#include "gpu/vk/longshot_items.h"
#define OOT_GAMEDATA_SLOT 1
static int calls, owned=1, event, loading, child=1, enabled=1, action, result;
static uint32_t capacity=8,taken,mask;
static Ctx called;
static void setter(Ctx*c) { calls++; called=*c; memset(c,0,sizeof *c); }
static A64Fn a64_lookup(uint64_t p) { assert(p==0x80400980ULL); return setter; }
static uint64_t oot_singleton(Ctx*c,uint64_t p) { (void)c;(void)p;return 100; }
static int oot_item_count(Ctx*c,const char*n) { (void)c;(void)n;return owned; }
static int oot_gamedata_bool(Ctx*c,uint32_t h,int*v) {
 (void)c;*v=h==0xcea220d3u?child:h==0xef2b60c2u?loading:owned;return 1;
}
static uint32_t recomp_load32(Ctx*c,uint64_t p) { (void)c;return p==100+0x270?capacity:taken; }
static int oot_event_playing(Ctx*c) { (void)c;return event; }
static void hos_log(const char*fmt,...) { (void)fmt; }
int rx_option(int id,int otherwise) { (void)otherwise; if(id==HOS_OPT_ITEM_WHEEL)return enabled;int a=action;action=0;return a; }
void rx_option_set(int id,int value) { if(id==HOS_OPT_QUICK_OWNED)mask=(uint32_t)value;else result=value; }
#include "host/oot_quick_items.inc"
int main(void) {
 Ctx c={{123,456}},before=c;
 assert(quick_hash("")==0 && quick_hash("foo")==0xf6a5c420u && quick_hash("hello")==0x248bfa47u);
 assert(quick_assign(&c,0,1));
 assert(calls==1 && !memcmp(&c,&before,sizeof c));
 assert(called.x[0]==100 && called.x[2]==0xa0029837u && called.x[1]==quick_hash("SlingShot"));
 assert(!quick_assign(&c,8,1) && !quick_assign(&c,0,0) && !quick_assign(&c,32,1));
 owned=0;assert(!quick_assign(&c,0,1) && !quick_assign(&c,17,1));owned=1;
 taken=4;assert(!quick_assign(&c,0,1));taken=0;
 assert(calls==1);
 action=9;child=0;quick_items_tick(&c,1000000000);
 assert(calls==2 && result==9 && called.x[2]==0xbc32ce24u && !(mask&1) && (mask&(1u<<8)));
 event=1;action=9;quick_items_tick(&c,2000000000);assert(calls==2 && result==-1 && mask==0);
 event=0;loading=1;action=9;quick_items_tick(&c,3000000000);assert(calls==2 && mask==0);
 loading=0;enabled=0;action=9;quick_items_tick(&c,4000000000);assert(calls==2 && action==0);
 puts("quick items: ownership, age, queue capacity, context, events and loads passed");
}
'''
    with tempfile.TemporaryDirectory(prefix="longshot-quick-") as folder:
        source, binary = Path(folder) / "quick.c", Path(folder) / "quick.exe"
        source.write_text(code, encoding="utf-8")
        subprocess.run([args.cc,"-std=c11","-Wall","-Wextra","-Werror","-I"+str(ROOT),str(source),"-o",str(binary)],check=True)
        subprocess.run([str(binary)],check=True)


if __name__ == "__main__":
    main()
