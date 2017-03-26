from tkinter import *
from time import sleep
import numpy as np

from PIL import Image, ImageTk  # pip install image
import cv2  # pip install opencv-python


def create_window_image():
    root = Tk()
    root.minsize(width=300, height=300)

    panel = Label(image=None)
    panel.image = None
    panel.pack()

    return root, panel


def display_image(panel, image, max_width, max_height):
    image_width, image_height = image.size

    scaler = max(image_height / max_height, image_width / max_width)
    image_resized = image.resize((int(image_width / scaler), int(image_height / scaler)), Image.ANTIALIAS)

    image_tk = ImageTk.PhotoImage(image_resized)

    panel.configure(image=image_tk)
    panel.image = image_tk


def read_image(filename):
    # image = Image.open()

    image_cv = cv2.imread(filename)

    if image_cv is None:
        return None

    # swap channels
    image_cv2 = np.zeros_like(image_cv)
    image_cv2[:, :, 0] = image_cv[:, :, 2]
    image_cv2[:, :, 1] = image_cv[:, :, 1]
    image_cv2[:, :, 2] = image_cv[:, :, 0]

    image = Image.frombytes('RGB', (image_cv2.shape[1], image_cv2.shape[0]), image_cv2)

    return image

if __name__ == '__main__':
    def on_quit():
        global need_break
        need_break = True


    max_width = 600
    max_height = 600

    root, panel = create_window_image()

    need_break = False
    root.protocol("WM_DELETE_WINDOW", on_quit)

    image = read_image('img.jpg')
    display_image(panel, image, max_width, max_height)

    # root.mainloop()

    while True:
        if need_break:
            break

        root.update()
        sleep(1)
