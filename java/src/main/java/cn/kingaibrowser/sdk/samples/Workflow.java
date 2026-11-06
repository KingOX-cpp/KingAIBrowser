package cn.kingaibrowser.sdk.samples;

import cn.kingaibrowser.sdk.KingAI;
import com.fasterxml.jackson.databind.JsonNode;
import java.util.Map;
import java.util.UUID;

/** Complete live workflow. Serve examples/demo.html first; see examples/README.md. */
public final class Workflow {
    private Workflow() {}

    private static String oneRef(KingAI.Session browser, String selector) {
        JsonNode result = browser.query(Map.of("selector", selector, "include_html", true, "limit", 2));
        System.out.println("DOM query: " + result);
        JsonNode elements = result.path("elements");
        if (!elements.isArray() || elements.size() != 1 || elements.get(0).path("ref").asText().isBlank()) {
            throw new IllegalStateException("Expected exactly one actionable DOM element: " + selector);
        }
        return elements.get(0).path("ref").asText();
    }

    public static String runWorkflow(KingAI api) {
        System.out.println("Capabilities: " + api.info());
        System.out.println("Saved environments: " + api.profiles());
        String name = "Java workflow " + UUID.randomUUID();
        String id = api.createProfile(name, Map.of("language", "en-US")).path("profileId").asText();
        if (id.isBlank()) throw new IllegalStateException("Profile creation returned no ID");
        // Configure before startup; only the newly created environment is modified.
        api.updateProfile(id, Map.of("name", name + " configured"));
        System.out.println("Configured environment: " + api.profile(id));
        KingAI.Session browser = api.start(Map.of("profile_id", id));
        try {
            browser.newTab("http://127.0.0.1:8765/demo.html");
            browser.call("browser_wait", Map.of("selector", "#demo-form", "state", "visible", "timeout_ms", 15000));
            System.out.println("Interactive DOM: " + browser.snapshot(Map.of("mode", "interactive", "limit", 30)));
            System.out.println("DOM inventory: " + browser.query(Map.of("limit", 30, "include_html", true, "max_chars", 12000)));
            // Generic session.call shows how to pass explicit tool options.
            // humanize=false avoids requiring humanize entitlement for this demo.
            browser.call("browser_fill", Map.of("ref", oneRef(browser, "#name"), "text", "KingAI Java", "humanize", false));
            browser.call("browser_fill", Map.of("ref", oneRef(browser, "#message"), "text", "Hello from the Java SDK", "humanize", false));
            browser.call("browser_click", Map.of("ref", oneRef(browser, "#submit"), "humanize", false));
            browser.call("browser_wait", Map.of("selector", "#result[data-submitted=\"true\"]", "text", "Submitted: KingAI Java", "timeout_ms", 10000));
            String result = browser.evaluate("document.querySelector('#result').textContent").asText();
            if (!result.equals("Submitted: KingAI Java | Hello from the Java SDK")) {
                throw new IllegalStateException("Unexpected form result: " + result);
            }
            System.out.println("Submission result: " + result);
            System.out.println("Page: " + browser.read());
            System.out.println("Tabs: " + browser.tabs());
            return result;
        } finally {
            browser.detach(); // Retain saved profile/window for inspection.
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 1 || !args[0].equals("--live")) {
            throw new IllegalArgumentException("Pass --live to create and operate a real saved environment");
        }
        try (KingAI api = new KingAI()) { runWorkflow(api); }
    }
}
