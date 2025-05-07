from moviepy.editor import VideoFileClip

# Path to your source video
source_video_path = ['D:\\data\\vlc\\VLC09\\VLC09_1.mp4']


# List of tuples containing start and end times for clips in seconds
time_segments = [
    (0, 45)
]

output_paths = ['D:\\data\\vlc\\VLC09\\VLC09.mp4']

# Function to trim video
def trim_video(source_path, start_time, end_time, output_filename):
    with VideoFileClip(source_path) as video:
        # Trim video
        trimmed_video = video.subclip(start_time, end_time)
        # Save video
        trimmed_video.write_videofile(output_filename, codec='libx264')

# Process each segment
for i in range(len(source_video_path)):
    output_path = output_paths[i]
    trim_video(source_video_path[i], time_segments[i][0], time_segments[i][1], output_path)
