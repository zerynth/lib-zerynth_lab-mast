import streams
from zerynth_lab.mast import temp_hum_click

streams.serial()
 
def print_temp_humidity():
    while True:
        tmp, hum = temp_hum.get_temp_humidity()
        print("Temp is:", tmp, "Humidity is:", hum)
        sleep(1000)
        
try:
    temp_hum = temp_hum_click.TempHumClick(I2C1,D38)
except Exception as e:
    print(e)

print_temp_humidity() 
