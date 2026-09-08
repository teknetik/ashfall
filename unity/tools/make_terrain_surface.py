"""Bake original periodic geological scalar fields. No third-party imagery."""
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
size=1024
rng=np.random.default_rng(84519)
def noise(scale):
 a=gaussian_filter(rng.random((size,size)).astype(np.float32),scale,mode='wrap')
 a=(a-a.mean())/(a.std()*5)+.5
 return np.clip(a,0,1)
broad=noise(44);medium=noise(12);fine=noise(2);grain=noise(.25)
y,x=np.mgrid[0:size,0:size]/size
# Seamless cellular fractures with irregular edges, plus fractured sediment grains.
warp=(medium-.5)*.013
first=np.full((size,size),10.0);second=first.copy()
for j in range(7):
 for i in range(7):
  px=(i+rng.uniform(.15,.85))/7;py=(j+rng.uniform(.15,.85))/7
  dx=np.abs(x+warp-px);dx=np.minimum(dx,1-dx)
  dy=np.abs(y+warp-py);dy=np.minimum(dy,1-dy)
  d=np.sqrt(dx*dx+dy*dy)
  second=np.minimum(second,np.maximum(first,d));first=np.minimum(first,d)
crack=np.clip((second-first)*190,0,1)
crack=crack*crack*(3-2*crack)
height=(.38*broad+.33*medium+.20*fine+.09*grain)*(.54+.46*crack)
data=np.stack((broad*.6+medium*.4,grain,crack,height),axis=-1)
path=Path(__file__).resolve().parents[1]/'AthenHill/Assets/AthenHill/Art/Terrain/Geology.png'
Image.fromarray(np.uint8(np.clip(data,0,1)*255)).save(path)
print(path)
