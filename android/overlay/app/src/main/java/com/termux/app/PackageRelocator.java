package com.termux.app;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

/** Experimental equal-length prefix relocation before APT invokes dpkg.
 * Java/JNI namespaces are deliberately retained. Does not rebuild upstream packages. */
public final class PackageRelocator {
    private static final String PREFIX = "/data/data/com.archoh/files/usr";
    private static final String[][] REPLACEMENTS = {
        {"data/data/com.termux", "data/data/com.archoh"},
        {"data/user/0/com.termux", "data/user/0/com.archoh"},
        {"\"com.termux\"", "\"com.archoh\""},
        {"'com.termux'", "'com.archoh'"},
        {"com.termux/com.termux.", "com.archoh/com.termux."},
        {"com.termux.service_", "com.archoh.service_"},
        {"com.termux.app.reload_style", "com.archoh.app.reload_style"},
        {"com.termux.app.request_storage_permissions", "com.archoh.app.request_storage_permissions"}
    };
    public static void main(String[] args) throws Exception {
        if (args.length == 1 && "--apt".equals(args[0])) {
            BufferedReader reader = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
            String path;
            while ((path = reader.readLine()) != null) {
                if (!path.isEmpty()) relocate(new File(path));
            }
        } else {
            if (args.length == 0) throw new IllegalArgumentException("Expected .deb paths or --apt");
            for (String path : args) relocate(new File(path));
        }
    }
    private static final class Member {
        byte[] header; String name; File encoded, tar; String suffix;
    }
    private static void relocate(File deb) throws Exception {
        if (!deb.isFile() || !deb.getName().endsWith(".deb")) throw new IOException("Not a Debian archive: " + deb);
        File work = Files.createTempDirectory(deb.getParentFile().toPath(), ".archohall-relocate-").toFile();
        File output = new File(work, "relocated.deb");
        try {
            List<Member> members = new ArrayList<>(); Member control = null, data = null;
            try (DataInputStream in = new DataInputStream(new FileInputStream(deb))) {
                byte[] magic = new byte[8]; in.readFully(magic);
                if (!Arrays.equals(magic, "!<arch>\n".getBytes(StandardCharsets.US_ASCII))) throw new IOException("Invalid ar magic");
                while (true) {
                    int first = in.read(); if (first == -1) break;
                    Member m = new Member(); m.header = new byte[60]; m.header[0] = (byte)first; in.readFully(m.header, 1, 59);
                    if (m.header[58] != '`' || m.header[59] != '\n') throw new IOException("Invalid ar header");
                    m.name = new String(m.header, 0, 16, StandardCharsets.US_ASCII).trim();
                    if (m.name.endsWith("/")) m.name = m.name.substring(0, m.name.length() - 1);
                    long length = Long.parseLong(new String(m.header, 48, 10, StandardCharsets.US_ASCII).trim());
                    if (length < 0) throw new IOException("Negative archive member length");
                    m.encoded = new File(work, "member-" + members.size());
                    try (OutputStream part = new FileOutputStream(m.encoded)) { copyExactly(in, part, length); }
                    if ((length & 1) != 0 && in.read() == -1) throw new EOFException();
                    if (m.name.startsWith("control.tar") || m.name.startsWith("data.tar")) {
                        if (m.name.startsWith("control.tar")) { if (control != null) throw new IOException("Duplicate control"); control = m; }
                        else { if (data != null) throw new IOException("Duplicate data"); data = m; }
                        m.suffix = m.name.substring(m.name.indexOf(".tar") + 4); m.tar = m.encoded;
                        if (!m.suffix.isEmpty()) { m.tar = new File(work, "tar-" + members.size()); codec(m.suffix, true, m.encoded, m.tar); }
                        patchTar(m.tar);
                    }
                    members.add(m);
                }
            }
            if (control == null || data == null) throw new IOException("Missing Debian control/data archive");
            refreshMd5sums(control.tar, data.tar);
            try (OutputStream out = new FileOutputStream(output)) {
                out.write("!<arch>\n".getBytes(StandardCharsets.US_ASCII));
                for (Member m : members) {
                    if (m.suffix != null && !m.suffix.isEmpty()) codec(m.suffix, false, m.tar, m.encoded);
                    byte[] size = String.format(Locale.ROOT, "%-10d", m.encoded.length()).getBytes(StandardCharsets.US_ASCII);
                    if (size.length != 10) throw new IOException("Archive member too large");
                    System.arraycopy(size, 0, m.header, 48, 10); out.write(m.header);
                    try (InputStream part = new FileInputStream(m.encoded)) { copyExactly(part, out, m.encoded.length()); }
                    if ((m.encoded.length() & 1) != 0) out.write('\n');
                }
            }
            try (RandomAccessFile sync = new RandomAccessFile(output, "rw")) { sync.getFD().sync(); }
            if (!output.renameTo(deb)) throw new IOException("Cannot atomically replace " + deb);
            System.err.println("Phosh relocated " + deb.getName());
        } finally { deleteTree(work); }
    }
    private static String tarText(byte[] b, int offset, int count) {
        int end = offset; while (end < offset + count && b[end] != 0) end++;
        return new String(b, offset, end - offset, StandardCharsets.UTF_8);
    }
    private static String normalize(String name) {
        while (name.startsWith("./")) name = name.substring(2);
        while (name.startsWith("/")) name = name.substring(1);
        return name;
    }
    private static void refreshMd5sums(File control, File data) throws Exception {
        Map<String, String> sums = new HashMap<>(); byte[] h = new byte[512], buffer = new byte[65536];
        try (RandomAccessFile f = new RandomAccessFile(data, "r")) {
            long pos = 0; String nextName = null;
            while (pos + 512 <= f.length()) {
                f.seek(pos); f.readFully(h); if (h[0] == 0) break;
                long size = octal(h, 124, 12); long payload = pos + 512;
                String name = tarText(h, 0, 100), prefix = tarText(h, 345, 155);
                if (!prefix.isEmpty()) name = prefix + "/" + name;
                byte type = h[156];
                if (type == 'L' || type == 'x') {
                    if (size > 1024 * 1024) throw new IOException("Oversized tar metadata");
                    byte[] metadata = new byte[(int)size]; f.readFully(metadata);
                    String text = new String(metadata, StandardCharsets.UTF_8);
                    if (type == 'L') nextName = text.replace("\0", "");
                    else for (String line : text.split("\n")) { int i = line.indexOf(" path="); if (i != -1) nextName = line.substring(i + 6); }
                } else {
                    if (nextName != null) { name = nextName; nextName = null; }
                    if (type == 0 || type == '0') {
                        java.security.MessageDigest md5 = java.security.MessageDigest.getInstance("MD5");
                        long left = size; while (left > 0) { int n = f.read(buffer, 0, (int)Math.min(left, buffer.length)); if (n < 0) throw new EOFException(); md5.update(buffer, 0, n); left -= n; }
                        StringBuilder hex = new StringBuilder(); for (byte b : md5.digest()) hex.append(String.format(Locale.ROOT, "%02x", b & 255));
                        sums.put(normalize(name), hex.toString());
                    }
                }
                pos = payload + ((size + 511) / 512) * 512;
            }
        }
        try (RandomAccessFile f = new RandomAccessFile(control, "rw")) {
            long pos = 0;
            while (pos + 512 <= f.length()) {
                f.seek(pos); f.readFully(h); if (h[0] == 0) break;
                long size = octal(h, 124, 12); long payload = pos + 512;
                if ("md5sums".equals(normalize(tarText(h, 0, 100)))) {
                    if (size > 16 * 1024 * 1024) throw new IOException("Oversized md5sums");
                    byte[] bytes = new byte[(int)size]; f.readFully(bytes);
                    int start = 0;
                    for (int end = 0; end <= bytes.length; end++) if (end == bytes.length || bytes[end] == '\n') {
                        if (end - start >= 34) {
                            String name = new String(bytes, start + 34, end - start - 34, StandardCharsets.UTF_8);
                            String sum = sums.get(normalize(name));
                            if (sum == null) throw new IOException("Missing md5sums member: " + name);
                            System.arraycopy(sum.getBytes(StandardCharsets.US_ASCII), 0, bytes, start, 32);
                        }
                        start = end + 1;
                    }
                    f.seek(payload); f.write(bytes);
                }
                pos = payload + ((size + 511) / 512) * 512;
            }
        }
    }
    private static void codec(String suffix, boolean decompress, File input, File output) throws Exception {
        String command;
        switch (suffix) {
            case ".gz": command = "gzip"; break;
            case ".xz": command = "xz"; break;
            case ".zst": command = "zstd"; break;
            case ".bz2": command = "bzip2"; break;
            default: throw new IOException("Unsupported Debian compression: " + suffix);
        }
        String bin = System.getProperty("archohall.relocator.bin", PREFIX + "/bin");
        List<String> argv = new ArrayList<>(); argv.add(bin + "/" + command);
        if (decompress) argv.add("-d"); argv.add("-c"); argv.add(input.getAbsolutePath());
        Process process = new ProcessBuilder(argv).redirectOutput(output).redirectError(ProcessBuilder.Redirect.INHERIT).start();
        if (process.waitFor() != 0) throw new IOException(command + " failed");
    }
    private static void patchTar(File tar) throws Exception {
        // Equal-length replacements preserve ELF offsets, tar sizes and PAX record lengths.
        try (RandomAccessFile file = new RandomAccessFile(tar, "rw")) {
            byte[] chunk = new byte[1024 * 1024 + 128]; long offset = 0;
            while (offset < file.length()) {
                file.seek(offset); int count = file.read(chunk);
                replace(chunk, count);
                int write = (offset + count < file.length()) ? count - 128 : count;
                if (write <= 0) throw new IOException("Invalid patch window");
                file.seek(offset); file.write(chunk, 0, count); offset += write;
            }
            // Recompute each tar header checksum after modifying filenames or symlink targets.
            long position = 0; byte[] header = new byte[512];
            while (position + 512 <= file.length()) {
                file.seek(position); file.readFully(header);
                boolean zero = true; for (byte b : header) zero &= b == 0;
                if (zero) break;
                long size = octal(header, 124, 12);
                Arrays.fill(header, 148, 156, (byte)' '); int checksum = 0;
                for (byte b : header) checksum += b & 255;
                byte[] sum = String.format(Locale.ROOT, "%06o", checksum).getBytes(StandardCharsets.US_ASCII);
                if (sum.length != 6) throw new IOException("Invalid tar checksum");
                System.arraycopy(sum, 0, header, 148, 6); header[154] = 0; header[155] = ' ';
                file.seek(position); file.write(header);
                if (size < 0 || size > file.length() - position - 512) throw new IOException("Invalid tar member size");
                position += 512 + ((size + 511) / 512) * 512;
            }
        }
    }
    private static long octal(byte[] bytes, int offset, int count) throws IOException {
        if ((bytes[offset] & 128) != 0) throw new IOException("Base-256 tar sizes are unsupported");
        long value = 0;
        for (int i = offset; i < offset + count; i++) {
            int b = bytes[i] & 255; if (b == 0 || b == ' ') continue;
            if (b < '0' || b > '7') throw new IOException("Invalid octal tar field");
            value = Math.addExact(Math.multiplyExact(value, 8), b - '0');
        }
        return value;
    }
    private static void replace(byte[] buffer, int count) {
        for (String[] pair : REPLACEMENTS) {
            byte[] old = pair[0].getBytes(StandardCharsets.US_ASCII), replacement = pair[1].getBytes(StandardCharsets.US_ASCII);
            if (old.length != replacement.length) throw new IllegalStateException("Relocation must preserve lengths");
            for (int i = 0; i <= count - old.length; i++) {
                int j = 0; while (j < old.length && buffer[i + j] == old[j]) j++;
                if (j == old.length) { System.arraycopy(replacement, 0, buffer, i, old.length); i += old.length - 1; }
            }
        }
    }
    private static void copyExactly(InputStream in, OutputStream out, long count) throws IOException {
        byte[] buffer = new byte[65536];
        while (count > 0) { int n = in.read(buffer, 0, (int)Math.min(count, buffer.length));
            if (n == -1) throw new EOFException(); out.write(buffer, 0, n); count -= n; }
    }
    private static void deleteTree(File file) {
        File[] children = file.listFiles(); if (children != null) for (File child : children) deleteTree(child);
        file.delete();
    }
}

