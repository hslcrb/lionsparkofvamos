
# Blender-authored celestial texture / 블렌더에서 생성한 천구 텍스처
import bpy,numpy as np,math,pathlib,json,hashlib
ROOT=pathlib.Path(__file__).resolve().parents[2]
W,H=4096,2048
rng=np.random.default_rng(1982)
rgb=np.zeros((H,W,3),dtype=np.float32)
ra=(np.arange(W,dtype=np.float32)+.5)/W*math.tau-math.pi
u=(np.arange(W,dtype=np.float32)+.5)/W
pole_ra,pole_dec=math.radians(192.85948),math.radians(27.12825)
pole=np.array([math.cos(pole_dec)*math.cos(pole_ra),math.cos(pole_dec)*math.sin(pole_ra),math.sin(pole_dec)])
gc=np.array([math.cos(math.radians(-28.94))*math.cos(math.radians(266.4)),math.cos(math.radians(-28.94))*math.sin(math.radians(266.4)),math.sin(math.radians(-28.94))])
gc-=pole*np.dot(gc,pole);gc/=np.linalg.norm(gc);cross=np.cross(pole,gc)
grids=[rng.random((gy+1,gx)).astype(np.float32) for gx,gy in [(32,16),(64,32),(128,64),(256,128),(512,256)]]
def field(grid,v):
 gy,gx=grid.shape[0]-1,grid.shape[1]
 px=u*gx;ix=px.astype(np.int32);tx=px-ix;tx=tx*tx*(3-2*tx)
 py=v*gy;iy=np.minimum(py.astype(np.int32),gy-1);ty=py-iy;ty=ty*ty*(3-2*ty)
 a=grid[iy[:,None],ix[None,:]%gx]*(1-tx)+grid[iy[:,None],(ix[None,:]+1)%gx]*tx
 b=grid[iy[:,None]+1,ix[None,:]%gx]*(1-tx)+grid[iy[:,None]+1,(ix[None,:]+1)%gx]*tx
 return a*(1-ty[:,None])+b*ty[:,None]
# Filamentary galactic light and absorbing dust / 은하의 성운광과 어두운 먼지 띠
for y0 in range(0,H,64):
 y1=min(H,y0+64);v=(np.arange(y0,y1,dtype=np.float32)+.5)/H
 dec=v*math.pi-math.pi/2;cd=np.cos(dec)[:,None];sd=np.sin(dec)[:,None]
 x=cd*np.cos(ra)[None,:];y=cd*np.sin(ra)[None,:]
 gal_lat=np.arcsin(np.clip(x*pole[0]+y*pole[1]+sd*pole[2],-1,1))
 glon=np.arctan2(x*cross[0]+y*cross[1]+sd*cross[2],x*gc[0]+y*gc[1]+sd*gc[2])
 noise=sum(w*field(g,v) for w,g in zip([.43,.25,.17,.10,.05],grids))
 fine=field(grids[-1],v)
 band=np.exp(-(gal_lat/.14)**2)
 dust_center=.014*np.sin(glon*3)+.025*(noise-.5)
 dust=np.exp(-((gal_lat-dust_center)/.028)**2)*np.clip((noise-.30)*2.5,0,1)
 core=np.exp((np.cos(glon)-1)/.17)*np.exp(-(gal_lat/.22)**2)
 emission=(.009+.085*np.maximum(noise-.20,0)**1.65)*band*(1-.88*dust)*(0.78+.35*fine)
 rgb[y0:y1]=emission[:,:,None]*np.array([.77,.86,1.0],dtype=np.float32)
 rgb[y0:y1]+=((.022+.034*noise)*core*(1-.73*dust))[:,:,None]*np.array([1.,.76,.47],dtype=np.float32)
