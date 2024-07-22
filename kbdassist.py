#!/usr/bin/python3

import evdev
import asyncio
import subprocess
import argparse
import shlex
import sys
from os.path import expanduser,exists
from os import system



# USB device physical location
PHYSDEV=''
# USB device physical location prefix
PHYSDEVPREFIX=''

# fragment of default device name
#PHYSDEVNAME='NOVATEK USB'
PHYSDEVNAME=''


# keycode for exiting the process from the console
EXITPROCESS='ALT_CTRL_SHIFT_C'

# times for long and longer press, in seconds, override from config file if needed via VLONG:<msec> and LONG:<msec> - CAUTION, number there is in MILLIseconds
TIME_LONG=0.3
TIME_VLONG=1

# initial value for strict timing (do NOT bubble longer keypress to shorter ones if longer not defined)
TIME_STRICT=False

# exit on errors, kill all processes instead of just crashing a specific task - for reading from more devices
ABORT_ON_ERROR=True

# timeout for key press combos, then assume no key pressed - for self healing of missing keyup events
MOD_TIMEOUT=15


# possible locations of config files, try in this order, override with -c
config_files=['~/.kbdassist.cfg','~/kbdassist.cfg','./kbdassist.cfg','/etc/kbdassist.cfg']


# defaults, modify in config file via MOD:key=prefix, clear with MOD_CLEAR
keyprefixes={
  'KEY_LEFTSHIFT':'SHIFT',
  'KEY_RIGHTSHIFT':'SHIFT',
  'KEY_LEFTCTRL':'CTRL',
  'KEY_RIGHTCTRL':'CTRL',
  'KEY_LEFTALT':'ALT',
  'KEY_RIGHTALT':'ALT',
  'KEY_LEFTMETA':'WIN',
  'KEY_RIGHTMETA':'WIN',
  'KEY_CAPSLOCK':'CAPS',
}


def printdefaultconfig():
  print("""# key-to-command binding for kbdassist.py

# default commands invoke OctoControl, 8control: https://www.improwis.com/projects/sw_8control/


# modifier key prefixes, in order
# VLONG_|LONG_ CAPS_ WIN_ ALT_ CTRL_ SHIFT_


# VLONG, LONG: time in milliseconds
VLONG: 1000
LONG:  300

# fraction of device name, to match
#DEVNAME:Keyboard

# key combination for process exiting, empty to disable, make sure the combo is valid!
EXITPROCESS: ALT_CTRL_SHIFT_C

# modifier key prefixes, in order
# VLONG_|LONG_ CAPS_ WIN_ ALT_ CTRL_ SHIFT_


# JOGPREF: prefix = distance
JOGPREF: CTRL_  = 0.1
JOGPREF:        = 1
JOGPREF: LONG_  = 5
JOGPREF: SHIFT_ = 10
JOGPREF: VLONG_ = 20
JOGPREF: CAPS_  = 50

# JOGKEY: key = command, # substituted for distance
JOGKEY: LEFT     = 8jog # -0 -0
JOGKEY: RIGHT    = 8jog -# -0 -0
JOGKEY: UP       = 8jog -0 -# -0
JOGKEY: DOWN     = 8jog -0 # -0
JOGKEY: PAGEUP   = 8jog -#
JOGKEY: HOME     = 8jog -#
JOGKEY: PAGEDOWN = 8jog #
JOGKEY: END      = 8jog #

# remove default key modifiers
#MOD_CLEAR

# modifiers for keys
#MOD: KEY_CAPSLOCK = CAPS
#MOD: KEY_TAB = TAB
# use empty prefix to disable a default one
#MOD: KEY_RSHIFT =


# cancel print
VLONG_C = 8cancel
LONG_C  = 8cancel
CAPS_C  = 8cancel
CTRL_C  = 8cancel

# start print
VLONG_CAPS_P = 8print

# pause/resume
P       = 8pause
VLONG_P = 8resume

# move and calibrate
# calibrate square, goto center
VLONG_CAPS_C = 8gmulti g29 g0x0y0
# zero to bed
VLONG_CAPS_Z = 8gmulti g30 g92z0 g0z10f2000
CAPS_Z       = 8gmulti g30 g92z0 g0z10f2000

# home
VLONG_H = 8home

# go to zero
VLONG_0 = 8g0 x0 y0 f2000

""")
  sys.exit(0)

