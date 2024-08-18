from machine import Pin, UART

arduino_uart = UART(2, baudrate=115200, tx=Pin(27), rx=Pin(26))
arduino_uart.init()