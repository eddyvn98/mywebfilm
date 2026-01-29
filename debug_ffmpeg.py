
import ffmpeg_service as ff
import os

video_path = r"C:\Users\hatha\Downloads\Video\Call sex với em teen dáng siêu ngon.mp4"
output_path = "debug_thumb.jpg"

print(f"Testing generation for: {video_path}")
print(f"Output to: {output_path}")

success = ff.generate_thumbnail(video_path, output_path)

if success:
    print("Success!")
else:
    print("Failed via module.")

# Check if file exists
if os.path.exists(output_path):
    print(f"File created, size: {os.path.getsize(output_path)}")
else:
    print("File not created.")
