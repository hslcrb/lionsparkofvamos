# Blender MCP reconstruction, v2. Photo-based geometry; hidden detail interpreted.

import bpy, math, random, os, pathlib
from mathutils import Vector
random.seed(1982)
ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "public" / "models"
OUT.mkdir(parents=True, exist_ok=True)
if bpy.data.scenes.get('Lionspark_Octagonal_V2'):
    raise RuntimeError('Open the saved v2 blend to edit it, or run this rebuild in a new Blender file.')
SCENE = bpy.data.scenes.new('Lionspark_Octagonal_V2')
bpy.context.window.scene = SCENE
SCENE.unit_settings.system = 'METRIC'
COL = bpy.data.collections.new("Lionspark_V2_World")
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

# V2 reference reconstruction. Eight explicit, unequal straight sides.
P=[(-62,-128),(62,-128),(136,-54),(136,62),(62,136),(-62,136),(-136,62),(-136,-54)]
def pp(side,t,s=1,z=0):
    a=P[side%8];b=P[(side+1)%8]
    return ((a[0]+(b[0]-a[0])*t)*s,(a[1]+(b[1]-a[1])*t)*s,z)
def face(name,points,material):add(name,points,[tuple(range(len(points)))],material)
def panel(name,side,t0,t1,s0,s1,z0,z1,thick,material):
    p=[pp(side,t0,s0,z0),pp(side,t1,s0,z0),pp(side,t1,s1,z1),pp(side,t0,s1,z1)]
    v=p+[(x,y,z-thick) for x,y,z in p]
    add(name,v,[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],material)
def linebox(name,a,b,width,height,material):
    a,b=Vector(a),Vector(b);d=b-a
    box(name,(a+b)/2,(d.xy.length,width,height),material,math.atan2(d.y,d.x))
def seat(p,angle,material):
    x,y,z=p
    box('Seat_Pans',(x,y,z+.23),(.46,.43,.10),material,angle)
    dx=-math.sin(angle)*.19;dy=math.cos(angle)*.19
    box('Seat_Backs',(x+dx,y+dy,z+.49),(.46,.08,.43),material,angle)
mat('RedPath',(.42,.115,.065),.94,texture=True)
mat('Water',(.035,.23,.22),.25,.25)
mat('LightStone',(.72,.74,.70),.87,texture=True)
mat('TurfShade',(.065,.18,.021),.97,texture=True)
# Reuse the real pavement PBR and photographed sky from the preserved scene.
old=bpy.data.scenes.get('Lionspark')
if old:
    SCENE.world=old.world.copy()
    for ob in old.objects:
        if ob.name.startswith('Sky'):
            sky=ob.copy();sky.data=ob.data.copy();COL.objects.link(sky);OBJS.append(sky)
    for key in ['Paving','PavingLight']:
        src=next((o for o in old.objects if o.name.startswith('WalkSurface_Plaza')),None)
        if src:MATS[key]=src.data.materials[0]
else:
    world=bpy.data.worlds.new('V2_Photographic_Sky');world.use_nodes=True;SCENE.world=world
    bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND')
    env=world.node_tree.nodes.new('ShaderNodeTexEnvironment')
    env.image=bpy.data.images.load(str(OUT/'lionspark-sky.jpg'),check_existing=True)
    world.node_tree.links.new(env.outputs['Color'],bg.inputs['Color']);bg.inputs['Strength'].default_value=.7

if not old:
    # Fresh-file fallback: create the same exported photo-sky dome and real pavement material.
    import bmesh
    sky_mat=bpy.data.materials.new('Sky_V2_Photographic');sky_mat.use_nodes=True
    nodes=sky_mat.node_tree.nodes;nodes.clear()
    out=nodes.new('ShaderNodeOutputMaterial');em=nodes.new('ShaderNodeEmission');tex=nodes.new('ShaderNodeTexImage')
    tex.image=env.image;sky_mat.node_tree.links.new(tex.outputs['Color'],em.inputs['Color'])
    sky_mat.node_tree.links.new(em.outputs['Emission'],out.inputs['Surface'])
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64,ring_count=32,radius=1800)
    sky=bpy.context.object;sky.name='SkyDome_V2_Photographic';sky.hide_render=True;sky.visible_shadow=False
    for coll in list(sky.users_collection):coll.objects.unlink(sky)
    COL.objects.link(sky)
    bm=bmesh.new();bm.from_mesh(sky.data);bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(sky.data);bm.free()
    sky.data.materials.append(sky_mat)
    for k in ['Paving','PavingLight']:
        material=MATS[k];bs=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        for suffix,socket in [('Diffuse','Base Color'),('Rough','Roughness')]:
            node=material.node_tree.nodes.new('ShaderNodeTexImage')
            node.image=bpy.data.images.load(str(ROOT/'assets'/'blender'/'textures'/('concrete_pavement_03_'+suffix+'_1k.jpg')),check_existing=True)
            if suffix!='Diffuse':node.image.colorspace_settings.name='Non-Color'
            material.node_tree.links.new(node.outputs['Color'],bs.inputs[socket])

font=bpy.data.fonts.load(r'C:\Windows\Fonts\malgunbd.ttf',check_existing=True)
sun_data=bpy.data.lights.new('V2_Daylight','SUN');sun_data.energy=2.5;sun_data.angle=math.radians(2.2)
sun=bpy.data.objects.new('V2_Daylight',sun_data);COL.objects.link(sun);sun.rotation_euler=(.48,-.42,-.52)
cam_data=bpy.data.cameras.new('V2_Aerial');cam=bpy.data.objects.new('V2_Aerial',cam_data);COL.objects.link(cam)
cam.location=(305,-390,330);cam.rotation_euler=(Vector((0,10,2))-cam.location).to_track_quat('-Z','Y').to_euler()
cam_data.lens=43;cam_data.clip_end=5000;SCENE.camera=cam
SCENE.render.resolution_x=1500;SCENE.render.resolution_y=1100;SCENE.render.resolution_percentage=100
SCENE.view_settings.view_transform='AgX'
print('V2_READY',SCENE.name,'8 straight sides')



