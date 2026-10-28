#!/usr/bin/env python3
"""Run real software EGL and framebuffer readback without X11/Wayland sockets.

This checks the DRM-less graphics primitive locally; it is not a substitute for
loading KWin and the stock mobile effect in the ARM64 integration environment.
"""
import ctypes as c
import json


def run():
    egl = c.CDLL('libEGL.so.1')
    egl.eglGetProcAddress.argtypes = [c.c_char_p]
    egl.eglGetProcAddress.restype = c.c_void_p
    egl.eglGetError.restype = c.c_uint

    def proc(name, result, *args):
        address = egl.eglGetProcAddress(name.encode())
        if not address:
            raise RuntimeError('Missing EGL/GL entry point: ' + name)
        return c.CFUNCTYPE(result, *args)(address)

    pointer = c.c_void_p
    integer = c.c_int
    query_devices = proc('eglQueryDevicesEXT', c.c_uint, integer, c.POINTER(pointer), c.POINTER(integer))
    query_string = proc('eglQueryDeviceStringEXT', c.c_char_p, pointer, integer)
    platform_display = proc('eglGetPlatformDisplayEXT', pointer, integer, pointer, c.POINTER(integer))
    initialize = proc('eglInitialize', c.c_uint, pointer, c.POINTER(integer), c.POINTER(integer))
    bind_api = proc('eglBindAPI', c.c_uint, c.c_uint)
    create_context = proc('eglCreateContext', pointer, pointer, pointer, pointer, c.POINTER(integer))
    make_current = proc('eglMakeCurrent', c.c_uint, pointer, pointer, pointer, pointer)
    destroy_context = proc('eglDestroyContext', c.c_uint, pointer, pointer)
    terminate = proc('eglTerminate', c.c_uint, pointer)

    count = integer()
    assert query_devices(0, None, c.byref(count)), hex(egl.eglGetError())
    devices = (pointer * count.value)()
    assert query_devices(count.value, devices, c.byref(count)), hex(egl.eglGetError())
    software = [d for d in devices if b'EGL_MESA_device_software' in (query_string(d, 0x3055) or b'')]
    assert software, 'No EGL_MESA_device_software device'
    display = platform_display(0x313F, software[0], None)
    assert display, hex(egl.eglGetError())
    major, minor = integer(), integer()
    assert initialize(display, c.byref(major), c.byref(minor)), hex(egl.eglGetError())
    assert bind_api(0x30A2), hex(egl.eglGetError())  # EGL_OPENGL_API
    attributes = (integer * 3)(0x3098, 3, 0x3038)
    context = create_context(display, None, None, attributes)
    assert context, hex(egl.eglGetError())
    assert make_current(display, None, None, context), hex(egl.eglGetError())

    get_string = proc('glGetString', c.c_char_p, c.c_uint)
    gen_textures = proc('glGenTextures', None, integer, c.POINTER(c.c_uint))
    bind_texture = proc('glBindTexture', None, c.c_uint, c.c_uint)
    texture_image = proc('glTexImage2D', None, c.c_uint, integer, integer, integer, integer, integer, c.c_uint, c.c_uint, pointer)
    gen_fbo = proc('glGenFramebuffers', None, integer, c.POINTER(c.c_uint))
    bind_fbo = proc('glBindFramebuffer', None, c.c_uint, c.c_uint)
    attach = proc('glFramebufferTexture2D', None, c.c_uint, c.c_uint, c.c_uint, c.c_uint, integer)
    check = proc('glCheckFramebufferStatus', c.c_uint, c.c_uint)
    viewport = proc('glViewport', None, integer, integer, integer, integer)
    clear_color = proc('glClearColor', None, c.c_float, c.c_float, c.c_float, c.c_float)
    clear = proc('glClear', None, c.c_uint)
    read = proc('glReadPixels', None, integer, integer, integer, integer, c.c_uint, c.c_uint, pointer)
    delete_fbo = proc('glDeleteFramebuffers', None, integer, c.POINTER(c.c_uint))
    delete_texture = proc('glDeleteTextures', None, integer, c.POINTER(c.c_uint))
    texture, framebuffer = c.c_uint(), c.c_uint()
    try:
        gen_textures(1, c.byref(texture))
        bind_texture(0x0DE1, texture.value)
        texture_image(0x0DE1, 0, 0x8058, 8, 8, 0, 0x1908, 0x1401, None)
        gen_fbo(1, c.byref(framebuffer))
        bind_fbo(0x8D40, framebuffer.value)
        attach(0x8D40, 0x8CE0, 0x0DE1, texture.value, 0)
        assert check(0x8D40) == 0x8CD5, 'Framebuffer incomplete'
        viewport(0, 0, 8, 8)
        clear_color(.25, .5, .75, 1)
        clear(0x4000)
        pixels = (c.c_ubyte * (8 * 8 * 4))()
        read(0, 0, 8, 8, 0x1908, 0x1401, pixels)
        expected = (64, 128, 191, 255)
        assert all(abs(pixels[i] - expected[i % 4]) <= 1 for i in range(len(pixels)))
        print(json.dumps({'egl': f'{major.value}.{minor.value}',
                          'renderer': get_string(0x1F01).decode(),
                          'gl': get_string(0x1F02).decode(),
                          'rgba': list(pixels[:4]), 'pixels_checked': 64,
                          'result': 'PASS: software EGL framebuffer readback'}, indent=2))
    finally:
        delete_fbo(1, c.byref(framebuffer))
        delete_texture(1, c.byref(texture))
        make_current(display, None, None, None)
        destroy_context(display, context)
        terminate(display)


if __name__ == '__main__':
    run()
