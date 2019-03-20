from PIL import Image, ImageDraw, ImageFilter, ImageFont
import cairo
import math
import os
import unicodedata
    
class Station:
    def __init__(self, key, zhName, enName, namePos, angle, lineNum, color="black", outline="white", thickness=0, interchange=None):
        self.__key = key
        self.__zhName = zhName
        self.__enName = enName
        self.__namePos = namePos
        self.__angle = angle
        self.__lineNum = lineNum
        self.__color = color
        self.__outline = outline
        self.__thickness = thickness
        self.__interchange = interchange
        
    def generate(self):
        circlePath, centerPoints = self.__createCircle(self.__angle, self.__lineNum)
        nameList = self.__createName(self.__zhName, self.__enName, self.__namePos, self.__color, self.__outline, self.__thickness)
        
        self.__mergeImage(Image.open(circlePath), nameList)
        
    def __from_pil(self, im, alpha=1.0, format=cairo.FORMAT_ARGB32):
        """
        :param im: Pillow Image
        :param alpha: 0..1 alpha to add to non-alpha images
        :param format: Pixel format for output surface
        """
        assert format in (cairo.FORMAT_RGB24, cairo.FORMAT_ARGB32), "Unsupported pixel format: %s" % format
        if 'A' not in im.getbands():
            im.putalpha(int(alpha * 256.))
        arr = bytearray(im.tobytes('raw', 'BGRa'))
        surface = cairo.ImageSurface.create_for_data(arr, format, im.width, im.height)
        return surface
        
    # str (path to the png), list (centre point for line)
    def __createCircle(self, angle, lineNum):
        assert type(angle) is int or type(angle) is float, "not int ot float"
        assert type(lineNum) is int, "not int"
        assert lineNum > 0, "line number must greater than 0"
        assert 0 <= angle < 180, "angle must be greater or equal than 0, and less than 180"
        
        x = 115 * (lineNum-1) * math.cos( angle * math.pi / 180 )
        y = 115 * (lineNum-1) * math.sin( angle * math.pi / 180 )
        
        width, height = 205 + int(math.ceil(abs(x))),\
                        205 + int(math.ceil(abs(y)))

        im = Image.new("RGBA", (width, height))
        surface = self.__from_pil(im)
        ctx = cairo.Context(surface)
        
        radius = (102.5, 77.5)
        
        for i in range(len(radius)):
            
            """
            : CIRCLE SEGMENT
            """
            
            for d in (0,1):
                
                ctx.arc(
                    102.5 + x * d - x * int(angle>90),
                    102.5 + y * d,
                    radius[i],
                    0,
                    math.pi * 2
                )
            
                ctx.close_path()
                ctx.set_source_rgb(i,i,i)
                ctx.fill()
            
            """
            : EXTENDED RECTANGLE
            """
            
            ctx.move_to( 102.5 - x * int(angle>90), 102.5 )
            ctx.line_to(
                102.5 + x - x * int(angle>90),
                102.5 + y
            )
            ctx.set_source_rgb(i,i,i)
            ctx.set_line_width(radius[i]*2)
            ctx.stroke()
            
        """
        : CALCULATE CENTRE POINT(S) FOR LINES
        """
        
        diff = (
            115 * math.cos( angle * math.pi / 180 ),
            115 * math.sin( angle * math.pi / 180 )
        )
        
        center = []
        
        for i in range(lineNum):
            center.append((
                float("{0:.5f}".format(
                    102.5 + x - x * int(angle>90) - diff[0] * (i)
                )),
                float("{0:.5f}".format(
                    102.5 + y - diff[1] * (i)
                ))
            ))
        
        path = "result/temp_circle.png"
        surface.write_to_png(path)
        return path, center[::-1]
        
    # list (of Image)
    def __createName(self, zhName, enName, namePos, color="black", outline="white", thickness=4):
        
        assert not ("E"  in namePos and "W"  in namePos) and not ("N"  in namePos and "S"  in namePos), "invalid position"
        
        name = [zhName, enName]
        png_list = []
        
        for d in range(len(name)):
            line = name[d].count("\n")+1
            size = (67 + 14 if d else 147 + 32) * 1.1 / line
            font = ImageFont.truetype(
                font='font/FreeSansBold.ttf' if d else 'font/SourceHanSerifTC-Bold.otf',
                size=int(size)
            )
            name_list = name[d].split("\n")
            
            maxWidth, maxHeight = 0, 0
            zhAve = []
            lineWidth = []
            for i in range(line):
            
                charWidth = [unicodedata.east_asian_width(char) for char in name_list[i]]
            
                w, h = ImageDraw.Draw(Image.new("RGBA",(1,1))).textsize(
                           name_list[i],
                           font=font
                       )
                w1, h1 = ImageDraw.Draw(Image.new("RGBA",(1,1))).textsize(
                           "hg",
                           font=font
                       )
                if w > maxWidth: maxWidth = w
                if h > maxHeight: maxHeight = h
                if h1 > maxHeight and d: maxHeight = h1
                if "Na" not in charWidth:
                    zhAve.append(w/len(name_list[i]))
                    lineWidth.append(1)
                else:
                    lineWidth.append(0)
                
            if zhAve: zhAve = sum(zhAve)/len(zhAve)
            else: zhAve = 0
                
            """
            : maxWidth indicates the width for every line of the text
            : maxHeight indicates the height for every line of the text
            : zhAve indicates the average value of East Asian character appeared; not include text that have non E.A. character
            : lineWidth[i] indicates whether there are non E.A. character in the text, used for aligning
            """
            
            width = maxWidth + thickness*2
            height = maxHeight * line + thickness*2
            
            png = Image.new("RGBA", (width, height))
            png_draw = ImageDraw.Draw(png)
            
            x = math.ceil(maxWidth/2)+thickness
            y = math.ceil(maxHeight/2)+thickness
            
            for i in range(line):
            
                w, h = ImageDraw.Draw(Image.new("RGBA",(1,1))).textsize(
                    name_list[i],
                    font=font
                )
                
                x1 = x - (
                         (w * int(d or not lineWidth[i]) + zhAve * len(name_list[i]) * lineWidth[i]) * int("W" in namePos or ("S" in namePos or "N" in namePos) and not ("E" in namePos))
                     ) / (
                         1 + int(("S" in namePos or "N" in namePos) and not ("W" in namePos))
                     ) + (
                         (x - thickness) * int("W" in namePos)
                     ) - (
                         (x - thickness) * int("E" in namePos)
                     )
                     
                for j in range(-thickness,thickness+1,1):
                    for k in range(-thickness,thickness+1,1):
                        png_draw.text(
                            (
                                x1 + j,
                                i * maxHeight + k
                            ),
                            text=name_list[i],
                            font=font, fill=outline
                        )
            
                png_draw.text(
                    (
                        x1,
                        i * maxHeight
                    ),
                    text=name_list[i],
                    font=font, fill=color
                )
            
            #png.save("result/__station__{0}__{1}.png".format(self.__key, "en" if d else "zh"))
            png_list.append(png)
            
        return png_list
        
    # centre point(s) of station circle (save as png)
    def __mergeImage(self, station, name, interchange=None):
        
        station_w, station_h = station.size
        zhname_w, zhname_h = name[0].size
        enname_w, enname_h = name[1].size
        
        hd = 20 # Horizontal difference
        
        if "N" in self.__namePos or "S" in self.__namePos:
            imageHeight = station_h + zhname_h + enname_h
        else:
            imageHeight = max(station_h, zhname_h + enname_h)
        if "E" in self.__namePos or "W" in self.__namePos:
            imageWidth = station_w + max(zhname_w, enname_w) + hd
        else:
            imageWidth = max(station_w, zhname_w, enname_w)
        
        im = Image.new("RGBA", (imageWidth, imageHeight))
        
        #"""
        if "N" in self.__namePos or "S" in self.__namePos:
            station_x = imageWidth//2 - station_w//2
            zhname_x = imageWidth//2 - zhname_w//2
            enname_x = imageWidth//2 - enname_w//2
        if "E" in self.__namePos:
            station_x = 0
            zhname_x = station_w + hd
            enname_x = station_w + hd
        if "W" in self.__namePos:
            station_x = imageWidth - station_w
            zhname_x = imageWidth - station_w - hd - zhname_w
            enname_x = imageWidth - station_w - hd - enname_w
        if "E" in self.__namePos or "W" in self.__namePos:
            station_y = imageHeight//2 - station_h//2
            zhname_y = 0
            enname_y = zhname_h
        if "S" in self.__namePos:
            station_y = 0
            zhname_y = station_h
            enname_y = station_h + zhname_h
        if "N" in self.__namePos:
            station_y = enname_h + zhname_h
            zhname_y = 0
            enname_y = zhname_h
            
        im.paste(station, (station_x, station_y))
        im.paste(name[0], (zhname_x, zhname_y))
        im.paste(name[1], (enname_x, enname_y))
        
        im.save("result/__station__{0}.png".format(self.__key))
        
        os.remove("result/temp_circle.png")
        