# The site blends into a broad circular terrain, without a visible square base.
face('WalkSurface_Terrain',[(1550*math.cos(i*math.tau/160),1550*math.sin(i*math.tau/160),-.09) for i in range(160)],'Grass')
face('WalkSurface_Concourse',[(x*1.18,y*1.18,.02) for x,y in P],'Paving')
# Baseball outfield and parallel mowing bands clipped to the polygon.
turf=[(0,61),(-94,-33),(-94,-53),(-58,-92),(58,-92),(94,-53),(94,-33)]
def clipy(poly,cut,above):
    out=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        ina=(a[1]>=cut) if above else (a[1]<=cut)
        inb=(b[1]>=cut) if above else (b[1]<=cut)
        if ina:out.append(a)
        if ina!=inb:
            t=(cut-a[1])/(b[1]-a[1]);out.append((a[0]+t*(b[0]-a[0]),cut))
    return out
face('WalkSurface_Field',[(x,y,.15) for x,y in turf],'Grass')
for j in range(16):
    poly=clipy(clipy(turf,-95+j*10,True),-85+j*10,False)
    if len(poly)>2:face('Field_Mowing_Stripes',[(x,y,.158) for x,y in poly],'GrassLight' if j%2 else 'Grass')
# Rounded infield clay and the grass diamond, oriented toward open outfield.
clay=[(-3,58),(3,58),(31,30)]
clay += [(34*math.cos(a),28+34*math.sin(a)) for a in [math.radians(-i*180/36) for i in range(37)]]
clay += [(-31,30)]
face('Field_Clay',[(x,y,.18) for x,y in clay],'Dirt')
face('Infield_Diamond',[(-1,50,.195),(23.5,27,.195),(0,3,.195),(-23.5,27,.195)],'GrassLight')
oval('Mound',(0,27,.27),(3,3,.16),'Dirt',40,3)
for x,y in [(26,27),(0,1),(-26,27)]:
    box('Bases',(x,y,.32),(.62,.62,.14),'WhitePaint',math.pi/4)
box('Pitcher_Rubber',(0,27,.45),(.65,.15,.06),'WhitePaint')
face('Home_Plate',[(-.25,53.22,.23),(.25,53.22,.23),(.25,52.98,.23),(0,52.72,.23),(-.25,52.98,.23)],'WhitePaint')
for s in [-1,1]:
    linebox('Foul_Lines',(0,53,.22),(s*91,-38,.22),.12,.025,'WhitePaint')
    for x in [-1.4,1.4]:box('Batters_Box',(x,53,.225),(.08,2,.02),'WhitePaint')
    box('Batters_Box',(s*1.4,52,.225),(1.3,.08,.02),'WhitePaint')
    beam('Yellow_Foul_Poles',(s*91,-38,.18),(s*91,-38,24),.13,'YellowPaint')
# Straight sided 2-tier grandstands; the front three sides remain low and open.
seat_count=0
for side in range(2,7):
    for tier,rows,sbase,ds,zbase,dz in [(0,22,.665,.0105,1.55,.59),(1,18,.915,.0082,17.65,.69)]:
        for row in range(rows):
            s=sbase+row*ds;z=zbase+row*dz
            panel('Grandstand_Treads',side,0,1,s,s+ds,z,z,.59,'Concrete')
            a,b=Vector(pp(side,0,s)),Vector(pp(side,1,s));d=b-a;length=d.length
            angle=math.atan2(d.y,d.x)+math.pi
            count=int(length/.63)
            for i in range(count):
                t=(i+.5)/count
                if min(abs(t-q) for q in [.025,.26,.5,.74,.975])<.018:continue
                seat(pp(side,t,s+ds*.47,z+.035),angle,'NavySeat' if tier else ('BlueSeat' if (side+int(t*4))%3 else 'AzureSeat'))
                seat_count+=1
            # The white aisle steps rise in three shallow increments per seating row.
            for t in [.025,.26,.5,.74,.975]:
                for sub in range(3):
                    q=s+ds*sub/3
                    panel('WalkSurface_Aisle_Steps',side,t-.014,t+.014,q,q+ds/3,z-.39+sub*.197,z-.39+sub*.197,.20,'Ivory')
    # Intermediate circulation ribbon, dark suites, and roof-level outer walkway.
    panel('WalkSurface_Mid_Concourse',side,0,1,.885,.927,15.1,15.1,.35,'Ivory')
    panel('Blue_Ribbon',side,0,1,.893,.899,16.6,16.6,1.15,'LionsBlue')
    panel('Suite_Window_Band',side,0,1,.904,.91,17.5,17.5,1.65,'Glass')
    for t in [.145,.38,.62,.855]:
        a,b=pp(side,t-.025,.904,16.1),pp(side,t+.025,.904,16.1)
        linebox('Exit_Portals',a,b,.55,2.4,'DarkMetal')
        linebox('Portal_Headers',pp(side,t-.026,.902,17.38),pp(side,t+.026,.902,17.38),.65,.20,'LionsBlue')
    panel('WalkSurface_Upper_Concourse',side,0,1,1.058,1.105,30.2,30.2,.4,'Ivory')
    # Five continuous but visibly faceted roof planes with white ribs.
    panel('White_Angular_Canopy',side,0,1,.89,1.145,31.9,35.2,.38,'Roof')
    panel('Canopy_Blue_Fascia',side,0,1,.889,.896,31.95,32.05,.6,'LionsBlue')
    for j in range(13):
        t=j/12
        beam('Roof_Seams',pp(side,t,.895,32.0),pp(side,t,1.14,35.25),.055,'Ivory')
        beam('Roof_Trusses',pp(side,t,.9,31.5),pp(side,t,1.13,34.7),.15,'Steel')
        beam('Roof_Truss_Braces',pp(side,t,.90,31.4),pp(side,t,1.06,29.2),.10,'Steel')
