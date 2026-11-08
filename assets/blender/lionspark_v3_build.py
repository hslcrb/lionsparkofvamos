# Reference-driven v3 edit recipe, run in Blender with this script's __file__.
# Opens preserved v2 and saves a separate v3; model geometry is authored with Blender MCP.
import bpy,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets'/'blender'/'lionspark-v2.blend'))

import bpy,math,random,sys,pathlib,json,shutil,bmesh
from mathutils import Vector,Matrix
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=ROOT/'public'/'models'
SCENE=bpy.context.scene;SCENE.name='Lionspark_Reference_V3'
COL=next(c for c in SCENE.collection.children if 'World' in c.name);COL.name='Lionspark_V3_World'
MATS={}
for ob in COL.objects:
 if ob.type=='MESH':
  for m in ob.data.materials:
   if m:MATS[m.name.split('.')[0]]=m
BATCH={};OBJS=[];random.seed(1982)
P=[(-62,-128),(62,-128),(136,-54),(136,62),(62,136),(-62,136),(-136,62),(-136,-54)]
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

def pp(side,t,s=1,z=0):
 a=P[side%8];b=P[(side+1)%8];return ((a[0]+(b[0]-a[0])*t)*s,(a[1]+(b[1]-a[1])*t)*s,z)
def face(name,points,material):add(name,points,[tuple(range(len(points)))],material)
def panel(name,side,t0,t1,s0,s1,z0,z1,thick,material):
 p=[pp(side,t0,s0,z0),pp(side,t1,s0,z0),pp(side,t1,s1,z1),pp(side,t0,s1,z1)]
 v=p+[(x,y,z-thick) for x,y,z in p]
 add(name,v,[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],material)
def linebox(name,a,b,width,height,material):
 a,b=Vector(a),Vector(b);d=b-a;box(name,(a+b)/2,(d.xy.length,width,height),material,math.atan2(d.y,d.x))
def remove_prefix(prefixes):
 for ob in list(COL.objects):
  if ob.name.startswith(tuple(prefixes)):bpy.data.objects.remove(ob,do_unlink=True)
