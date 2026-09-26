#include <stdio.h>
#include <X11/Xlib.h>
#include <GL/gl.h>
#include <GL/glx.h>

/* Temporary private-display capability query; no keyboard, mouse or focus calls. */
int main(void) {
    Display *d = XOpenDisplay(NULL);
    if (!d) return 1;
    int attrs[] = {GLX_RGBA, GLX_DOUBLEBUFFER, None};
    XVisualInfo *v = glXChooseVisual(d, DefaultScreen(d), attrs);
    if (!v) { XCloseDisplay(d); return 2; }
    Colormap c = XCreateColormap(d, RootWindow(d, v->screen), v->visual, AllocNone);
    XSetWindowAttributes a = {0};
    a.colormap = c;
    Window w = XCreateWindow(d, RootWindow(d, v->screen), 0, 0, 32, 32, 0,
        v->depth, InputOutput, v->visual, CWColormap, &a);
    GLXContext ctx = glXCreateContext(d, v, NULL, True);
    if (!ctx || !glXMakeCurrent(d, w, ctx)) return 3;
    printf("vendor=%s\nrenderer=%s\nversion=%s\ndirect=%d\n",
        glGetString(GL_VENDOR), glGetString(GL_RENDERER), glGetString(GL_VERSION),
        glXIsDirect(d, ctx));
    glXMakeCurrent(d, None, NULL);
    glXDestroyContext(d, ctx);
    XDestroyWindow(d, w);
    XFreeColormap(d, c);
    XFree(v);
    XCloseDisplay(d);
    return 0;
}
