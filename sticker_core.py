from PIL import Image, ImageDraw, ImageFilter
from io import BytesIO

class Dtelsticker(Image.Image):
    def __init__(self, pil_img):
        super().__init__()
        px = pil_img.load()
        self.__dict__ = pil_img.__dict__.copy()
        self.border_dots = []
        self.px = px
        self.new_size = None
        self.new_pos = None
        self.sides = [False, False, False, False]
    
    def __check_line_transparent(self, x_iter, y_iter):
        for x in x_iter:
            for y in y_iter:
                if self.px[x, y][3]:
                    return False
        return True
    
    def __check_pic_borders(self):
        width, height = self.size
        top = self.__check_line_transparent(range(width), [0])
        right = self.__check_line_transparent([-1], range(height))
        bottom = self.__check_line_transparent(range(width), [-1])
        left = right = self.__check_line_transparent([0], range(height))
        return (top, right, bottom, left)

    def __check_pixel(self, col, line):
        return (self.px[col    , line    ][3]) and not (
                self.px[col + 1, line    ][3] and
                self.px[col    , line + 1][3] and
                self.px[col - 1, line    ][3] and
                self.px[col    , line - 1][3])

    def __load_border_dots(self, lim):
        width, height = self.size
        width_lim = width - lim
        height_lim = height - lim
        for line in range(1, height - 1):
            for col in range(1, width - 1):
                if self.__check_pixel(col, line):
                    self.border_dots.append((col, line))
                    if line <= lim:
                        self.sides[0] = True
                    if col >= width_lim:
                        self.sides[1] = True
                    if line >= height_lim:
                        self.sides[2] = True
                    if col <= lim:
                        self.sides[3] = True
                        

    def __limit(self, num, limit):
        return (-limit if num < 0 else limit) if abs(num) > limit else num

    def __format_to_new(self, r, colour, blur):
        new_img = Image.new('RGBA', self.new_size, (255,255,255,0))
        draw = ImageDraw.Draw(new_img)
        for dot in self.border_dots:
            x, y = dot
            draw.ellipse((x - r, y - r, x + r, y + r), fill=colour)
        if blur:
            new_img = new_img.filter(ImageFilter.GaussianBlur(blur)) #or BoxBlur
        new_img.paste(self, self.new_pos, self)
        return Dtelsticker(new_img)
    
    def border(self, width, colour=(255,255,255,255), blur=0, pos=(0, 0)):
        if width >= 1 and self.mode == 'RGBA':
            width_r, height_r = self.size
            self.new_pos = (self.__limit(pos[0], width), self.__limit(pos[1], width))
            self.new_size = (width_r + self.new_pos[0], height_r + self.new_pos[1])
            self.__load_border_dots(width + blur)
            self = self.__format_to_new(width, colour, blur)
        return self
    
    def sticker(self, size=(512, 512)):
        if size[0] >= 512 or size[1] >= 512 :
            size = (512, 512)
        self.thumbnail(size, resample=Image.ANTIALIAS)
        return Dtelsticker(self)
