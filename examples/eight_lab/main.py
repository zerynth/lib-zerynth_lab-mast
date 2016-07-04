import streams
from zerynth_lab.mast.eight_click import eight_click
 
def led_display():
    intensity = 10
    while True:
        for row in range(8):
            for col in range(8):
                display.set_led( 0, col, row, 1 )
                sleep(display_speed)
                display.clear_display(0)
        display.set_intensity( 0, intensity )
        intensity += 1 
        if intensity > 16:
            intensity = 0 

streams.serial()
display = eight_click.LedDisplay(D17)
display_speed = 100


led_display() 
