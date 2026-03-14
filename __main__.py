import os
import re
import traceback

# Handle MoviePy v1 vs v2 imports
try:
    from moviepy.editor import VideoFileClip, concatenate_videoclips, CompositeVideoClip
except ImportError:
    from moviepy import VideoFileClip, concatenate_videoclips, CompositeVideoClip

def natural_sort_key(s):
    """Sorts strings numerically: 1.mp4, 2.mp4, 10.mp4"""
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]

class AutoVideoEditor:
    def __init__(self, config_file):
        from parser import readAndParse
        self.config = readAndParse(config_file)
        
        # Strictly define dimensions based on format
        self.target_width, self.target_height = self._get_dimensions(self.config['format'])
        print(f"Target Resolution: {self.target_width}x{self.target_height}")
        self.clips = []

    def _get_dimensions(self, fmt):
        """Standard resolutions for vertical/horizontal"""
        if fmt == '9x16': return (1080, 1920)
        if fmt == '16x9': return (1920, 1080)
        return (1080, 1080)

    def _apply_resize(self, clip, **kwargs):
        """Compatibility for MoviePy v1 (resize) and v2 (resized)"""
        if hasattr(clip, "resized"):
            return clip.resized(**kwargs)
        return clip.resize(**kwargs)

    def _process_sizing(self, clip, width_pref, height_pref):
        """Calculates pixels based on % strings and target resolution."""
        target_w = None
        target_h = None

        if "%" in str(width_pref):
            percent = float(width_pref.replace('%', '')) / 100
            target_w = int(self.target_width * percent)
        
        if "%" in str(height_pref):
            percent = float(height_pref.replace('%', '')) / 100
            target_h = int(self.target_height * percent)

        # Apply resizing logic
        if width_pref == 'auto' and height_pref == 'auto':
            return self._apply_resize(clip, width=self.target_width)
        
        if target_w and height_pref == 'auto':
            return self._apply_resize(clip, width=target_w)
        elif target_h and width_pref == 'auto':
            return self._apply_resize(clip, height=target_h)
        else:
            w = target_w or self.target_width
            h = target_h or self.target_height
            return self._apply_resize(clip, newsize=(w, h))

    def create_clip(self, video_path, action_settings):
        """Loads, resizes, and centers a clip on a fixed-size canvas."""
        try:
            print(f"  > Processing: {video_path}")
            raw_clip = VideoFileClip(video_path)
            
            # 1. Get Settings (Use action specific or global default)
            defaults = self.config['default_video_settings']
            width = action_settings.get('width', defaults['width'])
            height = action_settings.get('height', defaults['height'])
            pos = action_settings.get('pos', defaults['pos'])

            # 2. Resize the actual video source
            resized_clip = self._process_sizing(raw_clip, width, height)

            # 3. Position the clip
            pos_func = "with_position" if hasattr(resized_clip, "with_position") else "set_position"
            positioned_clip = getattr(resized_clip, pos_func)(pos)

            # 4. KEY FIX: Wrap the clip in a CompositeVideoClip of the TARGET size.
            # This 'crops' the 130% width video to the 1080x1920 frame.
            final_segment = CompositeVideoClip(
                [positioned_clip], 
                size=(self.target_width, self.target_height)
            ).with_duration(resized_clip.duration)

            return final_segment
            
        except Exception as e:
            print(f"Error processing {video_path}: {e}")
            traceback.print_exc()
            return None

    def build(self, output_filename="output.mp4"):
        for action in self.config['actions']:
            command = action['command']
            path = action['path']

            if command == 'new_video':
                clip = self.create_clip(path, action)
                if clip: self.clips.append(clip)

            elif command == 'rff':
                if os.path.isdir(path):
                    files = [os.path.join(path, f) for f in os.listdir(path) 
                             if f.lower().endswith(('.mp4', '.mov', '.mkv'))]
                    files.sort(key=natural_sort_key)
                    for f in files:
                        # Pass the 'action' dict so it uses settings like 'pos' for every file
                        clip = self.create_clip(f, action)
                        if clip: self.clips.append(clip)

        if self.clips:
            print(f"Concatenating {len(self.clips)} clips into vertical format...")
            # method="compose" is vital for keeping our Canvas settings
            final_video = concatenate_videoclips(self.clips, method="compose")
            
            final_video.write_videofile(
                output_filename, 
                fps=30, 
                codec="libx264", 
                audio_codec="aac",
                # Ensure the encoder knows the final size
                ffmpeg_params=["-vf", f"scale={self.target_width}:{self.target_height}"]
            )
        else:
            print("No clips found to process.")

if __name__ == "__main__":
    editor = AutoVideoEditor("video.vidlang") 
    editor.build("phone_video.mp4")