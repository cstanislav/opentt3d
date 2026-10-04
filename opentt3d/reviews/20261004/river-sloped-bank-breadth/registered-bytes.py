"""Place complete raw RGBA at integer tile anchors, without alpha compositing."""
from PIL import Image


def registered(picture, offset):
    if picture.mode != "RGBA" or len(offset) != 2 or any(type(value) is not int for value in offset):
        raise ValueError("Expected unconverted RGBA and the exact integer source tile anchor")
    x,y = offset
    return picture,(x,y,x+picture.width,y+picture.height)


def native(picture, registration):
    if list(picture.size) != registration["image_size"]:
        raise ValueError("Native dimensions differ from retained registration")
    return registered(picture,[-value for value in registration["model_origin"]])


def pair(source, model):
    pictures = [source,model]
    left,top = (min(bounds[axis] for _,bounds in pictures) for axis in (0,1))
    right,bottom = (max(bounds[axis] for _,bounds in pictures) for axis in (2,3))
    result = []
    for picture,bounds in pictures:
        canvas = Image.new("RGBA",(right-left,bottom-top),(0,0,0,0))
        # No alpha mask: preserve RGB under alpha zero and partially transparent
        # RGBA exactly. Transparent padding extends, never crops, the raw image.
        canvas.paste(picture,(bounds[0]-left,bounds[1]-top))
        result.append(canvas)
    return result,(left,top,right,bottom)