# Low external-field seating in turquoise and faceted decks.
for side in [7,0,1]:
    for row in range(10):
        s=.724+row*.014;z=1.05+row*.37
        panel('Outfield_Seating_Treads',side,0,1,s,s+.014,z,z,.37,'Ivory')
        a,b=Vector(pp(side,0,s)),Vector(pp(side,1,s));d=b-a
        count=int(d.length/.65);angle=math.atan2(d.y,d.x)+math.pi
        for j in range(count):
            t=(j+.5)/count
            if min(abs(t-q) for q in [.1,.36,.64,.9])<.022:continue
            seat(pp(side,t,s+.007,z+.02),angle,'AzureSeat');seat_count+=1
    panel('WalkSurface_Outfield_Deck',side,0,1,.866,1.035,5.0,5.0,.3,'Ivory')
    # Gate 2 middle opening is kept clear through the low pavilion.
    for t0,t1 in ([(0,.37),(.63,1)] if side==0 else [(0,1)]):
        panel('Blocker_Outfield_Pavilion',side,t0,t1,.91,1.03,4.7,4.7,4.7,'Ivory')
        panel('Outfield_Pavilion_Windows',side,t0,t1,1.031,1.033,3.6,3.6,2.2,'Glass')
        panel('Outfield_Blue_Trim',side,t0,t1,1.034,1.037,4.3,4.3,.42,'LionsBlue')
    for j in range(20):
        t=(j+.5)/20
        if side==0 and .37<t<.63:continue
        beam('Pavilion_Mullions',pp(side,t,1.038,.7),pp(side,t,1.038,4.2),.07,'Steel')
    # Inner boundary has a gate break at the central outfield.
    for t0,t1 in ([(0,.41),(.59,1)] if side==0 else [(0,1)]):
        panel('Blocker_Outfield_Fence',side,t0,t1,.716,.721,1.45,1.45,1.45,'LionsBlue')
# Ground level access enters through the central pavilion and reaches the field.
box('WalkSurface_Gate2',(0,-119,.10),(21,70,.12),'PavingLight')
flush()
print('V2_BOWL',seat_count,'seats;',len(OBJS),'batched meshes; polygon',P)



# Faceted white exterior with cantilevered gallery bands, gate recesses and columns.
def wall(name,side,t0,t1,s0,s1,z0,z1,material):
    pts=[pp(side,t0,s0,z0),pp(side,t1,s0,z0),pp(side,t1,s1,z1),pp(side,t0,s1,z1)]
    face(name,pts,material)
    face(name,[(x*.997,y*.997,z) for x,y,z in reversed(pts)],material)
for side in range(2,7):
    gaps=[(0,.39),(.61,1)] if side in [2,6] else [(0,1)]
    for a,b in gaps:wall('Blocker_Exterior_Base',side,a,b,.986,1.008,0,7.0,'Ivory')
    for z0,z1,s0,s1,material in [(7,10,1.008,1.02,'Glass'),(10,19,1.02,1.065,'Ivory'),(19,23,1.065,1.08,'Glass'),(23,30.7,1.08,1.112,'Ivory')]:
        wall('Cantilever_White_Facade' if material=='Ivory' else 'Exterior_Window_Ribbon',side,0,1,s0,s1,z0,z1,material)
    for j in range(17):
        t=j/16
        beam('Exterior_Slender_Columns',pp(side,t,.993,.15),pp(side,t,1.085,26.5),.21,'Ivory')
        for z,s in [(8.5,1.02),(21,1.081)]:
            beam('Window_Mullions',pp(side,t,s,z-1.45),pp(side,t,s,z+1.45),.065,'Steel')
    for z,s in [(6.9,1.015),(11,1.035),(19.0,1.076),(30.5,1.116)]:
        panel('Gallery_Projecting_Ledges',side,0,1,s,s+.025,z,z,.3,'Roof')
    for j in range(9):
        t=j/8
        beam('External_Steel_Braces',pp(side,t,.98,2),pp(side,t,1.08,24),.16,'Steel')
# Gate 1 and Gate 3 long forecourts and external stairs/ramp systems.
for side,label in [(2,'GATE 1'),(6,'GATE 3')]:
    a,b=Vector(pp(side,.36,1.03,7.35)),Vector(pp(side,.64,1.03,7.35))
    linebox('Gate_Entrance_Canopy',a,b,9,.45,'Roof')
    # Canopy columns sit at edges; the doorway remains open.
    for t in [.36,.64]:
        beam('Blocker_Gate_Columns',pp(side,t,1.05,.1),pp(side,t,1.05,7.2),.28,'Steel')
    p=pp(side,.5,1.04,4.5);rot=math.pi/2 if side==2 else -math.pi/2
    text('Gate_Number',label,p,2,'LionsBlue',rotation=(math.pi/2,0,rot),font=font)
    # Broad side stair reaches a terrace in shallow 18 cm risers.
    for step in range(28):
        x=(151+step*.38)*(1 if side==2 else -1)
        box('WalkSurface_Exterior_Steps',(x,48,.09+step*.18),(.4,10,.18),'LightStone')
    for y in [43,53]:
        beam('Stair_Handrails',((151)*(1 if side==2 else -1),y,1.1),((161.6)*(1 if side==2 else -1),y,6.1),.05,'Steel')
# Front outfield gate has a low fascia rather than a detached sign wall.
box('Gate2_Entry_Fascia',(0,-132.5,6.2),(34,1.0,1.4),'LionsBlue')
box('Gate2_Entry_Canopy',(0,-136,5.1),(38,10,.35),'Roof')
for x in [-18,18]:beam('Blocker_Gate2_Columns',(x,-139,.1),(x,-139,5),.22,'Steel')
text('Gate2_Lettering','GATE 2',(0,-133.1,5.85),1.05,'WhitePaint',font=font)
# Giant southwest outfield scoreboard: a shield/pentagon with stepped supports.
# A local facade baseline is angled to follow the clipped southwest corner.
score_center=Vector((-87,-88,0));ang=-math.pi/4
def scorep(x,y,z):
    return (score_center.x+x*math.cos(ang)-y*math.sin(ang),score_center.y+x*math.sin(ang)+y*math.cos(ang),z)
