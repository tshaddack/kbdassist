Autogenerated from [https://www.improwis.com/projects/sw_kbdassist/](https://www.improwis.com/projects/sw_kbdassist/)






Keyboard Assistant







Keyboard Assistant
==================



---

[Problem](#Problem "#Problem")  
[Solution](#Solution "Solution")  
[HID devices primer](#HIDdevicesprimer "HID devices primer")  
      [key events naming](#keyeventsnaming "HID devices primer.key events naming")  
[Devices](#Devices "Devices")  
      [device selection](#deviceselection "Devices.device selection")  
      [device/event debugging](#deviceeventdebugging "Devices.device/event debugging")  
[key to action mapping](#keytoactionmapping "key to action mapping")  
      [key event naming and modifier keys handling](#keyeventnamingandmodifierkeyshandling "key to action mapping.key event naming and modifier keys handling")  
            [key press length](#keypresslength "key to action mapping.key event naming and modifier keys handling.key press length")  
            [event monitor example](#eventmonitorexample "key to action mapping.key event naming and modifier keys handling.event monitor example")  
            [event monitor example, full event list](#eventmonitorexamplefulleventlist "key to action mapping.key event naming and modifier keys handling.event monitor example, full event list")  
      [config file](#configfile "key to action mapping.config file")  
      [command execution](#commandexecution "key to action mapping.command execution")  
[Commandline options](#Commandlineoptions "Commandline options")  
      [examples](#examples "Commandline options.examples")  
[Download](#Download "Download")  
[TODO](#TODO "TODO")  


---

Problem
-------



Fiddling with a CNC machine or a 3d printer requires sending arbitrary commands. Setting up a workpiece,
adjusting the head, running calibration or touch probe, all gets rather annoying when it involves a disco dance
between the machine and the laptop. Dedicated terminal is not always worth the cost.





---

Solution
--------



A regular USB keyboard gets attached to the machine. A python script (what else these days) is written
to take the [HID](https://en.wikipedia.org/wiki/USB_HID "Wikipedia link: USB HID") events from selected devices, track key press/release events to facilitate
key combinations, and measure time from key press to release to differentiate between short, long, and even longer
keypresses.





---

HID devices primer
------------------



The HID-class devices, or human-interface devices, are standardized devices providing events from the
user interface. An example of an event is a key press, key repeat or key release, a mouse button press or release,
a touchscreen touch, a mouse move, or a joystick move.




Such input device manifests in the linux system as a /dev/input/eventX (or similar) device node. Events
(small binary data chunks) and device descriptors (giving meaning to the binary mess) can be acquired from the device.




Many devices have multiple sub-devices in them. A keyboard controller can easily become four /dev/input devices, one for
regular keypresses, one for multimedia keys (consumer control), one for power/sleep buttons (system control), and one for
mouse events. Often the full set of supported functions claimed is not realized in hardware, as the same controller
may be missing keys or other peripherals. Sometimes these can be hacked into the hardware.



### key events naming



The keys have assigned numbers, paired to names. Partial example:

```
       ('KEY_ESC', 1)
       ('KEY_1', 2)
       ('KEY_2', 3)
       ('KEY_3', 4)
       ('KEY_4', 5)
       ('KEY_5', 6)
...
  
       ('KEY_J', 36)
       ('KEY_K', 37)
       ('KEY_L', 38)
       ('KEY_SEMICOLON', 39)
       ('KEY_APOSTROPHE', 40)
       ('KEY_GRAVE', 41)
       ('KEY_LEFTSHIFT', 42)
       ('KEY_BACKSLASH', 43)
...
  
       ('KEY_CHANNELUP', 402)
       ('KEY_CHANNELDOWN', 403)
       ('KEY_LAST', 405)
       ('KEY_NEXT', 407)
       ('KEY_RESTART', 408)

```




On the raw events level, there is no difference between keys. A key "A" is the same KEY\_A whether pressed together
with other keys or alone. The modifier keys like ctrl or shift or so have no special meaning here, that is handled later
downstream in the processing.




The keypress events are of three types:
* key down
* key repeat
* key up





---

Devices
-------



The [python-evdev](https://python-evdev.readthedocs.io/en/latest/ "remote link: https://python-evdev.readthedocs.io/en/latest/") library is chosen as the core process.



### device selection



The evdev library provides three pieces of information for each device, via evdev.list\_devices():
* path, the /dev/input/whatever device node
* phys, the physical device location in the tree
* name, the device descriptor name

More data may be possible to request via additional library calls.




Multiple devices can be opened at once:
* all, suitable for less work with only one HID device attached
* name match, where a substring has to match part of the device name
* device, where the device path is explicitly specified (may not be the best as the numbers change when devices are disconnected and reconnected)
* phys path, where the beginning (specified as prefix-suffix pair) has to match up to a slash; for convenience, this is split to prefix and suffix.




Examples:




Raspberry Pi 3B with a single USB keyboard

```
path: /dev/input/event3   addr: usb-3f980000.usb-1.4/input1       name: NOVATEK USB Keyboard
path: /dev/input/event2   addr: usb-3f980000.usb-1.4/input1       name: NOVATEK USB Keyboard Consumer Control
path: /dev/input/event1   addr: usb-3f980000.usb-1.4/input1       name: NOVATEK USB Keyboard System Control
path: /dev/input/event0   addr: usb-3f980000.usb-1.4/input0       name: NOVATEK USB Keyboard

```




Raspberry Pi 2B with a wireless 2.4GHz keyboard dongle, a Logitech wireless dongle, and a touchscreen

```
path: /dev/input/event5   phys: usb-3f980000.usb-1.3.4/input1     name: 2.4G Composite Devic System Control
path: /dev/input/event4   phys: usb-3f980000.usb-1.3.4/input1     name: 2.4G Composite Devic Consumer Control
path: /dev/input/event3   phys: usb-3f980000.usb-1.3.4/input1     name: 2.4G Composite Devic Mouse
path: /dev/input/event2   phys: usb-3f980000.usb-1.3.4/input0     name: 2.4G Composite Devic
path: /dev/input/event1   phys: usb-3f980000.usb-1.3.3/input2:1   name: Logitech K230
path: /dev/input/event0   phys: usb-3f980000.usb-1.3.1/input0     name: 深圳市全动电子技术有限公司 ByQDtech 触控USB鼠标

```




a give-or-take standard PC with a keyboard and some internal peripherals

```
path: /dev/input/event5   addr: ALSA                              name: HDA Intel PCH Headphone
path: /dev/input/event4   addr: eeepc-wmi/input0                  name: Eee PC WMI hotkeys
path: /dev/input/event3   addr: isa0061/input0                    name: PC Speaker
path: /dev/input/event2   addr: LNXPWRBN/button/input0            name: Power Button
path: /dev/input/event1   addr: PNP0C0C/button/input0             name: Power Button
path: /dev/input/event0   addr: isa0060/serio0/input0             name: AT Translated Set 2 keyboard

```




The raspberry pi boards have a single USB controller, with usb-3f980000.usb-1. as the constant part, followed by
dot-separated number of port (one number on the raspi port itself, then additional ones for the eventual chain of
hubs). This allows addressing of devices via physical port location; different keyboards can be plugged into the
same port and still operate properly.




When raspi board is detected, the constant part is set to the phys prefix, so devices can be addressed as "4" (for the usb-1.4 ones in the
3B example), or "3.4", "3.3" or "3.1" for the ones from the 2B example. The part after the end slash is ignored; eg.
the 3B example opens both input0 and input1 devices, or, all four /dev/input/eventX ones.



### device/event debugging



The above examples are obtained by listing the available HID devices.




It is also possible to list the available events, reported by the HID descriptor:
* [events-all-pi3.txt](events-all-pi3.txt "local file")
* [events-all-pi2.txt](events-all-pi2.txt "local file")
* [events-all-pc.txt](events-all-pc.txt "local file")




For tracing the real appearance of events, an option is provided that skips loading of the execute commands,
and instead just shows the event name and the device originating it.





---

key to action mapping
---------------------



To do something useful, the keypress event has to not be just recognized, but also followed up with
an action. This is achieved by pairing a command to execute.



### key event naming and modifier keys handling



Combo keys can be useful. Different functionalities can be assigned to combination of SHIFT-key, CTRL-key, ALT-SHIFT-key,
or even CAPS-WIN-CTRL-key. Caps Lock, otherwise pretty useless, can be used as another modifier key, eg. for various macros.




The kbdassist code handles the modifier keys by adding them into a set-type variable when pressed, removed when
released.




When a key is pressed, a timestamp is remembered in order to measure the keypress length.
When the key is released, a handlekey() function is invoked, with the keypress length, and the list of pressed and
not-yet-released keys. Presence of modifier keys can be checked in the list, and the active ones are prepended
to the key name as prefixes.




The main key name gets the KEY\_ prefix stripped, to simplify the naming.




The modifier keys are as follows:
* KEY\_CAPSLOCK: prepends CAPS\_
* KEY\_LEFTMETA, KEY\_RIGHTMETA: prepends WIN\_
* KEY\_LEFTALT, KEY\_RIGHTALT: prepends ALT\_
* KEY\_LEFTCTRL, KEY\_RIGHTCTRL: prepends CTRL\_
* KEY\_LEFTSHIFT, KEY\_RIGHTSHIFT: prepends SHIFT\_




The order of the keys is fixed. All of them together with KEY\_X result in CAPS\_WIN\_ALT\_CTRL\_SHIFT\_X.




The key modifiers are usual but can be done as arbitrary. For use of a numeric keypad, the +,-,\*,/,Enter
and other keys can be assigned as modifiers, whether by separate names
or by adding them to definitions of existing ones. MOD: and MOD\_CLEAR can be used for modifying the
default table. The -C option lists, inter alia, the configured modifiers and their prefix order.




On release of a modifier key, the keypress handler is invoked on it too. Just do not assign anything
to execute with these alone.



#### key press length



The code recognizes three brackets of keypress durations; normal, long, verylong. The length is added
to the key event name as another prefix, the very first from the left:
* (none) - for short keypress
* LONG\_ - for long keypress, by default above 300 milliseconds
* VLONG\_ - for very long keypress, by default above 1000 milliseconds




A long ctrl-X event will therefore be LONG\_CTRL\_X. A very long press of key 'C' will be VLONG\_C.




Unless strict timing is requested (-T option), event not defined for a longer keypress
will be attempted with shorter definition; VLONG\_C if not found will be tried as LONG\_C and then as C.




In that case, action defined for C will be executed for LONG\_C and VLONG\_C as well. Action defined for LONG\_D
will be executed also with VLONG\_D, but ignored by event D.



#### event monitor example



```
KEY: UP   |   device /dev/input/event2, name "2.4G Composite Devic", phys "usb-3f980000.usb-1.3.4/input0"
KEY: ENTER   |   device /dev/input/event2, name "2.4G Composite Devic", phys "usb-3f980000.usb-1.3.4/input0"
KEY: DOWN   |   device /dev/input/event2, name "2.4G Composite Devic", phys "usb-3f980000.usb-1.3.4/input0"
KEY: SEARCH   |   device /dev/input/event4, name "2.4G Composite Devic Consumer Control", phys "usb-3f980000.usb-1.3.4/input1"
KEY: HOMEPAGE   |   device /dev/input/event4, name "2.4G Composite Devic Consumer Control", phys "usb-3f980000.usb-1.3.4/input1"
KEY: BTN_LEFT   |   device /dev/input/event3, name "2.4G Composite Devic Mouse", phys "usb-3f980000.usb-1.3.4/input1"
KEY: BTN_RIGHT   |   device /dev/input/event3, name "2.4G Composite Devic Mouse", phys "usb-3f980000.usb-1.3.4/input1"
KEY: LONG_BTN_RIGHT   |   device /dev/input/event3, name "2.4G Composite Devic Mouse", phys "usb-3f980000.usb-1.3.4/input1"
KEY: VLONG_BTN_RIGHT   |   device /dev/input/event3, name "2.4G Composite Devic Mouse", phys "usb-3f980000.usb-1.3.4/input1"
KEY: W   |   device /dev/input/event2, name "2.4G Composite Devic", phys "usb-3f980000.usb-1.3.4/input0"
KEY: E   |   device /dev/input/event2, name "2.4G Composite Devic", phys "usb-3f980000.usb-1.3.4/input0"
KEY: R   |   device /dev/input/event2, name "2.4G Composite Devic", phys "usb-3f980000.usb-1.3.4/input0"
KEY: SHIFT_W  {'KEY_W', 'KEY_LEFTSHIFT'}   |   device /dev/input/event2, name "2.4G Composite Devic", phys "usb-3f980000.usb-1.3.4/input0"
KEY: SHIFT_E  {'KEY_E', 'KEY_W', 'KEY_LEFTSHIFT'}   |   device /dev/input/event2, name "2.4G Composite Devic", phys "usb-3f980000.usb-1.3.4/input0"
KEY: SHIFT_R  {'KEY_E', 'KEY_R', 'KEY_W', 'KEY_LEFTSHIFT'}   |   device /dev/input/event2, name "2.4G Composite Devic", phys "usb-3f980000.usb-1.3.4/input0"
KEY: LONG_LEFTSHIFT   |   device /dev/input/event2, name "2.4G Composite Devic", phys "usb-3f980000.usb-1.3.4/input0"
KEY: CAPS_W  {'KEY_CAPSLOCK', 'KEY_W'}   |   device /dev/input/event2, name "2.4G Composite Devic", phys "usb-3f980000.usb-1.3.4/input0"
KEY: CAPS_E  {'KEY_CAPSLOCK', 'KEY_E', 'KEY_W'}   |   device /dev/input/event2, name "2.4G Composite Devic", phys "usb-3f980000.usb-1.3.4/input0"
KEY: LONG_CAPSLOCK   |   device /dev/input/event2, name "2.4G Composite Devic", phys "usb-3f980000.usb-1.3.4/input0"
KEY: VLONG_CAPS_SHIFT_LEFTSHIFT  {'KEY_CAPSLOCK', 'KEY_LEFTSHIFT'}   |   device /dev/input/event2, name "2.4G Composite Devic", phys "usb-3f980000.usb-1.3.4/input0"
KEY: VLONG_CAPSLOCK   |   device /dev/input/event2, name "2.4G Composite Devic", phys "usb-3f980000.usb-1.3.4/input0"
KEY: SHIFT_G  {'KEY_G', 'KEY_LEFTSHIFT'}   |   device /dev/input/event2, name "2.4G Composite Devic", phys "usb-3f980000.usb-1.3.4/input0"
KEY: LONG_LEFTSHIFT   |   device /dev/input/event2, name "2.4G Composite Devic", phys "usb-3f980000.usb-1.3.4/input0"
KEY: CAPS_G  {'KEY_CAPSLOCK', 'KEY_G'}   |   device /dev/input/event2, name "2.4G Composite Devic", phys "usb-3f980000.usb-1.3.4/input0"
KEY: LONG_CAPSLOCK   |   device /dev/input/event2, name "2.4G Composite Devic", phys "usb-3f980000.usb-1.3.4/input0"
KEY: CTRL_SHIFT_G  {'KEY_LEFTCTRL', 'KEY_G', 'KEY_LEFTSHIFT'}   |   device /dev/input/event2, name "2.4G Composite Devic", phys "usb-3f980000.usb-1.3.4/input0"
KEY: CAPS_SHIFT_Y  {'KEY_Y', 'KEY_CAPSLOCK', 'KEY_T', 'KEY_LEFTSHIFT'}   |   device /dev/input/event2, name "2.4G Composite Devic", phys "usb-3f980000.usb-1.3.4/input0"
KEY: VLONG_CAPS_SHIFT_LEFTSHIFT  {'KEY_Y', 'KEY_CAPSLOCK', 'KEY_T', 'KEY_LEFTSHIFT'}   |   device /dev/input/event2, name "2.4G Composite Devic", phys "usb-3f980000.usb-1.3.4/input0"
KEY: VLONG_CAPSLOCK   |   device /dev/input/event2, name "2.4G Composite Devic", phys "usb-3f980000.usb-1.3.4/input0"
KEY: CTRL_C  {'KEY_C', 'KEY_LEFTCTRL'}   |   device /dev/input/event2, name "2.4G Composite Devic", phys "usb-3f980000.usb-1.3.4/input0"
Ctrl-C, exiting

```
**Beware, some more unusual key combinations may not be handled by the scanning matrix of a given keyboard device. Test, test, test!**

This is what the -E (and -M) option is for.



#### event monitor example, full event list



obtained via -F -A (full list, all devices)




```
 ----  device /dev/input/event2, name "2.4G Composite Devic", phys "usb-3f980000.usb-1.5.2/input0"
  type 4, code   4, val 0x0007001b | event at 1669771513.161219, code 04, type 04, val 458779, MSC_SCAN
  type 1, code  45, val          1 | key event at 1669771513.161219, 45 (KEY_X), down
  type 0, code   0, val          0 | synchronization event at 1669771513.161219, SYN_REPORT
 ----  device /dev/input/event2, name "2.4G Composite Devic", phys "usb-3f980000.usb-1.5.2/input0"
  type 1, code  45, val          2 | key event at 1669771513.413038, 45 (KEY_X), hold
  type 0, code   0, val          1 | synchronization event at 1669771513.413038, SYN_REPORT
 ----  device /dev/input/event2, name "2.4G Composite Devic", phys "usb-3f980000.usb-1.5.2/input0"
  type 1, code  45, val          2 | key event at 1669771513.863037, 45 (KEY_X), hold
  type 0, code   0, val          1 | synchronization event at 1669771513.863037, SYN_REPORT
  type 4, code   4, val 0x0007001b | event at 1669771513.863037, code 04, type 04, val 458779, MSC_SCAN
  type 1, code  45, val          0 | key event at 1669771513.863037, 45 (KEY_X), up
  type 0, code   0, val          0 | synchronization event at 1669771513.863037, SYN_REPORT

 ----  device /dev/input/event3, name "2.4G Composite Devic Mouse", phys "usb-3f980000.usb-1.5.2/input1"
  type 2, code   1, val          3 | relative axis event at 1669771593.527032, REL_Y
  type 0, code   0, val          0 | synchronization event at 1669771593.527032, SYN_REPORT
 ----  device /dev/input/event3, name "2.4G Composite Devic Mouse", phys "usb-3f980000.usb-1.5.2/input1"
  type 2, code   0, val         -1 | relative axis event at 1669771593.544034, REL_X
  type 2, code   1, val          2 | relative axis event at 1669771593.544034, REL_Y
  type 0, code   0, val          0 | synchronization event at 1669771593.544034, SYN_REPORT

 ----  device /dev/input/event3, name "2.4G Composite Devic Mouse", phys "usb-3f980000.usb-1.5.2/input1"
  type 4, code   4, val 0x00090001 | event at 1669771602.661007, code 04, type 04, val 589825, MSC_SCAN
  type 1, code 272, val          1 | key event at 1669771602.661007, 272 (['BTN_LEFT', 'BTN_MOUSE']), down
  type 0, code   0, val          0 | synchronization event at 1669771602.661007, SYN_REPORT
 ----  device /dev/input/event3, name "2.4G Composite Devic Mouse", phys "usb-3f980000.usb-1.5.2/input1"
  type 4, code   4, val 0x00090001 | event at 1669771602.806020, code 04, type 04, val 589825, MSC_SCAN
  type 1, code 272, val          0 | key event at 1669771602.806020, 272 (['BTN_LEFT', 'BTN_MOUSE']), up
  type 0, code   0, val          0 | synchronization event at 1669771602.806020, SYN_REPORT

 ----  device /dev/input/event0, name "深圳市全动电子技术有限公司 ByQDtech 触控USB鼠标", phys "usb-3f980000.usb-1.3.1/input0"
  type 3, code  47, val          2 | absolute axis event at 1669771626.693009, ABS_MT_SLOT
  type 3, code  57, val         59 | absolute axis event at 1669771626.693009, ABS_MT_TRACKING_ID
  type 3, code  53, val        638 | absolute axis event at 1669771626.693009, ABS_MT_POSITION_X
  type 3, code  54, val        388 | absolute axis event at 1669771626.693009, ABS_MT_POSITION_Y
  type 3, code  58, val         24 | absolute axis event at 1669771626.693009, ABS_MT_PRESSURE
  type 1, code 330, val          1 | key event at 1669771626.693009, 330 (BTN_TOUCH), down
  type 3, code   0, val        638 | absolute axis event at 1669771626.693009, ABS_X
  type 3, code   1, val        388 | absolute axis event at 1669771626.693009, ABS_Y
  type 3, code  24, val         24 | absolute axis event at 1669771626.693009, ABS_PRESSURE
  type 4, code   5, val 0x00000000 | event at 1669771626.693009, code 05, type 04, val 00, MSC_TIMESTAMP
  type 0, code   0, val          0 | synchronization event at 1669771626.693009, SYN_REPORT
 ----  device /dev/input/event0, name "深圳市全动电子技术有限公司 ByQDtech 触控USB鼠标", phys "usb-3f980000.usb-1.3.1/input0"
  type 4, code   5, val 0x00827800 | event at 1669771626.704959, code 05, type 04, val 8550400, MSC_TIMESTAMP
  type 0, code   0, val          0 | synchronization event at 1669771626.704959, SYN_REPORT
 ----  device /dev/input/event0, name "深圳市全动电子技术有限公司 ByQDtech 触控USB鼠标", phys "usb-3f980000.usb-1.3.1/input0"
  type 4, code   5, val 0x00ff779c | event at 1669771626.715957, code 05, type 04, val 16742300, MSC_TIMESTAMP
  type 0, code   0, val          0 | synchronization event at 1669771626.715957, SYN_REPORT
 ----  device /dev/input/event0, name "深圳市全动电子技术有限公司 ByQDtech 触控USB鼠标", phys "usb-3f980000.usb-1.3.1/input0"
  type 4, code   5, val 0x018ffe70 | event at 1669771626.734969, code 05, type 04, val 26214000, MSC_TIMESTAMP
  type 0, code   0, val          0 | synchronization event at 1669771626.734969, SYN_REPORT

```

Use -q to silence the SYN\_REPORT events.




Values for type 0 (SYN), 1 (KEY, keypress), 2 (REL, relative pointer move) and 3 (ABS, absolute pointer coordinates) are shown as decimal.




Values for type 4 (MSC, misc), 5 (SW, switch) and greater are shown as hexadecimal, as that's easier to look-and-see decode the
position-encoded and binary values. MSC\_ descriptions are hardcoded, evdev did not decode, may improve in later versions.




Ctrl-C is detected via scancodes, to facilitate termination of the process in order to avoid locking the hapless admin out of the terminal.
(Other remedy, connect in via SSH or so and kill the process. Or reboot the device.)



### config file



The actions are specified in a config file. By default, it can be in ~/.kbdassist.cfg, or /etc/kbdassist.cfg.




The actions are apecified as pairs of key name, '=', and a command.




For control of 3d printers and other Octoprint-based devices, [sw\_8control](https://www.improwis.com/projects/sw_8control "local project") is leveraged.




Example:

```
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
 VLONG_CAPS_C = 8gmulti g29 g0x0y0
 # zero to bed
 VLONG_CAPS_Z = 8gmulti g30 g92z0 g0z10f2000
 CAPS_Z       = 8gmulti g30 g92z0 g0z10f2000

 # home
 VLONG_H = 8home

```




For moving the head, many repeated commands with minor variants have to be used. To avoid spamming the config,
two separate tables are used:
* a list of modifier keys with the associated distances to move
* a list of commands with '#' as placeholder for the distance




Example:

```
 # JOGPREF: prefix = distance
 JOGPREF: CTRL_  = 0.1
 JOGPREF:        = 1
 JOGPREF: LONG_  = 5
 JOGPREF: SHIFT_ = 10
 JOGPREF: VLONG_ = 20
 JOGPREF: CAPS_  = 50

 # JOGKEY: key = command, # substituted for distance
 JOGKEY: LEFT     = 8jog # -0 -0
 JOGKEY: RIGHT    = 8jog -# -0 -0
 JOGKEY: UP       = 8jog -0 -# -0
 JOGKEY: DOWN     = 8jog -0 # -0
 JOGKEY: PAGEUP   = 8jog -#
 JOGKEY: HOME     = 8jog -#
 JOGKEY: PAGEDOWN = 8jog #
 JOGKEY: END      = 8jog #

```




This generates the head movement commands for six distances from 0.1 to 50 mm per step, and for all three axes
(with Z axis having both pgup/pgdn and home/end keys as synonymous, to allow for different keyboard layouts).
Much less annoying to write 6+8 lines than to explicitly handle 6\*8=48 ones.




For specifying different keypress lengths, the defaults can be overriden by the config file:

```
 # VLONG, LONG: time in milliseconds
 VLONG: 1000
 LONG:  300

```




For modifying the default modkey prefixes, use directives MOD\_CLEAR (for clearing the default mod table if needed), and MOD: for setting the key/prefix pair:

```
 MOD_CLEAR
 MOD: KEY_TAB = TAB
 MOD: KEY_RIGHTSHIFT = RSHIFT

```
Beware of the order. The prefixes, as defined, are added right to left. The keys are stored in a dict, so overwriting an existing key will
keep the original dict order and may be confusing.




A selection of device by name can be done in the config file as well:

```
 # fraction of device name, to match
 DEVNAME:NOVATEK

```
This can be overriden by the commandline options.




For defining the key combination to exit the process, when running from the console:

```
 # key combination for process exiting, empty to disable, make sure the combo is valid!
 EXITPROCESS: ALT_CTRL_SHIFT_C

```



### command execution



Normally, for a notch better performance, subprocess.Popen() call is used. This needs the command name
and arguments specified as a list. This is parsed from the configfile string via shlex.split() call.




Some commands have to be invoked via /bin/sh shell. When the command contains pipe, redirect, or semicolon,
the os.system() call is used instead.




The command is run as a parallel process, non-blocking.





---

Commandline options
-------------------



```
usage: kbdassist.py [-h] [-d DEVICE] [-dn DEVNAME] [-da DEVADDR]
                    [-dp DEVPREFIX] [-A] [-l] [-L] [-E] [-M] [-C] [-q] [-v]
                    [-D] [-T] [-c CONFIG] [--printdefaultconfig] [-F]

executes commands on keypresses and their combinations

optional arguments:
  -h, --help            show this help message and exit
  -d DEVICE, --device DEVICE
                        /dev/input device
  -dn DEVNAME, --devname DEVNAME
                        fraction of device name, default=""
  -da DEVADDR, --devaddr DEVADDR
                        device phys address or suffix (eg. 4, 2.1, 3.2.3),
                        match to last slash
  -dp DEVPREFIX, --devprefix DEVPREFIX
                        device address prefix, default=""
  -A, --matchall        match all devices
  -l, --list            list HID devices present
  -L, --listevents      list events for matching device(s)
  -E, --showevents      show detected event names and source devices, ignore
                        config
  -M, --forcemods       like -E, but force reading of config/modifier
  -C, --listcommands    list set commands
  -q, --quiet           suppress most output
  -v, --verbose         print more details
  -D, --dryrun          show command instead of executing
  -T, --stricttime      do not try VLONG-LONG-normal if longer command not
                        found
  -c CONFIG, --config CONFIG
                        keys config file, default=['~/.kbdassist.cfg',
                        '~/kbdassist.cfg', './kbdassist.cfg',
                        '/etc/kbdassist.cfg']
  --printdefaultconfig  print default config file content
  -F, --showallevents   show ALL detected events (not just keypresses), ignore
                        config; -q to suppress SYN_REPORT

```
### examples


* list all devices: kbdassist.py -l
* list events available for all devices: kbdassist.py -AL
* monitor events from all devices, exit via ctrl-C, hardcoded modifiers: kbdassist.py -AE
* monitor events from all devices, exit via ctrl-C, read modifiers from default config: kbdassist.py -AEM
* list available commands-to-keys mapping, to make sure the system understands the config: kbdassist.py -C
* run on all devices with default config: kbdassist.py -A
* run on device "NOVATEK USB Keyboard" with bigkbd.cfg file: kbdassist.py -dn NOVATEK -c bigkbd.cfg
* generate default config file: kbdassist.py --printdefaultconfig > ~/.kbdassist.cfg


Use -v to see what the program is doing, what files are being looked for where, etc.; can save a headscratcher of debugging.





---

Download
--------


* **[kbdassist.py](kbdassist.py "local file")** - help yourself



---

TODO
----


* multiple use of options -d, -da, for selecting more devices at once
* maybe possibility to enter strings or numbers as parameters for commands (may be tricky to do without visual feedback)
* /etc/udev/rules.d/ recipes to run the assistant on plugging in a device






