# Import the necessary packages
import argparse
import datetime
import time
import tkinter as tk
from typing import Union

import cv2
import imutils
import numpy as np
from imutils.video import VideoStream, FPS
from gpiozero import LED, Buzzer

blueLED = LED(17)
redLED = LED(27)
greenLED = LED(22)
buzzer = Buzzer(10)

# Construct the argument parse and parse the arguments
ap = argparse.ArgumentParser(description="Detect objects in a real time video stream")
ap.add_argument(
    "-p", "--prototxt", required=True, help="path to Caffe 'deploy' prototxt file"
)
ap.add_argument("-m", "--model", required=True, help="path to Caffe pre-trained model")
ap.add_argument(
    "-c",
    "--confidence",
    type=float,
    default=0.2,
    help="minimum probability to filter weak detections",
)
args = vars(ap.parse_args())

# Initialize the list of class labels MobileNet SSD was trained to detect,
# then generate a set of bounding box colors for each class.
# CLASSES = ["background", "bottle", "bus", "car", "cat", "chair", "person", "laptop",
#            "keyboard", "cellphone"]
CLASSES = [
    "background",
    "aeroplane",
    "bicycle",
    "bird",
    "boat",
    "bottle",
    "bus",
    "car",
    "cat",
    "chair",
    "cow",
    "diningtable",
    "dog",
    "horse",
    "motorbike",
    "person",
    "pottedplant",
    "sheep",
    "sofa",
    "train",
    "tvmonitor",
]
CHOSEN_CLASSES = {"car", "person"}
COLORS = np.random.uniform(0, 255, size=(len(CLASSES), 3))

RED: np.ndarray = np.array([204, 22, 22], dtype=float)[::-1]
TEAL: np.ndarray = np.array([22, 161, 166], dtype=float)[::-1]

# Get the device screen resolution
root = tk.Tk()
screen_res = (root.winfo_screenwidth(), root.winfo_screenheight())

# Load our serialized model from disk.
print("[INFO] loading model...")
net = cv2.dnn.readNetFromCaffe(args["prototxt"], args["model"])

# Initialize the video stream, allow the camera sensor to warm up.
# And initialize the FPS counter.
print("[INFO] starting video stream...")
stream_url = "rtsp://192.168.0.176:554/11"

vs = VideoStream(stream_url).start()
# vs = VideoStream(src=0).start()
time.sleep(2.0)
fps = FPS().start()

greenLED.on()
last_detected: Union[datetime.datetime, None] = None

# Loop over the frames from the video stream
while True:

    # Grab the frame from the threaded video stream and resize it
    # to have a maximum width of 400 pixels
    frame = vs.read()
    frame = imutils.resize(frame, width=400)

    # Grab the frame dimensions and convert it to a blob
    (h, w) = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(
        cv2.resize(frame, (300, 300)), 0.007843, (300, 300), 127.5
    )

    # Pass the blob through the network and obtain the detections and
    # predictions.
    net.setInput(blob)
    detections = net.forward()

    # Turn off LEDs for new loop.
    blueLED.off()
    redLED.off()

    num_persons = 0
    num_cars = 0

    # Loop over the detections
    for i in np.arange(0, detections.shape[2]):
        # Extract the confidence (i.e. probability) associated with the
        # prediction.
        confidence = detections[0, 0, i, 2]

        # Filter out weak detections by ensuring the 'confidence' is greater
        # than the minimum confidence
        if confidence > args["confidence"]:
            # Extract the index of the class label from the 'detections', then
            # compute the (x, y)-coordinates of the bounding box for the object.
            idx = int(detections[0, 0, i, 1])
            # Skip if not in the list of desired object classes.
            if CLASSES[idx] not in CHOSEN_CLASSES:
                continue

            if CLASSES[idx] == "car":
                num_cars += 1
                border_color = RED
                redLED.on()

                # Limit buzzer to around 4 seconds of activation.
                if last_detected is None:
                    last_detected = datetime.datetime.now()
                else:
                    duration = datetime.datetime.now() - last_detected
                    if duration.seconds > 4:
                        buzzer.off()
                    else:
                        buzzer.on()

            elif CLASSES[idx] == "person":
                num_persons += 1
                border_color = TEAL
                blueLED.on()

            else:
                border_color = COLORS[idx]

            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")

            # Draw the prediction on the frame
            label = "{}: {:.2f}%".format(CLASSES[idx], confidence * 100)
            cv2.rectangle(frame, (startX, startY), (endX, endY), border_color, 2)
            y = startY - 15 if startY - 15 > 15 else startY + 15
            cv2.putText(
                frame,
                label,
                (startX, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                border_color,
                2,
            )

    # Reset the last detected variable if number of detections is zero for the frame.
    if num_cars == 0:
        last_detected = None
        buzzer.off()

    # Show the output frame
    frame = cv2.resize(frame, screen_res, cv2.INTER_LINEAR)
    cv2.namedWindow("Video", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty("Video", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    cv2.imshow("Video", frame)
    key = cv2.waitKey(1) & 0xFF

    # If the 'q' key was pressed, break from the loop
    if key == ord("q"):
        break

    # Update the FPS counter
    fps.update()

# Turn off the LEDs
blueLED.off()
redLED.off()
greenLED.off()
buzzer.off()

# Stop the timer and display FPS information
fps.stop()
print("[INFO] elapsed time: {:.2f}".format(fps.elapsed()))
print("[INFO] approx. FPS: {:.2f}".format(fps.fps()))

# Do a bit of cleanup
cv2.destroyAllWindows()
vs.stop()
