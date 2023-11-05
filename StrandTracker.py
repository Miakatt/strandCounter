import tkinter as tk
from tkinter import filedialog
import matplotlib.pyplot as plt
from matplotlib.patches import Arrow, Circle
from scipy import signal
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk
import os
import numpy as np
import cv2

class ImageViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Viewer")

        self.image_paths = []  # List to store image file paths
        self.current_image_index = 0  # Index of the currently displayed image
        self.threshold = 25
        self.strandCount = 0
        self.prev_peaks = 0
        self.noOfStrands = 6
        # cropping region of the subimage. Select one of the ropes to work on.
        self.top = 1800
        self.bottom = 2340
        # detect if user is clicking next (increment strand count) or previous (decrement strand count)
        self.direction_forward = True
        # create some space to hold images/subimages and binary images.
        self.image = []
        self.subimage = []
        self.binaryImage = []
        self.kernel = []
        self.slice = []
        self.marker_height = (self.bottom - self.top) // 2 + self.top
        self.marker_colors = ['red', 'orange', 'yellow', 'lime', 'blue', 'magenta']
        # Create "Open Folder" button to select a folder of images
        self.open_button = tk.Button(self.root, text="Open Folder", command=self.open_folder)
        self.open_button.pack()

        # Create "Previous" and "Next" buttons
        self.prev_button = tk.Button(self.root, text="Previous", command=self.previous_image)
        self.next_button = tk.Button(self.root, text="Next", command=self.next_image)
        self.prev_button.pack()
        self.next_button.pack()

        # Create a Matplotlib figure for displaying images
        self.fig, self.axs = plt.subplots(1,3)
        self.fig.set_figheight(10)
        self.fig.set_figwidth(20)
        for ax in self.axs:
            ax.axis('off')

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack()
        # create kernel
        self.createKernel()

    def open_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.image_paths = [os.path.join(folder_path, file) for file in os.listdir(folder_path) if file.lower().endswith(('.jpg', '.jpeg', '.png'))]
            if self.image_paths:
                self.current_image_index = 0

                self.display_image()

    def display_image(self):
        if self.image_paths:
            image_path = self.image_paths[self.current_image_index]
            self.image = plt.imread(image_path)
            #photo = ImageTk.PhotoImage(self.image)
            self.axs[2].clear()
            self.axs[1].clear()
            self.axs[1].imshow(self.image)
            if self.current_image_index>0:
                prev_image_path = self.image_paths[self.current_image_index-1]
                prev_image = Image.open(prev_image_path)
                self.axs[0].clear()
                filename = os.path.basename(prev_image_path)
                filename, _ = os.path.splitext(filename)
                self.axs[0].set_title('%s' % filename, color='orange')
                self.axs[0].imshow(prev_image)
                self.fig.subplots_adjust(wspace=0.01)
                # crop out cam1 image.
                self.cropImage()
                # greyscale and binarize.
                self.binarize()
                self.convolve()
                self.findPeaks()
            filename = os.path.basename(image_path)
            filename, _ = os.path.splitext(filename)
            self.axs[1].set_title('%s' % filename, color='orange')

            self.canvas.draw()

    def createKernel(self):
        # FIX THIS. NEEDS TO BE AUTOMATIC.
        self.kernel = np.zeros((83, 770))
        for x in np.arange(0, 200):
            y = np.round(0.4 * x, 0).astype(int)
            self.kernel[y, x:x + 10] = 1
            self.kernel[y, x + 555:x + 565] = 1
        self.axs[2].imshow(self.kernel)

    def cropImage(self):
        imgSize = np.shape(self.image)
        self.subimage = self.image[self.top:self.bottom, 0:imgSize[1]]
        self.subimage = cv2.GaussianBlur(self.subimage, (7, 7), 0)

    def binarize(self):
        greyScaleImage = cv2.cvtColor(self.subimage, cv2.COLOR_RGB2GRAY)
        self.binaryImage = greyScaleImage < self.threshold
   #    self.axs[2].imshow(self.binaryImage)

    def convolve(self):
        output = signal.fftconvolve(self.binaryImage[:, :-150], self.kernel, mode='same')
      #  self.axs[2].imshow(output)
        self.slice = output[300, :]
       # These are required in the evnet tha the strand appears at the
        # very edge of the frame to make sure a peak is formed.
        self.slice[0] = 0
        self.slice[-1] = 0

    def findPeaks(self):
        peaks, _ = signal.find_peaks(self.slice, height=300, width=20)
        self.axs[2].plot(self.slice)
        self.strandCounter(peaks)

    def strandCounter(self, current_peaks):
        if self.direction_forward == True:
            self.prev_peaks = len(current_peaks)
            for p in current_peaks:
                self.strandCount += 1
                if self.strandCount > self.noOfStrands:
                    self.strandCount = 1
                print("Forward ", self.strandCount)
                markers = Circle((p, self.marker_height), radius=15, color=self.marker_colors[self.strandCount - 1],
                                 fill=True)
                self.axs[1].add_patch(markers)
        elif self.direction_forward == False:
            for p in np.arange(0, self.prev_peaks+len(current_peaks)):
                self.strandCount = self.strandCount-1
                if self.strandCount < 1:
                    self.strandCount = self.noOfStrands
            self.prev_peaks = len(current_peaks)
            for p in current_peaks:
                self.strandCount += 1
                if self.strandCount > self.noOfStrands:
                    self.strandCount = 1
                print("Re-counting ", self.strandCount)
                markers = Circle((p, self.marker_height), radius=15, color=self.marker_colors[self.strandCount - 1],
                                 fill=True)
                self.axs[1].add_patch(markers)



    def next_image(self):
        self.direction_forward = True  # going forward. Increment strandCount
        if self.image_paths:
            self.current_image_index = (self.current_image_index + 1) % len(self.image_paths)
            self.display_image()

    def previous_image(self):
        self.direction_forward = False
        if self.image_paths:
            self.current_image_index = (self.current_image_index - 1) % len(self.image_paths)
            self.display_image()

if __name__ == "__main__":
    root = tk.Tk()
    viewer = ImageViewer(root)
    root.mainloop()
