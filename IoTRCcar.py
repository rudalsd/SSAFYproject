from Raspi_MotorHAT import Raspi_MotorHAT, Raspi_DCMotor
from Raspi_PWM_Servo_Driver import PWM
import mysql.connector
from threading import Timer, Lock
from time import sleep
import signal
import sys
from time import sleep
import datetime
import threading, requests
import cv2
import numpy as np
import math
import socket
import sys
    
a = False
flag  = 0
cap = cv2.VideoCapture("http://192.168.25.12:8090/?action=stream")

def ROI_img(img, vertices):

    mask = np.zeros_like(img)

    cv2.fillPoly(mask, vertices, [255, 255, 255])

    roi = cv2.bitwise_and(img, mask)

    return roi



def hough_line(img, rho, theta, threshold, min_line_len, max_line_gap):

    hough_lines = cv2.HoughLinesP(img, rho, theta, threshold, np.array([]), min_line_len, max_line_gap)

    background_img = np.zeros((img.shape[0], img.shape[1], 3), np.uint8)
    
    if(np.all(hough_lines) == True):
        draw_hough_lines(background_img, hough_lines)

    return background_img

degree_R = 0
degree_L = 0

def draw_hough_lines(img, lines, color=[0, 0, 255], thickness = 10):
    line_R = np.empty((0,5), int)
    line_L = np.empty((0,5), int)
    line_arr = np.empty((len(lines), 5), int)
    global degree_L
    global degree_R
    for i in range(0, len(lines)):
        temp = 0
        l = lines[i][0]
        line_arr[i] = np.append(lines[i], np.array((np.arctan2(l[1] - l[3], l[0] - l[2])*180)/np.pi))
        
        if line_arr[i][1] > line_arr[i][3]:
            temp = line_arr[i][0], line_arr[i][1]
            line_arr[i][0], line_arr[i][1] = line_arr[i][2], line_arr[i][3]
            line_arr[i][2], line_arr[i][3] = temp 

        if line_arr[i][0] > 320 and (abs(line_arr[i][4]) < 170 and abs(line_arr[i][4])>95):
            line_L = np.append(line_L, line_arr[i])
        elif line_arr[i][0] < 320 and (abs(line_arr[i][4]) <170 and abs(line_arr[i][4]) > 95):
            line_R = np.append(line_R, line_arr[i])
    line_L = line_L.reshape(int(len(line_L) /5), 5)
    line_R = line_R.reshape(int(len(line_R) /5), 5)
    
    
    try:
        line_L = line_L[line_L[:, 0].argsort()[-1]]
        degree_L = line_L[4]
        cv2.line(img, (line_L[0], line_L[1]), (line_L[2], line_L[3]), (255, 0, 0), 10, cv2.LINE_AA)
    except:
        degree_L = 0
    try:
        line_R = line_R[line_R[:, 0].argsort()[0]]
        degree_R = line_R[4]
        cv2.line(img, (line_L[0], line_L[1]), (line_L[2], line_L[3]), (255, 0, 0), 10, cv2.LINE_AA)
    except:
        degree_R = 0
    
    #print(degree_L, degree_R)
    r, l = degree_R, degree_L
    
    if abs(l) <=155 or abs(r) <= 155:
        if l == 0 and r == 0:
            servo.setPWM(0,0,397)
        elif l == 0 or r == 0:
            if l < 0 or r< 0:
                servo.setPWM(0,0,350)
                #print('left')
            elif l > 0 or r > 0:
                servo.setPWM(0,0,480)
                #print('right')
        elif abs(l+25) > abs(r):
            servo.setPWM(0,0,480)
            #print('right')
        elif abs(r-25) > abs(l):
            servo.setPWM(0,0,350)
            #print('left')
        else:
            servo.setPWM(0,0,397)
            print('go')

    else:
        if l > 155 or r> 155:
            servo.setPWM(0,0,480)
            print('hard right')
        elif l < -155 or r< -155:
            servo.setPWM(0,0,250)
            print('hard left')

