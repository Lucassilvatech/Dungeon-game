"""Reproducible original pixel-art atlas compiler. Pillow only; no runtime dependency.
Generated source paintings are preserved; nearest sampling, palette reduction and
hand-authored directional sprite/tile programs produce the shipping PNG assets.
Run: .venv/bin/python scripts/build_pixel_assets.py
"""
from pathlib import Path
import hashlib
import json
import math
import random
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1] / 'frontend/public/assets/pixel'
ROOT.mkdir(parents=True, exist_ok=True)
manifest = {}

def save(name, image, frames):
    image.save(ROOT / (name + '.png'), optimize=True)
    manifest[name] = {'file':name+'.png','frames':frames,'width':image.width,'height':image.height,'sha256':hashlib.sha256((ROOT/(name+'.png')).read_bytes()).hexdigest()}

def source_atlas(filename, names, sizes, cols):
    source=Image.open(ROOT.parents[3]/'art/pixel/source'/filename).convert('RGBA')
    rows=math.ceil(len(names)/cols)
    atlas=Image.new('RGBA',(cols*128,rows*128))
    for i,name in enumerate(names):
        x,y=i%cols,i//cols
        crop=source.crop((round(x*source.width/cols),round(y*source.height/rows),round((x+1)*source.width/cols),round((y+1)*source.height/rows)))
        alpha=crop.getchannel('A').point(lambda v:255 if v>=112 else 0)
        crop.putalpha(alpha)
        box=alpha.getbbox()
        assert box, name
        crop=crop.crop(box)
        if name.startswith("house_"):crop=crop.resize(sizes[i],Image.Resampling.NEAREST)
        else:crop.thumbnail(sizes[i],Image.Resampling.NEAREST)
        # Keep hard alpha and a coherent finite palette, never runtime smoothing.
        crop=crop.quantize(colors=48,method=Image.Quantize.FASTOCTREE).convert('RGBA')
        atlas.alpha_composite(crop,(x*128+(128-crop.width)//2,y*128+126-crop.height))
    save(filename.split('-')[0],atlas,{name:i for i,name in enumerate(names)})

source_atlas('scenery-original.png',['tree_green_01','tree_green_02','tree_green_03','well','house_01','house_02','house_03','recovery_tent','barrel','crate','ruin','statue','obelisk','crystal','alchemy','forge'],[(48,64)]*3+[(32,40)]+[(96,80)]*3+[(72,64),(16,22),(20,20),(24,40),(24,40),(24,48),(24,32),(40,32),(40,40)],4)
if (ROOT.parents[3]/'art/pixel/source/bosses-original.png').exists():
    source_atlas('bosses-original.png',['moss_colossus','thorn_chief','abyssal_warden','basalt_drake'],[(96,96)]*4,2)

# 16x16 tiles, eight variants per material. Discrete clusters, shared directional light.
palettes={
 'grass':['#526f3d','#5f7c41','#668447','#708d4b','#8eaa55','#395739'],
 'wood':['#775239','#805a3c','#906546','#9d734f','#b88b5c','#4c392d'],
 'ruins':['#263f3c','#2b4540','#304b44','#39524a','#536854','#172e30'],
 'moss':['#263c35','#2a4339','#30493c','#3c5340','#647956','#192b29'],
 'cave':['#2c3e4a','#304451','#354957','#405363','#627783','#1a2b36'],
 'crypt':['#383d49','#3e4250','#454956','#515461','#747886','#232835'],
 'ritual':['#22273d','#292e47','#30364e','#394057','#515a70','#161b2f'],
 'secret':['#202c40','#253247','#2c394d','#364257','#566478','#151f32'],
 'path':['#b0a380','#bcae88','#c8b993','#d2c19a','#e5d4a9','#80795f'],
}
tiles=Image.new('RGBA',(16*8,16*(len(palettes)*2+1)))
tileframes={}
for row,(name,pal) in enumerate(palettes.items()):
 for variant in range(8):
    rng=random.Random(f'{name}:{variant}')
    im=Image.new('RGBA',(16,16),pal[variant%3]);d=ImageDraw.Draw(im)
    if name=='grass':
        for _ in range(8):
            x,y=rng.randrange(15),rng.randrange(15);d.line((x,y,x+1,y+1),fill=pal[rng.choice([0,2,3])])
        if variant in (2,5,7):
            for x,y in [(3,12),(10,5)]:
                d.line((x,y+2,x-1,y-1),fill=pal[5]);d.point((x,y),fill=pal[4]);d.line((x,y+2,x+2,y-2),fill=pal[3])
        if variant==7:
            for x,y in [(5,4),(12,12)]:d.rectangle((x,y,x+1,y+1),fill='#e4d99a');d.point((x,y),fill='#f6edcd')
    elif name=='wood':
        for y in (0,5,10,15):d.line((0,y,15,y),fill=pal[5]);d.line((0,y+1,15,y+1),fill=pal[3])
        for y in (2,7,12):
            x=rng.randrange(3,13);d.line((x,y,x+5,y),fill=pal[2]);d.line((x,y-1,x,y+2),fill=pal[5])
    else:
        # Irregular masonry seams; occasional cracks/moss, never random full-tile noise.
        d.line((0,0,15,0),fill=pal[4]);d.line((0,1,15,1),fill=pal[3]);d.line((0,0,0,15),fill=pal[3]);d.line((15,1,15,15),fill=pal[5]);d.line((1,15,15,15),fill=pal[5])
        for _ in range(4):
            x,y=rng.randrange(2,14),rng.randrange(2,14);d.rectangle((x,y,x+1,y),fill=pal[rng.choice([1,2,3])])
        if variant%3==0:d.line([(3,2),(4,5),(7,6),(6,9),(8,10)],fill=pal[5]);d.point((5,5),fill=pal[3])
        if variant in (2,5):
            for x,y in [(2,12),(4,14),(1,9),(11,2)]:d.rectangle((x,y,x+2,y+1),fill='#526447' if name not in ('secret','ritual') else '#394b56')
    tiles.alpha_composite(im,(variant*16,row*32));tileframes[f'{name}_{variant}']=row*16+variant
    wall=Image.new('RGBA',(16,16),pal[5]);wd=ImageDraw.Draw(wall)
    for yy in range(0,16,5):
        for xx in range(-8 if yy%2 else 0,16,8):
            wd.rectangle((xx+1,yy,xx+7,yy+3),fill=pal[1]);wd.line((xx+1,yy,xx+6,yy),fill=pal[3]);wd.point((xx+6,yy+2),fill=pal[2])
    wd.rectangle((0,13,15,15),fill=pal[5]);tiles.alpha_composite(wall,(variant*16,row*32+16));tileframes[f'{name}_wall_{variant}']=row*16+8+variant
# Paintings are sampled to native32px tiles: four quadrants × two authored variants.
tiles=tiles.resize((tiles.width*2,tiles.height*2),Image.Resampling.NEAREST)
terrain=Image.open(ROOT.parents[3]/'art/pixel/source/terrain-original.png').convert('RGBA')
for row,name in enumerate(palettes):
    if name=='wood':continue
    column=0 if name=='grass' else 1 if name=='path' else 3 if name in ('ritual','secret') else 2
    for variant in range(8):
        rr=variant//4
        crop=terrain.crop((round(column*terrain.width/4),round(rr*terrain.height/2),round((column+1)*terrain.width/4),round((rr+1)*terrain.height/2))).resize((128,128),Image.Resampling.NEAREST)
        q=variant%4;xx,yy=(q%2)*96,(q//2)*96;tile=crop.crop((xx,yy,xx+32,yy+32))
        if name=='grass':tile=Image.blend(tile,Image.new('RGBA',tile.size,'#526f3d'),0.28)
        if name in ('cave','crypt'):
            pixels=tile.load()
            for yy in range(32):
                for xx in range(32):
                    r,g,b,a=pixels[xx,yy];pixels[xx,yy]=(min(255,r+3),max(0,g-9),min(255,b+13),a) if name=='cave' else (min(255,r+10),max(0,g-12),min(255,b+8),a)
        tile=tile.quantize(colors=32,method=Image.Quantize.FASTOCTREE).convert('RGBA')
        tiles.paste(tile,(variant*32,row*64))
save('tiles',tiles,tileframes)

colors={'hero':('#d6af83','#547e94','#293e58'),'peer':('#d6ab87','#a27c9e','#493a58'),'npc':('#deb990','#ad8c51','#5e4334'),'merchant':('#d7ad82','#66855a','#394e3b'),'alchemist':('#d3ad8b','#8c72ae','#3b375e'),'blacksmith':('#c89b77','#8a6045','#323c44'),'hooded':('#060d17','#39464c','#121e2c'),'goblin':('#91a678','#5f7956','#2c3f3e'),'goblin_elite':('#92a58a','#834b65','#303945'),'slime':('#a4cf69','#598d4d','#244c42'),'slime_elite':('#c4bd8b','#75668c','#343a56'),'dummy':('#d8bf8a','#9f794c','#544433')}
for key,(skin,cloth,dark) in colors.items():
    atlas=Image.new('RGBA',(32*8,48*10))
    for frame in range(80):
        state,dir,step=frame//16,(frame%16)//4,frame%4
        im=Image.new('RGBA',(32,48));d=ImageDraw.Draw(im)
        bob=1 if (state==1 and step%2 or state==0 and step==2) else 0
        def rect(box,c):d.rectangle((box[0],box[1]+bob,box[2],box[3]+bob),fill=c)
        outline='#14262d';light='#f0d0a0'
        if key.startswith('slime'):
            d.polygon([(3,38),(4,29),(9,22),(14,20),(22,22),(27,28),(29,38),(26,42),(7,42)],fill=outline)
            d.polygon([(5,37),(7,29),(12,24),(19,23),(25,28),(27,37),(24,40),(8,40)],fill=cloth)
            d.polygon([(7,29),(12,24),(19,23),(23,27),(19,29),(11,29)],fill=skin)
            for x,y in [(9,32),(21,32)]:d.rectangle((x,y,x+2,y+3),fill=outline);d.point((x,y),fill='#fff0b9')
            d.line((13,38,18,38),fill=dark);d.rectangle((8,25,11,26),fill='#d7e7a1')
            if key.endswith('elite'):d.polygon([(8,22),(8,16),(12,19),(16,14),(19,19),(23,16),(23,23)],fill='#ba9971');d.point((16,18),fill='#a0e6df')
        elif key=='dummy':
            rect((14,11,17,43),dark);rect((5,23,26,27),dark);rect((9,13,22,34),cloth);rect((10,6,21,16),skin)
            for yy in [18,24,30]:rect((9,yy,22,yy+1),'#e3c491')
            d.ellipse((12,21,19,28),outline=dark,width=2)
        else:
            # Full outlined silhouette, asymmetric kit, cloth folds, boots, metal and face shading.
            leg=2 if state==1 and step%2 else 0
            rect((9,34,14,44-leg),outline);rect((19,34,24,44-(2-leg if state==1 else 0)),outline)
            rect((9,40-leg,15,44-leg),'#624b3d');rect((19,40,25,44),'#624b3d');rect((10,40-leg,13,41-leg),'#a88859')
            d.polygon([(8,18+bob),(22,18+bob),(26,37+bob),(20,39+bob),(7,36+bob)],fill=outline)
            rect((9,19,22,34),dark);rect((10,19,20,31),cloth);rect((11,21,12,30),'#9eac9a');rect((21,23,23,34),dark)
            rect((6,21,9,32),outline);rect((23,21,26,32),outline);rect((6,28,9,33),skin);rect((23,28,26,33),skin)
            rect((9,32,23,34),'#5d4938');rect((15,32,17,34),'#d4b369')
            rect((10,6,21,18),outline);rect((11,7,20,17),skin);rect((11,7,13,16),'#b08767');rect((14,7,19,9),light)
            rect((9,5,22,8),dark);rect((9,8,11,12),dark);rect((20,8,22,11),dark);rect((11,5,19,6),'#76644d')
            if dir!=3:
                for xx in ([12] if dir==1 else [19] if dir==2 else [13,19]):rect((xx,11,xx+1,13),outline);rect((xx,11,xx,11),'#ebead6')
                rect((15,16,17,16),'#8a6758')
            else:rect((10,7,21,16),dark);rect((12,7,19,9),'#716754');rect((12,19,20,30),cloth)
            if key in ('hero','peer'):
                rect((7,19,10,25),'#8398a1');rect((21,19,24,24),'#8398a1');rect((7,19,9,20),'#cfdbce')
                sx=26 if dir!=1 else 4;rect((sx,22-(step*2 if state==2 else 0),sx+1,39),'#d4e0da');rect((sx-2,33,sx+3,34),'#c5a264');rect((sx,35,sx+1,39),dark)
                rect((10,18,12,30),'#9b7853');rect((12,24,21,25),'#9b7853')
            elif key=='merchant':
                rect((8,4,23,6),'#8b6841');rect((12,1,20,5),'#846c46');rect((10,3,21,4),'#aa8c52');rect((21,28,28,36),'#72543d');rect((23,29,26,30),'#b99860');rect((10,19,12,31),'#b9a174')
            elif key=='alchemist':
                d.polygon([(8,11+bob),(14,0+bob),(19,3+bob),(24,12+bob)],fill=dark);rect((9,10,23,12),cloth);rect((23,29,27,34),'#8bcbd0');rect((24,27,26,28),'#c9ad73');rect((11,20,12,31),'#b5a0c5');rect((15,25,18,27),'#e2cb81')
            elif key=='blacksmith':
                rect((11,22,21,36),'#9e7751');rect((12,23,13,34),'#c39b69');rect((13,28,20,30),dark);rect((25,21,26,33),'#ad8356');rect((22,18,29,22),'#8b9b9c');rect((22,18,29,19),'#c6d1ba');rect((6,28,10,34),dark)
            elif key=='hooded':
                d.polygon([(7,18),(9,7),(16,2),(23,8),(25,20),(29,42),(6,42)],fill=dark);d.polygon([(9,18),(10,10),(16,6),(22,11),(22,19)],fill='#040911');d.line((9,20,7,39),fill='#52606a',width=2);d.line((23,21,26,40),fill='#344653');rect((10,39,24,42),'#17222b')
            elif key.startswith('goblin'):
                d.polygon([(10,8),(4,6),(7,15),(11,14)],fill=skin);d.polygon([(21,8),(28,5),(24,15),(21,14)],fill=skin);rect((12,14,13,15),'#ece2b3');rect((19,14,20,15),'#ece2b3');rect((23,21,25,37),'#a68a59');rect((24,20,29,24),'#9fb1aa')
                if key.endswith('elite'):
                    rect((8,18,12,23),'#9c91a3');rect((20,18,25,23),'#9c91a3');d.polygon([(10,6),(7,1),(13,5),(20,5),(25,1),(22,8)],fill='#b7a086');rect((11,8,21,10),'#656674')
        if state==3:
            alpha=im.getchannel('A');im=Image.blend(im,Image.new('RGBA',im.size,'#f5b0a0'),0.25);im.putalpha(alpha)
        if state==4:
            box=im.getbbox()
            if box:
                dead=im.crop(box).rotate(90,expand=True,resample=Image.Resampling.NEAREST);dead.thumbnail((28,12),Image.Resampling.NEAREST);im=Image.new('RGBA',(32,48));im.alpha_composite(dead,((32-dead.width)//2,44-dead.height))
        atlas.alpha_composite(im,((frame%8)*32,(frame//8)*48))
    save(key,atlas,{'frameWidth':32,'frameHeight':48,'endFrame':79})

# Small authored effects/props atlas. Four flames have deliberately different silhouettes.
names=['flame_0','flame_1','flame_2','flame_3','shadow','glow_warm','glow_cyan','glow_ritual','flower','bush','moss','mushroom','bones','banner','shelf','table','counter','chair','bench','rug','portal','herb','ore','lunar','rock','sign','rune','smoke']
effects=Image.new('RGBA',(64*8,64*4))
for i,name in enumerate(names):
    im=Image.new('RGBA',(64,64));d=ImageDraw.Draw(im)
    if name.startswith('flame'):
        f=int(name[-1]);d.rectangle((29,44,34,60),fill='#80604a');d.rectangle((26,39,37,43),fill='#555a58');d.polygon([(27,39),(24,30),(29,21),(28+f,10),(34,18),(37+f,28),(37,37),(33,41)],fill='#d85b35');d.polygon([(28,37),(28,29),(33,20+f),(35,30),(34,38)],fill='#f8ac52');d.rectangle((30,32,33,38),fill='#ffeab0')
    elif name=='shadow':d.polygon([(12,28),(20,24),(44,24),(52,28),(52,34),(44,38),(20,38),(12,34)],fill='#081d2855')
    elif name.startswith('glow'):
        rgb={'glow_warm':(255,159,70),'glow_cyan':(84,202,214),'glow_ritual':(139,92,197)}[name]
        for r,a in [(31,7),(26,12),(20,18),(15,24),(9,35)]:d.ellipse((32-r,32-r,32+r,32+r),fill=(*rgb,a))
    elif name in ('flower','herb','moss','bush','mushroom'):
        for x,y in [(15,48),(28,42),(40,51),(34,57)]:
            d.line((x,y,x-3,y-8),fill='#3e643e',width=2);d.line((x,y,x+4,y-12),fill='#7f9c50',width=2)
            if name in ('flower','herb'):d.rectangle((x+2,y-15,x+5,y-12),fill='#e8d4a1' if x%2 else '#d5a19b');d.point((x+3,y-13),fill='#f6edc9')
            if name=='mushroom':d.rectangle((x,y-8,x+1,y),fill='#8cae93');d.ellipse((x-4,y-12,x+5,y-7),fill='#63a0a1');d.point((x-1,y-10),fill='#c0d9b0')
        if name=='bush':
            for x,y,r in [(18,48,9),(30,42,12),(44,49,10)]:d.ellipse((x-r,y-r,x+r,y+r),fill='#355739');d.arc((x-r,y-r,x+r,y+r),180,290,fill='#94aa58',width=3)
    elif name in ('ore','lunar','rock'):
        col='#7eacbe' if name=='lunar' else '#777f72';d.polygon([(16,54),(20,41),(31,35),(46,40),(50,54),(39,60),(24,59)],fill='#263f48');d.polygon([(18,51),(22,41),(32,38),(45,42),(46,51),(35,54)],fill=col);d.line((23,42,31,39,40,42),fill='#ccdbbd',width=2)
        if name=='lunar':d.polygon([(27,49),(28,40),(33,35),(37,44),(34,51)],fill='#c8f5ec')
    elif name=='bones':
        d.line((15,55,45,39),fill='#9b9c89',width=4);d.ellipse((17,35,29,46),fill='#c5c4a5');d.rectangle((20,38,22,40),fill='#343f40');d.rectangle((25,38,27,40),fill='#343f40')
    elif name in ('portal','rune'):
        if name=='portal':d.rectangle((11,10,52,61),fill='#324f56');d.rectangle((15,14,48,61),fill='#b19a6a');d.rectangle((19,18,44,61),fill='#172c38');d.line((21,23,41,23),fill='#7eaba9',width=2)
        else:
            d.ellipse((5,5,59,59),outline='#9a52687a',width=1);d.ellipse((10,10,54,54),outline='#6e7d9a88',width=1);d.line((32,11,49,43,14,43,32,11),fill='#84476077',width=1)
            for a in range(0,360,30):
                x,y=round(32+24*math.cos(math.radians(a))),round(32+24*math.sin(math.radians(a)));d.line((x,y-1,x+1,y+1,x-1,y+2),fill='#c1889777')
    elif name=='smoke':d.rectangle((29,20,33,25),fill='#b3bfab44');d.rectangle((31,11,36,16),fill='#c7d0b533')
    elif name=='rug':
        d.rectangle((3,3,60,60),fill='#513d44');d.rectangle((5,5,58,58),outline='#c4a36b',width=2);d.rectangle((9,9,54,54),fill='#754f53');d.rectangle((12,12,51,51),outline='#a9825c')
        for xx in range(8,60,6):d.line((xx,1,xx,3),fill='#d0b47e');d.line((xx,61,xx,63),fill='#d0b47e')
        for xx,yy in [(20,20),(40,20),(20,40),(40,40)]:d.polygon([(xx,yy-5),(xx+4,yy),(xx,yy+5),(xx-4,yy)],outline='#c09b67')
    elif name=='banner':
        d.rectangle((17,4,47,6),fill='#a08759');d.polygon([(20,7),(44,7),(44,48),(32,56),(20,48)],fill='#513947');d.line((24,10,24,45,32,49,40,45,40,10),fill='#8a5a5b');d.line((32,18,32,37),fill='#b78361',width=2);d.line((27,22,37,29,27,34),fill='#b78361',width=2)
    else:
        # Crafted timber furniture with joinery, textured planks, rivets, highlighted edges.
        w=44 if name in ('table','counter','rug') else 30
        left=(64-w)//2
        d.rectangle((left+2,28,left+w-2,59),fill='#352d2c');d.rectangle((left,24,left+w,52),fill='#785438');d.rectangle((left+2,25,left+w-2,27),fill='#c19b64')
        for yy in (32,40,48):d.line((left+2,yy,left+w-2,yy),fill='#493c2f');d.line((left+3,yy+1,left+w-3,yy+1),fill='#9d774e')
        for xx in (left+3,left+w-3):d.rectangle((xx,28,xx+1,49),fill='#ad895c')
        if name=='shelf':
            for j,c in enumerate(['#829b85','#b88662','#a7966a','#6d7d99']):d.rectangle((left+4+j*6,29,left+7+j*6,39),fill=c)
        if name=='sign':d.line((32,48,32,63),fill='#65482f',width=4);d.line((22,35,42,35),fill='#d3b776',width=2)
    effects.alpha_composite(im,((i%8)*64,(i//8)*64))
save('effects',effects,{name:i for i,name in enumerate(names)})
(ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(ROOT.parents[3]/'frontend/src/visual/atlas.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(f'Compiled {len(manifest)} original atlases; '+str(sum((ROOT/v['file']).stat().st_size for v in manifest.values()))+' bytes')
