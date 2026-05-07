# yeah gonna have to install this. Not a requirement though
from tabulate import tabulate

while True:
    packet = input("Enter packet 0x09 or 0x02:\n> ")
    # 09 07 F8 00
    data = bytes.fromhex(packet)
    ID = data[0]
    # Get state flags from big endian. MSB first
    PURGE_ACTIVATE = (data[1] >> 7) & 0b1
    O2_ACTIVATE = (data[1] >> 6) & 0b1
    SELECTOR_NEUTRAL = (data[1] >> 5) & 0b1
    N2O_FILL_ACTIVATE = (data[1] >> 4) & 0b1
    IGNITION_FIRE = (data[1] >> 3) & 0b1
    IGNITION_SELECTED = (data[1] >> 2) & 0b1
    GAS_SELECTED = (data[1] >> 1) & 0b1
    SYS_ACTIVE = (data[1] >> 0) & 0b1

    INV_PURGE_ACTIVATE = (data[2] >> 7) & 0b1
    INV_O2_ACTIVATE = (data[2] >> 6) & 0b1
    INV_SELECTOR_NEUTRAL = (data[2] >> 5) & 0b1
    INV_N2O_FILL_ACTIVATE = (data[2] >> 4) & 0b1
    INV_IGNITION_FIRE = (data[2] >> 3) & 0b1
    INV_IGNITION_SELECTED = (data[2] >> 2) & 0b1
    INV_GAS_SELECTED = (data[2] >> 1) & 0b1
    INV_SYS_ACTIVE = (data[2] >> 0) & 0b1

    NULL = data[3]

    if ID == 0x09:
        if len(data) != 4:
            print(f"Invalid packet length: {len(data)}")
            continue
        flags = [
            ["PURGE_ACTIVATE", PURGE_ACTIVATE, INV_PURGE_ACTIVATE],
            ["O2_ACTIVATE", O2_ACTIVATE, INV_O2_ACTIVATE],
            ["SELECTOR_NEUTRAL", SELECTOR_NEUTRAL, INV_SELECTOR_NEUTRAL],
            ["N2O_FILL_ACTIVATE", N2O_FILL_ACTIVATE, INV_N2O_FILL_ACTIVATE],
            ["IGNITION_FIRE", IGNITION_FIRE, INV_IGNITION_FIRE],
            ["IGNITION_SELECTED", IGNITION_SELECTED, INV_IGNITION_SELECTED],
            ["GAS_SELECTED", GAS_SELECTED, INV_GAS_SELECTED],
            ["SYS_ACTIVE", SYS_ACTIVE, INV_SYS_ACTIVE],
        ]

        print(tabulate(flags, headers=["Field", "Value", "!Value"]))

        for flag in flags:
            if flag[1] == flag[2]:
                print(f"Bits are not inverted correctly: {flag[0]}")

        if NULL != 0x00:
            print("NULL byte is not 0x00")

    elif ID == 0x02:
        pass
    else:
        print("invalid packet ID")
