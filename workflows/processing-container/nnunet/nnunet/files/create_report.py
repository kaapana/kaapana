import os
import sys
import glob
import pathlib
import shutil
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
from datetime import datetime

args_got = sys.argv[1:]
if (len(args_got) != 2):
    print("# Arg0: experiment_path")
    print("# Arg1: target_path")
    print("# GOT: ")
    print(args_got)
    print("# -> exit")
    exit(1)
else:
    experiment_path = args_got[0]
    target_path = args_got[1]

print("# ")
print("# Starting export report...")
print("# ")
print(f"# experiment_path: {experiment_path}")
print(f"# target_path: {target_path}")
print("# ")

pathlib.Path(target_path).mkdir(parents=True, exist_ok=True)
progress_images_list = sorted(glob.glob(os.path.join(experiment_path,"**","progress.png"),recursive=True))

timestamp = datetime.now().strftime("%d_%m_%Y")
print(f"# 'progress.png'-list: {progress_images_list} ")
print(f"# Timestamp: {timestamp}")

# font = ImageFont.truetype("sans-serif.ttf", 16)
# img = Image.new('RGB', (0, 400), color = 'white')

im_list=[]
for image_path in progress_images_list:
    img_filename=os.path.basename(image_path)
    rgba = Image.open(image_path)
    rgb = Image.new('RGB', rgba.size, (255, 255, 255))  # white background
    rgb.paste(rgba, mask=rgba.split()[3])  
    draw = ImageDraw.Draw(rgb)
    draw.text((0, 0),f"Report: {img_filename}",(0,0,0))#,font=font)
    im_list.append(rgb)

pdf1_filename = os.path.join(target_path, f'nnunet_report_{timestamp}.pdf')

print(f"# Save report pdf at: {pdf1_filename}")
im_list[0].save(pdf1_filename, "PDF" ,resolution=100.0, save_all=True, append_images=im_list[1:])
print("# saved report.")