cmdarr={}






# detect raspi, autoset USB physdev prefix
try:
  with open('/sys/firmware/devicetree/base/model','r') as f:
    s=f.read().strip()
    if s.startswith('Raspberry Pi 3 ') or s.startswith('Raspberry Pi 2 '):
      PHYSDEVPREFIX='usb-3f980000.usb-1.'
except:
  pass



def readcfgfile(fn,force=False):
   fn2=expanduser(fn)
   if not force and not exists(fn2):
     if args.verbose: print('trying "'+fn2+'", not found')
     return False

   if args.verbose: print('reading config file "'+fn2+'"')
   try:
     f=open(fn2,'r')
   except Exception as e:
     print('ERROR: cannot open keymap file "'+args.config+'"')
     print(e)
     return False

   global TIME_LONG,TIME_VLONG,EXITPROCESS
   jogarr_movekeys=[]
   jogarr_movepref=[]
   cmddef=[]

   def addarr(a,s):
     sa=s.split('=',1)
     if len(sa)<2: return
     a.append([sa[0].strip(),sa[1].strip()])

   def adddict(a,s):
     sa=s.split('=',1)
     if len(sa)<2: return
     a[sa[0].strip()]=sa[1].strip()
     if sa[1].strip()=='': del a[sa[0].strip()] # if empty, remove from dict

   def getint(s,default):
     a=s.split(':')
     #print(a)
     try: return int(a[1].strip())
     except:
       print('WARN: cannot convert "'+s+'" to int, keeping default')
       return default

   a=f.read().split('\n')
   for s in a:
     s=s.strip()
     if len(s)<1: continue
     if s[0]=='#' or s[0]==';' or s[0]=='/': continue
     while '  ' in s: s=s.replace('  ',' ')
     #print(s)
     if s.startswith('MOD_CLEAR'): keyprefixes.clear();continue
     if s.startswith('LONG:'):  TIME_LONG =getint(s,TIME_LONG )/1000;continue
     if s.startswith('VLONG:'): TIME_VLONG=getint(s,TIME_VLONG)/1000;continue
     if s.startswith('EXITPROCESS:'): EXITPROCESS=s[12:].strip();continue
     if s.startswith('DEVNAME:'):
       if args.devname=='': args.devname=s[8:].strip()
       print('DEVNAME from config: "'+args.devname+'"')
       continue
     if '=' not in s: continue
     if s.startswith('JOGPREF:'): addarr(jogarr_movepref,s[8:]);continue
     if s.startswith('JOGKEY:'):  addarr(jogarr_movekeys,s[8:]);continue
     if s.startswith('MOD:'): adddict(keyprefixes,s[4:]);continue
     addarr(cmddef,s)

   f.close()

   if args.verbose: print('  read keybinds:',len(cmddef))

   for pref in jogarr_movepref:
     for key in jogarr_movekeys:
       cmdarr[pref[0]+key[0]]=key[1].replace('#',pref[1])

   if args.verbose: print('  generated jog keybinds:',len(cmdarr))

   for x in cmddef:
     if x[0] in cmdarr: print('WARN: cfgfile: duplicated key:',x[0])
     cmdarr[x[0]]=x[1]

   if args.verbose: print('  total keybinds:',len(cmdarr))

   return True


# try multiple config files from array
def readcfg():
   if args.config != '': return readcfgfile(args.config,force=True)
   for x in config_files:
     if readcfgfile(x): return True
   print('Config file not found: tried',config_files)
   return False
#   return readcfgfile(args.config)


#def doalert(alert):
#  subprocess.Popen(["alert", "-P","door",alert])

# convert command from string to array, where applicable, for faster execution
# if pipe or redirect or multiple commands present, leave as string to execute via /bin/sh
def convcmdarr():
  for x in cmdarr:
    if '|' not in cmdarr[x] and '>' not in cmdarr[x] and ';' not in cmdarr[x]:
      cmdarr[x]=shlex.split(cmdarr[x])



# execute command with list of options
def doexec_arr(a):
  if not args.quiet: print('  EXEC:',a)
  try:
    subprocess.Popen(a)
  except Exception as e:
    print('  EXEC error:',e)

# execute shell command as string
def doexec_shell(cmd):
  if not args.quiet: print('  ShellEXEC:',cmd)
  try:
    system(cmd)
  except Exception as e:
    print('  ShellEXEC error:',e)

