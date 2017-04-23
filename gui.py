from tkinter import *
from time import sleep
import numpy as np

from PIL import Image, ImageTk  # pip install image
import cv2  # pip install opencv-python

global_root = None

def create_window(title=''):
	global global_root

	if global_root is None:
		global_root = Tk()
		global_root_text = Label(master=global_root,
								 text=''
									  'Two windows show FSM changes of the sender and the receiver correspondingly. '
									  '\nIn addition, the receiver\'s window shows the image in transfer progress.'
								 )
		global_root_text.pack()

	root = Toplevel()
	root.minsize(width=300, height=300)

	if title != '':
		panel_title = Label(master=root, text=title, font=("Helvetica", 20))
		panel_title.pack()

	panel_img = Label(master=root, image=None)
	panel_img.image = None
	panel_img.pack()

	scrollbar_fsm = Scrollbar(master=root)
	scrollbar_fsm.pack(side=RIGHT, fill=Y)

	panel_fsm = Listbox(master=root)
	panel_fsm.pack()

	panel_fsm.config(yscrollcommand=scrollbar_fsm.set)
	scrollbar_fsm.config(command=panel_fsm.yview)

	return root, panel_img, panel_fsm


def display_image(panel, img, max_width, max_height):
	image_width, image_height = img.size

	scaler = max(image_height / max_height, image_width / max_width)
	image_resized = img.resize((int(image_width / scaler), int(image_height / scaler)), Image.ANTIALIAS)

	image_tk = ImageTk.PhotoImage(image_resized)

	panel.configure(image=image_tk)
	panel.image = image_tk


def update_fsm(panel, new_state):
	text = '-> {}'.format(new_state)
	panel.insert(0, text)
	# panel.configure(text=text)


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

	root_1, panel_img_1, panel_fsm_1 = create_window('test 1')
	root_2, panel_img_2, panel_fsm_2 = create_window('test 2')

	need_break = False
	root_1.protocol("WM_DELETE_WINDOW", on_quit)

	image = read_image('image.bmp')
	display_image(panel_img_1, image, max_width, max_height)
	display_image(panel_img_2, image, max_width, max_height)

	# root.mainloop()

	i = 0
	while True:
		if need_break:
			break

		update_fsm(panel_fsm_1, 'Test 1 {}'.format(i))
		update_fsm(panel_fsm_2, 'Test 2 {}'.format(i))

		root_1.update()
		root_2.update()
		sleep(1)
