from stservo.sts import sts
from stservo.port_handler import PortHandler
from stservo.stservo_def import *

class STServo:
    """Interface in degrees"""
    def __init__(self, ph, servo_id):
        self.ph = ph
        self.servo_id = servo_id
        self.default_speed = 90 # deg/s
        self.default_acc = 1 # deg/s2


        self.sts = sts(ph)
        ph.openPort()
        ph.setBaudRate(1000000)
        self._npos_rev = 4096

    def ping(self):
        sts_model_number, sts_comm_result, sts_error = self.sts.ping(self.servo_id)

        if sts_comm_result != COMM_SUCCESS:
            print("%s" % self.sts.getTxRxResult(sts_comm_result))
        else:
            print("[ID:%03d] ping Succeeded. STServo model number : %d" % (self.servo_id, sts_model_number))
        if sts_error != 0:
            print("%s" % self.sts.getRxPacketError(sts_error))

    def _convert_to_pos(self, angle):
        return int(angle * self._npos_rev / 360)

    def _convert_to_angle(self, pos):
        return pos / self._npos_rev * 360

    def status(self):
        sts_present_position, sts_present_speed, sts_comm_result, sts_error = self.sts.ReadPosSpeed(self.servo_id)
        if sts_comm_result != COMM_SUCCESS:
            print(self.sts.getTxRxResult(sts_comm_result))
        else:
            angle = self._convert_to_angle(sts_present_position)
            angular_speed = self._convert_to_angle(sts_present_speed)
            print(f"[ID:{self.servo_id}] Angle:{angle:.1f} deg Spd:{angular_speed:.2f} deg/s")
        if sts_error != 0:
            print(self.sts.getRxPacketError(sts_error))

    def is_moving(self):
        moving, comm, err = self.sts.ReadMoving(self.servo_id)
        if comm != COMM_SUCCESS:
            raise Exception(self.sts.getTxRxResult(comm))
        if err != 0:
            raise Exception(self.sts.getRxPacketError(err))
        return bool(moving)

    def move(self, angle, speed=None, acc=None):
        speed = self._convert_to_pos(speed) if speed else self._convert_to_pos(self.default_speed)
        acc = self._convert_to_pos(acc) if acc else self._convert_to_pos(self.default_acc)

        comm_result, error = self.sts.WritePosEx(self.servo_id, self._convert_to_pos(angle), speed, acc)
        if comm_result != COMM_SUCCESS:
            raise Exception(self.sts.getTxRxResult(comm_result))

    def set_wheel_mode(self):
        comm_result = self.sts.WheelMode(self.servo_id)
        if comm_result != COMM_SUCCESS:
            raise Exception(self.sts.getTxRxResult(comm_result))

    def program_movement(self, angle, speed=None, acc=None):
        """Setups a movement, but does not execute it until action is called"""
        speed = self._convert_to_pos(speed) if speed else self._convert_to_pos(self.default_speed)
        acc = self._convert_to_pos(acc) if acc else self._convert_to_pos(self.default_acc)

        comm_result, sts_error = self.sts.RegWritePosEx(self.servo_id, self._convert_to_pos(angle), speed, acc)
        print(comm_result, sts_error)
        if comm_result != COMM_SUCCESS:
            raise Exception(self.sts.getTxRxResult(comm_result))

    def program_speed(self, speed, acc=None):
        """Setups a speed, but does not execute it until action is called"""
        comm_result, error = self.sts.WriteSpec(self.servo_id, speed, acc)
        if comm_result != COMM_SUCCESS:
            raise Exception(self.sts.getTxRxResult(comm_result))

    def action(self):
        "Executes all setup movements (in all servos!)"
        self.sts.RegAction()

    def _lock_eeprom(self):
        comm_result = self.sts.LockEprom(self.servo_id)
        if comm_result != COMM_SUCCESS:
            raise Exception(self.sts.getTxRxResult(comm_result))

    def _unlock_eeprom(self):
        comm_result = self.sts.unLockEprom(self.servo_id)
        if comm_result != COMM_SUCCESS:
            raise Exception(self.sts.getTxRxResult(comm_result))


if __name__ == "__main__":
    st = STServo(PortHandler("COM6"), servo_id=9)

    st.ping()
    st.status()