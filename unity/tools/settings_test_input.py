"""Native input that also works on a private Xvfb display without a window manager."""
import os,time
from Xlib import X,display,protocol
from desktop_input import key,click

def window(d):
 root=d.screen().root
 clients=root.get_full_property(d.intern_atom('_NET_CLIENT_LIST'),X.AnyPropertyType)
 candidates=[d.create_resource_object('window',wid) for wid in clients.value] if clients is not None else root.query_tree().children
 for w in candidates:
  pid=w.get_full_property(d.intern_atom('_NET_WM_PID'),X.AnyPropertyType)
  if pid is not None and int(pid.value[0])==int(os.environ['ATHEN_NATIVE_PID']):return w
 raise RuntimeError('Native settings QA window not found')

def focus():
 d=display.Display();root=d.screen().root;w=window(d)
 if root.get_full_property(d.intern_atom('_NET_SUPPORTING_WM_CHECK'),X.AnyPropertyType) is not None:
  root.send_event(protocol.event.ClientMessage(window=w,client_type=d.intern_atom('_NET_ACTIVE_WINDOW'),data=(32,[2,X.CurrentTime,0,0,0])),event_mask=X.SubstructureRedirectMask|X.SubstructureNotifyMask)
 else:
  w.configure(stack_mode=X.Above);w.set_input_focus(X.RevertToParent,X.CurrentTime)
 d.sync();time.sleep(.25);return d
