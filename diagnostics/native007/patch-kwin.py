#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Enable native KWin OpenGL effects on a DRM-less nested X11 server.

The upstream effect/QML implementation is unmodified. Readback is confined to
an explicitly selected software X11 output transport; normal DRM paths remain.
"""
from pathlib import Path
import sys
root=Path(sys.argv[1])
def change(file,old,new):
 p=root/file;s=p.read_text();assert s.count(old)==1,(file,old[:80]);p.write_text(s.replace(old,new))
change('src/core/gpumanager.cpp','m_udevNotifier(std::make_unique<QSocketNotifier>(m_udevMonitor->fd(), QSocketNotifier::Read))','m_udevNotifier(m_udevMonitor ? std::make_unique<QSocketNotifier>(m_udevMonitor->fd(), QSocketNotifier::Read) : nullptr)')
change('src/core/gpumanager.cpp','''    if (m_udmabuf.isValid()) {
        if (auto device = RenderDevice::createSoftwareDevice(*m_udmabufDevId)) {''','''    if (m_udmabuf.isValid() || qEnvironmentVariableIsSet("ARCHOHALL_KWIN_SHM")) {
        struct stat shmStat{};
        stat("/tmp", &shmStat);
        if (auto device = RenderDevice::createSoftwareDevice(m_udmabufDevId.value_or(shmStat.st_dev))) {''')
change('src/core/gpumanager.cpp','''    m_udevMonitor->filterSubsystemDevType("drm");
    connect(m_udevNotifier.get(), &QSocketNotifier::activated, this, &GpuManager::handleUdevEvent);
    m_udevMonitor->enable();''','''    if (m_udevMonitor) {
        m_udevMonitor->filterSubsystemDevType("drm");
        connect(m_udevNotifier.get(), &QSocketNotifier::activated, this, &GpuManager::handleUdevEvent);
        m_udevMonitor->enable();
    } else {
        qWarning("ARCHOHALL_UDEV_UNAVAILABLE: no GPU hotplug monitoring");
    }''')
change('src/backends/x11/x11_windowed_backend.cpp', '    if (!m_hasDri) {', '    if (!m_hasDri && !(qEnvironmentVariableIsSet("ARCHOHALL_KWIN_SHM") && m_hasShm)) {')
change('src/core/gpumanager.cpp', '    scanForRenderDevices();\n}\n\nGpuManager::~GpuManager', '    if (!qEnvironmentVariableIsSet("ARCHOHALL_KWIN_SHM")) {\n        scanForRenderDevices();\n    }\n}\n\nGpuManager::~GpuManager')
change('src/backends/x11/x11_windowed_backend.cpp','''    if (m_hasDri) {
        xcb_dri3_open_cookie_t cookie''','''    if (m_hasDri && !qEnvironmentVariableIsSet("ARCHOHALL_KWIN_SHM")) {
        xcb_dri3_open_cookie_t cookie''')
change('src/backends/x11/x11_windowed_backend.cpp','''    xcb_depth_iterator_t it = xcb_screen_allowed_depths_iterator(m_screen);''','''    if (qEnvironmentVariableIsSet("ARCHOHALL_KWIN_SHM")) {
        m_renderDevice = GpuManager::self()->softwareDevice();
        if (!m_renderDevice) {
            qFatal("ArchOHall software EGL device initialization failed");
        }
    }
    xcb_depth_iterator_t it = xcb_screen_allowed_depths_iterator(m_screen);''')
change('src/backends/x11/x11_windowed_egl_backend.h','class EglSwapchainSlot;','''class ShmGraphicsBufferAllocator;
class QPainterSwapchain;
class QPainterSwapchainSlot;
class EglSwapchainSlot;''')
change('src/backends/x11/x11_windowed_egl_backend.h','''    std::shared_ptr<EglSwapchain> m_swapchain;''','''    std::unique_ptr<ShmGraphicsBufferAllocator> m_shmAllocator;
    std::unique_ptr<QPainterSwapchain> m_shmSwapchain;
    std::shared_ptr<QPainterSwapchainSlot> m_shmBuffer;
    std::unique_ptr<GLTexture> m_readbackTexture;
    std::unique_ptr<GLFramebuffer> m_readbackFramebuffer;
    std::shared_ptr<EglSwapchain> m_swapchain;''')
change('src/backends/x11/x11_windowed_egl_backend.cpp','#include "core/renderdevice.h"','''#include "core/renderdevice.h"
#include "core/shmgraphicsbufferallocator.h"
#include "core/graphicsbufferview.h"
#include "qpainter/qpainterswapchain.h"
#include <cstring>''')
change('src/backends/x11/x11_windowed_egl_backend.cpp','''X11WindowedEglPrimaryLayer::~X11WindowedEglPrimaryLayer()
{
}''','''X11WindowedEglPrimaryLayer::~X11WindowedEglPrimaryLayer()
{
    (void)m_backend->openglContext()->makeCurrent();
    m_readbackFramebuffer.reset();
    m_readbackTexture.reset();
}''')
change('src/backends/x11/x11_windowed_egl_backend.cpp','''    const QSize bufferSize = m_output->modeSize();
    if (!m_swapchain''','''    const QSize bufferSize = m_output->modeSize();
    if (qEnvironmentVariableIsSet("ARCHOHALL_KWIN_SHM")) {
        if (!m_readbackTexture || m_readbackTexture->size() != bufferSize) {
            m_readbackFramebuffer.reset();
            m_readbackTexture = GLTexture::allocate(GL_RGBA8, bufferSize);
            if (!m_readbackTexture) {
                return std::nullopt;
            }
            m_readbackFramebuffer = std::make_unique<GLFramebuffer>(m_readbackTexture.get());
            if (!m_readbackFramebuffer->valid()) {
                return std::nullopt;
            }
            m_shmAllocator = std::make_unique<ShmGraphicsBufferAllocator>();
            m_shmSwapchain = std::make_unique<QPainterSwapchain>(m_shmAllocator.get(), bufferSize, DRM_FORMAT_XRGB8888, false);
        }
        m_shmBuffer = m_shmSwapchain->acquire();
        if (!m_shmBuffer) {
            return std::nullopt;
        }
        m_output->clearExposedArea();
        m_query = GLRenderTimeQuery::begin(m_backend->openglContextRef());
        return OutputLayerBeginFrameInfo{
            .renderTarget = RenderTarget(m_readbackFramebuffer.get()),
            .repaint = Region::infinite(),
        };
    }
    if (!m_swapchain''')
change('src/backends/x11/x11_windowed_egl_backend.cpp','''    EGLNativeFence releaseFence{m_backend->eglDisplayObject()};''','''    if (qEnvironmentVariableIsSet("ARCHOHALL_KWIN_SHM")) {
        const QSize size = m_readbackTexture->size();
        QImage rgba(size, QImage::Format_RGBA8888_Premultiplied);
        GLFramebuffer::pushFramebuffer(m_readbackFramebuffer.get());
        m_backend->openglContext()->glReadnPixels(0, 0, size.width(), size.height(), GL_RGBA, GL_UNSIGNED_BYTE, rgba.sizeInBytes(), rgba.bits());
        GLFramebuffer::popFramebuffer();
        QImage *mapped = m_shmBuffer->view()->image();
        const QImage pixels = rgba.mirrored(false, true).convertToFormat(mapped->format());
        for (int y = 0; y < size.height(); ++y) {
            std::memcpy(mapped->scanLine(y), pixels.constScanLine(y), size.width() * 4);
        }
        m_output->setPrimaryBuffer(m_shmBuffer->buffer());
        m_shmSwapchain->release(m_shmBuffer);
        return true;
    }
    EGLNativeFence releaseFence{m_backend->eglDisplayObject()};''')
change('src/backends/x11/x11_windowed_egl_backend.cpp','''    return m_backend->backend()->driFormats();''','''    if (qEnvironmentVariableIsSet("ARCHOHALL_KWIN_SHM")) {
        return {{DRM_FORMAT_XRGB8888, {DRM_FORMAT_MOD_LINEAR}}};
    }
    return m_backend->backend()->driFormats();''')
change('src/backends/x11/x11_windowed_egl_backend.cpp','''void X11WindowedEglPrimaryLayer::releaseBuffers()
{
    m_buffer.reset();''','''void X11WindowedEglPrimaryLayer::releaseBuffers()
{
    (void)m_backend->openglContext()->makeCurrent();
    m_shmBuffer.reset();
    m_shmSwapchain.reset();
    m_shmAllocator.reset();
    m_readbackFramebuffer.reset();
    m_readbackTexture.reset();
    m_buffer.reset();''')
print('Patched X11 software EGL readback; native KWin effects and shortcuts retained')
