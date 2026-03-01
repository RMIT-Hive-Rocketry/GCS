import pygame
import time

pygame.init()
pygame.joystick.init()

while pygame.joystick.get_count() == 0:
    print("No controllers detected.")
    pygame.event.pump()
    time.sleep(0.5)

joystick = pygame.joystick.Joystick(0)
joystick.init()

print(f"Controller detected: {joystick.get_name()}")

running = True
while running:
    pygame.event.pump()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.JOYAXISMOTION:
            print(f"Joystick Axis: {event.axis}, Value: {event.value}")
        elif event.type == pygame.JOYBALLMOTION:
            print(f"Joystick Ball: {event.ball}, Value: {event.rel}")
        elif event.type == pygame.JOYHATMOTION:
            print(f"Joystick Hat: {event.hat}, Value: {event.value}")
        elif event.type == pygame.JOYBUTTONDOWN:
            print(f"Joystick Button {event.button} Down")
        elif event.type == pygame.JOYBUTTONUP:
            print(f"Joystick Button {event.button} Up")
        elif event.type == pygame.JOYDEVICEADDED:
            print("New controller connected.")
        elif event.type == pygame.JOYDEVICEREMOVED:
            print("Controller disconnected.")
            running = False

pygame.quit()