# Stellar points are statistical art, not a catalogue / 별 위치는 성표가 아닌 통계적 표현
def point(ra0,dec0,brightness,temp):
 cx=(ra0+math.pi)/math.tau*W-.5;cy=(dec0+math.pi/2)/math.pi*H-.5
 sy=.42+min(1,brightness)*.85;sx=sy/max(.15,math.cos(dec0))
 rx=min(24,int(math.ceil(sx*3)));ry=int(math.ceil(sy*3))
 xx=np.arange(math.floor(cx)-rx,math.floor(cx)+rx+1);yy=np.arange(max(0,math.floor(cy)-ry),min(H,math.floor(cy)+ry+1))
 if len(yy)==0:return
 dx=(xx-cx)/sx;dy=(yy-cy)/sy
 g=np.exp(-.5*(dy[:,None]**2+dx[None,:]**2)).astype(np.float32)
 wave=np.array([610e-9,550e-9,460e-9])
 spectral=1/(wave**5*np.expm1(.01438777/(wave*temp)))
 white=1/(wave**5*np.expm1(.01438777/(wave*6500)))
 color=spectral/white;color/=color.max();color=.40+.60*color
 rgb[yy[:,None],(xx[None,:]%W)]+=g[:,:,None]*color[None,None,:]*brightness
 if brightness>.3:
  g2=np.exp(-.5*((dy[:,None]/2.8)**2+(dx[None,:]/2.8)**2)).astype(np.float32)
  rgb[yy[:,None],xx[None,:]%W]+=g2[:,:,None]*color[None,None,:]*brightness*.035
count=10800
for i in range(count):
 if i<5000:
  ra0=rng.uniform(-math.pi,math.pi);dec0=math.asin(rng.uniform(-1,1))
 else:
  lon=rng.uniform(-math.pi,math.pi);lat=rng.normal(0,.095)
  n=math.cos(lat)*(math.cos(lon)*gc+math.sin(lon)*cross)+math.sin(lat)*pole
  ra0=math.atan2(n[1],n[0]);dec0=math.asin(float(n[2]))
 mag=.5+5.5*math.sqrt(rng.random());lum=.95*10**(-.4*(mag-.5))
 point(ra0,dec0,lum,rng.uniform(3500,10500))
# Save the lossless night atlas and its reproducible provenance / 무손실 천구 지도 저장
rgba=np.ones((H,W,4),dtype=np.float32)
linear=np.clip(rgb,0,1)
rgba[:,:,:3]=np.where(linear<=.0031308,linear*12.92,1.055*np.power(linear,1/2.4)-.055)
im=bpy.data.images.new('Lionspark_Celestial_Equatorial_Night',width=W,height=H,alpha=True)
im.pixels.foreach_set(rgba.ravel());im.filepath_raw=str(ROOT/'public'/'models'/'celestial-night.png');im.file_format='PNG';im.save();im.pack()
meta=dict(width=W,height=H,seed=1982,stars=count,projection='equatorial equirectangular',u='(RA+pi)/(2*pi)',v='(declination+pi/2)/pi',poleJ2000=[192.85948,27.12825],encoding='sRGB encoded from linear radiance',kind='procedural astronomical artwork, not a star catalogue',generator='Blender MCP / numpy',sha256=hashlib.sha256(pathlib.Path(im.filepath_raw).read_bytes()).hexdigest())
(ROOT/'assets'/'blender'/'celestial-sky-manifest.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
print('CELESTIAL_NIGHT_ATLAS',im.size[:],pathlib.Path(im.filepath_raw).stat().st_size,'bytes;',count,'stars')

# Editable sky-only Blender lab / 편집 가능한 하늘 전용 블렌더 자료
lab=bpy.data.scenes.new('Celestial_Texture_Studio')
world=bpy.data.worlds.new('Celestial_Night_Atlas_World');world.use_nodes=True;lab.world=world
bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Strength'].default_value=1
tex=world.node_tree.nodes.new('ShaderNodeTexEnvironment');tex.image=im;world.node_tree.links.new(tex.outputs['Color'],bg.inputs['Color'])
camd=bpy.data.cameras.new('Sky_Texture_Preview_Camera');camera=bpy.data.objects.new('Sky_Texture_Preview_Camera',camd);lab.collection.objects.link(camera);lab.camera=camera
camera.rotation_euler=(math.radians(90),0,math.radians(40));camd.lens=18
lab.render.resolution_x=1600;lab.render.resolution_y=900
lab['projection']='Equatorial equirectangular RA[-pi,pi], Dec[-pi/2,pi/2]'
lab['artwork']='Procedural astronomical starfield and MilkyWay, not a catalogue'
bpy.data.libraries.write(str(ROOT/'assets'/'blender'/'celestial-sky-v4.blend'),{lab},fake_user=True,compress=True)

meta.update(blendBytes=(ROOT/'assets'/'blender'/'celestial-sky-v4.blend').stat().st_size,blendSha256=hashlib.sha256((ROOT/'assets'/'blender'/'celestial-sky-v4.blend').read_bytes()).hexdigest())
(ROOT/'assets'/'blender'/'celestial-sky-manifest.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