class Interchange:
    def __init__(self, key, zhName, enName, lineColor, textColor="black", outline="white"):
        self.key = key
        self.zhName = zhName
        self.enName = enName
        self.lineColor = lineColor
        self.textColor = textColor
        self.outline = outline
        
class Interchanges:
    def __init__(self, interchange_list=[], direction="N", thickness=0):
        self.__list = interchange_list
        self.__direction = direction
        self.__thickness = thickness
        
    def generate(self):
        interchangePath = self.__createInterchange(self.__list, self.__direction, self.__thickness)
        
    def __from_pil(self, im, alpha=1.0, format=cairo.FORMAT_ARGB32):
        """
        :param im: Pillow Image
        :param alpha: 0..1 alpha to add to non-alpha images
        :param format: Pixel format for output surface
        """
        assert format in (cairo.FORMAT_RGB24, cairo.FORMAT_ARGB32), "Unsupported pixel format: %s" % format
        if 'A' not in im.getbands():
            im.putalpha(int(alpha * 256.))
        arr = bytearray(im.tobytes('raw', 'BGRa'))
        surface = cairo.ImageSurface.create_for_data(arr, format, im.width, im.height)
        return surface
    
    # str (path to the png)
    def __createInterchange(self, list, direction="N", thickness=0):
        assert type(direction) is str, "must be str"
        assert direction in ("N", "E", "W", "S"), "must be 'N', 'S', 'E' or 'W'"
        
        path = "result/temp_line.png"
        
        if direction in ("N", "S"):
            maxWidth = 0
            for i in list:
                for d in (0, 1):
                    size = (53 + 18 if d else 67 + 21) * 1.1
                    font = ImageFont.truetype(
                        font='font/FreeSansBold.ttf' if d else 'font/SourceHanSerifTC-Bold.otf',
                        size=int(size)
                    )
                
                    w, h = ImageDraw.Draw(Image.new("RGBA",(1,1))).textsize(
                        i.enName if d else i.zhName,
                        font=font
                    )
                    
                    if w > maxWidth: maxWidth = w
        
            width, height = 41+(maxWidth+thickness)*2, 122*len(list)
            
            png = Image.new( "RGBA", (width, height) )
            png_draw = ImageDraw.Draw(png)
            
            surface = self.__from_pil(png)
            ctx = cairo.Context(surface)
            
            for i in range(len(list)):
                ctx.move_to(width/2, 122*len(list))
                ctx.line_to(width/2, 122*len(list) - 122*(len(list)-i))
                ctx.set_source_rgb(
                    int(list[i].lineColor[0:2],16)/255,
                    int(list[i].lineColor[2:4],16)/255,
                    int(list[i].lineColor[4:6],16)/255
                )
                ctx.set_line_width(41)
                ctx.stroke()
                
            surface.write_to_png(path)
            png2 = Image.open(path)
            
            for d in (0, 1):
                size = (53 + 18 if d else 67 + 21)
                font = ImageFont.truetype(
                    font='font/FreeSansBold.ttf' if d else 'font/SourceHanSerifTC-Bold.otf',
                    size=size
                )
            
                for i in range(len(list)):
                    w, h = ImageDraw.Draw(Image.new("RGBA",(1,1))).textsize(
                        list[i].zhName,
                        font=font
                    )
                    w1, h1 = ImageDraw.Draw(Image.new("RGBA",(1,1))).textsize(
                        "hg",
                        font=font
                    )
                    
                    x = width/2 + 41/2 * (2*d-1) + w * (d-1) + (20 * (2*d-1)) + 2 * (d-1)
                    y = height/2 - h1/2 * d + h/2 * (d-1) + 12 * (d-1)
                                            
                    for j in range(-thickness,thickness+1,1):
                        for k in range(-thickness,thickness+1,1):
                            png_draw.text(
                                (
                                    x + j,
                                    y + 122 * i - ( 122*(len(list)-1) - 122*(len(list)-1)/2) + k
                                ),
                                text=list[i].enName if d else list[i].zhName,
                                font=font, fill=list[i].outline
                            )
                    
                    png_draw.text(
                        (
                            x,
                            y + 122 * i - ( 122*(len(list)-1) - 122*(len(list)-1)/2)
                        ),
                        text=list[i].enName if d else list[i].zhName,
                        font=font, fill=list[i].textColor
                    )
                
            png.alpha_composite(png2)
            png.save("result/__interchange.png".format(list[i].key, d))
                    
        else:
            pass
            
        os.remove(path)