import pygame
import time

pygame.init()
pygame.joystick.init()
pygame.display.init()

while pygame.joystick.get_count() == 0:
    print("No controllers detected.")
    pygame.event.pump()
    time.sleep(0.5)

joystick = pygame.joystick.Joystick(0)
joystick.init()

print(f"Controller detected: {joystick.get_name()}")

PENDANT_BINDINGS = {
    1: "IGNITION_O2",
    2: "IGNITION_FIRE",
    3: "FILL_PURGE",
    4: "IGNITION",
    5: "ESTOP",
    6: "FILL",
    8: "FILL_N2O",
}

THRUSTMASTER_PENDANT_BINDINGS = {
    16: "SYSTEM ACTIVE", #thrust lever
    0: "FILL MODE", # bottom back trigger
    1: "ARMED", # top back trigger
    
    2: "02", # spherical button
    3: "FIRE", # red button

    6: "N2O", # top left button on the right
    5: "PURGE", # top middle button on the right
}

PENDANT_BINDINGS = THRUSTMASTER_PENDANT_BINDINGS

PENDANT_ACTIVE = set()  # Set to keep track of active buttons

running = True
while running:
    pygame.event.pump()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.JOYAXISMOTION and abs(event.value) > 0.2:
            # Joystick deadzone to prevent console spam
            # print(f"Joystick Axis: {event.axis}, Value: {event.value}")
            pass
        elif event.type == pygame.JOYBALLMOTION:
            # print(f"Joystick Ball: {event.ball}, Value: {event.rel}")
            pass
        elif event.type == pygame.JOYHATMOTION:
            print(f"Joystick Hat: {event.hat}, Value: {event.value}")
        elif event.type == pygame.JOYBUTTONDOWN:
            # Check
            if event.button in PENDANT_BINDINGS:
                # print(PENDANT_BINDINGS[event.button])
                PENDANT_ACTIVE.add(PENDANT_BINDINGS[event.button])
                print(PENDANT_ACTIVE)
            else:
                print(f"Joystick Button {event.button} Down")
        elif event.type == pygame.JOYBUTTONUP:
            if event.button in PENDANT_BINDINGS:
                # print(PENDANT_BINDINGS[event.button])
                PENDANT_ACTIVE.remove(PENDANT_BINDINGS[event.button])
                if len(PENDANT_ACTIVE) > 0:
                    print(PENDANT_ACTIVE)
                else:
                    print("{}")
            else:
                print(f"Joystick Button {event.button} Up")
        elif event.type == pygame.JOYDEVICEADDED:
            print("New controller connected.")
        elif event.type == pygame.JOYDEVICEREMOVED:
            print("Controller disconnected.")
            running = False

pygame.quit()
