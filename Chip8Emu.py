"""
Goal:
    Create a Chip-8 Emulator
"""

import os, random, pygame, winsound

pygame.init()

class MyChip8:
    def __init__(self):
        # Initialize registers and memory

        self.opcode = 0  # All 35 opcodes are two bytes long
        self.memory = [0 for i in range(0, 4096)]
        self.I = 0  # Index register
        self.pc = int("200",16)  # Program Counter starts at 0x200
        self.sp = 0  # Stack Pointer

        self.original_gfx = [0] * (64 * 32)
        self.gfx = self.original_gfx.copy() # Holds the on/off value of every pixel
        self.stack = [0 for i in range(0, 16)]
        self.V = [0 for i in range(0, 17)]  # CPU Registers V0 to VE, 16th register is used for carry flag
        self.drawflag = 0

        # Load fontset
        self.font = [
            0xF0, 0x90, 0x90, 0x90, 0xF0, #0
            0x20, 0x60, 0x20, 0x20, 0x70, #1
            0xF0, 0x10, 0xF0, 0x80, 0xF0, #2
            0xF0, 0x10, 0xF0, 0x10, 0xF0, #3
            0x90, 0x90, 0xF0, 0x10, 0x10, #4
            0xF0, 0x80, 0xF0, 0x10, 0xF0, #5
            0xF0, 0x80, 0xF0, 0x90, 0xF0, #6
            0xF0, 0x10, 0x20, 0x40, 0x40, #7
            0xF0, 0x90, 0xF0, 0x90, 0xF0, #8
            0xF0, 0x90, 0xF0, 0x10, 0xF0, #9
            0xF0, 0x90, 0xF0, 0x90, 0x90, #A
            0xE0, 0x90, 0xE0, 0x90, 0xE0, #B
            0xF0, 0x80, 0x80, 0x80, 0xF0, #C
            0xE0, 0x90, 0x90, 0x90, 0xE0, #D
            0xF0, 0x80, 0xF0, 0x80, 0xF0, #E
            0xF0, 0x80, 0xF0, 0x80, 0x80] #F

        # Loads fontset into memory
        # Also saves starting address of each character
        self.sprite_addr = []
        for i in range(len(self.font)):
            self.memory[80+i] = self.font[i]
            if i % 5 == 0:
                self.sprite_addr.append(80+i)

        self.delay_timer = 0  # When set above zero, will count down to zero at 60 Hz
        self.sound_timer = 0  # Same as delay, but the system buzzer sounds when it reaches 0

        self.key = [0 for i in range(0, 16)]
        self.keymapping = {
            '0' : pygame.K_x,
            '1' : pygame.K_1,
            '2' : pygame.K_2,
            '3' : pygame.K_3,
            '4' : pygame.K_q,
            '5' : pygame.K_w,
            '6' : pygame.K_e,
            '7' : pygame.K_a,
            '8' : pygame.K_s,
            '9' : pygame.K_d,
            'a' : pygame.K_z,
            'b' : pygame.K_c,
            'c' : pygame.K_4,
            'd' : pygame.K_r,
            'e' : pygame.K_f,
            'f' : pygame.K_v
        }

    def load_game(self,file_name):
        f = open(file_name,"rb")
        for i in range(0,os.path.getsize(file_name)):
            self.memory[i+512] = int(f.read(1).hex(),16)
        f.close()

    def emulate_cycle(self):
        # Fetch Opcode
        self.opcode = hex(self.memory[self.pc] << 8 | self.memory[self.pc+1])
        self.drawflag = 0
        print(self.opcode,self.pc)

        # Decode opcode
        # TODO: Fix broken opcodes

        if "0x1" in self.opcode:
            # jumps to adress NNN
            self.pc = int(self.opcode[3:6],16)

        elif "0xa" in self.opcode:
            #sets I to adress NNN
            self.I = int(self.opcode.replace("0xa","0x0"),16)
            self.pc += 2

        elif "0x2" in self.opcode:
            #Calls subroutine
            self.stack[self.sp] = self.pc
            self.sp += 1
            self.pc = int(self.opcode.replace("0x2","0x0"),16)

        elif "0x3" in self.opcode:
            #Skips the next instruction if VX = NN
            if int(self.V[int(self.opcode[3],16)]) == int(self.opcode[4:6],16):
                self.pc += 2
            self.pc += 2

        elif '0x4' in self.opcode:
            # Skips the next instruction if VX doesn't equal NN.
            if int(self.V[int(self.opcode[3],16)]) != int(self.opcode[4:6],16):
                self.pc += 2
            self.pc += 2

        elif '0xf' in self.opcode:
            if self.opcode[4:6] == "33":
                #Stores a bcd of VX at adress I
                self.memory[self.I] = self.V[int(self.opcode[3],16)]/100
                self.memory[self.I + 1] = (self.V[int(self.opcode[3],16)] /10) % 10
                self.memory[self.I + 2] = (self.V[int(self.opcode[3],16)] % 100) % 10
                self.pc += 2

            elif self.opcode[4:6] == "65":
                """
                    Fills V0 to VX (including VX) with values
                    from memory starting at address I.

                    The offset from I is increased by 1 for each value written,
                    but I itself is left unmodified.
                """

                for index in range(0,int(self.opcode[3],16)+1):
                    self.V[index] = int(self.memory[self.I+index])

                self.pc += 2

            elif self.opcode[4:6] == "29":
                """
                Sets I to the location of the sprite
                for the character in VX. Characters 0-F
                (in hexadecimal) are represented by a 4x5 font.
                """

                self.I = self.sprite_addr[int(str(self.V[int(self.opcode[3],16)]),16)]
                self.pc += 2

            elif self.opcode[4:6] == "15":
                # Sets the delay timer to VX
                self.delay_timer = int(self.V[int(self.opcode[3],16)])
                self.pc += 2

            elif self.opcode[4:6] == "07":
                # Sets VX to the value of the delay timer.
                self.V[int(self.opcode[3],16)] = int(self.delay_timer)
                self.pc += 2

            elif self.opcode[4:6] == "1e":
                # Adds VX to I. VF is not affected.
                self.I += self.V[int(self.opcode[3],16)]
                self.pc += 2

            elif self.opcode[4:6] == "55":
                # Stores V0 to VX (including VX) in memory starting at address I.
                # The offset from I is increased by 1 for each value written,
                # but I itself is left unmodified.

                for index in range(0,int(self.opcode[3],16)+1):
                    self.memory[self.I+index] = self.V[index]

                self.pc += 2

            elif self.opcode[4:6] == "0a":
                # A key press is awaited, and then stored in VX.
                # (Blocking Operation. All instruction halted until next key event)
                pkeys = pygame.key.get_pressed()
                pressed = False
                for item in self.keymapping.keys():
                    if pkeys[self.keymapping[item]]:
                        self.V[int(self.opcode[3],16)] = item
                        pressed = True
                if pressed:
                    self.pc += 2

            elif self.opcode[4:6] == "18":
                # Sets the sound timer to VX.
                winsound.Beep(1000,self.V[int(self.opcode[3],16)])
                self.sound_timer = self.V[int(self.opcode[3],16)]
                self.pc += 2

            else:
                print("Unkown opcode: {}".format(self.opcode))

        elif '0x5' in self.opcode:
            # Skips the next instruction if VX equals VY.
            if int(self.V[int(self.opcode[3],16)]) == int(self.V[int(self.opcode[4],16)]):
                self.pc += 2
            self.pc += 2

        elif "0x6" in self.opcode:
            # Sets Vx to NN
            self.V[int(self.opcode[3],16)] = int(self.opcode[4:6],16)
            self.pc += 2

        elif "0x7" in self.opcode:
            # Adds NN to VX. (Carry flag is not changed)
            self.V[int(self.opcode[3],16)] += int(self.opcode[4:6],16)
            self.pc += 2

        elif "0xd" in self.opcode:
            #Draws a sprite
            height = int(self.opcode[5],16)
            x = self.V[int(self.opcode[3],16)]
            y = self.V[int(self.opcode[4],16)]

            if x + 8 >= 64: x %= 64
            if y + height >= 32: y %= 32

            self.V[0xF] = 0
            for yline in range(0,height):
                pixel = format(self.memory[int(self.I) + yline],'#010b').replace('0b','')
                for xline in range(0,8):
                    if int(pixel[xline]) != 0:
                        current_pixel = (x + xline + ((y + yline) * 64))
                        if current_pixel >= 64*32:
                            current_pixel -= 64*32
                        if self.gfx[current_pixel] == 1:
                            self.V[0xF] = 1
                        self.gfx[current_pixel] ^= 1

            self.drawflag = 1
            self.pc += 2

        elif "0xc" in self.opcode:
            """
            Sets VX to the result of a bitwise and operation
            on a random number (Typically: 0 to 255) and NN.
            """
            self.V[int(self.opcode[3],16)] = random.randint(0,255) & int(self.opcode[4:6],16)
            self.pc += 2

        elif "0xe" in self.opcode:
            if self.opcode[4:6] == "a1":
                # Skips the next instruction if
                # the key stored in VX isn't pressed.
                pkeys = pygame.key.get_pressed()
                if not pkeys[self.keymapping[str(hex(self.V[int(self.opcode[3],16)]).replace('0x',''))]]:
                    self.pc += 2
                self.pc += 2

            elif self.opcode[4:6] == "9e":
                # Skips the next instruction if
                # the key stored in VX is pressed.
                pkeys = pygame.key.get_pressed()
                if pkeys[self.keymapping[str(hex(self.V[int(self.opcode[3],16)]).replace('0x',''))]]:
                    self.pc += 2
                self.pc += 2

            elif self.opcode == "0xee":
                # Returns from subroutine
                self.sp -= 1
                self.pc = self.stack[self.sp]
                self.stack[self.sp] = 0
                self.pc += 2

            elif self.opcode == "0xe0":
                # Clears the screen
                self.gfx = self.original_gfx.copy()
                self.pc += 2

            else:
                print("Unkown opcode: {}".format(self.opcode))

        elif "0x8" in self.opcode:
            if self.opcode[5] == "4":
                # Adds VY to VX. VF is set to 1 when
                # there's a carry, and to 0 when there isn't.

                if self.V[(int(self.opcode,16) & 0x00F0) >> 4] > (0xFF - self.V[(int(self.opcode,16) & 0x0F00) >> 8]):
                    self.V[0xF] = 1
                else:
                    self.V[0xF] = 0
                self.V[(int(self.opcode,16) & 0x0F00) >> 8] += self.V[(int(self.opcode,16) & 0x00F0) >> 4]
                '''
                self.V[int(self.opcode[3],16)] += int(self.V[int(self.opcode[4],16)])
                self.V[0xF] = 0
                if int(self.opcode[4],16) > int(self.opcode[3],16):
                    self.V[0xF] = 1
                '''
                self.pc += 2

            elif self.opcode[5] == "2":
                # Sets VX to VX and VY. (Bitwise AND operation)
                self.V[int(self.opcode[3],16)] = self.V[int(self.opcode[3],16)] & self.V[int(self.opcode[4],16)]
                self.pc += 2

            elif self.opcode[5] == "e":
                # Stores the most significant bit of VX in VF and then shifts VX to the left by 1.
                self.V[0xF] = int(bin(int(str(self.V[int(self.opcode[3],16)]),16))[2],16)
                try:
                    self.V[int(self.opcode[3],16)] = int(str(self.V[int(self.opcode[3],16)])) << 1
                except ValueError:
                    self.V[int(self.opcode[3], 16)] = int(str(self.V[int(self.opcode[3], 16)]),16) << 1
                self.pc += 2

            elif self.opcode[5] == "6":
                # Stores the least significant bit of VX in VF and then shifts VX to the right by 1.
                self.V[0xF] = int(bin(int(str(self.V[int(self.opcode[3], 16)]), 16))[-1], 16)
                try:
                    self.V[int(self.opcode[3], 16)] = int(str(self.V[int(self.opcode[3], 16)])) >> 1
                except ValueError:
                    self.V[int(self.opcode[3], 16)] = int(str(self.V[int(self.opcode[3], 16)]), 16) >> 1
                self.pc += 2

            elif self.opcode[5] == "0":
                # Sets VX to the value of VY.
                self.V[int(self.opcode[3],16)] = self.V[int(self.opcode[4],16)]
                self.pc += 2

            elif self.opcode[5] == "5":
                # VY is subtracted from VX.
                # VF is set to 0 when there's a borrow, and 1 when there isn't.
                if self.V[int(self.opcode[3],16)] < self.V[int(self.opcode[4],16)]:
                    self.V[0xF] = 0
                    self.V[int(self.opcode[3], 16)] -= self.V[int(self.opcode[4],16)]
                else:
                    self.V[0xF] = 1
                    self.V[int(self.opcode[3], 16)] -= self.V[int(self.opcode[4], 16)]

                self.pc += 2

            elif self.opcode[5] == "3":
                self.V[int(self.opcode[3],16)] ^= self.V[int(self.opcode[4],16)]
                self.pc += 2

            else:
                print("Unkown opcode: {}".format(self.opcode))

        elif "0x9" in self.opcode:
            # Skips the next instruction if VX doesn't equal VY.
            if int(str(self.V[int(self.opcode[3],16)]),16) != int(str(self.V[int(self.opcode[4],16)]),16):
                self.pc += 2
            self.pc += 2

        else:
            print("Unkown opcode: {}".format(self.opcode))

        print(self.V,'\n')

        #Update timers
        if self.delay_timer > 0:
            self.delay_timer -= 1

        if self.sound_timer > 0:
            #print("BEEP!")
            self.sound_timer -= 1

emu = MyChip8()
gamename = "Pong.ch8"
emu.load_game(gamename)

sizem = 10 #Multiplies the screen size

screen = pygame.display.set_mode((64 * sizem,32 * sizem))
pygame.display.set_caption(f'Chip-8 Emulator: {gamename}')

timer = pygame.time.Clock()

framerate = 1000
black = (0,0,0)
white = (255,255,255)
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    timer.tick(framerate)

    emu.emulate_cycle()
    if emu.drawflag == 1:
        screen.fill(black)

        for y in range(0,32):
            for x in range(0,64):
                if emu.gfx[x+(y*64)] == 1:
                    screen.fill(white,pygame.rect.Rect(x*sizem,y*sizem,sizem,sizem))

        pygame.display.flip()