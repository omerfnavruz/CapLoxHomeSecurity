import os
#from time import time
import cv2
import cv2.cv2
import numpy as np
import face_recognition
import RPi.GPIO as GPIO
from datetime import datetime
import time
from picamera.array import PiRGBArray
from picamera import PiCamera
import firebase_admin
import requests
from firebase_admin import db
import smtplib
#import datetime
import imghdr
from email.message import EmailMessage
#used to update mean and variance for anomaly algorithm
def mean_update(prevMean, curSamplesize, newSample):
    curMean = (prevMean*(curSamplesize-1)+newSample)/curSamplesize
    return curMean
def std_update(prevMean, prevStd, curSamplesize, newSample):
    curMean = mean_update(prevMean, curSamplesize,newSample)
    curStd = (curSamplesize-2)*prevStd*prevStd+(newSample-curMean)*(newSample-prevMean)
    curStd = curStd/(curSamplesize-1)
    curStd = np.sqrt(curStd)
    return curStd

def email_sender(receiverEmail, contentGeneral, subjectGeneral,captureForMail=0):
    emailSubject = ["ABSENT RESIDENT","STILL AT HOME","EARLY ARRIVAL","TOO MANY STRANGERS AT THE DOOR"]
    class mail:
        def __init__(self):
            self.EMAIL_ADDRESS='caploxinc@gmail.com'
            self.EMAIL_PASSWORD='CapLox123!'
            self.SMTP_SERVER = 'smtp.gmail.com'
            self.SMTP_PORT = 465
            self.receiverEmail =receiverEmail
        def send_mail(self,image):
            info = emailSubject[subjectGeneral]

            # Default value of capture for mail is zero
            if captureForMail != 0:
                cv2.imwrite("dummy.png", image)


            msg = EmailMessage()
            msg['Subject']=info
            msg['From'] = self.EMAIL_ADDRESS
            msg['To']=self.recieverEmail

            e = datetime.now()

            date1= e.strftime("%a, %b %d, %Y")
            date2= e.strftime("%I:%M:%S %p")
            date = date1+ '\n' + date2
            emailContent = 'Dear User,\nWe are sorry to inform you about a situtation.\n'
            emailContent += contentGeneral
            emailContent += 'Undesired situation happened at '+date
            msg.set_content(emailContent)
            if captureForMail != 0:
                with open("dummy.png",'rb') as f:
                    fileData=f.read()
                    fileType=imghdr.what(f.name)
                    fileName=f.name
                msg.add_attachment(fileData,maintype='image',subtype=fileType,filename=fileName)

            with smtplib.SMTP_SSL(self.SMTP_SERVER,self.SMTP_PORT) as smtp:
                smtp.login(self.EMAIL_ADDRESS,self.EMAIL_PASSWORD)
                smtp.send_message(msg)
    sender=mail()
    sender.send_mail(captureForMail)





databaseURL= "https://*****.europe-west1.firebasedatabase.app/"
cred_object = firebase_admin.credentials.Certificate('*****.json')
default_app = firebase_admin.initialize_app(cred_object, {'databaseURL':databaseURL})
residentsRef = db.reference("/Residents/")
guestsRef = db.reference("/Guests/")
flagsRef = db.reference("/Flags/")
logRef = db.reference("/Logging/")

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

