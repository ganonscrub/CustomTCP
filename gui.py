from tkinter import *
from time import sleep

from PIL import Image, ImageTk # pip install image
import cv2 # pip install opencv-python

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


if __name__ == '__main__':
    def on_quit():
        global need_break
        need_break = True

    max_width = 600
    max_height = 600

    root, panel = create_window_image()

    need_break = False
    root.protocol("WM_DELETE_WINDOW", on_quit)

    # image = Image.open('img.jpg')
    image_cv = cv2.imread('img.jpg')
    image = Image.frombytes('RGB', (image_cv.shape[1],image_cv.shape[0]), image_cv)
    display_image(panel, image, max_width, max_height)

    # root.mainloop()

    while True:
        if need_break:
            break

        root.update()
        sleep(1)