# execute command, decide if shell or list
def doexec_auto(cmd):
  if args.dryrun:
    if isinstance(cmd,list): print('  would exec:',' '.join(cmd))
    else: print('  would shellexec:',cmd)
    return
  if isinstance(cmd,list): doexec_arr(cmd)
  else: doexec_shell(cmd)


## execute command, split string to list via shell lexer
#def doexec(cmd):
#  try:
#    a=shlex.split(cmd)
#  except Exception as e:
#    print('  EXEC parse error:',e,'with:',cmd)
#    return
#  doexec_arr(a)



def handle_keypress(name,presslen,pressed,dev):
  # strip KEY_ prefix
  if name[:4]=='KEY_': name=name[4:]

  # attach prefix [CAPS_][WIN_][ALT_][CTRL_][SHIFT_]
  # do prefixes via configurable array
  pref=[]
  for x in keyprefixes:
    if x in pressed and keyprefixes[x] not in pref:
      pref.append(keyprefixes[x])
  for x in pref:
    name=x+'_'+name

  # old code, do prefixes directly
  #if 'KEY_LEFTSHIFT' in pressed or 'KEY_RIGHTSHIFT' in pressed: name='SHIFT_'+name
  #if 'KEY_LEFTCTRL'  in pressed or 'KEY_RIGHTCTRL'  in pressed: name='CTRL_' +name
  #if 'KEY_LEFTALT'   in pressed or 'KEY_RIGHTALT'   in pressed: name='ALT_'  +name
  #if 'KEY_LEFTMETA'  in pressed or 'KEY_RIGHTMETA'  in pressed: name='WIN_'  +name
  #if 'KEY_CAPSLOCK'  in pressed:                                name='CAPS_' +name

  if name==EXITPROCESS:
    print('exiting')
    sys.exit(0)

  # attach VLONG_ or LONG_ prefix, for verylong and long key presses
  if presslen>TIME_VLONG: name='VLONG_'+name
  elif presslen>TIME_LONG: name='LONG_'+name

  # print what key was pressed, with all the prefixes
  print('KEY:',name,end='')
  if len(pressed)>0: print(' ',pressed,end='')
  if args.showevents and not args.quiet: print('   |  ',dev,end='')
  print()

  if args.showevents and name=='CTRL_C':
    print('Ctrl-C, exiting')
    sys.exit(0)

  # match and execute command
  if name in cmdarr: return doexec_auto(cmdarr[name])
  if TIME_STRICT: return False # do not try to bubble through to shorter keypresses
  # if VLONG not found, try LONG, then short
  if name.startswith('VLONG_'):
    name=name[1:]
    if args.verbose: print('  trying',name)
    if name in cmdarr: return doexec_auto(cmdarr[name])
  if name.startswith('LONG_'):
    name=name[5:]
    if args.verbose: print('  trying',name)
    if name in cmdarr: return doexec_auto(cmdarr[name])
  if args.verbose: print('  ...command not assigned')



# translate keypress ID to meaningful name
def getkeyname(code):
  try: keyname=evdev.ecodes.KEY[code]
  except: # try buttons
    try: keyname=evdev.ecodes.BTN[code]
    except: return '['+str(code)+']'
  if isinstance(keyname,list): return keyname[0]
  if keyname=='?': return '['+str(code)+']'
  return keyname


