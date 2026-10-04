"""Full raw-byte source/native audits and display-only individual orbit/street sheets."""
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from PIL import Image,ImageChops,ImageDraw

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'tools/assets'))
from compare_galleries import captures,image
spec=importlib.util.spec_from_file_location('shore_raw_registration',HERE.parent/'river-sloped-bank-breadth/registered-bytes.py')
raw=importlib.util.module_from_spec(spec);spec.loader.exec_module(raw)


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def display(picture):
    # Cropping/magnification belongs to presentation only, never a comparison.
    box=ImageChops.difference(picture.convert('RGB'),Image.new('RGB',picture.size,picture.getpixel((0,0))[:3])).getbbox()
    if box:picture=picture.crop(box)
    factor=max(1,min(8,275//picture.width,250//picture.height))
    return picture.resize((picture.width*factor,picture.height*factor),Image.Resampling.NEAREST)


def changed(a,b):
    if a.size!=b.size:return {'different':True,'size_mismatch':[list(a.size),list(b.size)]}
    left,right=a.tobytes(),b.tobytes()
    return {'different':left!=right,'different_pixels':sum(left[index:index+4]!=right[index:index+4] for index in range(0,len(left),4))}


def main():
    target=HERE/'individual-review-sheets';target.mkdir(exist_ok=False)
    sources=json.loads((HERE/'actual-source-index.json').read_text());runs=json.loads((HERE/'study-runs.json').read_text())
    rows=[];sheets=[];pairs=[]
    for source in sources:
        name=f"river_bank_shore_study_{source['climate_name']}_offset{source['requested_offset']:02d}";label='model-voxel-'+name
        directories={backend:ROOT/next(row['output'] for row in runs if row['climate']==source['climate_name'] and row['backend']==backend)/'renderer3d-reference' for backend in ('vulkan','opengl')}
        frames={backend:captures(directory,label+'-*') for backend,directory in directories.items()}
        assert len(frames['vulkan'])==len(frames['opengl'])==9 and frames['vulkan'].keys()==frames['opengl'].keys()
        native_path=frames['vulkan'][label+'-native'];registration=directories['vulkan']/(label+'-native.json')
        original=raw.registered(image(ROOT/source['source_pam']),source['native_offset'])
        model=raw.native(image(native_path),json.loads(registration.read_text()));(a,b),bounds=raw.pair(original,model)
        left,right=a.tobytes(),b.tobytes();pixels=sum(left[index:index+4]!=right[index:index+4] for index in range(0,len(left),4))
        silhouette=sum(bool(left[index+3])!=bool(right[index+3]) for index in range(0,len(left),4))
        paths=[ROOT/source['source_pam'],native_path,registration]
        rows.append({'model':name,'climate':source['climate'],'requested_offset':source['requested_offset'],'slope':source['slope'],
            'complete_rgba_changed_pixels':pixels,'alpha_presence_differences_additional_diagnostic':silhouette,
            'shared_bounds':bounds,'raw_source_bounds':original[1],'raw_native_bounds':model[1],
            'source_wave_fringe_and_hidden_rgb_preserved':True,'resizing_cropping_alpha_compositing_masks_or_tolerance_used':False,
            'evidence_sha256':{str(path.relative_to(ROOT)):digest(path) for path in paths},'quality_approved':False})
        canvas=Image.new('RGB',(1200,1000),(38,39,47));draw=ImageDraw.Draw(canvas)
        draw.text((8,8),name+' — unbound shore bank; no source/terrain/state/quality acceptance',fill='white')
        for slot,picture in enumerate((a,b)):
            picture=picture.resize((picture.width*8,picture.height*8),Image.Resampling.NEAREST)
            canvas.paste(picture,(slot*600+(600-picture.width)//2,65),picture)
            draw.text((slot*600+8,35),'Complete original + wave fringe, 8x' if slot==0 else 'Bank-only native at the same tile anchor, 8x',fill='white')
        for view in range(8):
            picture=display(image(frames['vulkan'][label+f'-{view}']));x,y=view%4*300,330+view//4*320
            canvas.paste(picture,(x+(300-picture.width)//2,y+35+(250-picture.height)//2))
            draw.text((x+8,y),f"{'Orbit' if view<4 else 'Street'} {view%4} — display only",fill='white')
        sheet=target/(name+'.png');canvas.save(sheet)
        sheets.append({'model':name,'sheet':str(sheet.relative_to(ROOT)),'sheet_sha256':digest(sheet),
            'native':str(native_path.relative_to(ROOT)),'registration':str(registration.relative_to(ROOT)),
            'source_pam':source['source_pam'],'source_pam_sha256':source['source_pam_sha256'],'source_native_failed_pixels':pixels,
            'source_silhouette_failed_pixels':silhouette,'quality_approved':False})
        for key in frames['vulkan']:
            result=changed(image(frames['vulkan'][key]),image(frames['opengl'][key]))
            pairs.append({'model':name,'view':key,'vulkan':str(frames['vulkan'][key].relative_to(ROOT)),
                'opengl':str(frames['opengl'][key].relative_to(ROOT)),**result})
    source_audit={'audited_utc':datetime.now(timezone.utc).isoformat(),'models':len(rows),'rows':rows,
        'different_images':sum(row['complete_rgba_changed_pixels']!=0 for row in rows),
        'different_pixels':sum(row['complete_rgba_changed_pixels'] for row in rows),
        'silhouette_differences_additional_diagnostic':sum(row['alpha_presence_differences_additional_diagnostic'] for row in rows),
        'all_raw_image_bytes_preserved_without_alpha_compositing':True,'source_wave_pixels_removed':False,'quality_approvals':0}
    for path,value in ((HERE/'source-native-audit.json',source_audit),(target/'index.json',sheets),
        (HERE/'backend-gallery-audit.json',{'images':len(pairs),'different_images':sum(row['different'] for row in pairs),
            'different_pixels':sum(row.get('different_pixels',0) for row in pairs),'rows':pairs,'quality_approvals':0})):
        with path.open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')
    print(json.dumps({key:value for key,value in source_audit.items() if key!='rows'}))


if __name__=='__main__':main()