TRIG = 23
ECHO = 24
BUTTON = 15
ratio = 0.01
ratio22 = 0.01
ratio2 = 0.7
multip = 1/ratio
recog = 0
recog2 = 0
incoming = 0
exiting = 0
isIntruder1 = 0
isIntruder2 = 0
GPIO.setup(TRIG,GPIO.OUT)
GPIO.setup(ECHO,GPIO.IN)
GPIO.setwarnings(False) # Ignore warning for now
GPIO.setup(BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # Set pin 10 to be an input pin and set initial value to be pulled low (off)
mailList[0] = "******@gmail.com"
door = 0
inside = 0
outside = 0
lognum = 0
enterlist = []
enterindex = []
exitlist = []
exitindex = []
preEntryList = []
preEntryIndex = []
preExitIndex = []
preExitList = []

log = {
	"time" : ' ',
	"name" : " ",
	"type" : " "
}


# initialize the camera and grab a reference to the raw camera capture
camera = PiCamera()
camera.resolution = (640, 480)
camera.framerate = 32
rawCapture = PiRGBArray(camera, size=(640, 480))
# allow the camera to warmup
time.sleep(0.1)
haar_cascade = cv2.CascadeClassifier('haarcascade_frontalface_alt.xml')
path = 'ImagesAttendance'

while 1:
    meanLogin  = []
    meanLogout = []
    stdLogin   = []
    stdLogout  = []
    sizeLogin  = []
    sizeLogout = []
    logState   = [] #0 means out, 1 means in
    anoState   = []
    mailList   = []
    residents = residentsRef.get()
    guests = guestsRef.get()
    for f in os.listdir(path):
        os.remove(os.path.join(path,f))

    for key in residents:
        residentRef = residentsRef.child(key)
        url = residentRef.child("Image URL").get()
        name = residentRef.child("Name").get()
        mailList.append(residentRef.child("email").get())
        stdLogin.append(residentRef.child("stdLogin").get())
        stdLogout.append(residentRef.child("stdLogout").get())
        sizeLogin.append(residentRef.child("sizeLogin").get())
        sizeLogout.append(residentRef.child("sizeLogout").get())
        logState.append(residentRef.child("isHome").get())
        fileName = "ImagesAttendance/" + name + ".jpg"
        img = requests.get(url).content
        with open(fileName, 'wb') as handler:
            handler.write(img)
    for key in guests:
        guestRef = guestsRef.child(key)
        url = guestRef.child("Image URL").get()
        name = guestRef.child("Name").get()
        fileName = "ImagesAttendance/" + name + ".jpg"
        img = requests.get(url).content
        with open(fileName, 'wb') as handler:
            handler.write(img)
    flagsRef.update({"Updated":"False"})
    isUpdated = flagsRef.child("Updated").get()
    images = []
    classNames = []
    myList = os.listdir(path)
    print((myList))
    for cl in myList:
        curImg = cv2.imread(f'{path}/{cl}')
        images.append(curImg)
        classNames.append(os.path.splitext(cl)[0])
    print(classNames)




    def findEncodings(images):
        encodeList = []
        for img in images:
            img = cv2.cvtColor(img,cv2.COLOR_BGR2RGB)
            encode = face_recognition.face_encodings(img)[0]
            encodeList.append(encode)
        return encodeList

    encodeListKnown = findEncodings(images)
    print('Encoding Finished')

    cap = cv2.VideoCapture('/dev/v4l/by-id/usb-046d_HD_Webcam_C615_0432EA50-video-index0')

    #debouncer = 0 #in each 60 seconds, time will be checked to determine anomaly

    for frame in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):

        checkTime = datetime.now()
        checkTime = checkTime.strftime('%d/%m/%Y %H:%M:%S')
        secTime = int(checkTime[17:19])
        minTime = int(checkTime[11:13])*60+int(checkTime[14:16])

        if(secTime < 11 and secTime > 0):
            for j in range(0,len(stdLogin)):
                if(minTime == np.round(meanLogin[j]+3*stdLogin[j]) and logState[j] == 0 and anoState[j] == 0):
                    anoState[j] = 1
                    #mail
                    email_sender(mailList[j],classNames[j]+" is still at outside",0)

                    print(classNames[j]+" is still at outside")
                elif(minTime == np.round(meanLogout[j]+3*stdLogout[j]) and logState[j] == 1 and anoState[j] == 0):
                    anoState[j] = 1
                    #mail
                    email_sender(mailList[j],classNames[j]+" is still at home",1)
                    print(classNames[j]+" is still at home")
        else:
            np.multiply(anoState,0)


        GPIO.output(TRIG, False)
        #time.sleep(0.5)

        if GPIO.input(BUTTON)==GPIO.HIGH: # if button is pressed
            #print('High')
            door = 0
        else:
            #print('Low')
            door = 1

        GPIO.output(TRIG, True)
        time.sleep(0.00001)
        GPIO.output(TRIG, False)

        while GPIO.input(ECHO)==0:
            pulse_start = time.time()

        while GPIO.input(ECHO)==1:
            pulse_end = time.time()

        pulse_duration = pulse_end - pulse_start

        distance = pulse_duration * 17150
        distance = round(distance, 2)

        if(distance < 10):
            outside = 1
            print("close \n")
        elif (distance >=12):
            outside = 0
        #if distance > 2 and distance < 400:
            #print("Mesafe:",distance - 0.5,"cm")
        #else:
        #    print("Menzil asildi")

        #startTime=time()
        succes, img = cap.read()
        img2 = frame.array
        imgS =  cv2.resize(img,(0,0),None,ratio,ratio)
        imgS2 =  cv2.resize(img2,(0,0),None,ratio22,ratio22)
        imgGray =  cv2.resize(img,(0,0),None,ratio2,ratio2)
        imgGray2 =  cv2.resize(img2,(0,0),None,ratio2,ratio2)
        imgS = cv2.cvtColor(imgS,cv2.COLOR_BGR2RGB)
        imgS2 = cv2.cvtColor(imgS2,cv2.COLOR_BGR2RGB)
        gray_img = cv2.cvtColor(imgGray, cv2.COLOR_BGR2GRAY)
        gray_img2 = cv2.cvtColor(imgGray2, cv2.COLOR_BGR2GRAY)
        faces_rect = haar_cascade.detectMultiScale(
            gray_img, scaleFactor=1.2, minNeighbors=3, minSize=(10, 10))
        faces_rect2 = haar_cascade.detectMultiScale(
            gray_img2, scaleFactor=1.2, minNeighbors=3, minSize=(10, 10))

        if(len(faces_rect)>0):
            #print(len(faces_rect))
            recog = 1
            ratio = 0.4
        elif(ratio==0.2):
            recog = 0
            ratio = 0.01
        if(len(faces_rect2)>0):
            #print(len(faces_rect2))
            recog2 = 1
            ratio22 = 0.4
        elif(ratio==0.2):
            recog2 = 0
            ratio22 = 0.01

        if(recog):
            facesCurFrame = face_recognition.face_locations(imgS)
            encodesCurFrame = face_recognition.face_encodings(imgS,facesCurFrame)
            preEntryList = []
            preEntryIndex = []
            for encodeFace, in zip(encodesCurFrame):
                matches = face_recognition.compare_faces(encodeListKnown,encodeFace)
                faceDis = face_recognition.face_distance(encodeListKnown,encodeFace)
                #print(matches)
                #print(faceDis)
                matchIndex = np.argmin(faceDis)
                if matches[matchIndex]:
                    name = classNames[matchIndex].upper()
                    preEntryList.append(name)
                    preEntryIndex.append(matchIndex)
                    isIntruder1 = 0
                else:
                    name = 'Intruder'
                    isIntruder1 += 1
                    isIntruder1 = isIntruder1%6
                    print("isIntruder1: "+str(isIntruder1))
                cv2.putText(img,name,(50,50),cv2.FONT_HERSHEY_COMPLEX,1,(255,255,0),2)
                #print(name)
        if(recog2):
            facesCurFrame2 = face_recognition.face_locations(imgS2)
            encodesCurFrame2 = face_recognition.face_encodings(imgS2,facesCurFrame2)
            preExitList = []
            preExitIndex = []
            #print("Camera 2 recognized \n")
            for encodeFace2, in zip(encodesCurFrame2):
                matches = face_recognition.compare_faces(encodeListKnown,encodeFace2)
                faceDis = face_recognition.face_distance(encodeListKnown,encodeFace2)
                #print(matches)
                #print(faceDis)
                matchIndex = np.argmin(faceDis)

                if matches[matchIndex]:
                    isIntruder2 = 0
                    name = classNames[matchIndex].upper()
                    preExitList.append(name)
                    preExitIndex.append(matchIndex)
                else:
                    isIntruder2 = 1
                    name = 'Intruder'
                cv2.putText(img2,name,(50,50),cv2.FONT_HERSHEY_COMPLEX,1,(255,255,0),2)
              #  print(name)
        # For logging
        print("door: " + str(door))
        if(outside == 1 and door == 0 and isIntruder1 == 5):
            print("notification intrusion")
            isIntruder1 = 0
        if(isIntruder2 == 1):
            i = 0
            # Alarm here
        elif(incoming == 0 and exiting == 0 and outside == 1 and door == 0):
            incoming = 1
            #if(isIntruder1 >= 2):
                #print("notification anomaly")
                #isIntruder1 = 0
        elif(incoming == 1 and exiting == 0 and door == 1):
            for person in preEntryList:
                if person not in enterlist:
                    enterlist.append(person)
            for k in preEntryIndex:
                if k not in enterindex:
                    enterindex.append(k)
        elif(incoming == 1 and exiting == 0 and door == 0 and outside == 0):
            incoming=0
            for person in preEntryList:
                if person in enterlist:
                    enterlist.remove(person)
            print(enterlist)
            for k in preEntryIndex:
                if k in enterindex:
                    enterindex.remove(k)
            print(enterindex)
            for index in enterlist:
                lognum+=1
                log['name'] = index
                now = datetime.now()
                now = now.strftime('%d/%m/%Y %H:%M')
                log['time'] = now
                log['type'] = "IN"
                logRef.update({"Log" + str(lognum) :log})


            enterlist = []
            for k in enterindex:
                now = datetime.now()
                now = now.strftime('%d/%m/%Y %H:%M')
                timeMin = int(now[11:13])*60+int(now[14:16])
                logState[k] = 1
                if(timeMin<meanLogin[k]-3*stdLogin[k]):
                    print("ANOMALY: "+ classNames[k]+ " came home early")
                    #anomaly situation occured, send notification
                    email_sender(mailList[k],classNames[k]+" came home early",2)
                elif(timeMin<meanLogin[k]+3*stdLogin[k]):
                    meanLogin[k] = mean_update(meanLogin[k],sizeLogin[k]+1,timeMin)
                    stdLogin[k] = std_update(meanLogin[k],stdLogin[k],sizeLogin[k]+1,timeMin)
                    sizeLogin[k] += 1

            enterindex = []

        elif(incoming == 0 and exiting == 0 and outside == 0 and door == 1):# out
            exiting = 1
        elif(incoming == 0 and exiting == 1 and outside == 0 and door == 1):
            for person in preExitList:
                if person not in exitlist:
                    exitlist.append(person)
            for k in preExitIndex:
                if k not in exitindex:
                    exitindex.append(k)

        elif(incoming == 0 and exiting == 1 and door == 0 and outside == 0):
            exiting=0
            for person in preExitList:
                if person in exitlist:
                    exitlist.remove(person)
            print(exitlist)
            for k in preExitIndex:
                if k in exitindex:
                    exitindex.remove(k)
            print(exitindex)

            for index in exitlist:
                lognum+=1
                log['name'] = index
                now = datetime.now()
                now = now.strftime('%d/%m/%Y %H:%M')
                log['time'] = now
                log['type'] = "OUT"
                logRef.update({"Log" + str(lognum) :log})
            exitlist = []
            for k in exitindex:
                logState[k] = 0
            exitindex = []

        cv2.imshow("Security Feed", img)
        cv2.imshow("Security Feed 2", img2)
        rawCapture.truncate(0)

        #finishTime=time()
        #fps = 1/np.round(finishTime - startTime, 3) #Measure the FPS.
        #print(f"Frames Per Second : {fps}")
        if (isUpdated=="True"):
            cap.release()
            cv2.destroyAllWindows()
            break
    key = cv2.waitKey(1)& 0xFF
    if key == ord("q"):
        break
