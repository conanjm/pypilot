#!/usr/bin/env python
#
#   Copyright (C) 2019 Sean D'Epagnier
#
# This Program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.  

class Rudder(object):
    def __init__(self, server):
        timestamp = server.TimeStamp('rudder')
        self.angle = self.Register(SensorValue, 'angle', timestamp)
        self.last = 0
        self.last_time = time.time()
        self.offset = self.Register(Value, 'offset', 0, persistent=True)
        self.scale = self.Register(Value, 'scale', 1, persistent=True)
        self.nonlinearity = self.Register(Value, 'nonlinearity',  0, persistent=True)
        self.calibration_state = self.Register(EnumProperty, 'calibration_state', 'idle', ['idle', 'centered', 'starboard range', 'port range', 'auto gain'])
        self.calibration.raw = {}
        self.range = self.Register(RangeProperty, 'range',  60, 10, 100, persistent=True)
        self.autogain_state = 'idle'

    def Register(self, _type, name, *args, **kwargs):
        return self.server.Register(_type(*(['rudder.' + name] + list(args)), **kwargs))

    def calibration(self, command):
        if command == 'centered':
            true_angle = 0
        elif command == 'port range':
            true_angle = -self.rudder.range.value
        elif command == 'starboard range':
            true_angle = self.rudder.range.value
        else:
            print 'unhandled rudder_calibration', command
            return
        
            # raw range -.5 to .5
        self.rudder.calibration.raw[command] = {'raw': self.driver.rudder - 0.5,
                                                'rudder': true_angle}
        offset = self.rudder.offset.value
        scale = self.rudder.scale.value
        nonlinearity = self.rudder.nonlinearity.value*scale

        # rudder = (nonlinearity * raw + scale) * raw + offset
        p = []
        for c in self.rudder.calibration.raw:
            p.append(self.rudder.calibration.raw[c])

        l = len(p)
        # 1 point, estimate offset
        if l == 1:
            rudder= p[0]['rudder']
            raw = p[0]['raw']
            offset = rudder - (nonlinearity * raw + scale) * raw

        # 2 points, estimate scale and offset
        elif l == 2:
            rudder0, rudder1 = p[0]['rudder'], p[1]['rudder']
            raw0, raw1 = p[0]['raw'], p[1]['raw']
            if abs(raw1-raw0) > .001:
                scale = (rudder1 - rudder0 + nonlinearity*(raw0**2 - raw1**2)) / (raw1 - raw0)
            offset = rudder0 - (nonlinearity * raw0 + scale) * raw0

            
        # 3 points, estimate nonlinearity scale and offset
        if l == 3:
            rudder0, rudder1, rudder2 = p[0]['rudder'], p[1]['rudder'], p[2]['rudder']
            raw0, raw1, raw2 = p[0]['raw'], p[1]['raw'], p[2]['raw']

            # rudder0 = (nonlinearity*raw0 + scale)*raw0 + offset
            # rudder1 = (nonlinearity*raw1 + scale)*raw1 + offset
            # rudder2 = (nonlinearity*raw2 + scale)*raw2 + offset

            # rudder1 = (nonlinearity*raw1 + scale)*raw1 + rudder0 - (nonlinearity*raw0 + scale)*raw0
            # rudder2 = (nonlinearity*raw2 + scale)*raw2 + rudder0 - (nonlinearity*raw0 + scale)*raw0
            # rudder1 - rudder0 = nonlinearity*(raw1^2 - raw0^2) + scale*(raw1 - raw0)
            # rudder2 - rudder0 = nonlinearity*(raw2^2 - raw0^2) + scale*(raw2 - raw0)


            # scale = (rudder1 - rudder0 - nonlinearity*(raw1^2 - raw0^2)) / (raw1 - raw0)
            # A = (raw2 - raw0)/(raw1 - raw0)
            # rudder2 - rudder0 + A*(rudder0 - rudder1) = nonlinearity*((raw2^2 - raw0^2) - (raw1^2 - raw0^2)*A) 

            A = (raw2 - raw0)/(raw1 - raw0)
            C = (rudder2 - rudder0 + (rudder0 - rudder1)*A)
            D = ((raw2**2 - raw0**2) - (raw1**2 - raw0**2)*A)
            if abs(D) > .001:
                nonlinearity = C / D
            if abs(raw1-raw0) > .001:
                scale = (rudder1 - rudder0 - nonlinearity*(raw1**2 - raw0**2)) / (raw1 - raw0)
            offset = rudder0 - (nonlinearity*raw0 + scale)*raw0

        if abs(scale) <= .01:
            # bad update, trash an other reading
            print 'bad servo rudder calibration', scale, nonlinearity
            while len(self.rudder.calibration.raw) > 1:
                for c in self.rudder.calibration.raw:
                    if c != command:
                        del self.rudder.calibration.raw[c]
                        break
        else:
            self.rudder.offset.update(offset)
            self.rudder.scale.update(scale)

            nonlinearity /= scale
            if abs(nonlinearity) < 2:
                self.rudder.nonlinearity.update(nonlinearity)

    def invalid(self):
        return type(self.angle.value) == type(False)

    def poll(self):
        if self.calibration.value == 'idle':
            return

        if self.rudder.calibration.value == 'auto gain':
            def idle():
                self.autogain_state='idle'
                self.calibration_state.set('idle')

            t = time.time();
            if self.autogain_state=='idle':
                self.gain.set(1)
                self.autogain_state='fwd'
                self.autogain_movetime = t

            # must have rudder readings
            if type(self.value) == type(False):
                idle()

            rng = self.range.value
            #print self.autogain_state, self.angle.value, rng

            if self.autogain_state=='fwd':
                self.command.set(1)
                if abs(self.angle.value) >= rng:
                    self.autogain_state='center'
                    self.autogain_time = t

            if self.autogain_state=='center':
                self.command.set(-1)
                if abs(self.angle.value) < rng - 1:
                    self.autogain_state='rev'
                                        
            if self.autogain_state=='rev':
                self.command.set(-1)
                if abs(self.value) >= rng:
                    dt = time.time() - self.autogain_time
                    #print 'hardover', dt, 'with', rng/dt, 'deg/s'
                    # 5 deg/s is gain of 1

                    gain = min(max(5*dt/rng, .5), 2)
                    if self.angle.value < 0:
#                            print 'negative gain detected'
                        gain = -gain
                    self.gain.set(gain)
                    idle()

            if self.current.value:
                self.autogain_movetime = t

            if t - self.autogain_movetime > 3:
                print 'servo rudder autogain failed'
                idle()
        else: # perform calibration
            self.calibration(self.calibration_state.value)
            self.calibration_state.set('idle')

    def update(self, raw):
        if math.isnan(raw):
            self.angle.update(False)
            return

        # rudder = (nonlinearity*raw + 1)*scale*raw + offset
        self.angle.set((self.nonlinearity.value * raw + 1)*
                       self.scale.value*raw +
                       self.offset.value)

        t = time.time()
        dt = t - self.last_time

        if dt > self.period:
            dt = self.period
        if dt > 0:
            speed = (self.angle.value - self.last) / dt
            self.last_time = t
            self.last = self.angle.value
            self.speed.set(.9*self.speed.value + .1*speed)
