import asyncio
import logging

logging.getLogger().setLevel(logging.DEBUG)

from bleak import BleakScanner
from datetime import datetime

async def main():
    async with BleakScanner() as scanner:
        print("Scanning...")
        async for bd, ad in scanner.advertisement_data():
            if bd.name == 'BR':
                print(f"{datetime.now()} Device {bd!r}")
                for k, v in ad.manufacturer_data.items():
                    bytes = k.to_bytes(2, 'little')
                    raw = bytes + v
                    ints = list(raw)
                    psi_major = ints[3] << 8
                    psi_minor = ints[4] & 255
                    psi = psi_major | psi_minor
                    psi -= 146 # check min 146
                    print({ 
                        'volt': ints[1] / 10.0, # min 2.6
                        'temp': ints[2],
                        'psi':  psi / 10.0, # min 146 => 148
                        'bar': psi / 14.5038 / 10.0,
                        'raw': ints,
                        'bytes': raw
                    })
                print("\n")

if __name__ == "__main__":
    asyncio.run(main())