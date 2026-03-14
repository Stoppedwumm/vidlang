def readFile(path: str) -> str:
    content = ""
    with open(path, "r") as f:
        content = f.read()
    return content

def checkForLength(arr) -> bool: return len(arr) < 2

def readAndParse(filename: str):
    info = {
        "format": "",
        "default_video_settings": {

        },
        "actions": []
    }
    content = readFile(filename).split("\n")
    actionContext = ""
    contextWindow = {}
    contextMode = False
    i = 0
    for command in content:
        i+=1
        if command.strip() == "":
            continue
        c = command.strip().split(" ")
        print(c, contextMode)
        if c[0] == "-":
                if contextMode == False:
                    raise ValueError("Tried to close nothing")
                if actionContext == "std_vid":
                    info["default_video_settings"] = contextWindow
                else:
                    info["actions"].append(contextWindow)
                
                actionContext = ""
                contextWindow = {}
                contextMode = False
                continue
        if c[0].startswith("|"):
            if contextMode == False:
                raise ValueError("Trying to read context from nothing, line " + str(i))
            actualCommand = c[0].removeprefix("|")
            if actionContext == "std_vid" or actionContext == "new_video" or actionContext == "rff":
                contextWindow[actualCommand] = c[1]

        if c[0].startswith(":"):
            actualCommand = c[0].removeprefix(":")
            print(actualCommand)
            if actualCommand == "format":
                info["format"] = c[1]
            if actualCommand == "standard_video_settings":
                actionContext = "std_vid"
                contextMode = True
            if actualCommand == "new":
                actionContext = "new_" + c[1]
                contextMode = True
            if actualCommand == "repeatforfiles":
                actionContext = "rff"
                contextMode = True

    return info

if __name__ == "__main__":
    print(readAndParse("video.vidlang"))