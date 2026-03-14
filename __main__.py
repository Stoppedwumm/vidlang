import os
import re
import traceback
import textwrap

# Handle MoviePy v1 vs v2 imports
try:
    from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, concatenate_videoclips
except ImportError:
    from moviepy import VideoFileClip, TextClip, CompositeVideoClip, concatenate_videoclips

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]

class AutoVideoEditor:
    def __init__(self, config_file):
        from parser import readAndParse
        self.config = readAndParse(config_file)
        self.target_width, self.target_height = self._get_dimensions(self.config['format'])
        print(f"Target Resolution: {self.target_width}x{self.target_height}")
        self.clips = []

    def _get_dimensions(self, fmt):
        if fmt == '9x16': return (1080, 1920)
        if fmt == '16x9': return (1920, 1080)
        return (1080, 1080)

    def _call(self, clip, method_name, *args, **kwargs):
        for prefix in ["with_", "set_"]:
            full_name = f"{prefix}{method_name}"
            if hasattr(clip, full_name):
                return getattr(clip, full_name)(*args, **kwargs)
        if method_name == "resize":
            if hasattr(clip, "resized"): return clip.resized(*args, **kwargs)
            if hasattr(clip, "resize"): return clip.resize(*args, **kwargs)
        return getattr(clip, method_name)(*args, **kwargs)

    def _process_sizing(self, clip, width_pref, height_pref):
        tw, th = self.target_width, self.target_height
        target_w = int(tw * float(width_pref.replace('%',''))/100) if '%' in str(width_pref) else None
        target_h = int(th * float(height_pref.replace('%',''))/100) if '%' in str(height_pref) else None
        if width_pref == 'auto' and height_pref == 'auto': 
            return self._call(clip, "resize", width=int(tw))
        if target_w and height_pref == 'auto': 
            return self._call(clip, "resize", width=int(target_w))
        if target_h and width_pref == 'auto': 
            return self._call(clip, "resize", height=int(target_h))
        return self._call(clip, "resize", newsize=(int(target_w or tw), int(target_h or th)))

    def create_video_segment(self, video_path, action_settings):
        try:
            print(f"  > Video: {video_path}")
            raw_clip = VideoFileClip(video_path)
            defaults = self.config['default_video_settings']
            width = action_settings.get('width', defaults.get('width', '100%'))
            height = action_settings.get('height', defaults.get('height', 'auto'))
            pos = action_settings.get('pos', defaults.get('pos', 'center'))

            resized_clip = self._process_sizing(raw_clip, width, height)
            positioned_clip = self._call(resized_clip, "position", pos)

            final_segment = CompositeVideoClip([positioned_clip], size=(int(self.target_width), int(self.target_height)))
            return self._call(final_segment, "duration", raw_clip.duration)
        except Exception as e:
            print(f"Error processing {video_path}: {e}")
            return None

    def create_text_overlay(self, settings):
        """Creates each line on a forced tall canvas to prevent clipping."""
        if not self.clips: return

        raw_text = settings.get('text', '')
        print(f"  > Text Overlay: {raw_text}")
        
        lines = textwrap.wrap(raw_text, width=18) 
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        
        font_size = 70
        line_spacing_gap = 140 # The vertical distance between lines
        
        total_text_height = len(lines) * line_spacing_gap
        text_pos_key = settings.get('text_pos', 'center')
        
        if text_pos_key == "up_center":
            base_y = 200
        elif text_pos_key == "down_center":
            base_y = self.target_height - total_text_height - 300
        else:
            base_y = (self.target_height - total_text_height) // 2

        new_line_clips = []
        for i, line_text in enumerate(lines):
            # KEY FIX: We use method='caption' and size=(width, 160)
            # This FORCES the line to have a 160px high box, 
            # ensuring the font + stroke cannot be cut off.
            l_clip = TextClip(
                text=line_text,
                font_size=font_size,
                color='white',
                font=font_path,
                stroke_color='black',
                stroke_width=2,
                method='caption',
                text_align='center',
                size=(int(self.target_width), 160) 
            )
            
            # Position the line. We subtract a bit from y to account for the 160px box height
            y_pos = int(base_y + (i * line_spacing_gap))
            l_clip = self._call(l_clip, "position", ("center", y_pos))
            l_clip = self._call(l_clip, "duration", self.clips[-1].duration)
            new_line_clips.append(l_clip)

        # Flat composite to avoid ValueError broadcast issues
        self.clips[-1] = CompositeVideoClip(
            [self.clips[-1]] + new_line_clips, 
            size=(int(self.target_width), int(self.target_height))
        )

    def build(self, output_filename="final_video.mp4"):
        for action in self.config['actions']:
            cmd = action['command']
            path = action.get('path', '')
            if cmd == 'new_video':
                clip = self.create_video_segment(path, action)
                if clip: self.clips.append(clip)
            elif cmd == 'new_text':
                self.create_text_overlay(action)
            elif cmd == 'rff':
                if os.path.isdir(path):
                    files = sorted([os.path.join(path, f) for f in os.listdir(path) 
                             if f.lower().endswith(('.mp4', '.mov', '.mkv', '.mov'))], key=natural_sort_key)
                    for f in files:
                        clip = self.create_video_segment(f, action)
                        if clip: self.clips.append(clip)

        if self.clips:
            print(f"Concatenating {len(self.clips)} segments...")
            final_video = concatenate_videoclips(self.clips, method="compose")
            print(f"Writing file: {output_filename}")
            final_video.write_videofile(output_filename, fps=30, codec="libx264", audio_codec="aac")
        else:
            print("No clips to process.")

if __name__ == "__main__":
    editor = AutoVideoEditor("video.vidlang") 
    editor.build("output.mp4")