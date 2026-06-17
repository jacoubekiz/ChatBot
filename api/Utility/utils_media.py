import os
import requests


def download_and_save_image(image_url, headers, save_directory, image_name):
    """
    Downloads an image from a URL and saves it to a specified directory on the server.

    :param image_url: URL of the image to download.
    :param save_directory: Directory where the image will be saved.
    :return: Full path to the saved image.
    """
    full_path = os.path.join(save_directory, image_name)
    response = requests.get(image_url, headers=headers, stream=True)
    if response.status_code == 200:
        with open(full_path, 'wb') as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)
        return full_path
    else:
        raise Exception(f"Failed to download image. Status code: {response.status_code}")
