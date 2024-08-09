from kollar_instruments.Keithley2400 import keithley

device = keithley('ASRL5::INSTR')
device.mode = 'current' #or voltage
device.Output = 1  #or 0 for off
device.set_voltage_meas_range(30) #all values are float Volts or Amps
measurements=[]
for i in range(0,100):
    device.set_current(i/100)
    measurements.append(device.measure())
print(measurements)

device.reset()
device.close()

