import os

def readFile(path: str) -> str:
    with open(path, "r") as f:
        return f.read()

def readAndParse(filename: str):
    info = {
        "format": "",
        "default_video_settings": {},
        "actions": []
    }
    content = readFile(filename).split("\n")
    actionContext = ""
    contextWindow = {}
    contextMode = False
    
    for i, line in enumerate(content, 1):
        line = line.strip()
        if not line: continue

        # End of block
        if line == "-":
            if not contextMode: raise ValueError(f"Line {i}: Tried to close nothing")
            if actionContext == "std_vid":
                info["default_video_settings"] = contextWindow
            else:
                contextWindow["command"] = actionContext
                info["actions"].append(contextWindow)
            
            actionContext = ""
            contextWindow = {}
            contextMode = False
            continue

        # Properties (Key Value)
        if line.startswith("|"):
            if not contextMode: raise ValueError(f"Line {i}: Context missing")
            
            # Split only on the first space to preserve spaces in text/paths
            parts = line.removeprefix("|").split(" ", 1)
            key = parts[0]
            val = parts[1].strip().strip('"') if len(parts) > 1 else ""
            contextWindow[key] = val

        # Commands
        if line.startswith(":"):
            parts = line.removeprefix(":").split(" ", 1)
            cmd = parts[0]
            
            if cmd == "format":
                info["format"] = parts[1]
            elif cmd == "standard_video_settings":
                actionContext = "std_vid"
                contextMode = True
            elif cmd == "new":
                # Handles 'new video' and 'new text'
                actionContext = "new_" + parts[1]
                contextMode = True
            elif cmd == "repeatforfiles":
                actionContext = "rff"
                contextMode = True

    return info