def auto():
    global a
    flag = 0
    while True :
        while(a):
            flag = 1
            ret, frame = cap.read()
            if(ret):

                height, width = frame.shape[:2]

                img = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                img = cv2.GaussianBlur(img, (3, 3), 0)

                img = cv2.Canny(img, 70, 210)

                vertices = np.array([[(0, height), (50, 300), (590, 300), (640, height)]], np.int32)

                img = ROI_img(img, vertices)



                hough_lines = hough_line(img, 1, np.pi/180, 20, 10, 10)

        #cv2.imshow('hough', hough_lines)
        #cv2.imshow('img',img)
                img_new = cv2.add(frame, hough_lines)
        
                cv2.imshow('new',img_new)
        #cv2.imshow('img', img)
        
                if cv2.waitKey(1) & 0xFF == 27:
                    break     
        if(flag == 1):
            cap.release()

            cv2.destroyAllWindows()
            flag = 0
        
t1 = threading.Thread(target=auto)
t1.daemon = True
t1.start()

def closeDB(signal, frame):
    print("BYE")
    mh.getMotor(2).run(Raspi_MotorHAT.RELEASE)
    cur.close()
    db.close()
    timer.cancel()
    timer2.cancel()
    sys.exit(0)

def polling():
    global cur, db, ready
    
    lock.acquire()
    cur.execute("select * from command order by time desc limit 1")
    for (id, time, cmd_string, arg_string, is_finish) in cur:
        if is_finish == 1 : break
        ready = (cmd_string, arg_string)
        cur.execute("update command set is_finish=1 where is_finish=0")

    db.commit()
    lock.release()
     
    global timer
    timer = Timer(0.1, polling)
    timer.start()

def sensing():
    global cur, db, sense, degree_R, degree_L

    time = datetime.datetime.now()
    num1 = str(degree_L)
    num2 = degree_R
    num3 = "1"
    meta_string = '0|0|0'
    is_finish = 0

    #print(num1, num2, num3)
    query = "insert into sensing(time, num1, num2, num3, meta_string, is_finish) values (%s, %s, %s, %s, %s, %s)"
    #value = (time, num1, num2, num3, meta_string, is_finish)

    lock.acquire()
    #cur.execute(query, value)
    db.commit()
    lock.release()

    global timer2
    timer2 = Timer(1, sensing)
    timer2.start()

def go():
    myMotor.setSpeed(80)
    myMotor.run(Raspi_MotorHAT.FORWARD)

def back():
    myMotor.setSpeed(200)
    myMotor.run(Raspi_MotorHAT.BACKWARD)

def stop():
    myMotor.setSpeed(200)
    myMotor.run(Raspi_MotorHAT.RELEASE)

def left():
    servo.setPWM(0, 0, 330)

def mid():
    servo.setPWM(0, 0, 370)

def right():
    servo.setPWM(0, 0, 440)

def switch():
    global a
    if(a == True):
        a = False
    else:
        a = True
#init
db = mysql.connector.connect(host='52.79.242.176', user='rudalsd', password='1', database='minDB', auth_plugin='mysql_native_password')
cur = db.cursor()
ready = None
timer = None

mh = Raspi_MotorHAT(addr=0x6f)
myMotor = mh.getMotor(2)
servo = PWM(0x6F)
servo.setPWMFreq(60)

timer2 = None
lock = Lock()

signal.signal(signal.SIGINT, closeDB)
polling()
sensing()

#main thread
while True:
    sleep(0.1)
    if ready == None : continue
    
    cmd, arg = ready
    ready = None
    print(cmd)

    if cmd == "go" : go()
    if cmd == "back" : back()
    if cmd == "stop" : stop()
    if cmd == "left" : left()
    if cmd == "mid" : mid()
    if cmd == "right" : right()
    if cmd == "switch" : switch()
