# TPMS BLE

Custom Homeassistant Integration for [Aliexpress TPMS system](https://www.aliexpress.com/item/1005006115457035.html) which has name `BR` and provides service `0x27a5`

This integration was done based on reverse engineering of official Android application.

## Sensor spec

Sensors expose data over Bluetooth 5.0

These sensors are not connectable (in BLE terms) and share its data in advertisement only if there are changes in pressure/temperature/battery voltage. Otherwise they are in sleep mode

Android app uses raw advertisement data to extract info from sensor, for some reason Python's `bleak` library doesn't provide data at this low level but I was able to extract this data from manufacturer data.

Sensor exposes its data as:

```py
{ 7720: b'\x1a\x01>\xe0C' }
```

both key and value contains actual data, so the key will always change because it represents the first 2 bytes of advertised data and actually contains battery level.

Key needs to be converted back to bytes:

```py
key = 7720
key.to_bytes(2, 'little').hex() # 281e
```

`1e` is a battery level, in this case it's `30` (need to devide by 10 to get actual level)

After converting the rest of bytes to int array:

```py
list(b'\x1a\x01>\xe0C') # [26, 1, 62, 224, 67]
```

the 1st value in array is a temperature. The 2nd 2 relates to major and minor value for pressure in psi. To get the actual value of PSI we need:

```py
psi_major = ints[1] << 8
psi_minor = ints[2]
psi = psi_major | psi_minor # 318
psi -= 146 # have no idea why we need subtraction (copied from Android app and it actually reflects the real value)
```

To get the actual value we need to divide it by 10, in this case it's `17.2` Psi.

The sensor starts advertisement more often if pressure < 20.7 Psi
