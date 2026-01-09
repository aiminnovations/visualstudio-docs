import urllib.request
import time
import os

# Create a folder for the downloads so they don't clutter your main directory
folder_name = "wash_2d_zips"
if not os.path.exists(folder_name):
    os.makedirs(folder_name)

base_url = "https://static.case.law/wash-2d/"

# The page lists files from 1.zip to 187.zip
print("Starting download...")

for i in range(1, 188):
    file_name = f"{i}.zip"
    url = base_url + file_name
    save_path = os.path.join(folder_name, file_name)

    print(f"Downloading {file_name}...")
    try:
        # download the file
        urllib.request.urlretrieve(url, save_path)
    except Exception as e:
        print(f"Failed to download {file_name}: {e}")

    # Pause briefly to be polite to the server
    time.sleep(0.1)

print("All downloads finished!")