outline=[(-22,6),(-22,22),(-12,22),(0,37),(12,22),(22,22),(22,6)]
verts=[scorep(x,y,z) for y in [-1.4,1.4] for x,z in outline];n=len(outline)
add('Blue_Pentagonal_Scoreboard',verts,[tuple(reversed(range(n))),tuple(range(n,n*2))]+[(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)],'LionsBlue')
for s in [-1,1]:
    for j in range(3):
        x=s*(23+j*4)
        box('Scoreboard_Stepped_Supports',scorep(x,0,7.8-j*1.7),(4,7,15.6-j*3.4),'Ivory' if j%2==0 else 'LionsBlue',ang)
for a,b in zip(outline,outline[1:]+outline[:1]):
    beam('Scoreboard_Silver_Outline',scorep(a[0],-1.48,a[1]),scorep(b[0],-1.48,b[1]),.12,'Ivory')
text('Scoreboard_Slogan','YES! BEGIN AGAIN!',scorep(0,-1.55,9.4),1.45,'WhitePaint',rotation=(math.pi/2,0,ang),font=font)
text('Scoreboard_Club','SAMSUNG',scorep(0,-1.55,28.0),1.1,'WhitePaint',rotation=(math.pi/2,0,ang),font=font)
# A discreet actual LED screen on the inward-facing panel.
box('Scoreboard_Inner_Screen',scorep(0,1.47,19),(34,.12,16),'DarkMetal',ang)
text('Scoreboard_Screen_Letters','LIONS',scorep(0,1.56,18),4,'WhitePaint',rotation=(math.pi/2,0,ang+math.pi),font=font)
# Six white floodlight masts, four A-frames on the roof and two exterior towers.
for side,t in [(3,.1),(3,.85),(5,.15),(5,.9)]:
    p=Vector(pp(side,t,1.105,34.7));q=Vector(pp(side,t,.98,34.7));center=(p+q)/2;h=48.8
    for dx in [-4,4]:
        beam('Roof_Floodlight_AFrames',(p.x+dx,p.y,p.z),(center.x+dx*.35,center.y,h),.16,'Roof')
        beam('Roof_Floodlight_AFrames',(q.x+dx,q.y,q.z),(center.x+dx*.35,center.y,h),.16,'Roof')
    beam('Floodlight_Cross_Brace',(p.x-4,p.y,p.z),(center.x+1.4,center.y,h),.08,'Steel')
    box('Floodlight_Lamp_Frame',(center.x,center.y,h),(12,.7,3.1),'Steel')
    for j in range(11):
        for k in range(3):box('Floodlight_Reflectors',(center.x-5+j,center.y-.45,h-1+k),(.7,.25,.6),'Roof')
for x,y in [(-113,-33),(113,-33)]:
    for dx in [-.8,.8]:beam('Front_Floodlight_Poles',(x+dx,y,.1),(x+dx*.45,y,46),.24,'Roof')
    for z in range(3,45,4):
        beam('Front_Mast_Lacing',(x-.7,y,z),(x+.7,y,z+4),.06,'Steel')
    box('Front_Light_Frame',(x,y,46),(12,1,3.4),'Steel')
    for j in range(11):
        for k in range(3):box('Floodlight_Reflectors',(x-5+j,y-.6,45+k),(.75,.3,.6),'Roof')
# Low annex with rooftop service details, linked east concourse and stepped plaza.
box('Blocker_East_Annex',(208,82,5),(74,113,10),'Ivory')
box('Annex_Glazed_Front',(208,25.3,4),(68,.2,5.8),'Glass')
box('Annex_Flat_White_Roof',(208,82,10.4),(78,117,.6),'Roof')
for x in [180,195,210,225,240]:
    box('Annex_Roof_Skylights',(x,84,10.95),(4,70,.35),'Glass')
