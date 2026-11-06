// Complete live workflow. Serve examples/demo.html first; see examples/README.md.
package main

import (
    "context"
    "crypto/rand"
    "encoding/hex"
    "errors"
    "flag"
    "fmt"
    "os"

    kingai "github.com/KingOX-cpp/KingAIBrowser/go"
)

func oneRef(ctx context.Context, browser *kingai.Session, selector string) (string, error) {
    result, err := browser.Query(ctx, kingai.Arguments{"selector": selector, "include_html": true, "limit": 2})
    if err != nil { return "", err }
    fmt.Println("DOM query:", result)
    object, ok := result.(map[string]any)
    if !ok { return "", errors.New("query returned no object") }
    elements, ok := object["elements"].([]any)
    if !ok || len(elements) != 1 { return "", fmt.Errorf("expected one DOM element: %s", selector) }
    element, ok := elements[0].(map[string]any)
    if !ok { return "", errors.New("query returned an invalid element") }
    ref, ok := element["ref"].(string)
    if !ok || ref == "" { return "", errors.New("element has no actionable ref") }
    return ref, nil
}

func runWorkflow(ctx context.Context, api *kingai.Client) (err error) {
    info, err := api.Info(ctx)
    if err != nil { return err }
    fmt.Println("Capabilities:", info)
    profiles, err := api.Profiles(ctx)
    if err != nil { return err }
    fmt.Println("Saved environments:", profiles)
    random := make([]byte, 12)
    if _, err = rand.Read(random); err != nil { return err }
    name := "Go workflow " + hex.EncodeToString(random)
    created, err := api.CreateProfile(ctx, name, kingai.Arguments{"language": "en-US"})
    if err != nil { return err }
    object, ok := created.(map[string]any)
    if !ok { return errors.New("profile creation returned no object") }
    id, ok := object["profileId"].(string)
    if !ok || id == "" { return errors.New("profile creation returned no ID") }
    if _, err = api.UpdateProfile(ctx, id, kingai.Arguments{"name": name + " configured"}); err != nil { return err }
    profile, err := api.Profile(ctx, id)
    if err != nil { return err }
    fmt.Println("Configured environment:", profile)
    browser, err := api.Start(ctx, kingai.Arguments{"profile_id": id})
    if err != nil { return err }
    defer func() {
        // Leave the window open. Report detach errors without hiding the original error.
        _, detachErr := browser.Detach(ctx)
        err = errors.Join(err, detachErr)
    }()
    if _, err = browser.NewTab(ctx, "http://127.0.0.1:8765/demo.html"); err != nil { return err }
    if _, err = browser.Call(ctx, "browser_wait", kingai.Arguments{"selector": "#demo-form", "state": "visible", "timeout_ms": 15000}); err != nil { return err }
    snapshot, err := browser.Snapshot(ctx, kingai.Arguments{"mode": "interactive", "limit": 30})
    if err != nil { return err }
    fmt.Println("Interactive DOM:", snapshot)
    dom, err := browser.Query(ctx, kingai.Arguments{"include_html": true, "limit": 30, "max_chars": 12000})
    if err != nil { return err }
    fmt.Println("DOM inventory:", dom)
    for _, field := range [][2]string{{"#name", "KingAI Go"}, {"#message", "Hello from the Go SDK"}} {
        ref, e := oneRef(ctx, browser, field[0])
        if e != nil { return e }
        // Explicit false avoids requiring humanize entitlement for this local demo.
        if _, e = browser.Call(ctx, "browser_fill", kingai.Arguments{"ref": ref, "text": field[1], "humanize": false}); e != nil { return e }
    }
    ref, err := oneRef(ctx, browser, "#submit")
    if err != nil { return err }
    if _, err = browser.Call(ctx, "browser_click", kingai.Arguments{"ref": ref, "humanize": false}); err != nil { return err }
    if _, err = browser.Call(ctx, "browser_wait", kingai.Arguments{"selector": "#result[data-submitted=\"true\"]", "text": "Submitted: KingAI Go", "timeout_ms": 10000}); err != nil { return err }
    result, err := browser.Evaluate(ctx, "document.querySelector('#result').textContent")
    if err != nil { return err }
    if result != "Submitted: KingAI Go | Hello from the Go SDK" { return fmt.Errorf("unexpected form result: %v", result) }
    fmt.Println("Submission result:", result)
    page, err := browser.Read(ctx)
    if err != nil { return err }
    fmt.Println("Page:", page)
    tabs, err := browser.Tabs(ctx)
    if err != nil { return err }
    fmt.Println("Tabs:", tabs)
    return nil
}

func run() error {
    live := flag.Bool("live", false, "Create and operate a real saved environment")
    flag.Parse()
    if !*live { return errors.New("pass --live to operate your real installation") }
    ctx := context.Background()
    api, err := kingai.Connect(ctx, kingai.Options{})
    if err != nil { return err }
    defer api.Close()
    return runWorkflow(ctx, api)
}

func main() {
    if err := run(); err != nil { fmt.Fprintln(os.Stderr, err); os.Exit(1) }
}