def emission_mat(name,color,strength=1):
 key=mat(name,color,.5)
 bs=next(n for n in MATS[key].node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 bs.inputs['Emission Color'].default_value=(*color,1);bs.inputs['Emission Strength'].default_value=strength
 return key
# Reference photographs are kept in the references folder as aerial-v3.png and night-facade-v3.png.
refs=ROOT/'assets'/'blender'/'references'
print('V3 reference working scene ready',len(COL.objects))

MATS['PavingLight']=next(o.data.materials[0] for o in COL.objects if o.type=='MESH' and o.name.startswith('WalkSurface_Entrance_Plaza'))



# SVG paths are composited once in painter order. One image plane replaces coplanar overlapping letters.
TEX=ROOT/'assets'/'blender'/'textures'
def bake_svg(path,label,width=4096):
 saved=bpy.context.window.scene
 bake=bpy.data.scenes.new('Bake_'+label);bpy.context.window.scene=bake
 before=set(bpy.data.objects);bpy.ops.import_curve.svg(filepath=str(path))
 objs=[o for o in bpy.data.objects if o not in before and o.type=='CURVE']
 bpy.context.view_layer.update()
 bounds=[o.matrix_world@Vector(c) for o in objs for c in o.bound_box]
 lo=Vector((min(p.x for p in bounds),min(p.y for p in bounds),0));hi=Vector((max(p.x for p in bounds),max(p.y for p in bounds),0))
 w=hi.x-lo.x;h=hi.y-lo.y
 for i,o in enumerate(objs):
  o.location.z+=i*max(w*1e-5,1e-7)
  for m in o.data.materials:
   if not m:continue
   col=tuple(m.diffuse_color);m.use_nodes=True;ns=m.node_tree.nodes;ns.clear()
   em=ns.new('ShaderNodeEmission');em.inputs['Color'].default_value=col
   out=ns.new('ShaderNodeOutputMaterial');m.node_tree.links.new(em.outputs['Emission'],out.inputs['Surface'])
 camd=bpy.data.cameras.new('Logo_Orthographic');camera=bpy.data.objects.new('Logo_Orthographic',camd);bake.collection.objects.link(camera)
 camd.type='ORTHO';camd.ortho_scale=w*1.025
 camera.location=((lo.x+hi.x)/2,(lo.y+hi.y)/2,max(w,1))
 bake.camera=camera;bake.render.engine=SCENE.render.engine
 transforms=[i.identifier for i in bake.view_settings.bl_rna.properties['view_transform'].enum_items]
 if 'Standard' in transforms:bake.view_settings.view_transform='Standard'
 bake.render.film_transparent=True;bake.render.resolution_x=width
 bake.render.resolution_y=round(width*h/w);bake.render.resolution_percentage=100
 bake.render.image_settings.file_format='PNG';bake.render.image_settings.color_mode='RGBA';bake.render.image_settings.color_depth='8'
 bake.render.filepath=str(TEX/(label+'.png'));bake.render.use_file_extension=True
 bpy.ops.render.render(write_still=True,scene=bake.name)
 image=bpy.data.images.load(bake.render.filepath,check_existing=True);image.pack()
 bpy.context.window.scene=saved
 for o in list(bake.objects):bpy.data.objects.remove(o,do_unlink=True)
 bpy.data.scenes.remove(bake)
 return image,w/h
facade_image,facade_aspect=bake_svg(ROOT/'assets'/'blender'/'facade.svg','facade-logo-v3')
club_image,club_aspect=bake_svg(ROOT/'public'/'lions.svg','lions-crest-v3',2048)
def logo_plane(name,image,aspect,center,width,angle=0,luminous=False):
 mesh=bpy.data.meshes.new(name);h=width/aspect;hw=width/2;hh=h/2
 mesh.from_pydata([(-hw,-hh,0),(hw,-hh,0),(hw,hh,0),(-hw,hh,0)],[],[(0,1,2,3)]);mesh.update()
 uv=mesh.uv_layers.new()
 for li,xy in enumerate([(0,0),(1,0),(1,1),(0,1)]):uv.data[li].uv=xy
 ob=bpy.data.objects.new(name,mesh);COL.objects.link(ob)
 ob.matrix_world=Matrix.Translation(center)@Matrix.Rotation(angle,4,'Z')@Matrix.Rotation(math.pi/2,4,'X')
 m=bpy.data.materials.new(name+'_Stable_Image');m.use_nodes=True
 bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image;tex.extension='CLIP'
 m.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
 m.node_tree.links.new(tex.outputs['Alpha'],bs.inputs['Alpha'])
 m.node_tree.links.new(tex.outputs['Color'],bs.inputs['Emission Color'])
 bs.inputs['Emission Strength'].default_value=.12 if luminous else 0
 bs.inputs['Roughness'].default_value=.7
 # glTF alpha mask keeps transparent borders from covering geometry behind them.
 m.alpha_threshold=.35
 methods=[i.identifier for i in m.bl_rna.properties['surface_render_method'].enum_items]
 if 'DITHERED' in methods:m.surface_render_method='DITHERED'
 m.use_backface_culling=True;mesh.materials.append(m)
 ob['stable_logo']=True;ob['luminous_logo']=luminous
 return ob
# Remove all stacked vector faces and excessive protruding sign blocks.
remove_prefix(['Facade_Original_SVG','Scoreboard_Original_Lions_Crest','Main_Sign_Mounting_Frieze'])
logo_plane('Facade_Original_SVG_Gate2_Stable',facade_image,facade_aspect,(-42,-132.55,2.8),23)
sc=Vector((-87,-88,0));a=-math.pi/4
center=(sc.x+1.65*math.sin(a),sc.y-1.65*math.cos(a),20.5)
logo_plane('Scoreboard_Original_Lions_Crest_Stable',club_image,club_aspect,center,20,a,True)
print('STABLE_LOGOS',facade_image.size[:],club_image.size[:],facade_aspect,club_aspect)



# Photo reference: open angular portal facade, not a continuous stack of glass ribbons.
remove_prefix(['Cantilever_White_Facade','Exterior_Window_Ribbon','Exterior_Slender_Columns','Window_Mullions','Gallery_Projecting_Ledges','External_Steel_Braces'])
mat('Facade_Charcoal_Concrete',(.235,.255,.25),.91,texture=True)
emission_mat('Night_Blue_Architecture',(.004,.16,.80),1)
emission_mat('Night_White_Fittings',(.82,.90,1),1)
nightLights=[]
def vwall(name,side,t0,t1,s,z0,z1,material,thick=.48):
 p=[pp(side,t0,s,z0),pp(side,t1,s,z0),pp(side,t1,s,z1),pp(side,t0,s,z1)]
 # solid wall panel thickness extends toward the bowl
 q=[(x*(s-thick/140)/s,y*(s-thick/140)/s,z) for x,y,z in p]
 add(name,p+q,[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],material)
for side in range(2,7):
 # Heavy top fascia carries the original park identity at the photographed roofline.
 vwall('Exterior_Roof_Fascia',side,0,1,1.13,27.6,34.6,'Facade_Charcoal_Concrete',1.5)
 vwall('Exterior_Portal_Sill',side,0,1,1.045,8,11.3,'Facade_Charcoal_Concrete',1.4)
 # Three large trapezoidal openings per facet.
 for j in range(4):
  t=j/3;half=.045 if j in [0,3] else .035
  p=[pp(side,max(0,t-half),1.045,11.2),pp(side,min(1,t+half),1.045,11.2),
     pp(side,min(1,t+half*.7),1.13,27.7),pp(side,max(0,t-half*.7),1.13,27.7)]
  q=[(x*.994,y*.994,z) for x,y,z in p]
  add('Exterior_Angular_Portal_Piers',p+q,[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],'Facade_Charcoal_Concrete')
 for j in range(3):
  t=(j+.5)/3
  # Ceiling and truss strips sit behind the genuine open portals.
  vwall('Night_Facade_Glow',side,t-.12,t+.12,1.018,23.8,27.0,'Night_Blue_Architecture',.15)
  for k in range(4):
   tt=t-.115+k*.077
   beam('Exterior_Portal_Ribs',pp(side,tt,.99,16),pp(side,tt,1.092,29),.12,'Ivory')
   beam('Night_Facade_Glow_Ribs',pp(side,tt,1.001,20),pp(side,tt,1.10,28.1),.065,'Night_Blue_Architecture')
 # Add believable lower concourse windows and scale-defining columns.
 vwall('Lower_Concourse_Window',side,0,1,1.015,5.1,7.0,'Glass',.10)
 for j in range(19):
  t=j/18
  beam('Lower_Concourse_Columns',pp(side,t,1.02,.1),pp(side,t,1.035,8.2),.15,'Ivory')
 # Logo placement on the upper band, including the two diagonal facets seen in photo two.
 if side in [2,3,5,6]:
  a,b=Vector(pp(side,0)),Vector(pp(side,1));d=(b-a).normalized();normal=Vector((d.y,-d.x,0))
  c=Vector(pp(side,.53,1.13,31.2))+normal*.20
  logo_plane('Facade_Luminous_Logo_'+str(side),facade_image,facade_aspect,c,26,math.atan2(d.y,d.x),True)
 for t in [.22,.78]:
  c=pp(side,t,1.17,21)
  if side in [2,3,5,6]:nightLights.append(dict(kind='facade',position=[c[0],c[2],-c[1]],target=[c[0]*.86,24,-c[1]*.86]))
# Fill the overly wide earlier outfield opening; keep a real pedestrian portal six meters wide.
remove_prefix(['Outfield_Seating_Treads','WalkSurface_Outfield_Deck'])
def seat(p,angle,material):
 x,y,z=p;box('Seat_Pans',(x,y,z+.23),(.46,.43,.10),material,angle)
 box('Seat_Backs',(x-math.sin(angle)*.19,y+math.cos(angle)*.19,z+.49),(.46,.08,.43),material,angle)
for side in [7,0,1]:
 ranges=[(0,.475),(.525,1)] if side==0 else [(0,1)]
 for a,b in ranges:
  for row in range(10):
   s=.724+row*.014;z=1.05+row*.37
   panel('Outfield_Seating_Treads',side,a,b,s,s+.014,z,z,.37,'Ivory')
  panel('WalkSurface_Outfield_Deck',side,a,b,.866,1.035,5,5,.3,'Ivory')
# Seats in the restored strips avoid duplicating the surviving v2 seats.
for row in range(10):
 s=.724+row*.014;z=1.05+row*.37
 for a,b in [(.41,.475),(.525,.59)]:
  count=max(1,int((b-a)*124*s/.63))
  for j in range(count):seat(pp(0,a+(b-a)*(j+.5)/count,s+.007,z+.02),math.pi,'AzureSeat')
for a,b in [(.37,.465),(.535,.63)]:
 panel('Blocker_Outfield_Pavilion_Fill',0,a,b,.91,1.03,4.7,4.7,4.7,'Ivory')
# Floodlight fittings and road lamp glass are named for the live night lighting controller.
for ob in COL.objects:
 if ob.name.startswith(('Floodlight_Reflectors','Street_Lamp_Head')):
  ob.name=('Night_Floodlight_Fittings' if ob.name.startswith('Floodlight') else 'Night_Road_Lamps')+'_'+ob.name
  ob.data.materials[0]=MATS['Night_White_Fittings']
for x,y,z in [(-113,-33,46),(113,-33,46),(-85,130,49),(85,130,49)]:
 nightLights.append(dict(kind='flood',position=[x,z,-y],target=[0,0,10]))
for x,y in [(-130,-235),(0,-235),(130,-235),(-255,-170),(275,-170),(295,-50),(295,100),(-286,100)]:
 nightLights.append(dict(kind='road',position=[x,7,-y],target=[x,0,-y]))
flush()
print('REFERENCE_FACADE',len(COL.objects),'objects; upper band logos and genuine portal openings')



# Crossroads are split into clear approach segments so paint never continues through the junction.
remove_prefix(['WalkSurface_Road_','WalkSurface_Red_Cycleway','WalkSurface_Road_Sidewalk','Road_Edge_Line','Road_Centre_Lines','Road_Lane_Dashes','Crosswalk','Signal_Housing'])
def road_segment(a,b,width=28):
 av,bv=Vector(a),Vector(b);d=bv-av;length=d.length;u=d.normalized();n=Vector((-u.y,u.x))
 linebox('WalkSurface_Road',(*a,.045),(*b,.045),width,.09,'Asphalt')
 for sign in [-1,1]:
  v=n*sign*(width/2+3.0)
  linebox('WalkSurface_Red_Cycleway',(*(av+v),.075),(*(bv+v),.075),4.0,.10,'RedPath')
  v=n*sign*(width/2+7.0)
  linebox('WalkSurface_Road_Sidewalk',(*(av+v),.13),(*(bv+v),.13),3.6,.12,'PavingLight')
  v=n*sign*(width/2+.1)
  linebox('Road_Edge_Line',(*(av+v),.105),(*(bv+v),.105),.13,.015,'WhitePaint')
  v=n*sign*.21
  linebox('Road_Centre_Lines',(*(av+v),.108),(*(bv+v),.108),.12,.016,'YellowPaint')
 for j in range(int(length/10)):
  p=av+u*(j*10+2)
  if j*10+6>length:continue
  for offset in [-8,-4,4,8]:
   if abs(offset)<width/2-1:
    v=n*offset;linebox('Road_Lane_Dashes',(*(p+v),.108),(*(p+v+u*4.5),.108),.13,.016,'WhitePaint')
for a,b in [((-700,-235),(-300,-235)),((-272,-235),(281,-235)),((309,-235),(700,-235))]:road_segment(a,b,28)
for x,w in [(295,28),(-286,22)]:
 for y0,y1 in [(-700,-249),(-221,197.5),(212.5,700)]:road_segment((x,y0),(x,y1),w)
for a,b in [((-700,205),(-297,205)),((-275,205),(281,205)),((309,205),(700,205))]:road_segment(a,b,15)
def arrow(x,y,angle):
 shape=[(-.17,-2.1),(.17,-2.1),(.17,.8),(.72,.25),(0,2.1),(-.72,.25),(-.17,.8)]
 c,s=math.cos(angle),math.sin(angle)
 face('Road_Directional_Arrows',[(x+vx*c-vy*s,y+vx*s+vy*c,.126) for vx,vy in shape],'WhitePaint')
for cx,cy,wx,wy in [(-286,-235,22,28),(295,-235,28,28),(-286,205,22,15),(295,205,28,15)]:
 box('WalkSurface_Intersection',(cx,cy,.045),(wx,wy,.09),'Asphalt')
 # Each crosswalk lies outside the clean asphalt junction, with a stop line behind it.
 for sign in [-1,1]:
  x=cx+sign*(wx/2+8)
  for j in range(int(wy/3)):
   box('Zebra_Crosswalks',(x,cy-wy/2+1.8+j*3,.124),(4.0,1.3,.025),'WhitePaint')
  y=cy+sign*(wy/2+8)
  for j in range(int(wx/3)):
   box('Zebra_Crosswalks',(cx-wx/2+1.8+j*3,y,.124),(1.3,4.0,.025),'WhitePaint')
  # Stop bars span incoming lanes only, avoiding doubled white crosses.
  box('Junction_Stop_Lines',(cx+sign*(wx/2+13),cy+sign*wy/4,.128),(.4,wy/2-.8,.026),'WhitePaint')
  box('Junction_Stop_Lines',(cx-sign*wx/4,cy+sign*(wy/2+13),.128),(wx/2-.8,.4,.026),'WhitePaint')
  arrow(cx+sign*(wx/2+34),cy+sign*wy/4,sign*math.pi/2)
  arrow(cx-sign*wx/4,cy+sign*(wy/2+34),math.pi if sign>0 else 0)
 # Recessed corner drain grilles read at walking distance.
 for dx,dy in [(-1,-1),(-1,1),(1,-1),(1,1)]:
  x=cx+dx*(wx/2+1);y=cy+dy*(wy/2+1)
  box('Curb_Drain_Grilles',(x,y,.11),(1.3,.65,.06),'DarkMetal')
  for k in range(7):box('Drain_Slots',(x-.5+k*.16,y,.146),(.07,.57,.02),'Steel')
# Lane paint is raised slightly from asphalt and uses a matte, non-emissive finish.
bs=next(n for n in MATS['WhitePaint'].node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Roughness'].default_value=.86
flush()
# Photographic concrete and small-scale asphalt/grass textures use world-space UV scale.
for ob in COL.objects:
 if ob.type!='MESH':continue
 uv=ob.data.uv_layers.active
 if not uv:continue
 if 'Asphalt' in ob.name or 'Road' in ob.name:
  for loop in ob.data.loops:
   p=ob.data.vertices[loop.vertex_index].co;uv.data[loop.index].uv=(p.x/4,p.y/4)
 if 'Woodland_Continuous_Terrain' in ob.name:ob.name='WalkSurface_Woodland_Hills'
print('ROAD_JUNCTIONS complete; paint clipped at all four junctions')



# A modeled compact sedan, with local coordinates; the browser only moves this Blender object.
car_root=bpy.data.objects.new('Driveable_Car',None);COL.objects.link(car_root)
car_root.location=(-130,-235,.1);car_root.rotation_euler.z=-math.pi/2
car_root['driveable']=True
mat('Car_Lions_Metallic',(.008,.115,.32),.24,.72)
mat('Car_Interior',(.025,.030,.035),.93)
def car_mesh(name,verts,faces,material,bevel=0):
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
 ob=bpy.data.objects.new(name,mesh);COL.objects.link(ob);ob.parent=car_root;mesh.materials.append(MATS[material])
 if bevel:
  for o in bpy.data.objects:o.select_set(False)
  ob.select_set(True);bpy.context.view_layer.objects.active=ob
  mod=ob.modifiers.new('Soft_body_edges','BEVEL');mod.width=bevel;mod.segments=3
  bpy.ops.object.modifier_apply(modifier=mod.name)
 return ob
def car_box(name,center,size,material,bevel=0):
 x,y,z=center;a,b,c=[n/2 for n in size]
 verts=[(x-a,y-b,z-c),(x+a,y-b,z-c),(x+a,y+b,z-c),(x-a,y+b,z-c),(x-a,y-b,z+c),(x+a,y-b,z+c),(x+a,y+b,z+c),(x-a,y+b,z+c)]
 return car_mesh(name,verts,[(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],material,bevel)
sects=[(-2.25,.70,.38,.67),(-1.95,.88,.33,.82),(-1.0,.93,.32,.90),(.9,.93,.32,.90),(1.98,.85,.37,.77),(2.25,.68,.42,.65)]
verts=[]
for y,w,lo,hi in sects:verts.extend([(-w,y,lo),(w,y,lo),(w,y,hi),(-w,y,hi)])
faces=[(3,2,1,0),(20,21,22,23)]
for j in range(len(sects)-1):
 for k in range(4):faces.append((j*4+k,j*4+(k+1)%4,(j+1)*4+(k+1)%4,(j+1)*4+k))
car_mesh('Car_Painted_Body',verts,faces,'Car_Lions_Metallic',.065)
cab=[(-.78,-1.1,.88),(.78,-1.1,.88),(.78,.94,.88),(-.78,.94,.88),(-.61,-.70,1.43),(.61,-.70,1.43),(.61,.28,1.43),(-.61,.28,1.43)]
car_mesh('Car_Glass_Cabin',cab,[(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],'Glass',.025)
car_box('Car_Painted_Roof',(0,-.2,1.44),(1.27,1.04,.07),'Car_Lions_Metallic',.04)
for side in [-1,1]:
 car_box('Car_B_Pillars',(side*.755,-.20,1.10),(.065,.10,.50),'DarkMetal',.02)
 car_box('Car_Door_Handles',(side*.948,-.25,.86),(.035,.20,.06),'Steel',.015)
 car_box('Car_Door_Handles',(side*.948,-.88,.86),(.035,.18,.06),'Steel',.015)
 car_box('Car_Side_Mirrors',(side*1.005,.64,1.00),(.23,.20,.15),'Car_Lions_Metallic',.035)
 car_box('Car_Headlamp_Housing',(side*.52,2.12,.69),(.45,.12,.13),'DarkMetal',.04)
 car_box('Night_Road_Lamps_Car_Headlamps',(side*.52,2.19,.70),(.40,.05,.09),'Night_White_Fittings',.035)
 car_box('Car_Taillamps',(side*.52,-2.17,.69),(.42,.06,.10),'RedPath',.025)
car_box('Car_Front_Grille',(0,2.21,.52),(.77,.045,.17),'DarkMetal',.03)
for j in range(6):car_box('Car_Grille_Slats',(-.32+j*.128,2.24,.52),(.03,.025,.12),'Steel')
car_box('Car_Front_Plate',(0,2.265,.43),(.42,.018,.10),'WhitePaint',.01)
car_box('Car_Rear_Plate',(0,-2.265,.48),(.42,.018,.10),'WhitePaint',.01)
for side in [-1,1]:
 for y in [-1.40,1.40]:
  # Tires and alloy hubs rotate about the physical axle.
  for name,r,depth,material in [('Tire',.34,.22,'Tire'),('Alloy',.22,.235,'Steel')]:
   vs=[]
   for x in [side*.91-depth/2,side*.91+depth/2]:
    for j in range(20):
     a=j*math.tau/20;vs.append((x,y+r*math.sin(a),.36+r*math.cos(a)))
   fs=[tuple(reversed(range(20))),tuple(range(20,40))]+[(j,(j+1)%20,(j+1)%20+20,j+20) for j in range(20)]
   ob=car_mesh('Car_Wheel_'+name,vs,fs,material)
   for p in ob.data.polygons:p.use_smooth=True
# Fine paint texture is assigned to asphalt; original photographed paving is retained.
SCENE['version']='reference-v3';SCENE['clock_timezone']='Asia/Seoul'
print('DRIVEABLE_CAR',len(car_root.children),'modeled parts at',tuple(car_root.location))



# Upper fascia uses the white lettering treatment visible in the supplied night photo.
import numpy as np
w,h=facade_image.size;pixels=np.empty(w*h*4,dtype=np.float32);facade_image.pixels.foreach_get(pixels)
pixels=pixels.reshape((h,w,4));pixels[:,:int(w*.395),:3]=1;pixels[:,int(w*.70):,:3]=1
facade_luminous=bpy.data.images.new('Facade_White_Lettering_V3',width=w,height=h,alpha=True)
facade_luminous.pixels.foreach_set(pixels.ravel());facade_luminous.filepath_raw=str(TEX/'facade-luminous-v3.png');facade_luminous.file_format='PNG';facade_luminous.save();facade_luminous.pack()
for ob in COL.objects:
 if ob.name.startswith('Facade_Luminous_Logo'):
  for m in ob.data.materials:
   for n in m.node_tree.nodes:
    if n.type=='TEX_IMAGE':n.image=facade_luminous
for side in range(2,7):
 for j in range(3):
  t=(j+.5)/3
  panel('Night_Facade_Glow_Soffits',side,t-.122,t+.122,1.035,1.114,18.5,26.9,.12,'Night_Blue_Architecture')
flush()
# Roughness and world-scale material frequencies avoid stretched default-looking surfaces.
for ob in COL.objects:
 if ob.type!='MESH':continue
 if ob.name.startswith('Exterior_'):
  for p in ob.data.polygons:p.use_smooth=False
 # Skip logos: their image UVs must remain exactly 0..1.
 if ob.get('stable_logo'):continue
 if ob.data.uv_layers.active and any(m==MATS['PavingLight'] for m in ob.data.materials):
  uv=ob.data.uv_layers.active
  for loop in ob.data.loops:
   p=ob.data.vertices[loop.vertex_index].co;uv.data[loop.index].uv=(p.x/2.1,p.y/2.1)
print('White roofline identity and recessed blue architectural soffits complete')



# Entrance plaza luminaires provide the visible warm ground lighting in the night reference.
for x in [-12,12]:
 beam('Plaza_Lamp_Poles',(x,-176,.1),(x,-176,6.5),.085,'Steel')
 box('Plaza_Lamp_Cap',(x,-176,6.65),(1.25,.7,.16),'DarkMetal')
 box('Night_Road_Lamps_Plaza',(x,-176,6.52),(1.05,.52,.075),'Night_White_Fittings')
nightLights[:0]=[dict(kind='road',position=[x,6.4,176],target=[x,0,176]) for x in [-12,12]]
flush()
print('Plaza fixtures and nearby night anchors',len(nightLights))



# Soft contact shadow travels with the modeled car without redrawing the entire stadium shadow map.
shadow=bpy.data.images.new('Car_Contact_Shadow_Texture',width=128,height=256,alpha=True)
p=[]
for y in range(256):
 for x in range(128):
  r=((x-63.5)/64)**2+((y-127.5)/128)**2
  p.extend([0,0,0,.24*max(0,1-r)**1.6])
shadow.pixels.foreach_set(p);shadow.pack()
mat_shadow=bpy.data.materials.new('Car_Contact_Shadow_Material');mat_shadow.use_nodes=True
ns=mat_shadow.node_tree.nodes;ns.clear();out=ns.new('ShaderNodeOutputMaterial');bs=ns.new('ShaderNodeBsdfPrincipled');tx=ns.new('ShaderNodeTexImage');tx.image=shadow
bs.inputs['Base Color'].default_value=(0,0,0,1);bs.inputs['Roughness'].default_value=1
mat_shadow.node_tree.links.new(tx.outputs['Alpha'],bs.inputs['Alpha']);mat_shadow.node_tree.links.new(bs.outputs['BSDF'],out.inputs['Surface'])
MATS['Car_Contact_Shadow_Material']=mat_shadow
ob=car_mesh('Car_Contact_Shadow',[(-1.15,-2.45,.025),(1.15,-2.45,.025),(1.15,2.45,.025),(-1.15,2.45,.025)],[(0,1,2,3)],'Car_Contact_Shadow_Material')
uv=ob.data.uv_layers.new()
for li,xy in enumerate([(0,0),(1,0),(1,1),(0,1)]):uv.data[li].uv=xy
# Golden lion and orb at the side-gate plaza, as visible in the supplied night reference.
mat('Sculpture_Gold',(.62,.36,.065),.23,.85)
mat('Polished_Gold',(.78,.48,.08),.12,.96)
# Replace the invented fan-shaped ornament with reference-based gold statuary.
remove_prefix(['Blue_Plaza_Sculpture'])
# The original small circular forecourt plinth remains; the statue belongs to the side-gate approach.
sculpt_origin=Vector((-174,8,0));sculpt_angle=-math.pi/2
def sp(x,y,z):
 return (sculpt_origin.x+x*math.cos(sculpt_angle)-y*math.sin(sculpt_angle),sculpt_origin.y+x*math.sin(sculpt_angle)+y*math.cos(sculpt_angle),z)
box('Blocker_Statue_Plinth',sp(0,0,.35),(4.6,4.8,.7),'LightStone',sculpt_angle)
oval('Golden_Lion_Torso',sp(0,.35,2.2),(.68,1.35,.83),'Sculpture_Gold',16,10)
oval('Golden_Lion_Head',sp(0,-.88,3.25),(.63,.65,.69),'Sculpture_Gold',16,10)
oval('Golden_Lion_Muzzle',sp(0,-1.40,3.12),(.43,.33,.30),'Sculpture_Gold',14,8)
for x in [-.43,.43]:
 oval('Golden_Lion_Ears',sp(x,-.75,3.81),(.20,.17,.22),'Sculpture_Gold',12,8)
for x,y in [(-.46,1.08),(.46,1.08),(-.48,-.45),(.48,-.45)]:
 beam('Golden_Lion_Legs',sp(x,y,.72),sp(x,y,2.1),.17,'Sculpture_Gold',10)
 oval('Golden_Lion_Paws',sp(x,y-.12,.82),(.25,.40,.16),'Sculpture_Gold',12,6)
# Mane locks are faceted bronze-gold strands rather than an invented crest/logo.
for j in range(28):
 a=j*math.tau/28
 start=sp(.60*math.cos(a),-.63+.15*math.sin(a),3.20+.66*math.sin(a))
 end=sp(.90*math.cos(a),-.10+.25*math.sin(a),2.95+.91*math.sin(a))
 beam('Golden_Lion_Mane',start,end,.12,'Sculpture_Gold',5)
oval('Polished_Golden_Orb',sp(.95,-1.32,1.55),(.72,.72,.72),'Polished_Gold',32,20)
beam('Golden_Lion_Forearm',sp(.48,-.48,2.0),sp(.88,-1.25,2.18),.18,'Sculpture_Gold',10)
for j in range(12):
 a=j/11*math.pi
 if j:beam('Golden_Lion_Tail',prev,sp(.6+.45*math.sin(a),1.35+.8*math.sin(a/2),2.3+.6*math.cos(a)),.08,'Sculpture_Gold')
 prev=sp(.6+.45*math.sin(a),1.35+.8*math.sin(a/2),2.3+.6*math.cos(a))
flush()
print('Car contact shadow and reference side-gate gold sculpture modeled')



# All physical loose components receive conservative oriented collision footprints.
# The moving sedan is excluded from this static index; runtime handles its dynamic body separately.
for ob in COL.objects:
 if ob.type=='MESH' and ob.name.startswith(('Field_Clay','Infield_Diamond','Mound')):
  ob.name='WalkSurface_'+ob.name
def physical(ob):
 if ob.type!='MESH' or ob.get('stable_logo'):return False
 p=ob
 while p:
  if p==car_root:return False
  p=p.parent
 skip=['WalkSurface','Sky','Night_','Field_','Foul_Lines','Home_Plate','Batters_Box','Infield_','Road_','Zebra_','Junction_','Parking_Stall','Plaza_Paving_Inlays','Drain_Slots','Signal_Housing']
 return not ob.name.startswith(tuple(skip))
def object_solids(ob):
 mesh=ob.data;n=len(mesh.vertices)
 if n==0:return []
 parent=list(range(n))
 def find(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 for e in mesh.edges:
  a,b=e.vertices;ra,rb=find(a),find(b)
  if ra!=rb:parent[rb]=ra
 groups={}
 for v in mesh.vertices:groups.setdefault(find(v.index),[]).append(ob.matrix_world@v.co)
 solids=[]
 for pts in groups.values():
  if len(pts)<3:continue
  p=np.array([(v.x,-v.y,v.z) for v in pts],dtype=np.float64)
  xy=p[:,:2];zlo=float(p[:,2].min());zhi=float(p[:,2].max())
  # Flush pavement seams, paint and drains are part of the ground, not invisible obstacles.
  if zhi-zlo<.09 and zhi<.36:continue
  center=xy.mean(axis=0);q=xy-center
  xx=float((q[:,0]*q[:,0]).mean());zz=float((q[:,1]*q[:,1]).mean());xz=float((q[:,0]*q[:,1]).mean())
  angle=.5*math.atan2(2*xz,xx-zz);c=math.cos(angle);s=math.sin(angle)
  ax=q[:,0]*c+q[:,1]*s;az=-q[:,0]*s+q[:,1]*c
  lo0=float(ax.min());hi0=float(ax.max());lo1=float(az.min());hi1=float(az.max())
  u=(lo0+hi0)/2;v=(lo1+hi1)/2
  solids.append(dict(cx=round(float(center[0]+u*c-v*s),5),cz=round(float(center[1]+u*s+v*c),5),
    hx=round(max(.015,(hi0-lo0)/2),5),hz=round(max(.015,(hi1-lo1)/2),5),yaw=round(angle,7),
    minY=round(zlo,5),maxY=round(zhi,5)))
 return solids
STATIC=[]
for ob in list(COL.objects):
 if physical(ob):STATIC.extend(object_solids(ob))
metadata=dict(boxes=[],solids=STATIC,spawn=[0,1.7,165],overview=[310,320,400],
 vehicleSpawn=[-130,.1,235,-math.pi/2],nightLights=nightLights,units='meters',version='reference-v3',
 source='Blender loose-component oriented conservative bounds; excludes ground, paint and moving car')
(OUT/'lionspark-collision.json').write_text(json.dumps(metadata,separators=(',',':')),encoding='utf-8')
# Export stable image logos, all Blender geometry, and the parented driveable sedan.
for ob in bpy.data.objects:ob.select_set(False)
for ob in COL.objects:ob.select_set(ob.type in {'MESH','EMPTY'})
import contextlib,io
with contextlib.redirect_stdout(io.StringIO()):
 bpy.ops.export_scene.gltf(filepath=str(OUT/'lionspark.glb'),export_format='GLB',
 use_selection=True,use_active_scene=True,use_visible=False,use_renderable=False,
 export_apply=True,export_yup=True,export_extras=True,export_animations=False,
 export_draco_mesh_compression_enable=True,export_draco_mesh_compression_level=6,
 export_draco_position_quantization=16,export_draco_normal_quantization=10,export_draco_texcoord_quantization=12)
(OUT/'lionspark-scene.json').write_text(json.dumps(dict(version='reference-v3',footprintSides=8,footprint=P,
 clock='Asia/Seoul live epoch time',solidCount=len(STATIC),vehicle='Driveable_Car',logo='SVG composited to single 4K image surfaces; roofline white-letter variant',
 features=['open portal facade','roofline original identity','night blue architectural light','stadium floodlights','crossroads with clean markings','running','driving','individual object collision'],
 source='Supplied aerial and night facade references; hidden detail remains interpreted'),ensure_ascii=False,indent=2),encoding='utf-8')
print('WEB_EXPORT', (OUT/'lionspark.glb').stat().st_size,'bytes;',len(STATIC),'static oriented solids;',len(nightLights),'light anchors')



# Keep only the editable v3 scene in this copy; v1 and v2 files remain untouched in Git.
for other in list(bpy.data.scenes):
 if other!=SCENE:bpy.data.scenes.remove(other)
used=set(SCENE.objects)
for ob in list(bpy.data.objects):
 if ob not in used:bpy.data.objects.remove(ob,do_unlink=True)
bpy.data.orphans_purge(do_recursive=True)
cam=SCENE.camera;cam.location=(310,-400,320);cam.data.clip_start=1;cam.data.lens=43
cam.rotation_euler=(Vector((0,8,3))-cam.location).to_track_quat('-Z','Y').to_euler()
SCENE.render.filepath=str(ROOT/'.lemonade'/'lionspark-v3-aerial.png')
(ROOT/'.lemonade').mkdir(parents=True,exist_ok=True)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'.lemonade'/'lionspark-v3.blend'),compress=True)
target=ROOT/'assets'/'blender'/'lionspark-v3.blend';shutil.copy2(bpy.data.filepath,target)
import hashlib
manifest=dict(version='reference-v3',blend=target.name,blendBytes=target.stat().st_size,
 blendSha256=hashlib.sha256(target.read_bytes()).hexdigest(),glbBytes=(OUT/'lionspark.glb').stat().st_size,
 glbSha256=hashlib.sha256((OUT/'lionspark.glb').read_bytes()).hexdigest(),
 colliderCount=len(STATIC),preservedV2='lionspark-v2.blend',clock='Asia/Seoul real time')
(ROOT/'assets'/'blender'/'v3-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('V3_SAVED',manifest)
