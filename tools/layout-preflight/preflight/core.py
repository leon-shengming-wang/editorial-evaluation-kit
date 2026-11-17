import math
import re
from itertools import combinations

COLOR = re.compile(r'#[0-9a-fA-F]{6}\Z')
FONT = re.compile(r'[A-Za-z][A-Za-z0-9 -]{0,63}\Z')
MAX_ABS_NUMBER = 100000

def number(value, positive=False):
    # Check bounds before math.isfinite: converting an enormous integer to float
    # can overflow. This also keeps sums and SVG geometry within finite limits.
    return (type(value) in (int,float) and -MAX_ABS_NUMBER <= value <= MAX_ABS_NUMBER
            and math.isfinite(value) and (not positive or value > 0))

def validate(spec):
    errors=[]
    if not isinstance(spec,dict): return ['spec must be an object']
    if set(spec) != {'title','canvas','rules','boxes'}: errors.append('spec requires exactly title, canvas, rules and boxes')
    if not isinstance(spec.get('title'),str) or not spec['title'].strip(): errors.append('title must be nonempty text')
    canvas=spec.get('canvas'); rules=spec.get('rules'); boxes=spec.get('boxes')
    if not isinstance(canvas,dict) or set(canvas)!={'width','height','background'}: errors.append('invalid canvas fields')
    else:
        for k in ('width','height'):
            if not number(canvas[k],True) or canvas[k]>10000: errors.append(k+' must be positive and at most 10000')
        if not isinstance(canvas['background'],str) or not COLOR.fullmatch(canvas['background']): errors.append('background must be #RRGGBB')
    if not isinstance(rules,dict) or set(rules)!={'safe_margin','body_min_px','headline_ratio','allowed_fonts'}: errors.append('invalid rules fields')
    else:
        for k in ('safe_margin','body_min_px','headline_ratio'):
            if not number(rules[k],True): errors.append(k+' must be positive')
        fonts=rules['allowed_fonts']
        if not isinstance(fonts,list) or not fonts or any(not isinstance(f,str) or not FONT.fullmatch(f) for f in fonts): errors.append('allowed_fonts must be a nonempty list of simple family names')
        if number(rules['headline_ratio']) and rules['headline_ratio']<=1: errors.append('headline_ratio must exceed 1')
        if isinstance(canvas,dict) and number(canvas.get('width')) and number(canvas.get('height')) and number(rules['safe_margin']):
            if rules['safe_margin']*2>=min(canvas['width'],canvas['height']): errors.append('safe margin leaves no usable area')
    if not isinstance(boxes,list) or not 1<=len(boxes)<=1000: errors.append('boxes must contain 1-1000 records')
    else:
        seen=set()
        required={'id','role','x','y','width','height','font_px','font_family','color','text'}
        for i,box in enumerate(boxes):
            label='box '+str(i)
            if not isinstance(box,dict) or set(box)!=required:
                errors.append(label+' has invalid fields'); continue
            if not isinstance(box['id'],str) or not re.fullmatch('[a-z0-9-]{1,64}',box['id']): errors.append(label+' has invalid id')
            elif box['id'] in seen: errors.append(label+' has duplicate id')
            else: seen.add(box['id'])
            if box['role'] not in ('headline','body','caption'): errors.append(label+' has invalid role')
            for k in ('x','y','width','height','font_px'):
                if not number(box[k],k not in ('x','y')): errors.append(label+'.'+k+' is invalid')
            if not isinstance(box['font_family'],str) or not FONT.fullmatch(box['font_family']): errors.append(label+' has invalid font family')
            if not isinstance(box['color'],str) or not COLOR.fullmatch(box['color']): errors.append(label+' has invalid color')
            if not isinstance(box['text'],str) or not box['text'].strip(): errors.append(label+' has empty text')
    return errors

def luminance(color):
    if not isinstance(color,str) or not COLOR.fullmatch(color): raise ValueError('expected #RRGGBB')
    channels=[int(color[i:i+2],16)/255 for i in (1,3,5)]
    linear=[v/12.92 if v<=0.04045 else ((v+0.055)/1.055)**2.4 for v in channels]
    return sum(v*w for v,w in zip(linear,(0.2126,0.7152,0.0722)))

def contrast(a,b):
    x,y=sorted((luminance(a),luminance(b)))
    return (y+0.05)/(x+0.05)

def inspect(spec):
    errors=validate(spec)
    if errors: raise ValueError('; '.join(errors))
    findings=[]; canvas=spec['canvas']; rules=spec['rules']; boxes=spec['boxes']
    def add(code,box,message,severity='warning'):
        findings.append({'code':code,'box':box,'severity':severity,'message':message})
    for box in boxes:
        x,y,w,h=box['x'],box['y'],box['width'],box['height']; margin=rules['safe_margin']
        if x<0 or y<0 or x+w>canvas['width'] or y+h>canvas['height']:
            add('OUT_OF_BOUNDS',box['id'],'Declared box extends beyond the canvas.','error')
        elif min(x,y,canvas['width']-x-w,canvas['height']-y-h)<margin:
            add('SAFE_MARGIN',box['id'],'Declared box enters the configured safe margin.')
        ratio=contrast(box['color'],canvas['background'])
        # Deliberately conservative: no large-text or logo exemptions in this tool.
        if ratio<4.5: add('CONTRAST',box['id'],'Text/background contrast is {:.3f}:1; this project requires 4.5:1 for every text role.'.format(ratio),'error')
        if box['font_family'] not in rules['allowed_fonts']: add('FONT_FAMILY',box['id'],'Font family is outside the declared design system.')
        if box['role']=='body' and box['font_px']<rules['body_min_px']: add('BODY_SIZE',box['id'],'Body font is smaller than the project minimum.')
    body_sizes=[b['font_px'] for b in boxes if b['role']=='body']
    for box in boxes:
        if box['role']=='headline' and body_sizes and box['font_px']<max(body_sizes)*rules['headline_ratio']:
            add('HIERARCHY',box['id'],'Headline/body size ratio is below the configured target.')
    for a,b in combinations(boxes,2):
        if a['x']<b['x']+b['width'] and b['x']<a['x']+a['width'] and a['y']<b['y']+b['height'] and b['y']<a['y']+a['height']:
            add('BOX_OVERLAP',a['id']+' + '+b['id'],'Declared rectangles overlap; inspect whether this is intentional.')
    by_role={role:{b['font_family'] for b in boxes if b['role']==role} for role in ('headline','body','caption')}
    for role,fonts in by_role.items():
        if len(fonts)>1: add('ROLE_FONT_VARIATION',role,'Multiple font families are used for the same role; review intentionality.')
    return findings
