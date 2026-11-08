# Blender MCP reconstruction of the supplied Lionspark aerial photo.
# Run inside Blender. Shapes and unseen surroundings are interpretive, not survey data.


import bpy, math, random, os, pathlib
from mathutils import Vector
random.seed(1982)
ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "public" / "models"
OUT.mkdir(parents=True, exist_ok=True)
if bpy.data.scenes.get('Lionspark'):
    raise RuntimeError('Run the rebuild script in a new Blender file; open the saved .blend to edit the existing scene.')
SCENE = bpy.data.scenes.new("Lionspark")
bpy.context.window.scene = SCENE
SCENE.unit_settings.system = 'METRIC'
COL = bpy.data.collections.new("Lionspark_World")
SCENE.collection.children.link(COL)
MATS = {}
BATCH = {}
OBJS = []
def mat(name, color, rough=.7, metal=0, texture=False):
    m=bpy.data.materials.new(name); m.use_nodes=True
    bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Roughness'].default_value=rough
    bs.inputs['Metallic'].default_value=metal
    m.diffuse_color=(*color,1)
    if texture:
        size=256
        im=bpy.data.images.new(name+"_surface",width=size,height=size)
        pixels=[]
        rng=random.Random(sum(map(ord,name)))
        for y in range(size):
            for x in range(size):
                factor=.92+rng.random()*.16+.025*math.sin(x*.16)*math.sin(y*.22)
                pixels.extend([min(1,c*factor) for c in color]+[1])
        im.pixels.foreach_set(pixels); im.pack()
        tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=im
        tex.extension='REPEAT'
        m.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
    MATS[name]=m
    return name
mat('Concrete',(0.64,.66,.65),.9,texture=True)
mat('Ivory',(0.86,.89,.88),.55)
mat('Roof',(0.92,.95,.94),.43,.2)
mat('Steel',(.44,.51,.54),.3,.65)
mat('DarkMetal',(.09,.14,.18),.4,.5)
mat('LionsBlue',(.005,.21,.48),.35,.1)
mat('BlueSeat',(.01,.34,.66),.43)
mat('AzureSeat',(.02,.45,.74),.43)
mat('NavySeat',(.008,.12,.30),.4)
mat('Glass',(.055,.17,.24),.23,.45)
mat('Grass',(.095,.24,.025),.95,texture=True)
mat('GrassLight',(.14,.32,.035),.95,texture=True)
mat('Dirt',(.58,.32,.13),.95,texture=True)
mat('Asphalt',(.075,.085,.09),.95,texture=True)
mat('Paving',(.50,.48,.43),.93,texture=True)
mat('PavingLight',(.73,.72,.67),.92,texture=True)
mat('WhitePaint',(.88,.90,.86),.7)
mat('YellowPaint',(.87,.65,.055),.75)
mat('Bark',(.18,.105,.045),.9,texture=True)
mat('LeafDark',(.027,.115,.028),.98,texture=True)
mat('LeafMid',(.055,.205,.035),.98,texture=True)
mat('LeafSun',(.12,.285,.045),.95,texture=True)
mat('Sand',(.53,.47,.34),1)
mat('CarWhite',(.75,.79,.80),.28,.35)
mat('CarGrey',(.17,.21,.23),.28,.5)
mat('CarBlue',(.015,.12,.24),.25,.4)
mat('Tire',(.015,.019,.021),.9)
def add(name,verts,faces,material):
    key=(name,material)
    v,f=BATCH.setdefault(key,([],[]))
    base=len(v);v.extend(verts);f.extend([tuple(base+i for i in face) for face in faces])