# handle HID keypress event itself
async def handle_event(dev):
  pressed=set() # currently pressed keys
  pressed2=set() # combo keys, clear on release of all keys
  keywhen=999999999999 # init to too big nonsense
  isctrl=False
  MSC_EVCODES=['SERIAL','PULSELED','GESTURE','RAW','SCAN','TIMESTAMP']
  sys.stdout.flush()
  try:
    async for event in dev.async_read_loop():

      # debug code: showing all events
      if args.showallevents:
        # various names defined in /usr/include/linux/input-event-codes.h
        if not keywhen==event.timestamp():
          print('---- ',dev)
        keywhen=event.timestamp()
        #print(event.type,getkeyname(event.code),event,end='')
        if args.quiet and event.type==0 and event.code==0: continue # ignore SYN_REPORT events, annoyingly spammy at times
        print('  ',end='')
        print('type{:2}, code{:4}, '.format(event.type,event.code),end='')
        if event.type>=4: print('val 0x{:08x}'.format(event.value),end='')
        else:             print('val{:-11}'.format(event.value),end='')
        print(' |',evdev.categorize(event),end='')
        if event.type==4:
          if event.code<len(MSC_EVCODES): print(', MSC_'+MSC_EVCODES[event.code],end='')
        #if not args.quiet: print('   |  ',event,end='')
        print()

        # exit on ctrl-c, kludgy and hardcoded to avoid extra lookups
        if event.type==1:
          if event.code==29 or event.code==97: isctrl=(event.value>0) # key event, KEY_LEFTCTRL or KEY_RIGHTCTRL, isctrl True when down or hold
          if isctrl and event.code==46 and event.value==0: # key event, KEY_C, up
            print('Ctrl-C, exiting')
            sys.exit(0)

        sys.stdout.flush()
        continue

      if event.type==0: continue # ignore sync events
      if event.type!=1: continue # ignore non-key events

      if event.value==1: # pressed
        keydown=event.code
        if event.timestamp()-keywhen>MOD_TIMEOUT and len(pressed2)>0:
          print('CAUTION: too long from last keypress, clearing modifiers array')
          pressed.clear()
          pressed2.clear()
        keywhen=event.timestamp()
        keyname=getkeyname(keydown)
        pressed.add(keyname)
        pressed2.add(keyname)
      elif event.value==0: #released
        keyup=event.code
        keyupname=getkeyname(keyup)
        pressed.discard(keyupname)
        if len(pressed)==0: pressed2.clear()
        handle_keypress(keyupname,event.timestamp()-keywhen,pressed2,dev)
        keyname=''
      sys.stdout.flush()
  except IOError as e:
#    print("IOEXCEPT!",e)
#    printdev('device: ',dev)
    printdev('IOEXCEPT! '+str(e)+': ',dev)
    if ABORT_ON_ERROR:
      print('Aborting!')
      sys.exit(2)
    return False
  except Exception as e:
#    print("EXCEPT!",e)
    printdev('EXCEPT! '+str(e)+': ',dev)
    if ABORT_ON_ERROR:
      print('Aborting!')
      sys.exit(2)
    return False




# print individual device
def printdev(pref,device):
  print('{}path: {:18s}  addr: {:32s}  name: {}'.format(pref,device.path,device.phys,device.name))

# list detected devices
def listdevs(pref=''):
  devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
  for device in devices:
    printdev(pref,device)


def printdevevents(device):
  print('=======')
  print('DEVICE:')
  print('   devpath:',device.path)
  print('   devaddr:', device.phys)
  print('   devname:',device.name)
  print('EVENTS:')
  cap=device.capabilities(verbose=True)
  for x in cap:
    print('  ',x)
    for y in cap[x]:
      print('      ',y)


# print defined command-to-key bindings, actual setting of modifiers, times and process exit command
def listcommands():
  for x in cmdarr:
    print('{:15s}:  {}'.format(x,cmdarr[x]))
  print()

  print('MODIFIERS:')
  l=[]
  for x in keyprefixes:
    print('{:15s}:  {}'.format(x,keyprefixes[x]))
    if keyprefixes[x] not in l: l.append(keyprefixes[x])
  print('prefix order: ',end='')
  for t in range(0,len(l)):
    #print('['+l[len(l)-t-1]+'_]',end='')
    print(' '+l[len(l)-t-1],end='')
  print()

  print()
  print('time LONG: ',round(1000*TIME_LONG),'ms')
  print('time VLONG:',round(1000*TIME_VLONG),'ms')

  print()
  print('EXITPROCESS:',EXITPROCESS)




