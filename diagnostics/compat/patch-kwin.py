#!/usr/bin/env python3
"""Minimal null-monitor fix for the pinned KWin 6.7.5 compatibility build."""
from pathlib import Path
import sys

p = Path(sys.argv[1]) / 'src/core/gpumanager.cpp'
text = p.read_text()
old = 'm_udevNotifier(std::make_unique<QSocketNotifier>(m_udevMonitor->fd(), QSocketNotifier::Read))'
new = 'm_udevNotifier(m_udevMonitor ? std::make_unique<QSocketNotifier>(m_udevMonitor->fd(), QSocketNotifier::Read) : nullptr)'
assert text.count(old) == 1
text = text.replace(old, new)
old = '''    m_udevMonitor->filterSubsystemDevType("drm");
    connect(m_udevNotifier.get(), &QSocketNotifier::activated, this, &GpuManager::handleUdevEvent);
    m_udevMonitor->enable();'''
new = '''    if (m_udevMonitor) {
        m_udevMonitor->filterSubsystemDevType("drm");
        connect(m_udevNotifier.get(), &QSocketNotifier::activated, this, &GpuManager::handleUdevEvent);
        m_udevMonitor->enable();
    } else {
        qWarning("ARCHOHALL_UDEV_UNAVAILABLE: continuing without GPU hotplug monitoring");
    }'''
assert text.count(old) == 1
p.write_text(text.replace(old, new))

# Confirm that this source actually contains the required software path.
backend = (p.parents[2] / 'src/backends/x11/x11_windowed_backend.cpp').read_text()
assert 'ret.append(QPainterCompositing)' in backend
print('Applied null-monitor fix; X11 QPainter support present')
