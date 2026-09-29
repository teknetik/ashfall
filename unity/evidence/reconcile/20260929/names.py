import re, os
t = open(os.environ["TMPDIR"] + "/merge/main.unity", errors="replace").read()
def name_of(tid):
    m = re.search(r'--- !u!4 &%s\nTransform:.*?m_GameObject: \{fileID: (\d+)\}' % tid, t, re.S)
    go = m.group(1)
    n = re.search(r'--- !u!1 &%s\nGameObject:.*?m_Name: ([^\n]*)' % go, t, re.S).group(1)
    f = re.search(r'--- !u!4 &%s\nTransform:.*?m_Father: \{fileID: (\d+)\}' % tid, t, re.S).group(1)
    return n, f
for start in ("226721071", "1851674839"):
    i = start
    for _ in range(6):
        n, f = name_of(i); print(i, n, "->", f)
        if f == "0": break
        i = f
