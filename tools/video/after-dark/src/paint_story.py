"""paint_story.py <slug> '<json list of per-beat scene options>'  -> stories/<slug>-painted.json
Each option dict may hold: n (picture index, default beat index), focus, move, amount, snow, rain, orbs, ghost..., dim."""
import json, sys, os, shutil, glob
slug=sys.argv[1]; opts=json.loads(sys.argv[2]) if len(sys.argv)>2 else []
F='/root/afterdark/film'
src='/mnt/user-data/uploads/Videos/After Dark painted/%s'%slug
dst='%s/paint/%s'%(F,slug); os.makedirs(dst,exist_ok=True)
for f in glob.glob(src+'/*.jpg'): shutil.copy(f,dst)
d=json.load(open('%s/stories/%s.json'%(F,slug)))
d['slug']=slug+'-painted'; d['ai_pictures']=True
nb=len(d['beats'])
for i,b in enumerate(d['beats']):
    o=dict(opts[i]) if i<len(opts) else {}
    if o.pop('keep',False): continue
    n=o.pop('n', i if not b.get('end') else 0)
    sc=dict({"kind":"paint","src":"paint/%s/p%d.jpg"%(slug,n),"move":"in","amount":0.10},**o)
    if b.get('end'):
        sc.setdefault('dim',0.7); sc['move']=o.get('move','still')
        b['end_card']['scene']=sc; b['credit']='Pictures: AI-generated (Canva)'
    else:
        b['scene']=sc
        c=b.get('credit','').replace('History: ','').replace('What people report: ','').split(';')[0].strip()
        b['credit']=(c+' · ' if c else '')+'AI-generated picture'
json.dump(d,open('%s/stories/%s-painted.json'%(F,slug),'w'),indent=1)
print('ok',nb,'beats')