for j in range(12):
    box('Annex_Roof_Plant',(179+(j%6)*11,125-(j//6)*10,11.2),(4,3,1.1),'Steel')
box('Annex_Covered_Link',(158,70,6),(30,11,.45),'Roof')
for x in [146,160,172]:beam('Annex_Link_Pillars',(x,70,.1),(x,70,5.9),.24,'Steel')
for j in range(24):
    box('WalkSurface_Annex_Plaza_Steps',(206,12-j*.52,.09+j*.15),(74,.54,.18),'LightStone')
# West outfield grass berm and walking promenade.
for j in range(7):
    box('West_Field_Berm',(-127-j*2.9,-45,1.0+j*.25),(3.0,52,.5),'GrassLight')
box('WalkSurface_Berm_Promenade',(-150,-46,2.8),(6,64,.2),'PavingLight')
for j in range(16):
    box('WalkSurface_Berm_Access',(-150,-88+j*.7,.09+j*.17),(6,.72,.18),'LightStone')
flush()
print('EXTERIOR complete',len(OBJS),'batches')



# Give the foul territory a grass edge and narrow warning track, instead of a broad paved void.
face('Field_Warning_Track',[pp(i,0,.667,.13) for i in range(8)],'Dirt')
face('Field_Foul_Turf',[pp(i,0,.644,.14) for i in range(8)],'Grass')
# Front entrance plaza follows the clipped stadium corners.
plaza=[(-161,-143),(-65,-159),(70,-159),(231,-214),(-174,-214)]
face('WalkSurface_Entrance_Plaza',[(x,y,.045) for x,y in plaza],'PavingLight')
for x in [-94,-54,54,94]:
    linebox('Plaza_Paving_Inlays',(x,-151,.06),(x*1.34,-211,.06),.22,.025,'Steel')
# Roads, red cycle paths, pale sidewalks and full intersections.
def road(a,b,width=24):
    linebox('WalkSurface_Road',(*a,.0),(*b,.0),width,.08,'Asphalt')
    av,bv=Vector(a),Vector(b);d=(bv-av);length=d.length;u=d.normalized();n=Vector((-u.y,u.x))
    for sign in [-1,1]:
        v=n*sign*(width/2+3.1)
        linebox('WalkSurface_Red_Cycleway',(*(av+v),.03),(*(bv+v),.03),4.1,.08,'RedPath')
        v=n*sign*(width/2+7.0)
        linebox('WalkSurface_Road_Sidewalk',(*(av+v),.065),(*(bv+v),.065),3.7,.09,'PavingLight')
        v=n*sign*(width/2+.15)
        linebox('Road_Edge_Line',(*(av+v),.055),(*(bv+v),.055),.13,.025,'WhitePaint')
        v=n*sign*.22
        linebox('Road_Centre_Lines',(*(av+v),.055),(*(bv+v),.055),.12,.025,'YellowPaint')
    for j in range(int(length/10)):
        p=av+u*(j*10+3)
        for offset in [-8,-4,4,8]:
            if abs(offset)<width/2-1:
                v=n*offset
                linebox('Road_Lane_Dashes',(*(p+v),.055),(*(p+v+u*4.6),.055),.12,.025,'WhitePaint')
road((-610,-235),(620,-235),28)
road((295,-590),(295,590),28)
road((-286,-580),(-286,580),22)
road((-285,205),(360,205),15)
# Longitudinal parking aisles and landscaped dividers on both sides.
def car(x,y,rot=0,material='CarWhite'):
    box('Parked_Cars',(x,y,.72),(1.85,4.5,1.22),material,rot)
    box('Car_Windows',(x,y+.15,.0+1.48),(1.65,2.2,.40),'Glass',rot)
    for s in [-1,1]:
        for j in [-1,1]:
            dx=s*.91;dy=j*1.35
            c=(x+dx*math.cos(rot)-dy*math.sin(rot),y+dx*math.sin(rot)+dy*math.cos(rot),.43)
            box('Car_Tires',c,(.25,.66,.58),'Tire',rot)
def parking(x0,y0,cols,rows):
    box('WalkSurface_Parking',(x0+(cols-1)*2.75/2,y0+(rows-1)*13/2,.005),(cols*2.75+6,rows*13+9,.06),'Asphalt')
    for j in range(rows):
        y=y0+j*13
        for i in range(cols+1):
            x=x0+(i-.5)*2.75
            box('Parking_Stall_Markings',(x,y,.05),(.09,5.3,.025),'WhitePaint')
        for i in range(cols):
            if random.random()<.7:car(x0+i*2.75,y,0,random.choice(['CarWhite','CarWhite','CarGrey','CarBlue']))
        box('Parking_Divider',(x0+(cols-1)*2.75/2,y+5.7,.25),(cols*2.75,1.6,.45),'LightStone')
        box('Parking_Divider_Planting',(x0+(cols-1)*2.75/2,y+5.7,.49),(cols*2.75-1,1.1,.08),'Grass')
parking(-251,-177,23,24)
parking(-98,170,58,3)
parking(168,-111,34,8)
# Zebra crossings and street trees continue across all visible road ends.
for x in [263,327,-316,-258]:
    for j in range(9):box('Crosswalk',(x,-248+j*3.0,.065),(7,1.4,.025),'WhitePaint')
for y in [-202,-268]:
    for j in range(9):box('Crosswalk',(282+j*3.0,y,.065),(1.4,7,.025),'WhitePaint')
for x,y in [(-285,-235),(295,-235),(295,205)]:
    for dx,dy in [(-20,-18),(20,18),(-20,18),(20,-18)]:
        beam('Signal_Poles',(x+dx,y+dy,.1),(x+dx,y+dy,6),.11,'Steel')
        box('Signal_Housing',(x+dx,y+dy,5.4),(.45,.45,1.2),'DarkMetal')
for j in range(24):
    x=-535+j*46
    for y in [-255,-215]:
        beam('Street_Lighting',(x,y,.1),(x,y,8),.09,'Steel')
        beam('Street_Lighting',(x,y,8),(x+2,y,8.4),.07,'Steel')
        box('Street_Lamp_Head',(x+2,y,8.35),(1.2,.45,.18),'Ivory')
for x,y,rot in [(80,-242,math.pi/2),(-120,-229,math.pi/2),(301,-104,0),(289,124,0),(-280,70,0)]:
    car(x,y,rot,'CarWhite')
# Irregular planted islands and plaza benches.
planters=[(-106,-171,9,5),(-73,-193,7,4),(-32,-183,7,5),(34,-184,9,4),(91,-175,8,5),(136,-194,11,5),(193,-194,8,4)]
for x,y,rx,ry in planters:
    oval('Blocker_Planter_Edge',(x,y,.35),(rx,ry,.35),'LightStone',20,3)
    oval('Planter_Soil',(x,y,.62),(rx-.5,ry-.5,.08),'Sand',18,2)
    for j in range(4):
        a=j*math.pi/2
        oval('Plaza_Shrubs',(x+math.cos(a)*rx*.55,y+math.sin(a)*ry*.5,1),(1.2,1,.65),'LeafSun',8,4)
for x in [-124,-91,-54,56,99,146]:
    box('Bench_Seats',(x,-157,.52),(3.2,.55,.13),'Bark')
    box('Bench_Backrest',(x,-156.75,.89),(3.2,.13,.6),'Bark')
    for dx in [-1.15,1.15]:box('Bench_Supports',(x+dx,-157,.25),(.12,.45,.5),'Steel')
# A blue sculptural fan feature in front of Gate 2, on a circular stone plinth.
oval('Plaza_Art_Platform',(0,-188,.16),(6,5,.16),'LightStone',36,2)
for j in range(7):
    x=-3+j
    beam('Blue_Plaza_Sculpture',(x,-188,.3),(x*1.7,-188,5.5+2*math.sin(j*math.pi/6)),.20,'LionsBlue')
beam('Blue_Plaza_Sculpture',(-5.1,-188,5.5),(5.1,-188,5.5),.17,'LionsBlue')
# Woodland terrain, reservoir shoreline and distant soft mountain silhouettes.
def hillheight(x,y):
    peaks=[(-385,310,30,130,170),(360,410,42,210,120),(-260,720,95,270,170),(420,860,135,330,190),(0,1100,190,470,210),(-750,350,110,250,480)]
    return sum(h*math.exp(-((x-cx)/sx)**2-((y-cy)/sy)**2) for cx,cy,h,sx,sy in peaks)
verts=[];faces=[];nx=92;ny=55
for j in range(ny+1):
    y=220+j*22
    for i in range(nx+1):
        x=-1012+i*22;z=hillheight(x,y)-.09
        verts.append((x,y,z))
for j in range(ny):
    for i in range(nx):
        k=j*(nx+1)+i;faces.append((k,k+1,k+nx+2,k+nx+1))
add('Woodland_Continuous_Terrain',verts,faces,'LeafDark')
# Reservoir is on a low shelf; shore is an irregular polygon rather than an oval prop.
shore=[]
for i in range(72):
    a=i*math.tau/72;r=1+.035*math.sin(a*5)+.028*math.cos(a*9)
    shore.append((35+185*r*math.cos(a),426+78*r*math.sin(a),5.7))
face('Reservoir_Bank',[(35+(x-35)*1.05,426+(y-426)*1.10,5.65) for x,y,z in shore],'Sand')
face('Reservoir_Water',shore,'Water')
# Tree crowns are branching clustered volumes with mixed species and height.
def tree(x,y,h=8,woodland=False):
    z=hillheight(x,y) if y>=220 else .12
    if woodland and ((x-35)/204)**2+((y-426)/91)**2<1.18:return
    beam('Tree_Trunks',(x,y,z),(x,y,z+h*.65),h*.023,'Bark',7)
    if int(x+y)%4==0:
        # Tiered tapered evergreen profile.
        for k in range(4):
            cz=z+h*(.40+k*.15);r=h*(.28-k*.047)
            vs=[(x,y,cz+h*.36)]+[(x+r*math.cos(a*math.tau/10),y+r*math.sin(a*math.tau/10),cz) for a in range(10)]
            add('Woodland_Pines',vs,[(0,j+1,(j+1)%10+1) for j in range(10)],'LeafDark' if k%2 else 'LeafMid')
    else:
        for j in range(7):
            a=j*2.399
            dx=math.cos(a)*h*.16;dy=math.sin(a)*h*.16;cz=z+h*(.67+random.random()*.18)
            beam('Tree_Branches',(x,y,z+h*.4),(x+dx,y+dy,cz),h*.009,'Bark',5)
            oval('Tree_Cluster_Crowns',(x+dx,y+dy,cz),(h*.21,h*.19,h*.25),random.choice(['LeafDark','LeafMid','LeafSun']),9,5)
# Plaza, street allees and landscaped parking islands.
for x,y,rx,ry in planters:tree(x,y,random.uniform(5,8))
for j in range(42):
    x=-520+j*25
    for y in [-260,-210]:
        if -18<x<18 or abs(x-295)<25 or abs(x+286)<22:continue
        tree(x,y,random.uniform(6,9))
for y in range(-170,206,22):
    for x in [-271,-164,271,320]:tree(x,y,random.uniform(6,9))
for y in range(-171,140,26):
    for x in [-242,-217,-192]:tree(x,y+6,random.uniform(4,6))
for j in range(330):
    x=random.uniform(-640,650);y=random.uniform(237,900)
    tree(x,y,random.uniform(8,15),True)
# Distant city fabric, kept beyond the wooded slopes.
for j in range(45):
    x=random.uniform(-1000,1000);y=random.uniform(980,1300);h=random.uniform(8,38);z=hillheight(x,y)
    box('Distant_Urban_Buildings',(x,y,z+h/2),(random.uniform(9,24),random.uniform(12,26),h),'Ivory')
flush()
# Flat ground surfaces must face up, including concave infield polygons.
for ob in COL.objects:
    if ob.type!='MESH':continue
    if any(k in ob.name for k in ['Field_Clay','Infield_Diamond','Home_Plate']):
        for poly in ob.data.polygons:
            if poly.normal.z<0:poly.flip()
        ob.data.update()
    if any(k in ob.name for k in ['Crowns','Terrain','Reservoir','Planter','Shrub']):
        for poly in ob.data.polygons:poly.use_smooth=True
print('CONTEXT',len(OBJS),'objects;',sum(len(o.data.vertices) for o in COL.objects if o.type=='MESH'),'vertices')



# Keep the shallow surface layers distinct even in aerial depth buffers.
for ob in COL.objects:
    if ob.type!='MESH':continue
    z=None
    if ob.name.startswith('Field_Mowing_Stripes'):z=.24;ob.name='WalkSurface_Field_Mowing_Stripes'
    elif ob.name.startswith('WalkSurface_Field_'):z=.215
    elif ob.name.startswith('Field_Clay'):z=.32
    elif ob.name.startswith('Infield_Diamond'):z=.40
    elif ob.name.startswith('Field_Foul_Turf'):z=.18
    elif ob.name.startswith('Home_Plate'):z=.46
    if z is not None:
        for v in ob.data.vertices:v.co.z=z
        ob.data.update()
# Rich Lions seat blues with darker concrete beneath; white remains on aisles.
mat('BowlConcrete',(.15,.19,.22),.92)
for ob in COL.objects:
    if ob.name.startswith('Grandstand_Treads'):ob.data.materials[0]=MATS['BowlConcrete']
for k,c in [('BlueSeat',(.005,.13,.42)),('AzureSeat',(.008,.25,.48)),('NavySeat',(.003,.065,.22))]:
    m=MATS[k];bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    bs.inputs['Base Color'].default_value=(*c,1)
cam_data.clip_start=1.0
# Thin foul lines sit above turf and clay layers.
for ob in COL.objects:
    if ob.name.startswith('Foul_Lines'):
        for v in ob.data.vertices:v.co.z+=.27
# The wide lens sees beyond the roof into the bowl.
cam.location=(310,-400,320)
cam.rotation_euler=(Vector((0,8,3))-cam.location).to_track_quat('-Z','Y').to_euler()
print('Surface layers and seating contrast corrected')



# Preserve the exact supplied vector paths, and convert SVG shaders for glTF.
from mathutils import Matrix
def mount_svg(path,name,center,width,angle=0):
    before=set(bpy.data.objects)
    bpy.ops.import_curve.svg(filepath=str(path))
    imported=[o for o in bpy.data.objects if o not in before and o.type in {'CURVE','MESH'}]
    for ob in imported:
        for coll in list(ob.users_collection):coll.objects.unlink(ob)
        COL.objects.link(ob)
    bpy.context.view_layer.update()
    corners=[o.matrix_world@Vector(c) for o in imported for c in o.bound_box]
    lo=[min(v[i] for v in corners) for i in range(2)];hi=[max(v[i] for v in corners) for i in range(2)]
    transform=Matrix.Translation(center)@Matrix.Rotation(angle,4,'Z')@Matrix.Rotation(math.pi/2,4,'X')@Matrix.Scale(width/(hi[0]-lo[0]),4)@Matrix.Translation((-(lo[0]+hi[0])/2,-(lo[1]+hi[1])/2,0))
    for o in bpy.data.objects:o.select_set(False)
    for o in imported:o.matrix_world=transform@o.matrix_world;o.select_set(True)
    bpy.context.view_layer.objects.active=imported[0]
    bpy.ops.object.convert(target='MESH')
    meshes=list(bpy.context.selected_objects)
    for o in meshes:
        for material in o.data.materials:
            if not material:continue
            color=tuple(material.diffuse_color)
            material.use_nodes=True;nodes=material.node_tree.nodes
            nodes.clear();bs=nodes.new('ShaderNodeBsdfPrincipled');out=nodes.new('ShaderNodeOutputMaterial')
            bs.inputs['Base Color'].default_value=color;bs.inputs['Roughness'].default_value=.46
            material.node_tree.links.new(bs.outputs['BSDF'],out.inputs['Surface'])
    bpy.context.view_layer.objects.active=meshes[0]
    bpy.ops.object.join();sign=bpy.context.object;sign.name=name
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    mod=sign.modifiers.new('Raised_Letters','SOLIDIFY');mod.thickness=.045
    bpy.ops.object.modifier_apply(modifier=mod.name);OBJS.append(sign)
    return sign
# Main original facade sign on the tall east main gate exterior.
box('Main_Sign_Mounting_Frieze',(150,4,25.5),(4.8,50,8.0),'Ivory')
mount_svg(ROOT/'assets'/'blender'/'facade.svg','Facade_Original_SVG_Main',(152.6,4,25.5),47,math.pi/2)
# A smaller matching outfield sign is mounted onto the low pavilion, beside the open gate.
mount_svg(ROOT/'assets'/'blender'/'facade.svg','Facade_Original_SVG_Gate2',(-42,-132.3,2.8),23,0)
# Original club mark is mounted onto the outward-facing giant scoreboard.
mount_svg(ROOT/'public'/'lions.svg','Scoreboard_Original_Lions_Crest',scorep(0,-1.55,20.5),20,ang)
# A central opening through the low terrace makes the existing walking route continuous.
for ob in list(COL.objects):
    if ob.name.startswith(('Outfield_Seating_Treads','WalkSurface_Outfield_Deck')):
        bpy.data.objects.remove(ob,do_unlink=True)
for side in [7,0,1]:
    ranges=[(0,.41),(.59,1)] if side==0 else [(0,1)]
    for a,b in ranges:
        for row in range(10):
            s=.724+row*.014;z=1.05+row*.37
            panel('Outfield_Seating_Treads',side,a,b,s,s+.014,z,z,.37,'Ivory')
        panel('WalkSurface_Outfield_Deck',side,a,b,.866,1.035,5,5,.3,'Ivory')
import bmesh
for ob in COL.objects:
    if ob.type!='MESH' or not ob.name.startswith(('Seat_Pans','Seat_Backs')):continue
    bm=bmesh.new();bm.from_mesh(ob.data)
    faces=[f for f in bm.faces if all(abs(v.co.x)<11.5 and v.co.y<-91 for v in f.verts)]
    bmesh.ops.delete(bm,geom=faces,context='FACES')
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    bm.to_mesh(ob.data);bm.free()
flush()
# Make plaza pavement read at human scale, with real photographic texture rather than giant stones.
for ob in COL.objects:
    if ob.type!='MESH':continue
    if any(m==MATS['PavingLight'] for m in ob.data.materials):
        uv=ob.data.uv_layers.active
        if uv:
            for loop in ob.data.loops:
                v=ob.data.vertices[loop.vertex_index].co;uv.data[loop.index].uv=(v.x/2.1,v.y/2.1)
    textured=any(m and m.use_nodes and any(n.type=='TEX_IMAGE' for n in m.node_tree.nodes) for m in ob.data.materials)
    if not textured:
        for uv in list(ob.data.uv_layers):ob.data.uv_layers.remove(uv)
print('SVG signs mounted; Gate 2 open; model objects',len(COL.objects))



# Final ground-height details and denser wooded banks match the supplied aerial context.
for ob in COL.objects:
    if ob.type!='MESH':continue
    if ob.name.startswith('Bases'):
        for v in ob.data.vertices:v.co.z+=.24
    elif ob.name.startswith('Mound'):
        for v in ob.data.vertices:v.co.z+=.22
    elif ob.name.startswith(('Pitcher_Rubber','Batters_Box')):
        for v in ob.data.vertices:v.co.z+=.25
for j in range(650):
    x=random.uniform(-405,430);y=random.uniform(241,630)
    # Keep the rear access road and reservoir open.
    if abs(y-205)<20:continue
    tree(x,y,random.uniform(7.5,13.5),True)
# Low bushes merge the forest floor into dense clusters rather than isolated trees.
for j in range(150):
    x=random.uniform(-420,440);y=random.uniform(240,650)
    if ((x-35)/210)**2+((y-426)/94)**2<1.1:continue
    z=hillheight(x,y)
    oval('Woodland_Understory',(x,y,z+.8),(random.uniform(2,4),random.uniform(2,4),1.6),'LeafMid',9,4)
flush()
for ob in COL.objects:
    if ob.type=='MESH' and any(t in ob.name for t in ['Crowns','Understory']):
        for p in ob.data.polygons:p.use_smooth=True
# Set the local terrain below the lake to prevent hidden water faces.
terrain=next(o for o in COL.objects if o.name.startswith('Woodland_Continuous_Terrain'))
for v in terrain.data.vertices:
    r=((v.co.x-35)/190)**2+((v.co.y-426)/83)**2
    if r<1.02:v.co.z=min(v.co.z,5.35)
terrain.data.update()
# The model is authored in meters, with named geometry for the browser walk controller.
SCENE['reference_basis']='Supplied aerial photos + octagonal floor plan; hidden detail interpreted.'
SCENE['version']='octagonal-v2'
SCENE['footprint_sides']=8
SCENE['spawn_blender']=[0,-165,1.7]
for ob in COL.objects:
    if ob.type=='MESH' and not any(m and m.use_nodes and any(n.type=='TEX_IMAGE' for n in m.node_tree.nodes) for m in ob.data.materials):
        for uv in list(ob.data.uv_layers):ob.data.uv_layers.remove(uv)
print('FINAL_MESHES',sum(o.type=='MESH' for o in COL.objects),'vertices',sum(len(o.data.vertices) for o in COL.objects if o.type=='MESH'))



# Continuous paved Gate 2 approach and visible gate fascia.
box('WalkSurface_Gate2_Approach',(0,-159,.11),(21,110,.14),'PavingLight')
for ob in COL.objects:
    if ob.name.startswith('Gate2_Lettering'):ob.location.y=-141.1;ob.location.z=4.55
    elif ob.name.startswith('Gate2_Entry_Fascia'):
        for v in ob.data.vertices:v.co.y-=8.2;v.co.z-=1.2
flush()
# Store exact eight-sided footprint and reconstruction notes beside the exported model.
import json,hashlib
(OUT/'lionspark-scene.json').write_text(json.dumps({
    'version':'octagonal-v2','units':'meters','footprint':P,'footprintSides':8,
    'source':'Supplied aerial photos and clipped-corner octagonal floor plan',
    'modeling':'Blender MCP; unseen detail interpreted; not a survey model',
    'features':['two-tier blue infield seating','low outfield decks','five-sided white canopy','pentagonal scoreboard','original vector facade signs','east annex','plaza','parking','red cycleway','woodland','reservoir','photographic sky']
},ensure_ascii=False,indent=2),encoding='utf-8')
# Collider bounds for each disconnected component, transformed into glTF Y-up coordinates.
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
    for v in mesh.vertices:components.setdefault(find(v.index),[]).append(ob.matrix_world@v.co)
    for points in components.values():
        lo=[min(p[j] for p in points) for j in range(3)];hi=[max(p[j] for p in points) for j in range(3)]
        boxes.append(dict(minX=lo[0],maxX=hi[0],minY=lo[2],maxY=hi[2],minZ=-hi[1],maxZ=-lo[1]))
collision=dict(boxes=boxes,spawn=[0,1.7,165],overview=[310,320,400],units='meters',source='Blender octagonal-v2 connected components')
(OUT/'lionspark-collision.json').write_text(json.dumps(collision,separators=(',',':')),encoding='utf-8')
# Convert Korean text to meshes and export only the active reconstruction scene.
for ob in bpy.data.objects:ob.select_set(False)
for ob in list(COL.objects):
    if ob.type=='FONT':
        ob.select_set(True);bpy.context.view_layer.objects.active=ob
        bpy.ops.object.convert(target='MESH');ob.select_set(False)
for ob in COL.objects:
    if ob.type=='MESH':ob.select_set(True)
import contextlib,io
with contextlib.redirect_stdout(io.StringIO()):
    bpy.ops.export_scene.gltf(filepath=str(OUT/'lionspark.glb'),export_format='GLB',
        use_selection=True,use_active_scene=True,use_visible=False,use_renderable=False,
        export_apply=True,export_yup=True,export_extras=True,export_animations=False,
        export_draco_mesh_compression_enable=True,export_draco_mesh_compression_level=6,
        export_draco_position_quantization=16,export_draco_normal_quantization=10,export_draco_texcoord_quantization=12)
# Restore a useful aerial camera and a saved working Blender copy.
cam.location=(310,-400,320);cam.data.clip_start=1;cam.data.lens=43
cam.rotation_euler=(Vector((0,8,3))-cam.location).to_track_quat('-Z','Y').to_euler()
SCENE.render.filepath=str(ROOT/'.lemonade'/'lionspark-v2-aerial.png')
bpy.ops.file.pack_all()
(ROOT/'.lemonade').mkdir(parents=True,exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'.lemonade'/'lionspark-v2.blend'),compress=True)
print('V2_EXPORTED', (OUT/'lionspark.glb').stat().st_size,'bytes;',len(boxes),'colliders;',len(COL.objects),'objects')
