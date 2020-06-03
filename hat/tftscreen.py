import display
import time

class screen(object):
    def __init__(self):
        print('inmitit')
        self.width = 320
        self.height = 240
        self.bypp = 4

        self.tft = display.TFT()
        self.tft.init(self.tft.ST7789,bgr=False,rot=self.tft.PORTRAIT, miso=17,backl_pin=4,backl_on=1, mosi=19, clk=18, cs=5, dc=16)
        self.tft.setwin(52,40,240, 320)

    def refresh(self):
        pass
        
    def blit(self, surface, x, y, flip=False):
        pass
        
    def fill(self, color):
        self.tft.set_bg(color)
        self.tft.clear()

    def box(self, x1, y1, x2, y2, color):
        self.tft.rect(min(x1, x2), min(y1, y2), abs(x2-x1), abs(y2-y1), color, color)

    def invert(self, x1, y1, x2, y2):
        pass

    def putpixel(self, x, y, color):
        self.tft.pixel(x, y, color)

    def line(self, x1, y1, x2, y2, color):
        self.tft.line(x1, y1, x2, y2, color)

class dfont(object):
    def draw(self, surface, pos, text, size, bw, crop=False):
        return (0, 0)
        s.tft.font(s.tft.FONT_Comic, transparent=True, rotate=0)
        surface.tft.text(pos[0], pos[1], text)

font = dfont()


def main():
    s = screen()
    while(True):
        s.fill(0xffff00)
        time.sleep(.1)
        print('ok')
        
        s.fill(0xff0000)
        time.sleep(.1)
        Print('box')
        s.box(5, 5, 135-5, 240-5, 0x00ff00)
        s.line(0, 0, 100, 200, 0x0000ff)

        text="ST7789 with micropython!"
        #s.tft.font(s.tft.FONT_Comic, transparent=True, rotate=0)
        #s.tft.text(0,20,text,0xFFFFFF)        
        time.sleep(3)
        
if __name__ == '__main__':
    main()