def cmdlineparse():
  parser = argparse.ArgumentParser(prog='kbdassist.py',description='executes commands on keypresses and their combinations',epilog='')
  parser.add_argument('-d' ,'--device',      type=str, default='', help='/dev/input device')
  parser.add_argument('-dn','--devname',     type=str, default=PHYSDEVNAME, help='fraction of device name, default="'+PHYSDEVNAME+'"')
  parser.add_argument('-da','--devaddr',     type=str, default=PHYSDEV, help='device phys address or suffix (eg. 4, 2.1, 3.2.3), match to last slash')
  parser.add_argument('-dp','--devprefix',   type=str, default=PHYSDEVPREFIX, help='device address prefix, default="'+PHYSDEVPREFIX+'"')
  parser.add_argument('-A' ,'--matchall',    action='store_const', default=False, const=True, help='match all devices')
  parser.add_argument('-l' ,'--list',        action='store_const', default=False, const=True, help='list HID devices present')
  parser.add_argument('-L' ,'--listevents',  action='store_const', default=False, const=True, help='list events for matching device(s)')
  parser.add_argument('-E' ,'--showevents',  action='store_const', default=False, const=True, help='show detected event names and source devices, ignore config')
  parser.add_argument('-M' ,'--forcemods',   action='store_const', default=False, const=True, help='like -E, but force reading of config/modifier')
  parser.add_argument('-C' ,'--listcommands',action='store_const', default=False, const=True, help='list set commands')
  parser.add_argument('-q' ,'--quiet',       action='store_const', default=False, const=True, help='suppress most output')
  parser.add_argument('-v' ,'--verbose',     action='store_const', default=False, const=True, help='print more details')
  parser.add_argument('-D' ,'--dryrun',      action='store_const', default=False, const=True, help='show command instead of executing')
  parser.add_argument('-T' ,'--stricttime',  action='store_const', default=False, const=True, help='do not try VLONG-LONG-normal if longer command not found')
  parser.add_argument('-c' ,'--config',      type=str, default='', help='keys config file, default='+str(config_files))
  parser.add_argument('--printdefaultconfig',action='store_const', default=False, const=True, help='print default config file content')
  parser.add_argument('-F' ,'--showallevents',action='store_const', default=False, const=True, help='show ALL detected events (not just keypresses), ignore config; -q to suppress SYN_REPORT')
  return parser


parser=cmdlineparse()
args = parser.parse_args()
#print(args)

if args.forcemods: args.showevents=True
if args.showallevents: args.showevents=True


if args.printdefaultconfig:
  printdefaultconfig()
  sys.exit(0)

# list devices
if args.list:
  listdevs()
  sys.exit(0)


# read config file
if (not args.showevents and not args.listevents) or args.forcemods:
  if not readcfg():
    print('Aborting.')
    sys.exit(1)

# list commands, depens on read config
  if args.listcommands:
    listcommands()
    sys.exit(0)


matched_devices=[]

devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
for device in devices:
  match=False
  if args.matchall: match=True
  elif device.phys.startswith(args.devprefix+args.devaddr+'/'): match=True
  elif args.devname!=''   and args.devname in device.name: match=True
  elif args.device!=''    and args.device==device.path: match=True
  if not match: continue

  if args.listevents:
    printdevevents(device)
  else:
    if not args.quiet: printdev('Attaching: ',device)
  matched_devices.append(evdev.InputDevice(device.path))


if len(matched_devices)==0:
  print('Present devices:')
  listdevs(pref='  ')
  print()
  print('ERROR: no match in devices, none watched')
  print('Aborting.')
  sys.exit(1)

# list currently assigned keys and exec events
if args.listevents: sys.exit(0)

# convert command array to array of parameters, avoid parsing at every command
convcmdarr()


# running tasks
async_tasks=set()

# attach event monitors
for hid_device in matched_devices:
  task=asyncio.ensure_future(handle_event(hid_device))
  async_tasks.add(task)
  hid_device.grab() # avoid passing events to other processes/kernel




loop = asyncio.get_event_loop()

if args.showevents:
  print()
  if args.showallevents:
    print('Showing ALL events',end='')
    if args.quiet: print(' except SYN_REPORT',end='')
  else:
    print('Showing key(up) events ',end='')
    if args.forcemods: print('with modifiers from config file',end='')
    else: print('with default modifiers',end='')
  print(', ctrl-C to exit')

else:
  if not args.quiet: print('Initialized. Waiting for keypresses.')
  if not args.quiet and EXITPROCESS!='': print('Press '+EXITPROCESS+' to exit.')

if args.dryrun: print('Dry run, will not exect commands.');

if args.verbose: print('Starting asyncio loop...')
if not args.quiet: print()
sys.stdout.flush()

#loop.run_forever()
try:
    loop.run_forever()
except KeyboardInterrupt:
    print('ctrl-c')
finally:
    if args.verbose: print('KILLING TASKS')
    sys.stdout.flush()
    for t in async_tasks:
      if args.verbose: print(t);sys.stdout.flush()
      t.cancel()

    loop.stop()
    loop._run_once()

    loop.close()
    if not args.quiet: print('finish')

#loop._run_once()
