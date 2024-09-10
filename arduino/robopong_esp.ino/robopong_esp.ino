// robopong.ino
// Alberto Gomez-Casado 2024

/*
send commands via serial surrounded by <>
<home x/y/z>
<mvby x/y/z steps>
<mvto x/y/z steps>
<stop x/y/z>
<sped x/y/z speed>

the steps/speed are scaled by the stepped mode 1/1, 1/2 ... 1/32 defined below

FIXME: wrap-around for continuous rotation

*/

#include <ESP_FlexyStepper.h>

#define xstep 32
#define xdir 33
#define ystep 25
#define ydir 26
#define zstep 27
#define zdir 14
#define enable 13

#define RXD2 16
#define TXD2 17

ESP_FlexyStepper xstepper;
ESP_FlexyStepper ystepper;
ESP_FlexyStepper zstepper;

const int mode = 16; // the microstep mode, set by hw jumpers on the driver
const int speed = 2000 * mode;
const int accel = 6000 * mode;



const byte numChars = 32;
char receivedChars[numChars];

boolean newData = false;

String HOME = "home";
String MOVEBY = "mvby";
String MOVETO = "mvto";
String STOP = "stop";
String SPEED = "sped";
String ON = "on";
String OFF = "off";


void setup() {
  Serial.begin(115200);
  Serial2.begin(115200, SERIAL_8N1, RXD2, TXD2);

  xstepper.connectToPins(xstep, xdir);
  ystepper.connectToPins(ystep, ydir);
  zstepper.connectToPins(zstep, zdir);

  xstepper.setSpeedInStepsPerSecond(speed);
  ystepper.setSpeedInStepsPerSecond(speed);
  zstepper.setSpeedInStepsPerSecond(speed);

  xstepper.setAccelerationInStepsPerSecondPerSecond(accel);
  ystepper.setAccelerationInStepsPerSecondPerSecond(accel);
  zstepper.setAccelerationInStepsPerSecondPerSecond(accel);

  xstepper.setDecelerationInStepsPerSecondPerSecond(accel);
  ystepper.setDecelerationInStepsPerSecondPerSecond(accel);
  zstepper.setDecelerationInStepsPerSecondPerSecond(accel);

// void setDirectionToHome(signed char directionTowardHome)

  xstepper.setCurrentPositionInSteps(0);
  ystepper.setCurrentPositionInSteps(0);
  zstepper.setCurrentPositionInSteps(0);

  xstepper.startAsService();
  ystepper.startAsService();
  zstepper.startAsService();

  pinMode(enable, OUTPUT);
  digitalWrite(enable, LOW);

  }


void recvWithStartEndMarkers() {
  static boolean recvInProgress = false;
  static byte ndx = 0;
  char startMarker = '<';
  char endMarker = '>';
  char rc;

  while (Serial.available() > 0 && newData == false) {
    rc = Serial.read();

    if (recvInProgress == true) {
      if (rc != endMarker) {
        receivedChars[ndx] = rc;
        ndx++;
        if (ndx >= numChars) {
          ndx = numChars - 1;
        }
      } else {
        receivedChars[ndx] = '\0';  // terminate the string
        recvInProgress = false;
        ndx = 0;
        newData = true;
      }
    }

    else if (rc == startMarker) {
      recvInProgress = true;
    }
  }
}

void recvWithStartEndMarkers2() {
  static boolean recvInProgress = false;
  static byte ndx = 0;
  char startMarker = '<';
  char endMarker = '>';
  char rc;

  while (Serial2.available() > 0 && newData == false) {
    rc = Serial2.read();

    if (recvInProgress == true) {
      if (rc != endMarker) {
        receivedChars[ndx] = rc;
        ndx++;
        if (ndx >= numChars) {
          ndx = numChars - 1;
        }
      } else {
        receivedChars[ndx] = '\0';  // terminate the string
        recvInProgress = false;
        ndx = 0;
        newData = true;
      }
    }

    else if (rc == startMarker) {
      recvInProgress = true;
    }
  }
}


void interpret() {
  if (newData == true) {
    String recv = String(receivedChars);

    if (recv.startsWith(HOME)) home(recv.charAt(5));
    if (recv.startsWith(MOVEBY)) move_by(recv.charAt(5), recv.substring(7).toInt());
    if (recv.startsWith(MOVETO)) move_to(recv.charAt(5), recv.substring(7).toInt());
    if (recv.startsWith(SPEED)) set_speed(recv.charAt(5), recv.substring(7).toInt());
    if (recv.startsWith(STOP)) stop(recv.charAt(5));
    if (recv.startsWith(ON)) digitalWrite(enable, LOW);
    if (recv.startsWith(OFF)) digitalWrite(enable, HIGH);


    newData = false;
    Serial.println(receivedChars);
    Serial2.println(receivedChars);
  }
}

void stop(char axis) {
  ESP_FlexyStepper* stepper = NULL;

  if (axis == 'x') stepper = &xstepper;
  if (axis == 'y') stepper = &ystepper;
  if (axis == 'z') stepper = &zstepper;
  if (stepper != NULL) stepper->setTargetPositionToStop();
}

void home(char axis) {
  ESP_FlexyStepper* stepper = NULL;

  if (axis == 'x') stepper = &xstepper;
  if (axis == 'y') stepper = &ystepper;
  if (axis == 'z') stepper = &zstepper;
  if (stepper != NULL) {
    Serial.println("TBD homing");
  };
}

void move_to(char axis, int steps) {
  ESP_FlexyStepper* stepper = NULL;

  if (axis == 'x') stepper = &xstepper;
  if (axis == 'y') stepper = &ystepper;
  if (axis == 'z') stepper = &zstepper;
  if (stepper != NULL) stepper->setTargetPositionInSteps(steps * mode);
}

void set_speed(char axis, int speed) {
  ESP_FlexyStepper* stepper = NULL;

  if (axis == 'x') stepper = &xstepper;
  if (axis == 'y') stepper = &ystepper;
  if (axis == 'z') stepper = &zstepper;
  if (stepper != NULL) stepper->setSpeedInStepsPerSecond(speed * mode);
}

void move_by(char axis, int steps) {
  ESP_FlexyStepper* stepper = NULL;

  if (axis == 'x') stepper = &xstepper;
  if (axis == 'y') stepper = &ystepper;
  if (axis == 'z') stepper = &zstepper;

  if (stepper != NULL) {
    stepper->setTargetPositionRelativeInSteps(steps * mode);
  }
}



void loop() {
  recvWithStartEndMarkers();
  recvWithStartEndMarkers2();
  interpret();
  if ((xstepper.motionComplete()) & (ystepper.motionComplete()) & (zstepper.motionComplete())) digitalWrite(enable, HIGH);
  else digitalWrite(enable, LOW);

}