def box(name,center,size,material,rot=0):
    x,y,z=center;a,b,c=[v/2 for v in size]
    coords=[(-a,-b,-c),(a,-b,-c),(a,b,-c),(-a,b,-c),(-a,-b,c),(a,-b,c),(a,b,c),(-a,b,c)]
    co,si=math.cos(rot),math.sin(rot)
    verts=[(x+vx*co-vy*si,y+vx*si+vy*co,z+vz) for vx,vy,vz in coords]
    add(name,verts,[(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],material)
def beam(name,a,b,r,material,sides=6):
    av,bv=Vector(a),Vector(b);d=bv-av
    if d.length<.001:return
    quat=d.to_track_quat('Z','Y');verts=[]
    for p in (av,bv):
        for j in range(sides):
            vv=quat@Vector((r*math.cos(j*math.tau/sides),r*math.sin(j*math.tau/sides),0))+p
            verts.append(tuple(vv))
    faces=[tuple(reversed(range(sides))),tuple(range(sides,sides*2))]
    faces += [(j,(j+1)%sides,(j+1)%sides+sides,j+sides) for j in range(sides)]
    add(name,verts,faces,material)
def oval(name,center,scale,material,segments=10,rings=6):
    verts=[];faces=[];x,y,z=center
    for j in range(rings+1):
        t=math.pi*j/rings
        for i in range(segments):
            a=i*math.tau/segments
            verts.append((x+scale[0]*math.sin(t)*math.cos(a),y+scale[1]*math.sin(t)*math.sin(a),z+scale[2]*math.cos(t)))
    for j in range(rings):
        for i in range(segments):
            k=j*segments+i;kn=j*segments+(i+1)%segments
            faces.append((k,kn,kn+segments,k+segments))
    add(name,verts,faces,material)
def point(a,rx,ry,z=0):
    t=math.radians(a)
    # Faceted eight-sided stadium envelope.
    factor=math.cos(math.pi/8)/math.cos((t+math.pi/8)%(math.pi/4)-math.pi/8)
    return (rx*math.cos(t)*factor,10+ry*math.sin(t)*factor,z)
def strip(name,a0,a1,rx0,ry0,rx1,ry1,z0,z1,thick,material,steps=16):
    for j in range(steps):
        a=a0+(a1-a0)*j/steps;b=a0+(a1-a0)*(j+1)/steps
        p=[point(a,rx0,ry0,z0),point(b,rx0,ry0,z0),point(b,rx1,ry1,z1),point(a,rx1,ry1,z1)]
        v=p+[(x,y,z-thick) for x,y,z in p]
        add(name,v,[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],material)
def flush():
    created=[]
    for (name,material),(verts,faces) in list(BATCH.items()):
        mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
        ob=bpy.data.objects.new(name+"_"+material,mesh);COL.objects.link(ob);ob.data.materials.append(MATS[material])
        uv=mesh.uv_layers.new()
        for poly in mesh.polygons:
            n=poly.normal
            for li in poly.loop_indices:
                v=mesh.vertices[mesh.loops[li].vertex_index].co
                if abs(n.z)>.6:uv.data[li].uv=(v.x*.08,v.y*.08)
                elif abs(n.y)>.6:uv.data[li].uv=(v.x*.08,v.z*.08)
                else:uv.data[li].uv=(v.y*.08,v.z*.08)
        created.append(ob);OBJS.append(ob)
    BATCH.clear()
    return created
def text(name,body,location,size,material,rotation=(math.pi/2,0,0),font=None):
    cu=bpy.data.curves.new(name,'FONT');cu.body=body;cu.size=size;cu.align_x='CENTER'
    cu.extrude=.015;cu.bevel_depth=.003
    if font:cu.font=font
    ob=bpy.data.objects.new(name,cu);COL.objects.link(ob);ob.location=location;ob.rotation_euler=rotation
    cu.materials.append(MATS[material]);OBJS.append(ob);return ob
print("LIONSPARK initialized: 25 PBR materials and batched modeling helpers")


# Existing photographic sky is a CC0 baked panorama supplied with this reconstruction.
world=bpy.data.worlds.new('Lionspark_Clear_Sky');world.use_nodes=True;SCENE.world=world
bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND')
env=world.node_tree.nodes.new('ShaderNodeTexEnvironment');env.image=bpy.data.images.load(str(OUT/'lionspark-sky.jpg'),check_existing=True)
world.node_tree.links.new(env.outputs['Color'],bg.inputs['Color']);bg.inputs['Strength'].default_value=.7
sun_data=bpy.data.lights.new('Afternoon_Sun','SUN');sun_data.energy=3.2;sun_data.angle=math.radians(1.6)
sun=bpy.data.objects.new('Afternoon_Sun',sun_data);COL.objects.link(sun);sun.rotation_euler=(math.radians(28),math.radians(-24),math.radians(-30))
cam_data=bpy.data.cameras.new('Lionspark_Aerial');cam=bpy.data.objects.new('Lionspark_Aerial',cam_data);COL.objects.link(cam)
cam.location=(285,-360,265);cam.rotation_euler=(Vector((0,12,10))-cam.location).to_track_quat('-Z','Y').to_euler();cam_data.lens=43;cam_data.clip_end=5000;SCENE.camera=cam
SCENE.render.resolution_x=1400;SCENE.render.resolution_y=930;SCENE.render.resolution_percentage=100
SCENE.view_settings.view_transform='AgX'


# Stadium bowl, two tiers, white faceted canopy, and field.
box('WalkSurface_Site',(0,0,-.35),(900,900,.7),'Grass')
box('WalkSurface_Plaza',(0,-145,.035),(330,105,.07),'PavingLight')
box('WalkSurface_Concourse',(0,10,.04),(310,265,.08),'Paving')
box('WalkSurface_Field',(0,-5,.12),(165,140,.08),'Grass')
# Baseball fan, home plate at (0,40), outfield to the south.
home=(0,40,.19)
for k in range(16):
    a0=225+90*k/16;a1=225+90*(k+1)/16
    v=[home]
    for j in range(9):
        a=math.radians(a0+(a1-a0)*j/8)
        v.append((home[0]+104*math.cos(a),home[1]+104*math.sin(a),.19))
    add('Field_Mowed_Stripes',v,[tuple(range(len(v)))],'GrassLight' if k%2 else 'Grass')
# Clay infield, diamond, mound and bases.
oval('Field_Infield',(0,18,.23),(39,36,.06),'Dirt',64,2)
diamond=[(0,40,.31),(23.5,16.5,.31),(0,-7,.31),(-23.5,16.5,.31)]
add('Infield_Grass',diamond,[(0,1,2,3)],'GrassLight')
oval('Pitchers_Mound',(0,16.5,.35),(3.1,3.1,.22),'Dirt',32,3)
for x,y in [(23.5,16.5),(0,-7),(-23.5,16.5)]:
    box('Bases',(x,y,.39),(.6,.6,.16),'WhitePaint',math.pi/4)
box('Pitcher_Rubber',(0,16.5,.59),(.62,.16,.08),'WhitePaint')
add('Home_Plate',[(-.22,40.15,.39),(.22,40.15,.39),(.22,39.9,.39),(0,39.68,.39),(-.22,39.9,.39)],[(0,1,2,3,4)],'WhitePaint')
for sign in [-1,1]:
    beam('Foul_Lines',(0,40,.31),(sign*73.5,-33.5,.31),.055,'WhitePaint',4)
    box('Batters_Box',(sign*.9,40,.31),(1.2,2.15,.025),'WhitePaint')
    box('Batters_Box_Clay',(sign*.9,40,.33),(1.05,2.0,.025),'Dirt')
for row in range(20):
    strip('Lower_Concrete_Tiers',-30,210,84+row*1.12,78+row*1.12,85.12+row*1.12,79.12+row*1.12,2.4+row*.46,2.4+row*.46,.46,'Concrete',96)
for row in range(14):
    strip('Upper_Concrete_Tiers',-30,210,108+row*1.27,102+row*1.27,109.27+row*1.27,103.27+row*1.27,17.8+row*.6,17.8+row*.6,.6,'Concrete',96)
# Seat silhouettes are L-shaped extrusions, batched by shade.
def seat(center,angle,material):
    x,y,z=center;w=.61
    profile=[(-.28,0),(.28,0),(.28,.67),(.17,.67),(.17,.13),(-.28,.13)]
    verts=[]
    co,si=math.cos(angle),math.sin(angle)
    for xx in [-w/2,w/2]:
        for yy,zz in profile:
            verts.append((x+xx*co-yy*si,y+xx*si+yy*co,z+zz))
    faces=[tuple(reversed(range(6))),tuple(range(6,12))]
    faces += [(j,(j+1)%6,(j+1)%6+6,j+6) for j in range(6)]
    add('Seating',verts,faces,material)
seat_count=0
for tier,rows,rx,ry,zbase,step,rise in [('Lower',20,84.6,78.6,2.55,1.12,.46),('Upper',14,108.7,102.7,17.95,1.27,.6)]:
    for row in range(rows):
        count=int((rx+ry+row*step*2)/2*math.radians(240)/.86)
        for i in range(count):
            a=-30+240*(i+.5)/count
            # Wide radial aisles divide the blue seating blocks.
            if min(abs((a+30)%24),24-((a+30)%24))<1.5:continue
            p=point(a,rx+row*step,ry+row*step,zbase+row*rise)
            material=['BlueSeat','AzureSeat','NavySeat'][(int((a+30)//24)+row//7)%3]
            seat(p,math.radians(a-90),material);seat_count+=1
# Inter-tier concourse, hospitality windows, continuous exterior wall.
strip('Concourse_Ring',-30,210,103,97,111,105,15.1,15.1,.9,'Ivory',96)
strip('Blocker_Bowl_Retaining',-30,210,83.5,77.5,84,78,2.4,2.4,2.4,'LionsBlue',96)
strip('Blocker_Exterior',-30,210,130,124,132,126,17.2,17.2,17.2,'Ivory',96)
strip('Hospitality_Glass',-28,208,131.2,125.2,132,126,14.9,14.9,4.0,'Glass',96)
strip('Hospitality_Silver_Fascia',-30,210,131,125,132.5,126.5,15.5,15.5,.5,'Steel',96)
for a in range(-30,211,8):
    p=point(a,131.5,125.5,8.3)
    beam('Exterior_Columns',(p[0],p[1],.2),(p[0],p[1],26.5),.48,'Ivory')
    q=point(a,110,104,15)
    r=point(a,127,121,26.7)
    beam('Stand_Structure',q,r,.22,'Steel')
# Angular roof ring and structural rafters.
strip('White_Canopy',-32,212,107,101,140,132,30.8,34.2,.55,'Roof',64)
strip('Roof_Blue_Edge',-32,212,106.9,100.9,108,102,30.9,31.02,.7,'LionsBlue',96)
for a in range(-30,211,6):
    p=point(a,107.5,101.5,30.35);q=point(a,139.5,131.5,33.7)
    beam('Roof_Rafters',p,q,.17,'Steel')
    r=point(a,132,126,25.8)
    beam('Canopy_Braces',r,p,.12,'Steel')
# Low outfield stands with a central walk-through opening.
for a0,a1 in [(210,263),(277,330)]:
    for row in range(10):
        strip('Outfield_Terraces',a0,a1,85+row*1.3,78+row*1.3,86.3+row*1.3,79.3+row*1.3,1.1+row*.42,1.1+row*.42,.42,'Concrete',26)
        count=int((a1-a0)*math.pi/180*(85+row*1.3)/.9)
        for i in range(count):
            a=a0+(a1-a0)*(i+.5)/count
            if abs((a-a0)%19)<1.6:continue
            seat(point(a,85.65+row*1.3,78.65+row*1.3,1.25+row*.42),math.radians(a-90),'AzureSeat');seat_count+=1
    strip('Blocker_Outfield_Wall',a0,a1,83,76,83.5,76.5,2.2,2.2,2.2,'LionsBlue',40)
# Front entrance, kiosks, canopy and access gates.
for side in [-1,1]:
    box('Blocker_Entrance_Wing',(side*57,-107,4.2),(92,17,8.4),'Ivory')
    box('Entrance_Glass',(side*57,-115.6,3.4),(88,.18,5.4),'Glass')
    for x in range(15,99,6):
        box('Facade_Mullions',(side*x,-115.8,3.4),(.16,.22,5.6),'Steel')
    box('Entrance_Blue_Fascia',(side*57,-115.8,7.3),(92,.25,1.0),'LionsBlue')
box('Gate_Sign_Backing',(0,-107.8,12.6),(96,1.25,5.1),'Ivory')
box('Entrance_Canopy',(0,-119,9.1),(124,13,.5),'Roof')
for x in [-61,-35,35,61]:
    beam('Blocker_Canopy_Columns',(x,-123,.15),(x,-123,9),.27,'Steel')
for x in [-7.2,-4.8,-2.4,2.4,4.8,7.2]:
    box('Gate_Turnstile_Base',(x,-109,.48),(.65,1.1,.95),'Steel')
    beam('Gate_Turnstile_Arms',(x-.45,-109,1.05),(x+.45,-109,1.05),.055,'Steel')
# Scoreboard rising above the left field.
box('Scoreboard_Support',(-83,-61,8),(17,8,16),'Concrete')
box('Outfield_Scoreboard',(-83,-64,19),(26,3,23),'LionsBlue',-.25)
box('Screen',(-83,-62.4,19),(22,.1,16),'DarkMetal',-.25)
# Four high floodlight masts, trusses and lamp arrays.
for x,y in [(-112,12),(112,12),(-70,118),(70,118)]:
    h=52 if y<100 else 58
    for side in [-1,1]:
        beam('Floodlight_Masts',(x+side*1.7,y,.2),(x+side*.7,y,h),.24,'Roof')
    for z in range(4,int(h),5):
        beam('Floodlight_Lacing',(x-1.5,y,z),(x+1.5,y,z+5),.065,'Steel')
        beam('Floodlight_Lacing',(x+1.5,y,z),(x-1.5,y,z+5),.065,'Steel')
    box('Floodlight_Frame',(x,y,h),(15,1.25,4.2),'Steel')
    for ix in range(12):
        for iz in range(3):
            box('Floodlight_Lamps',(x-6.6+ix*1.2,y-.75,h-1.3+iz*1.3),(.85,.3,.8),'Ivory')
# Yellow foul poles and safety mesh posts.
for x in [-73.5,73.5]:
    beam('Foul_Poles',(x,-33.5,.2),(x,-33.5,22),.15,'YellowPaint')
for a in range(-28,210,9):
    p=point(a,82.7,76.7,0)
    beam('Safety_Net_Posts',(p[0],p[1],1),(p[0],p[1],15),.09,'DarkMetal')
flush()
print("STADIUM",seat_count,"individual seat silhouettes;",len(OBJS),"batched objects")


# Urban context, plaza details, road markings, car park, woodland and distant water.
box('WalkSurface_Front_Sidewalk',(0,-184,.13),(760,12,.26),'PavingLight')
box('WalkSurface_Main_Road',(0,-205,.03),(850,29,.06),'Asphalt')
box('WalkSurface_Cycleway',(0,-222,.06),(850,4,.12),'Paving')
box('WalkSurface_West_Road',(-178,-10,.05),(22,375,.1),'Asphalt')
for x in range(-410,411,12):
    box('Traffic_Lane_Marks',(x,-205,.1),(6,.12,.02),'WhitePaint')
for y in [-191.7,-218.5]:
    box('Road_Edge_Lines',(0,y,.1),(850,.14,.02),'WhitePaint')
for y in [-203.8,-206.2]:
    box('Road_Center_Lines',(0,y,.105),(850,.12,.02),'YellowPaint')
for x in [-5.2,-3.1,-1,1.1,3.2,5.3]:
    box('Crosswalk',(x,-205,.12),(1.1,28,.025),'WhitePaint')
for x in range(-165,166,15):
    box('Plaza_Paver_Joints',(x,-150,.09),(.075,61,.02),'Concrete')
for y in range(-178,-119,10):
    box('Plaza_Paver_Joints',(0,y,.09),(330,.075,.02),'Concrete')
for side in [-1,1]:
    for x in range(20,151,6):
        box('Blocker_Bollards',(side*x,-179,.6),(.25,.25,1.2),'Steel')
# Parking plaza to the west.
box('WalkSurface_Parking',(-225,-108,.04),(110,145,.08),'Asphalt')
for ix in range(3):
    x=-266+ix*33
    for iy in range(20):
        y=-171+iy*6.3
        box('Parking_Marks',(x,y,.1),(13,.1,.025),'WhitePaint')
        if iy<19:
            box('Parking_Marks',(x+6.45,y+3.1,.1),(.12,6.1,.025),'WhitePaint')
# Simple but correctly scaled parked vehicles with glazing, roof and wheels.
def car(x,y,rot,material):
    co,si=math.cos(rot),math.sin(rot)
    def pos(dx,dy,z):return(x+dx*co-dy*si,y+dx*si+dy*co,z)
    box('Parked_Cars',pos(0,0,.65),(1.88,4.45,.82),material,rot)
    box('Car_Glazing',pos(0,-.18,1.27),(1.66,2.45,.62),'Glass',rot)
    box('Car_Roofs',pos(0,-.18,1.59),(1.66,2.17,.075),material,rot)
    for xx in [-.95,.95]:
        for yy in [-1.42,1.42]:
            beam('Car_Wheels',pos(xx-.09,yy,.38),pos(xx+.09,yy,.38),.32,'Tire',10)
    for xx in [-.58,.58]:
        box('Car_Lights',pos(xx,2.24,.8),(.32,.055,.16),'Ivory',rot)
for ix in range(3):
    for iy in range(14):
        if random.random()<.76:
            car(-264+ix*33,-167+iy*9.2,math.pi/2,['CarWhite','CarGrey','CarBlue'][random.randrange(3)])
# Grass islands and shade trees along the entrance plaza.
def tree(x,y,h=10,near=False):
    material=random.choice(['LeafDark','LeafMid','LeafSun'])
    beam('Blocker_Tree_Trunks',(x,y,.1),(x+.15,y,h*.64),.20 if near else .16,'Bark',7)
    for j in range(5 if near else 3):
        a=j*math.tau/(5 if near else 3)+random.random()
        bx=x+math.cos(a)*h*.18;by=y+math.sin(a)*h*.18
        beam('Tree_Branches',(x,y,h*.4),(bx,by,h*.73),.1,'Bark',5)
        oval('Tree_Canopies',(bx,by,h*.77),(h*.25,h*.23,h*.3),material,10 if near else 8,6 if near else 5)
    oval('Tree_Canopies',(x,y,h*.93),(h*.23,h*.22,h*.24),material,10 if near else 8,6 if near else 5)
for x in range(-155,156,18):
    for y in [-173,-133]:
        if abs(x)<17:continue
        box('Planter_Curb',(x,y,.22),(6.2,6.2,.44),'Concrete')
        box('Planter_Soil',(x,y,.46),(5.8,5.8,.08),'Dirt')
        tree(x,y,random.uniform(8,11),True)
        # Ground-level benches under each tree.
        box('Blocker_Benches',(x,y+4,.45),(3.4,.7,.25),'Bark')
        for xx in [-1.3,1.3]:
            box('Bench_Legs',(x+xx,y+4,.23),(.12,.55,.46),'Steel')
for side in [-1,1]:
    for y in range(-85,151,18):
        tree(side*155,y,random.uniform(9,13),True)
# Distant wooded foothills and mature forest around the bowl.
for cx,cy,sx,sy,h in [(-300,130,125,120,26),(255,180,150,110,35),(-130,230,180,90,32),(100,270,190,65,25)]:
    oval('Woodland_Terrain',(cx,cy,-13),(sx,sy,h),'LeafDark',28,12)
for i in range(220):
    x=random.uniform(-390,390);y=random.uniform(140,340)
    if abs(x)<145 and y<155:continue
    base=max(0,10*(1-abs(y-220)/150))
    # Keep road and concourse open. Woodland trunks are decorative at the horizon.
    h=random.uniform(10,17)
    tree(x,y,h,False)
for i in range(65):
    side=random.choice([-1,1]);x=side*random.uniform(205,390);y=random.uniform(-70,165)
    tree(x,y,random.uniform(10,16),False)
# A calm reservoir behind the woods, echoing the supplied aerial context.
mat('Reservoir',(.03,.24,.27),.16,.25)
oval('Reservoir',(20,375,-.05),(290,90,.18),'Reservoir',64,2)
# Street lights and entrances provide human scale at walking height.
for x in range(-300,301,45):
    beam('Street_Lights',(x,-184,.2),(x,-184,9),.11,'Steel')
    beam('Street_Light_Arms',(x,-184,9),(x+2,-184,9.3),.09,'Steel')
    box('Street_Light_Heads',(x+2,-184,9.25),(1.2,.45,.16),'Ivory')
for x in [-92,92]:
    box('Ticket_Office',(x,-131,1.7),(8,5,3.4),'Ivory')
    box('Ticket_Window',(x,-133.55,1.8),(6,.08,1.35),'Glass')
    box('Ticket_Awning',(x,-133.9,3.4),(8.5,1.2,.2),'LionsBlue')
# Replace radial grass wedges with parallel mown strips clipped to the baseball fan.
for ob in list(COL.objects):
    if ob.name.startswith('Field_Mowed_Stripes'):
        bpy.data.objects.remove(ob,do_unlink=True)
def clip(poly,fn):
    if not poly:return []
    result=[]
    prev=poly[-1];pv=fn(prev)
    for cur in poly:
        cv=fn(cur)
        if (pv>=0)!=(cv>=0):
            t=pv/(pv-cv);result.append(tuple(prev[j]+(cur[j]-prev[j])*t for j in range(3)))
        if cv>=0:result.append(cur)
        prev,pv=cur,cv
    return result
fan=[(0,40,.205)]+[(104*math.cos(math.radians(a)),40+104*math.sin(math.radians(a)),.205) for a in range(225,316,2)]
for k in range(-18,19):
    poly=clip(fan,lambda p,k=k:p[0]+p[1]*.6-k*8)
    poly=clip(poly,lambda p,k=k:(k+1)*8-p[0]-p[1]*.6)
    if len(poly)>2:add('Field_Mowed_Parallel',poly,[tuple(range(len(poly)))],'GrassLight' if k%2 else 'Grass')
flush()
# Darker royal blues match the supplied seating photograph in daylight.
for name,c in [('BlueSeat',(.004,.16,.43)),('AzureSeat',(.008,.27,.52)),('NavySeat',(.002,.065,.22))]:
    bs=next(n for n in MATS[name].node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(*c,1);MATS[name].diffuse_color=(*c,1)
print('ENVIRONMENT',len(OBJS),'batched meshes; roads, 300+ trees, parking and plaza details')


# Mount the supplied vector sign on the actual south facade.
from mathutils import Matrix
for ob in list(COL.objects):
    if ob.name.startswith('Gate_Sign_Backing_'):
        bpy.data.objects.remove(ob,do_unlink=True)
box('Gate_Sign_Backing',(0,-107.8,14.3),(96,1.25,11.8),'Ivory')
flush()
before=set(bpy.data.objects)
bpy.ops.import_curve.svg(filepath=str(ROOT/'assets'/'blender'/'facade.svg'))
imported=[o for o in bpy.data.objects if o not in before]
for ob in imported:
    for coll in list(ob.users_collection):coll.objects.unlink(ob)
    COL.objects.link(ob)
bpy.context.view_layer.update()
coords=[ob.matrix_world@Vector(corner) for ob in imported for corner in ob.bound_box]
minx=min(v.x for v in coords);maxx=max(v.x for v in coords)
miny=min(v.y for v in coords);maxy=max(v.y for v in coords)
cx=(minx+maxx)/2;cy=(miny+maxy)/2
factor=65/(maxx-minx)
mount=Matrix.Translation((0,-116.1,14.1))@Matrix.Rotation(math.pi/2,4,'X')@Matrix.Scale(factor,4)@Matrix.Translation((-cx,-cy,0))
bpy.ops.object.select_all(action='DESELECT')
for ob in imported:
    ob.matrix_world=mount@ob.matrix_world
    ob.select_set(True)
bpy.context.view_layer.objects.active=imported[0]
bpy.ops.object.convert(target='MESH')
converted=[ob for ob in bpy.context.selected_objects if ob.type=='MESH']
for ob in converted:
    bpy.context.view_layer.objects.active=ob
    for other in converted:other.select_set(other==ob)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    mod=ob.modifiers.new('Raised_Vector_Sign','SOLIDIFY');mod.thickness=.065;mod.offset=0
    bpy.ops.object.modifier_apply(modifier=mod.name)
for ob in converted:ob.select_set(True)
bpy.context.view_layer.objects.active=converted[0]
bpy.ops.object.join()
sign=bpy.context.object;sign.name='Facade_Original_SVG_Daegu_Samsung_Lions_Park';OBJS.append(sign)

# SVG importer uses Diffuse shaders; convert to glTF-supported Principled shaders while preserving its linear colors.
for m in sign.data.materials:
    color=tuple(m.diffuse_color)
    m.use_nodes=True;m.node_tree.nodes.clear()
    bs=m.node_tree.nodes.new('ShaderNodeBsdfPrincipled');bs.inputs['Base Color'].default_value=color;bs.inputs['Roughness'].default_value=.55
    out=m.node_tree.nodes.new('ShaderNodeOutputMaterial');m.node_tree.links.new(bs.outputs['BSDF'],out.inputs['Surface'])

font=bpy.data.fonts.load(r'C:\Windows\Fonts\malgunbd.ttf')
for side in [-1,1]:
    text('Gate_Entrance_Name','대구삼성라이온즈파크',(side*57,-116.2,5.8),2.3,'LionsBlue',font=font)
    text('Gate_Number','GATE 1' if side<0 else 'GATE 2',(side*57,-116.25,1.2),.85,'WhitePaint',font=font)
text('Welcome','SAMSUNG LIONS PARK',(0,-116.3,9.85),1.1,'LionsBlue')
text('Scoreboard_Lettering','WIN OR\nWOW',(-83,-65.8,18.2),4.4,'WhitePaint')
# Separate marked walkable surface through the open central gate.
box('WalkSurface_Gate',(0,-92,.20),(18,57,.12),'PavingLight')
box('WalkSurface_Access_Path',(0,-151,.13),(14,61,.1),'Paving')
flush()
# Remove unnecessary UV attributes from untextured plastic and structural materials.
removed_uv=0
for ob in COL.objects:
    if ob.type!='MESH':continue
    textured=any(m and m.use_nodes and any(n.type=='TEX_IMAGE' for n in m.node_tree.nodes) for m in ob.data.materials)
    if not textured:
        for layer in list(ob.data.uv_layers):ob.data.uv_layers.remove(layer);removed_uv+=1
print('SIGN_IMPORTED',len(converted),'vector components; mounted width',round(sign.dimensions.x,1),'m. Removed redundant UV sets:',removed_uv)


# Use a CC0 photographic sky panorama.
import bmesh, json
world=SCENE.world
env=next(n for n in world.node_tree.nodes if n.type=='TEX_ENVIRONMENT')
SCENE.render.image_settings.file_format='JPEG'
SCENE.render.image_settings.quality=92
SCENE.render.image_settings.color_mode='RGB'
# The baked sky image is already shipped in public/models.
sky_image=bpy.data.images.load(str(OUT/'lionspark-sky.jpg'),check_existing=True)
sky_material=bpy.data.materials.new('Sky_Photographic_Park_Panorama');sky_material.use_nodes=True
nodes=sky_material.node_tree.nodes;nodes.clear()
out=nodes.new('ShaderNodeOutputMaterial');em=nodes.new('ShaderNodeEmission');tex=nodes.new('ShaderNodeTexImage');tex.image=sky_image
em.inputs['Strength'].default_value=1
sky_material.node_tree.links.new(tex.outputs['Color'],em.inputs['Color'])
sky_material.node_tree.links.new(em.outputs['Emission'],out.inputs['Surface'])
bpy.ops.mesh.primitive_uv_sphere_add(segments=64,ring_count=32,radius=1800,location=(0,0,0))
sky=bpy.context.object;sky.name='SkyDome_Photographic_Environment'
for coll in list(sky.users_collection):coll.objects.unlink(sky)
COL.objects.link(sky)
bm=bmesh.new();bm.from_mesh(sky.data);bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(sky.data);bm.free()
sky.data.materials.append(sky_material)
sky.hide_render=True
sky.visible_shadow=False
OBJS.append(sky)
# Smooth organic surfaces while keeping architectural edges crisp.
for ob in COL.objects:
    if ob.type=='MESH' and any(t in ob.name for t in ['Canopies','Woodland','Reservoir']):
        for p in ob.data.polygons:p.use_smooth=True
# Precise walking colliders: one box for each disconnected component of batched Blocker meshes.
boxes=[]
for ob in COL.objects:
    if ob.type!='MESH' or not ob.name.startswith('Blocker'):continue
    mesh=ob.data;n=len(mesh.vertices);parent=list(range(n))
    def find(x):
        while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
        return x
    for edge in mesh.edges:
        a,b=edge.vertices;ra,rb=find(a),find(b)
        if ra!=rb:parent[rb]=ra
    components={}
    for v in mesh.vertices:
        p=ob.matrix_world@v.co
        components.setdefault(find(v.index),[]).append(p)
    for points in components.values():
        lo=[min(p[j] for p in points) for j in range(3)];hi=[max(p[j] for p in points) for j in range(3)]
        boxes.append(dict(minX=lo[0],maxX=hi[0],minY=lo[2],maxY=hi[2],minZ=-hi[1],maxZ=-lo[1]))
collision=dict(boxes=boxes,spawn=[0,1.7,165],overview=[255,240,340],units='meters',source='Blender model connected components')
(OUT/'lionspark-collision.json').write_text(json.dumps(collision,separators=(',',':')),encoding='utf-8')
(ROOT/'public'/'models'/'credits.txt').write_text('Stadium reconstructed in Blender from the supplied aerial reference; unseen details are interpretive.\nOriginal facade sign: supplied 대구 삼성 라이온즈 파크.svg.\nPhotographic sky: Kloofendal 38d Partly Cloudy Pure Sky by Greg Zaal and Jarod Guest, Poly Haven, CC0. https://polyhaven.com/a/kloofendal_38d_partly_cloudy_puresky\n',encoding='utf-8')
print('SKY',sky_image.size[:],'; precise collision boxes',len(boxes),'; vertices',sum(len(o.data.vertices) for o in COL.objects if o.type=='MESH'))


# Portable real-scale CC0 concrete paving.
paving_mat=bpy.data.materials.new('Concrete_Pavement_03');paving_mat.use_nodes=True
bs=next(n for n in paving_mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
tex_dir=ROOT/'assets'/'blender'/'textures'
for image_path in tex_dir.glob('*.jpg'):
    node=paving_mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=bpy.data.images.load(str(image_path),check_existing=True)
    if 'Diffuse' in image_path.name:paving_mat.node_tree.links.new(node.outputs['Color'],bs.inputs['Base Color'])
    elif 'Rough' in image_path.name:
        node.image.colorspace_settings.name='Non-Color';paving_mat.node_tree.links.new(node.outputs['Color'],bs.inputs['Roughness'])
    elif 'nor_gl' in image_path.name:
        node.image.colorspace_settings.name='Non-Color';normal=paving_mat.node_tree.nodes.new('ShaderNodeNormalMap');paving_mat.node_tree.links.new(node.outputs['Color'],normal.inputs['Color']);paving_mat.node_tree.links.new(normal.outputs['Normal'],bs.inputs['Normal'])
for name in ['WalkSurface_Plaza_PavingLight','WalkSurface_Front_Sidewalk_PavingLight','WalkSurface_Concourse_Paving','WalkSurface_Access_Path_Paving','WalkSurface_Gate_PavingLight']:
    ob=bpy.data.objects[name];ob.data.materials.clear();ob.data.materials.append(paving_mat)
    uv=ob.data.uv_layers.active
    for poly in ob.data.polygons:
        for li in poly.loop_indices:
            co=ob.matrix_world@ob.data.vertices[ob.data.loops[li].vertex_index].co;uv.data[li].uv=(co.x/2.1,co.y/2.1)


# Export the modeled geometry, not Blender lights/cameras, for the existing Three.js viewer.
bpy.ops.object.select_all(action='DESELECT')
for ob in list(COL.objects):
    if ob.type=='FONT':
        ob.select_set(True);bpy.context.view_layer.objects.active=ob
        bpy.ops.object.convert(target='MESH');ob.select_set(False)
for ob in COL.objects:
    ob.select_set(ob.type=='MESH')
bpy.ops.export_scene.gltf(
    filepath=str(OUT/'lionspark.glb'),
    export_format='GLB',use_selection=True,use_active_scene=True,use_visible=False,use_renderable=False,
    export_apply=True,export_yup=True,export_extras=True,export_animations=False,
    export_draco_mesh_compression_enable=True,export_draco_mesh_compression_level=6,
    export_draco_position_quantization=16,export_draco_normal_quantization=10,
    export_draco_texcoord_quantization=12,
)
bpy.ops.file.pack_all()
SCENE.render.image_settings.file_format='PNG'
SCENE.render.filepath=str(ROOT/'.lemonade'/'lionspark-aerial.png')
(ROOT/'.lemonade').mkdir(exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'.lemonade'/'lionspark.blend'),compress=True)
print('EXPORT_BYTES',(OUT/'lionspark.glb').stat().st_size)
print('SAVED_BLEND',bpy.data.filepath)
