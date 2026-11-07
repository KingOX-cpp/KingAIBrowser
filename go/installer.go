package kingai

import (
    "context"
    "crypto/sha256"
    "encoding/hex"
    "errors"
    "fmt"
    "io"
    "net/http"
    "os"
    "os/exec"
    "path/filepath"
    "runtime"
    "strings"
    "time"
)

type InstallOptions struct { DownloadDir string; SHA256 string; DownloadOnly bool }
type InstallResult struct { Status string; Platform string; InstallerPath string; SHA256 string; ChecksumVerified bool; Bytes int64; URL string }

func installerTarget() (string, string, error) {
    if runtime.GOOS == "windows" {
        arch := os.Getenv("PROCESSOR_ARCHITEW6432")
        if arch == "" { arch = os.Getenv("PROCESSOR_ARCHITECTURE") }
        if arch == "" { arch = runtime.GOARCH }
        if !strings.EqualFold(arch,"amd64") && !strings.EqualFold(arch,"x86_64") { return "","",errors.New("Windows installer requires Intel/AMD x64; ARM and 32-bit Windows are unsupported") }
        return "windows-x64", "KingAIBrowserSetup.exe", nil
    }
    if runtime.GOOS == "darwin" {
        if runtime.GOARCH != "arm64" {
            output,err := exec.Command("/usr/sbin/sysctl","-in","hw.optional.arm64").Output()
            if err != nil || strings.TrimSpace(string(output)) != "1" { return "","",errors.New("macOS installer supports Apple Silicon only") }
        }
        return "macos-arm64", "KingAIBrowser.dmg", nil
    }
    return "","",errors.New("installers support Windows x64 and Apple Silicon macOS only")
}

// Install downloads an official installer and optionally opens its native UI.
// InstallerStarted does not mean installation or MCP discovery has completed.
func Install(ctx context.Context, options InstallOptions) (*InstallResult, error) {
    platform, filename, err := installerTarget()
    if err != nil { return nil, err }
    if options.SHA256 != "" {
        decoded,e := hex.DecodeString(options.SHA256)
        if e != nil || len(decoded) != 32 { return nil,errors.New("SHA256 must be 64 hexadecimal characters") }
    }
    directory := options.DownloadDir
    if directory == "" {
        if runtime.GOOS == "windows" { directory = `D:\code\KingAIBrowser-downloads` } else {
            home,e := os.UserHomeDir(); if e != nil { return nil,e }; directory = filepath.Join(home,"Downloads","KingAIBrowser")
        }
    }
    if !filepath.IsAbs(directory) { return nil,errors.New("DownloadDir must be absolute") }
    if err = os.MkdirAll(directory,0700); err != nil { return nil,err }
    work,err := os.MkdirTemp(directory,"download-")
    if err != nil { return nil,err }
    partial := filepath.Join(work,filename+".part")
    defer os.Remove(partial)
    url := "https://161.118.255.111/download/"+filename
    requestCtx,cancel := context.WithTimeout(ctx,10*time.Minute); defer cancel()
    request,err := http.NewRequestWithContext(requestCtx,http.MethodGet,url,nil)
    if err != nil { return nil,err }
    client := &http.Client{CheckRedirect:func(req *http.Request,via []*http.Request)error {
        if req.URL.Scheme != "https" || len(via)>5 { return errors.New("invalid or excessive installer redirects") }; return nil
    }}
    response,err := client.Do(request)
    if err != nil { return nil,fmt.Errorf("installer HTTPS download failed (TLS verification remains enabled): %w",err) }
    defer response.Body.Close()
    if response.StatusCode != 200 || strings.Contains(strings.ToLower(response.Header.Get("Content-Type")),"text/html") { return nil,errors.New("server did not return an installer file") }
    output,err := os.OpenFile(partial,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600)
    if err != nil { return nil,err }
    digest := sha256.New()
    const maximum = int64(3*1024*1024*1024)
    size,copyErr := io.Copy(io.MultiWriter(output,digest),io.LimitReader(response.Body,maximum+1))
    closeErr := output.Close()
    if copyErr != nil || closeErr != nil { return nil,errors.Join(copyErr,closeErr) }
    if size==0 || size>maximum || (response.ContentLength>=0 && size!=response.ContentLength) { return nil,errors.New("installer size is invalid or incomplete") }
    actual := hex.EncodeToString(digest.Sum(nil))
    if options.SHA256!="" && !strings.EqualFold(options.SHA256,actual) { return nil,errors.New("installer SHA-256 mismatch") }
    if platform=="windows-x64" {
        file,e := os.Open(partial); if e!=nil { return nil,e }; header:=make([]byte,2); _,e=io.ReadFull(file,header); file.Close()
        if e!=nil || string(header)!="MZ" { return nil,errors.New("invalid Windows executable") }
    }
    destination := filepath.Join(work,filename)
    if err=os.Rename(partial,destination);err!=nil { return nil,err }
    result:=&InstallResult{Status:"downloaded",Platform:platform,InstallerPath:destination,SHA256:actual,ChecksumVerified:options.SHA256!="",Bytes:size,URL:url}
    if !options.DownloadOnly {
        command:=exec.Command(destination)
        if runtime.GOOS=="darwin" { command=exec.Command("/usr/bin/open",destination) }
        if err=command.Start();err!=nil { return result,fmt.Errorf("installer downloaded but could not be opened: %w",err) }
        go func(){ _=command.Wait() }()
        result.Status="installer_started"
    }
    return result,nil
}
