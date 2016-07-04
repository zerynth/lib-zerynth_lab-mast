
from zerynth_lab.mast.maxim import ds2482
from zerynth_lab.mast.maxim import ds1820

def get_temp_sensor(drv):
    ow = ds2482.DS2482(drv)
    ow.start()
    ow.set_channel(2)
    res = ow.search_raw()
    for i,k in enumerate(res):
        return ds1820.DS1820(k,ow)