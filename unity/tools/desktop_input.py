"""Local X11 keyboard/mouse driver for real Unity Game View QA."""
from Xlib import X, XK, display, protocol
from Xlib.ext import xtest
import time,os

def focus():
    d=display.Display(); root=d.screen().root
    for wid in root.get_full_property(d.intern_atom('_NET_CLIENT_LIST'),X.AnyPropertyType).value:
        w=d.create_resource_object('window',wid)
        qa_pid=os.environ.get('ATHEN_NATIVE_PID');pid=w.get_full_property(d.intern_atom('_NET_WM_PID'),X.AnyPropertyType)
        matches=bool(pid is not None and int(pid.value[0])==int(qa_pid)) if qa_pid else 'AthenHill' in (w.get_wm_name() or '')
        if matches:
            root.send_event(protocol.event.ClientMessage(window=w,client_type=d.intern_atom('_NET_ACTIVE_WINDOW'),data=(32,[2,X.CurrentTime,0,0,0])),event_mask=X.SubstructureRedirectMask|X.SubstructureNotifyMask)
            d.sync();time.sleep(.25)
            return d
    raise RuntimeError('AthenHill Editor window not found')

def key(d,name,down):
    xtest.fake_input(d,X.KeyPress if down else X.KeyRelease,d.keysym_to_keycode(XK.string_to_keysym(name)));d.sync()

def click(d,x,y):
    xtest.fake_input(d,X.MotionNotify,x=x,y=y);xtest.fake_input(d,X.ButtonPress,1);xtest.fake_input(d,X.ButtonRelease,1);d.sync()

if __name__=='__main__':
    import sys
    d=focus()
    if len(sys.argv)>1:
        key(d,sys.argv[1],True)
        try:time.sleep(float(sys.argv[2]))
        finally:key(d,sys.argv[1],False)
