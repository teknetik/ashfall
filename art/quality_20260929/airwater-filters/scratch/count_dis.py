import re
t = open('scratch/inspect_full.txt').read()
m = re.search(r"bank renderers disabled in scene: \[(.*?)\]\n", t, re.S)
names = re.findall(r"'([^']+)'", m.group(1))
print('disabled', len(names), 'unique', len(set(names)))
print('with m_Enabled override 0 for all 65:', t.count("('m_Enabled', '0'"))
