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

#include <AccelStepper.h>

AccelStepper stepperx(1, 2, 5);
AccelStepper steppery(1, 3, 6);
AccelStepper stepperz(1, 4, 7);

const byte enablePin = 8;

const int mode = 16; // the microstep mode, set by hw jumpers on the driver

const float speed = 100.0 * mode;
const float accel = 200.0 * mode;

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
  Serial.println("<Arduino is ready>");
  pinMode(enablePin, OUTPUT);
  digitalWrite(enablePin, LOW);

  stepperx.setMaxSpeed(speed);
  stepperx.setAcceleration(accel);

  steppery.setMaxSpeed(speed);
  steppery.setAcceleration(accel);

  stepperz.setMaxSpeed(speed);
  stepperz.setAcceleration(accel);
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

void interpret() {
  if (newData == true) {
    String recv = String(receivedChars);

    if (recv.startsWith(HOME)) home(recv.charAt(5));
    if (recv.startsWith(MOVEBY)) move_by(recv.charAt(5), recv.substring(7).toInt());
    if (recv.startsWith(MOVETO)) move_to(recv.charAt(5), recv.substring(7).toInt());
    if (recv.startsWith(SPEED)) set_speed(recv.charAt(5), recv.substring(7).toInt());
    if (recv.startsWith(STOP)) stop(recv.charAt(5));
    if (recv.startsWith(ON)) digitalWrite(enablePin, LOW);
    if (recv.startsWith(OFF)) digitalWrite(enablePin, HIGH);


    newData = false;
    Serial.println(receivedChars);
  }
}

void stop(char axis) {
  AccelStepper* stepper = NULL;

  if (axis == 'x') stepper = &stepperx;
  if (axis == 'y') stepper = &steppery;
  if (axis == 'z') stepper = &stepperz;
  if (stepper != NULL) stepper->stop();
}

void home(char axis) {
  AccelStepper* stepper = NULL;

  if (axis == 'x') stepper = &stepperx;
  if (axis == 'y') stepper = &steppery;
  if (axis == 'z') stepper = &stepperz;
  if (stepper != NULL) {
    Serial.println("TBD homing");
  };
}

void move_to(char axis, int steps) {
  AccelStepper* stepper = NULL;

  if (axis == 'x') stepper = &stepperx;
  if (axis == 'y') stepper = &steppery;
  if (axis == 'z') stepper = &stepperz;
  if (stepper != NULL) stepper->moveTo(steps * mode);
}

void set_speed(char axis, int speed) {
  AccelStepper* stepper = NULL;

  if (axis == 'x') stepper = &stepperx;
  if (axis == 'y') stepper = &steppery;
  if (axis == 'z') stepper = &stepperz;
  if (stepper != NULL) stepper->setMaxSpeed(speed * mode);
}

void move_by(char axis, int steps) {
  AccelStepper* stepper = NULL;

  if (axis == 'x') stepper = &stepperx;
  if (axis == 'y') stepper = &steppery;
  if (axis == 'z') stepper = &stepperz;

  if (stepper != NULL) {
    int previous = stepper->targetPosition();
    stepper->moveTo(previous + steps * mode);
  }
}

void loop() {
  recvWithStartEndMarkers();
  interpret();
  stepperx.run();
  steppery.run();
  stepperz.run();
  if ((stepperx.distanceToGo() == 0) & (steppery.distanceToGo() == 0) & (stepperz.distanceToGo() == 0)) digitalWrite(enablePin, HIGH);
  else digitalWrite(enablePin, LOW);
}
