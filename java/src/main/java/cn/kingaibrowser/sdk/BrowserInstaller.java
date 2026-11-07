package cn.kingaibrowser.sdk;

import java.io.InputStream;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Duration;
import java.util.HexFormat;
import java.util.Locale;

/** Downloads official installers. Opening their native UI is a separate explicit action. */
public final class BrowserInstaller {
    private BrowserInstaller() {}
    public record Result(String status, String platform, Path installerPath, String sha256,
                         boolean checksumVerified, long bytes, String url) {}

    private static String platform() throws IOException, InterruptedException {
        String os = System.getProperty("os.name").toLowerCase(Locale.ROOT);
        String arch = System.getProperty("os.arch").toLowerCase(Locale.ROOT);
        if (os.startsWith("windows")) {
            String nativeArch = System.getenv("PROCESSOR_ARCHITEW6432");
            if (nativeArch == null) nativeArch = System.getenv("PROCESSOR_ARCHITECTURE");
            if (nativeArch == null) nativeArch = arch;
            if (!nativeArch.equalsIgnoreCase("amd64") && !nativeArch.equalsIgnoreCase("x86_64"))
                throw new IOException("Windows installers support Intel/AMD x64 only, not ARM or 32-bit Windows");
            return "windows-x64";
        }
        if (os.contains("mac")) {
            if (!arch.equals("aarch64") && !arch.equals("arm64")) {
                Process probe = new ProcessBuilder("/usr/sbin/sysctl", "-in", "hw.optional.arm64").start();
                String result = new String(probe.getInputStream().readAllBytes(), java.nio.charset.StandardCharsets.UTF_8).trim();
                if (probe.waitFor() != 0 || !result.equals("1")) throw new IOException("macOS installer supports Apple Silicon only");
            }
            return "macos-arm64";
        }
        throw new IOException("Installers support Windows x64 and Apple Silicon macOS only");
    }

    public static Result download(Path downloadDir, String expectedSha256) throws IOException, InterruptedException {
        String platform = platform();
        if (expectedSha256 != null && !expectedSha256.matches("[a-fA-F0-9]{64}"))
            throw new IllegalArgumentException("expectedSha256 must be 64 hexadecimal characters");
        Path directory = downloadDir == null ? (platform.equals("windows-x64")
            ? Path.of("D:\\code\\KingAIBrowser-downloads")
            : Path.of(System.getProperty("user.home"), "Downloads", "KingAIBrowser")) : downloadDir;
        if (!directory.isAbsolute()) throw new IllegalArgumentException("downloadDir must be absolute");
        Files.createDirectories(directory);
        Path work = Files.createTempDirectory(directory, "download-");
        String filename = platform.equals("windows-x64") ? "KingAIBrowserSetup.exe" : "KingAIBrowser.dmg";
        Path partial = work.resolve(filename + ".part"), destination = work.resolve(filename);
        String url = "https://161.118.255.111/download/" + filename;
        URI current = URI.create(url);
        HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(30)).followRedirects(HttpClient.Redirect.NEVER).build();
        long bytes = 0;
        String hash;
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            for (int redirects = 0; ; redirects++) {
                HttpRequest request = HttpRequest.newBuilder(current).timeout(Duration.ofMinutes(10)).GET().build();
                HttpResponse<InputStream> response = client.send(request, HttpResponse.BodyHandlers.ofInputStream());
                try (InputStream input = response.body()) {
                    int status = response.statusCode();
                    if (status == 301 || status == 302 || status == 303 || status == 307 || status == 308) {
                        if (redirects >= 5) throw new IOException("Too many installer redirects");
                        current = current.resolve(response.headers().firstValue("location").orElseThrow(() -> new IOException("Missing redirect location")));
                        if (!"https".equalsIgnoreCase(current.getScheme())) throw new IOException("Installer redirects must use HTTPS");
                        continue;
                    }
                    if (status != 200 || response.headers().firstValue("content-type").orElse("").contains("text/html"))
                        throw new IOException("Server did not return an installer file");
                    try (var output = Files.newOutputStream(partial, java.nio.file.StandardOpenOption.CREATE_NEW)) {
                        byte[] buffer = new byte[1024 * 1024];
                        int read;
                        while ((read = input.read(buffer)) != -1) {
                            bytes += read;
                            if (bytes > 3L * 1024 * 1024 * 1024) throw new IOException("Installer exceeds 3 GiB");
                            digest.update(buffer, 0, read); output.write(buffer, 0, read);
                        }
                    }
                    long declared = response.headers().firstValueAsLong("content-length").orElse(-1);
                    if (bytes == 0 || (declared >= 0 && bytes != declared)) throw new IOException("Installer download is incomplete");
                    break;
                }
            }
            hash = HexFormat.of().formatHex(digest.digest());
            if (expectedSha256 != null && !hash.equalsIgnoreCase(expectedSha256)) throw new IOException("Installer SHA-256 mismatch");
            if (platform.equals("windows-x64")) {
                try (var input = Files.newInputStream(partial)) {
                    if (input.read() != 'M' || input.read() != 'Z') throw new IOException("Invalid Windows executable");
                }
            }
            Files.move(partial, destination);
        } catch (NoSuchAlgorithmException impossible) {
            throw new IllegalStateException(impossible);
        } finally { Files.deleteIfExists(partial); }
        return new Result("downloaded", platform, destination, hash, expectedSha256 != null, bytes, url);
    }

    public static Result openInstaller(Result downloaded) throws IOException, InterruptedException {
        String current = platform();
        if (!current.equals(downloaded.platform()) || !Files.isRegularFile(downloaded.installerPath()))
            throw new IOException("Installer platform/file mismatch");
        ProcessBuilder process = current.equals("windows-x64")
            ? new ProcessBuilder(downloaded.installerPath().toString())
            : new ProcessBuilder("/usr/bin/open", downloaded.installerPath().toString());
        process.inheritIO().start();
        return new Result("installer_started", current, downloaded.installerPath(), downloaded.sha256(),
            downloaded.checksumVerified(), downloaded.bytes(), downloaded.url());
    }
}
