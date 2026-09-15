"""Prepare DinoStomp's hand-pixelled README assets, locally with Pillow."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/exports/readme'
STEM = '20260915_120000_readme_pixel-dino'
SCALE = 2
FRAMES = 48
COLORS = ['#10151e', '#1a2430', '#293c49', '#416069', '#73d6a0', '#dfeaf5', '#a9cbdc', '#536c7b', '#f5cd70', '#42996d']
FONT = ImageFont.load_default()
GLYPHS = {
 'd':['00001','00001','01111','10001','10001','10001','01111'],
 'i':['00100','00000','01100','00100','00100','00100','01110'],
 'n':['00000','00000','11110','10001','10001','10001','10001'],
 'o':['00000','00000','01110','10001','10001','10001','01110'],
 's':['00000','00000','01111','10000','01110','00001','11110'],
 't':['00100','00100','11111','00100','00100','00101','00010'],
 'm':['00000','00000','11010','10101','10101','10101','10101'],
 'p':['00000','00000','11110','10001','11110','10000','10000'],
}

def canvas(size: tuple[int, int]) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    """Create a canvas with the shared pixel palette."""
    im = Image.new('P', size, 0)
    palette = [int(c[i:i+2], 16) for c in COLORS for i in (1, 3, 5)]
    im.putpalette(palette + [0] * (768-len(palette)))
    return im, ImageDraw.Draw(im)

def dino(draw: ImageDraw.ImageDraw, x: int, y: int, unit: int = 3, phase: int = 0) -> None:
    """A tiny T. rex, with a planted foot, swinging tail and blink."""
    def rect(a,b,c,d,color):
        draw.rectangle((x+a*unit,y+b*unit,x+(c+1)*unit-1,y+(d+1)*unit-1),fill=color)
    lift = 1 if 10 <= phase < 22 else 0
    # Tail, back, neck and a broad, friendly snout.
    rect(0,15-lift,2,17-lift,9); rect(3,17-lift,5,20-lift,9)
    rect(6,18,10,22,4); rect(10,13,20,24,4)
    rect(16,5,23,20,4); rect(19,2,30,12,4); rect(22,4,33,10,4)
    rect(19,11,28,13,9); rect(12,21,20,24,9)
    rect(18,16,20,22,6); rect(21,16,24,17,4); rect(23,17,24,18,4)
    rect(22,5,23,6 if phase not in (34,35) else 5,0)
    rect(22,5,22,5,5 if phase not in (34,35) else 0)
    rect(31,6,31,6,0); rect(27,10,32,10,0); rect(28,11,28,11,5)
    rect(10,12,12,14,8); rect(13,9,15,11,8); rect(16,6,18,8,8)
    rect(11,24,14,27-lift,9); rect(10,27-lift,15,28-lift,9)
    rect(18,24,21,28,4); rect(18,28,24,29,4)
    rect(22,28,24,28,6)

def banner(index: int) -> Image.Image:
    """Render one frame of the README banner."""
    im, d = canvas((600,180))
    d.rectangle((8,8,591,171),outline=2); d.line((199,36,199,144),fill=2)
    d.rectangle((48,141,164,143),fill=2)
    dino(d,48,48,3,index)
    if 22 <= index < 30:
        radius = index-22
        for side in (-1,1):
            x=110+side*(12+radius*3)
            d.rectangle((x,137-radius//2,x+2,139-radius//2),fill=8 if radius<4 else 3)
    for n in range(12):
        x=30+(n*37)%145; y=24+(n*19)%105
        if x<48 or y<44: d.point((x,y),fill=4 if (index+n*5)%48<9 else 2)
    x=219
    for letter in 'dinostomp':
        for row,cells in enumerate(GLYPHS[letter]):
            for col,cell in enumerate(cells):
                if cell=='1': d.rectangle((x+col*3,48+row*3,x+col*3+2,50+row*3),fill=5)
        x+=18
    d.text((219,83),'Stomp the eval. Trust the evidence.',font=FONT,fill=6)
    d.text((219,110),'DATA  /  SCORERS  /  RUNS  /  CLAIMS',font=FONT,fill=4)
    for n in range(6):
        x=219+n*49
        d.line((x,138,x+39,138),fill=2)
        d.rectangle((x,135,x+5,141),fill=4 if n<=index//8 else 3)
    d.text((219,151),'Every boundary gets checked.',font=FONT,fill=7)
    return im.resize((1200,360),Image.Resampling.NEAREST)

def architecture() -> Image.Image:
    """Draw the six evidence boundaries and their checks."""
    im,d=canvas((600,425))
    d.rectangle((8,8,591,416),outline=2)
    d.text((26,24),'FOLLOW THE EVIDENCE',font=FONT,fill=4)
    d.text((26,44),'One pipeline. Checks at every boundary.',font=FONT,fill=6)
    stages=[('01  ITEMS','Duplicates, leakage, key bias'),
            ('02  RUNNER','Spend and coverage'),
            ('03  RECORDS','Integrity, truncation, engine drift'),
            ('04  SCORER','Witnesses and mutation tests'),
            ('05  AGGREGATE','Seed noise and prompt sensitivity'),
            ('06  CLAIM','Does the evidence support the claim?')]
    for n,(label,detail) in enumerate(stages):
        y=78+n*47
        if n < 5:
            d.line((47,y+15,47,y+58),fill=3)
        d.rectangle((29,y,66,y+34),fill=1)
        dino(d,31,y+2,1)
        d.text((85,y+2),label,font=FONT,fill=5)
        d.text((242,y+2),detail,font=FONT,fill=6)
        d.line((85,y+28,569,y+28),fill=2)
    d.text((26,377),'REPORT: findings + coverage + a scoped verdict',font=FONT,fill=4)
    d.text((26,397),'Mechanical integrity is not proof of construct validity.',font=FONT,fill=7)
    return im.resize((1200,850),Image.Resampling.NEAREST)

def main() -> None:
    """Rebuild the curated GIF and static README artwork."""
    OUT.mkdir(parents=True,exist_ok=True)
    frames=[banner(i) for i in range(FRAMES)]
    frames[0].save(OUT/(STEM+'_1200x360_s42.png'))
    frames[0].save(OUT/(STEM+'_1200x360_s42.gif'),save_all=True,
                   append_images=frames[1:],duration=80,loop=0,optimize=False,disposal=1)
    architecture().save(OUT/(STEM+'_architecture_1200x850_s42.png'))
    print('Rendered banner: 48 frames, 3.84-second loop; still and architecture PNGs.')

if __name__=='__main__':
    main()
