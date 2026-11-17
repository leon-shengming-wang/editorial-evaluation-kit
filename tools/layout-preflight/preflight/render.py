"""Render original schematic SVG specimens. No font measurements are inferred."""
from html import escape
from .core import validate

def svg(spec):
    errors=validate(spec)
    if errors: raise ValueError('; '.join(errors))
    c=spec['canvas']; m=spec['rules']['safe_margin']
    parts=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {} {}" role="img"><title>{}</title>'.format(c['width'],c['height'],escape(spec['title'])),
           '<rect width="100%" height="100%" fill="{}"/>'.format(c['background']),
           '<rect x="{0}" y="{0}" width="{1}" height="{2}" fill="none" stroke="#809499" stroke-dasharray="6 6"/>'.format(m,c['width']-2*m,c['height']-2*m)]
    for b in spec['boxes']:
        parts.append('<rect x="{x}" y="{y}" width="{width}" height="{height}" fill="none" stroke="#809499" stroke-opacity="0.6"/>'.format(**b))
        # Lines are explicitly authored. Browser font substitution may change rendering.
        parts.append('<text x="{}" y="{}" font-size="{}" font-family="{}" fill="{}">'.format(b['x'],b['y']+b['font_px'],b['font_px'],escape(b['font_family'],quote=True),b['color']))
        for i,line in enumerate(b['text'].splitlines()):
            parts.append('<tspan x="{}" dy="{}">{}</tspan>'.format(b['x'],0 if i==0 else b['font_px']*1.3,escape(line)))
        parts.append('</text>')
    return ''.join(parts)+'</svg>'

def html(spec,findings):
    rows=''.join('<tr><td>{}</td><td>{}</td><td>{}</td></tr>'.format(escape(f['code']),escape(f['box']),escape(f['message'])) for f in findings)
    if not rows: rows='<tr><td colspan="3">No configured rule violations. Visual review is still required.</td></tr>'
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Layout Preflight</title><style>body{margin:0;background:#111719;color:#e8efec;font:16px/1.6 system-ui,sans-serif}main{max-width:1100px;margin:auto;padding:48px 24px}h1{font-size:48px;letter-spacing:-2px}small{color:#93cbb7}svg{display:block;max-height:750px;width:100%;margin:32px auto;border:1px solid #425151}table{border-collapse:collapse;width:100%}td,th{padding:14px;text-align:left;border-bottom:1px solid #425151;vertical-align:top}code{color:#93cbb7}@media(max-width:600px){main{padding:24px 14px}h1{font-size:36px}td,th{padding:8px;font-size:13px}}</style><main><small>LAYOUT PREFLIGHT / SYNTHETIC DESIGN QA</small><h1>''' + escape(spec['title']) + '</h1><p>A deterministic check of declared design specifications, not an automated aesthetic judgment.</p>'+svg(spec)+'<h2>Review queue</h2><table><thead><tr><th>Rule</th><th>Element</th><th>Observation</th></tr></thead><tbody>'+rows+'</tbody></table><h2>Human review remains essential</h2><p>Dashed lines show the safe area. Solid rectangles show declared text boxes, not measured glyph bounds. This tool cannot detect actual text overflow, font substitution, image quality, spelling, historical accuracy, or the quality of a rendered exhibit. It evaluates opaque text on a single solid canvas background only.</p></main></html>'
