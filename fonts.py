import os
def list_fonts():
    paths = ["/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts")]
    fonts = []
    for path in paths:
        if os.path.exists(path):
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.endswith((".ttf", ".otf")):
                        fonts.append(file)
    return sorted(set(fonts))

print(list_fonts()[:20]) # Print first 20 fonts